#!/usr/bin/env python3
"""Offline adversarial checks for the parent pair verifier; no services or timings."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

import pair_runner as pair
from harness_common import write_private


class PairVerifierTests(unittest.TestCase):
    """Check strict JSON, raw binding, frozen prerequisites and finite stop decisions."""

    def test_json_types_duplicates_and_nonfinite(self):
        """Booleans, duplicate fields and nonfinite values must not satisfy typed evidence."""
        self.assertFalse(pair.equal(True, 1))
        self.assertFalse(pair.equal(False, 0))
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(ValueError):
                pair.decode(raw)

    def sample(self):
        """Build one exact synthetic request/response and hash-bound sample for negative tests."""
        request = {'draftId': str(uuid.UUID(int=1)), 'draftEpoch': 0, 'baseRevision': 1, 'candidate': {}}
        raw = json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode()
        source = 'sig Synthetic {}'
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        data = {key: request[key] for key in ('draftId', 'draftEpoch', 'baseRevision')}
        data.update(requestHash=hashlib.sha256(raw).hexdigest(), supportMode='BLOCK_SUPPORTED',
                    diagnostics=[], proposedSource=source, proposedSourceHash=source_hash, sourceHash=source_hash)
        value = {'protocol': 1, 'requestId': str(uuid.UUID(int=2)), 'status': 'VALIDATED', 'data': data}
        response = json.dumps(value).encode()
        record = {'event': 0, 'phase': 'warmup', 'path': 'requests/0000.json', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        sample = {'event': 0, 'phase': 'warmup', 'request_sha256': record['sha256'], 'status': 'PASS',
                  'http_status': 200, 'elapsed_ms': 300.0, 'response_sha256': hashlib.sha256(response).hexdigest(),
                  'response_bytes': len(response)}
        return request, raw, value, response, record, sample

    def test_raw_sample_mutations(self):
        """Missing events, swapped bytes, failure status and altered response digests are blocking."""
        request, raw, _, response, record, sample = self.sample()
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            root = Path(directory)
            (root/'requests').mkdir()
            (root/'responses').mkdir()
            (root/'requests/0000.json').write_bytes(raw)
            (root/'responses/0000.json').write_bytes(response)
            pair.check_sample(root, 0, sample, record, request)
            for field, value in (('event', True), ('status', 'BLOCKED'), ('elapsed_ms', True),
                                 ('http_status', 500), ('response_sha256', '0' * 64)):
                changed = dict(sample, **{field: value})
                with self.assertRaises(ValueError):
                    pair.check_sample(root, 0, changed, record, request)
            (root/'requests/0000.json').write_bytes(raw + b' ')
            with self.assertRaises(ValueError):
                pair.check_sample(root, 0, sample, record, request)

    def test_response_boolean_and_unknown_fields(self):
        """Every response field is checked with exact JSON types and no surplus fields."""
        request, raw, response, _, _, _ = self.sample()
        for field, value in (('protocol', True), ('draftEpoch', False), ('baseRevision', True), ('sourceHash', '0' * 64)):
            changed = copy.deepcopy(response)
            (changed if field == 'protocol' else changed['data'])[field] = value
            with self.assertRaises(ValueError):
                pair.response_matches(json.dumps(changed).encode(), request, raw)
        changed = copy.deepcopy(response)
        changed['data']['extra'] = 1
        with self.assertRaises(ValueError):
            pair.response_matches(json.dumps(changed).encode(), request, raw)

    def test_nearest_rank_and_latency_only_classification(self):
        """A complete baseline above 300ms retains its measured percentile and failed latency flag."""
        rows = [{'elapsed_ms': 1.0} for _ in range(100)] + [{'elapsed_ms': float(index)} for index in range(1, 1001)]
        original = {'status': 'BLOCKED', 'warmups': 100, 'measured': 1000, 'required_warmups': 100,
                    'required_measured': 1000, 'failures': [], 'p50_ms': 500.0, 'p95_ms': 950.0,
                    'p99_ms': 990.0, 'maximum_ms': 1000.0}
        result = pair.summary(rows, original)
        self.assertEqual(result['p95_ms'], 950.0)
        self.assertEqual(result['latency_gate'], 'FAIL')
        changed = dict(original, p95_ms=300.0)
        with self.assertRaises(ValueError):
            pair.summary(rows, changed)
        changed = dict(original, failures=[{'event': 0}])
        with self.assertRaises(ValueError):
            pair.summary(rows, changed)

    def test_prerequisites_require_hashed_actual_success(self):
        """A supplied PASS label cannot override a failed or mutated source report."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            root = Path(directory)
            receipt = {}
            for name in pair.REQUIRED:
                path = root/(name + '.json')
                write_private(path, {'status': 'PASS', 'failures': 0})
                receipt[name] = dict(pair.binding(path), success_pointer='/status', success_value='PASS',
                                     assertions=[{'pointer': '/failures', 'equals': 0}])
            path = root/'receipt.json'
            write_private(path, receipt)
            self.assertEqual(len(pair.prerequisites(path)), 5)
            (root/'java_safety.json').write_text('{"status":"PASS","failures":true}')
            with self.assertRaises(ValueError):
                pair.prerequisites(path)

    def test_failure_stops_remaining_pairs_without_activation(self):
        """Failed first F1 leaves pairs two and three unexecuted and records KEEP_F0."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory))
            candidate = verdicts[(1, 'F1')]
            candidate.update(valid_measurement=False, p95_ms=350.0)
            (Path(registrations[(1, 'F1')]['run'])/'pair-verification.json').write_text(json.dumps(candidate))
            for variant in ('F0', 'F1'):
                pair.finish_history(registrations[(1, variant)], verdicts[(1, variant)])
            result = pair.load(history/'selection.json')
            self.assertEqual(result['status'], 'KEEP_F0')
            self.assertEqual(result['profile_activation'], 'NOT_PERFORMED')
            self.assertTrue(all(row['status'] == 'NOT_EXECUTED' for row in result['trials'][2:]))
            with self.assertRaises(ValueError):
                pair.check_order(history, 2, 'F1', value)

    def test_equal_f1_p95_cannot_pass_pair(self):
        """Meeting the absolute threshold alone cannot select an unimproved F1."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory), baseline=250.0, candidate=250.0)
            for variant in ('F0', 'F1'):
                pair.finish_history(registrations[(1, variant)], verdicts[(1, variant)])
            self.assertEqual(pair.load(history/'pair-1.json')['status'], 'BLOCKED')

    def history_fixture(self, root, baseline=500.0, candidate=200.0):
        """Create synthetic immutable verdicts; mock only expensive raw-evidence recomputation."""
        history = root/'history'; history.mkdir()
        value = {'input_root_sha256': 'a'*64, 'trials': []}
        registrations, verdicts, recomputed = {}, {}, {}
        experiment = root/'experiment.json'; write_private(experiment, value)
        for number, variant in pair.ORDER:
            run = root/f'run-{number}-{variant}'; run.mkdir()
            manifest = run/'manifest.json'; write_private(manifest, {'synthetic': True})
            source_root = str(number) + variant + 'b'*60
            value['trials'].append({'pair': number, 'variant': variant, 'manifest': pair.binding(manifest),
                                    'input_root_sha256': source_root})
            registration = {'run': str(run), 'history': str(history), 'pair': number, 'variant': variant,
                            'experiment_binding': pair.binding(experiment)}
            verdict = {'pair': number, 'variant': variant, 'valid_measurement': True,
                       'input_root_sha256': source_root, 'p95_ms': baseline if variant == 'F0' else candidate}
            write_private(run/'pair-verification.json', verdict)
            registrations[(number, variant)] = registration; verdicts[(number, variant)] = verdict
            recomputed[str(run/'pair-registration.json')] = copy.deepcopy(verdict)
        self.addCleanup(patch.stopall)
        patch.object(pair, 'experiment_at', return_value=value).start()
        patch.object(pair, 'verify_trial', side_effect=lambda path: copy.deepcopy(recomputed[str(path)])).start()
        pair.history_anchor(history, experiment, value, create=True)
        return history, value, registrations, verdicts

    def test_complete_three_pairs_bind_all_records_and_no_activation(self):
        """Successful selection retains all six trial hashes and all three comparisons."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory))
            for key in pair.ORDER: pair.finish_history(registrations[key], verdicts[key])
            selection = pair.load(history/'selection.json')
            self.assertEqual(selection['status'], 'THREE_HTTP_PAIRS_PASSED')
            self.assertEqual(selection['experiment_root_sha256'], value['input_root_sha256'])
            self.assertEqual(len(selection['pairs']), 3)
            self.assertTrue(all(row['record'] == pair.binding(pair.history_path(history, row['pair'], row['variant']))
                                for row in selection['trials']))
            self.assertEqual(selection['profile_activation'], 'NOT_PERFORMED')

    def test_history_chain_and_experiment_identity_mutations(self):
        """An earlier true verdict cannot authorize a changed chain or experiment root."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory))
            pair.finish_history(registrations[(1, 'F0')], verdicts[(1, 'F0')])
            path = pair.history_path(history, 1, 'F0'); original = pair.load(path)
            for key, changed in (('previous_trial', {'sha256': '0'*64}), ('experiment_root_sha256', '0'*64),
                                 ('input_root_sha256', '0'*64), ('variant', 'F1'), ('pair', True)):
                with self.subTest(key=key):
                    path.write_text(json.dumps(dict(original, **{key: changed})))
                    with self.assertRaises(ValueError): pair.check_order(history, 1, 'F1', value)

    def test_history_replays_raw_verdict_and_hashes(self):
        """Mutating a retained verdict and resealing its pointer still fails independent replay."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory))
            pair.finish_history(registrations[(1, 'F0')], verdicts[(1, 'F0')])
            path = pair.history_path(history, 1, 'F0'); row = pair.load(path)
            verdict_path = Path(row['verdict']['path'])
            verdict_path.write_text(json.dumps(dict(verdicts[(1, 'F0')], p95_ms=900.0)))
            with self.assertRaisesRegex(ValueError, 'history_verdict_binding'): pair.check_order(history, 1, 'F1', value)
            row['verdict'] = pair.binding(verdict_path); path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'history_verdict_replay_mismatch'): pair.check_order(history, 1, 'F1', value)

    def test_prior_pair_comparison_is_recomputed(self):
        """Even a retained PASS summary cannot conceal a modified pair evidence pointer."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory))
            for variant in ('F0', 'F1'): pair.finish_history(registrations[(1, variant)], verdicts[(1, variant)])
            path = history/'pair-1.json'; row = pair.load(path); row['F0']['sha256'] = '0'*64
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'earlier_pair_not_passed'): pair.check_order(history, 2, 'F1', value)

    def cleanup_fixture(self):
        """Build explicit finite terminal evidence with no real processes or cgroups."""
        metrics = {'memory.events': 'oom 0\noom_kill 0\noom_group_kill 0', 'pids.events': 'max 0',
                   'memory.peak': '1024', 'pids.peak': '10', 'cpu.stat': 'usage_usec 100'}
        snapshot = {'processes': [], 'metrics': metrics, 'observed_monotonic_ns': 10}
        cleanup = {'status': 'PASS', 'populated_zero_observed': True, 'owned_identities_absent': True,
                   'stop_exit_code': 0, 'graceful_kill_exit_code': 0, 'stop_disposition': 'stop_command',
                   'last_cgroup_events': 'populated 0\nfrozen 0', 'terminal_resources_complete': True,
                   'terminal_resource_limits_passed': True,
                   'terminal_resources': {'metrics': copy.deepcopy(metrics), 'observed_monotonic_ns': 11}, 'unit': {}}
        return {'cleanup': cleanup}, [snapshot]

    def test_terminal_counters_fail_closed(self):
        """Late OOM/task exhaustion, absent counters, memory excess and stale observations block."""
        report, snapshots = self.cleanup_fixture(); self.assertEqual(pair.cleanup_checks(report, snapshots), 1024)
        mutations = [('memory.events', 'oom 1\noom_kill 0\noom_group_kill 0'), ('pids.events', 'max 1'),
                     ('memory.events', 'oom 0\noom_kill 0'), ('memory.peak', '5368709121'), ('pids.peak', '513')]
        for name, text in mutations:
            changed = copy.deepcopy(report); changed['cleanup']['terminal_resources']['metrics'][name] = text
            with self.assertRaises(ValueError): pair.cleanup_checks(changed, snapshots)
        for name in report['cleanup']['terminal_resources']['metrics']:
            changed = copy.deepcopy(report); changed['cleanup']['terminal_resources']['metrics'].pop(name)
            with self.assertRaises(ValueError): pair.cleanup_checks(changed, snapshots)
        changed = copy.deepcopy(report); changed['cleanup']['terminal_resources']['observed_monotonic_ns'] = 9
        with self.assertRaises(ValueError): pair.cleanup_checks(changed, snapshots)

    def test_removed_scope_requires_positive_empty_and_absence(self):
        """Auto-unloading is acceptable only after explicit empty and exact owned-identity absence."""
        report, snapshots = self.cleanup_fixture(); cleanup = report['cleanup']
        cleanup.update(stop_exit_code=5, stop_disposition='already_removed_after_explicit_empty', unit={'LoadState': 'not-found'})
        pair.cleanup_checks(report, snapshots)
        for name, value in (('populated_zero_observed', False), ('owned_identities_absent', False),
                            ('last_cgroup_events', 'populated 1'), ('stop_disposition', 'stop_command'),
                            ('unit', {'LoadState': 'loaded'})):
            changed = copy.deepcopy(report); changed['cleanup'][name] = value
            with self.assertRaises(ValueError): pair.cleanup_checks(changed, snapshots)

    def test_absolute_threshold_is_strict_even_when_relative_improvement(self):
        """An F1 at exactly300ms cannot pass despite beating a slower baseline."""
        with tempfile.TemporaryDirectory(prefix='allow-pair-test-') as directory:
            history, value, registrations, verdicts = self.history_fixture(Path(directory), candidate=300.0)
            for variant in ('F0', 'F1'): pair.finish_history(registrations[(1, variant)], verdicts[(1, variant)])
            self.assertEqual(pair.load(history/'selection.json')['status'], 'KEEP_F0')

    def test_scope_snapshot_requires_exact_owner_group_and_affinity(self):
        """A scope receipt cannot substitute MainPID0 or another PID incarnation for its supervisor."""
        owner = {'pid': 100, 'start_ticks': '200'}; group = '/user.slice/test.scope'
        invocation = {'main_identity': owner, 'invocation_id': 'fixed', 'control_group': group}
        manifest = {'unit': 'test.scope', 'input_root_sha256': 'a'*64, 'launch_lane': 'owned_caller_scope_v1'}
        snapshot = {'unit': {'Id': 'test.scope', 'Description': 'allow-fresh:'+'a'*64,
                            'InvocationID': 'fixed', 'KillMode': 'control-group', 'Delegate': 'no', 'ControlGroup': group},
                    'launch_lane': 'owned_caller_scope_v1', 'supervisor_identity': owner,
                    'limits': copy.deepcopy(pair.containment.EXPECTED), 'observed_monotonic_ns': 1,
                    'processes': [dict(owner, cgroup=group, threads=[{'tid': 100, 'affinity': [0, 1, 2, 3]}])],
                    'metrics': {'memory.events': 'oom 0\noom_kill 0\noom_group_kill 0', 'pids.events': 'max 0', 'memory.peak': '1024'}}
        self.assertEqual(pair.verify_snapshot(snapshot, manifest, invocation), 1024)
        variants = []
        changed = copy.deepcopy(snapshot); changed['supervisor_identity']['start_ticks'] = 'other'; variants.append(changed)
        changed = copy.deepcopy(snapshot); changed['unit']['ControlGroup'] = ''; variants.append(changed)
        changed = copy.deepcopy(snapshot); changed['processes'][0]['threads'][0]['affinity'] = [0, 1]; variants.append(changed)
        changed = copy.deepcopy(snapshot); changed['launch_lane'] = 'other'; variants.append(changed)
        changed = copy.deepcopy(snapshot); changed['processes'][0]['cgroup'] = '/elsewhere'; variants.append(changed)
        for changed in variants:
            with self.assertRaises(ValueError): pair.verify_snapshot(changed, manifest, invocation)


if __name__ == '__main__':
    unittest.main()
