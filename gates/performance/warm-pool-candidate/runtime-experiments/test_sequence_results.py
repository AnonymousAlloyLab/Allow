"""Independent synthetic checks of lifecycle evidence; no process or SQL acceptance is implied."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import sequence_results as subject
import probe_results
from harness_common import digest, write_private

HERE = Path(__file__).resolve().parent
POOL = '00000000-0000-4000-8000-000000000042'
BUILD = '1' * 64


def packed(value):
    """Encode a finite compact synthetic frame without a transport delimiter."""
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def fixture(name):
    """Read the already frozen public corpus fixture for independent expectation construction."""
    raw = (HERE/'fixtures/semantic'/name).read_bytes()
    return json.loads(raw), raw


def plan(aba=True):
    """Build the independently stated two approved finite case plans."""
    names = [('source-supported.json', 'BLOCK_SUPPORTED')]
    if aba:
        names += [('source-text-only.json', 'TEXT_ONLY'), ('source-supported.json', 'BLOCK_SUPPORTED')]
    value = {'id': 'sequence-refill-aba' if aba else 'idle-expiry-demand',
             'kind': ('SAME_INCARNATION_ONE_USE_REFILL_ABA' if aba
                      else 'REAL_IDLE_EXPIRY_NO_SELF_REFILL_NEW_DEMAND'),
             'expected_group_count': 4 if aba else 3, 'steps': [],
             'expected_cleanup': 'PASS', 'expected_capacity_retained': False}
    for name, mode in names:
        _, raw = fixture(name)
        value['steps'].append({'fixture': 'fixtures/semantic/'+name,
                              'fixture_sha256': hashlib.sha256(raw).hexdigest(), 'expected_mode': mode})
    if not aba:
        value.update(idle_duration_ns=30_000_000_000, quiet_duration_ns=2_000_000_000)
    return value


def bind_payload(row, prefix, value=None, raw=None):
    """Rehash changed synthetic evidence so tests exercise meaning beyond digest equality."""
    raw = packed(value) if raw is None else raw
    row.update({prefix+'Base64': base64.b64encode(raw).decode(), prefix+'Bytes': len(raw),
                prefix+'Sha256': hashlib.sha256(raw).hexdigest()})


def decoded(row, prefix):
    """Decode one synthetic complete payload for controlled adversarial changes."""
    return json.loads(base64.b64decode(row[prefix+'Base64']))


def worker(number):
    """Use unique nonexistent process identities and contiguous per-slot generations."""
    slot, generation = number % 2, number // 2 + 1
    return {'slot': slot, 'generation': generation,
            'workerNonce': f'00000000-0000-4000-8000-{number + 100:012d}',
            'group': f'pool-{POOL}/slot-{slot}-g{generation}',
            'pid': 1073741800 + number, 'start_ticks': str(100 + number)}


def group(identity):
    """Supply complete synthetic bootstrap and terminal metadata for independent replay."""
    value = {'slot': identity['slot'], 'generation': identity['generation'], 'group': identity['group'],
             'device': 11, 'inode': identity['pid'], 'pid': identity['pid'], 'startTicks': identity['start_ticks'],
             'finalPhase': 'RELEASED', 'directChildReaped': True, 'exitCode': 0}
    value['productionBootstrapMetadata'] = {
        'poolNonce': POOL, 'workerNonce': identity['workerNonce'], 'slot': identity['slot'],
        'generation': identity['generation'], 'childPid': identity['pid'], 'childStartTicks': identity['start_ticks'],
        'cgroupRoot': '/synthetic/cgroup', 'cgroupRelative': identity['group'],
        'cgroupDevice': value['device'], 'cgroupInode': value['inode']}
    value['terminalCounters'] = {
        'cgroup.events': 'populated 0\nfrozen 0\n', 'memory.peak': '1048576\n',
        'memory.events': 'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n',
        'pids.peak': '4\n', 'pids.events': 'max 0\n', 'cpu.stat': 'usage_usec 3\n'}
    return value


def response(frame, mode, index):
    """Create a closed synthetic response whose fresh IDs differ while its public graph is stable."""
    module = None
    if mode == 'BLOCK_SUPPORTED':
        module = {'version': 1, 'signatures': [{
            'tag': 'signature', 'id': f'server:00000000-0000-4000-8000-{index + 200:012d}',
            'name': 'A', 'multiplicity': 'set'}],
            'fields': [], 'predicates': [], 'facts': [], 'assertions': [], 'commands': [], 'nodes': []}
    source = frame['candidate']['source']
    return {'protocol': 1, 'requestId': frame['requestId'], 'status': 'VALIDATED', 'data': {
        'mode': mode, 'source': source, 'sourceHash': hashlib.sha256(source.encode()).hexdigest(),
        'module': module, 'occurrences': [], 'trivia': [], 'analysisDescriptors': [],
        'diagnostics': [], 'idRemapping': {}}}


def step(planned, index, selected, replacement, admission):
    """Build one independent complete request/reply and its observed one-use lifecycle."""
    frame, _ = fixture(Path(planned['fixture']).name)
    nonce = f'00000000-0000-4000-8000-{index + 300:012d}'
    frame['requestId'] = nonce
    ready = admission + 100_000_000 if index == 0 else admission - 500_000_000
    row = dict(planned, index=index, requestId=nonce, status='VALIDATED', mode=planned['expected_mode'],
               admissionNanos=admission, beforeDemandReservations=0 if index == 0 else 1,
               phaseBeforeValidate='STARTING' if index == 0 else 'READY', transportReadyNanos=ready,
               idleDeadlineNanos=ready+30_000_000_000, selected=selected, replacement=replacement,
               phaseAfterPublish='RELEASED', published=True, publishedNanos=admission+200_000_000,
               frameObservation='PRODUCTION_ENCODER_RECONSTRUCTION_NOT_PIPE_CAPTURE',
               responseCapture='RESERIALIZED_COMPLETE_POOL_RESPONSE')
    bind_payload(row, 'frame', frame)
    bind_payload(row, 'response', response(frame, planned['expected_mode'], index))
    return row


def specimen(aba=True):
    """Construct both finite receipt families without executing a worker, SQL or real timer."""
    item = plan(aba)
    workers = [worker(number) for number in range(item['expected_group_count'])]
    offset = 0 if aba else 1
    admission = 1_000_000_000 if aba else 33_300_000_000
    rows = [step(planned, index, workers[index+offset], workers[index+offset+1],
                 admission+index*1_000_000_000) for index, planned in enumerate(item['steps'])]
    lifecycle = {'kind': item['kind'], 'initialReservations': 0, 'steps': rows,
                 'observations': [{'label': 'initial', 'observedNanos': 1, 'reservations': 0,
                                   'unassigned': 0, 'active': 0, 'online': True}]}
    if not aba:
        lifecycle['idle'] = {'expired': workers[0], 'transportReadyNanos': 1_000_000_000,
            'idleDeadlineNanos': 31_000_000_000,
            'phaseSamples': [{'observedNanos': 1_000_000_000, 'phase': 'READY', 'reservations': 1},
                             {'observedNanos': 31_100_000_000, 'phase': 'RELEASED', 'reservations': 0}],
            'releasedObservedNanos': 31_100_000_000, 'quietStartNanos': 31_200_000_000,
            'quietEndNanos': 33_200_000_000, 'generationsBefore': [1, 0], 'generationsAfter': [1, 0],
            'quietSamples': [{'observedNanos': 31_200_000_000, 'reservations': 0, 'online': True},
                             {'observedNanos': 33_200_000_000, 'reservations': 0, 'online': True}],
            'noBeginDuringQuiet': True, 'terminalCleanupObservedBeforeQuiet': True, 'redemandNanos': admission}
    value = {'contextBoundary': 'TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL', 'poolNonce': POOL,
             'ledgerOnline': True, 'remainingReservations': 0,
             'groups': [group(identity) for identity in workers], 'lifecycle': lifecycle}
    result = {'id': item['id'], 'status': 'PASS', 'classification': item['kind'],
              'identities': [{'pid': identity['pid'], 'start_ticks': identity['start_ticks']} for identity in workers],
              'cleanup': {'status': 'PASS', 'capacityRetained': False, 'directChildReaped': True,
                          'populatedZero': True}, 'evidence': []}
    return item, value, result


class SequencePlanTests(unittest.TestCase):
    """Reject test plans that silently change the approved fixtures or real idle durations."""

    def test_original_two_plans_are_accepted(self):
        """Both concrete case shapes have nonvacuous exact registered inputs."""
        subject.check_plan(HERE, plan())
        subject.check_plan(HERE, plan(False))

    def test_missing_reordered_or_surplus_steps_are_rejected(self):
        """ABA order is significant even when every individual fixture hash is correct."""
        cases = []
        changed = plan(); changed['steps'].pop(); cases.append(changed)
        changed = plan(); changed['steps'].reverse(); changed['steps'][0], changed['steps'][1] = changed['steps'][1], changed['steps'][0]; cases.append(changed)
        changed = plan(); changed['steps'].append(copy.deepcopy(changed['steps'][0])); cases.append(changed)
        for changed in cases:
            with self.subTest(steps=len(changed['steps'])):
                with self.assertRaises((ValueError, AssertionError)):
                    subject.check_plan(HERE, changed)

    def test_fixture_mode_hash_path_and_group_count_are_exact(self):
        """A rehashed or relabeled fixture cannot change the expected test surface."""
        for field, value in [('fixture_sha256', '0'*64), ('expected_mode', 'TEXT_ONLY'),
                             ('fixture', 'fixtures/semantic/source-text-only.json')]:
            changed = plan(); changed['steps'][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises((ValueError, AssertionError)):
                    subject.check_plan(HERE, changed)
        for count in (3, 5, True):
            with self.assertRaises(ValueError):
                subject.check_plan(HERE, dict(plan(), expected_group_count=count))

    def test_real_idle_and_quiet_intervals_cannot_be_shortened_or_coerced(self):
        """The test must retain production30s expiry and the registered2s observation interval."""
        for field in ('idle_duration_ns', 'quiet_duration_ns'):
            for value in (1, True, 30_000_000_000.0):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        subject.check_plan(HERE, dict(plan(False), **{field: value}))


class SequenceEvidenceTests(unittest.TestCase):
    """Replay complete synthetic private receipts through the real composed case verifier."""

    def setUp(self):
        """Keep each synthetic mutation in an isolated private evidence directory."""
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-sequence-oracle-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.serial = 0

    def replay(self, item, value, result):
        """Bind fresh private evidence bytes and invoke the same public replay path as runtime."""
        self.serial += 1
        root = self.root/str(self.serial)
        for planned in item['steps']:
            path = root/'.gate'/planned['fixture']
            if not path.exists():
                path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                path.write_bytes((HERE/planned['fixture']).read_bytes())
                path.chmod(0o600)
        write_private(root/'.runtime/warm-pool/config.json',
                      {'cgroupRoot': '/synthetic/cgroup', 'rootDevice': 11, 'rootInode': 10})
        ownership = root/'.gate/evidence'/(item['id']+'-ownership.json')
        write_private(ownership, value)
        result = dict(result, evidence=[{'path': ownership.name, 'sha256': digest(ownership)}])
        return probe_results.case_result(root, item, result)

    def rejected(self, item, value, result):
        """Require a changed receipt to fail closed, including missing mandatory evidence fields."""
        with self.assertRaises((ValueError, AssertionError, KeyError, TypeError)):
            self.replay(item, value, result)

    def test_both_complete_receipt_families_have_positive_witnesses(self):
        """The rejection suite starts with accepted full receipts for ABA and actual-duration idle shapes."""
        for aba in (True, False):
            with self.subTest(aba=aba):
                item, value, result = specimen(aba)
                self.assertEqual('PASS', self.replay(item, value, result)['status'])
        rows = specimen()[1]['lifecycle']['steps']
        self.assertNotEqual(decoded(rows[0], 'response')['data']['module']['signatures'][0]['id'],
                            decoded(rows[2], 'response')['data']['module']['signatures'][0]['id'])

    def test_selected_and_refill_must_name_distinct_exact_owned_generations(self):
        """Reuse, disconnected refill and altered identity components cannot satisfy the chain."""
        for part in ('selected', 'replacement'):
            for field, wrong in [('slot', True), ('generation', 99), ('workerNonce', POOL),
                                 ('group', 'pool-foreign/slot-0-g1'), ('pid', 42), ('start_ticks', '999')]:
                item, value, result = specimen()
                value['lifecycle']['steps'][1][part][field] = wrong
                with self.subTest(part=part, field=field):
                    self.rejected(item, value, result)
        for replacement in ('selected', 'prior_selected'):
            item, value, result = specimen()
            rows = value['lifecycle']['steps']
            rows[1]['replacement'] = copy.deepcopy(rows[1 if replacement == 'selected' else 0]['selected'])
            self.rejected(item, value, result)
        item, value, result = specimen()
        value['lifecycle']['steps'][1]['selected'] = copy.deepcopy(value['lifecycle']['steps'][2]['replacement'])
        self.rejected(item, value, result)

    def test_exact_child_bootstrap_and_terminal_receipts_cannot_be_substituted(self):
        """An unrelated empty group or unreaped child never authorizes the selected worker's release."""
        for field, wrong in [('pid', 42), ('startTicks', '999'), ('directChildReaped', False),
                             ('exitCode', False), ('finalPhase', 'UNKNOWN'), ('device', 99), ('inode', 0)]:
            item, value, result = specimen()
            value['groups'][0][field] = wrong
            with self.subTest(field=field):
                self.rejected(item, value, result)
        for field, wrong in [('poolNonce', 'foreign'), ('workerNonce', POOL), ('childPid', 42),
                             ('childStartTicks', '999'), ('slot', 1), ('generation', 2),
                             ('cgroupRoot', '/other'), ('cgroupRelative', 'other'),
                             ('cgroupDevice', 99), ('cgroupInode', 999)]:
            item, value, result = specimen()
            value['groups'][0]['productionBootstrapMetadata'][field] = wrong
            with self.subTest(bootstrap_field=field):
                self.rejected(item, value, result)

    def test_same_process_or_worker_nonce_cannot_reappear_in_another_generation(self):
        """Coherently renaming all links still cannot reuse one process incarnation or bootstrap nonce."""
        for kind in ('pid', 'workerNonce'):
            item, value, result = specimen()
            rows, groups = value['lifecycle']['steps'], value['groups']
            if kind == 'pid':
                for identity in (rows[1]['replacement'], rows[2]['selected']):
                    identity.update(pid=groups[0]['pid'], start_ticks=groups[0]['startTicks'])
                groups[2].update(pid=groups[0]['pid'], startTicks=groups[0]['startTicks'])
                groups[2]['productionBootstrapMetadata'].update(
                    childPid=groups[0]['pid'], childStartTicks=groups[0]['startTicks'])
                result['identities'][2] = copy.deepcopy(result['identities'][0])
            else:
                nonce = groups[0]['productionBootstrapMetadata']['workerNonce']
                rows[1]['replacement']['workerNonce'] = nonce
                rows[2]['selected']['workerNonce'] = nonce
                groups[2]['productionBootstrapMetadata']['workerNonce'] = nonce
            self.rejected(item, value, result)

    def test_missing_duplicate_surplus_groups_or_process_inventory_are_rejected(self):
        """All allocated generations require exactly one matching process and terminal group receipt."""
        for target in ('groups', 'identities'):
            for operation in ('missing', 'duplicate', 'surplus'):
                item, value, result = specimen()
                values = value['groups'] if target == 'groups' else result['identities']
                if operation == 'missing':
                    values.pop()
                elif operation == 'duplicate':
                    values[-1] = copy.deepcopy(values[0])
                else:
                    values.append(copy.deepcopy(values[0]))
                with self.subTest(target=target, operation=operation):
                    self.rejected(item, value, result)

    def test_contiguous_generation_counters_reject_hidden_transient_reservations(self):
        """A coherent group/nonce rename cannot conceal a skipped reservation number in either slot."""
        item, value, result = specimen()
        rows, target = value['lifecycle']['steps'], value['groups'][2]
        new_name = f'pool-{POOL}/slot-0-g3'
        for identity in (rows[1]['replacement'], rows[2]['selected']):
            identity.update(generation=3, group=new_name)
        target.update(generation=3, group=new_name)
        target['productionBootstrapMetadata'].update(generation=3, cgroupRelative=new_name)
        self.rejected(item, value, result)

    def test_private_frame_requires_exact_fixture_and_original_operation_nonce(self):
        """Rehashed frames cannot borrow a response nonce or change source, policy, context or operation."""
        for field, wrong in [('requestId', POOL), ('operation', 'REVALIDATE'), ('policyVersion', 'changed'),
                             ('candidate', {'mode': 'SOURCE', 'source': 'sig B {}'}),
                             ('ownedIdInventory', {'extra': []}), ('protocol', True), ('extra', None)]:
            item, value, result = specimen()
            row = value['lifecycle']['steps'][1]
            frame = decoded(row, 'frame'); frame[field] = wrong
            bind_payload(row, 'frame', frame)
            with self.subTest(field=field):
                self.rejected(item, value, result)
        item, value, result = specimen()
        row = value['lifecycle']['steps'][0]
        frame = decoded(row, 'frame'); del frame['requestId']
        bind_payload(row, 'frame', frame)
        self.rejected(item, value, result)

    def test_full_response_nonce_source_mode_hash_and_closed_shape_are_checked(self):
        """Correct rehashing never repairs a swapped request, altered source, mode or closed envelope."""
        mutations = [('requestId', POOL), ('protocol', True), ('status', 'UNAVAILABLE'), ('extra', 1)]
        for field, wrong in mutations:
            item, value, result = specimen()
            row = value['lifecycle']['steps'][0]
            response_value = decoded(row, 'response'); response_value[field] = wrong
            bind_payload(row, 'response', response_value)
            with self.subTest(field=field):
                self.rejected(item, value, result)
        for field, wrong in [('source', 'sig B {}'), ('mode', 'TEXT_ONLY'), ('sourceHash', '0'*64), ('extra', None)]:
            item, value, result = specimen()
            row = value['lifecycle']['steps'][0]
            response_value = decoded(row, 'response'); response_value['data'][field] = wrong
            if field == 'source':
                response_value['data']['sourceHash'] = hashlib.sha256(wrong.encode()).hexdigest()
            bind_payload(row, 'response', response_value)
            with self.subTest(data_field=field):
                self.rejected(item, value, result)

    def test_repeated_request_nonce_is_rejected_even_when_both_payloads_are_coherent(self):
        """The ABA equality normalization cannot silently reuse an operation identity."""
        item, value, result = specimen()
        rows = value['lifecycle']['steps']
        rows[2]['requestId'] = rows[0]['requestId']
        for prefix in ('frame', 'response'):
            payload = decoded(rows[2], prefix); payload['requestId'] = rows[0]['requestId']
            bind_payload(rows[2], prefix, payload)
        self.rejected(item, value, result)

    def test_aba_full_response_comparison_rejects_graph_and_diagnostic_drift(self):
        """A repeat comparison preserves every schema field beyond its declared fresh ID bijection."""
        for mutation in ('signature_name', 'multiplicity', 'diagnostic', 'additional_signature'):
            item, value, result = specimen()
            row = value['lifecycle']['steps'][2]
            response_value = decoded(row, 'response')
            signature = response_value['data']['module']['signatures'][0]
            if mutation == 'diagnostic':
                response_value['data']['diagnostics'].append({'code': 'UNEXPECTED', 'message': 'changed'})
            elif mutation == 'additional_signature':
                response_value['data']['module']['signatures'].append(dict(signature, id='server:'+POOL, name='B'))
            else:
                signature['name' if mutation == 'signature_name' else 'multiplicity'] = 'changed'
            bind_payload(row, 'response', response_value)
            with self.subTest(mutation=mutation):
                self.rejected(item, value, result)

    def test_payload_hash_length_framing_duplicate_keys_and_nonfinite_are_strict(self):
        """A bounded reserialized object is distinct from pipe capture and must remain strict finite JSON."""
        for prefix in ('frame', 'response'):
            for suffix, wrong in [('Sha256', '0'*64), ('Bytes', True), ('Bytes', 1), ('Base64', '!!')]:
                item, value, result = specimen()
                value['lifecycle']['steps'][0][prefix+suffix] = wrong
                with self.subTest(prefix=prefix, field=suffix):
                    self.rejected(item, value, result)
            for mutation in ('newline', 'duplicate', 'nonfinite'):
                item, value, result = specimen()
                row = value['lifecycle']['steps'][0]
                raw = base64.b64decode(row[prefix+'Base64'])
                raw = (raw+b'\n' if mutation == 'newline' else
                       raw.replace(b'"protocol":1', b'"protocol":1,"protocol":1') if mutation == 'duplicate'
                       else raw.replace(b'"protocol":1', b'"protocol":NaN'))
                bind_payload(row, prefix, raw=raw)
                with self.subTest(prefix=prefix, mutation=mutation):
                    self.rejected(item, value, result)

    def test_capture_labels_and_fixture_links_are_exact(self):
        """Reconstructed frames and reserialized replies cannot be relabeled as raw pipe evidence."""
        for field, wrong in [('frameObservation', 'ACTUAL_PIPE_CAPTURE'), ('responseCapture', 'ACTUAL_STDOUT_FRAME'),
                             ('fixture_sha256', '0'*64), ('fixture', 'fixtures/semantic/source-text-only.json'),
                             ('status', 'PASS'), ('mode', 'TEXT_ONLY')]:
            item, value, result = specimen()
            value['lifecycle']['steps'][0][field] = wrong
            with self.subTest(field=field):
                self.rejected(item, value, result)

    def test_deadline_publication_and_ready_evidence_are_mutually_ordered(self):
        """Publication must follow actual readiness and precede the original admitted request deadline."""
        mutations = [('published', False), ('phaseAfterPublish', 'CLEAN'), ('publishedNanos', 999_999_999),
                     ('publishedNanos', 1_050_000_000), ('publishedNanos', 11_000_000_000),
                     ('transportReadyNanos', True), ('idleDeadlineNanos', 31_100_000_000.0),
                     ('idleDeadlineNanos', 1_100_000_001), ('beforeDemandReservations', True)]
        for field, wrong in mutations:
            item, value, result = specimen()
            value['lifecycle']['steps'][0][field] = wrong
            with self.subTest(field=field, wrong=wrong):
                self.rejected(item, value, result)
        for phase in ('STARTING', 'BUSY', 'RELEASED'):
            item, value, result = specimen()
            value['lifecycle']['steps'][1]['phaseBeforeValidate'] = phase
            self.rejected(item, value, result)
        item, value, result = specimen()
        row = value['lifecycle']['steps'][1]
        row.update(transportReadyNanos=row['admissionNanos']+1,
                   idleDeadlineNanos=row['admissionNanos']+30_000_000_001)
        self.rejected(item, value, result)

    def test_ready_hit_admission_cannot_follow_its_idle_expiry(self):
        """Even a ready worker's coherent deadline must not already have expired at the next admission."""
        item, value, result = specimen()
        row = value['lifecycle']['steps'][1]
        row.update(admissionNanos=row['idleDeadlineNanos'], publishedNanos=row['idleDeadlineNanos']+1)
        later = value['lifecycle']['steps'][2]
        later.update(admissionNanos=row['publishedNanos']+1, publishedNanos=row['publishedNanos']+2,
                     transportReadyNanos=row['publishedNanos'], idleDeadlineNanos=row['publishedNanos']+30_000_000_000)
        self.rejected(item, value, result)

    def test_capacity_samples_terminal_cleanup_and_trust_scope_remain_required(self):
        """Sampled bounds supplement exact cleanup receipts without replacing them with success labels."""
        for field, wrong in [('reservations', 3), ('unassigned', 2), ('active', 2),
                             ('online', False), ('observedNanos', True)]:
            item, value, result = specimen()
            value['lifecycle']['observations'][0][field] = wrong
            self.rejected(item, value, result)
        for target, field, wrong in [('value', 'remainingReservations', 1), ('value', 'ledgerOnline', False),
                                     ('value', 'contextBoundary', 'ACTUAL_SQL_CLEAN'),
                                     ('cleanup', 'directChildReaped', False), ('cleanup', 'capacityRetained', True),
                                     ('cleanup', 'populatedZero', False), ('cleanup', 'status', 'UNKNOWN')]:
            item, value, result = specimen()
            (value if target == 'value' else result['cleanup'])[field] = wrong
            self.rejected(item, value, result)
        for missing in ('lifecycle', 'groups'):
            item, value, result = specimen(); del value[missing]
            self.rejected(item, value, result)

    def test_kernel_terminal_empty_and_resource_counters_are_not_optional(self):
        """The composed replay checks kernel metadata independently of RELEASED and cleanup booleans."""
        mutations = [('cgroup.events', 'populated 1\n'), ('cgroup.events', 'frozen 0\n'),
                     ('memory.events', 'oom 1\noom_kill 0\noom_group_kill 0\n'),
                     ('pids.events', 'max 1\n'), ('pids.peak', '33\n'), ('memory.peak', '1073741825\n'),
                     ('cpu.stat', 'user_usec 1\n')]
        for field, wrong in mutations:
            item, value, result = specimen()
            value['groups'][0]['terminalCounters'][field] = wrong
            with self.subTest(counter=field):
                self.rejected(item, value, result)

    def test_idle_expiry_cannot_be_shortened_or_released_before_its_deadline(self):
        """Observed release must bracket the unchanged actual30s expiry and retain a READY observation."""
        mutations = [('idleDeadlineNanos', 2_000_000_000), ('transportReadyNanos', True),
                     ('releasedObservedNanos', 30_999_999_999), ('releasedObservedNanos', 34_000_000_001)]
        for field, wrong in mutations:
            item, value, result = specimen(False)
            value['lifecycle']['idle'][field] = wrong
            with self.subTest(field=field):
                self.rejected(item, value, result)
        for samples in ([{'observedNanos': 31_100_000_000, 'phase': 'RELEASED', 'reservations': 0}],
                        [{'observedNanos': 1_000_000_000, 'phase': 'READY', 'reservations': 1},
                         {'observedNanos': 30_999_999_999, 'phase': 'RELEASED', 'reservations': 0}]):
            item, value, result = specimen(False)
            value['lifecycle']['idle']['phaseSamples'] = samples
            self.rejected(item, value, result)

    def test_idle_phase_reversal_or_capacity_release_without_reaped_generation_is_rejected(self):
        """A released slot cannot return to READY and an expired child still requires exact cleanup."""
        item, value, result = specimen(False)
        rows = value['lifecycle']['idle']['phaseSamples']
        rows[1:1] = [{'observedNanos': 31_000_000_000, 'phase': 'RETIRING', 'reservations': 1},
                     {'observedNanos': 31_000_000_001, 'phase': 'READY', 'reservations': 1}]
        self.rejected(item, value, result)
        for field, wrong in [('finalPhase', 'UNKNOWN'), ('directChildReaped', False)]:
            item, value, result = specimen(False)
            value['groups'][0][field] = wrong
            self.rejected(item, value, result)

    def test_idle_quiet_interval_requires_endpoint_observations_and_no_demand(self):
        """Two samples at one instant cannot substantiate the registered2s quiet interval."""
        for mutation in ('shortened', 'missing', 'single', 'same_start', 'late_start', 'refill', 'offline',
                         'begin', 'cleanup_not_observed'):
            item, value, result = specimen(False)
            idle = value['lifecycle']['idle']
            if mutation == 'shortened': idle['quietEndNanos'] -= 1
            elif mutation == 'missing': idle['quietSamples'] = []
            elif mutation == 'single': idle['quietSamples'].pop()
            elif mutation == 'same_start': idle['quietSamples'][-1]['observedNanos'] = idle['quietStartNanos']
            elif mutation == 'late_start': idle['quietSamples'][0]['observedNanos'] += 1
            elif mutation == 'refill': idle['quietSamples'][1]['reservations'] = 1
            elif mutation == 'offline': idle['quietSamples'][1]['online'] = False
            elif mutation == 'begin': idle['noBeginDuringQuiet'] = False
            else: idle['terminalCleanupObservedBeforeQuiet'] = False
            with self.subTest(mutation=mutation):
                self.rejected(item, value, result)

    def test_idle_counter_vector_and_redemand_are_bound_to_the_expired_slot(self):
        """No transient reservation advance or swapped slot vector may hide inside a quiet interval."""
        for mutation in ('advanced', 'wrong_slot', 'boolean', 'redemand_early', 'admission_early', 'reuse'):
            item, value, result = specimen(False)
            idle = value['lifecycle']['idle']
            if mutation == 'advanced': idle['generationsAfter'] = [2, 0]
            elif mutation == 'wrong_slot': idle.update(generationsBefore=[0, 1], generationsAfter=[0, 1])
            elif mutation == 'boolean': idle.update(generationsBefore=[True, 0], generationsAfter=[True, 0])
            elif mutation == 'redemand_early': idle['redemandNanos'] = idle['quietEndNanos']-1
            elif mutation == 'admission_early': value['lifecycle']['steps'][0]['admissionNanos'] = idle['redemandNanos']-1
            else: value['lifecycle']['steps'][0]['selected'] = copy.deepcopy(idle['expired'])
            with self.subTest(mutation=mutation):
                self.rejected(item, value, result)


if __name__ == '__main__':
    unittest.main()
