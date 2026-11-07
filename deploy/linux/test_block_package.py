"""Require shipped block-workbench evidence to retain its exact recorded inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('block_package', ROOT / 'scripts/package_iis.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class BlockPackageTests(unittest.TestCase):
    """Exercise independent proof output and contract binding failures."""

    def inputs(self):
        """Resolve only explicit package members, without compiled application inputs."""
        return {name: ROOT / name for name in PACKAGE.FIXED}

    def test_current_evidence_is_bound(self):
        """The current supplement and both complete builds are accepted."""
        PACKAGE.verify_block_evidence(self.inputs())

    def test_replaced_compiler_evidence_is_rejected(self):
        """A changed compile log cannot retain the old formal report's authority."""
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / 'compile.log'
            changed.write_text('unrelated compiler output\n')
            members = self.inputs()
            members['gates/block-workbench-v1/formal-2/compile.log'] = changed
            with self.assertRaisesRegex(ValueError, 'proof build mismatch'):
                PACKAGE.verify_block_evidence(members)

    def test_foreign_council_binding_is_rejected(self):
        """An approval for another contract does not authorize this package."""
        with tempfile.TemporaryDirectory() as directory:
            members = self.inputs()
            name = 'gates/block-workbench-v1/council-disposition.json'
            value = json.loads(members[name].read_text())
            value['contract_sha256'] = '0' * 64
            changed = Path(directory) / 'council.json'
            changed.write_text(json.dumps(value))
            members[name] = changed
            with self.assertRaisesRegex(ValueError, 'council binding mismatch'):
                PACKAGE.verify_block_evidence(members)


if __name__ == '__main__':
    unittest.main()
