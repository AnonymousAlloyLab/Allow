#!/usr/bin/env python3
"""Finite harness authoring checks; no service, SQL, Java workload or benchmark is launched."""
import importlib.util
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import containment
import controller
import http_driver
import installation
import stack_owner
from harness_common import HERE, ROOT, clean_environment, digest, record, regular, relative_name, root_hash, write_private


class HarnessChecks(unittest.TestCase):
    """Exercise fail-closed input boundaries and independently registered numeric budgets."""

    def test_containment_contract(self):
        """Runtime cgroup literals must agree with the approved experiment bytes."""
        limits = json.loads((HERE.parent/'experiment.json').read_text())['isolation']['effective_limits']
        expected = {'cpu.max': limits['cpu_max'], 'memory.high': str(limits['memory_high_bytes']),
                    'memory.max': str(limits['memory_max_bytes']), 'memory.swap.max': str(limits['memory_swap_max_bytes']),
                    'pids.max': str(limits['pids_max'])}
        self.assertEqual(containment.EXPECTED, expected)
        self.assertEqual(limits['cpu_affinity'], [0, 1, 2, 3])

    def test_source_aliases_rejected(self):
        """A source symlink or hardlink cannot smuggle a mutable live file into a copy."""
        with tempfile.TemporaryDirectory(prefix='allow-ft1-test-') as directory:
            root = Path(directory)
            (root/'source').write_text('synthetic')
            (root/'alias').symlink_to(root/'source')
            with self.assertRaises(ValueError):
                regular(root/'alias')
            os.link(root/'source', root/'hard')
            with self.assertRaises(ValueError):
                regular(root/'hard')

    def test_unsafe_inventory_paths_rejected(self):
        """Copied input names cannot address a live runtime, absolute path or parent."""
        for name in ('/tmp/target', '../source', '.runtime/database.json', 'scripts/../../secret'):
            with self.assertRaises(ValueError):
                relative_name(name)

    def test_environment_authority_is_not_inherited(self):
        """Ambient credentials, database settings and JVM options never enter owner environment."""
        os.environ.update(ALLOW_TOKEN='test-secret', PGPASSWORD='test-secret', JAVA_TOOL_OPTIONS='-Dtest=true')
        values = clean_environment(Path('/tmp/allow-ft1-test'))
        self.assertNotIn('ALLOW_TOKEN', values)
        self.assertNotIn('PGPASSWORD', values)
        self.assertNotIn('JAVA_TOOL_OPTIONS', values)
        self.assertEqual(values['ALLOW_CORPUS_RUNTIME'], '/tmp/allow-ft1-test/.runtime/corpus')

    def test_spring_budget_matches_contract(self):
        """Every preregistered JVM/Tomcat budget must be explicit in the actual command."""
        budgets = json.loads((HERE.parent/'experiment.json').read_text())['component_budgets']['spring']
        argv = stack_owner.spring_argv(Path('/tmp/allow-ft1-test'), {'java': {'executable': '/fixed/java'}, 'port': 43210})
        for budget in budgets:
            self.assertIn(budget if budget.startswith('-') else '--' + budget, argv)
        self.assertFalse(any('TieredStopAtLevel' in value for value in argv))

    def test_manifest_metadata_mutation_changes_root(self):
        """Identity binds port, variant, unit and copied root as well as file bytes."""
        initial = {'port': 1234, 'variant': 'F0', 'copied_root': '/tmp/allow-ft1-one', 'unit': 'owned'}
        original = root_hash(initial)
        for key in initial:
            altered = dict(initial, **{key: 'changed'})
            self.assertNotEqual(root_hash(altered), original)

    def test_original_http_threshold_is_strict(self):
        """Exactly 300ms cannot pass, and a warmup failure or missing sample is blocking."""
        rows = [{'event': n, 'phase': 'warmup' if n < 100 else 'measured', 'status': 'PASS', 'elapsed_ms': 299.9}
                for n in range(1100)]
        self.assertEqual(http_driver.summarize(rows)['status'], 'PASS')
        self.assertEqual(http_driver.summarize(rows[:-1])['status'], 'BLOCKED')
        rows[0]['status'] = 'BLOCKED'
        self.assertEqual(http_driver.summarize(rows)['status'], 'BLOCKED')
        rows[0]['status'] = 'PASS'
        for row in rows:
            row['elapsed_ms'] = 300
        self.assertEqual(http_driver.summarize(rows)['status'], 'BLOCKED')

    def test_http_boolean_integer_confusion_is_rejected(self):
        """Python equality must not promote boolean protocol/revision fields to integer matches."""
        request = {'draftId': http_driver.identifier('test'), 'draftEpoch': 0, 'baseRevision': 1}
        raw = http_driver.encode(request)
        source = 'sig Synthetic {}'
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        data = dict(request, requestHash=hashlib.sha256(raw).hexdigest(), supportMode='BLOCK_SUPPORTED',
                    diagnostics=[], proposedSource=source, proposedSourceHash=source_hash, sourceHash=source_hash)
        valid = {'protocol': 1, 'requestId': http_driver.identifier('reply'), 'status': 'VALIDATED', 'data': data}
        http_driver.check_response(200, valid, request, raw)
        for field, value in (('protocol', True), ('draftEpoch', False), ('baseRevision', True)):
            changed = copy.deepcopy(valid)
            (changed if field == 'protocol' else changed['data'])[field] = value
            with self.assertRaises(ValueError):
                http_driver.check_response(200, changed, request, raw)

    def test_ready_receipt_is_complete_and_exact(self):
        """A truncated inventory or changed file cannot pass a source-ready receipt."""
        with tempfile.TemporaryDirectory(prefix='allow-ft1-test-') as directory:
            root = Path(directory)
            (root/'a').write_text('frozen')
            row = record(root/'a', root)
            installation.require_inventory(root, [row], [row])
            with self.assertRaises(ValueError):
                installation.require_inventory(root, [], [row])
            (root/'a').write_text('changed')
            with self.assertRaises(ValueError):
                installation.require_inventory(root, [row], [row])

    def test_owner_manifest_and_surplus_code_are_checked(self):
        """Unlisted owner-side code or altered self-referential manifest cannot evade run binding."""
        with tempfile.TemporaryDirectory(prefix='allow-ft1-test-') as directory:
            root = Path(directory)
            (root/'.gate').mkdir()
            (root/'.gate/program.py').write_text('pass\n')
            manifest = {'files': [record(root/'.gate/program.py', root)], 'tooling': {'aliases': []}}
            write_private(root/'.gate/manifest.json', manifest)
            installation.verify_copied_members(root, manifest, True)
            (root/'.gate/unregistered.py').write_text('pass\n')
            with self.assertRaises(ValueError):
                installation.verify_copied_members(root, manifest, True)
            (root/'.gate/unregistered.py').unlink()
            changed = dict(manifest, port=9999)
            with self.assertRaises(ValueError):
                installation.verify_copied_members(root, changed, True)


if __name__ == '__main__':
    unittest.main()
