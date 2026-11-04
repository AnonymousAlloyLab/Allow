"""Finite ownership/control checks; simulated observations are not PostgreSQL cleanup proof."""
import asyncio
import copy
import json
import os
import struct
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from allow_retrieval.sql_context_control import decode_request, read_request
from allow_retrieval.sql_context_identity import kernel_record, identity_absent, process_identity
from allow_retrieval.sql_context_journal import ContextJournal, JournalUnavailable
from allow_retrieval.sql_context_lease import ContextLeases
from allow_retrieval.sql_context_observer import privacy_ready


class LeaseTests(unittest.IsolatedAsyncioTestCase):
    """Test durable reservations and bound receipts without starting a database connection."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.manager = ContextLeases(SimpleNamespace(status=root/'status.json', listen=root/'sql',
                                                    backend=root/'backend', cancel_keys=set()))
        self.peer = process_identity(os.getpid())

    def tearDown(self):
        self.manager.observer.shutdown()
        self.temporary.cleanup()

    def register(self):
        self.manager.route_enabled = True
        self.manager.ready = True
        nonce = str(uuid.uuid4())
        result = self.manager.register(nonce, self.peer)
        self.assertEqual('REGISTERED', result['status'])
        return nonce, result

    def test_noncanonical_route_never_registers_or_runs_preflight(self):
        self.manager.ready = True
        self.assertEqual('UNAVAILABLE', self.manager.register(str(uuid.uuid4()), self.peer)['status'])
        self.assertFalse(self.manager.route_enabled)
        self.assertIsNone(self.manager.journal.entry('observer'))

    def test_registration_is_exclusive_and_durable(self):
        nonce, _ = self.register()
        self.assertEqual(nonce, ContextJournal(self.manager.journal.directory).entry('context')['nonce'])
        self.assertEqual('UNAVAILABLE', self.manager.register(str(uuid.uuid4()), self.peer)['status'])

    def test_unknown_survives_restart_and_blocks_replacement(self):
        self.register()
        self.manager.unknown('context')
        restored = ContextJournal(self.manager.journal.directory)
        self.assertEqual('UNKNOWN', restored.entry('context')['phase'])
        self.assertTrue(restored.entry('context')['failed'])
        self.assertEqual('UNAVAILABLE', self.manager.register(str(uuid.uuid4()), self.peer)['status'])

    async def test_cleanup_after_failure_cannot_enable_success(self):
        nonce, registration = self.register()
        self.manager.poison('context')
        self.manager.complete('context', True)
        request = dict(registration, operation='awaitLease')
        request.pop('status')
        receipt = await self.manager.await_receipt(request, self.peer)
        self.assertEqual('CLEAN', receipt['status'])
        self.assertFalse(receipt['successPermitted'])
        self.assertEqual(nonce, receipt['nonce'])

    async def test_wrong_generation_never_receives_clean_receipt(self):
        _, registration = self.register()
        self.manager.complete('context')
        request = dict(registration, operation='awaitLease', generation=str(uuid.uuid4()))
        request.pop('status')
        self.assertEqual('UNAVAILABLE', (await self.manager.await_receipt(request, self.peer))['status'])

    async def test_wrong_process_generation_cannot_await(self):
        _, registration = self.register()
        self.manager.complete('context')
        request = dict(registration, operation='awaitLease')
        request.pop('status')
        foreign = dict(self.peer, startTicks='0')
        self.assertEqual('UNAVAILABLE', (await self.manager.await_receipt(request, foreign))['status'])

    def test_context_mutation_preserves_observer_entry(self):
        self.register()
        context = self.manager.journal.entry('context')
        observer = self.manager.new_entry('observer', self.manager.generation,
                       {key:context[key] for key in ('ownerPid','ownerStart','parentPid','parentStart')})
        self.manager.persist('observer', observer, advance=True)
        self.manager.poison('context')
        self.assertEqual(observer, self.manager.journal.entry('observer'))

    def test_expiry_does_not_drop_unknown_reservation(self):
        self.register()
        self.manager.unknown('context')
        with patch('allow_retrieval.sql_context_lease.time.monotonic', return_value=10**20):
            self.manager.expire_receipts()
        self.assertEqual('UNKNOWN', self.manager.journal.entry('context')['phase'])

    def test_absolute_deadline_and_parent_loss_are_fences(self):
        self.register()
        self.manager.deadline = 0
        with self.assertRaises(ValueError):
            self.manager.require_work()
        self.manager.deadline = 10**20
        with patch('allow_retrieval.sql_context_lease.owner_alive', return_value=False):
            with self.assertRaises(ValueError):
                self.manager.require_work()

    def test_missing_initialized_journal_degrades(self):
        self.manager.journal.path.unlink()
        self.assertTrue(ContextJournal(self.manager.journal.directory).failed)

    def test_duplicate_fields_and_boolean_version_degrade(self):
        for raw in (b'{"version":1,"version":1}',
                    b'{"version":true,"counter":0,"context":null,"observer":null}'):
            self.manager.journal.path.write_bytes(raw)
            self.assertTrue(ContextJournal(self.manager.journal.directory).failed)

    def test_deeply_nested_corrupt_journal_degrades_without_crash(self):
        self.manager.journal.path.write_bytes(b'[' * 2000 + b'0' + b']' * 2000)
        self.assertTrue(ContextJournal(self.manager.journal.directory).failed)

    def test_invalid_journal_cannot_replace_the_safe_in_memory_schema(self):
        """Corrupt parsed objects keep ordinary status usable and both reservations unknown."""
        for raw in (b'{}',b'[]',b'null',b'{"version":1}'):
            self.manager.journal.path.write_bytes(raw)
            restored = ContextLeases(self.manager.server)
            try:
                self.assertTrue(restored.journal.failed)
                self.assertEqual(restored.status(),{'protocol':1,'status':'DEGRADED',
                    'contextOccupied':True,'observerOccupied':True})
                self.assertEqual(restored.journal.path.read_bytes(),raw)
                self.assertEqual(restored.register(str(uuid.uuid4()),self.peer)['status'],'UNAVAILABLE')
            finally:
                restored.observer.shutdown()

    def test_uncertified_clean_and_impossible_phase_rejected(self):
        self.register()
        original = self.manager.journal.entry('context')
        variants = [dict(original, phase='CLEAN', opened=True),
                    dict(original, phase='RESERVED', opened=True),
                    dict(original, phase='KEYED', opened=True),
                    dict(original, phase='UNKNOWN', failed=False)]
        for entry in variants:
            with self.assertRaises(JournalUnavailable):
                self.manager.journal.replace('context', entry)

    def test_other_thread_cannot_mutate_journal(self):
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(self.manager.journal.write, copy.deepcopy(self.manager.journal.value))
            with self.assertRaises(JournalUnavailable):
                future.result()

    def test_journal_and_marker_modes_are_private(self):
        self.assertEqual(0o600, self.manager.journal.path.stat().st_mode & 0o777)
        self.assertEqual(0o600, self.manager.journal.marker.stat().st_mode & 0o777)
        self.assertEqual(0o700, self.manager.journal.directory.stat().st_mode & 0o777)

    async def test_observer_binding_cannot_overwrite_concurrent_retirement(self):
        async def delayed(method, *arguments, **keywords):
            if method.__name__ == 'probe':
                return True
            pid = os.getpid()
            self.manager.keyed('observer', struct.pack('!II', pid, 123))
            self.manager.poison('observer')
            return ((pid, '2026-01-01', 'allow_retrieval', 'allow_app', self.manager.observer.tag),)
        with patch.object(self.manager.observer, 'call', side_effect=delayed):
            with self.assertRaises(ValueError):
                await self.manager.open_observer()
        self.assertEqual('RETIRING', self.manager.journal.entry('observer')['phase'])
        self.assertTrue(self.manager.journal.entry('observer')['failed'])

    async def test_unknown_observer_cannot_be_overwritten_by_replacement(self):
        from unittest.mock import AsyncMock
        self.register()
        context = self.manager.journal.entry('context')
        observer = self.manager.new_entry('observer', self.manager.generation,
                       {key:context[key] for key in ('ownerPid','ownerStart','parentPid','parentStart')})
        self.manager.persist('observer', observer, advance=True)
        self.manager.unknown('observer')
        retained = self.manager.journal.entry('observer')
        with patch.object(self.manager.observer, 'call', new_callable=AsyncMock) as call:
            with self.assertRaises(ValueError):
                await self.manager.open_observer()
            call.assert_not_called()
        self.assertEqual(retained, self.manager.journal.entry('observer'))


class FailureCompletionTests(unittest.IsolatedAsyncioTestCase):
    """A private failure notification can forward only actual failed Ready, never data."""

    async def test_only_actual_failed_ready_completes_error(self):
        """Preserve libpq SQLSTATE without manufacturing transaction completion."""
        from unittest.mock import AsyncMock, Mock
        from allow_retrieval.sql_proxy import Session, packet, ProtocolError
        for kind, body, accepted in ((b'Z',b'E',True),(b'Z',b'I',False),(b'D',b'private',False)):
            session = Session(SimpleNamespace(),None,None)
            session.backend_reader = asyncio.StreamReader()
            session.backend_reader.feed_data(packet(kind,body))
            session.state = Mock()
            session.context_protocol = Mock()
            with patch('allow_retrieval.sql_proxy.send',new_callable=AsyncMock) as send:
                if accepted:
                    await session.context_error_ready()
                    send.assert_awaited_once_with(None,packet(b'Z',b'E'))
                    session.context_protocol.backend.assert_called_once_with(b'Z',b'E')
                else:
                    with self.assertRaises(ProtocolError):
                        await session.context_error_ready()
                    send.assert_not_awaited()


class ControlTests(unittest.IsolatedAsyncioTestCase):
    """Closed control bytes are checked after EOF, before registration side effects."""

    def frame(self):
        return json.dumps({'protocol':1,'operation':'register','nonce':str(uuid.uuid4())}).encode()

    def test_exact_boundary_and_overflow(self):
        raw = self.frame()
        self.assertEqual('register', decode_request(raw + b' ' * (8191-len(raw)) + b'\n')['operation'])
        with self.assertRaises(ValueError):
            decode_request(raw + b' ' * (8192-len(raw)) + b'\n')

    def test_closed_shape_and_duplicate_protocol(self):
        for raw in (b'{"protocol":1,"protocol":1,"operation":"status"}\n',
                    b'{"protocol":1,"operation":"status","sql":"SELECT 1"}\n',
                    b'{"protocol":true,"operation":"status"}\n'):
            with self.assertRaises(ValueError):
                decode_request(raw)

    async def test_deep_json_handler_denies_without_registration(self):
        from allow_retrieval.sql_context_control import ContextControl
        from unittest.mock import AsyncMock, Mock
        manager = Mock()
        control = ContextControl(manager, '/unused')
        reader = asyncio.StreamReader()
        reader.feed_data(b'[' * 2000 + b'0' + b']' * 2000 + b'\n')
        reader.feed_eof()
        writer = Mock()
        writer.wait_closed = AsyncMock()
        with patch('allow_retrieval.sql_context_control.peer_identity', return_value={}):
            await control.connected(reader, writer)
        manager.register.assert_not_called()
        writer.write.assert_not_called()

    async def test_two_frames_rejected_before_dispatch(self):
        reader = asyncio.StreamReader()
        reader.feed_data(self.frame() + b'\n' + self.frame() + b'\n')
        reader.feed_eof()
        with self.assertRaises(ValueError):
            await read_request(reader)

    async def test_first_line_without_half_close_does_not_dispatch(self):
        reader = asyncio.StreamReader()
        reader.feed_data(self.frame() + b'\n')
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(read_request(reader), .01)

    async def test_control_shutdown_closes_clients_before_server_wait(self):
        from allow_retrieval.sql_context_control import ContextControl
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            control = ContextControl(Mock(), Path(directory)/'context.sock')
            await control.start()
            reader, writer = await asyncio.open_unix_connection(str(control.path))
            writer.write(b'{')
            await writer.drain()
            await asyncio.sleep(.01)
            await asyncio.wait_for(control.close(), 1)
            self.assertEqual(b'', await reader.read())
            writer.close()
            await writer.wait_closed()


class ObserverPrerequisiteTests(unittest.TestCase):
    """Finite settings and process-generation checks do not exercise PG cleanup."""

    def test_safe_defaults_and_disabled_parameter_logging(self):
        self.assertTrue(privacy_ready(('20','3','0','none','-1','-1','0','-1','0')))
        self.assertTrue(privacy_ready(('20','3','0','all','0','0','1','0','0')))

    def test_unsafe_settings_fail_closed(self):
        base = ['20','3','0','none','-1','-1','0','-1','0']
        for index, value in ((0,'21'),(1,'4'),(2,'1'),(3,'all'),(4,'0'),(5,'0'),(6,'1'),(8,'1')):
            changed = base.copy()
            changed[index] = value
            self.assertFalse(privacy_ready(tuple(changed)))

    def test_current_identity_and_reused_generation(self):
        identity = kernel_record(os.getpid())
        self.assertFalse(identity_absent(identity))
        self.assertTrue(identity_absent(dict(identity, startTicks='0')))


class ForwardingFenceTests(unittest.IsolatedAsyncioTestCase):
    """The actual frontend coroutine rechecks work authority after awaited parser work."""

    async def test_parser_completion_after_deadline_cannot_forward_sql(self):
        from allow_retrieval.sql_proxy import Session, packet
        from allow_retrieval.sql_context_protocol import StrictContextProtocol
        from unittest.mock import Mock
        expired = False

        def require_work():
            if expired:
                raise ValueError('context_retired')

        async def admit(tag, sql):
            nonlocal expired
            await asyncio.sleep(0)
            expired = True

        reader = asyncio.StreamReader()
        reader.feed_data(packet(b'Q', b'BEGIN\0'))
        server = SimpleNamespace(contexts=SimpleNamespace(require_work=require_work),
                                 admit=admit, record=Mock())
        session = Session(server, reader, Mock())
        session.authenticated = True
        session.ready_event.set()
        session.lease_kind = 'context'
        session.context_protocol = StrictContextProtocol('context')
        session.context_protocol.backend(b'Z', b'I')
        session.backend_writer = Mock()
        with self.assertRaises(ValueError):
            await session.frontend()
        session.backend_writer.write.assert_not_called()

    async def test_shutdown_keeps_observer_until_context_cleanup_finishes(self):
        from allow_retrieval.sql_proxy import ProxyServer
        log = []
        stop = asyncio.Event()
        started = asyncio.Event()

        async def observer():
            await stop.wait()
            log.append('observer_exit')

        observer_task = asyncio.create_task(observer())

        async def context():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                self.assertFalse(observer_task.done())
                log.append('context_cleaned')

        context_task = asyncio.create_task(context())
        await started.wait()

        async def stop_admission():
            log.append('admission_stopped')

        async def stop_observer():
            self.assertTrue(context_task.done())
            log.append('observer_close')
            stop.set()

        contexts = SimpleNamespace(sessions={'observer':SimpleNamespace(owner_task=observer_task)},
                                   stop_admission=stop_admission, stop=stop_observer)
        server = SimpleNamespace(contexts=contexts, handlers={context_task,observer_task})
        await asyncio.wait_for(ProxyServer.close_sessions(server), 1)
        self.assertEqual(['admission_stopped','context_cleaned','observer_close','observer_exit'], log)

    def test_error_notification_keeps_only_whitelisted_sqlstate(self):
        from allow_retrieval.sql_proxy import context_error
        for code in (b'55P03', b'57014', b'25P03'):
            body = b'SERROR\0C' + code + b'\0Mprivate_source\0Dprivate_parameters\0\0'
            result = context_error(body)
            self.assertIn(b'C' + code + b'\0', result)
            self.assertNotIn(b'private_', result)
        self.assertIn(b'C58000\0', context_error(b'SERROR\0C55P03\0C57014\0\0'))

    async def test_actual_proxy_run_exits_with_live_persistent_connection(self):
        from allow_retrieval.sql_proxy import ProxyServer, packet

        class FixtureGate:
            info = {'test_fixture':'shutdown-only-no-SQL'}

            def validate(self, sql):
                raise AssertionError('Shutdown fixture must not issue SQL')

        async def backend(reader, writer):
            try:
                size = struct.unpack('!I', await reader.readexactly(4))[0]
                await reader.readexactly(size - 4)
                frames = [packet(b'R', struct.pack('!I', 0)),
                          packet(b'S', b'client_encoding\0UTF8\0'),
                          packet(b'S', b'standard_conforming_strings\0on\0'),
                          packet(b'K', struct.pack('!II', 123, 456)), packet(b'Z', b'I')]
                writer.write(b''.join(frames))
                await writer.drain()
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend_server = await asyncio.start_unix_server(backend, path=str(root/'backend'))
            proxy = ProxyServer(root/'backend', root/'proxy', root/'status.json', gate=FixtureGate())
            running = asyncio.create_task(proxy.run())
            try:
                async with asyncio.timeout(2):
                    while not (root/'status.json').exists():
                        await asyncio.sleep(.005)
                reader, writer = await asyncio.open_unix_connection(str(root/'proxy'))
                startup = struct.pack('!I', 196608) + b'user\0test\0database\0test\0application_name\0allow-tests\0\0'
                writer.write(struct.pack('!I', len(startup)+4) + startup)
                await writer.drain()
                while True:
                    kind = await reader.readexactly(1)
                    size = struct.unpack('!I', await reader.readexactly(4))[0]
                    await reader.readexactly(size-4)
                    if kind == b'Z':
                        break
                proxy.stopping.set()
                await asyncio.wait_for(running, 2)
                self.assertEqual(b'', await reader.read())
                writer.close()
                await writer.wait_closed()
            finally:
                proxy.stopping.set()
                if not running.done():
                    running.cancel()
                await asyncio.gather(running, return_exceptions=True)
                backend_server.close()
                await backend_server.wait_closed()
