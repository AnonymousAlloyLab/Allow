"""Private PostgreSQL wire gate: SQL is admitted before any SQL-bearing frame is sent.

The proxy preserves protocol payloads. Grammar acceptance is neither SQL static
validity nor authorization; PostgreSQL still executes queries and enforces RLS.
"""
import argparse
import asyncio
from collections import Counter, deque
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import sys
import time
import threading

from .sql_guard import ParserGate, SQLGuardError, is_context_setting
from .sql_context_identity import peer_identity
from .sql_context_lease import ContextLeases
from .sql_context_protocol import StrictContextProtocol
from .sql_inventory import source_names

MAX_FRAME = 8388608
MAX_SQL = 1048576
MAX_STARTUP = 65536
MAX_OBJECTS = 256
MAX_METADATA = 4194304
MAX_NAME = 63
FRAME_SECONDS = 30
HANDSHAKE_SECONDS = 15
TAGS = {'allow-app', 'allow-bootstrap', 'allow-recovery', 'allow-tests',
        'allow-pg-dump', 'allow-pg-restore', 'allow-migration', 'allow-proxy-readiness',
        'allow-recovery-dump', 'allow-recovery-restore', 'allow-recovery-control',
        'allow-document-context', 'allow-context-observer'}
GATE_REASONS = {'invalid SQL bytes', 'parser identity mismatch', 'parser unavailable',
                'parser rejected', 'parser output too large', 'parser output unavailable',
                'parser response framing', 'parser evidence mismatch', 'invalid productions',
                'forbidden statement', 'unreviewed setting', 'unreviewed extension',
                'invalid tokens', 'unicode identifier', 'unreviewed set_config',
                'prepared transaction forbidden', 'copy program forbidden', 'parser admission failed',
                'nested native statement', 'native statement is not sole top-level statement',
                'invalid native statement name', 'multiple native statements',
                'invalid native parameter declaration', 'invalid native prepare body',
                'empty native prepare body', 'invalid native prepare body span',
                'invalid token span', 'invalid statement families'}


class ProtocolError(ValueError):
    """Content-free error for a rejected protocol shape or unsupported transition."""


def integer(value):
    """Encode a PostgreSQL unsigned four-byte length or protocol discriminator."""
    return struct.pack('!I', value)


def packet(kind, body):
    """Preserve the PostgreSQL length convention, which includes its own four bytes."""
    return kind + integer(len(body) + 4) + body


def context_error(body):
    """Retain only a validated timeout SQLSTATE, discarding every private error field."""
    code, offset, seen = b'58000', 0, False
    try:
        while offset < len(body) and body[offset:offset + 1] != b'\0':
            kind = body[offset:offset + 1]
            value, offset = cstring(body, offset + 1)
            if kind == b'C':
                if seen:
                    return b'SERROR\0VERROR\0C58000\0MContext query unavailable\0\0'
                seen = True
                if value in (b'55P03', b'57014', b'25P03'):
                    code = value
        if offset != len(body) - 1:
            code = b'58000'
    except (ValueError, UnicodeError):
        code = b'58000'
    return b'SERROR\0VERROR\0C' + code + b'\0MContext query unavailable\0\0'


def cstring(body, offset=0):
    """Read an exact UTF-8 NUL-delimited field, returning bytes and its next offset."""
    end = body.find(b'\0', offset)
    if end < 0:
        raise ProtocolError('missing_terminator')
    value = body[offset:end]
    value.decode('utf-8', errors='strict')
    return value, end + 1


def complete_string(body):
    """Require precisely one terminated field rather than silently ignoring trailing bytes."""
    value, end = cstring(body)
    if end != len(body):
        raise ProtocolError('trailing_payload')
    return value


def object_name(value):
    """Reject PostgreSQL hash-key truncation aliases for statements and portals."""
    if len(value) > MAX_NAME:
        raise ProtocolError('object_name_limit')
    return value


def count16(body, offset):
    """Decode a bounded unsigned count, rejecting an incomplete frame."""
    if offset + 2 > len(body):
        raise ProtocolError('short_count')
    return struct.unpack_from('!H', body, offset)[0], offset + 2


def validate_bind(body):
    """Validate Bind framing without interpreting text or binary parameter values as SQL."""
    portal, offset = cstring(body)
    statement, offset = cstring(body, offset)
    formats, offset = count16(body, offset)
    for _ in range(formats):
        value, offset = count16(body, offset)
        if value not in (0, 1):
            raise ProtocolError('invalid_format')
    parameters, offset = count16(body, offset)
    if formats not in (0, 1, parameters):
        raise ProtocolError('format_count_mismatch')
    for _ in range(parameters):
        if offset + 4 > len(body):
            raise ProtocolError('short_parameter')
        length = struct.unpack_from('!i', body, offset)[0]
        offset += 4
        if length < -1 or offset + max(length, 0) > len(body):
            raise ProtocolError('parameter_length')
        offset += max(length, 0)
    results, offset = count16(body, offset)
    for _ in range(results):
        value, offset = count16(body, offset)
        if value not in (0, 1):
            raise ProtocolError('invalid_result_format')
    if offset != len(body):
        raise ProtocolError('bind_trailing_payload')
    return portal, statement


@dataclass(frozen=True)
class Statement:
    """Immutable provenance captured only after successful parser admission."""
    name: bytes
    sql: bytes
    generation: int
    body_span: tuple[int, int] | None = None


@dataclass(frozen=True)
class Portal:
    """A bound statement snapshot remains independent of later named statement replacement."""
    statement: Statement
    cycle: int


class ProtocolState:
    """Conservative accepted provenance; PostgreSQL alone determines object/execution success."""

    def __init__(self):
        self.statements = {}
        self.portals = {}
        self.cycle = 0
        self.generation = 0
        self.barriers = deque()
        self.pending = set()
        self.initial_ready = False
        self.copy_in = False

    def budget(self):
        """Reject bounded-state exhaustion before storing further SQL metadata."""
        if len(self.statements) > MAX_OBJECTS or len(self.portals) > MAX_OBJECTS:
            raise ProtocolError('object_limit')
        size = sum(len(k) + len(v.sql) for k, v in self.statements.items())
        size += sum(len(k) + len(v.statement.sql) for k, v in self.portals.items())
        if size > MAX_METADATA or max(len(self.barriers), len(self.pending)) > MAX_OBJECTS:
            raise ProtocolError('metadata_limit')

    def remember_statement(self, name, sql, body_span=None):
        """Retain accepted source in the shared protocol/native statement namespace."""
        object_name(name)
        self.generation += 1
        self.statements[name] = Statement(name, sql, self.generation, body_span)

    def native_statement(self, sql, decision):
        """Apply immutable classification only to this connection's accepted provenance."""
        if decision is None:
            return
        if decision.kind == 'prepare':
            self.remember_statement(decision.name, sql, decision.body_span)
        elif decision.kind == 'execute':
            if decision.name not in self.statements:
                raise ProtocolError('unknown_native_statement')
        else:
            raise ProtocolError('native_classification')

    def seal_cycle(self):
        """Mark an effect and associate its Q/Sync Ready before any transport write."""
        self.pending.add(self.cycle)
        self.barriers.append(self.cycle)
        self.cycle += 1

    def accept_sql(self, kind, body, sql, decision=None):
        """Record accepted SQL only after the parser gate has returned successfully."""
        self.native_statement(sql, decision)
        if kind == b'Q':
            self.statements.pop(b'', None)
            self.portals.pop(b'', None)
            self.seal_cycle()
        else:
            name, _ = cstring(body)
            self.remember_statement(name, sql)
            self.pending.add(self.cycle)
        self.budget()

    def sql_request(self, kind, body):
        """Extract the exact SQL bytes from Q/P, requiring complete message framing."""
        if self.copy_in:
            raise ProtocolError('sql_during_copy')
        if self.pending:
            raise ProtocolError('pending_lexical_effect')
        if kind == b'Q':
            sql = complete_string(body)
        else:
            name, offset = cstring(body)
            object_name(name)
            sql, offset = cstring(body, offset)
            count, offset = count16(body, offset)
            if offset + count * 4 != len(body):
                raise ProtocolError('parse_parameter_types')
        if len(sql) > MAX_SQL:
            raise ProtocolError('sql_limit')
        return sql

    def control(self, kind, body):
        """Validate non-SQL frontend frames and update bounded connection-local provenance."""
        if self.copy_in and kind not in (b'd', b'c', b'f', b'H', b'S', b'X'):
            raise ProtocolError('copy_phase')
        if kind == b'B':
            portal, name = validate_bind(body)
            object_name(portal)
            object_name(name)
            if name not in self.statements:
                raise ProtocolError('unknown_statement')
            self.portals[portal] = Portal(self.statements[name], self.cycle)
        elif kind == b'E':
            name, end = cstring(body)
            object_name(name)
            if end + 4 != len(body) or name not in self.portals:
                raise ProtocolError('unknown_portal')
            if struct.unpack_from('!i', body, end)[0] < 0:
                raise ProtocolError('negative_row_limit')
        elif kind in (b'C', b'D'):
            self.object_control(kind, body)
        elif kind in (b'S', b'H', b'X', b'c'):
            self.empty_control(kind, body)
        elif kind in (b'd', b'f'):
            if not self.copy_in:
                raise ProtocolError('copy_outside_phase')
            if kind == b'f':
                complete_string(body)
                self.copy_in = False
        else:
            raise ProtocolError('unsupported_frontend_message')
        if kind in (b'B', b'D', b'E', b'C'):
            self.pending.add(self.cycle)
        self.budget()

    def object_control(self, kind, body):
        """Handle Describe/Close; Close removes dependent local portal provenance conservatively."""
        if not body or body[:1] not in (b'S', b'P'):
            raise ProtocolError('object_kind')
        name = object_name(complete_string(body[1:]))
        objects = self.statements if body[:1] == b'S' else self.portals
        if name not in objects:
            raise ProtocolError('unknown_object')
        if kind == b'C':
            objects.pop(name)
            if body[:1] == b'S':
                self.portals = {key: value for key, value in self.portals.items()
                                if value.statement.name != name}

    def empty_control(self, kind, body):
        """Account for synchronization barriers without confusing later pipelined portals."""
        if body:
            raise ProtocolError('unexpected_payload')
        if kind == b'c':
            if not self.copy_in:
                raise ProtocolError('copy_outside_phase')
            self.copy_in = False
        if kind == b'S':
            self.seal_cycle()

    def ready(self, status):
        """Expire portals for a completed idle cycle while retaining later pipelined objects."""
        if status not in (b'I', b'T', b'E'):
            raise ProtocolError('ready_status')
        if not self.initial_ready:
            if self.barriers or self.pending or status != b'I':
                raise ProtocolError('startup_ready')
            self.initial_ready = True
            return
        if not self.barriers:
            raise ProtocolError('unexpected_ready')
        finished = self.barriers.popleft()
        self.pending = {cycle for cycle in self.pending if cycle > finished}
        if status == b'I':
            self.portals = {key: value for key, value in self.portals.items()
                            if value.cycle > finished}
        self.copy_in = False


async def read_exact(reader, size, timeout=FRAME_SECONDS):
    """Apply a progress deadline to each bounded complete frame read."""
    return await asyncio.wait_for(reader.readexactly(size), timeout)


async def read_frame(reader):
    """Check advertised size before allocation, then return one immutable complete frame."""
    # Silence between messages is legitimate: it includes idle transactions and
    # long-running queries. Only an incomplete frame receives a progress deadline.
    first = await reader.readexactly(1)
    header = first + await read_exact(reader, 4)
    length = struct.unpack('!I', header[1:])[0]
    if length < 4 or length > MAX_FRAME:
        raise ProtocolError('frame_length')
    body = await read_exact(reader, length - 4)
    return header[:1], body


async def send(writer, data):
    """Bound write backpressure; never accumulate unbounded outgoing messages."""
    writer.write(data)
    await asyncio.wait_for(writer.drain(), FRAME_SECONDS)


def startup_fields(body):
    """Admit only ordinary version3 UTF-8 sessions with a closed startup parameter set."""
    if body[:4] != integer(196608) or not body.endswith(b'\0'):
        raise ProtocolError('startup_protocol')
    fields = body[4:-1].split(b'\0')
    if fields[-1:] == [b'']:
        fields.pop()
    if len(fields) % 2:
        raise ProtocolError('startup_fields')
    result = {}
    for key, value in zip(fields[::2], fields[1::2]):
        key, value = key.decode('utf-8'), value.decode('utf-8')
        if key in result or key not in {'user', 'database', 'application_name', 'client_encoding', 'options'}:
            raise ProtocolError('startup_parameter')
        result[key] = value
    if not result.get('user') or not result.get('database'):
        raise ProtocolError('startup_identity')
    if result.get('client_encoding', 'UTF8').replace('-', '').upper() != 'UTF8' or result.get('options', ''):
        raise ProtocolError('startup_lexical_mode')
    return result


class Session:
    """One authenticated transport with separately parsed SQL and uninterpreted bound data."""

    def __init__(self, server, reader, writer):
        self.server, self.reader, self.writer = server, reader, writer
        self.backend_reader = self.backend_writer = None
        self.state = ProtocolState()
        self.tag = 'other'
        self.authenticated = False
        self.ready_event = asyncio.Event()
        self.lexical = {}
        self.cancel_key = None
        self.lease_kind = None
        self.context_protocol = None
        self.owner_task = asyncio.current_task()
        self.context_error_sent = False

    async def start(self):
        """Apply one deadline across negotiation, authentication and first readiness."""
        current = asyncio.current_task()
        timer = asyncio.get_running_loop().call_later(
            HANDSHAKE_SECONDS, self.handshake_expired, current)
        try:
            await self.start_session()
        finally:
            timer.cancel()

    def handshake_expired(self, task):
        """A slow startup cannot retain cancellation capacity across renewed per-read deadlines."""
        if not self.ready_event.is_set():
            self.server.record(self.tag, 'handshake_timeout')
            task.cancel()

    async def start_session(self):
        """Read bounded startup, reserve normal capacity, then relay until either peer stops."""
        raw = await self.startup_packet()
        if raw[4:8] == integer(80877102):
            await self.cancel(raw)
            return
        fields = startup_fields(raw[4:])
        application = fields.get('application_name', 'other')
        self.lease_kind = self.server.contexts.attach(self, fields, peer_identity(self.writer))
        self.tag = ('allow-document-context' if self.lease_kind == 'context' else
                    'allow-context-observer' if self.lease_kind == 'observer' else application)
        if self.tag not in TAGS:
            self.tag = 'other'
        if self.lease_kind is not None:
            self.context_protocol = StrictContextProtocol(self.lease_kind)
        if self.lease_kind is None and self.server.active >= 15:
            raise ProtocolError('session_capacity')
        if self.lease_kind is None:
            self.server.active += 1
        self.server.record(self.tag, 'connections')
        try:
            self.backend_reader, self.backend_writer = await asyncio.wait_for(
                asyncio.open_unix_connection(str(self.server.backend)), 15)
            await send(self.backend_writer, raw)
            await self.relay()
        finally:
            if self.lease_kind is None:
                self.server.active -= 1

    async def startup_packet(self):
        """Refuse encryption negotiation on this private Unix-only endpoint, then read version3."""
        for _ in range(3):
            length = struct.unpack('!I', await read_exact(self.reader, 4, 15))[0]
            if length < 8 or length > MAX_STARTUP:
                raise ProtocolError('startup_length')
            body = await read_exact(self.reader, length - 4, 15)
            if length == 8 and body in (integer(80877103), integer(80877104)):
                await send(self.writer, b'N')
                continue
            return integer(length) + body
        raise ProtocolError('repeated_negotiation')

    async def cancel(self, raw):
        """Allow cancellation only for keys received from active owned backend sessions."""
        if len(raw) != 16 or raw[8:] not in self.server.cancel_keys:
            raise ProtocolError('cancel_identity')
        self.server.contexts.cancelled(raw[8:])
        await self.server.cancel_owned(raw[8:])

    async def relay(self):
        """Cancel both halves on any failure; admitted mutations are never retried."""
        tasks = [asyncio.create_task(self.frontend()), asyncio.create_task(self.backend())]
        try:
            ready = asyncio.create_task(asyncio.wait_for(self.ready_event.wait(), 15))
            initial, _ = await asyncio.wait([*tasks, ready], return_when=asyncio.FIRST_COMPLETED)
            if ready not in initial:
                ready.cancel()
                await asyncio.gather(ready, return_exceptions=True)
                for task in initial:
                    task.result()
                return
            ready.result()
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def frontend(self):
        """Admit exact SQL before forwarding Q/P; validate all remaining protocol transitions."""
        while True:
            kind, body = await read_frame(self.reader)
            if not self.authenticated:
                if kind != b'p' or len(body) > 65536:
                    raise ProtocolError('authentication_phase')
                self.server.record(self.tag, 'auth')
            else:
                await asyncio.wait_for(self.ready_event.wait(), 15)
                if self.lease_kind == 'context':
                    self.server.contexts.require_work()
                if self.context_protocol is not None:
                    self.context_protocol.frontend(kind, body)
                if kind in (b'Q', b'P'):
                    sql = self.state.sql_request(kind, body)
                    if self.lease_kind is None and is_context_setting(sql):
                        raise ProtocolError('context_setting_outside_lease')
                    decision = await self.server.admit(self.tag, sql)
                    self.state.accept_sql(kind, body, sql, decision)
                else:
                    self.state.control(kind, body)
                self.server.record(self.tag, kind.decode('ascii'))
            if self.authenticated and self.lease_kind == 'context':
                self.server.contexts.require_work()
            await send(self.backend_writer, packet(kind, body))
            if kind == b'X':
                return

    async def backend(self):
        """Enforce the parser's lexical assumptions and COPY phase before exposing backend replies."""
        while True:
            kind, body = await read_frame(self.backend_reader)
            if kind == b'R':
                if len(body) < 4:
                    raise ProtocolError('authentication_response')
                method = struct.unpack('!I', body[:4])[0]
                if method == 0:
                    self.authenticated = True
                elif method not in (10, 11, 12):
                    raise ProtocolError('unsupported_authentication')
            elif kind == b'S':
                self.parameter_status(body)
            elif kind == b'K':
                if len(body) != 8:
                    raise ProtocolError('backend_key')
                self.cancel_key = body
                self.server.cancel_keys.add(body)
                if self.lease_kind is not None:
                    self.server.contexts.keyed(self.lease_kind, body)
            elif kind == b'Z':
                if self.lexical != {'client_encoding': 'UTF8', 'standard_conforming_strings': 'on'}:
                    raise ProtocolError('unconfirmed_lexical_mode')
                initial = not self.state.initial_ready
                if initial and self.lease_kind is not None:
                    await self.server.contexts.bound(self.lease_kind)
                self.state.ready(body)
                self.ready_event.set()
            elif kind == b'G':
                self.state.copy_in = True
            elif kind == b'W':
                raise ProtocolError('copy_both_unsupported')
            if self.context_protocol is not None:
                self.context_protocol.backend(kind, body)
                if self.lease_kind == 'context' and self.context_protocol.failed:
                    self.server.contexts.poison('context')
                    if kind == b'E':
                        self.context_error_sent = True
                        await send(self.writer, packet(b'E', context_error(body)))
                        await self.context_error_ready()
                    raise ProtocolError('context_database_failure')
            if self.authenticated and self.lease_kind == 'context':
                self.server.contexts.require_work()
            await send(self.writer, packet(kind, body))

    async def context_error_ready(self):
        """Finish only an actual failed PG cycle so libpq retains its SQLSTATE.

        This forwards no row data or success result. EOF/fatal errors still fail
        closed; cleanup remains independently observed by the lease owner.
        """
        try:
            kind, body = await asyncio.wait_for(read_frame(self.backend_reader), 0.5)
        except (OSError, asyncio.IncompleteReadError, asyncio.TimeoutError):
            return
        if kind != b'Z' or body != b'E':
            raise ProtocolError('context_failure_completion')
        self.state.ready(body)
        self.context_protocol.backend(kind, body)
        await send(self.writer, packet(kind, body))

    def parameter_status(self, body):
        """Stop unexpected lexical-mode changes, independently of the SQL policy guard."""
        name, offset = cstring(body)
        value = complete_string(body[offset:])
        if name == b'client_encoding':
            if value != b'UTF8':
                raise ProtocolError('encoding_changed')
            self.lexical['client_encoding'] = 'UTF8'
        if name == b'standard_conforming_strings':
            if value != b'on':
                raise ProtocolError('string_mode_changed')
            self.lexical['standard_conforming_strings'] = 'on'

    async def close(self):
        """Retain context cancellation authority until independently observed cleanup."""
        if self.lease_kind is not None:
            task = asyncio.create_task(self.server.contexts.finish(self))
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
            await task
        else:
            await self.close_transports()
            if self.cancel_key is not None:
                self.server.cancel_keys.discard(self.cancel_key)

    async def close_transports(self):
        """Close owned streams without treating their EOF as database cleanup evidence."""
        for writer in (self.backend_writer, self.writer):
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), 2)
                except (OSError, asyncio.TimeoutError):
                    pass


class ProxyServer:
    """Bounded workspace-only proxy with non-sensitive per-client execution counters."""

    def __init__(self, backend, listen, status, gate=None, ready=None):
        self.backend, self.listen, self.status = Path(backend), Path(listen), Path(status)
        self.gate = gate if gate is not None else ParserGate()
        self.parser_slots = asyncio.Semaphore(2)
        self.active = 0
        self.handlers = set()
        self.cancel_keys = set()
        self.counters = {tag: Counter() for tag in sorted(TAGS | {'other'})}
        self.stopping = asyncio.Event()
        self.started = time.time()
        self.ready_path = Path(ready) if ready else None
        from .sql_image_config import workspace_root
        root = workspace_root()
        sources = {name:root/name for name in source_names()}
        self.loaded_inputs = {name:hashlib.sha256(path.read_bytes()).hexdigest()
                              for name,path in sources.items()}
        if isinstance(self.gate, ParserGate):
            # Bind the exact bytes read into the immutable snapshot, not a later lock read.
            self.loaded_inputs['config/sqlean-parser-lock.json'] = self.gate.info['configuration_sha256']
        self.contexts = ContextLeases(self)

    async def cancel_owned(self, key):
        """Forward only an owned secret-bound PostgreSQL cancellation protocol packet."""
        if len(key) != 8 or key not in self.cancel_keys:
            raise ProtocolError('cancel_identity')
        _, backend = await asyncio.wait_for(asyncio.open_unix_connection(str(self.backend)), 0.5)
        try:
            await asyncio.wait_for(send(backend, integer(16) + integer(80877102) + key), 0.5)
            self.record('other', 'cancel')
        finally:
            backend.close()
            await asyncio.wait_for(backend.wait_closed(), 0.5)

    def record(self, tag, key):
        """Record counts only; neither SQL, parameter values nor their hashes enter status output."""
        self.counters[tag][key] += 1

    async def admit(self, tag, sql):
        """Serialize bounded parser work and distinguish SQL rejection from protocol failure."""
        try:
            await asyncio.wait_for(self.parser_slots.acquire(), FRAME_SECONDS)
            try:
                if isinstance(self.gate, ParserGate):
                    cancelled = threading.Event()
                    work = asyncio.get_running_loop().run_in_executor(
                        None, lambda:self.gate.validate(sql, cancel=cancelled))
                    try:
                        decision = await asyncio.shield(work)
                    except asyncio.CancelledError:
                        cancelled.set()
                        # Keep the outer slot until the thread owns no child/fd reservation.
                        while not work.done():
                            try:
                                await asyncio.shield(work)
                            except asyncio.CancelledError:
                                # Repeated cancellation cannot release ownership early.
                                cancelled.set()
                            except Exception:
                                break
                        if not work.cancelled():
                            work.exception()  # Consume an expected denial after cancellation.
                        raise
                else:
                    decision = await asyncio.to_thread(self.gate.validate, sql)
            finally:
                self.parser_slots.release()
            self.record(tag, 'accepted')
            return decision
        except Exception as error:
            self.record(tag, 'rejected')
            if isinstance(error, SQLGuardError):
                category = error.category
                if category in {'policyDenied','parserFailure','infrastructureFailure'}:
                    self.record(tag, 'parser_category_' + category)
            reason = str(error) if isinstance(error, SQLGuardError) else ''
            code = reason.replace(' ', '_') if reason in GATE_REASONS else 'unexpected_failure'
            self.record(tag, 'parser_reason_' + code)
            raise ProtocolError('parser_denied') from None

    async def connected(self, reader, writer):
        """Reserve four handlers beyond normal capacity for bounded startup and cancellation."""
        current = asyncio.current_task()
        session = Session(self, reader, writer)
        if len(self.handlers) >= 21:
            writer.close()
            await writer.wait_closed()
            return
        self.handlers.add(current)
        try:
            await session.start()
        except (ValueError, UnicodeError, asyncio.TimeoutError, RuntimeError):
            if session.context_protocol is not None:
                session.context_protocol.mark_failed()
            self.record(session.tag, 'protocol_error')
            try:
                if not session.context_error_sent:
                    await send(writer, packet(b'E', b'SERROR\0VERROR\0C42601\0MSQLean query gate denied this session\0\0'))
            except (OSError, asyncio.TimeoutError):
                pass
        except (OSError, asyncio.IncompleteReadError):
            if session.context_protocol is not None:
                session.context_protocol.mark_failed()
            self.record(session.tag, 'disconnected')
        finally:
            try:
                if session.context_protocol is not None and not session.context_protocol.terminated_successfully:
                    session.context_protocol.mark_failed()
                await session.close()
            finally:
                self.handlers.discard(current)
                self.write_status()

    def write_status(self):
        """Atomically publish private aggregate status without database credentials or query text."""
        self.status.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        import psycopg
        value = {'pid': os.getpid(), 'started': self.started, 'active': self.active,
                 'parser': self.gate.info, 'clients': self.counters,
                 'loaded_inputs': self.loaded_inputs, 'context': self.contexts.status(),
                 'runtime': {'executable':sys.executable, 'psycopg':psycopg.__version__,
                             'libpq':psycopg.pq.version()}}
        path = self.status.with_suffix('.new')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, sort_keys=True)
            output.write('\n')
        path.replace(self.status)

    async def publish_status(self):
        """Refresh active-session counters periodically without creating per-query log records."""
        while not self.stopping.is_set():
            self.write_status()
            try:
                await asyncio.wait_for(self.stopping.wait(), 0.25)
            except asyncio.TimeoutError:
                pass

    async def run(self):
        """Own one private socket and remove it on graceful stop; never unlink an existing listener."""
        self.listen.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.listen.parent.chmod(0o700)
        if self.listen.exists() or self.listen.is_symlink():
            raise RuntimeError('proxy_socket_already_exists')
        server = await asyncio.start_unix_server(self.connected, path=str(self.listen), limit=65536)
        self.listen.chmod(0o600)
        await self.contexts.start()
        self.write_status()
        if self.ready_path:
            fd = os.open(self.ready_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as output:
                json.dump({'pid': os.getpid(), 'started': self.started, 'listen': str(self.listen)}, output)
        publisher = asyncio.create_task(self.publish_status())
        try:
            await self.stopping.wait()
        finally:
            server.close()
            await self.close_sessions()
            await server.wait_closed()
            publisher.cancel()
            await asyncio.gather(publisher, return_exceptions=True)
            closer = getattr(self.gate, 'close', None)
            if closer is not None:
                await asyncio.to_thread(closer)
            self.listen.unlink(missing_ok=True)
            if self.ready_path:
                self.ready_path.unlink(missing_ok=True)
            self.write_status()

    async def close_sessions(self):
        """Retire context clients before the persistent observer and Python3.12 server wait."""
        await self.contexts.stop_admission()
        observer = self.contexts.sessions.get('observer')
        observer_task = observer.owner_task if observer is not None else None
        clients = [task for task in tuple(self.handlers) if task is not observer_task]
        for task in clients:
            task.cancel()
        await asyncio.gather(*clients, return_exceptions=True)
        await self.contexts.stop()
        remaining = tuple(self.handlers)
        for task in remaining:
            if task is not observer_task:
                task.cancel()
        await asyncio.gather(*remaining, return_exceptions=True)


async def serve(args):
    """Install shutdown handlers only for this owned proxy process."""
    proxy = ProxyServer(args.backend, args.listen, args.status, ready=args.ready)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, proxy.stopping.set)
    await proxy.run()


def main():
    """Start an explicitly configured local proxy, reporting sanitized startup failure only."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', required=True, type=Path)
    parser.add_argument('--listen', required=True, type=Path)
    parser.add_argument('--status', required=True, type=Path)
    parser.add_argument('--ready', type=Path)
    args = parser.parse_args()
    try:
        asyncio.run(serve(args))
        return 0
    except Exception:
        print('SQLean proxy unavailable', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
