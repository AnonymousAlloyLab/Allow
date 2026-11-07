"""Offline intake deployment checks; no secrets, email or Google calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    """Load one local source module for the isolated unit seam."""
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


TRUST = module('intake_trust_test', ROOT / 'deploy/linux/trust.py')
PACKAGE = module('intake_package_test', ROOT / 'scripts/package_iis.py')


class IntakeDeploymentTests(unittest.TestCase):
    """Exercise path protection and binding tamper failures."""

    def test_disabled_and_external_private_path(self):
        """Absence stays disabled; a private external path is accepted without parsing secrets."""
        TRUST.validate_access_request_config({})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text('{}')
            path.chmod(0o600)
            TRUST.validate_access_request_config({'access_request_config': str(path)})
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                TRUST.validate_access_request_config({'access_request_config': str(path)})

    def test_missing_relative_internal_link_and_public_parent(self):
        """Unsafe settings are never forwarded to Spring."""
        for name in ('', 'settings.json', str(ROOT / 'settings.json'), '/tmp/missing-allow-intake.json'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                TRUST.validate_access_request_config({'access_request_config': name})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text('{}')
            path.chmod(0o600)
            link = Path(directory) / 'linked.json'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                TRUST.validate_access_request_config({'access_request_config': str(link)})
            Path(directory).chmod(0o755)
            with self.assertRaises(ValueError):
                TRUST.validate_access_request_config({'access_request_config': str(path)})

    def test_exact_package_bindings(self):
        """The current approved contract and proof pass the package boundary."""
        PACKAGE.verify_access_request_evidence({name: ROOT / name for name in PACKAGE.FIXED})

    def test_substituted_proof_and_council(self):
        """A changed proof or different reviewer model cannot reuse the approval."""
        with tempfile.TemporaryDirectory() as directory:
            members = {name: ROOT / name for name in PACKAGE.FIXED}
            changed = Path(directory) / 'changed'
            changed.write_text('different proof')
            members['formal/Allow/AiAccessRequest.lean'] = changed
            with self.assertRaisesRegex(ValueError, 'proof binding'):
                PACKAGE.verify_access_request_evidence(members)
            members = {name: ROOT / name for name in PACKAGE.FIXED}
            name = 'gates/ai-access-request-v1/council-disposition.json'
            council = json.loads(members[name].read_text())
            council['reviewers'][0]['model'] = 'another-model'
            changed.write_text(json.dumps(council))
            members[name] = changed
            with self.assertRaisesRegex(ValueError, 'six exact council'):
                PACKAGE.verify_access_request_evidence(members)


if __name__ == '__main__':
    unittest.main()
