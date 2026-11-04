#!/usr/bin/env python3
"""Check fail-closed ownership/path safeguards without copying production or starting databases."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

import experiment


class OwnershipTests(unittest.TestCase):
    """Exercise actual owned process incarnations and reject stale authority before signaling."""
    @classmethod
    def setUpClass(cls):
        """Refuse an incapable interpreter before creating even a harmless fixture child."""
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise RuntimeError('managed_python_with_pidfd_required')

    def test_active_root_rejected(self):
        """Never permit execution against the active repository root."""
        with self.assertRaisesRegex(ValueError, 'isolated_root_required'):
            experiment.check_installation({'copied_root': str(experiment.ROOT)})

    def test_wrong_temporary_prefix_rejected(self):
        """Do not treat unrelated temporary directories as owned installations."""
        with self.assertRaisesRegex(ValueError, 'isolated_root_required'):
            experiment.check_installation({'copied_root': '/tmp/not-allow-runtime'})

    def test_stale_identity_never_signals(self):
        """A fabricated start tick cannot authorize a signal to even an owned live child."""
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])
        identity = experiment.process_identity(child.pid)
        try:
            stale = dict(identity, start=str(int(identity['start'])+1))
            with self.assertRaisesRegex(RuntimeError, 'process_identity_changed_before_pidfd'):
                experiment.signal_owned(stale, signal.SIGTERM)
            self.assertIsNone(child.poll())
        finally:
            experiment.signal_owned(identity, signal.SIGTERM)
            self.assertEqual(child.wait(timeout=3), -signal.SIGTERM)

    def test_actual_pidfd_terminates_owned_child(self):
        """Verify the available kernel pidfd route on one newly created harmless child."""
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])
        identity = experiment.process_identity(child.pid)
        experiment.signal_owned(identity, signal.SIGTERM)
        self.assertEqual(child.wait(timeout=3), -signal.SIGTERM)
        self.assertIsNone(experiment.process_identity(child.pid))

    def test_environment_discards_inherited_routes(self):
        """Canonical copied modules/runtime replace ambient authority rather than inheriting it."""
        from unittest.mock import patch
        with patch.dict(os.environ, {'PGHOST': 'forbidden', 'ALLOW_TOKEN': 'forbidden', 'PYTHONPATH': 'forbidden'}):
            environment = experiment.clean_environment(Path('/tmp/allow-cc-test'))
        self.assertNotIn('PGHOST', environment)
        self.assertNotIn('ALLOW_TOKEN', environment)
        self.assertEqual(environment['PYTHONPATH'], '/tmp/allow-cc-test/retrieval')

    def test_copied_gate_helper_import(self):
        """The shallow copied .gate layout must load pidfd helpers without resolving active ROOT."""
        import runpy
        with tempfile.TemporaryDirectory(prefix='allow-cc-helper-') as directory:
            root = Path(directory)
            gate = root/'.gate'
            gate.mkdir()
            source = gate/'experiment.py'
            source.write_bytes(Path(experiment.__file__).read_bytes())
            loaded = runpy.run_path(str(source))
            self.assertEqual(loaded['ROOT'], root)


if __name__ == '__main__':
    unittest.main()
