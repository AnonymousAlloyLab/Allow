"""Finite client receipt and publication checks without database or live services."""
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

from allow_documents import context_lease as lease


class ContextLeaseClientTests(unittest.TestCase):
    """Exercise closed frames and cleanup-before-return independently of the proxy."""

    def setUp(self):
        """Mint synthetic operational identities, unrelated to any document."""
        self.nonce = str(uuid.uuid4())
        self.registration = {'protocol':1,'status':'REGISTERED','generation':str(uuid.uuid4()),
                             'leaseGeneration':1,'nonce':self.nonce}
        self.receipt = dict(self.registration,status='CLEAN',successPermitted=True)

    def test_registration_is_closed_and_nonce_bound(self):
        """Reject coercions and stale fields before accepting a control capability."""
        self.assertEqual(lease.validate_reply(self.registration,self.nonce),self.registration)
        changes = [{'extra':True},{'protocol':True},{'nonce':str(uuid.uuid4())},
                   {'status':'CLEAN'},{'generation':'INVALID'},{'leaseGeneration':True},
                   {'leaseGeneration':0},{'leaseGeneration':9007199254740992}]
        for change in changes:
            with self.subTest(change=tuple(change)):
                with self.assertRaises(RuntimeError):
                    lease.validate_reply(dict(self.registration,**change),self.nonce)

    def test_cleanup_receipt_matches_all_registration_identity(self):
        """A new proxy, reused nonce or different lease cannot discharge old ownership."""
        changes = [{'generation':str(uuid.uuid4())},{'leaseGeneration':2},
                   {'nonce':str(uuid.uuid4())},{'successPermitted':1},{'extra':'no'},
                   {'status':'UNKNOWN'}]
        for change in changes:
            with self.subTest(change=tuple(change)):
                with self.assertRaises(RuntimeError):
                    lease.validate_reply(dict(self.receipt,**change),self.nonce,True,self.registration)

    def test_cleanup_success_flag_is_required(self):
        """CLEAN without the explicit Boolean publication flag is not a success receipt."""
        value = dict(self.receipt)
        del value['successPermitted']
        with self.assertRaises(RuntimeError):
            lease.validate_reply(value,self.nonce,True,self.registration)

    def run_connection(self, receipt=None, failure=None):
        """Record real context-manager ordering with a controlled database transport."""
        events = []
        def connect(**kwargs):
            """Model transaction close while retaining exact canonical client arguments."""
            self.assertEqual(kwargs['client'],'allow-document-context:'+self.nonce)
            events.append('connect')
            class Connection:
                """Model explicit commit and close without an implicit error rollback."""
                def commit(self):
                    """Record only successful completion of the read-only transaction."""
                    events.append('committed')
                def close(self):
                    """Record close before the independent cleanup receipt is requested."""
                    events.append('closed')
            return Connection()
        def registered(nonce):
            """Require registration to precede opening a database transport."""
            self.assertEqual(nonce,self.nonce)
            events.append('register')
            return self.registration
        def cleaned(registration):
            """A receipt is requested only after the caller's transport has closed."""
            self.assertEqual(events[-1],'closed')
            events.append('receipt')
            if isinstance(receipt,Exception):
                raise receipt
            return receipt if receipt is not None else self.receipt
        with patch.object(lease,'register',registered), patch.object(lease,'await_cleanup',cleaned):
            with patch.object(lease.sql_connections,'connect',connect):
                with lease.connection(self.nonce,object()) as connection:
                    self.assertIsNotNone(connection)
                    events.append('staged')
                    if failure is not None:
                        raise failure
                events.append('returned')
        return events

    def test_success_waits_for_transport_close_and_receipt(self):
        """Staged output cannot return between connection closure and confirmed cleanup."""
        self.assertEqual(self.run_connection(),
                         ['register','connect','staged','committed','closed','receipt','returned'])

    def test_poisoned_cleanup_never_becomes_success(self):
        """A failed lease can be clean without permitting validation publication."""
        with self.assertRaisesRegex(RuntimeError,'context_validation_retired'):
            self.run_connection(dict(self.receipt,successPermitted=False))

    def test_original_request_failure_survives_confirmed_cleanup(self):
        """A missing document stays a request error after its failed lease is cleaned."""
        with self.assertRaisesRegex(ValueError,'document_not_found'):
            self.run_connection(dict(self.receipt,successPermitted=False),ValueError('document_not_found'))

    def test_unconfirmed_cleanup_overrides_request_error(self):
        """Unresolved ownership is unavailable even when the original request was invalid."""
        with self.assertRaisesRegex(RuntimeError,'unknown'):
            self.run_connection(RuntimeError('unknown'),ValueError('document_not_found'))

    def test_registration_failure_never_connects(self):
        """No backend is opened without a proxy-issued exclusive reservation."""
        with patch.object(lease,'register',side_effect=RuntimeError('busy')):
            with patch.object(lease.sql_connections,'connect') as connect:
                with self.assertRaises(RuntimeError):
                    with lease.connection(self.nonce,object()):
                        self.fail('unregistered connection yielded')
                connect.assert_not_called()

    def test_control_request_has_no_pid_route_or_scope(self):
        """Only operational nonce and generation fields cross the private control channel."""
        with patch.object(lease,'exchange',return_value=self.registration) as exchange:
            self.assertEqual(lease.register(self.nonce),self.registration)
            self.assertEqual(exchange.call_args.args[0],
                             {'protocol':1,'operation':'register','nonce':self.nonce})
        with patch.object(lease,'exchange',return_value=self.receipt) as exchange:
            lease.await_cleanup(self.registration)
            self.assertEqual(set(exchange.call_args.args[0]),
                             {'protocol','operation','nonce','generation','leaseGeneration'})

    def real_exchange(self, response):
        """Drive the actual bounded Unix client against a private test-only server."""
        with tempfile.TemporaryDirectory(prefix='allow-cc-client-') as directory:
            path = Path(directory)/'context.sock'
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                server.bind(str(path)); path.chmod(0o600); server.listen(1)
                failures, requests = [], []
                def serve():
                    """Require request EOF before returning this fixture's exact reply bytes."""
                    try:
                        with server.accept()[0] as peer:
                            peer.settimeout(2)
                            chunks = []
                            while data := peer.recv(8193):
                                chunks.append(data)
                            requests.append(json.loads(b''.join(chunks)))
                            peer.sendall(response)
                    except Exception as error:
                        failures.append(type(error).__name__)
                thread = threading.Thread(target=serve,daemon=True)
                thread.start()
                try:
                    with patch.object(lease.sql_connections,'PROXY_DIRECTORY',Path(directory)):
                        return lease.exchange({'protocol':1,'operation':'status'})
                finally:
                    thread.join(timeout=3)
                    self.assertFalse(thread.is_alive())
                    self.assertFalse(failures)
                    self.assertEqual(requests,[{'protocol':1,'operation':'status'}])

    def test_real_control_eof_and_exact_reply(self):
        """The real socket path sends a complete frame before parsing its response."""
        self.assertEqual(self.real_exchange(json.dumps(self.registration).encode()+b'\n'),self.registration)

    def test_real_control_duplicate_and_oversize_replies(self):
        """Duplicate-key, invalid UTF8 and oversized output cannot become a receipt."""
        for raw in (b'{"protocol":1,"protocol":1}', b'\xff', b' '*8193):
            with self.subTest(length=len(raw)):
                with self.assertRaises((ValueError,RuntimeError)):
                    self.real_exchange(raw)

    def test_real_control_exact_byte_limit_is_inclusive(self):
        """A valid response padded to exactly8192 bytes retains its closed fields."""
        raw = json.dumps(self.registration).encode()
        self.assertEqual(self.real_exchange(raw+b' '*(8192-len(raw))),self.registration)

    def test_private_control_socket_modes_are_required(self):
        """Wrong modes and symlinks fail before connecting to any endpoint."""
        with tempfile.TemporaryDirectory(prefix='allow-cc-modes-') as directory:
            path = Path(directory)/'context.sock'
            path.write_text('not a socket')
            path.chmod(0o600)
            with patch.object(lease.sql_connections,'PROXY_DIRECTORY',Path(directory)):
                with self.assertRaises(RuntimeError):
                    lease.control_path()
                path.unlink()
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                    server.bind(str(path)); path.chmod(0o666)
                    with self.assertRaises(RuntimeError):
                        lease.control_path()


if __name__ == '__main__':
    unittest.main()
