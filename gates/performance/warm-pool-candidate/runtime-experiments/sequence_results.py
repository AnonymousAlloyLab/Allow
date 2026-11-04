"""Check finite same-incarnation lifecycle observations without claiming SQL or timing acceptance."""
import copy
import base64
import hashlib
import json
from pathlib import Path
import uuid

import compare_responses
from harness_common import digest, read_private

CASES = {'sequence-refill-aba', 'idle-expiry-demand'}


def require(value, reason):
    """Reject missing or inconsistent lifecycle evidence."""
    if not value:
        raise ValueError('sequence_' + reason)


def integer(value, minimum=0):
    """Keep booleans out of numeric observations."""
    return type(value) is int and value >= minimum


def check_plan(gate, item):
    """Require the exact finite fixtures and unchanged real idle durations before freezing."""
    require(item['id'] in CASES, 'plan_case')
    aba = item['id'] == 'sequence-refill-aba'
    expected = [('source-supported.json', 'BLOCK_SUPPORTED')]
    if aba:
        expected += [('source-text-only.json', 'TEXT_ONLY'), ('source-supported.json', 'BLOCK_SUPPORTED')]
    steps = item['steps']
    require(isinstance(steps, list) and len(steps) == len(expected), 'plan_steps')
    require(type(item['expected_group_count']) is int and item['expected_group_count'] == (4 if aba else 3),
            'plan_group_count')
    for row, (filename, mode) in zip(steps, expected):
        name = 'fixtures/semantic/' + filename
        require(row['fixture'] == name and row['expected_mode'] == mode
                and digest(gate/name) == row['fixture_sha256'], 'plan_fixture')
    if not aba:
        require(type(item['idle_duration_ns']) is int and item['idle_duration_ns'] == 30_000_000_000
                and type(item['quiet_duration_ns']) is int and item['quiet_duration_ns'] == 2_000_000_000,
                'plan_real_durations')


def identity(value, groups, pool):
    """Bind a selected process generation to its actual terminal and bootstrap receipts."""
    require(set(value) == {'slot', 'generation', 'workerNonce', 'group', 'pid', 'start_ticks'}, 'identity_shape')
    require(type(value['slot']) is int and value['slot'] in (0, 1)
            and integer(value['generation'], 1) and integer(value['pid'], 1)
            and isinstance(value['start_ticks'], str) and value['start_ticks'].isdigit(), 'identity_types')
    require(str(uuid.UUID(value['workerNonce'])) == value['workerNonce'], 'worker_nonce')
    name = f"pool-{pool}/slot-{value['slot']}-g{value['generation']}"
    require(value['group'] == name and name in groups, 'identity_group')
    group = groups[name]
    require(group['slot'] == value['slot'] and group['generation'] == value['generation']
            and group.get('pid') == value['pid'] and group.get('startTicks') == value['start_ticks']
            and group['finalPhase'] == 'RELEASED' and group.get('directChildReaped') is True
            and type(group.get('exitCode')) is int, 'identity_terminal')
    bootstrap = group['productionBootstrapMetadata']
    require(bootstrap['poolNonce'] == pool and bootstrap['workerNonce'] == value['workerNonce']
            and bootstrap['slot'] == value['slot'] and bootstrap['generation'] == value['generation']
            and bootstrap['childPid'] == value['pid'] and bootstrap['childStartTicks'] == value['start_ticks'],
            'identity_bootstrap')
    return name


def payload(row, prefix, limit):
    """Decode bounded exact reserialized evidence and require both byte count and digest."""
    encoded = row[prefix + 'Base64']
    require(isinstance(encoded, str) and len(encoded) <= 4 * ((limit + 2) // 3), 'payload_bound')
    raw = base64.b64decode(encoded, validate=True)
    require(integer(row[prefix + 'Bytes'], 1) and len(raw) == row[prefix + 'Bytes']
            and len(raw) < limit and hashlib.sha256(raw).hexdigest() == row[prefix + 'Sha256'], 'payload_identity')
    require(b'\n' not in raw and b'\r' not in raw, 'payload_framing')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=compare_responses.unique)
    compare_responses.finite(value)
    return value


def decode_step(root, planned, row):
    """Check exact original nonce and complete response before any cross-operation comparison."""
    require(row['fixture'] == planned['fixture'] and row['fixture_sha256'] == planned['fixture_sha256'],
            'step_fixture_binding')
    path = root/'.gate'/planned['fixture']
    require(digest(path) == planned['fixture_sha256'], 'step_fixture_bytes')
    fixture = read_private(path)
    frame = payload(row, 'frame', 2097152)
    response = payload(row, 'response', 1048577)
    require(str(uuid.UUID(row['requestId'])) == row['requestId'], 'operation_nonce')
    expected = copy.deepcopy(fixture)
    expected['requestId'] = row['requestId']
    require(compare_responses.identical(frame, expected), 'frame_fixture')
    require(row['frameObservation'] == 'PRODUCTION_ENCODER_RECONSTRUCTION_NOT_PIPE_CAPTURE'
            and row['responseCapture'] == 'RESERIALIZED_COMPLETE_POOL_RESPONSE', 'capture_scope')
    compare_responses.check_response(response, frame)
    require(response['status'] == row['status'] == 'VALIDATED'
            and response['data']['mode'] == row['mode'] == planned['expected_mode']
            and response['data']['source'] == fixture['candidate']['source'], 'expected_response')
    return frame, response


def observations(rows):
    """Check sampled capacity bounds without claiming continuous production telemetry."""
    require(isinstance(rows, list) and bool(rows), 'observations_missing')
    previous = 0
    for row in rows:
        require(isinstance(row['label'], str) and bool(row['label']) and integer(row['observedNanos'], previous),
                'observation_order')
        previous = row['observedNanos']
        require(integer(row['reservations']) and row['reservations'] <= 2
                and integer(row['unassigned']) and row['unassigned'] <= 1
                and integer(row['active']) and row['active'] <= 1
                and row['unassigned'] + row['active'] <= row['reservations']
                and row['online'] is True, 'observed_capacity')


def verify_steps(root, item, lifecycle, groups, pool):
    """Require one-use generation linkage and compare only the registered A repeat."""
    rows = lifecycle['steps']
    require(isinstance(rows, list) and len(rows) == len(item['steps']), 'step_count')
    frames, responses, ordered, nonces = [], [], [], []
    for index, (planned, row) in enumerate(zip(item['steps'], rows)):
        require(type(row['index']) is int and row['index'] == index, 'step_index')
        selected = identity(row['selected'], groups, pool)
        replacement = identity(row['replacement'], groups, pool)
        require(selected != replacement and (not ordered or selected == ordered[-1]), 'refill_link')
        if not ordered:
            ordered.append(selected)
        ordered.append(replacement)
        require(integer(row['beforeDemandReservations']) and row['beforeDemandReservations'] == (0 if index == 0 else 1),
                'demand_reservations')
        require(row['phaseBeforeValidate'] in {'STARTING', 'READY'}, 'validate_phase')
        if index:
            require(row['phaseBeforeValidate'] == 'READY', 'replacement_not_ready')
        require(integer(row['admissionNanos'], 1) and integer(row['publishedNanos'], row['admissionNanos'])
                and row['publishedNanos'] - row['admissionNanos'] < 10_000_000_000
                and row['published'] is True and row['phaseAfterPublish'] == 'RELEASED', 'publication')
        require(integer(row['transportReadyNanos'], 1) and type(row['idleDeadlineNanos']) is int
                and row['idleDeadlineNanos'] == row['transportReadyNanos'] + 30_000_000_000
                and row['publishedNanos'] >= row['transportReadyNanos'], 'ready_deadline')
        if index:
            require(row['admissionNanos'] > rows[index - 1]['publishedNanos']
                    and row['transportReadyNanos'] <= row['admissionNanos'] < row['idleDeadlineNanos'], 'admission_order')
        frame, response = decode_step(root, planned, row)
        frames.append(frame)
        responses.append(response)
        nonces.append(row['requestId'])
    require(len(set(nonces)) == len(nonces) and len(set(ordered)) == len(ordered), 'one_use_identity')
    if len(rows) == 3:
        first = copy.deepcopy(responses[0])
        first['requestId'] = rows[-1]['requestId']
        compare_responses.compare(first, responses[-1], frames[-1])
    return ordered


def verify_idle(item, lifecycle, groups, pool):
    """Check actual timer observations and durable evidence of no refill over a finite quiet interval."""
    idle = lifecycle['idle']
    expired = identity(idle['expired'], groups, pool)
    ready, deadline = idle['transportReadyNanos'], idle['idleDeadlineNanos']
    require(integer(ready, 1) and type(deadline) is int and deadline == ready + item['idle_duration_ns'], 'idle_deadline')
    rows = idle['phaseSamples']
    require(isinstance(rows, list) and len(rows) >= 2, 'idle_samples')
    previous, saw_ready, saw_released, phase_index = ready, False, False, 0
    for row in rows:
        now = row['observedNanos']
        require(integer(now, previous) and integer(row['reservations']) and row['reservations'] <= 1, 'idle_sample_order')
        previous = now
        require(row['phase'] in {'READY', 'RETIRING', 'CLEAN', 'RELEASED'}, 'idle_phase')
        next_phase = ('READY', 'RETIRING', 'CLEAN', 'RELEASED').index(row['phase'])
        require(next_phase >= phase_index, 'idle_phase_reversal')
        phase_index = next_phase
        if now < deadline:
            require(row['phase'] == 'READY' and row['reservations'] == 1, 'early_retirement_observed')
            saw_ready = True
        if row['phase'] == 'RELEASED':
            require(now >= deadline and row['reservations'] == 0, 'idle_release_observation')
            saw_released = True
    released = idle['releasedObservedNanos']
    require(saw_ready and saw_released and integer(released, deadline) and released <= deadline + 3_000_000_000
            and rows[-1]['observedNanos'] == released and rows[-1]['phase'] == 'RELEASED', 'idle_release_bracket')
    require(idle['terminalCleanupObservedBeforeQuiet'] is True, 'idle_cleanup_before_quiet')
    quiet_start, quiet_end = idle['quietStartNanos'], idle['quietEndNanos']
    require(integer(quiet_start, released) and integer(quiet_end, quiet_start + item['quiet_duration_ns'])
            and idle['noBeginDuringQuiet'] is True, 'quiet_duration')
    before, after = idle['generationsBefore'], idle['generationsAfter']
    expected_generations = [0, 0]
    expected_generations[idle['expired']['slot']] = idle['expired']['generation']
    require(isinstance(before, list) and len(before) == 2 and all(integer(value) for value in before)
            and sum(before) == 1 and compare_responses.identical(before, expected_generations)
            and compare_responses.identical(before, after), 'quiet_generation_advance')
    samples = idle['quietSamples']
    require(isinstance(samples, list) and len(samples) >= 2, 'quiet_samples')
    previous = quiet_start
    for row in samples:
        require(integer(row['observedNanos'], previous) and row['observedNanos'] <= quiet_end
                and type(row['reservations']) is int and row['reservations'] == 0
                and row['online'] is True, 'quiet_refill_observed')
        previous = row['observedNanos']
    require(samples[0]['observedNanos'] == quiet_start and samples[-1]['observedNanos'] == quiet_end,
            'quiet_observation_bracket')
    require(integer(idle['redemandNanos'], quiet_end) and lifecycle['steps'][0]['admissionNanos'] >= idle['redemandNanos'],
            'redemand_order')
    return expired


def verify(root, item, value, result):
    """Tie bounded lifecycle facts to every exact owned group and original process identity."""
    lifecycle = value['lifecycle']
    require(lifecycle['kind'] == item['kind'] and type(lifecycle['initialReservations']) is int
            and lifecycle['initialReservations'] == 0 and value['ledgerOnline'] is True
            and type(value['remainingReservations']) is int and value['remainingReservations'] == 0,
            'lifecycle_scope')
    require(len(value['groups']) == item['expected_group_count'], 'group_count')
    groups = {group['group']: group for group in value['groups']}
    require(len(groups) == len(value['groups']), 'duplicate_group')
    observations(lifecycle['observations'])
    ordered = verify_steps(root, item, lifecycle, groups, value['poolNonce'])
    if item['id'] == 'idle-expiry-demand':
        ordered.insert(0, verify_idle(item, lifecycle, groups, value['poolNonce']))
    require(len(set(ordered)) == len(ordered) and set(ordered) == set(groups), 'complete_generation_inventory')
    counts = {0: 0, 1: 0}
    worker_nonces, child_ids = set(), set()
    for name in ordered:
        group = groups[name]
        require(group['generation'] == counts[group['slot']] + 1, 'generation_order')
        counts[group['slot']] = group['generation']
        worker_nonces.add(group['productionBootstrapMetadata']['workerNonce'])
        child_ids.add((group['pid'], group['startTicks']))
    require(len(worker_nonces) == len(groups) and len(child_ids) == len(groups), 'worker_reuse')
    require(len(result['identities']) == len(groups)
            and {(row['pid'], row['start_ticks']) for row in result['identities']} == child_ids, 'complete_child_inventory')
