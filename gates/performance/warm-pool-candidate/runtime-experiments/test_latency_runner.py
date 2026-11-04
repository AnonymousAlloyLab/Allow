"""Finite fail-closed orchestration checks; never launch a JVM or real scope."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import latency_owner as owner
import latency_runner as runner


class LatencyRunnerTests(unittest.TestCase):
    def test_diagnostic_claim_copy_preserves_original_scope_and_containment(self):
        original = json.loads((Path(__file__).parent/'runtime-claims.json').read_text())
        snapshot = copy.deepcopy(original)
        plan = {'profile': 'FRESH', 'warmups': 20, 'measured': 100}
        with patch.object(runner, 'read_private', return_value=original):
            result = runner.diagnostic_claims(Path('/copy'), plan)
        self.assertEqual(original, snapshot)
        self.assertEqual(result['namespace'], 'ALLOW-WARM-LATENCY-DIAGNOSTIC-R1')
        self.assertEqual([r for r in result['claims'] if r['id'] != 'WP-H03'],
                         [r for r in original['claims'] if r['id'] != 'WP-H03'])
        self.assertEqual(result['claims'][2]['plan'], plan)
        self.assertEqual(result['claims'][2]['verifier'], 'latency_results.verify_variant')
        self.assertNotIn('comparative performance', result['excluded'])
        self.assertIn('HTTP acceptance', result['excluded'])

    def test_exact_measured_schedule_and_population(self):
        self.assertEqual(runner.schedule('MEASURED'), [
            ('pair1-fresh', 'FRESH', 20, 100), ('pair1-pool', 'POOL_SERIAL', 20, 100),
            ('pair2-pool', 'POOL_SERIAL', 20, 100), ('pair2-fresh', 'FRESH', 20, 100),
            ('pair3-fresh', 'FRESH', 20, 100), ('pair3-pool', 'POOL_SERIAL', 20, 100),
            ('ready-conditioned', 'POOL_READY', 20, 100), ('empty-pool', 'POOL_EMPTY', 0, 20)])
        self.assertEqual(sum(w+m for _, _, w, m in runner.schedule('MEASURED')), 860)
        with self.assertRaisesRegex(ValueError, 'mode'):
            runner.schedule('OTHER')

    def freeze_setup(self, folder, duplicate=False):
        names = [row[0] for row in runner.PREFLIGHT]
        paths = [folder/'run-a', folder/('run-a' if duplicate else 'run-b')]
        for p in paths:
            p.mkdir(exist_ok=True)
        supplied = folder/'supplied.json'
        supplied.write_text(json.dumps(dict(zip(names, map(str, paths)))))
        return argparse.Namespace(suite=folder/'suite', runs=supplied, mode='PREFLIGHT',
                                  ownership=folder/'ownership', compatibility=None), paths

    def test_duplicate_run_rejected_before_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, _ = self.freeze_setup(Path(temporary), duplicate=True)
            with patch.object(runner, 'suite_path', side_effect=lambda p, **k: p), \
                 patch.object(runner.controller, 'run_path', side_effect=lambda p: p), \
                 patch.object(runner, 'read_private', return_value={'copied_root': '/same'}), \
                 patch.object(runner.installation, 'verify') as verify:
                with self.assertRaisesRegex(ValueError, 'distinct_scopes_required'):
                    runner.freeze(args)
                verify.assert_not_called()

    def test_reused_copy_rejected_even_with_distinct_run_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, _ = self.freeze_setup(Path(temporary))
            with patch.object(runner, 'suite_path', side_effect=lambda p, **k: p), \
                 patch.object(runner.controller, 'run_path', side_effect=lambda p: p), \
                 patch.object(runner, 'read_private', return_value={'copied_root': '/same'}):
                with self.assertRaisesRegex(ValueError, 'distinct_scopes_required'):
                    runner.freeze(args)

    def test_measured_requires_compatibility_before_registration(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            supplied = folder/'supplied.json'
            supplied.write_text(json.dumps({row[0]: str(folder/row[0]) for row in runner.TIMED}))
            args = argparse.Namespace(suite=folder/'suite', runs=supplied, mode='MEASURED',
                                      ownership=folder/'ownership', compatibility=None)
            def private(path):
                return {'copied_root': str(path.parent/'copy'), 'input_root_sha256': 'hash'}
            with patch.object(runner, 'suite_path', side_effect=lambda p, **k: p), \
                 patch.object(runner.controller, 'run_path', side_effect=lambda p: p), \
                 patch.object(runner, 'read_private', side_effect=private), \
                 patch.object(runner.installation, 'verify', return_value=folder), \
                 patch.object(runner.semantic_runner, 'same_inputs'), \
                 patch.object(runner.semantic_runner, 'ownership_prerequisite', return_value=[]), \
                 patch.object(runner.HERE.__class__, 'glob', return_value=[]), \
                 patch.object(Path, 'is_file', return_value=True), \
                 patch.object(runner, 'write_private') as write:
                with self.assertRaisesRegex(ValueError, 'compatibility_required_before_timing'):
                    runner.freeze(args)
                write.assert_not_called()

    def test_concrete_inputs_rejects_nonexact_owner_completion(self):
        root = Path('/copied')
        baseline = {'status': 'COMPLETE', 'exit_code': 0, 'probe_reaped': True,
                    'plan': {'path': 'p'}, 'java_report': {'path': 'j'}}
        cases = [('exit_code', True), ('exit_code', 1), ('probe_reaped', False),
                 ('status', 'BLOCKED')]
        for field, value in cases:
            done = dict(baseline, **{field: value})
            with self.subTest(field=field, value=value), \
                 patch.object(runner, 'read_private', return_value=done):
                with self.assertRaisesRegex(ValueError, 'owner_incomplete'):
                    runner.concrete_inputs(root, {}, {})

    def test_concrete_inputs_rejects_plan_or_report_digest_change(self):
        for field in ('plan', 'java_report'):
            done = {'status': 'COMPLETE', 'exit_code': 0, 'probe_reaped': True,
                    'plan': {'sha256': 'old'}, 'java_report': {'sha256': 'old'}}
            with self.subTest(field=field), patch.object(runner, 'read_private', return_value=done), \
                 patch.object(runner, 'record', side_effect=lambda p: {'sha256': 'new' if
                              (field == 'plan') == (p.name == 'latency-plan.json') else 'old'}):
                with self.assertRaisesRegex(ValueError, 'owner_receipt_changed'):
                    runner.concrete_inputs(Path('/copied'), {}, {})

    def test_owner_rejects_launch_root_binding(self):
        with patch.object(owner, 'read_private', return_value={'cgroupRoot': '/group'}), \
             patch.object(owner, 'write_private') as write:
            with self.assertRaisesRegex(ValueError, 'launch_installation_binding'):
                owner.concrete_plan(Path('/copied'), {'input_root_sha256': 'new'},
                                    {'plan': {}, 'installation_root': 'old'})
            write.assert_not_called()

    def test_owner_rejects_cgroup_identity_and_fixture_changes(self):
        for changed in ('identity', 'fixture'):
            config = {'cgroupRoot': '/group', 'rootDevice': 7, 'rootInode': 8}
            stat = argparse.Namespace(st_dev=7, st_ino=9 if changed == 'identity' else 8)
            launch = {'installation_root': 'root', 'plan': {'fixtureSha256': 'expected'}}
            with self.subTest(changed=changed), patch.object(owner, 'read_private', return_value=config), \
                 patch.object(Path, 'stat', return_value=stat), \
                 patch.object(owner, 'digest', return_value='changed'), \
                 patch.object(owner, 'write_private') as write:
                with self.assertRaisesRegex(ValueError, 'cgroup_identity' if changed == 'identity' else 'fixture_changed'):
                    owner.concrete_plan(Path('/copied'), {'input_root_sha256': 'root'}, launch)
                write.assert_not_called()

    def test_owner_reap_exception_preserves_blocked_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'.gate/evidence').mkdir(parents=True)
            (root/'.gate/evidence/latency-java.json').write_text('{}')
            child = MagicMock(returncode=0, pid=123)
            rows = {}
            with patch.object(owner, 'concrete_plan'), \
                 patch.object(owner, 'command', return_value=['never-executed']), \
                 patch.object(owner, 'clean_environment', return_value={}), \
                 patch.object(owner.subprocess, 'Popen', return_value=child), \
                 patch.object(owner, 'process_identity', return_value={'pid': 123, 'start_ticks': 4}), \
                 patch.object(owner, 'record', return_value={'sha256': 'bound'}), \
                 patch.object(owner.probe_owner, 'bounded_output', return_value=0), \
                 patch.object(owner.probe_owner, 'terminate', side_effect=RuntimeError('reap failed')), \
                 patch.object(owner, 'write_private', side_effect=lambda p, v: rows.__setitem__(p.name, copy.deepcopy(v))):
                owner.run(root, {}, {})
            completion = rows['latency-complete.json']
            self.assertEqual(completion['status'], 'BLOCKED')
            self.assertFalse(completion['probe_reaped'])
            self.assertEqual(completion['reap_failure_class'], 'RuntimeError')
            self.assertEqual(completion['java_report'], {'sha256': 'bound'})
            self.assertIn('finished_monotonic_ns', completion)

    def test_compare_preserves_initial_registration_when_replay_changes(self):
        suite = Path('/suite')
        pointer = {'path': '/suite/registration.json', 'sha256': 'initial-bytes'}
        initial = {'input_root_sha256': 'initial-root'}
        for error in (FileNotFoundError('deleted'), ValueError('mutated')):
            rows = {}
            with self.subTest(error=type(error).__name__), \
                 patch.object(runner, 'suite_path', return_value=suite), \
                 patch.object(runner, 'record', return_value=pointer), \
                 patch.object(runner, 'read_private', return_value=initial), \
                 patch.object(runner, 'registered', return_value=(suite, initial)), \
                 patch.object(runner, 'compare_checked', side_effect=error), \
                 patch.object(runner, 'write_private', side_effect=lambda p, v: rows.__setitem__(p.name, copy.deepcopy(v))):
                result = runner.compare(argparse.Namespace(suite=suite))
            self.assertEqual(result['status'], 'BLOCKED')
            report = rows['report.json']
            self.assertEqual(report['registration'], pointer)
            self.assertEqual(report['input_root_sha256'], 'initial-root')
            self.assertEqual(report['performance_interpretation'], 'INVALID')
            self.assertEqual(report['failure_class'], type(error).__name__)
            self.assertFalse(report['promotion_authorized'])

    def test_registered_rejects_changed_population_or_plan(self):
        for mutation in ('population', 'plan'):
            value = {'input_root_sha256': 'root', 'promotion_authorized': False,
                     'mode': 'MEASURED', 'order': [r[0] for r in runner.TIMED],
                     'total_requests': 860, 'variants': {r[0]: {'plan': {'name': r[0]}} for r in runner.TIMED}}
            if mutation == 'population':
                value['total_requests'] = 859
            else:
                value['variants']['pair1-fresh']['plan'] = {'name': 'changed'}
            with self.subTest(mutation=mutation), \
                 patch.object(runner, 'suite_path', return_value=Path('/suite')), \
                 patch.object(runner, 'read_private', return_value=value), \
                 patch.object(runner, 'root_hash', return_value='root'), \
                 patch.object(runner, 'plan_template', side_effect=lambda item, mode: {'name': item[0]}):
                with self.assertRaisesRegex(ValueError, 'registered_population' if mutation == 'population' else 'registered_plan'):
                    runner.registered(Path('/suite'))


if __name__ == '__main__':
    unittest.main()
