#!/usr/bin/env python3
"""Freeze, run and independently classify finite HTTP pairs without changing prepared inputs."""
import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import containment
import controller
import experiment_binding
import installation
import scope_launch
from harness_common import (HERE, clean_environment, digest, packed, process_identity, read_private,
                            root_hash, write_private)

ORDER = ((1, 'F0'), (1, 'F1'), (2, 'F1'), (2, 'F0'), (3, 'F0'), (3, 'F1'))
REQUIRED = ('finite_semantics', 'comparator_negative_cases', 'p1_regressions', 'java_safety')
PROGRAMS = ('pair_runner.py', 'controller.py', 'containment.py', 'installation.py',
            'harness_common.py', 'http_driver.py', 'stack_owner.py', 'scope_launch.py',
            'attached_launch.py', 'http_setup.py', 'experiment_binding.py', 'test_experiment_binding.py',
            'test_pair_runner.py', 'workload_correspondence.py', 'test_workload_correspondence.py',
            'compare_responses.py', 'test_compare_responses.py')


def require(condition, reason):
    """Reject any absent, malformed or unresolved required condition."""
    if not condition:
        raise ValueError(reason)


def unique_object(rows):
    """Reject duplicate JSON keys instead of silently changing a recorded response."""
    value = {}
    for key, item in rows:
        require(key not in value, 'duplicate_json_key')
        value[key] = item
    return value


def reject_constant(value):
    """JSON evidence never admits NaN or infinities."""
    raise ValueError('nonfinite_json_constant')


def decode(raw):
    """Decode strict finite UTF-8 JSON with duplicate-key rejection."""
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)


def load(path):
    """Read an evidence document without changing it."""
    return decode(Path(path).read_bytes())


def equal(left, right):
    """Preserve JSON types, including booleans versus integers, in equality checks."""
    return packed(left) == packed(right)


def binding(path):
    """Bind an absolute evidence/program path to exact bytes."""
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': digest(path)}


def pointer(value, path):
    """Resolve a frozen JSON pointer without interpreting arbitrary expressions."""
    require(path == '' or path.startswith('/'), 'invalid_success_pointer')
    for field in path.split('/')[1:] if path else []:
        key = field.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def prerequisites(path):
    """Evaluate exact predeclared typed predicates on separately hashed prerequisite reports."""
    receipt = load(path)
    require(set(receipt) == set(REQUIRED), 'exact_prerequisite_set_required')
    rows = [binding(path)]
    for name in REQUIRED:
        item = receipt[name]
        require(digest(Path(item['path'])) == item['sha256'], 'prerequisite_hash_' + name)
        report = load(item['path'])
        expected = item.get('success_value', 'PASS')
        require(expected in ('PASS', 'VERIFIED'), 'prerequisite_success_value')
        require(equal(pointer(report, item.get('success_pointer', '/status')), expected), 'prerequisite_failed_' + name)
        for assertion in item.get('assertions', []):
            require(equal(pointer(report, assertion['pointer']), assertion['equals']), 'prerequisite_assertion_' + name)
        rows.append(binding(item['path']))
    return rows


def frozen_files(rows):
    """Require unique, unchanged registered files at every execution boundary."""
    require(len({row['path'] for row in rows}) == len(rows), 'duplicate_registered_path')
    for row in rows:
        require(binding(row['path']) == row, 'registered_input_mutation')


def history_path(history, pair, variant):
    """Return the one immutable result path for an ordered trial."""
    return history/f'pair-{pair}-{variant}.json'


def experiment_at(path):
    """Require one complete immutable six-trial registration before admitting any trial."""
    value = load(path)
    experiment_binding.verify_experiment(value)
    require(equal(value['order'], [list(row) for row in ORDER]), 'experiment_order_mismatch')
    return value


def history_anchor(history, experiment_path, value, create=False):
    """Bind an entire history directory permanently to one exact experiment root."""
    expected = {'experiment': binding(experiment_path), 'input_root_sha256': value['input_root_sha256']}
    path = history/'experiment.json'
    if create and not path.exists():
        write_private(path, expected)
    require(equal(load(path), expected), 'history_experiment_mismatch')


def history_entry(history, pair, variant, value, previous):
    """Recompute a successful historical verdict from its registered raw evidence."""
    path = history_path(history, pair, variant)
    row = load(path)
    require(type(row['pair']) is int and row['pair'] == pair and row['variant'] == variant
            and row['experiment_root_sha256'] == value['input_root_sha256'], 'history_trial_identity')
    require(equal(row['previous_trial'], previous), 'history_chain_mismatch')
    trial = next(item for item in value['trials'] if item['pair'] == pair and item['variant'] == variant)
    run = Path(trial['manifest']['path']).parent
    require(row['input_root_sha256'] == trial['input_root_sha256']
            and equal(row['verdict'], binding(run/'pair-verification.json')), 'history_verdict_binding')
    verdict = load(row['verdict']['path'])
    require(verdict.get('valid_measurement') is True, 'earlier_trial_failed')
    require(equal(verify_trial(run/'pair-registration.json'), verdict), 'history_verdict_replay_mismatch')
    return verdict


def pair_summary(history, pair, value, baseline, candidate):
    """Compute the exact immutable two-trial comparison from independently checked verdicts."""
    passed = baseline['valid_measurement'] is True and candidate['valid_measurement'] is True \
        and candidate.get('p95_ms', math.inf) < 300 and candidate.get('p95_ms', math.inf) < baseline.get('p95_ms', -math.inf)
    return {'status': 'PASS' if passed else 'BLOCKED', 'pair': pair,
            'experiment_root_sha256': value['input_root_sha256'],
            'F0': binding(history_path(history, pair, 'F0')), 'F1': binding(history_path(history, pair, 'F1')),
            'strictly_lower_F1_p95': candidate.get('p95_ms', math.inf) < baseline.get('p95_ms', -math.inf)}


def check_order(history, pair, variant, value):
    """Admit only the preregistered alternating order, stopping after any failed trial/pair."""
    index = ORDER.index((pair, variant))
    require(not (history/'selection.json').exists(), 'experiment_already_terminal')
    verdicts, previous = {}, None
    for previous_pair, previous_variant in ORDER[:index]:
        path = history_path(history, previous_pair, previous_variant)
        require(path.is_file(), 'earlier_trial_not_completed')
        verdicts[(previous_pair, previous_variant)] = history_entry(history, previous_pair, previous_variant, value, previous)
        previous = binding(path)
    require(not history_path(history, pair, variant).exists(), 'trial_already_recorded')
    for earlier in range(1, pair):
        expected = pair_summary(history, earlier, value, verdicts[(earlier, 'F0')], verdicts[(earlier, 'F1')])
        require(expected['status'] == 'PASS' and equal(load(history/f'pair-{earlier}.json'), expected), 'earlier_pair_not_passed')
    return previous


def runtime_document(registration, registration_path):
    """Derive the original controller's registration without weakening its recorded checks."""
    files = registration['files'] + [binding(registration_path)]
    driver = next(row for row in files if row['path'] == str(HERE/'pair_runner.py'))
    return {'status': 'FROZEN_RUNTIME_INPUTS', 'installation_root_sha256': registration['installation_root_sha256'],
            'prerequisites': {name: 'PASS' for name in REQUIRED}, 'files': files, 'driver': driver}


def freeze(arguments):
    """Freeze one trial's evidence rules and source/report identities without scheduling it."""
    run, manifest = controller.read_run(arguments.run)
    require(manifest['variant'] == arguments.variant, 'variant_manifest_mismatch')
    installation.verify(manifest, fresh=True)
    controller.require_preflight(arguments.preflight)
    history = arguments.history.resolve()
    require(history.is_relative_to(HERE/'runs'), 'gate_history_required')
    history.mkdir(mode=0o700, parents=True, exist_ok=True)
    require((arguments.pair, arguments.variant) in ORDER, 'registered_pair_required')
    require(not (history/'selection.json').exists(), 'experiment_already_terminal')
    require(not history_path(history, arguments.pair, arguments.variant).exists(), 'trial_already_recorded')
    experiment = experiment_at(arguments.experiment_binding)
    require(str(arguments.preflight.resolve()) == experiment['scope_preflight'], 'experiment_scope_preflight_mismatch')
    experiment_binding.verify_trial(experiment, run/'manifest.json', arguments.pair, arguments.variant)
    require(str(arguments.prerequisites.resolve()) == experiment['prerequisites'], 'experiment_prerequisites_mismatch')
    history_anchor(history, arguments.experiment_binding, experiment, create=True)
    rows = prerequisites(arguments.prerequisites)
    rows += [binding(HERE/name) for name in PROGRAMS]
    rows += [binding(run/'manifest.json'), binding(arguments.preflight/'manifest.json'), binding(arguments.preflight/'report.json')]
    rows += [binding(arguments.experiment_binding), binding(history/'experiment.json')]
    rows = list({row['path']: row for row in rows}.values())
    copied = {row['path']: row['sha256'] for row in manifest['files']}
    require(all(copied.get('.gate/' + name) == digest(HERE/name) for name in PROGRAMS), 'prepared_gate_program_mismatch')
    value = {'schema_version': '1.0', 'classification': 'FROZEN_NOT_RELEASED', 'pair': arguments.pair,
             'variant': arguments.variant, 'run': str(run), 'history': str(history),
             'installation_root_sha256': manifest['input_root_sha256'], 'files': rows,
             'experiment_binding': binding(arguments.experiment_binding), 'experiment_root_sha256': experiment['input_root_sha256'],
             'prerequisites': str(arguments.prerequisites.resolve()), 'preflight': str(arguments.preflight.resolve()),
             'order': [list(row) for row in ORDER], 'policy': policy()}
    value['registration_root_sha256'] = hashlib.sha256(packed(value)).hexdigest()
    target = run/'pair-registration.json'
    write_private(target, value)
    write_private(run/'pair-runtime-registration.json', runtime_document(value, target))
    return {'status': 'FROZEN_NOT_RELEASED', 'registration': str(target),
            'registration_root_sha256': value['registration_root_sha256']}


def policy():
    """Keep validity, baseline measurement and F1 selection predicates distinct and fixed."""
    return {'warmups': 100, 'measured': 1000, 'nodes': 500, 'errors': 0,
            'percentile': 'nearest_rank_sorted_ceil_nq_minus_one', 'memory_peak_max_bytes': 5368709120,
            'F0': 'MEASURED_BASELINE if every validity predicate passes; p95>=300 alone is not invalidity',
            'F1': 'Strict p95<300 and memory<=5GiB and every validity predicate; pair requires F1p95<F0p95',
            'failure': 'Stop experiment, keep F0, untouched later trials NOT_EXECUTED',
            'excluded': ['profile activation', 'target-host acceptance', 'universal semantic equivalence']}


def registration_at(path):
    """Validate the entire frozen rule set and all bound artifacts before consuming a result."""
    value = load(path)
    root = value['registration_root_sha256']
    require(hashlib.sha256(packed({key: item for key, item in value.items()
            if key != 'registration_root_sha256'})).hexdigest() == root, 'pair_registration_root')
    require(equal(value['policy'], policy()) and equal(value['order'], [list(row) for row in ORDER]), 'frozen_policy_mutation')
    frozen_files(value['files'])
    prerequisites(Path(value['prerequisites']))
    require(binding(value['experiment_binding']['path']) == value['experiment_binding'], 'experiment_binding_mutation')
    experiment = experiment_at(value['experiment_binding']['path'])
    require(experiment['input_root_sha256'] == value['experiment_root_sha256'], 'experiment_root_mismatch')
    require(value['preflight'] == experiment['scope_preflight'], 'experiment_scope_preflight_mismatch')
    history_anchor(Path(value['history']), value['experiment_binding']['path'], experiment)
    run, manifest = controller.read_run(Path(value['run']))
    experiment_binding.verify_trial(experiment, run/'manifest.json', value['pair'], value['variant'])
    require(manifest['input_root_sha256'] == value['installation_root_sha256'], 'pair_installation_root')
    require(equal(load(run/'pair-runtime-registration.json'), runtime_document(value, path)), 'runtime_registration_mutation')
    return value, run, manifest


def envelope(raw, expected):
    """Independently enforce the complete public protocol envelope on retained wire bytes."""
    value = decode(raw)
    require(isinstance(value, dict) and set(value) == {'protocol', 'requestId', 'status', 'data'}, 'response_envelope')
    require(type(value['protocol']) is int and value['protocol'] == 1, 'response_protocol')
    require(value['status'] == expected and type(value['requestId']) is str, 'response_status_id')
    require(str(uuid.UUID(value['requestId'])) == value['requestId'], 'response_uuid')
    return value['data']


def response_matches(raw, request, request_raw):
    """Check every decoded HTTP field and identity/hash binding without trusting driver PASS."""
    data = envelope(raw, 'VALIDATED')
    fields = {'requestHash', 'draftId', 'draftEpoch', 'baseRevision', 'supportMode', 'diagnostics',
              'proposedSource', 'proposedSourceHash', 'sourceHash'}
    require(isinstance(data, dict) and set(data) == fields, 'response_data_fields')
    require(data['supportMode'] == 'BLOCK_SUPPORTED' and equal(data['diagnostics'], []), 'response_support_diagnostics')
    require(all(equal(data[key], request[key]) for key in ('draftId', 'draftEpoch', 'baseRevision')), 'response_request_identity')
    require(data['requestHash'] == hashlib.sha256(request_raw).hexdigest(), 'response_request_hash')
    require(type(data['proposedSource']) is str, 'response_source_type')
    source_hash = hashlib.sha256(data['proposedSource'].encode()).hexdigest()
    require(data['sourceHash'] == data['proposedSourceHash'] == source_hash, 'response_source_hash')


def setup_inputs(root, evidence, manifest):
    """Bind the accepted synthetic document and SOURCE setup to the frozen 500-node fixture."""
    from http_setup import verify_setup
    route, module, metadata = verify_setup(root, evidence, manifest)
    require(metadata['status'] == 'PASS' and len(module['nodes']) == 500, 'original_setup_correspondence')
    return route, module


def verify_samples(root, run, manifest):
    """Replay all 1100 distinct frozen edits, raw response hashes and exact recorded counts."""
    evidence = run/'http-private'
    request_manifest = load(evidence/'requests-manifest.json')
    declared_root = request_manifest['request_root_sha256']
    require(hashlib.sha256(packed({key: value for key, value in request_manifest.items()
            if key != 'request_root_sha256'})).hexdigest() == declared_root, 'request_manifest_root')
    require(request_manifest['installation_root_sha256'] == manifest['input_root_sha256'], 'request_installation_root')
    require(request_manifest['fixture_sha256'] == digest(root/'gates/document/headless-preview-fixture.json'), 'request_fixture_hash')
    route, module = setup_inputs(root, evidence, manifest)
    require(request_manifest['route'] == route, 'request_route')
    rows = [decode(line) for line in (evidence/'samples.jsonl').read_bytes().splitlines()]
    require(len(rows) == len(request_manifest['files']) == 1100, 'complete_1100_rows_required')
    expected_names = {f'{index:04d}.json' for index in range(1100)}
    require({path.name for path in (evidence/'requests').iterdir()} == expected_names
            and {path.name for path in (evidence/'responses').iterdir()} == expected_names, 'surplus_or_missing_wire_files')
    candidate = {'mode': 'BLOCK_SUPPORTED', 'module': copy.deepcopy(module), 'presentationCopies': []}
    leaves = [node for node in candidate['module']['nodes'] if node['tag'] == 'signature_ref']
    signatures = [signature['id'] for signature in module['signatures']]
    require(len(signatures) == 2 and len(leaves) > 0, 'original_edit_shape')
    for index, (sample, record) in enumerate(zip(rows, request_manifest['files'])):
        node = leaves[index % len(leaves)]
        node['targetId'] = signatures[1] if node['targetId'] == signatures[0] else signatures[0]
        request = {'draftId': str(uuid.uuid5(uuid.NAMESPACE_URL, 'allow:fresh-tier1:http:edits')),
                   'draftEpoch': index, 'baseRevision': 1, 'candidate': candidate}
        check_sample(evidence, index, sample, record, request)
    report = load(run/'http-original-report.json')
    require(equal(report['samples'], rows) and report['request_root_sha256'] == declared_root, 'driver_rows_root_disagreement')
    require(report['input_root_sha256'] == manifest['input_root_sha256'] and report['variant'] == manifest['variant'], 'driver_root_variant')
    require(report['verifier_sha256'] == digest(HERE/'http_driver.py'), 'driver_implementation_hash')
    return summary(rows, report)


def check_sample(evidence, index, sample, record, request):
    """Require exact event order, frozen byte identity, finite timings and a complete valid reply."""
    phase = 'warmup' if index < 100 else 'measured'
    require(type(sample['event']) is int and sample['event'] == index and sample['phase'] == phase, 'sample_order')
    require(type(record['event']) is int and record['event'] == index and record['phase'] == phase, 'request_order')
    require(record['path'] == f'requests/{index:04d}.json', 'request_path')
    raw = (evidence/record['path']).read_bytes()
    expected = json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode()
    require(raw == expected and record['sha256'] == hashlib.sha256(raw).hexdigest(), 'original_distinct_edit_bytes')
    require(type(record['bytes']) is int and record['bytes'] == len(raw), 'request_byte_count')
    require(sample['status'] == 'PASS' and type(sample['http_status']) is int and sample['http_status'] == 200, 'request_error')
    require(sample['request_sha256'] == record['sha256'], 'sample_request_hash')
    elapsed = sample['elapsed_ms']
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed > 0, 'sample_duration')
    response = (evidence/'responses'/f'{index:04d}.json').read_bytes()
    require(sample['response_sha256'] == hashlib.sha256(response).hexdigest(), 'response_file_hash')
    require(type(sample['response_bytes']) is int and sample['response_bytes'] == len(response) <= 1048576, 'response_byte_count')
    response_matches(response, request, raw)


def summary(rows, original):
    """Recompute nearest-rank percentiles and identify latency-only baseline failures exactly."""
    values = sorted(row['elapsed_ms'] for row in rows[100:])
    result = {'warmups': 100, 'measured': 1000, 'failures': [], 'p50_ms': values[499],
              'p95_ms': values[949], 'p99_ms': values[989], 'maximum_ms': values[-1]}
    for key, value in result.items():
        require(equal(original[key], value), 'driver_summary_disagreement_' + key)
    expected = 'PASS' if result['p95_ms'] < 300 else 'BLOCKED'
    require(original['status'] == expected and original['required_warmups'] == 100
            and original['required_measured'] == 1000, 'driver_latency_classification')
    result['latency_gate'] = 'PASS' if result['p95_ms'] < 300 else 'FAIL'
    return result


def resource_peak(snapshot):
    """Require complete nonnegative kernel counters and strict finite resource admission."""
    metrics = snapshot['metrics']
    require(all(isinstance(metrics.get(name), str) for name in ('memory.events', 'pids.events', 'memory.peak')),
            'resource_metric_type')
    memory, pids = containment.counters(metrics['memory.events']), containment.counters(metrics['pids.events'])
    require({'oom', 'oom_kill', 'oom_group_kill'} <= set(memory) and 'max' in pids, 'resource_counter_missing')
    require(all(type(value) is int and value >= 0 for value in [*memory.values(), *pids.values()]), 'resource_counter_invalid')
    require(all(memory[name] == 0 for name in ('oom', 'oom_kill', 'oom_group_kill')) and pids['max'] == 0, 'resource_exhaustion')
    peak = int(metrics['memory.peak'])
    require(0 < peak <= 5368709120, 'whole_stack_memory_peak')
    return peak


def verify_snapshot(snapshot, manifest, invocation):
    """Check retained kernel counters, unit ownership, task affinity and resource failures."""
    require(equal(snapshot['limits'], containment.EXPECTED), 'snapshot_limits')
    unit = snapshot['unit']
    require(unit['Id'] == manifest['unit'] and unit['Description'] == 'allow-fresh:' + manifest['input_root_sha256'], 'snapshot_unit')
    require(unit['InvocationID'] == invocation['invocation_id'] and unit['KillMode'] == 'control-group'
            and unit['Delegate'] == 'no', 'snapshot_incarnation')
    require(unit['ControlGroup'] == invocation['control_group'] and invocation['control_group'].startswith('/user.slice/')
            and type(snapshot['observed_monotonic_ns']) is int, 'snapshot_owned_group')
    require(manifest['launch_lane'] == snapshot['launch_lane'] == 'owned_caller_scope_v1', 'snapshot_launch_lane')
    owner = invocation['main_identity']
    require(equal(snapshot['supervisor_identity'], owner)
            and any(equal({'pid': row['pid'], 'start_ticks': row['start_ticks']}, owner)
                    for row in snapshot['processes']), 'snapshot_owner_absent')
    for process in snapshot['processes']:
        group = process['cgroup']
        require(group == unit['ControlGroup'] or group.startswith(unit['ControlGroup'] + '/'), 'snapshot_escape')
        require(process['threads'] and all(equal(row['affinity'], [0, 1, 2, 3]) for row in process['threads']), 'snapshot_affinity')
    return resource_peak(snapshot)


def driver(arguments):
    """Wrap the original driver; preserve its raw verdict and capture final live-group counters."""
    run = arguments.output.resolve().parent
    registration, registered_run, manifest = registration_at(run/'pair-registration.json')
    require(run == registered_run and arguments.root.resolve() == Path(manifest['copied_root']), 'wrapper_run_root')
    root = arguments.root.resolve()
    original = run/'http-original-report.json'
    started = time.monotonic_ns()
    child = subprocess.run([str(root/'.tools/retrieval-venv/bin/python'), str(HERE/'http_driver.py'),
                            '--root', str(root), '--output', str(original)], cwd=root,
                           env=clean_environment(root), timeout=1150)
    completed = time.monotonic_ns()
    snapshot = scope_launch.observe(manifest)
    write_private(run/'driver-final-cgroup.json', snapshot)
    exit_record = {'exit_code': child.returncode, 'driver_sha256': digest(HERE/'http_driver.py'),
                   'installation_root_sha256': manifest['input_root_sha256'], 'started_monotonic_ns': started,
                   'driver_completed_monotonic_ns': completed,
                   'finished_monotonic_ns': time.monotonic_ns()}
    write_private(run/'http-original-exit.json', exit_record)
    statistics = verify_samples(root, run, manifest)
    require(child.returncode == (0 if statistics['latency_gate'] == 'PASS' else 1), 'original_exit_not_latency_only')
    invocation = read_private(root/'.gate/unit-invocation.json')
    peak = verify_snapshot(snapshot, manifest, invocation)
    allowed = manifest['variant'] == 'F0' or statistics['latency_gate'] == 'PASS'
    wrapped = dict(statistics, status='PASS' if allowed else 'BLOCKED',
                   classification='MEASURED_BASELINE' if manifest['variant'] == 'F0' else 'F1_THRESHOLD_ASSESSED',
                   input_root_sha256=manifest['input_root_sha256'], original_report=binding(original),
                   original_exit=binding(run/'http-original-exit.json'), final_cgroup=binding(run/'driver-final-cgroup.json'),
                   observed_peak_memory_bytes=peak, registration_root_sha256=registration['registration_root_sha256'])
    write_private(arguments.output, wrapped)
    return wrapped


def cleanup_checks(report, snapshots):
    """Require explicit empty-group evidence and absence of every observed incarnation."""
    cleanup = report['cleanup']
    require(cleanup['status'] == 'PASS' and cleanup['populated_zero_observed'] is True
            and cleanup['owned_identities_absent'] is True, 'cleanup_unproven')
    stopped = (cleanup.get('stop_disposition') == 'stop_command' and type(cleanup['stop_exit_code']) is int
               and cleanup['stop_exit_code'] == 0)
    removed = (cleanup.get('stop_disposition') == 'already_removed_after_explicit_empty'
               and type(cleanup['stop_exit_code']) is int and cleanup['stop_exit_code'] == 5
               and cleanup['unit'].get('LoadState') == 'not-found')
    require((stopped or removed) and type(cleanup['graceful_kill_exit_code']) is int
            and cleanup['graceful_kill_exit_code'] == 0, 'cleanup_exit')
    require(containment.counters(cleanup['last_cgroup_events']).get('populated') == 0, 'cleanup_no_explicit_zero')
    for snapshot in snapshots:
        for row in snapshot['processes']:
            require(process_identity(row['pid']) != {'pid': row['pid'], 'start_ticks': row['start_ticks']}, 'owned_identity_survives')
    require(cleanup.get('terminal_resources_complete') is True
            and cleanup.get('terminal_resource_limits_passed') is True, 'terminal_resources_incomplete')
    terminal = cleanup['terminal_resources']
    require(type(terminal['observed_monotonic_ns']) is int
            and all(terminal['observed_monotonic_ns'] >= row['observed_monotonic_ns'] for row in snapshots),
            'terminal_resources_precede_live_snapshot')
    require({'memory.peak', 'memory.events', 'pids.events', 'pids.peak', 'cpu.stat'} <= set(terminal['metrics']),
            'terminal_metrics_missing')
    require(isinstance(terminal['metrics']['pids.peak'], str) and 0 < int(terminal['metrics']['pids.peak']) <= 512,
            'terminal_task_peak')
    cpu = containment.counters(terminal['metrics']['cpu.stat'])
    require('usage_usec' in cpu and all(value >= 0 for value in cpu.values()), 'terminal_cpu_counters')
    peak = resource_peak(terminal)
    require(peak >= max(int(row['metrics']['memory.peak']) for row in snapshots), 'terminal_peak_regressed')
    return peak


def verify_trial(registration_path):
    """Recheck source/tooling after cleanup and independently classify one complete raw trial."""
    registration, run, manifest = registration_at(registration_path)
    root = installation.verify(manifest, fresh=False)
    statistics = verify_samples(root, run, manifest)
    exit_record = load(run/'http-original-exit.json')
    require(exit_record['installation_root_sha256'] == manifest['input_root_sha256'], 'original_exit_root')
    require(exit_record['exit_code'] == (0 if statistics['latency_gate'] == 'PASS' else 1), 'original_exit_mismatch')
    require(exit_record['driver_sha256'] == digest(HERE/'http_driver.py'), 'original_exit_implementation')
    report = load(run/'report.json')
    require(report['input_root_sha256'] == manifest['input_root_sha256'] and report['benchmark_executed'] is True, 'controller_root')
    require(report['verifier_sha256'] == digest(HERE/'controller.py'), 'controller_verifier_hash')
    final = load(run/'driver-final-cgroup.json')
    require(final['observed_monotonic_ns'] >= exit_record['driver_completed_monotonic_ns'], 'final_snapshot_precedes_driver_exit')
    wrapped = load(run/'driver-report.json')
    for field, name in (('original_report', 'http-original-report.json'), ('original_exit', 'http-original-exit.json'),
                        ('final_cgroup', 'driver-final-cgroup.json')):
        require(wrapped[field] == binding(run/name), 'wrapper_sidecar_binding_' + field)
    require(wrapped['input_root_sha256'] == manifest['input_root_sha256']
            and wrapped['registration_root_sha256'] == registration['registration_root_sha256'], 'wrapper_root')
    require(all(equal(wrapped[key], value) for key, value in statistics.items()), 'wrapper_statistics')
    snapshots = report['snapshots'] + [final]
    require(report['snapshots'], 'missing_controller_observation')
    invocation = read_private(root/'.gate/unit-invocation.json')
    readiness = read_private(root/'.gate/evidence/ready.json')
    require(readiness['supervisor'] == invocation['main_identity'], 'ready_supervisor_mismatch')
    peak = max(verify_snapshot(row, manifest, invocation) for row in snapshots)
    peak = max(peak, cleanup_checks(report, snapshots))
    allowed = manifest['variant'] == 'F0' or statistics['latency_gate'] == 'PASS'
    require(report['status'] == 'PASS' if allowed else report['status'] == 'BLOCKED', 'controller_classification')
    if allowed:
        require(report.get('checks_passed_before_cleanup') is True and 'blocking_reason' not in report, 'controller_incomplete_checks')
        require(report['driver']['report_sha256'] == digest(run/'driver-report.json'), 'controller_driver_report_binding')
    else:
        require(report.get('blocking_reason') == 'registered_driver_failed', 'f1_unexpected_failure')
    return dict(statistics, status='PASS' if allowed else 'BLOCKED', valid_measurement=allowed,
                classification='MEASURED_BASELINE' if manifest['variant'] == 'F0' else 'F1_THRESHOLD_ASSESSED',
                pair=registration['pair'], variant=manifest['variant'], input_root_sha256=manifest['input_root_sha256'],
                experiment_root_sha256=registration['experiment_root_sha256'],
                registration_path=str(registration_path.resolve()),
                registration_root_sha256=registration['registration_root_sha256'], observed_peak_memory_bytes=peak,
                evidence=[binding(run/name) for name in ('report.json', 'driver-report.json', 'http-original-report.json',
                          'http-original-exit.json', 'driver-final-cgroup.json', 'http-private/requests-manifest.json',
                          'http-private/samples.jsonl')], target_acceptance='OPEN', profile_activation='NOT_PERFORMED')


def finish_history(registration, verdict):
    """Record immutable pair comparisons and stop the finite experiment on its first failure."""
    history, pair = Path(registration['history']), registration['pair']
    value = experiment_at(registration['experiment_binding']['path'])
    history_anchor(history, registration['experiment_binding']['path'], value)
    previous = check_order(history, pair, verdict['variant'], value)
    run = Path(registration['run'])
    require(equal(load(run/'pair-verification.json'), verdict), 'current_verdict_file_disagrees')
    if verdict['valid_measurement'] is True:
        require(equal(verify_trial(run/'pair-registration.json'), verdict), 'current_verdict_replay_mismatch')
    entry = {'pair': pair, 'variant': verdict['variant'], 'previous_trial': previous,
             'experiment_root_sha256': value['input_root_sha256'], 'input_root_sha256': verdict['input_root_sha256'],
             'verdict': binding(run/'pair-verification.json')}
    write_private(history_path(history, pair, verdict['variant']), entry)
    paths = [history_path(history, pair, variant) for variant in ('F0', 'F1')]
    failed = verdict['valid_measurement'] is not True
    if all(path.exists() for path in paths):
        baseline, candidate = [load(load(path)['verdict']['path']) for path in paths]
        comparison = pair_summary(history, pair, value, baseline, candidate)
        write_private(history/f'pair-{pair}.json', comparison)
        failed = failed or comparison['status'] != 'PASS'
    if failed or (pair == 3 and all(path.exists() for path in paths)):
        trials = [{'pair': number, 'variant': variant,
                   'status': 'RECORDED' if history_path(history, number, variant).exists() else 'NOT_EXECUTED',
                   'record': binding(history_path(history, number, variant)) if history_path(history, number, variant).exists() else None}
                  for number, variant in ORDER]
        write_private(history/'selection.json', {'status': 'KEEP_F0' if failed else 'THREE_HTTP_PAIRS_PASSED',
                      'experiment': registration['experiment_binding'], 'experiment_root_sha256': value['input_root_sha256'],
                      'pairs': [binding(history/f'pair-{number}.json') for number in range(1, 4) if (history/f'pair-{number}.json').exists()],
                      'trials': trials, 'target_acceptance': 'OPEN', 'profile_activation': 'NOT_PERFORMED',
                      'boundary': 'Other selection gates and root authorization remain required; no activation here.'})


def run_trial(arguments):
    """Release and execute only an already frozen ordered trial; never activate a profile."""
    require(arguments.release_schedule, 'explicit_schedule_release_required')
    registration, run, manifest = registration_at(arguments.registration)
    lock = os.open(Path(registration['history'])/'execution.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute_trial(arguments, registration, run, manifest)
    finally:
        os.close(lock)


def execute_trial(arguments, registration, run, manifest):
    """Hold the experiment lock through owned cleanup and immutable verdict recording."""
    experiment = experiment_at(registration['experiment_binding']['path'])
    check_order(Path(registration['history']), registration['pair'], registration['variant'], experiment)
    installation.verify(manifest, fresh=True)
    release = {'status': 'SCHEDULE_RELEASED', 'installation_root_sha256': manifest['input_root_sha256'],
               'other_performance_work_finished': True, 'containment_preflight_run': registration['preflight'],
               'runtime_registration_sha256': digest(run/'pair-runtime-registration.json')}
    write_private(run/'pair-schedule-release.json', release)
    descriptor = os.open(run/'pair-controller-private.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            result = subprocess.run([sys.executable, str(HERE/'controller.py'), 'stack', '--run', str(run),
                                     '--runtime-registration', str(run/'pair-runtime-registration.json'),
                                     '--schedule-release', str(run/'pair-schedule-release.json')],
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=1650)
        write_private(run/'pair-controller-exit.json', {'exit_code': result.returncode})
        verdict = verify_trial(arguments.registration)
        require(result.returncode == (0 if verdict['valid_measurement'] else 1), 'controller_exit_mismatch')
    except Exception as error:
        cleanup = emergency_cleanup(run, manifest)
        verdict = {'status': 'BLOCKED', 'valid_measurement': False, 'pair': registration['pair'],
                   'variant': registration['variant'], 'failure_class': type(error).__name__,
                   'reason': str(error) if type(error) is ValueError else 'verification_failed',
                   'input_root_sha256': manifest['input_root_sha256'], 'profile_activation': 'NOT_PERFORMED',
                   'experiment_root_sha256': registration['experiment_root_sha256'], 'failure_cleanup': cleanup}
    write_private(run/'pair-verification.json', verdict)
    finish_history(registration, verdict)
    return {'status': verdict['status'], 'classification': verdict.get('classification'),
            'report': str(run/'pair-verification.json'), 'p95_ms': verdict.get('p95_ms')}


def emergency_cleanup(run, manifest):
    """Attempt exact owned cleanup after a controller failure; unknown evidence never admits another trial."""
    report_path = run/'report.json'
    if report_path.is_file() and load(report_path).get('cleanup', {}).get('status') == 'PASS':
        return {'status': 'RETAINED_CONTROLLER_CLEANUP', 'report': binding(report_path)}
    result = {'status': 'UNKNOWN', 'reason': 'no_owned_invocation'}
    try:
        witness = read_private(Path(manifest['copied_root'])/'.gate/unit-invocation.json')
        result = containment.stop(manifest, [witness['main_identity']], witness['invocation_id'])
    except Exception as error:
        result = {'status': 'UNKNOWN', 'failure_class': type(error).__name__}
    path = run/'pair-emergency-cleanup.json'
    write_private(path, result)
    return {'status': result['status'], 'report': binding(path)}


def parser():
    """Expose a wrapper-compatible driver mode plus explicit freeze/release/verify operations."""
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('operation', nargs='?', choices=('freeze', 'run', 'verify'))
    result.add_argument('--root', type=Path)
    result.add_argument('--output', type=Path)
    result.add_argument('--run', type=Path)
    result.add_argument('--pair', type=int, choices=(1, 2, 3))
    result.add_argument('--variant', choices=('F0', 'F1'))
    result.add_argument('--history', type=Path)
    result.add_argument('--prerequisites', type=Path)
    result.add_argument('--experiment-binding', type=Path)
    result.add_argument('--preflight', type=Path)
    result.add_argument('--registration', type=Path)
    result.add_argument('--release-schedule', action='store_true')
    return result


def main():
    """Report bounded classifications only; private controller/HTTP logs remain on disk."""
    arguments = parser().parse_args()
    operation = {'freeze': freeze, 'run': run_trial, 'verify': lambda args: verify_trial(args.registration)}
    try:
        result = operation[arguments.operation](arguments) if arguments.operation else driver(arguments)
        print(json.dumps(result if arguments.operation else {'status': result['status'], 'classification': result['classification']}))
        return 1 if result.get('status') == 'BLOCKED' else 0
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'failure_class': type(error).__name__,
                          'reason': str(error) if type(error) is ValueError else 'operation_failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
