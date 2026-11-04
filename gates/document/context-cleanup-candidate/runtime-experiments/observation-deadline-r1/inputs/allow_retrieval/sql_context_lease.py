"""Proxy-owned read-only leases keep uncertain PostgreSQL work out of replacement admission."""
import asyncio
from collections import OrderedDict
import os
import struct
import time
import uuid

from .sql_context_control import ContextControl
from .sql_context_identity import (kernel_record, identity_absent, owner_record, owner_matches,
                                   owner_alive, process_identity)
from .sql_context_journal import ContextJournal, canonical_uuid
from .sql_context_observer import ContextObserver
from .sql_connections import PROXY_SOCKET, BACKEND_SOCKET


def occupied(entry):
    """A clean resource alone is reusable; unknown and retiring resources stay reserved."""
    return entry is not None and entry['phase'] != 'CLEAN'


class ContextLeases:
    """One asyncio owner serializes journal, registration, cleanup and receipt decisions."""

    def __init__(self, server):
        self.server = server
        self.generation = str(uuid.uuid4())
        self.journal = ContextJournal(server.status.parent)
        self.observer = ContextObserver(self.generation)
        self.control = ContextControl(self, server.listen.parent / 'context.sock')
        self.ready = False
        self.degraded = self.journal.failed
        self.stopping = False
        self.maintenance = None
        self.sessions = {}
        self.receipts = OrderedDict()
        self.deadline = None
        self.wakeup = asyncio.Event()
        self.observer_attempted = False
        self.next_probe = 0.0
        self.route_enabled = server.listen == PROXY_SOCKET and server.backend == BACKEND_SOCKET

    def status(self):
        """Expose bounded aggregate state without owner/backend identities or secrets."""
        state = 'READY' if self.ready and not self.stopping else 'NOT_READY'
        if self.degraded or self.journal.failed:
            state = 'DEGRADED'
        return {'protocol': 1, 'status': state,
                'contextOccupied': self.journal.failed or occupied(self.journal.entry('context')),
                'observerOccupied': self.journal.failed or occupied(self.journal.entry('observer'))}

    def persist(self, kind, entry, *, advance=False):
        """Persist the current whole-state mutation or retain reservations in degraded mode."""
        try:
            self.journal.replace(kind, entry, advance=advance)
        except (OSError, ValueError, TypeError):
            self.degraded = True
            self.ready = False
            raise
        self.wakeup.set()

    def new_entry(self, kind, nonce, owner):
        """Construct a closed reservation before any backend connection is attempted."""
        tag = ('allow-document-context:' + nonce if kind == 'context'
               else 'allow-context-observer:' + self.generation)
        return dict(owner, generation=self.generation, leaseGeneration=self.journal.value['counter'] + 1,
                    nonce=nonce, database='allow_retrieval', user='allow_app', applicationName=tag,
                    phase='RESERVED', backendPid=None, backendKey=None, backendStart=None,
                    kernelIdentity=None, failed=False, successPermitted=False, opened=False)

    def reply(self, status, nonce, generation=None, lease_generation=0):
        """Return the closed private identity envelope used by both control operations."""
        return {'protocol': 1, 'status': status, 'generation': generation or self.generation,
                'leaseGeneration': lease_generation, 'nonce': nonce}

    def register(self, nonce, peer):
        """Reserve once with an absolute work deadline and actual peer/parent identities."""
        self.expire_receipts()
        if (not self.route_enabled or not self.ready or self.stopping or self.degraded or self.journal.failed
                or occupied(self.journal.entry('context')) or nonce in self.receipts):
            return self.reply('UNAVAILABLE', nonce)
        try:
            entry = self.new_entry('context', nonce, owner_record(peer))
            self.persist('context', entry, advance=True)
            self.deadline = time.monotonic() + 3
            return self.reply('REGISTERED', nonce, lease_generation=entry['leaseGeneration'])
        except (OSError, ValueError, TypeError):
            return self.reply('UNAVAILABLE', nonce)

    def expire_receipts(self):
        """Bound clean receipts independently of active/unknown durable reservations."""
        now = time.monotonic()
        for key, (_, until) in tuple(self.receipts.items()):
            if until <= now:
                self.receipts.pop(key)
        while len(self.receipts) > 64:
            self.receipts.popitem(last=False)

    async def await_receipt(self, request, peer):
        """Wait boundedly for exact cleanup; socket EOF or elapsed time never means CLEAN."""
        until = time.monotonic() + 6
        failure = self.reply('UNAVAILABLE', request['nonce'], request['generation'], request['leaseGeneration'])
        while True:
            self.expire_receipts()
            receipt = self.receipts.get(request['nonce'])
            entry = receipt[0] if receipt else self.journal.entry('context')
            if (entry is None or entry['nonce'] != request['nonce'] or not owner_matches(entry, peer)
                    or entry['generation'] != request['generation']
                    or entry['leaseGeneration'] != request['leaseGeneration']):
                return failure
            if receipt:
                result = self.reply('CLEAN', entry['nonce'], entry['generation'], entry['leaseGeneration'])
                result['successPermitted'] = entry['successPermitted'] and owner_alive(entry)
                return result
            if entry['phase'] == 'UNKNOWN' or time.monotonic() >= until or self.stopping:
                return failure
            self.wakeup.clear()
            try:
                await asyncio.wait_for(self.wakeup.wait(), max(0.001, until - time.monotonic()))
            except asyncio.TimeoutError:
                return failure

    def role(self, application):
        """Recognize only the two exact dynamic private startup tag families."""
        for kind, prefix in (('context', 'allow-document-context:'), ('observer', 'allow-context-observer:')):
            if application.startswith(prefix):
                if not canonical_uuid(application[len(prefix):]):
                    raise ValueError('invalid_context_tag')
                return kind
        return None

    def attach(self, session, fields, peer):
        """Bind an authenticated endpoint attempt to its previously durable reservation."""
        kind = self.role(fields.get('application_name', ''))
        if kind is None:
            return None
        entry = self.journal.entry(kind)
        if (not self.route_enabled or entry is None or self.journal.failed or self.stopping or kind in self.sessions
                or fields.get('user') != entry['user'] or fields.get('database') != entry['database']
                or fields.get('application_name') != entry['applicationName'] or not owner_matches(entry, peer)):
            raise ValueError('context_registration_required')
        if kind == 'context':
            if entry['phase'] != 'RESERVED' or entry['generation'] != self.generation:
                raise ValueError('context_generation_unavailable')
            self.require_work()
        elif peer['pid'] != os.getpid() or entry['phase'] != 'CONNECTING':
            raise ValueError('observer_peer_denied')
        entry.update(phase='CONNECTING', opened=True)
        self.persist(kind, entry)
        self.sessions[kind] = session
        return kind

    def require_work(self):
        """Fence every context forwarding/success operation with owner and absolute deadline."""
        entry = self.journal.entry('context')
        if (entry is None or entry['failed'] or self.deadline is None
                or time.monotonic() >= self.deadline or not owner_alive(entry)
                or self.degraded or self.journal.failed or self.stopping):
            raise ValueError('context_retired')

    def keyed(self, kind, key):
        """Durably capture BackendKeyData before exposing startup readiness."""
        entry = self.journal.entry(kind)
        if entry is None or entry['phase'] != 'CONNECTING' or len(key) != 8:
            raise ValueError('context_backend_identity')
        entry.update(phase='KEYED', backendPid=struct.unpack('!I', key[:4])[0], backendKey=key.hex())
        if kind == 'observer':
            entry['kernelIdentity'] = kernel_record(entry['backendPid'])
        self.persist(kind, entry)

    async def bound(self, kind):
        """Bind context metadata through the independent owned observer before initial Ready."""
        if kind == 'observer':
            return
        self.require_work()
        entry = self.journal.entry(kind)
        rows = await self.observer.call(self.observer.identity, entry['backendPid'], entry['database'],
                                        entry['user'], entry['applicationName'])
        if (len(rows) != 1 or rows[0][0] != entry['backendPid']
                or tuple(rows[0][2:]) != (entry['database'], entry['user'], entry['applicationName'])):
            raise ValueError('context_metadata_unavailable')
        self.require_work()
        entry.update(phase='BOUND', backendStart=rows[0][1])
        self.persist(kind, entry)

    def poison(self, kind):
        """Sticky failure disables publication even when later cleanup succeeds."""
        entry = self.journal.entry(kind)
        if occupied(entry):
            entry.update(failed=True, successPermitted=False, phase='RETIRING')
            self.persist(kind, entry)
        if kind == 'observer':
            self.ready = False

    async def send_cancel(self, entry):
        """Use only a durably owned key; no PostgreSQL PID-only signaling function exists."""
        if not entry['backendKey']:
            return
        key = bytes.fromhex(entry['backendKey'])
        self.server.cancel_keys.add(key)
        await self.server.cancel_owned(key)

    def cancelled(self, key):
        """Linearize a caller's cancellation before any later staged success publication."""
        for kind in ('context', 'observer'):
            entry = self.journal.entry(kind)
            if occupied(entry) and entry['backendKey'] == key.hex():
                self.poison(kind)
                session = self.sessions.get(kind)
                if session is not None:
                    session.context_protocol.mark_failed()
                    session.owner_task.cancel()

    async def finish(self, session):
        """Retire the owned transport, observe exit, then issue a bounded cleanup receipt."""
        kind = session.lease_kind
        if kind == 'observer':
            self.ready = False
        entry = self.journal.entry(kind)
        if entry is None:
            await session.close_transports()
            return
        normal = kind == 'context' and session.context_protocol.terminated_successfully
        try:
            if normal:
                self.require_work()
            else:
                entry['failed'] = True
        except (ValueError, OSError):
            entry['failed'] = True
        entry.update(phase='RETIRING', successPermitted=False)
        try:
            self.persist(kind, entry)
            if entry['failed']:
                await self.send_cancel(entry)
        except (OSError, ValueError, asyncio.TimeoutError):
            self.ready = False
        await session.close_transports()
        self.sessions.pop(kind, None)
        try:
            clean = await self.observe_cleanup(kind)
            if clean:
                self.complete(kind, normal and not entry['failed'])
            else:
                self.unknown(kind)
        except (OSError, ValueError, RuntimeError, asyncio.TimeoutError):
            self.unknown(kind)
        if kind == 'observer':
            self.ready = False

    def unknown(self, kind):
        """Keep uncertain ownership durable; never infer release from a timeout."""
        self.ready = False
        self.degraded = True
        entry = self.journal.entry(kind)
        if entry is not None and not self.journal.failed:
            entry.update(phase='UNKNOWN', failed=True, successPermitted=False)
            self.persist(kind, entry)
        self.wakeup.set()

    def complete(self, kind, success=False):
        """Publish cleanup only after persistence and retain sticky failure semantics."""
        entry = self.journal.entry(kind)
        if entry is None:
            return
        entry.update(phase='CLEAN', successPermitted=success and not entry['failed'])
        self.persist(kind, entry)
        if entry['backendKey']:
            self.server.cancel_keys.discard(bytes.fromhex(entry['backendKey']))
        if kind == 'context':
            self.receipts[entry['nonce']] = (entry, time.monotonic() + 60)
            self.expire_receipts()
            self.deadline = None

    async def observe_cleanup(self, kind):
        """Observe positive absence within a budget, retaining unresolved identity otherwise."""
        until = time.monotonic() + 2.5
        while time.monotonic() < until:
            entry = self.journal.entry(kind)
            if not entry['opened']:
                return True
            if kind == 'observer':
                if entry['kernelIdentity'] is None:
                    return False
                if identity_absent(entry['kernelIdentity']):
                    return True
            else:
                if entry['backendStart'] is None:
                    rows = await self.observer.call(self.observer.reconcile, entry['database'],
                                                    entry['user'], entry['applicationName'], timeout=0.75)
                    if len(rows) != 1 or (entry['backendPid'] is not None and rows[0][0] != entry['backendPid']):
                        return False
                    entry.update(backendPid=rows[0][0], backendStart=rows[0][1])
                    self.persist(kind, entry)
                rows = await self.observer.call(self.observer.identity, entry['backendPid'], entry['database'],
                                                entry['user'], entry['applicationName'], timeout=0.75)
                if not rows or (len(rows) == 1 and rows[0][1] != entry['backendStart']):
                    return True
                if len(rows) != 1:
                    return False
            await asyncio.sleep(0.025)
        return False

    async def start(self):
        """Serve ordinary SQL independently while context startup reconciles private state."""
        await self.control.start()
        if self.route_enabled:
            self.maintenance = asyncio.create_task(self.maintain())

    async def recover_observer(self):
        """Resolve only a recorded kernel generation before opening any replacement observer."""
        entry = self.journal.entry('observer')
        if not occupied(entry):
            return True
        if not entry['opened']:
            self.complete('observer')
            return True
        if entry['kernelIdentity'] is None:
            self.unknown('observer')
            return False
        await self.send_cancel(entry)
        if await self.observe_cleanup('observer'):
            self.complete('observer')
            return True
        self.unknown('observer')
        return False

    async def open_observer(self):
        """Reserve after bounded configured-role preflight; never overlap connection attempts."""
        if occupied(self.journal.entry('observer')) or self.observer_attempted:
            raise ValueError('observer_reservation_retained')
        if not await self.observer.call(self.observer.probe, timeout=6):
            return False
        peer = process_identity(os.getpid())
        parent = process_identity(peer['parentPid'])
        if parent is None:
            raise ValueError('observer_parent_unavailable')
        owner = {'ownerPid': peer['pid'], 'ownerStart': peer['startTicks'],
                 'parentPid': parent['pid'], 'parentStart': parent['startTicks']}
        entry = self.new_entry('observer', self.generation, owner)
        self.persist('observer', entry, advance=True)
        entry.update(phase='CONNECTING', opened=True)
        self.persist('observer', entry)
        self.observer_attempted = True
        rows = await self.observer.call(self.observer.open, timeout=8)
        entry = self.journal.entry('observer')
        if (entry['phase'] != 'KEYED' or entry['failed'] or len(rows) != 1 or rows[0][0] != entry['backendPid']
                or tuple(rows[0][2:]) != (entry['database'], entry['user'], entry['applicationName'])
                or identity_absent(entry['kernelIdentity'])):
            raise ValueError('observer_identity_unavailable')
        entry.update(phase='BOUND', backendStart=rows[0][1])
        self.persist('observer', entry)
        return True

    async def maintain(self):
        """Poll owner/deadline fences and perform at most one serialized startup attempt."""
        try:
            if not self.journal.failed and not await self.recover_observer():
                return
            while not self.stopping:
                if not self.ready and not self.degraded and time.monotonic() >= self.next_probe:
                    self.next_probe = time.monotonic() + 1
                    if self.observer_attempted:
                        self.degraded = True
                        continue
                    try:
                        if await self.open_observer():
                            entry = self.journal.entry('context')
                            if occupied(entry):
                                self.poison('context')
                                await self.send_cancel(entry)
                                if await self.observe_cleanup('context'):
                                    self.complete('context')
                                else:
                                    self.unknown('context')
                            self.ready = not self.degraded
                    except (OSError, ValueError, RuntimeError, asyncio.TimeoutError):
                        if self.observer_attempted:
                            self.unknown('observer')
                entry = self.journal.entry('context')
                if occupied(entry) and entry['generation'] == self.generation and entry['phase'] not in {'RETIRING', 'UNKNOWN'}:
                    try:
                        self.require_work()
                    except (ValueError, OSError):
                        self.poison('context')
                        session = self.sessions.get('context')
                        if session is not None:
                            session.context_protocol.mark_failed()
                            session.owner_task.cancel()
                        elif not entry['opened']:
                            self.complete('context')
                        else:
                            self.unknown('context')
                self.expire_receipts()
                await asyncio.sleep(0.025)
        except (OSError, ValueError, RuntimeError):
            self.degraded = True
            self.ready = False

    async def stop(self):
        """Stop admission; retain any resource that cannot be independently observed gone."""
        await self.stop_admission()
        try:
            await self.observer.call(self.observer.close, timeout=2.5)
        except (OSError, ValueError, RuntimeError, asyncio.TimeoutError):
            if occupied(self.journal.entry('observer')):
                self.unknown('observer')
        self.observer.shutdown()
        await self.control.close()

    async def stop_admission(self):
        """Stop new work while keeping the existing observer alive for context cleanup."""
        self.stopping = True
        self.ready = False
        self.wakeup.set()
        if self.maintenance is not None:
            self.maintenance.cancel()
            await asyncio.gather(self.maintenance, return_exceptions=True)
