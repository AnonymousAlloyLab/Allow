"""Independent checks and descriptive statistics for the frozen component diagnostic."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import uuid

import compare_responses
import containment
from harness_common import digest, read_private, same_process

CONTRACT = '626a50b7afa537c906b38219c8646ca1043d59dbf38187820ad8b56a9f1253f2'
CONTEXT = 'TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL'
PROFILES = {'FRESH', 'POOL_SERIAL', 'POOL_READY', 'POOL_EMPTY'}


def require(condition, reason):
    """Unknown or inconsistent evidence blocks performance interpretation."""
    if not condition:
        raise ValueError('latency_' + reason)


def number(value, minimum=0):
    """Reject booleans and floating-point substitutes for integer clocks/counts."""
    return type(value) is int and value >= minimum


def canonical_uuid(value):
    """Validate an exact canonical operation or generation nonce."""
    require(isinstance(value, str) and str(uuid.UUID(value)) == value, 'uuid')


def statistics(values):
    """Compute exact nearest-rank descriptive percentiles without rounding selection inputs."""
    require(isinstance(values, list) and bool(values) and all(number(v) for v in values), 'samples')
    ordered = sorted(values)
    result = {'count': len(values), 'min_ns': ordered[0], 'max_ns': ordered[-1]}
    for percentile in (50, 95, 99):
        result[f'p{percentile}_ns'] = ordered[(percentile * len(values) + 99) // 100 - 1]
    result['mean_ns'] = sum(values) / len(values)
    result['milliseconds'] = {key[:-3]: value / 1_000_000 for key, value in result.items() if key.endswith('_ns')}
    return result


def response(row):
    """Parse the complete retained JSON bytes, without trusting producer summary fields."""
    encoded = row['responseBase64']
    require(isinstance(encoded, str) and len(encoded) <= 1_398_104, 'response_encoding_bound')
    raw = base64.b64decode(encoded, validate=True)
    require(number(row['responseBytes'], 1) and len(raw) == row['responseBytes'] <= 1048576,
            'response_byte_count')
    value = compare_responses.decode(raw + b'\n')
    canonical_uuid(row['requestNonce'])
    require(value['requestId'] == row['requestNonce'], 'response_nonce')
    return value


def check_response(value, fixture, expected, oracle=None):
    """Validate every complete output and compare its full contents to the frozen fresh oracle."""
    frame = copy.deepcopy(fixture)
    frame['requestId'] = value['requestId']
    compare_responses.check_response(value, frame)
    require(value['status'] == 'VALIDATED' and value['data']['mode'] == 'BLOCK_SUPPORTED', 'response_class')
    data = value['data']
    require(len(data['module']['nodes']) == expected['nodes'] == 500
            and data['source'] == expected['source'] and data['sourceHash'] == expected['source_sha256'],
            'response_expected_content')
    if oracle is not None:
        original = copy.deepcopy(fixture)
        original['requestId'] = oracle['requestId']
        compare_responses.check_response(oracle, original)
        normalized = copy.deepcopy(oracle)
        normalized['requestId'] = value['requestId']
        compare_responses.compare(normalized, value, frame)


def row_timing(row, previous, profile):
    """Require full operation boundaries and explicitly segregate preparation/conditioning."""
    start, end = row['startNs'], row['endNs']
    require(number(start, 1) and number(end, start + 1) and type(row['durationNs']) is int
            and row['durationNs'] == end - start, 'duration')
    milestones = ['capacityAcquiredNs', 'callStartNs', 'callEndNs', 'serializedNs']
    if profile != 'FRESH':
        milestones.append('publicationEndNs')
    else:
        require(row['publicationEndNs'] is None, 'fabricated_fresh_publication')
    milestones.append('capacityReleasedNs')
    cursor = start
    for field in milestones:
        require(number(row[field], cursor) and row[field] <= end, 'milestone_' + field)
        cursor = row[field]
    if previous is None:
        require(row['previousEndToAdmissionGapNs'] is None, 'first_gap')
    else:
        require(number(start, previous['endNs']) and number(row['previousEndToAdmissionGapNs'])
                and row['previousEndToAdmissionGapNs'] == start - previous['endNs'], 'admission_gap')
    cycle = row['cycleStartNs']
    require(number(cycle, 1) and cycle <= start and number(row['cycleDurationNs'], end - cycle), 'cycle')
    condition = ['conditionStartNs', 'conditionEndNs', 'conditionDurationNs']
    if profile == 'POOL_READY':
        left, right = row['conditionStartNs'], row['conditionEndNs']
        require(number(left, cycle) and number(right, left) and right <= start
                and type(row['conditionDurationNs']) is int and row['conditionDurationNs'] == right - left,
                'conditioning')
    else:
        require(all(row[key] is None for key in condition), 'unregistered_ready_wait')
    cold_fields = ['initializationStartNs', 'initializationEndNs', 'teardownStartNs', 'teardownEndNs']
    if profile == 'POOL_EMPTY':
        left, right, close, done = (row[key] for key in cold_fields)
        require(number(left, cycle) and number(right, left) and right <= start and number(close, end)
                and number(done, close) and row['cycleDurationNs'] == done - cycle, 'empty_cycle')
    else:
        require(all(row[key] is None for key in cold_fields), 'unexpected_per_request_teardown')
        require(row['cycleDurationNs'] == end - cycle, 'cycle_duration')
    if 'cycleEndNs' in row:
        require(type(row['cycleEndNs']) is int and row['cycleEndNs'] == cycle + row['cycleDurationNs'], 'cycle_end')


def process_identity(pid, ticks):
    """Require a positive exact original child identity and independent current absence."""
    require(number(pid, 1) and isinstance(ticks, str) and ticks.isdigit(), 'process_identity')
    require(not same_process({'pid': pid, 'start_ticks': ticks}), 'process_remains')
    return pid, ticks


def generation_key(value):
    """Bind pool incarnation and monotone slot generation without conflating different pools."""
    canonical_uuid(value['poolNonce'])
    canonical_uuid(value['workerNonce'])
    require(type(value['slot']) is int and value['slot'] in (0, 1) and number(value['generation'], 1), 'slot_generation')
    name = f"pool-{value['poolNonce']}/slot-{value['slot']}-g{value['generation']}"
    require(value['group'] == name and number(value['device'], 1) and number(value['inode'], 1), 'generation_group')
    return name


def terminal_groups(rows, config):
    """Independently parse every production terminal receipt and require actual process absence."""
    require(isinstance(rows, list), 'generation_list')
    result, children, nonces = {}, set(), set()
    for row in rows:
        key = generation_key(row)
        require(key not in result and row['device'] == config['rootDevice'], 'duplicate_or_wrong_group')
        require(row['phase'] == 'RELEASED' and row['attempted'] is True
                and row['directChildReaped'] is True and row['pidStartAbsent'] is True
                and type(row['exitCode']) is int, 'generation_cleanup')
        child = process_identity(row['pid'], row['startTicks'])
        require(child not in children and row['workerNonce'] not in nonces, 'generation_reuse')
        children.add(child)
        nonces.add(row['workerNonce'])
        counters = row['terminalCounters']
        required = {'cgroup.events', 'memory.peak', 'memory.events', 'pids.peak', 'pids.events', 'cpu.stat'}
        require(set(counters) == required and all(isinstance(v, str) for v in counters.values()), 'terminal_counter_schema')
        require(containment.counters(counters['cgroup.events']).get('populated') == 0, 'group_not_empty')
        require(not containment.exhausted({'metrics': counters}) and 0 <= int(counters['memory.peak']) <= 1073741824
                and 0 <= int(counters['pids.peak']) <= 32, 'worker_resource_limit')
        require('usage_usec' in containment.counters(counters['cpu.stat']), 'worker_cpu_counter')
        result[key] = row
    return result


def row_ownership(row, profile, groups):
    """Check the actual policy-specific receipt; fresh workers have no invented child cgroup."""
    if profile == 'FRESH':
        require(row['admission'] is None and row['consumed'] is None, 'fresh_pool_observation')
        receipt = row['freshRecovery']
        require(receipt['noWorkerStarted'] is False, 'fresh_not_started')
        process_identity(receipt['workerPid'], receipt['workerStartTicks'])
        return None, 'FRESH'
    require(row['freshRecovery'] is None, 'pool_fresh_receipt')
    consumed, admission = row['consumed'], row['admission']
    key = generation_key(consumed)
    require(key in groups, 'consumed_receipt_missing')
    actual = groups[key]
    for field in ('poolNonce', 'slot', 'generation', 'workerNonce', 'group', 'device', 'inode', 'pid', 'startTicks'):
        require(type(consumed[field]) is type(actual[field]) and consumed[field] == actual[field], 'consumed_' + field)
    require(consumed['requestNonce'] == row['requestNonce'] and consumed['phaseBeforePublish'] == 'CLEAN', 'consumed_identity')
    require(number(row['admissionObservedNs'], row['startNs'])
            and row['admissionObservedNs'] <= row['capacityAcquiredNs'], 'admission_observation')
    require(row['publicationEndNs'] - row['startNs'] < 10_000_000_000, 'success_deadline')
    phase = admission['phase']
    require(phase in {'EMPTY', 'STARTING', 'READY'} and admission['poolNonce'] == consumed['poolNonce'], 'admission_phase')
    if phase != 'EMPTY':
        require(generation_key(admission) == key, 'admission_selected_generation')
        allowed = {'READY'} if phase == 'READY' else {'RESERVED', 'STARTING'}
        require(admission['actualPhase'] in allowed, 'admission_actual_phase')
    if profile == 'POOL_READY':
        require(phase == 'READY', 'conditioned_not_ready')
    if profile == 'POOL_EMPTY':
        require(phase == 'EMPTY', 'nonempty_cold_pool')
    return key, phase


def inventory(rows, profile, groups, selected):
    """Account for every one-use consumption and final automatic spare in each incarnation."""
    if profile == 'FRESH':
        require(not groups and not selected, 'fresh_generation_inventory')
        identities = [(r['freshRecovery']['workerPid'], r['freshRecovery']['workerStartTicks']) for r in rows]
        require(len(set(identities)) == len(rows), 'fresh_child_reuse')
        return
    require(len(selected) == len(rows) and len(set(selected)) == len(selected), 'consumption_reuse')
    pools = {group['poolNonce'] for group in groups.values()}
    expected_pools = len(rows) if profile == 'POOL_EMPTY' else 1
    require(len(pools) == expected_pools and len(groups) == len(rows) + expected_pools, 'generation_count')
    for pool in pools:
        owned = [g for g in groups.values() if g['poolNonce'] == pool]
        used = [key for key in selected if groups[key]['poolNonce'] == pool]
        require(len(owned) == len(used) + 1, 'spare_inventory')
        for slot in (0, 1):
            generations = sorted(g['generation'] for g in owned if g['slot'] == slot)
            require(generations == list(range(1, len(generations) + 1)), 'generation_gap')


def cpu_metrics(report, rows, warmups):
    """Expose measured CPU and asynchronous teardown tail separately, preserving raw counters."""
    cpu, timing = report['cpu'], report['timing']
    names = ('beforeMeasured', 'afterMeasured', 'afterTeardown')
    values, clocks = [], []
    for name in names:
        row = cpu[name]
        require(number(row['observedNs'], 1) and isinstance(row['raw'], str), 'cpu_sample')
        parsed = containment.counters(row['raw'])
        require(all(number(parsed.get(field)) for field in ('usage_usec', 'user_usec', 'system_usec')), 'cpu_counters')
        values.append(parsed)
        clocks.append(row['observedNs'])
    require(clocks == sorted(clocks) and clocks[0] <= rows[warmups]['cycleStartNs']
            and clocks[1] >= rows[-1]['endNs'] and clocks[2] >= timing['teardownEndNs'], 'cpu_time_brackets')
    for key in ('usage_usec', 'user_usec', 'system_usec'):
        require(values[0][key] <= values[1][key] <= values[2][key], 'cpu_counter_reversal')
    require(number(timing['measurementStartNs'], clocks[0])
            and timing['measurementStartNs'] <= rows[warmups]['cycleStartNs']
            and number(timing['measurementEndNs'], rows[-1]['endNs'])
            and timing['measurementEndNs'] <= clocks[1] <= timing['teardownStartNs']
            and number(timing['teardownStartNs'], timing['measurementEndNs'])
            and number(timing['teardownEndNs'], timing['teardownStartNs']), 'block_time_brackets')
    return {'measured_usage_usec': values[1]['usage_usec'] - values[0]['usage_usec'],
            'teardown_tail_usage_usec': values[2]['usage_usec'] - values[1]['usage_usec'],
            'teardown_ns': timing['teardownEndNs'] - timing['teardownStartNs']}


def metrics(report, phases, resources, plan):
    """Report descriptive per-variant populations; never convert these into acceptance thresholds."""
    rows = report['rows'][plan['warmups']:]
    start = rows[0]['cycleStartNs'] if plan['profile'] in {'POOL_READY', 'POOL_EMPTY'} else rows[0]['startNs']
    end = rows[-1]['cycleStartNs'] + rows[-1]['cycleDurationNs']
    elapsed = end - start
    require(number(elapsed, 1), 'measurement_interval')
    gaps = [row['previousEndToAdmissionGapNs'] for row in rows if row['previousEndToAdmissionGapNs'] is not None]
    result = {'latency': statistics([row['durationNs'] for row in rows]),
              'all_attempt_terminal_duration': statistics([row['cycleDurationNs'] for row in rows]),
              'attempted': len(rows), 'succeeded': len(rows), 'errors': 0,
              'warmups_retained': plan['warmups'], 'measurement_interval_ns': elapsed,
              'serial_completion_rate_per_second': len(rows) * 1e9 / elapsed,
              'admission_counts': {phase: phases[plan['warmups']:].count(phase) for phase in sorted(set(phases))},
              'admission_gap_ns': gaps, 'cpu': resources,
              'interpretation': 'DESCRIPTIVE_COMPONENT_ONLY_NOT_HTTP_OR_CAPACITY_ACCEPTANCE'}
    if plan['profile'] == 'POOL_READY':
        result['excluded_ready_wait'] = statistics([row['conditionDurationNs'] for row in rows])
        result['ready_wait_ns'] = [row['conditionDurationNs'] for row in rows]
    if plan['profile'] == 'POOL_EMPTY':
        result['initialization'] = statistics([r['initializationEndNs'] - r['initializationStartNs'] for r in rows])
        result['shutdown'] = statistics([r['teardownEndNs'] - r['teardownStartNs'] for r in rows])
    return result


def verify_variant(root, evidence, manifest, plan, fixture, oracle=None):
    """Validate exact inputs, complete attempt accounting, output equality and all owned receipts."""
    root, evidence = Path(root), Path(evidence)
    require(plan['schema'] == 1 and type(plan['schema']) is int and plan['profile'] in PROFILES
            and plan['mode'] in {'PREFLIGHT', 'MEASURED'} and plan['contractSha256'] == CONTRACT, 'plan')
    expected_counts = (0, 1) if plan['mode'] == 'PREFLIGHT' else ((0, 20) if plan['profile'] == 'POOL_EMPTY' else (20, 100))
    require(type(plan['warmups']) is int and type(plan['measured']) is int
            and (plan['warmups'], plan['measured']) == expected_counts, 'plan_counts')
    config = read_private(root/'.runtime/warm-pool/config.json')
    require(plan['cgroupRoot'] == config['cgroupRoot'] and plan['cpuStat'] == config['cgroupRoot'] + '/cpu.stat'
            and plan['fixture'] == str(root/'.gate/latency-fixture.json')
            and digest(Path(plan['fixture'])) == plan['fixtureSha256'], 'plan_runtime_binding')
    require(compare_responses.identical(fixture, read_private(Path(plan['fixture']))) and 'requestId' not in fixture,
            'fixture_template')
    expected = read_private(root/'.gate/latency-expected.json')
    require(expected['headless_fixture_sha256'] == digest(root/'gates/document/headless-preview-fixture.json')
            and expected['printer_class_sha256'] == digest(root/'backend/target/classes/dev/allow/document/ModulePrinter.class')
            and hashlib.sha256(expected['source'].encode()).hexdigest() == expected['source_sha256'], 'source_oracle_binding')
    report = read_private(evidence/'latency-java.json')
    require(report['schema'] == 1 and type(report['schema']) is int and report['status'] == 'COMPLETE'
            and report['failure'] is None and report['notExecuted'] == [], 'incomplete_or_failed_variant')
    for field in ('variantId', 'profile', 'mode', 'contractSha256', 'fixtureSha256'):
        require(report[field] == plan[field], 'report_' + field)
    require(report['buildSha256'] == manifest['build_identity']['value'] and report['contextBoundary'] == CONTEXT,
            'build_or_context')
    require(type(report['expectedWarmups']) is int and type(report['expectedMeasured']) is int
            and (report['expectedWarmups'], report['expectedMeasured']) == expected_counts, 'report_counts')
    rows = report['rows']
    require(isinstance(rows, list) and len(rows) == sum(expected_counts), 'row_count')
    groups = terminal_groups(report['generations'], config)
    selected, phases, nonces = [], [], set()
    previous = None
    for index, row in enumerate(rows):
        require(type(row['index']) is int and row['index'] == index and row['outcome'] == 'SUCCESS'
                and row['failure'] is None and row['phase'] == ('WARMUP' if index < plan['warmups'] else 'MEASURED'), 'row_accounting')
        row_timing(row, previous, plan['profile'])
        value = response(row)
        require(row['requestNonce'] not in nonces, 'operation_nonce_reuse')
        nonces.add(row['requestNonce'])
        check_response(value, fixture, expected, oracle)
        key, phase = row_ownership(row, plan['profile'], groups)
        if key is not None:
            selected.append(key)
        phases.append(phase)
        previous = row
    inventory(rows, plan['profile'], groups, selected)
    cleanup = report['cleanup']
    require(cleanup['poolClosed'] is True and cleanup['ledgerClosed'] is True
            and type(cleanup['remainingReservations']) is int and cleanup['remainingReservations'] == 0, 'logical_cleanup')
    resources = cpu_metrics(report, rows, plan['warmups'])
    result = {'status': 'PASS', 'classification': 'CHECKED_FINITE_COMPONENT_DIAGNOSTIC_NOT_PROMOTION',
              'profile': plan['profile'], 'mode': plan['mode'], 'variantId': plan['variantId'],
              'java_report_sha256': digest(evidence/'latency-java.json'), 'attempts_checked': len(rows),
              'generation_count': len(groups), 'context_boundary': CONTEXT}
    if plan['mode'] == 'MEASURED':
        require(oracle is not None, 'measured_oracle_required')
        result['metrics'] = metrics(report, phases, resources, plan)
    return result


def extract_oracle(evidence):
    """Extract the single fresh compatibility response only after independent preflight success."""
    report = read_private(Path(evidence)/'latency-java.json')
    require(report['mode'] == 'PREFLIGHT' and report['profile'] == 'FRESH' and len(report['rows']) == 1,
            'oracle_preflight')
    return response(report['rows'][0])


def compare_preflight(fresh_response, pool_response, fixture):
    """Require full output equality after checking each original nonce independently."""
    for value in (fresh_response, pool_response):
        canonical_uuid(value['requestId'])
        frame = copy.deepcopy(fixture)
        frame['requestId'] = value['requestId']
        compare_responses.check_response(value, frame)
    left = copy.deepcopy(fresh_response)
    left['requestId'] = pool_response['requestId']
    frame = copy.deepcopy(fixture)
    frame['requestId'] = pool_response['requestId']
    return compare_responses.compare(left, pool_response, frame)


def paired_metrics(fresh, pool):
    """Present descriptive differences within a registered pair without a selection verdict."""
    require(fresh['profile'] == 'FRESH' and pool['profile'] == 'POOL_SERIAL'
            and fresh['status'] == pool['status'] == 'PASS', 'pair_profiles')
    result = {}
    for field in ('p50_ns', 'p95_ns', 'p99_ns', 'max_ns'):
        left, right = fresh['metrics']['latency'][field], pool['metrics']['latency'][field]
        require(number(left, 1) and number(right, 1), 'pair_latency')
        result[field] = {'fresh': left, 'pool': right, 'pool_minus_fresh': right - left,
                         'pool_over_fresh': right / left, 'reduction_percent': (left - right) * 100 / left}
    return result
