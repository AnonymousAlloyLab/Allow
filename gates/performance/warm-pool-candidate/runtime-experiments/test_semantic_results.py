"""Independent offline adversarial checks for the finite semantic evidence verifier."""
import base64
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import semantic_results as subject
import semantic_runner
from harness_common import digest, process_identity, write_private

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE/'semantic-fixtures.json').read_bytes())
BUILD = '1' * 64
POOL = '00000000-0000-0000-0000-000000000042'
DEAD = {'pid': 1073741823, 'start_ticks': '123'}


def packed(value):
    """Encode finite compact synthetic protocol JSON, without a framing delimiter."""
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


def fixture(name='context-invalid-ownedIdInventory'):
    """Use the actual frozen corpus row and original unchanged request bytes."""
    item = copy.deepcopy(next(row for row in PLAN['fixtures'] if row['name'] == name))
    raw = (HERE/item['path']).read_bytes()
    return item, json.loads(raw), raw


def result(item, frame, variant='W0', value=None):
    """Build a correctly bound synthetic complete record, never a runtime receipt."""
    value = value or {'protocol': 1, 'requestId': frame['requestId'], 'status': 'UNAVAILABLE', 'data': {}}
    raw = packed(value) + b'\n'
    capture = ('RESERIALIZED_COMPLETE_POOL_RESPONSE' if variant == 'W1' and item['operation'] == 'VALIDATE'
               else 'ACTUAL_STDOUT_FRAME')
    return {'schemaVersion': 1, 'profile': 'DEFAULT', 'variant': variant,
            'inputSha256': item['sha256'], 'inputBytes': item['bytes'], 'buildIdentity': BUILD,
            'outcome': 'COMPLETE_RESPONSE', 'requestIdentityMatches': True, 'reaped': True,
            'noWorkerStarted': False, 'noPrivateHandoff': False, 'workerExitCode': 0,
            'workerPid': DEAD['pid'], 'workerStartTicks': DEAD['start_ticks'],
            'responseBase64': base64.b64encode(raw).decode(), 'responseBytes': len(raw),
            'responseSha256': hashlib.sha256(raw).hexdigest(), 'responseCapture': capture,
            'workerStatus': value['status'], 'contextBoundary': subject.CONTEXT,
            'productionFrameStrictJsonEqual': True, 'productionFrameBytes': item['bytes'],
            'productionFrameSha256': item['sha256'], 'published': True,
            'route': subject.REVALIDATE if variant == 'W1' and item['operation'] == 'REVALIDATE' else subject.ROUTES[variant]}


def group():
    """Create synthetic complete kernel-counter evidence at a single exact worker identity."""
    return {'slot': 0, 'generation': 1, 'group': f'pool-{POOL}/slot-0-g1', 'device': 11, 'inode': 12,
            'pid': DEAD['pid'], 'startTicks': DEAD['start_ticks'], 'directChildReaped': True,
            'exitCode': 0, 'finalPhase': 'RELEASED', 'terminalCounters': {
                'cgroup.events': 'populated 0\nfrozen 0\n', 'memory.peak': '1048576\n',
                'memory.events': 'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n',
                'pids.peak': '4\n', 'pids.events': 'max 0\n', 'cpu.stat': 'usage_usec 3\n'}}


class SemanticResultTests(unittest.TestCase):
    """Synthetic evidence tests cover verifier mechanics, not actual process or model behavior."""

    def setUp(self):
        """Provision only private temporary metadata, with no database or subprocess."""
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-semantic-oracle-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root/'.gate/evidence'
        self.evidence.mkdir(parents=True, mode=0o700)
        self.serial = 0
        write_private(self.root/'.runtime/warm-pool/config.json',
                      {'schema': 1, 'cgroupRoot': '/synthetic/cgroup', 'rootDevice': 11, 'rootInode': 10})

    def store(self, value):
        """Write a fresh hashed private evidence object without overwriting previous mutations."""
        self.serial += 1
        path = self.evidence/f'synthetic-{self.serial}.json'
        write_private(path, value)
        return {'path': path.name, 'sha256': digest(path)}

    def specimen(self, variant='W0', name='context-invalid-ownedIdInventory'):
        """Build an exact Java-shaped synthetic row with the original unframed fixture file."""
        item, frame, raw = fixture(name)
        path = self.root/'.gate'/item['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o600)
        record = result(item, frame, variant)
        owned = {'perWorkerCgroup': variant == 'W1', 'groups': [group()] if variant == 'W1' else [],
                 'poolNonce': POOL, 'remainingReservations': 0, 'ledgerOnline': True, 'noGroupAllocated': False}
        row = {'id': item['name'], 'status': 'PASS', 'route': record['route'],
               'contextBoundary': subject.CONTEXT, 'identities': [copy.deepcopy(DEAD)],
               'cleanup': {'status': 'PASS', 'directChildReaped': True, 'capacityRetained': False,
                           'populatedZero': variant == 'W1', 'noGroupAllocated': False,
                           'outerScopeCleanupRequired': variant == 'W0'}}
        row['record'], row['ownership'] = self.store(record), self.store(owned)
        return item, frame, record, owned, row

    def test_original_unframed_fixture_and_both_routes_pass(self):
        """The request decoder must accept actual corpus files ending in }, unlike response framing."""
        for variant in ('W0', 'W1'):
            with self.subTest(variant=variant):
                item, frame, record, owned, row = self.specimen(variant)
                actual = subject.check_row(self.root, {'build_identity': {'value': BUILD}}, item, row, variant)
                self.assertEqual('PASS', actual['status'])

    def test_complete_response_hash_nonce_types_exit_and_capture_are_checked(self):
        """Every independently bound envelope scalar must reject a substituted or coerced value."""
        item, frame, record, _, _ = self.specimen('W1')
        mutations = {'profile': 'DOCUMENT_ADVISORY_TIER1', 'variant': 'W0', 'inputSha256': '0'*64,
                     'inputBytes': True, 'buildIdentity': '2'*64, 'outcome': 'WORKER_UNAVAILABLE',
                     'responseBytes': True, 'responseSha256': '0'*64, 'responseCapture': 'ACTUAL_STDOUT_FRAME',
                     'requestIdentityMatches': 1, 'reaped': 1, 'workerExitCode': True,
                     'responseBase64': '@@invalid@@', 'noWorkerStarted': True, 'noPrivateHandoff': True,
                     'workerStatus': 'VALIDATED', 'productionFrameStrictJsonEqual': False, 'published': False,
                     'productionFrameBytes': True, 'productionFrameSha256': 'unbound'}
        for key, value in mutations.items():
            with self.subTest(field=key):
                changed = dict(record, **{key: value})
                with self.assertRaises((ValueError, AssertionError, KeyError)):
                    subject.response(changed, item, frame, 'W1', BUILD)

    def test_closed_response_nonce_protocol_and_status(self):
        """Rehashing a wrong envelope never repairs the request identity or strict JSON types."""
        item, frame, _, _, _ = self.specimen()
        valid = {'protocol': 1, 'requestId': frame['requestId'], 'status': 'UNAVAILABLE', 'data': {}}
        for field, value in [('protocol', True), ('requestId', POOL), ('status', 'VALIDATED'), ('extra', 1)]:
            with self.subTest(field=field):
                with self.assertRaises((ValueError, AssertionError, KeyError)):
                    subject.response(result(item, frame, value=dict(valid, **{field: value})), item, frame, 'W0', BUILD)

    def test_full_response_framing_duplicate_keys_and_nonfinite(self):
        """Even correctly rehashed output must retain exact one-line finite closed JSON framing."""
        item, frame, record, _, _ = self.specimen()
        base = base64.b64decode(record['responseBase64'])
        for raw in (base[:-1], base+b'\n', base.replace(b'"protocol":1', b'"protocol":1,"protocol":1'),
                    base.replace(b'"protocol":1', b'"protocol":NaN')):
            changed = dict(record, responseBase64=base64.b64encode(raw).decode(), responseBytes=len(raw),
                           responseSha256=hashlib.sha256(raw).hexdigest())
            with self.subTest(raw_size=len(raw)):
                with self.assertRaises((ValueError, AssertionError)):
                    subject.response(changed, item, frame, 'W0', BUILD)

    def test_private_result_hash_and_alias_rejection(self):
        """Private records remain content-bound and cannot resolve an external or symlinked path."""
        pointer = self.store({'value': 1})
        self.assertEqual({'value': 1}, subject.private_result(self.root, pointer))
        for changed in (dict(pointer, sha256='0'*64), dict(pointer, path='../escape.json')):
            with self.assertRaises(ValueError):
                subject.private_result(self.root, changed)
        (self.evidence/'alias.json').symlink_to(self.evidence/pointer['path'])
        with self.assertRaises(ValueError):
            subject.private_result(self.root, dict(pointer, path='alias.json'))

    def test_case_record_route_trust_boundary_and_worker_identity_are_bound(self):
        """A valid complete response cannot borrow another route, context claim or absent process."""
        item, _, record, _, row = self.specimen('W1')
        mutations = {'route': subject.REVALIDATE, 'contextBoundary': 'ACTUAL_SQL_CLEAN',
                     'workerPid': DEAD['pid'] - 1, 'workerStartTicks': '999'}
        for key, value in mutations.items():
            with self.subTest(field=key):
                changed_row = dict(row, record=self.store(dict(record, **{key: value})))
                with self.assertRaises((ValueError, AssertionError)):
                    subject.check_row(self.root, {'build_identity': {'value': BUILD}}, item, changed_row, 'W1')
        with self.assertRaises((ValueError, AssertionError)):
            subject.check_row(self.root, {'build_identity': {'value': BUILD}}, item,
                              dict(row, contextBoundary='ACTUAL_SQL_CLEAN'), 'W1')

    def test_warm_counters_must_show_positive_empty_and_no_exhaustion(self):
        """Independent counter parsing rejects missing zero evidence and exhausted worker limits."""
        item, _, _, owned, row = self.specimen('W1')
        mutations = [('cgroup.events', 'populated 1\n'), ('cgroup.events', 'frozen 0\n'),
                     ('cgroup.events', 'populated 0\npopulated 0\n'), ('memory.peak', '1073741825'),
                     ('pids.peak', '33'), ('memory.events', 'oom 0\noom_kill 1\noom_group_kill 0\n'),
                     ('memory.events', 'oom 0\n'), ('pids.events', 'max 1\n'), ('cpu.stat', 'user_usec 1\n')]
        for key, value in mutations:
            with self.subTest(counter=key, value=value):
                changed = copy.deepcopy(owned)
                changed['groups'][0]['terminalCounters'][key] = value
                changed_row = dict(row, ownership=self.store(changed))
                with self.assertRaises(ValueError):
                    subject.ownership(self.root, changed_row, item, 'W1')

    def test_group_receipts_require_exact_owned_identities_and_uniqueness(self):
        """A foreign empty group cannot substitute for the original direct child or generation."""
        item, _, _, owned, row = self.specimen('W1')
        mutations = []
        changed = copy.deepcopy(owned); changed['groups'][0]['pid'] += 1; mutations.append(changed)
        changed = copy.deepcopy(owned); changed['groups'][0]['startTicks'] = '999'; mutations.append(changed)
        changed = copy.deepcopy(owned); changed['groups'].append(copy.deepcopy(changed['groups'][0])); mutations.append(changed)
        changed = copy.deepcopy(owned); changed['groups'][0]['directChildReaped'] = False; mutations.append(changed)
        changed = copy.deepcopy(owned); changed['groups'][0]['finalPhase'] = 'UNKNOWN'; mutations.append(changed)
        for changed in mutations:
            with self.subTest(group=changed['groups']):
                with self.assertRaises(ValueError):
                    subject.ownership(self.root, dict(row, ownership=self.store(changed)), item, 'W1')

    def test_live_direct_child_and_boolean_pid_are_rejected(self):
        """Process absence is checked using real PID/start metadata without starting a child."""
        item, _, _, _, row = self.specimen()
        for identity in (process_identity(os.getpid()), {'pid': True, 'start_ticks': '123'}):
            with self.assertRaises(ValueError):
                subject.ownership(self.root, dict(row, identities=[identity]), item, 'W0')

    def test_baseline_does_not_claim_nonexistent_worker_group_zero(self):
        """Baseline cleanup is process-only and requires final outer-scope cleanup separately."""
        item, _, _, _, row = self.specimen()
        for mutation in ({'populatedZero': True}, {'outerScopeCleanupRequired': False}):
            changed = dict(row, cleanup=dict(row['cleanup'], **mutation))
            with self.assertRaises(ValueError):
                subject.ownership(self.root, changed, item, 'W0')

    def test_binding_rejection_has_no_worker_group_or_handoff(self):
        """The one preregistered domain gap is explicit and cannot hide a worker response."""
        item, frame, _ = fixture('context-invalid-policyVersion')
        record = result(item, frame, 'W1')
        for key in ('responseBase64', 'responseBytes', 'responseSha256', 'responseCapture'):
            record.pop(key)
        record.update(outcome='BINDING_INPUT_REJECTED', noPrivateHandoff=True, noWorkerStarted=True,
                      outputEquivalence='NOT_COMPARABLE', rejectionCode='BLANK_POLICY_UNREACHABLE_INSTALLED_CONTEXT')
        self.assertIsNone(subject.response(record, item, frame, 'W1', BUILD))
        for key, value in [('outcome', 'WORKER_UNAVAILABLE'), ('noPrivateHandoff', False),
                           ('noWorkerStarted', False), ('responseBase64', ''), ('outputEquivalence', 'PASS')]:
            with self.subTest(field=key):
                with self.assertRaises(ValueError):
                    subject.response(dict(record, **{key: value}), item, frame, 'W1', BUILD)

    def test_no_group_binding_receipt_has_no_actual_child_claim(self):
        """No allocated worker is distinct from positive emptiness or an unbound child identity."""
        item, _, _, owned, row = self.specimen('W1', 'context-invalid-policyVersion')
        owned.update(groups=[], noGroupAllocated=True)
        row.update(ownership=self.store(owned), identities=[])
        row['cleanup'].update(populatedZero=False, noGroupAllocated=True)
        subject.ownership(self.root, row, item, 'W1')
        for changed in (dict(row, identities=[DEAD]), dict(row, cleanup=dict(row['cleanup'], populatedZero=True))):
            with self.assertRaises(ValueError):
                subject.ownership(self.root, changed, item, 'W1')

    def test_input_limit_requires_specific_rejection_not_arbitrary_failure(self):
        """Both registered oversized inputs must reject before private transport, with finite cleanup."""
        for name in ('private-frame-2097152', 'private-frame-2097153'):
            item, frame, _ = fixture(name)
            for variant in ('W0', 'W1'):
                record = result(item, frame, variant)
                for key in ('responseBase64', 'responseBytes', 'responseSha256', 'responseCapture'):
                    record.pop(key)
                record.update(outcome='INPUT_REJECTED', noPrivateHandoff=True, noWorkerStarted=variant == 'W0',
                              rejectionCode='PRIVATE_INPUT_LIMIT')
                if variant == 'W1':
                    record['boundaryObservation'] = 'ACTUAL_POOL_ENCODER_EXCEPTION_BEFORE_EXCHANGE'
                self.assertIsNone(subject.response(record, item, frame, variant, BUILD))
                for key, value in [('outcome', 'WORKER_UNAVAILABLE'), ('noPrivateHandoff', False),
                                   ('rejectionCode', 'UNRELATED_FAILURE'), ('responseBase64', '')]:
                    with self.subTest(name=name, variant=variant, field=key):
                        with self.assertRaises(ValueError):
                            subject.response(dict(record, **{key: value}), item, frame, variant, BUILD)

    def test_exact_oversized_original_fixture_can_be_checked_without_response_cap(self):
        """Request parsing handles the registered2MiB boundary without using the1MiB response cap."""
        for name in ('private-frame-2097152', 'private-frame-2097153'):
            item, _, record, owned, row = self.specimen('W0', name)
            for key in ('responseBase64', 'responseBytes', 'responseSha256', 'responseCapture'):
                record.pop(key)
            record.update(outcome='INPUT_REJECTED', noWorkerStarted=True, noPrivateHandoff=True,
                          rejectionCode='PRIVATE_INPUT_LIMIT')
            row.update(record=self.store(record), identities=[])
            checked = subject.check_row(self.root, {'build_identity': {'value': BUILD}}, item, row, 'W0')
            self.assertEqual('INPUT_REJECTED', checked['outcome'])

    def test_history_uses_strict_types_and_exact_source(self):
        """History cannot quietly change source, module types or stable location/trivia fields."""
        base = {'mode': 'TEXT_ONLY', 'source': 'sig A {}', 'sourceHash': hashlib.sha256(b'sig A {}').hexdigest(),
                'module': None, 'occurrences': [], 'trivia': []}
        frame = {'candidate': None, 'baseArtifact': base}
        response = {'data': copy.deepcopy(base)}
        subject.content_oracle(response, frame, {'historicalExact': True})
        for key, value in [('source', 'sig B {}'), ('module', False), ('occurrences', False), ('trivia', {})]:
            changed = {'data': dict(base, **{key: value})}
            with self.assertRaises(ValueError):
                subject.content_oracle(changed, frame, {'historicalExact': True})

    def test_actual_corpus_keeps_exact_one_noncomparable_row(self):
        """The frozen domain gap is one explicit blank-policy row, not a wildcard exclusion."""
        gaps = [row for row in PLAN['fixtures'] if row['comparison'] == 'NOT_COMPARABLE']
        self.assertEqual(['context-invalid-policyVersion'], [row['name'] for row in gaps])
        self.assertEqual(189, sum(row['comparison'] != 'NOT_COMPARABLE' for row in PLAN['fixtures']))
        item, frame, _ = fixture('context-invalid-policyVersion')
        left = {'protocol': 1, 'requestId': frame['requestId'], 'status': 'UNAVAILABLE', 'data': {}}
        compared = subject.compare_case(item, frame, left, None)
        self.assertEqual('NOT_COMPARABLE', compared['status'])
        with self.assertRaises(ValueError):
            subject.compare_case(item, frame, left, left)

    def metadata_report(self, mutation=None, exit_code=0):
        """Prepare only top-level synthetic metadata; fixture and row checks are explicitly mocked."""
        self.serial += 1
        root = self.root/f'metadata-{self.serial}'
        write_private(root/'.gate/semantic-fixtures.json', PLAN)
        report = {'schema': 1, 'status': 'PASS', 'variant': 'W0', 'buildIdentity': BUILD,
                  'caseManifestSha256': digest(root/'.gate/semantic-fixtures.json'),
                  'contextBoundary': subject.CONTEXT, 'selectedRuntimeRoute': 'NOT_TESTED_PRODUCTION_DISABLED',
                  'classification': 'FINITE_CASE_CHECKS_NOT_PAIRWISE_EQUIVALENCE', 'cases': [{} for _ in range(190)]}
        report.update(mutation or {})
        write_private(root/'.gate/evidence/semantic-java.json', report)
        write_private(root/'.gate/evidence/semantic-complete.json', {'status': 'COMPLETE', 'exit_code': exit_code,
                      'probe_reaped': True, 'java_report_sha256': digest(root/'.gate/evidence/semantic-java.json')})
        return root

    def test_report_trust_labels_counts_and_integer_exit_are_checked(self):
        """Metadata-only tests prevent finite checks from being relabeled full production equivalence."""
        with patch.object(subject.semantic_plan, 'verify'), patch.object(subject, 'check_row', return_value={'status': 'PASS'}):
            actual = subject.verify_variant(self.metadata_report(), {'build_identity': {'value': BUILD}}, 'W0')
            self.assertEqual('FINITE_CASE_CHECKS_NOT_PAIRWISE_EQUIVALENCE', actual['classification'])
            self.assertEqual('OPEN', actual['selected_runtime_route'])
            self.assertIs(False, actual['performance_evidence'])
            mutations = {'schema': True, 'status': 'VERIFIED', 'variant': 'W1', 'buildIdentity': '0'*64,
                         'caseManifestSha256': '0'*64, 'contextBoundary': 'ACTUAL_SQL_CLEAN',
                         'selectedRuntimeRoute': 'PRODUCTION_ENABLED', 'classification': 'FULL_EQUIVALENCE',
                         'cases': [{} for _ in range(189)]}
            for key, value in mutations.items():
                with self.subTest(field=key):
                    with self.assertRaises(ValueError):
                        subject.verify_variant(self.metadata_report({key: value}), {'build_identity': {'value': BUILD}}, 'W0')
            with self.assertRaises(ValueError):
                subject.verify_variant(self.metadata_report(exit_code=False), {'build_identity': {'value': BUILD}}, 'W0')

    def aggregate_rows(self):
        """Build only already-checked synthetic comparison summaries for finite aggregate tests."""
        rows = []
        for item in PLAN['fixtures']:
            row = {'id': item['name'], 'status': 'PASS'}
            if item['comparison'] == 'NOT_COMPARABLE':
                row['status'] = 'NOT_COMPARABLE'
            elif item.get('expectedProbeReject'):
                row['comparison'] = 'EXPLICIT_INPUT_LIMIT_REJECTION'
            else:
                row['full_response_equal'] = True
            rows.append(row)
        return rows

    def test_aggregate189_case_outcomes_and_one_gap_always_remain_blocked(self):
        """Expected finite checks cannot promote the preregistered noncomparable corpus row."""
        report = semantic_runner.aggregate(self.aggregate_rows(), PLAN['fixtures'])
        self.assertEqual('PASS', report['finite_expected_checks'])
        self.assertEqual(189, report['comparable_passed'])
        self.assertEqual(187, report['full_response_pairs_passed'])
        self.assertEqual(2, report['matching_input_rejections'])
        self.assertEqual(['context-invalid-policyVersion'], report['not_comparable'])
        self.assertEqual('BLOCKED', report['status'])
        self.assertEqual('BLOCKED', report['whole190_pairwise_equivalence'])
        self.assertEqual('OPEN', report['selected_runtime_route'])
        self.assertEqual('OPEN', report['sql_route'])
        self.assertIs(False, report['performance_evidence'])
        self.assertIs(False, report['promotion_authorized'])

    def test_aggregate_rejects_missing_reordered_and_duplicate_cases(self):
        """Finite aggregation requires the complete frozen identity sequence, not merely190 rows."""
        original = self.aggregate_rows()
        duplicate = copy.deepcopy(original); duplicate[1] = copy.deepcopy(duplicate[0])
        for rows in (original[:-1], list(reversed(original)), duplicate):
            with self.assertRaises(ValueError):
                semantic_runner.aggregate(rows, PLAN['fixtures'])

    def test_aggregate_does_not_hide_failures_or_move_the_domain_gap(self):
        """Any additional failure or a reclassified blank-policy row blocks finite expected checks."""
        original = self.aggregate_rows()
        mutations = []
        changed = copy.deepcopy(original); changed[0]['status'] = 'BLOCKED'; mutations.append(changed)
        changed = copy.deepcopy(original); changed[0]['status'] = 'NOT_COMPARABLE'; mutations.append(changed)
        changed = copy.deepcopy(original); changed[0]['full_response_equal'] = False; mutations.append(changed)
        changed = copy.deepcopy(original)
        next(row for row in changed if row.get('comparison') == 'EXPLICIT_INPUT_LIMIT_REJECTION')['comparison'] = 'OTHER'
        mutations.append(changed)
        changed = copy.deepcopy(original)
        next(row for row in changed if row['id'] == 'context-invalid-policyVersion')['status'] = 'PASS'
        mutations.append(changed)
        for rows in mutations:
            report = semantic_runner.aggregate(rows, PLAN['fixtures'])
            self.assertEqual('BLOCKED', report['finite_expected_checks'])
            self.assertEqual('BLOCKED', report['status'])

    def comparison_with_mutation(self, mutation, input_failure=False):
        """Mock only I/O/row decoding to exercise actual terminal comparison and failure preservation."""
        prerequisite = [{'path': str(self.root/'ownership/manifest.json'), 'sha256': '2'*64}]
        frozen = {'input_root_sha256': '3'*64, 'ownership_prerequisite': prerequisite}
        manifest = {'build_identity': {'value': BUILD}}
        verified = {'cases': [{'record': {}} for _ in range(190)]}
        checked = {v: (self.root, manifest, verified, {'path': v, 'sha256': '4'*64}) for v in ('W0', 'W1')}
        terminal = copy.deepcopy(checked)
        if mutation == 'variant':
            terminal['W1'] = (*terminal['W1'][:3], {'path': 'W1', 'sha256': '5'*64})
        pointer = {'path': str(self.root/'registration.json'), 'sha256': '6'*64}
        registrations = [(self.root, frozen), FileNotFoundError('removed registration')
                         if mutation == 'registration' else (self.root, frozen)]
        with ExitStack() as stack:
            stack.enter_context(patch.object(semantic_runner, 'registered', side_effect=registrations))
            observer = stack.enter_context(patch.object(semantic_runner, 'record', return_value=pointer))
            stack.enter_context(patch.object(semantic_runner, 'compare_variant_inputs', side_effect=[checked, terminal]))
            stack.enter_context(patch.object(semantic_runner, 'read_private', return_value=PLAN))
            stack.enter_context(patch.object(semantic_runner, 'ownership_prerequisite',
                                            return_value=[] if mutation == 'prerequisite' else prerequisite))
            frames = [FileNotFoundError('removed fixture'), *[{} for _ in range(189)]] if input_failure else [{} for _ in range(190)]
            stack.enter_context(patch.object(subject, 'input_frame', side_effect=frames))
            stack.enter_context(patch.object(subject, 'private_result', return_value={}))
            stack.enter_context(patch.object(subject, 'response', return_value=None))
            stack.enter_context(patch.object(subject, 'compare_case', side_effect=self.comparison_outcome))
            written = stack.enter_context(patch.object(semantic_runner, 'write_private'))
            semantic_runner.compare_all(SimpleNamespace(suite=self.root))
            written.assert_called_once()
            observer.assert_called_once_with(self.root/'registration.json')
            return written.call_args.args[1], pointer

    def comparison_outcome(self, item, frame, left, right):
        """Return a synthetic already-verified row while leaving terminal aggregation real."""
        return next(row for row in self.aggregate_rows() if row['id'] == item['name'])

    def test_terminal_variant_prerequisite_and_registration_mutations_preserve_blocked_report(self):
        """Changed terminal evidence cannot retain finite PASS or erase the bound registration pointer."""
        for mutation in ('variant', 'prerequisite', 'registration'):
            with self.subTest(mutation=mutation):
                report, pointer = self.comparison_with_mutation(mutation)
                self.assertEqual('BLOCKED', report['finite_expected_checks'])
                self.assertEqual('BLOCKED', report['terminal_input_and_evidence_recheck'])
                self.assertEqual(['TERMINAL_INPUT_OR_EVIDENCE_CHANGED'], report['blocking_reasons'])
                self.assertEqual(pointer, report['registration'])
                self.assertEqual(190, len(report['cases']))

    def test_input_and_terminal_registration_deletion_preserve_all_case_failures(self):
        """An unreadable fixture and later registration deletion still produce immutable finite failure evidence."""
        report, pointer = self.comparison_with_mutation('registration', input_failure=True)
        self.assertEqual('BLOCKED', report['status'])
        self.assertEqual('BLOCKED', report['finite_expected_checks'])
        self.assertEqual(190, len(report['cases']))
        self.assertEqual(PLAN['fixtures'][0]['name'], report['cases'][0]['id'])
        self.assertEqual('BLOCKED', report['cases'][0]['status'])
        self.assertEqual('FileNotFoundError', report['cases'][0]['failure_class'])
        self.assertEqual(pointer, report['registration'])

    def test_invalid_source_null_expected_mode_requires_absent_mode(self):
        """All five actual registered invalid SOURCE cases allow no mode field in the closed error body."""
        names = [row['name'] for row in PLAN['fixtures'] if 'expectedMode' in row and row['expectedMode'] is None]
        self.assertEqual(5, len(names))
        for name in names:
            item, frame, _ = fixture(name)
            value = {'protocol': 1, 'requestId': frame['requestId'], 'status': 'INVALID',
                     'data': {'code': 'INVALID_SOURCE', 'diagnostics': []}}
            for variant in ('W0', 'W1'):
                with self.subTest(name=name, variant=variant):
                    checked = subject.response(result(item, frame, variant, value), item, frame, variant, BUILD)
                    self.assertEqual('INVALID', checked['status'])
                    self.assertNotIn('mode', checked['data'])
                    for mode in (None, 'TEXT_ONLY', 'BLOCK_SUPPORTED'):
                        changed = copy.deepcopy(value)
                        changed['data']['mode'] = mode
                        with self.assertRaises((ValueError, AssertionError)):
                            subject.response(result(item, frame, variant, changed), item, frame, variant, BUILD)

    def test_nonnull_expected_mode_still_requires_exact_mode(self):
        """The null error-body exception does not weaken a validated result's declared support mode."""
        item, frame, _ = fixture('source-text-only')
        source = frame['candidate']['source']
        value = {'protocol': 1, 'requestId': frame['requestId'], 'status': 'VALIDATED', 'data': {
            'mode': 'TEXT_ONLY', 'source': source, 'sourceHash': hashlib.sha256(source.encode()).hexdigest(),
            'module': None, 'occurrences': [], 'trivia': [], 'analysisDescriptors': [],
            'diagnostics': [], 'idRemapping': {}}}
        for variant in ('W0', 'W1'):
            checked = subject.response(result(item, frame, variant, value), item, frame, variant, BUILD)
            self.assertEqual('TEXT_ONLY', checked['data']['mode'])
            changed = dict(item, expectedMode='BLOCK_SUPPORTED')
            with self.assertRaisesRegex(ValueError, 'semantic_expected_mode'):
                subject.response(result(changed, frame, variant, value), changed, frame, variant, BUILD)


if __name__ == '__main__':
    unittest.main()
