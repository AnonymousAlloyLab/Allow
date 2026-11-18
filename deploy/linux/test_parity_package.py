"""Reject substituted oracle parity proof and council inputs before packaging."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('parity_package', ROOT / 'scripts/package_iis.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class ParityPackageTests(unittest.TestCase):
    """Check current bindings and reject unrelated compiler evidence or approvals."""

    def inputs(self):
        """Resolve explicit source members without collecting runtime files."""
        return {name: ROOT / name for name in PACKAGE.FIXED}

    def test_current_inputs(self):
        """Both clean proof builds and the approved contract match."""
        PACKAGE.verify_parity_evidence(self.inputs())

    def test_changed_build(self):
        """Compiler output from another proof cannot satisfy this report."""
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / 'axioms.log'
            changed.write_text('other proof\n')
            members = self.inputs()
            members['gates/oracle-parity-v1/formal-2/axioms.log'] = changed
            with self.assertRaisesRegex(ValueError, 'proof build mismatch'):
                PACKAGE.verify_parity_evidence(members)

    def test_wrong_council(self):
        """Six approvals must be the required model seats for this contract."""
        with tempfile.TemporaryDirectory() as directory:
            members = self.inputs()
            name = 'gates/oracle-parity-v1/council-disposition.json'
            council = json.loads(members[name].read_text())
            council['reviewers'][0]['model'] = 'other-model'
            changed = Path(directory) / 'council.json'
            changed.write_text(json.dumps(council))
            members[name] = changed
            with self.assertRaisesRegex(ValueError, 'six exact council approvals'):
                PACKAGE.verify_parity_evidence(members)


if __name__ == '__main__':
    unittest.main()
