"""Offline tests for AI runtime attestation and deployment defaults."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ai_runtime_tests', ROOT / 'services/ai/runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    """Exercise exact runtime files and forbidden startup hooks without pip."""

    def setUp(self):
        """Create a tiny private fixture with a valid attestation."""
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / '.tools').mkdir(mode=0o700)
        self.site = self.root / '.tools/ai-venv/lib/python3.12/site-packages'
        self.site.mkdir(parents=True, mode=0o700)
        for path in (self.site, *self.site.parents):
            if path == self.root / '.tools':
                break
            path.chmod(0o700)
        (self.site / 'fixture.py').write_text('value = 1\n')
        (self.site / 'fixture.py').chmod(0o600)
        (self.root / '.tools/ai-venv/pyvenv.cfg').write_text('include-system-site-packages = false\n')
        (self.root / '.tools/ai-venv/pyvenv.cfg').chmod(0o600)
        (self.root / 'retrieval').mkdir(mode=0o700)
        lock = self.root / 'retrieval/requirements-ai.lock'
        lock.write_text('fixture\n')
        data = {'schema': 1, 'lock_sha256': hashlib.sha256(lock.read_bytes()).hexdigest(),
                'files': runtime.inventory(self.root / '.tools/ai-venv')}
        self.record = self.root / '.tools/ai-venv.inventory.json'
        self.record.write_text(json.dumps(data))
        self.record.chmod(0o600)

    def tearDown(self):
        """Remove this private fixture."""
        self.temp.cleanup()

    def test_exact_inventory_and_changed_code(self):
        """One altered dependency byte denies execution."""
        self.assertEqual(runtime.verify(self.root), self.site)
        (self.site / 'fixture.py').write_text('value = 2\n')
        with self.assertRaises(ValueError):
            runtime.verify(self.root)

    def test_startup_hook_and_unknown_file_denied(self):
        """An unlisted startup hook cannot reach the Python interpreter."""
        (self.site / 'unknown.pth').write_text('import os\n')
        with self.assertRaises(ValueError):
            runtime.verify(self.root)

    def test_changed_lock_denied(self):
        """The runtime is bound to the packaged lock bytes."""
        (self.root / 'retrieval/requirements-ai.lock').write_text('different\n')
        with self.assertRaises(ValueError):
            runtime.verify(self.root)


class EvidenceTests(unittest.TestCase):
    """Prove packaged finite reports bind their declared inputs."""

    def test_report_hashes_must_match(self):
        """Reject a report whose packaged proof input was altered."""
        package_spec = importlib.util.spec_from_file_location('package_test', ROOT / 'scripts/package_iis.py')
        package = importlib.util.module_from_spec(package_spec)
        package_spec.loader.exec_module(package)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / 'source'
            source.write_text('proof input')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            members = {'source': source}
            for gate in ('ai-native-v1', 'ai-langgraph-v1', 'ai-system-v1'):
                report = directory / gate
                report.write_text(json.dumps({'sha256': {'source': digest}}))
                members['gates/' + gate + '/formal-report.json'] = report
            package.verify_ai_evidence(members)
            source.write_text('altered')
            with self.assertRaises(ValueError):
                package.verify_ai_evidence(members)


if __name__ == '__main__':
    unittest.main()
