"""Finite rejection checks for the owned scope's release protocol."""
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import Mock, patch

import scope_launch as subject
from harness_common import process_identity, write_private


class ScopeReleaseTests(unittest.TestCase):
    """Reject changed owner/invocation/placement without executing any application."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-ft1-scope-test-')
        self.root = Path(self.temporary.name)
        (self.root/'.gate').mkdir(mode=0o700)
        self.identity = process_identity(os.getpid())
        write_private(self.root/'.gate/scope-intent.json', {'controller': self.identity, 'input_root_sha256': 'bound'})
        write_private(self.root/'.gate/unit-invocation.json', {'invocation_id': 'owned', 'control_group': '/owned'})

    def tearDown(self):
        self.temporary.cleanup()

    def rejected_release(self, release, group='/owned', affinity={0, 1, 2, 3}):
        write_private(self.root/'.gate/scope-release.json', release)
        library = Mock()
        library.prctl.return_value = 0
        with patch.object(subject.ctypes, 'CDLL', return_value=library), \
             patch.object(subject.containment, 'pid_group', return_value=group), \
             patch.object(subject.os, 'sched_getaffinity', return_value=affinity), \
             patch.object(subject.os, 'execve') as execute:
            with self.assertRaises(ValueError):
                subject.gated(self.root, '/usr/bin/true', [])
            execute.assert_not_called()

    def test_wrong_root_never_releases(self):
        self.rejected_release({'owner': self.identity, 'input_root_sha256': 'other', 'invocation_id': 'owned'})

    def test_wrong_invocation_never_releases(self):
        self.rejected_release({'owner': self.identity, 'input_root_sha256': 'bound', 'invocation_id': 'other'})

    def test_changed_membership_never_releases(self):
        self.rejected_release({'owner': self.identity, 'input_root_sha256': 'bound', 'invocation_id': 'owned'}, group='/outside')

    def test_changed_affinity_never_releases(self):
        self.rejected_release({'owner': self.identity, 'input_root_sha256': 'bound', 'invocation_id': 'owned'}, affinity={0})

    def test_delegation_rejected(self):
        state = {'Description': 'allow-fresh:bound', 'InvocationID': 'owned', 'KillMode': 'control-group', 'Delegate': 'yes'}
        with patch.object(subject.containment, 'unit_properties', return_value=state):
            with self.assertRaisesRegex(ValueError, 'delegation_not_permitted'):
                subject.unit_state({'unit': 'unique.scope', 'input_root_sha256': 'bound'})

    def test_timed_out_launcher_is_killed_and_reaped(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('owned', 5), 0]
        with patch.object(subject, 'read_private', return_value={'main_identity': self.identity, 'invocation_id': 'owned'}), \
             patch.object(subject.containment, 'stop', return_value={'status': 'PASS'}):
            subject.failed_cleanup(self.root, {'unit': 'owned.scope'}, child, None)
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)


if __name__ == '__main__':
    unittest.main()
