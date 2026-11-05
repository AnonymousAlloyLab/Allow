"""Explicit opt-in only: run in an isolated fresh package, never a live workspace."""
import os
import time
import uuid
import unittest
from allow_documents import lifecycle, wire
from allow_documents.store import Store


@unittest.skipUnless(os.environ.get('ALLOW_ANONYMOUS_ISOLATED_SQL_TESTS') == '1',
                     'Requires an explicitly isolated fresh SQL installation')
class AnonymousSQLTests(unittest.TestCase):
    """Exercise real proxy-only RLS, bounded admission and scoped atomic purge."""
    def setUp(self):
        """Allocate two fresh test scopes without changing private identity files."""
        self.scopes = []
        self.incarnation = str(uuid.uuid4())
        for _ in range(2):
            scope = {'version': 1, 'principalId': str(uuid.uuid4()), 'workspaceId': str(uuid.uuid4()),
                     'logicalLaunchId': str(uuid.uuid4())}
            args = {'policyVersion': 'document-v1', 'expiresAtEpochMillis': int(time.time() * 1000) + 1800000,
                    'incarnation': self.incarnation}
            self.scopes.append(scope)
            self.assertEqual(lifecycle.initialize(scope, args, Store)['status'], 'READY')
        self.a, self.b = (Store(scope, public=True) for scope in self.scopes)

    def tearDown(self):
        """Purge only registered test scopes; never reset journals or private state."""
        for scope in self.scopes:
            lifecycle.purge(scope, {'incarnation': self.incarnation})

    def create(self, store, key=None):
        """Reuse existing accepted-frame fixtures while exercising actual SQL commits."""
        from test_documents import DocumentSQLTests
        helper = DocumentSQLTests()
        helper.store = store
        request = helper.request()
        if key is not None:
            content = wire.decode(wire.unb64(request['bodyBase64'], wire.MAX_REQUEST))
            content['idempotencyKey'] = key
            request.update(key=key, bodyBase64=wire.b64(wire.encode(content)))
        admission = store.admit(request)
        self.assertEqual(admission['status'], 'ADMITTED')
        result, args, raw = helper.finish(request, admission)
        self.assertEqual(result['status'], 'COMMITTED')
        return result['documentId'], request, raw

    def test_same_key_independent_and_cross_scope_history_denied(self):
        """Equal keys in two scopes yield independent receipts/documents, never leakage."""
        key = uuid.uuid4().hex
        first, request, first_raw = self.create(self.a, key)
        second, _, second_raw = self.create(self.b, key)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first_raw, second_raw)
        self.assertEqual(self.a.receipt(request)['responseBase64'], wire.b64(first_raw))
        self.assertEqual(self.b.receipt(request)['responseBase64'], wire.b64(second_raw))
        with self.assertRaises(ValueError):
            self.b.read({'documentId': first, 'revision': 0})
        lifecycle.purge(self.scopes[0], {'incarnation': self.incarnation})
        self.assertEqual(self.b.read({'documentId': second, 'revision': 0})['documentId'], second)

    def test_fourth_document_rejected_in_store(self):
        """The SQL store, not the browser, enforces three-document anonymous quota."""
        for _ in range(3):
            self.create(self.a)
        from test_documents import DocumentSQLTests
        helper = DocumentSQLTests()
        helper.store = self.a
        self.assertEqual(self.a.admit(helper.request())['status'], 'CAPACITY_PRE_ADMISSION')

    def test_initializer_and_purge_serialize_without_orphan_resurrection(self):
        """An actual table-lock race drains initialization before deleting its provenance."""
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import contextmanager
        import threading
        target = {'version': 1, 'principalId': str(uuid.uuid4()), 'workspaceId': str(uuid.uuid4()),
                  'logicalLaunchId': str(uuid.uuid4())}
        args = {'policyVersion': 'document-v1', 'expiresAtEpochMillis': int(time.time() * 1000) + 1800000,
                'incarnation': self.incarnation}
        lifecycle.register(target, args)
        self.scopes.append(target)
        store = Store(target, public=True)
        original = store.transaction
        entered, resume = threading.Event(), threading.Event()

        @contextmanager
        def paused(initializing=False):
            with original(initializing=initializing) as connection:
                entered.set()
                if not resume.wait(5):
                    raise RuntimeError('test initialization barrier timed out')
                yield connection

        store.transaction = paused
        with ThreadPoolExecutor(max_workers=2) as executor:
            initializer = executor.submit(store.initialize, 'document-v1')
            self.assertTrue(entered.wait(5))
            cleanup = executor.submit(lifecycle.purge, target, {'incarnation': self.incarnation})
            resume.set()
            self.assertEqual(initializer.result(10)['status'], 'READY')
            self.assertEqual(cleanup.result(10)['status'], 'PURGED')
        with self.assertRaises(ValueError):
            Store(target, public=True).initialize('document-v1')

    def test_public_validation_context_exact_registry_branch(self):
        """The real parser/proxy context lane accepts only owned public snapshots."""
        document, _, _ = self.create(self.a)
        args = {'documentId': document, 'revision': 0, 'ids': []}
        result = self.a.validation_context(args)
        self.assertEqual(result['documentId'], document)
        self.assertEqual(result['baseRevision'], 0)
        self.assertEqual(result['ownedIdInventory'], {})
        with self.assertRaises((ValueError, RuntimeError)):
            self.b.validation_context(args)

    def test_registry_rls_read_only_app_permissions(self):
        """App registry reads are scoped and INSERT/UPDATE/DELETE remain denied."""
        import psycopg
        with self.a.transaction() as connection:
            rows = connection.execute('SELECT principal_id,workspace_id FROM documents.public_workspace_lifecycle').fetchall()
            self.assertEqual(rows, [{'principal_id': self.scopes[0]['principalId'],
                                     'workspace_id': self.scopes[0]['workspaceId']}])
            other = connection.execute('SELECT 1 FROM documents.public_workspace_lifecycle WHERE principal_id=%s AND workspace_id=%s',
                                       (self.scopes[1]['principalId'], self.scopes[1]['workspaceId'])).fetchone()
            self.assertIsNone(other)
        statements = (
            "UPDATE documents.public_workspace_lifecycle SET state='QUARANTINED' WHERE principal_id=%s AND workspace_id=%s",
            'DELETE FROM documents.public_workspace_lifecycle WHERE principal_id=%s AND workspace_id=%s',
            "INSERT INTO documents.public_workspace_lifecycle(principal_id,workspace_id,launch_id,incarnation,expires_at_ms,policy_version,state) VALUES(%s,%s,'no-launch','no-incarnation',1,'test','READY')",
        )
        for statement in statements:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with self.a.transaction() as connection:
                    connection.execute(statement, (self.scopes[0]['principalId'], self.scopes[0]['workspaceId']))
        self.assertEqual(lifecycle.registered(self.scopes[0])['state'], 'READY')

    def test_private_workspace_cannot_be_registered_or_purged(self):
        """A collision cannot turn existing private control data into cleanup authority."""
        private_scope = {'version': 1, 'principalId': str(uuid.uuid4()), 'workspaceId': str(uuid.uuid4()),
                         'logicalLaunchId': str(uuid.uuid4())}
        private_store = Store(private_scope)
        self.assertEqual(private_store.initialize('document-v1')['status'], 'READY')
        args = {'policyVersion': 'document-v1', 'expiresAtEpochMillis': int(time.time() * 1000) + 1800000,
                'incarnation': self.incarnation}
        with self.assertRaises(ValueError):
            lifecycle.initialize(private_scope, args, Store)
        with self.assertRaises(ValueError):
            lifecycle.purge(private_scope, {'incarnation': self.incarnation})
        self.assertEqual(private_store.initialize('document-v1')['status'], 'READY')


if __name__ == '__main__':
    unittest.main()
