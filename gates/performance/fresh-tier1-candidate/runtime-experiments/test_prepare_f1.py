"""Offline negative checks for the copied F1 recipe; no services or workloads."""
from pathlib import Path
import tempfile
import unittest
import prepare_f1
from harness_common import record


class RecipeBoundaryTests(unittest.TestCase):
    """Prevent extra source changes, hidden files and filesystem aliases."""

    def test_exact_one_constant_patch(self):
        source = (prepare_f1.BASELINE + '\nnew DocumentWorker(ADVISORY_PROFILE);\n').encode()
        patched = prepare_f1.patch_source(source)
        self.assertEqual(patched, source.replace(prepare_f1.BASELINE.encode(), prepare_f1.TIER1.encode()))
        self.assertEqual(patched.replace(prepare_f1.TIER1.encode(), prepare_f1.BASELINE.encode()), source)

    def test_already_enabled_duplicate_or_unrelated_source_denied(self):
        sources = [prepare_f1.TIER1, prepare_f1.BASELINE * 2, 'new DocumentWorker();',
                   prepare_f1.BASELINE + '\nnew DocumentWorker(untrusted);']
        for source in sources:
            with self.subTest(source=source), self.assertRaises(ValueError):
                prepare_f1.patch_source(source.encode())

    def test_unregistered_gate_file_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'.gate').mkdir()
            (root/'.gate/extra.py').write_text('unregistered')
            manifest = {'files': [], 'tooling': {'aliases': [{'alias': '.tools/retrieval-venv', 'resolved': '/missing'}]}}
            with self.assertRaisesRegex(ValueError, 'surplus_or_missing'):
                prepare_f1.declared_tree(root, manifest)

    def test_unregistered_symlink_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'unexpected').symlink_to('/tmp')
            manifest = {'files': [], 'tooling': {'aliases': [{'alias': '.tools/retrieval-venv', 'resolved': '/missing'}]}}
            with self.assertRaisesRegex(ValueError, 'alias_denied'):
                prepare_f1.declared_tree(root, manifest)

    def test_surplus_delta_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            base, output = Path(temporary)/'baseline', Path(temporary)/'output'
            base.mkdir()
            output.mkdir()
            for name in (prepare_f1.SOURCE, prepare_f1.CLASS, 'extra.txt'):
                for root in (base, output):
                    (root/name).parent.mkdir(parents=True, exist_ok=True)
                    (root/name).write_text('before' if root == base else 'after')
            manifest = {'files': [record(base/name, base) for name in (prepare_f1.SOURCE, prepare_f1.CLASS, 'extra.txt')]}
            with self.assertRaisesRegex(ValueError, 'unexpected_f1_delta'):
                prepare_f1.verify_delta(base, output, manifest)


if __name__ == '__main__':
    unittest.main()
