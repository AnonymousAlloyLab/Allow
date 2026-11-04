"""Finite checks for explicit-empty cleanup and terminal resource evidence."""
import unittest
from unittest.mock import patch

import containment as subject


class CleanupCaptureTests(unittest.TestCase):
    """Never convert missing empty observation, live owners or bus failures into successful cleanup."""

    def test_removed_scope_requires_positive_empty(self):
        self.assertFalse(subject.removed_after_empty(False, True, 5, {'LoadState': 'not-found'}))

    def test_removed_scope_requires_all_owners_absent(self):
        self.assertFalse(subject.removed_after_empty(True, False, 5, {'LoadState': 'not-found'}))

    def test_other_command_error_not_converted(self):
        self.assertFalse(subject.removed_after_empty(True, True, 1, {'LoadState': 'not-found'}))

    def test_still_loaded_scope_not_converted(self):
        self.assertFalse(subject.removed_after_empty(True, True, 5, {'LoadState': 'loaded'}))

    def test_positive_empty_then_removed_scope_recognized(self):
        self.assertTrue(subject.removed_after_empty(True, True, 5, {'LoadState': 'not-found'}))

    def test_wrong_invocation_rejected_before_cleanup(self):
        manifest = {'unit': 'unique.scope', 'input_root_sha256': 'bound'}
        state = {'Description': 'allow-fresh:bound', 'InvocationID': 'replacement'}
        with patch.object(subject, 'unit_properties', return_value=state):
            with self.assertRaisesRegex(ValueError, 'incarnation_changed'):
                subject.stop(manifest, [], 'original')

    def test_bus_failure_not_converted(self):
        with patch.object(subject, 'unit_properties', side_effect=RuntimeError('bus unavailable')):
            with self.assertRaises(RuntimeError):
                subject.stop({'unit': 'unique.scope'}, [], 'original')

    def test_terminal_counter_failure_remains_incomplete(self):
        with patch.object(subject, 'descriptor_text', side_effect=OSError('deleted group')):
            with self.assertRaises(OSError):
                subject.terminal_resources({'memory.peak': 3})


if __name__ == '__main__':
    unittest.main()
