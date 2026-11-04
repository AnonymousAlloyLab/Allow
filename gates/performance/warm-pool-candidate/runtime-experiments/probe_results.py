"""Independently check the finite registered Java probe report and retained bytes."""
from pathlib import Path
import uuid

import containment
import sequence_results
from harness_common import digest, read_private, same_process


def require(value, reason):
    """Unknown, missing and type-coerced success are blocking."""
    if not value:
        raise ValueError(reason)


def check_plan(gate, plan):
    """Require nonvacuous unique cases and exact concrete inputs before registration."""
    cases = plan['cases']
    require(isinstance(cases, list) and bool(cases), 'probe_nonempty_cases_required')
    require(len({row['id'] for row in cases}) == len(cases), 'probe_duplicate_case_id')
    for item in cases:
        require(item['required'] is True and item['physical_cleanup_required'] is True, 'probe_required_physical_cleanup')
        require(item['expected_cleanup'] in {'PASS', 'UNKNOWN'}, 'probe_expected_cleanup_enum')
        require(type(item['expected_capacity_retained']) is bool, 'probe_expected_capacity_boolean')
        require(item['expected_capacity_retained'] == (item['expected_cleanup'] == 'UNKNOWN'), 'probe_unknown_capacity_rule')
        path = Path(item['fixture'])
        require(not path.is_absolute() and '..' not in path.parts and path.parent == Path('fixtures/semantic'),
                'probe_fixture_path')
        require(digest(gate/path) == item['fixture_sha256'], 'probe_fixture_identity')
        if item['id'] == 'shutdown-starting':
            require(item['expected_phase_at_shutdown_entry'] == 'STARTING'
                    and item['expected_attached_at_shutdown_entry'] is True
                    and item['expected_private_handoff'] is False and item['expected_terminal_phase'] == 'RELEASED'
                    and type(item['expected_group_count']) is int and item['expected_group_count'] == 1,
                    'probe_starting_shutdown_predicates')
        if item['id'] in sequence_results.CASES:
            sequence_results.check_plan(gate, item)
    return cases


def evidence_files(root, rows):
    """Bind private files without permitting traversal or report-relative aliases."""
    require(isinstance(rows, list), 'probe_evidence_list_required')
    seen = set()
    for row in rows:
        path = Path(row['path'])
        require(not path.is_absolute() and '..' not in path.parts and str(path) not in seen, 'probe_evidence_path')
        seen.add(str(path))
        actual = root/'.gate/evidence'/path
        require(actual.resolve().is_relative_to(root/'.gate/evidence'), 'probe_evidence_escape')
        require(actual.is_file() and not actual.is_symlink() and digest(actual) == row['sha256'], 'probe_evidence_hash')


def group_receipt(group, pool_nonce, config):
    """Parse captured kernel receipts independently of the probe's success booleans."""
    require(type(group['slot']) is int and group['slot'] in (0, 1), 'probe_group_slot')
    require(type(group['generation']) is int and group['generation'] > 0, 'probe_group_generation')
    expected = f"pool-{pool_nonce}/slot-{group['slot']}-g{group['generation']}"
    require(group['group'] == expected and group['device'] == config['rootDevice']
            and type(group['inode']) is int and group['inode'] > 0, 'probe_group_identity')
    terminal = group['terminalCounters']
    required = {'cgroup.events', 'memory.peak', 'memory.events', 'pids.peak', 'pids.events', 'cpu.stat'}
    require(set(terminal) == required and all(isinstance(value, str) for value in terminal.values()),
            'probe_terminal_counter_schema')
    require(containment.counters(terminal['cgroup.events']).get('populated') == 0, 'probe_group_terminal_empty')
    require(not containment.exhausted({'metrics': terminal}), 'probe_group_exhaustion')
    require(0 <= int(terminal['memory.peak']) <= 1073741824 and 0 <= int(terminal['pids.peak']) <= 32,
            'probe_worker_peak_limit')
    require('usage_usec' in containment.counters(terminal['cpu.stat']), 'probe_worker_cpu_counter')
    if 'productionBootstrapMetadata' in group:
        value = group['productionBootstrapMetadata']
        require(value['cgroupRoot'] == config['cgroupRoot'] and value['cgroupRelative'] == expected
                and value['cgroupDevice'] == group['device'] and value['cgroupInode'] == group['inode'],
                'probe_bootstrap_group_binding')


def ownership_receipt(root, item, result):
    """Require each concrete case's retained operational receipts without counting old directories as live."""
    name = item['id']+'-ownership.json'
    require(any(row['path'] == name for row in result['evidence']), 'probe_ownership_evidence_missing')
    value = read_private(root/'.gate/evidence'/name)
    nonce = value['poolNonce']
    require(str(uuid.UUID(nonce)) == nonce, 'probe_pool_nonce')
    require(value['contextBoundary'] == 'TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL', 'probe_context_trust_boundary')
    require(isinstance(value['groups'], list) and bool(value['groups']), 'probe_group_receipts_required')
    keys = [group['group'] for group in value['groups']]
    require(len(set(keys)) == len(keys), 'probe_group_receipt_duplicate')
    config = read_private(root/'.runtime/warm-pool/config.json')
    for group in value['groups']:
        group_receipt(group, nonce, config)
        if 'pid' in group:
            require({'pid': group['pid'], 'start_ticks': group['startTicks']} in result['identities'],
                    'probe_group_process_identity_unbound')
    require(type(value['remainingReservations']) is int and 0 <= value['remainingReservations'] <= 2,
            'probe_remaining_reservations_bound')
    require((value['remainingReservations'] > 0) is item['expected_capacity_retained'], 'probe_retained_ledger_count')
    if item['id'] == 'shutdown-starting':
        starting_shutdown_receipt(value, result)
    if item['id'] in sequence_results.CASES:
        sequence_results.verify(root, item, value, result)


def starting_shutdown_receipt(value, result):
    """Bind actual attached STARTING at close entry to its released, reaped generation."""
    require(value['shutdownBarrier'] == 'GATE_MONITOR_BARRIER_BEFORE_LEDGER_READY_PUBLICATION'
            and value['phaseAtCloseEntry'] == 'STARTING' and value['rawReadyEmission'] == 'NOT_ASSERTED',
            'probe_starting_shutdown_boundary')
    for name in ('attachedBeforeClose', 'noPrivateHandoff', 'poolClosedObservedWhileStarting',
                 'standbyMonitorHeldAtObservation', 'closeThreadJoined'):
        require(value[name] is True, 'probe_starting_shutdown_witness_'+name)
    require(value['closeThreadFailed'] is False and type(value['remainingReservations']) is int
            and value['remainingReservations'] == 0,
            'probe_starting_shutdown_not_clean')
    identity = {'pid': value['startingChildPid'], 'start_ticks': value['startingChildStartTicks']}
    require(type(identity['pid']) is int and identity['pid'] > 0 and isinstance(identity['start_ticks'], str)
            and identity['start_ticks'].isdigit() and result['identities'] == [identity],
            'probe_starting_shutdown_child_identity')
    require(len(value['groups']) == 1, 'probe_starting_shutdown_one_group')
    group = value['groups'][0]
    require(group.get('pid') == identity['pid'] and group.get('startTicks') == identity['start_ticks']
            and type(group.get('pid')) is int and group['directChildReaped'] is True
            and type(group['exitCode']) is int and group['finalPhase'] == 'RELEASED',
            'probe_starting_shutdown_release_receipt')


def case_result(root, item, result):
    """Require both the registered logical disposition and actual process absence."""
    require(result['id'] == item['id'] and result['status'] == 'PASS', 'probe_case_not_pass')
    require(result['classification'] == item['kind'], 'probe_case_wrong_classification')
    cleanup = result['cleanup']
    require(cleanup['status'] == item['expected_cleanup'], 'probe_cleanup_classification')
    require(cleanup['capacityRetained'] is item['expected_capacity_retained'], 'probe_capacity_release_mismatch')
    require(cleanup['directChildReaped'] is True, 'probe_direct_child_unreaped')
    if cleanup['status'] == 'PASS':
        require(cleanup['populatedZero'] is True, 'probe_positive_empty_required')
    identities = result['identities']
    require(isinstance(identities, list), 'probe_owned_identities_required')
    if item['id'] in {'normal-cold', 'normal-ready-hit', 'revalidate-fresh', 'shutdown-starting'} | sequence_results.CASES:
        require(bool(identities), 'probe_actual_worker_identity_required')
    for identity in identities:
        require(set(identity) == {'pid', 'start_ticks'} and type(identity['pid']) is int and identity['pid'] > 0,
                'probe_identity_schema')
        require(isinstance(identity['start_ticks'], str) and identity['start_ticks'].isdigit(), 'probe_start_identity')
        require(not same_process(identity), 'probe_owned_incarnation_still_alive')
    evidence_files(root, result['evidence'])
    ownership_receipt(root, item, result)
    return {'id': item['id'], 'status': 'PASS', 'classification': result['classification'], 'cleanup': cleanup}


def verify(root, manifest):
    """Check exact case count/order, immutable input/build and every retained result."""
    plan = read_private(root/'.gate/probe-cases.json')
    check_plan(root/'.gate', plan)
    done = read_private(root/'.gate/evidence/probe-complete.json')
    require(done['status'] == 'COMPLETE' and done['exit_code'] == 0 and done['probe_reaped'] is True,
            'probe_transport_incomplete')
    path = root/'.gate/evidence/java-probe.json'
    require(digest(path) == done['java_report_sha256'], 'probe_report_after_completion_mutation')
    report = read_private(path)
    require(report['schema'] == 1 and type(report['schema']) is int and report['status'] == 'PASS', 'probe_report_status')
    require(report['buildIdentity'] == manifest['build_identity']['value'], 'probe_build_identity')
    require(report['caseManifestSha256'] == digest(root/'.gate/probe-cases.json'), 'probe_case_manifest_identity')
    require(len(report['cases']) == len(plan['cases']), 'probe_case_count')
    checked = [case_result(root, item, result) for item, result in zip(plan['cases'], report['cases'])]
    return {'status': 'PASS', 'cases': checked, 'java_report_sha256': digest(path),
            'scope': plan['scope'], 'probe_transport': done}
