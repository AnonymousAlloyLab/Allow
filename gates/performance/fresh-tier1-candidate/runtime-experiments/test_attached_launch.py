"""Finite fault checks for blocked attachment ownership and cleanup paths."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import attached_launch as subject
from harness_common import process_identity, read_private, write_private


class AttachmentTests(unittest.TestCase):
    """Exercise failures before release without creating any service or JVM."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-ft1-attach-test-')
        self.root = Path(self.temporary.name)
        (self.root/'.gate').mkdir(mode=0o700)
        self.manifest = {'copied_root': str(self.root), 'unit': 'test-owned.service', 'input_root_sha256': 'frozen'}

    def tearDown(self):
        self.temporary.cleanup()

    def test_pipe_failure_still_cleans_anchor(self):
        with patch.object(subject.containment, 'launch', return_value={'InvocationID': 'owned'}), \
             patch.object(subject.os, 'pipe2', side_effect=OSError('finite injected fault')), \
             patch.object(subject, 'failed_launch_cleanup') as cleanup:
            with self.assertRaises(OSError):
                subject.launch(self.manifest, '/usr/bin/true', [], 10)
            cleanup.assert_called_once_with(self.manifest, {'InvocationID': 'owned'}, None)

    def test_partial_launch_failure_attempts_reconciliation(self):
        with patch.object(subject.containment, 'launch', side_effect=RuntimeError('partial')), \
             patch.object(subject, 'failed_launch_cleanup') as cleanup:
            with self.assertRaises(RuntimeError):
                subject.launch(self.manifest, '/usr/bin/true', [], 10)
            cleanup.assert_called_once_with(self.manifest, None, None)

    def test_child_reap_timeout_does_not_skip_unit_stop(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('owned', 3)
        with patch.object(subject, 'reconcile_start', return_value=({'InvocationID': 'owned'}, {'pid': 42})), \
             patch.object(subject.containment, 'stop', return_value={'status': 'PASS'}) as stop:
            with self.assertRaises(RuntimeError):
                subject.failed_launch_cleanup(self.manifest, None, child)
            stop.assert_called_once()
        report = read_private(self.root/'.gate/failed-attach-cleanup.json')
        self.assertEqual(report['status'], 'UNKNOWN')
        self.assertFalse(report['child_reaped'])

    def test_name_only_cleanup_rejected(self):
        state = {'LoadState': 'loaded', 'Description': 'some-other-unit', 'InvocationID': 'a'*32}
        with patch.object(subject.containment, 'unit_properties', return_value=state):
            with self.assertRaisesRegex(ValueError, 'ownership_unproven'):
                subject.reconcile_start(self.manifest, None)

    def test_disappeared_unit_is_not_empty_group_evidence(self):
        with patch.object(subject.containment, 'unit_properties', return_value={'LoadState': 'not-found'}):
            with self.assertRaisesRegex(ValueError, 'without_empty_witness'):
                subject.reconcile_start(self.manifest, {'InvocationID': 'known'})

    def test_pipe_eof_never_executes_payload(self):
        read_end, write_end = os.pipe2(os.O_CLOEXEC)
        os.close(write_end)
        parent = process_identity(os.getpid())
        marker = self.root/'forbidden-payload'
        argv = [sys.executable, '-B', str(Path(subject.__file__)), 'gated', '--root', str(self.root),
                '--fd', str(read_end), '--parent-pid', str(parent['pid']), '--parent-start', parent['start_ticks'],
                '--', sys.executable, '-c', 'from pathlib import Path; Path('+repr(str(marker))+').touch()']
        try:
            result = subprocess.run(argv, pass_fds=(read_end,), capture_output=True, timeout=5)
        finally:
            os.close(read_end)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.root/'.gate/gated.json').exists())
        self.assertFalse(marker.exists())

    def test_changed_parent_never_waits_or_executes(self):
        parent = process_identity(os.getpid())
        parent['start_ticks'] = '-1'
        with self.assertRaisesRegex(RuntimeError, 'parent_absent'):
            subject.gated(self.root, -1, parent, '/usr/bin/true', [])


if __name__ == '__main__':
    unittest.main()
