"""Mocked closed anonymous scope/lifecycle regressions; no live SQL or credentials."""
import copy
import uuid
import unittest
from unittest.mock import MagicMock, patch
from allow_documents import cli, lifecycle, wire
from allow_documents.store import Store, RESERVATION


def scope():
    """Allocate a canonical private test identity without touching runtime metadata."""
    return {'version': 1, 'principalId': str(uuid.uuid4()), 'workspaceId': str(uuid.uuid4()),
            'logicalLaunchId': str(uuid.uuid4())}


def registration(identity, incarnation=None):
    """Represent one complete trusted registry row."""
    return {'principal_id': identity['principalId'], 'workspace_id': identity['workspaceId'],
            'launch_id': identity['logicalLaunchId'], 'incarnation': incarnation or str(uuid.uuid4()),
            'expires_at_ms': 1800001, 'policy_version': 'test-policy', 'state': 'READY'}


def mock_database():
    """Provide a context-managed fake canonical connection and query cursor."""
    connection = MagicMock()
    cursor = connection.execute.return_value
    connector = MagicMock()
    connector.return_value.__enter__.return_value = connection
    return connector, connection, cursor


class ScopeProtocolTests(unittest.TestCase):
    """Private v1 remains unchanged; v2 cannot select private policy/identity paths."""
    def test_scope_closed_canonical_and_not_path(self):
        """Only exact integer version and canonical UUID scope fields are accepted."""
        good = scope()
        self.assertEqual(lifecycle.validate_scope(good), good)
        for bad in (good | {'version': True}, good | {'workspaceId': '../../private'},
                    good | {'role': 'admin'}, good | {'principalId': good['principalId'].upper()}):
            with self.assertRaises(ValueError):
                lifecycle.validate_scope(bad)

    def test_v2_listing_has_server_scope_and_smaller_quota(self):
        """The scoped bridge constructs only a registered public Store instance."""
        identity = scope()
        frame = {'protocol': 2, 'requestId': str(uuid.uuid4()), 'operation': 'list', 'args': {}, 'scope': identity}
        with patch.object(cli.lifecycle, 'registered') as registered, patch.object(cli, 'Store') as store:
            store.return_value.listing.return_value = {'documents': []}
            self.assertEqual(cli.dispatch(frame), {'documents': []})
            registered.assert_called_once_with(identity)
            store.assert_called_once_with(identity, public=True)

    def test_private_v1_and_lifecycle_protocol_separation(self):
        """v1 cannot smuggle a scope; v2 cannot modify installed/private policy."""
        frame = {'protocol': 1, 'requestId': str(uuid.uuid4()), 'operation': 'list', 'args': {}}
        with patch.object(cli, 'Store') as store:
            cli.dispatch(frame)
            store.assert_called_once_with()
        with self.assertRaises(ValueError):
            cli.dispatch(frame | {'scope': scope()})
        for operation, args in (('init', {'policyVersion': 'x'}),
                                ('policy', {'expectedPolicyVersion': 'x', 'policyVersion': 'y'})):
            with self.assertRaises(ValueError):
                cli.dispatch(frame | {'protocol': 2, 'scope': scope(), 'operation': operation, 'args': args})


class LifecycleTests(unittest.TestCase):
    """Provenance, occupied-slot bounds and cleanup are enforced before admin mutation."""
    def test_private_collision_never_marked_public(self):
        """An existing unregistered workspace refuses enrollment before INSERT."""
        identity = scope()
        args = {'policyVersion': 'test-policy', 'expiresAtEpochMillis': 1800001, 'incarnation': str(uuid.uuid4())}
        connector, connection, cursor = mock_database()
        cursor.fetchone.side_effect = [None, {'exists': 1}]
        with patch.object(lifecycle, 'connect', connector), self.assertRaisesRegex(ValueError, 'cannot_become_public'):
            lifecycle.register(identity, args)
        self.assertFalse(any('INSERT' in call.args[0] for call in connection.execute.call_args_list))
        self.assertTrue(all(call.kwargs.get('admin') is True for call in connector.call_args_list))

    def test_all_four_registry_slots_including_uncertain_count(self):
        """Count all rows, without filtering out provisioning or quarantine."""
        identity = scope()
        args = {'policyVersion': 'test-policy', 'expiresAtEpochMillis': 1800001, 'incarnation': str(uuid.uuid4())}
        connector, connection, cursor = mock_database()
        cursor.fetchone.side_effect = [None, None, {'occupied': 4}]
        with patch.object(lifecycle, 'connect', connector), self.assertRaisesRegex(ValueError, 'capacity'):
            lifecycle.register(identity, args)
        count = [call.args[0] for call in connection.execute.call_args_list if 'count(*)' in call.args[0]]
        self.assertEqual(len(count), 1)
        self.assertNotIn('WHERE', count[0])
        self.assertFalse(any('INSERT' in call.args[0] for call in connection.execute.call_args_list))

    def test_initialization_failure_retains_committed_provenance(self):
        """A failed Store.initialize never erases the already committed registry slot."""
        identity = scope()
        args = {'policyVersion': 'test-policy', 'expiresAtEpochMillis': 1800001, 'incarnation': str(uuid.uuid4())}
        factory = MagicMock()
        factory.return_value.initialize.side_effect = RuntimeError('unknown initialization outcome')
        with patch.object(lifecycle, 'register') as register, patch.object(lifecycle, 'connect') as connect:
            with self.assertRaisesRegex(RuntimeError, 'unknown initialization'):
                lifecycle.initialize(identity, args, factory)
            register.assert_called_once_with(identity, args)
            factory.assert_called_once_with(identity, public=True)
            connect.assert_not_called()

    def test_listing_overflow_fails_instead_of_hiding_occupied_slots(self):
        """Five registry rows cannot silently become a four-entry report."""
        connector, connection, cursor = mock_database()
        cursor.fetchall.return_value = [{}] * 5
        with patch.object(lifecycle, 'connect', connector), self.assertRaisesRegex(ValueError, 'over_capacity'):
            lifecycle.listing()
        self.assertIn('LIMIT 5', connection.execute.call_args.args[0])

    def test_private_or_wrong_incarnation_purge_refused(self):
        """Admin cleanup cannot target an unregistered private workspace or a new owner."""
        identity = scope()
        connector, connection, cursor = mock_database()
        cursor.fetchone.side_effect = [None, {'exists': 1}]
        with patch.object(lifecycle, 'connect', connector), self.assertRaisesRegex(ValueError, 'cannot_be_purged'):
            lifecycle.purge_transaction(identity, str(uuid.uuid4()))
        self.assertFalse(any('DELETE' in call.args[0] for call in connection.execute.call_args_list))
        cursor.fetchone.side_effect = [registration(identity)]
        with patch.object(lifecycle, 'connect', connector), self.assertRaisesRegex(ValueError, 'incarnation'):
            lifecycle.purge_transaction(identity, str(uuid.uuid4()))

    def test_purge_live_owner_refuses_delete(self):
        """CANCELLED presentation or elapsed time never replaces actual owner drain."""
        identity = scope()
        row = registration(identity)
        connector, connection, cursor = mock_database()
        cursor.fetchone.return_value = row
        cursor.fetchall.return_value = [{'owner_pid': 123, 'owner_start': 'old-start'}]
        with patch.object(lifecycle, 'connect', connector), patch.object(lifecycle.identity, 'alive', return_value=True):
            with self.assertRaisesRegex(ValueError, 'owner_still_alive'):
                lifecycle.purge_transaction(identity, row['incarnation'])
        self.assertFalse(any('DELETE' in call.args[0] for call in connection.execute.call_args_list))

    def test_context_uncertainty_quarantines_and_preserves_failure(self):
        """A fresh control failure cannot be converted into successful deletion."""
        identity = scope()
        incarnation = str(uuid.uuid4())
        with patch.object(lifecycle, 'require_clean_context', side_effect=RuntimeError('unknown context')), \
                patch.object(lifecycle, 'quarantine') as quarantine, patch.object(lifecycle, 'purge_transaction') as purge:
            with self.assertRaisesRegex(RuntimeError, 'unknown context'):
                lifecycle.purge(identity, {'incarnation': incarnation})
            quarantine.assert_called_once_with(identity, incarnation)
            purge.assert_not_called()

    def test_context_status_requires_ready_boolean_idle_lane(self):
        """Control status must be current READY and exactly false contextOccupied."""
        good = {'protocol': 1, 'status': 'READY', 'contextOccupied': False, 'observerOccupied': True}
        with patch.object(lifecycle.context_lease, 'exchange', return_value=good) as exchange:
            lifecycle.require_clean_context()
            exchange.assert_called_once_with({'protocol': 1, 'operation': 'status'})
        for bad in (good | {'status': 'DEGRADED'}, good | {'contextOccupied': True},
                    good | {'contextOccupied': 0}, good | {'observerOccupied': None}):
            with patch.object(lifecycle.context_lease, 'exchange', return_value=bad), self.assertRaises(ValueError):
                lifecycle.require_clean_context()

    def test_purge_all_deletes_explicit_scope_and_atomic_connection(self):
        """The fixed dependency order has no unscoped admin DELETE or app connection."""
        identity = scope()
        row = registration(identity)
        connector, connection, cursor = mock_database()
        cursor.fetchone.return_value = row
        cursor.fetchall.return_value = []
        with patch.object(lifecycle, 'connect', connector), patch.object(lifecycle, 'require_clean_context') as context:
            self.assertEqual(lifecycle.purge_transaction(identity, row['incarnation']), {'status': 'PURGED'})
            context.assert_called_once_with()
        deletes = [call for call in connection.execute.call_args_list if call.args[0].startswith('DELETE')]
        self.assertEqual(len(deletes), 8)
        for call in deletes:
            self.assertIn('WHERE principal_id=%s AND workspace_id=%s', call.args[0])
            self.assertEqual(call.args[1], (identity['principalId'], identity['workspaceId']))
        connector.assert_called_once_with(admin=True, client='allow-migration', row_factory=lifecycle.dict_row)


class TransactionFenceTests(unittest.TestCase):
    """A scoped transaction cannot resurrect deleted provenance or snapshot before its fence."""
    def test_public_transaction_locks_before_first_select(self):
        """Implicit snapshots cannot precede the registry ACCESS SHARE table lock."""
        from allow_documents import store as store_module
        identity = scope()
        connector, connection, cursor = mock_database()
        cursor.fetchone.return_value = {'launch_id': identity['logicalLaunchId'], 'state': 'READY'}
        with patch.object(store_module, 'connect', connector):
            with Store(identity, public=True).transaction():
                pass
        statements = [call.args[0] for call in connection.execute.call_args_list]
        lock = statements.index('LOCK TABLE documents.public_workspace_lifecycle IN ACCESS SHARE MODE')
        self.assertTrue(all(index > lock for index, sql in enumerate(statements) if sql.startswith('SELECT')))
        self.assertIn('SELECT launch_id,state', statements[-1])

    def test_late_initializer_after_purge_cannot_resurrect_workspace(self):
        """A missing registry row in the same transaction rejects before any INSERT."""
        from allow_documents import store as store_module
        connector, connection, cursor = mock_database()
        cursor.fetchone.return_value = None
        with patch.object(store_module, 'connect', connector), self.assertRaisesRegex(ValueError, 'scope_not_ready'):
            Store(scope(), public=True).initialize('test-policy')
        self.assertFalse(any(call.args[0].startswith('INSERT') for call in connection.execute.call_args_list))

    def test_only_initializer_accepts_provisioning(self):
        """Normal operations cannot run in a registered but unfinished workspace."""
        identity = scope()
        connector, connection, cursor = mock_database()
        cursor.fetchone.return_value = {'launch_id': identity['logicalLaunchId'], 'state': 'PROVISIONING'}
        store = Store(identity, public=True)
        with self.assertRaises(ValueError):
            store._public_guard(connection)
        store._public_guard(connection, initializing=True)

    def test_purge_requires_access_exclusive_registry_lock(self):
        """The purge lock conflicts with every scoped read/init transaction fence."""
        identity = scope()
        row = registration(identity)
        connector, connection, cursor = mock_database()
        cursor.fetchone.return_value = row
        cursor.fetchall.return_value = []
        with patch.object(lifecycle, 'connect', connector), patch.object(lifecycle, 'require_clean_context'):
            lifecycle.purge_transaction(identity, row['incarnation'])
        statements = [call.args[0] for call in connection.execute.call_args_list]
        self.assertIn('LOCK TABLE documents.public_workspace_lifecycle IN ACCESS EXCLUSIVE MODE', statements)
        lock = statements.index('LOCK TABLE documents.public_workspace_lifecycle IN ACCESS EXCLUSIVE MODE')
        self.assertTrue(all(index > lock for index, sql in enumerate(statements) if sql.startswith('DELETE')))


class QuotaTests(unittest.TestCase):
    """Public SQL admission includes every pending reservation within smaller budgets."""
    def test_public_caps_and_private_limits_unchanged(self):
        """Each exceeded public dimension rejects before SQL writes; private admits it."""
        identity = scope()
        key = 'K' * 16
        req = ('CREATE', key, 'POST', '/api/v1/documents', wire.encode({'idempotencyKey': key, 'title': 'Test'}))
        args = {'operation': 'CREATE', 'expectedRevision': None, 'ownerPid': 12, 'ownerStartTicks': '34'}
        base = {'document_count': 0, 'reserved_documents': 0, 'revision_count': 0, 'reserved_revisions': 0,
                'receipt_count': 0, 'reserved_receipts': 0, 'accounted_bytes': 0, 'reserved_bytes': 0,
                'policy_version': 'test-policy'}
        for excess in ({'document_count': 2, 'reserved_documents': 1},
                       {'revision_count': 127, 'reserved_revisions': 1},
                       {'receipt_count': 255, 'reserved_receipts': 1},
                       {'accounted_bytes': 12582912, 'reserved_bytes': 1}):
            workspace = base | excess
            connection = MagicMock()
            result = Store(identity, public=True).reserve(connection, args, req, workspace)
            self.assertEqual(result['status'], 'CAPACITY_PRE_ADMISSION')
            connection.execute.assert_not_called()
            private = Store(identity).reserve(connection, args, req, workspace)
            self.assertEqual(private['status'], 'ADMITTED')
        self.assertEqual(RESERVATION, 4194304)


if __name__ == '__main__':
    unittest.main()
