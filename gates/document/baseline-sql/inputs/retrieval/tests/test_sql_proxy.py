"""Independent finite wire checks for the SQLean PostgreSQL admission proxy.

Run with PYTHONPATH=retrieval python -m unittest discover -s retrieval/tests
-p test_sql_proxy.py. These checks require the built, pinned parser; a missing
parser is a failure, never a skipped admission check. Backend fixtures execute no
SQL and retain only authored test strings in temporary process memory.
"""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import queue
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def packet(kind, body=b''):
    return kind + struct.pack('!I', len(body) + 4) + body


def cstring(value):
    return value.encode('utf-8') + b'\0'


def startup(**overrides):
    values = {'user': 'authored_test', 'database': 'authored_test',
              'client_encoding': 'UTF8', 'application_name': 'allow-tests'}
    values.update(overrides)
    body = struct.pack('!I', 196608)
    body += b''.join(cstring(k) + cstring(v) for k, v in values.items()) + b'\0'
    return struct.pack('!I', len(body) + 4) + body


def exact(stream, amount):
    data = bytearray()
    while len(data) < amount:
        chunk = stream.recv(amount - len(data))
        if not chunk:
            raise EOFError('wire peer closed')
        data.extend(chunk)
    return bytes(data)


def receive(stream):
    kind = exact(stream, 1)
    length = struct.unpack('!I', exact(stream, 4))[0]
    if not 4 <= length <= 16 * 1024 * 1024:
        raise AssertionError('invalid response frame length')
    return kind, exact(stream, length - 4)


def until(stream, end=b'Z'):
    frames = []
    while True:
        frame = receive(stream)
        frames.append(frame)
        if frame[0] == end:
            return frames


def parse(sql, name=''):
    return packet(b'P', cstring(name) + cstring(sql) + struct.pack('!H', 0))


def bind(portal='', statement='', value=None, binary=False):
    body = cstring(portal) + cstring(statement)
    if value is None:
        body += struct.pack('!HHH', 0, 0, 0)
    else:
        body += struct.pack('!HHH', 1, int(binary), 1)
        body += struct.pack('!i', len(value)) + value + struct.pack('!H', 0)
    return packet(b'B', body)


def execute(name=''):
    return packet(b'E', cstring(name) + struct.pack('!I', 0))


class FrameDeadlineTests(unittest.IsolatedAsyncioTestCase):
    """Accelerated read deadlines distinguish valid silence from partial frames."""

    def short_deadline(self, module):
        original = module.read_exact

        async def bounded(reader, amount, timeout=None):
            return await original(reader, amount, timeout=.03)

        return patch.object(module, 'read_exact', bounded)

    async def test_idle_before_first_byte_outlasts_frame_deadline(self):
        from allow_retrieval import sql_proxy
        reader = asyncio.StreamReader()
        with self.short_deadline(sql_proxy):
            pending = asyncio.create_task(sql_proxy.read_frame(reader))
            try:
                await asyncio.sleep(.09)
                self.assertFalse(pending.done(), 'valid inter-frame silence timed out')
                reader.feed_data(packet(b'Q', b'SELECT 1\0'))
                self.assertEqual(await asyncio.wait_for(pending, .5), (b'Q', b'SELECT 1\0'))
            finally:
                if not pending.done():
                    pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)

    async def test_partial_header_stall_receives_frame_deadline(self):
        from allow_retrieval import sql_proxy
        reader = asyncio.StreamReader()
        reader.feed_data(b'Q\0')
        with self.short_deadline(sql_proxy):
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(sql_proxy.read_frame(reader), .5)

    async def test_partial_body_stall_receives_frame_deadline(self):
        from allow_retrieval import sql_proxy
        reader = asyncio.StreamReader()
        reader.feed_data(b'Q' + struct.pack('!I', 12) + b'SE')
        with self.short_deadline(sql_proxy):
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(sql_proxy.read_frame(reader), .5)


class Backend:
    """Small wire peer independent of the proxy's parsing and state helpers."""
    def __init__(self, path):
        self.path = str(path)
        self.frames = queue.Queue()
        self.executions = queue.Queue()
        self.errors = queue.Queue()
        self.encoding = b'UTF8'
        self.strings = b'on'
        self.ready_delay = 0
        self.hold_ready = False
        self.pending_ready = queue.Queue()
        self.stop = threading.Event()
        self.connections = []
        self.listener = socket.socket(socket.AF_UNIX)
        self.listener.bind(self.path)
        self.listener.listen(32)
        self.listener.settimeout(.1)
        self.thread = threading.Thread(target=self._accept, daemon=True)
        self.thread.start()

    def _accept(self):
        while not self.stop.is_set():
            try:
                stream, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.connections.append(stream)
            threading.Thread(target=self._session, args=(stream,), daemon=True).start()

    def _session(self, stream):
        try:
            length = struct.unpack('!I', exact(stream, 4))[0]
            hello = exact(stream, length - 4)
            if len(hello) == 12 and hello[:4] == struct.pack('!I', 80877102):
                self.frames.put((b'cancel', hello))
                return
            stream.sendall(packet(b'R', struct.pack('!I', 0)) +
                           packet(b'S', b'client_encoding\0' + self.encoding + b'\0') +
                           packet(b'S', b'standard_conforming_strings\0' + self.strings + b'\0') +
                           packet(b'K', struct.pack('!II', 1234, 5678)))
            if self.ready_delay:
                self.stop.wait(self.ready_delay)
            stream.sendall(packet(b'Z', b'I'))
            statements, portals = {}, {}
            transaction = b'I'
            copy_active = False
            failed_pipeline = False
            def ready():
                response = packet(b'Z', transaction)
                if self.hold_ready:
                    self.pending_ready.put((stream, response))
                else:
                    stream.sendall(response)
            while not self.stop.is_set():
                kind, body = receive(stream)
                self.frames.put((kind, body))
                if failed_pipeline:
                    if kind == b'S':
                        failed_pipeline = False
                        ready()
                    continue
                if kind == b'Q':
                    statements.pop('', None)
                    portals.pop('', None)
                    sql = body[:-1].decode()
                    native = re.match(r'(?is)^\s*PREPARE\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s+AS\s+(.*)', sql)
                    invoked = re.match(r'(?is)^\s*EXECUTE\s+([A-Za-z_][A-Za-z0-9_]*)', sql)
                    if native:
                        statements[native[1].lower()] = native[2]
                    elif invoked:
                        self.executions.put(statements[invoked[1].lower()])
                    if sql.startswith('COPY authored_copy FROM STDIN'):
                        copy_active = True
                        stream.sendall(packet(b'G', struct.pack('!BHH', 0, 1, 0)))
                        continue
                    if sql.strip().upper().startswith('BEGIN'):
                        transaction = b'T'
                    elif sql.strip().upper().startswith(('COMMIT', 'ROLLBACK')):
                        transaction = b'I'
                        portals.clear()
                    stream.sendall(packet(b'C', b'SELECT 1\0'))
                    ready()
                elif kind == b'P':
                    name, sql, _ = body.split(b'\0', 2)
                    if b'authored_missing_column' in sql:
                        failed_pipeline = True
                        stream.sendall(packet(b'E', b'SERROR\0C42703\0Mauthored backend error\0\0'))
                        continue
                    statements[name.decode()] = sql.decode()
                    stream.sendall(packet(b'1'))
                elif kind == b'B':
                    name, statement, _ = body.split(b'\0', 2)
                    portals[name.decode()] = statements[statement.decode()]
                    stream.sendall(packet(b'2'))
                elif kind == b'E':
                    name = body.split(b'\0', 1)[0].decode()
                    self.executions.put(portals[name])
                    stream.sendall(packet(b'C', b'SELECT 1\0'))
                elif kind == b'S':
                    if transaction == b'I':
                        portals.clear()
                    ready()
                elif kind == b'C':
                    name = body[1:-1].decode()
                    (statements if body[:1] == b'S' else portals).pop(name, None)
                    stream.sendall(packet(b'3'))
                elif kind == b'X':
                    return
                elif kind == b'D':
                    stream.sendall(packet(b'n'))
                elif kind == b'd' and copy_active:
                    pass
                elif kind == b'c' and copy_active:
                    copy_active = False
                    stream.sendall(packet(b'C', b'COPY 1\0'))
                    ready()
                elif kind == b'H':
                    pass
                else:
                    # An unexpected frontend frame is itself test evidence.
                    return
        except (EOFError, ConnectionError, OSError):
            pass
        except Exception as error:
            self.errors.put(error)
        finally:
            stream.close()

    def drain(self):
        frames = []
        while True:
            try:
                frames.append(self.frames.get_nowait())
            except queue.Empty:
                return frames

    def release_ready(self, prefix=b''):
        stream, response = self.pending_ready.get(timeout=2)
        stream.sendall(prefix + response)

    def discard_pending(self):
        self.hold_ready = False
        while not self.pending_ready.empty():
            self.pending_ready.get_nowait()

    def close(self):
        self.stop.set()
        self.listener.close()
        for stream in self.connections:
            with contextlib.suppress(OSError):
                stream.shutdown(socket.SHUT_RDWR)
                stream.close()
        self.thread.join(timeout=2)


class HandshakeDeadlineTests(unittest.IsolatedAsyncioTestCase):
    """One accelerated startup deadline spans reads and backend authentication."""

    async def asyncSetUp(self):
        from allow_retrieval import sql_proxy

        class FixtureGate:
            info = {'test_fixture': 'handshake transport only'}

            def validate(self, source):
                pass

        self.temporary = tempfile.TemporaryDirectory(prefix='allow-handshake-')
        self.directory = Path(self.temporary.name)
        self.backend = Backend(self.directory / 'backend.sock')
        self.writers = []
        self.deadline_patch = patch.object(sql_proxy, 'HANDSHAKE_SECONDS', .1)
        self.deadline_patch.start()
        self.path = self.directory / 'proxy.sock'
        self.server = sql_proxy.ProxyServer(self.backend.path, self.path,
                                            self.directory / 'status.json', gate=FixtureGate())
        self.running = asyncio.create_task(self.server.run())
        deadline = time.monotonic() + 2
        while not self.path.exists():
            if self.running.done():
                await self.running
            self.assertLess(time.monotonic(), deadline, 'handshake fixture failed to start')
            await asyncio.sleep(.005)

    async def asyncTearDown(self):
        try:
            for writer in self.writers:
                writer.close()
                with contextlib.suppress(OSError):
                    await writer.wait_closed()
            self.server.stopping.set()
            await asyncio.wait_for(self.running, 2)
        finally:
            self.deadline_patch.stop()
            await asyncio.to_thread(self.backend.close)
            self.temporary.cleanup()

    async def open(self):
        reader, writer = await asyncio.open_unix_connection(str(self.path))
        self.writers.append(writer)

        async def close():
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

        self.addAsyncCleanup(close)
        return reader, writer

    async def response(self, reader):
        header = await asyncio.wait_for(reader.readexactly(5), .5)
        length = struct.unpack('!I', header[1:])[0]
        self.assertGreaterEqual(length, 4)
        self.assertLessEqual(length, 16 * 1024 * 1024)
        body = await asyncio.wait_for(reader.readexactly(length - 4), .5)
        return header[:1], body

    async def ready(self, reader):
        while True:
            frame = await self.response(reader)
            if frame[0] == b'Z':
                self.assertEqual(frame[1], b'I')
                return

    async def test_fragmented_startup_cannot_renew_overall_deadline(self):
        reader, writer = await self.open()
        authored = startup()
        started = time.monotonic()
        writer.write(authored[:2])
        await writer.drain()
        await asyncio.sleep(.04)
        writer.write(authored[2:4])
        await writer.drain()
        await asyncio.sleep(.04)
        writer.write(authored[4:7])
        await writer.drain()
        await asyncio.wait_for(reader.read(), .3)
        self.assertLess(time.monotonic() - started, .35)
        self.assertEqual(self.server.counters['other']['handshake_timeout'], 1)
        self.assertEqual(self.backend.drain(), [])

    async def test_backend_not_ready_cannot_outlast_overall_deadline(self):
        self.backend.ready_delay = .3
        reader, writer = await self.open()
        writer.write(startup())
        await writer.drain()
        response = await asyncio.wait_for(reader.read(), .3)
        self.assertNotIn(packet(b'Z', b'I'), response)
        self.assertEqual(self.server.counters['allow-tests']['handshake_timeout'], 1)

    async def test_ready_session_remains_usable_beyond_handshake_deadline(self):
        reader, writer = await self.open()
        writer.write(startup())
        await writer.drain()
        await self.ready(reader)
        await asyncio.sleep(.16)
        writer.write(packet(b'Q', cstring('SELECT 1;')))
        await writer.drain()
        self.assertEqual((await self.response(reader))[0], b'C')
        await self.ready(reader)
        self.assertEqual(self.server.counters['allow-tests']['handshake_timeout'], 0)
        self.assertEqual(self.backend.frames.get(timeout=1), (b'Q', b'SELECT 1;\0'))


class WireProxyTests(unittest.TestCase):
    """Each test owns its socket pair and proxy; no production database access."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-wire-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.backend = Backend(self.directory / 'backend.sock')
        self.addCleanup(self.backend.close)
        self.path = self.directory / 'proxy.sock'
        self.status = self.directory / 'status.json'
        environment = os.environ.copy()
        environment['PYTHONPATH'] = str(ROOT / 'retrieval')
        self.process = subprocess.Popen(
            [sys.executable, '-m', 'allow_retrieval.sql_proxy',
             '--backend', self.backend.path, '--listen', str(self.path),
             '--status', str(self.status)],
            env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.addCleanup(self._stop_proxy)
        deadline = time.monotonic() + 15
        while not self.path.exists():
            if self.process.poll() is not None:
                self.fail('proxy failed to start: ' + self.process.stderr.read().decode()[-1500:])
            if time.monotonic() > deadline:
                self.fail('proxy startup deadline exceeded')
            time.sleep(.01)

    def _stop_proxy(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process.stderr.close()

    def tearDown(self):
        self.assertTrue(self.backend.errors.empty(), 'independent backend fixture failed')

    def connect(self, hello=None):
        stream = socket.socket(socket.AF_UNIX)
        stream.settimeout(8)
        self.addCleanup(stream.close)
        stream.connect(str(self.path))
        stream.sendall(hello or startup())
        frames = until(stream)
        self.assertEqual(frames[-1], (b'Z', b'I'))
        self.backend.drain()
        return stream

    def denied(self, stream):
        """A denial may send ErrorResponse, then must close the session."""
        errors = []
        try:
            while True:
                kind, body = receive(stream)
                self.assertEqual(kind, b'E', 'denied session returned a success frame')
                errors.append(body)
        except (EOFError, ConnectionResetError, BrokenPipeError):
            return errors

    def sync(self, stream):
        stream.sendall(packet(b'S'))
        return until(stream)

    def prepared_portal(self, stream):
        stream.sendall(packet(b'Q', cstring('BEGIN')))
        until(stream)
        stream.sendall(parse('SELECT 1;', 'base'))
        self.assertEqual(receive(stream)[0], b'1')
        stream.sendall(bind('p', 'base'))
        self.assertEqual(receive(stream)[0], b'2')
        self.sync(stream)
        self.backend.drain()

    def test_query_and_numbered_parse_admission(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('SELECT 1;')))
        until(stream)
        self.assertEqual(self.backend.frames.get(timeout=2), (b'Q', b'SELECT 1;\0'))
        stream.sendall(parse('SELECT $1::text;', 'numbered'))
        self.assertEqual(receive(stream)[0], b'1')
        self.assertEqual(self.backend.frames.get(timeout=2)[0], b'P')

    def test_invalid_query_never_reaches_backend(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('THIS IS NOT VALID SQL !')))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_invalid_parse_never_reaches_backend(self):
        stream = self.connect()
        stream.sendall(parse('SELECT FROM WHERE;', 'bad'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_injected_parser_failure_has_no_direct_backend_fallback(self):
        self._stop_proxy()
        script = '''import asyncio,sys
from allow_retrieval.sql_proxy import ProxyServer
class FailedGate:
    info = {"test_fixture": "deliberate unavailable parser"}
    def validate(self, sql):
        raise RuntimeError("authored parser failure")
asyncio.run(ProxyServer(*sys.argv[1:], gate=FailedGate()).run())
'''
        environment = os.environ.copy()
        environment['PYTHONPATH'] = str(ROOT / 'retrieval')
        self.process = subprocess.Popen(
            [sys.executable, '-c', script, self.backend.path, str(self.path), str(self.status)],
            env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 5
        while not self.path.exists():
            if self.process.poll() is not None or time.monotonic() > deadline:
                self.fail('isolated injected-gate proxy did not start')
            time.sleep(.01)
        for authored in (packet(b'Q', cstring('SELECT 1;')), parse('SELECT 1;', 'safe')):
            stream = self.connect()
            stream.sendall(authored)
            errors = self.denied(stream)
            self.assertTrue(errors)
            self.assertNotIn(b'authored parser failure', b''.join(errors))
            self.assertEqual(self.backend.drain(), [])

    def test_opaque_and_nested_execute_denied(self):
        for sql in ('DO $$ BEGIN invalid body; END $$;',
                    'CREATE FUNCTION f() RETURNS void LANGUAGE SQL AS $$ SELECT 1 $$;',
                    'EXPLAIN EXECUTE hidden;', 'CREATE TABLE t AS EXECUTE hidden;',
                    "PREPARE TRANSACTION 'authored';"):
            with self.subTest(sql=sql):
                stream = self.connect()
                stream.sendall(packet(b'Q', cstring(sql)))
                self.denied(stream)
                self.assertEqual(self.backend.drain(), [])

    def test_bind_preserves_sql_looking_text_and_binary(self):
        for binary, value in ((False, b"'); DROP TABLE imaginary; --"),
                              (True, b'\0\xffSET client_encoding=SQL_ASCII;\0')):
            with self.subTest(binary=binary):
                stream = self.connect()
                stream.sendall(parse('SELECT $1::bytea;' if binary else 'SELECT $1::text;'))
                self.assertEqual(receive(stream)[0], b'1')
                sent = bind(value=value, binary=binary)
                stream.sendall(sent)
                self.assertEqual(receive(stream)[0], b'2')
                frames = self.backend.drain()
                self.assertIn((b'B', sent[5:]), frames)

    def test_implicit_transaction_control_admitted(self):
        stream = self.connect()
        for sql in ('BEGIN', 'SELECT 1', 'COMMIT', 'BEGIN', 'ROLLBACK'):
            stream.sendall(packet(b'Q', cstring(sql)))
            until(stream)
        self.assertEqual([b[:-1].decode() for k, b in self.backend.drain() if k == b'Q'],
                         ['BEGIN', 'SELECT 1', 'COMMIT', 'BEGIN', 'ROLLBACK'])

    def test_native_prepare_execute_and_cache_cannot_prepare_another_session(self):
        stream = self.connect()
        source = 'PREPARE MiXeD AS SELECT 71;'
        stream.sendall(packet(b'Q', cstring(source)))
        until(stream)
        stream.sendall(packet(b'Q', cstring('EXECUTE mixed;')))
        until(stream)
        self.assertEqual(self.backend.executions.get(timeout=2), 'SELECT 71;')
        fresh = self.connect()
        fresh.sendall(packet(b'Q', cstring('EXECUTE mixed;')))
        self.denied(fresh)
        self.assertEqual(self.backend.drain(), [])

    def test_native_unknown_target_denied(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('EXECUTE not_prepared_here;')))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_native_and_protocol_share_accepted_namespace_both_directions(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('PREPARE native AS SELECT 81;')))
        until(stream)
        stream.sendall(bind('from_native', 'native'))
        self.assertEqual(receive(stream)[0], b'2')
        stream.sendall(execute('from_native'))
        self.assertEqual(receive(stream)[0], b'C')
        self.assertEqual(self.backend.executions.get(timeout=2), 'SELECT 81;')
        self.sync(stream)
        stream.sendall(parse('SELECT 82;', 'protocol'))
        self.assertEqual(receive(stream)[0], b'1')
        self.sync(stream)
        stream.sendall(packet(b'Q', cstring('EXECUTE protocol;')))
        until(stream)
        self.assertEqual(self.backend.executions.get(timeout=2), 'SELECT 82;')

    def test_native_classifier_and_names_are_conservative(self):
        cases = ('PREPARE "quoted" AS SELECT 1;',
                 'PREPARE ' + 'a' * 64 + ' AS SELECT 1;',
                 'PREPARE s AS SELECT 1; SELECT 2;',
                 'EXECUTE s; EXECUTE s;', 'EXPLAIN EXECUTE s;',
                 'CREATE TEMP TABLE t AS EXECUTE s;',
                 "PREPARE s AS SELECT set_config('client_encoding','SQL_ASCII',false);",
                 "EXECUTE s(set_config('standard_conforming_strings','off',false));")
        for source in cases:
            with self.subTest(source=source):
                stream = self.connect()
                stream.sendall(packet(b'Q', cstring(source)))
                self.denied(stream)
                self.assertEqual(self.backend.drain(), [])

    def test_native_prepare_counts_toward_shared_object_capacity(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('PREPARE native AS SELECT 1;')))
        until(stream)
        for index in range(255):
            stream.sendall(parse('SELECT 1;', 's' + str(index)))
            self.assertEqual(receive(stream)[0], b'1')
            self.sync(stream)
        self.backend.drain()
        stream.sendall(packet(b'Q', cstring('PREPARE overflow AS SELECT 1;')))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_protocol_name_lengths_and_prefix_collisions_fail_closed(self):
        prefix = 's' * 63
        stream = self.connect()
        stream.sendall(parse('SELECT 1;', prefix))
        self.assertEqual(receive(stream)[0], b'1')
        self.sync(stream)
        stream.sendall(bind('p' * 63, prefix))
        self.assertEqual(receive(stream)[0], b'2')
        stream.sendall(execute('p' * 63))
        self.assertEqual(receive(stream)[0], b'C')
        self.sync(stream)
        for authored in (parse('SELECT 2;', prefix + 'x'), bind('ok', prefix + 'x'),
                         bind('p' * 64, prefix), execute('p' * 64),
                         packet(b'C', b'S' + cstring(prefix + 'x')),
                         packet(b'D', b'P' + cstring('p' * 64)),
                         parse('SELECT 2;', '\u03bb' * 32)):
            with self.subTest(frame=authored[:25]):
                candidate = self.connect()
                candidate.sendall(packet(b'Q', cstring('BEGIN')))
                until(candidate)
                candidate.sendall(parse('SELECT 1;', prefix))
                self.assertEqual(receive(candidate)[0], b'1')
                self.sync(candidate)
                candidate.sendall(bind('p' * 63, prefix))
                self.assertEqual(receive(candidate)[0], b'2')
                self.sync(candidate)
                self.backend.drain()
                candidate.sendall(authored)
                self.denied(candidate)
                self.assertEqual(self.backend.drain(), [])

    def test_each_effect_blocks_both_new_source_message_kinds(self):
        for effect in (b'Q', b'P', b'B', b'D', b'E', b'C', b'S'):
            for next_kind in (b'Q', b'P'):
                with self.subTest(effect=effect, next_kind=next_kind):
                    self.backend.discard_pending()
                    stream = self.connect()
                    self.prepared_portal(stream)
                    self.backend.hold_ready = effect in (b'Q', b'S')
                    authored = {b'Q': packet(b'Q', cstring('SELECT 41;')),
                                b'P': parse('SELECT 42;', 'new'),
                                b'B': bind('next', 'base'),
                                b'D': packet(b'D', b'Sbase\0'),
                                b'E': execute('p'), b'C': packet(b'C', b'Sbase\0'),
                                b'S': packet(b'S')}[effect]
                    stream.sendall(authored)
                    if effect != b'S':
                        expected = {b'Q': b'C', b'P': b'1', b'B': b'2', b'D': b'n', b'E': b'C', b'C': b'3'}
                        self.assertEqual(receive(stream)[0], expected[effect])
                    else:
                        self.assertEqual(self.backend.frames.get(timeout=2)[0], b'S')
                    self.backend.drain()
                    forbidden = (packet(b'Q', cstring('SELECT 99;')) if next_kind == b'Q'
                                 else parse('SELECT 99;', 'forbidden'))
                    stream.sendall(forbidden)
                    self.denied(stream)
                    self.assertEqual(self.backend.drain(), [])

    def test_old_ready_does_not_release_newer_execute_effect(self):
        stream = self.connect()
        self.prepared_portal(stream)
        self.backend.hold_ready = True
        stream.sendall(execute('p'))
        self.assertEqual(receive(stream)[0], b'C')
        stream.sendall(packet(b'S') + execute('p'))
        self.assertEqual(receive(stream)[0], b'C')
        self.backend.release_ready()
        self.assertEqual(receive(stream), (b'Z', b'T'))
        self.backend.drain()
        stream.sendall(parse('SELECT 99;', 'forbidden'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_matching_ready_releases_completed_effect_and_copy_has_no_orphan(self):
        stream = self.connect()
        self.prepared_portal(stream)
        stream.sendall(packet(b'D', b'Sbase\0') + execute('p') + packet(b'S'))
        self.assertEqual(receive(stream)[0], b'n')
        self.assertEqual(receive(stream)[0], b'C')
        until(stream)
        stream.sendall(parse('SELECT 53;', 'later'))
        self.assertEqual(receive(stream)[0], b'1')
        self.sync(stream)
        stream.sendall(packet(b'Q', cstring('COPY authored_copy FROM STDIN;')))
        self.assertEqual(receive(stream)[0], b'G')
        stream.sendall(packet(b'd', b'authored row\n') + packet(b'c'))
        until(stream)
        stream.sendall(packet(b'Q', cstring('SELECT 54;')))
        until(stream)
        self.assertIn((b'Q', b'SELECT 54;\0'), self.backend.drain())

    def test_unsafe_fragmented_status_precedes_barrier_release(self):
        stream = self.connect()
        self.backend.hold_ready = True
        stream.sendall(packet(b'Q', cstring('SELECT 1;')))
        self.assertEqual(receive(stream)[0], b'C')
        backend, ready = self.backend.pending_ready.get(timeout=2)
        authored = packet(b'S', b'standard_conforming_strings\0off\0')
        backend.sendall(authored[:3])
        time.sleep(.02)
        backend.sendall(authored[3:] + ready)
        self.denied(stream)
        self.backend.drain()
        with self.assertRaises((BrokenPipeError, ConnectionResetError, OSError)):
            for _ in range(3):
                stream.sendall(parse('SELECT 99;', 'late'))
                if stream.recv(1) == b'':
                    raise BrokenPipeError()
        self.assertEqual(self.backend.drain(), [])

    def test_unsolicited_ready_after_startup_fails_closed(self):
        for body in (b'I', b'', b'IT', b'?'):
            with self.subTest(body=body):
                stream = self.connect()
                self.backend.connections[-1].sendall(packet(b'Z', body))
                self.denied(stream)
                self.assertEqual(self.backend.drain(), [])

    def test_portal_snapshots_unnamed_statement_before_replacement(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('BEGIN')))
        until(stream)
        stream.sendall(parse('SELECT 11;'))
        self.assertEqual(receive(stream)[0], b'1')
        stream.sendall(bind('saved'))
        self.assertEqual(receive(stream)[0], b'2')
        self.sync(stream)
        stream.sendall(parse('SELECT 22;'))
        self.assertEqual(receive(stream)[0], b'1')
        stream.sendall(execute('saved'))
        self.assertEqual(receive(stream)[0], b'C')
        self.assertEqual(self.backend.executions.get(timeout=2), 'SELECT 11;')

    def test_simple_query_invalidates_unnamed_statement(self):
        stream = self.connect()
        stream.sendall(parse('SELECT 1;'))
        receive(stream)
        self.sync(stream)
        stream.sendall(packet(b'Q', cstring('SELECT 2;')))
        until(stream)
        self.backend.drain()
        stream.sendall(bind())
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_execute_requires_connection_local_portal(self):
        stream = self.connect()
        stream.sendall(execute('missing'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_idle_transaction_end_invalidates_named_portal(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('BEGIN')))
        until(stream)
        stream.sendall(parse('SELECT 1;', 'statement'))
        receive(stream)
        stream.sendall(bind('named', 'statement'))
        receive(stream)
        self.sync(stream)
        stream.sendall(packet(b'Q', cstring('COMMIT')))
        until(stream)
        self.backend.drain()
        stream.sendall(execute('named'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_close_statement_invalidates_dependent_portal(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('BEGIN')))
        until(stream)
        stream.sendall(parse('SELECT 1;', 'source'))
        receive(stream)
        stream.sendall(bind('dependent', 'source'))
        receive(stream)
        stream.sendall(packet(b'C', b'Ssource\0'))
        self.assertEqual(receive(stream)[0], b'3')
        self.backend.drain()
        stream.sendall(execute('dependent'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_prepared_object_capacity_fails_before_forwarding_overflow(self):
        stream = self.connect()
        for index in range(256):
            stream.sendall(parse('SELECT 1;', 's' + str(index)))
            self.assertEqual(receive(stream)[0], b'1')
            self.sync(stream)
        self.backend.drain()
        stream.sendall(parse('SELECT 1;', 'overflow'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_fragmented_query_preserved(self):
        stream = self.connect()
        authored = packet(b'Q', cstring('SELECT\n\n1;'))
        for byte in authored:
            stream.sendall(bytes([byte]))
        until(stream)
        self.assertEqual(self.backend.frames.get(timeout=2), (b'Q', authored[5:]))

    def test_invalid_wire_frames_fail_closed(self):
        cases = (packet(b'F', b'\0' * 12), packet(b'?', b''),
                 b'Q' + struct.pack('!I', 8388609),
                 b'Q' + struct.pack('!I', 3),
                 packet(b'Q', b'SELECT \xff;\0'),
                 packet(b'Q', b'SELECT 1\0SELECT 2\0'),
                 packet(b'P', b'bad\0SELECT 1\0\0\1'))
        for authored in cases:
            with self.subTest(frame=authored[:20]):
                stream = self.connect()
                stream.sendall(authored)
                self.denied(stream)
                self.assertEqual(self.backend.drain(), [])

    def test_unsafe_mode_change_stops_pipeline_before_forwarding(self):
        cases = ('SET standard_conforming_strings=off;',
                 'SET client_encoding=SQL_ASCII;', 'RESET ALL;',
                 "SELECT set_config('standard_conforming_strings','off',false);",
                 "SELECT pg_catalog.set_config($1,$2,false);",
                 'ALTER ROLE authored_test SET standard_conforming_strings=off;')
        for sql in cases:
            with self.subTest(sql=sql):
                stream = self.connect()
                stream.sendall(packet(b'Q', cstring(sql)) + packet(b'Q', cstring('SELECT 99;')))
                self.denied(stream)
                self.assertEqual(self.backend.drain(), [])

    def test_cancel_packet_routes_without_sql_admission(self):
        self.connect()  # Establish the active BackendKeyData authority first.
        stream = socket.socket(socket.AF_UNIX)
        stream.settimeout(3)
        self.addCleanup(stream.close)
        stream.connect(str(self.path))
        body = struct.pack('!III', 80877102, 1234, 5678)
        stream.sendall(struct.pack('!I', 16) + body)
        self.assertEqual(self.backend.frames.get(timeout=3), (b'cancel', body))
        self.assertEqual(stream.recv(1), b'')

    def test_twenty_sessions_reject_overflow_and_preserve_cancel_capacity(self):
        sessions = [self.connect() for _ in range(20)]
        self.assertEqual(len(sessions), 20)
        overflow = socket.socket(socket.AF_UNIX)
        self.addCleanup(overflow.close)
        overflow.settimeout(5)
        overflow.connect(str(self.path))
        overflow.sendall(startup())
        self.denied(overflow)
        cancellation = socket.socket(socket.AF_UNIX)
        self.addCleanup(cancellation.close)
        cancellation.settimeout(5)
        cancellation.connect(str(self.path))
        body = struct.pack('!III', 80877102, 1234, 5678)
        cancellation.sendall(struct.pack('!I', 16) + body)
        self.assertEqual(self.backend.frames.get(timeout=3), (b'cancel', body))
        self.assertEqual(cancellation.recv(1), b'')

    def test_copy_data_preserved_only_during_server_copy_stage(self):
        stream = self.connect()
        stream.sendall(packet(b'Q', cstring('COPY authored_copy FROM STDIN;')))
        self.assertEqual(receive(stream)[0], b'G')
        authored = b"SELECT set_config('client_encoding','SQL_ASCII',false);\n\xff\0"
        stream.sendall(packet(b'd', authored) + packet(b'c'))
        until(stream)
        self.assertIn((b'd', authored), self.backend.drain())
        stream.sendall(packet(b'd', b'outside COPY'))
        self.denied(stream)
        self.assertEqual(self.backend.drain(), [])

    def test_startup_unsafe_encoding_denied(self):
        for options in ({'client_encoding': 'SQL_ASCII'},
                        {'options': '-c standard_conforming_strings=off'},
                        {'replication': 'database'}):
            with self.subTest(options=options):
                stream = socket.socket(socket.AF_UNIX)
                self.addCleanup(stream.close)
                stream.settimeout(5)
                stream.connect(str(self.path))
                stream.sendall(startup(**options))
                self.denied(stream)
                self.assertEqual(self.backend.drain(), [])

    def test_backend_unsafe_initial_mode_never_allows_ready_query(self):
        self.backend.strings = b'off'
        stream = socket.socket(socket.AF_UNIX)
        self.addCleanup(stream.close)
        stream.settimeout(5)
        stream.connect(str(self.path))
        stream.sendall(startup())
        try:
            while True:
                kind, _ = receive(stream)
                self.assertNotEqual(kind, b'Z', 'unsafe backend reached ready state')
        except (EOFError, ConnectionResetError):
            pass
        self.assertEqual(self.backend.drain(), [])

    def test_backend_parse_error_cannot_execute_failed_pipeline(self):
        stream = self.connect()
        stream.sendall(parse('SELECT authored_missing_column;', 'bad') +
                       bind('badportal', 'bad') + execute('badportal') + packet(b'S'))
        seen = []
        try:
            while True:
                frame = receive(stream)
                seen.append(frame)
                if frame[0] == b'Z':
                    break
        except (EOFError, ConnectionResetError):
            pass
        self.assertIn(b'E', [kind for kind, _ in seen])
        self.assertTrue(self.backend.executions.empty())


if __name__ == '__main__':
    unittest.main()
