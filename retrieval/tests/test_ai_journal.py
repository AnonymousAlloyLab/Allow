"""Finite crash/replay/privacy checks for the isolated filesystem budget ledger."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from allow_ai.journal import DispatchJournal
from allow_ai.provider import ProviderFailure


class JournalTests(unittest.TestCase):
    """Exercise persistent consumption independently of replayable graph state."""
    def setUp(self):
        """Create a fresh private operator-owned temporary directory."""
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.path = self.directory / 'dispatch.json'

    def tearDown(self):
        """Remove synthetic accounting data after each isolated test."""
        self.temp.cleanup()

    def journal(self, path=None):
        """Construct an explicitly external ledger."""
        return DispatchJournal(path or self.path, root=Path.cwd())

    def test_reserve_two_calls_and_global_ceiling(self):
        """Persist both reservations before calls, with no refunds on finish."""
        with self.journal() as ledger:
            ledger.claim('operation', 1)
            state = json.loads(self.path.read_text())
            self.assertEqual(state['operations']['operation'][0]['reserved'], 50000)
            ledger.finish('operation', 1, 'COMPLETED')
            ledger.claim('operation', 2)
            ledger.finish('operation', 2, 'COMPLETED')
            with self.assertRaises(ProviderFailure) as caught:
                ledger.claim('other-operation', 1)
            self.assertEqual(caught.exception.code, 'BUDGET_EXHAUSTED')
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        self.assertNotIn('source', self.path.read_text())

    def test_crash_unknown_and_reopen_cannot_repair_or_replay(self):
        """An unfinished durable dispatch remains consumed on restart."""
        with self.journal() as ledger:
            ledger.claim('operation', 1)
        with self.journal() as ledger:
            for attempt in (1, 2):
                with self.assertRaises(ProviderFailure) as caught:
                    ledger.claim('operation', attempt)
                self.assertEqual(caught.exception.code, 'DISPATCH_REPLAY')
            ledger.claim('other', 1)
            with self.assertRaises(ProviderFailure):
                ledger.claim('third', 1)

    def test_unknown_first_call_cannot_loop(self):
        """Even a live graph cannot claim a repair for uncertain dispatch."""
        with self.journal() as ledger:
            ledger.claim('operation', 1)
            ledger.finish('operation', 1, 'OUTCOME_UNKNOWN')
            with self.assertRaises(ProviderFailure):
                ledger.claim('operation', 2)

    def test_concurrent_lock_and_outside_context(self):
        """One exclusive lock covers all runner/network activity."""
        with self.journal() as ledger:
            with self.assertRaises(ProviderFailure):
                with self.journal():
                    self.fail('Concurrent ledger ownership')
            ledger.claim('operation', 1)
        with self.assertRaises(ProviderFailure):
            ledger.claim('outside', 1)

    def test_missing_after_initialization_does_not_reset(self):
        """Existing lock plus missing state is ambiguous and fails closed."""
        with self.journal():
            pass
        self.path.unlink()
        with self.assertRaises(ProviderFailure):
            with self.journal():
                self.fail('Deleted ledger reset')

    def test_malformed_duplicate_oversized_and_insecure_state(self):
        """Deny corrupt accounting rather than repairing or resetting it."""
        with self.journal():
            pass
        for raw in (b'{}', b'{"schema":1,"schema":1,"operations":{}}', b'X' * 1048577):
            self.path.write_bytes(raw)
            with self.assertRaises(ProviderFailure):
                with self.journal():
                    self.fail('Malformed ledger admitted')
        self.path.write_text('{"schema":1,"operations":{}}')
        self.path.chmod(0o644)
        with self.assertRaises(ProviderFailure):
            with self.journal():
                self.fail('Insecure ledger admitted')

    def test_symlink_ancestor_file_and_hardlink_denied(self):
        """Do not follow linked operator paths or accept shared ledger inodes."""
        linked = self.directory / 'linked'
        linked.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ProviderFailure):
            with self.journal(linked / 'ledger'):
                self.fail('Linked parent admitted')
        target = self.directory / 'target'
        target.write_text('{}')
        target.chmod(0o600)
        self.path.symlink_to(target)
        with self.assertRaises(ProviderFailure):
            with self.journal():
                self.fail('Linked ledger admitted')
        self.path.unlink()
        os.link(target, self.path)
        with self.assertRaises(ProviderFailure):
            with self.journal():
                self.fail('Hardlinked ledger admitted')

    def test_project_path_and_open_directory_denied(self):
        """Require a private parent outside the project trust boundary."""
        with self.assertRaises(ProviderFailure):
            with DispatchJournal(self.path, root=self.directory):
                self.fail('Project ledger admitted')
        self.directory.chmod(0o755)
        with self.assertRaises(ProviderFailure):
            with self.journal():
                self.fail('Open ledger directory admitted')

    def test_failed_fsync_poisoning_and_no_new_dispatch(self):
        """Ambiguous durable write failure prevents all subsequent admissions."""
        with self.journal() as ledger:
            with patch('allow_ai.journal.os.fsync', side_effect=OSError('private failure')):
                with self.assertRaises(ProviderFailure):
                    ledger.claim('operation', 1)
            with self.assertRaises(ProviderFailure):
                ledger.claim('another', 1)

    def test_closed_status_and_attempt_sequence(self):
        """Reject arbitrary journal content and graph-supplied attempt jumps."""
        with self.journal() as ledger:
            for operation, attempt in (('operation', 2), ('operation', True), ('private/path', 1)):
                with self.assertRaises(ProviderFailure):
                    ledger.claim(operation, attempt)
            ledger.claim('operation', 1)
            with self.assertRaises(ProviderFailure):
                ledger.finish('operation', 1, 'private response content')
