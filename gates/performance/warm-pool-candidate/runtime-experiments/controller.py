#!/usr/bin/env python3
"""Prepare, freeze and execute finite delegated preflights; never run a benchmark."""
import argparse
import json
from pathlib import Path
import sys
import time
import subprocess

import containment
import installation
import probe_results
import scope_launch
import semantic_plan
from harness_common import HERE, digest, read_private, record, root_hash, same_process, write_private


def run_path(path):
    """Keep new evidence exclusively in this candidate's private run directory."""
    result = path.resolve(strict=True)
    if not result.is_relative_to(HERE/'runs') or result == HERE/'runs':
        raise ValueError('candidate_run_directory_required')
    return result


def freeze(arguments):
    """Freeze every actual input and predicate before one finite launch attempt."""
    run = run_path(arguments.run)
    manifest = read_private(run/'manifest.json')
    root = installation.verify(manifest)
    semantic_plan.verify(root/'.gate')
    programs = [record(p) for p in sorted(HERE.glob('*.py'))]
    for row in programs:
        if digest(root/'.gate'/Path(row['path']).name) != row['sha256']:
            raise ValueError('copied_verifier_differs_from_current_registration')
    cases, claims = read_private(root/'.gate/probe-cases.json'), read_private(root/'.gate/runtime-claims.json')
    probe_results.check_plan(root/'.gate', cases)
    if len(claims['claims']) != 4 or {row['id'] for row in claims['claims']} != {'WP-H01', 'WP-H02', 'WP-H03', 'WP-H04'}:
        raise ValueError('finite_harness_claim_set_required')
    if arguments.mode == 'ACCEPTANCE' and (cases['status'] != 'MATERIALIZED_RUNTIME_CASES'
            or claims['status'] != 'FROZEN_FINITE_RUNTIME_CLAIMS'):
        raise ValueError('concrete_case_and_claim_freeze_required')
    if arguments.operation == 'probe' and not (root/'.gate/probe-classes/dev/allow/backend/WarmPoolProbeMain.class').is_file():
        raise ValueError('registered_warm_probe_class_required')
    selected_claims = dict(claims)
    if arguments.operation == 'stack':
        selected_claims['claims'] = [row for row in claims['claims'] if row['id'] != 'WP-H03']
    value = {'schema': 1, 'classification': arguments.mode, 'operation': arguments.operation,
             'installation_manifest': record(run/'manifest.json'), 'installation_root': manifest['input_root_sha256'],
             'claims': selected_claims, 'case_ids': [row['id'] for row in cases['cases']],
             'verifier': record(Path(__file__)), 'programs': programs,
             'benchmark_authorized': False, 'target_host_acceptance': 'OPEN'}
    value['input_root_sha256'] = root_hash(value)
    write_private(run/'preflight-registration.json', value)
    return {'status': 'FROZEN_NOT_EXECUTED', 'registration': str(run/'preflight-registration.json'),
            'input_root_sha256': value['input_root_sha256']}


def registration(run, manifest):
    """Reject changed predicates, code and installation pointers before execution."""
    value = read_private(run/'preflight-registration.json')
    if root_hash(value) != value['input_root_sha256'] or value['benchmark_authorized'] is not False:
        raise ValueError('invalid_preflight_registration')
    if value['installation_manifest'] != record(run/'manifest.json') or value['installation_root'] != manifest['input_root_sha256']:
        raise ValueError('registered_installation_changed')
    for row in [value['verifier'], *value['programs']]:
        if record(Path(row['path'])) != row:
            raise ValueError('registered_verifier_mutated')
    return value


def collect(manifest, known, snapshots):
    """Observe aggregate limits and every currently visible owned descendant/thread."""
    snapshot = scope_launch.observe(manifest, list(known.values()))
    for row in snapshot['processes']:
        identity = {key: row[key] for key in ('pid', 'start_ticks')}
        known[(identity['pid'], identity['start_ticks'])] = identity
    snapshots.append(snapshot)
    if containment.exhausted(snapshot) or int(snapshot['metrics']['memory.peak']) > 5368709120:
        raise ValueError('aggregate_resource_gate_failed')


def wait_complete(root, manifest, kind, known, snapshots, child):
    """Keep a fixed original deadline and collect containment evidence during finite work."""
    name = 'probe-complete.json' if kind == 'probe' else 'ready.json'
    deadline = time.monotonic() + (190 if kind == 'probe' else 120)
    while not (root/'.gate/evidence'/name).exists():
        collect(manifest, known, snapshots)
        if child.poll() is not None or time.monotonic() >= deadline:
            raise ValueError('preflight_owner_exit_or_deadline')
        if (root/'.gate/evidence/failure.json').exists():
            raise ValueError('preflight_stack_owner_failure')
        time.sleep(.1)
    collect(manifest, known, snapshots)
    return probe_results.verify(root, manifest) if kind == 'probe' else stack_result(root, manifest)


def stack_result(root, manifest):
    """Bind readiness to exact live server incarnations in the control leaf."""
    ready = read_private(root/'.gate/evidence/ready.json')
    owner = read_private(root/'.gate/unit-invocation.json')
    if ready['status'] != 'READY' or ready['input_root_sha256'] != manifest['input_root_sha256']:
        raise ValueError('stack_ready_root_binding')
    if ready['supervisor'] != owner['main_identity']:
        raise ValueError('stack_ready_supervisor_binding')
    for name in ('supervisor', 'spring', 'proxy', 'postgres'):
        identity = ready[name]
        if not same_process(identity) or containment.pid_group(identity['pid']) != owner['control_group']+'/control':
            raise ValueError('stack_ready_live_control_ownership')
        containment.process_row(identity['pid'], owner['control_group'])
    return ready


def finish(run, root, manifest, state, child, known, report):
    """Always retain attempted work, terminal counters and exact cleanup uncertainty."""
    write_private(run/'outcome-before-cleanup.json', report)
    try:
        if state is None and child is None and (root/'.gate/scope-failed-cleanup.json').exists():
            failure = read_private(root/'.gate/scope-failed-cleanup.json')
            report['cleanup'] = failure['unit']
            report['launcher_reaped'] = failure['launcher_reaped']
        else:
            invocation = read_private(root/'.gate/unit-invocation.json')
            report['cleanup'] = containment.stop(manifest, list(known.values()), invocation['invocation_id'])
    except Exception as error:
        report['cleanup'] = {'status': 'UNKNOWN', 'failure_class': type(error).__name__}
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
                report['launcher_reaped'] = True
            except Exception as error:
                report['launcher_reaped'] = False
                report['launcher_reap_failure'] = type(error).__name__
    finalize_result(run, manifest, report)


def finalize_result(run, manifest, report):
    """Post-cleanup identity and resources remain mandatory for a finite PASS."""
    try:
        installation.verify(manifest, fresh=False)
        registration(run, manifest)
        report['post_input_identity'] = 'PASS'
    except Exception as error:
        report['post_input_identity'] = type(error).__name__
    terminal = report['cleanup'].get('terminal_resources') or {}
    peak = int(terminal.get('metrics', {}).get('memory.peak', 5368709121))
    good = report.get('checks_passed') is True and report['cleanup']['status'] == 'PASS'
    good = good and report.get('launcher_reaped') is True and report['post_input_identity'] == 'PASS' and peak <= 5368709120
    report['status'] = 'PASS' if good else 'BLOCKED'
    identity = report['post_input_identity'] == 'PASS'
    predicates = {'WP-H01': bool(report['snapshots']) and report.get('checks_passed') is True,
                  'WP-H02': identity, 'WP-H03': report.get('result', {}).get('status') == 'PASS',
                  'WP-H04': report['cleanup']['status'] == 'PASS' and report.get('launcher_reaped') is True and peak <= 5368709120}
    report['claim_results'] = [{'id': row['id'], 'status': 'PASS' if identity and predicates[row['id']] else 'BLOCKED',
                               'kind': row['kind']} for row in report['registered_claims']['claims']]
    if report['classification'] == 'ACCEPTANCE':
        report['closure_state'] = 'VERIFIED' if good else 'BLOCKED'
    else:
        report['acceptance_evidence'] = False
    write_private(run/'report.json', report)


def execute(arguments):
    """Execute exactly the frozen finite operation with no load-driver capability."""
    run = run_path(arguments.run)
    manifest = read_private(run/'manifest.json')
    frozen = registration(run, manifest)
    root = installation.verify(manifest)
    write_private(run/'execution-started.json', {'input_root_sha256': frozen['input_root_sha256']})
    report = {'status': 'BLOCKED', 'classification': frozen['classification'], 'snapshots': [],
              'input_root_sha256': frozen['input_root_sha256'], 'installation_root': manifest['input_root_sha256'],
              'benchmark_executed': False, 'target_host_acceptance': 'OPEN', 'registered_claims': frozen['claims']}
    state, child, known = None, None, {}
    try:
        entry = 'probe_owner.py' if frozen['operation'] == 'probe' else 'stack_owner.py'
        state, child = scope_launch.launch(manifest, sys.executable, ['-B', root/'.gate'/entry], 240)
        report['result'] = wait_complete(root, manifest, frozen['operation'], known, report['snapshots'], child)
        report['checks_passed'] = report['result']['status'] in {'PASS', 'READY'}
    except Exception as error:
        report['failure_class'] = type(error).__name__
        report['blocking_reason'] = str(error) if type(error) is ValueError else 'registered_operation_failed'
    finally:
        finish(run, root, manifest, state, child, known, report)
    return {'status': report['status'], 'report': str(run/'report.json'), 'benchmark_executed': False}


def main():
    """Separate copy, immutable registration and execution into explicit commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--source-ready', type=Path, required=True)
    prepare.add_argument('--run-id', required=True)
    registration_parser = sub.add_parser('freeze')
    registration_parser.add_argument('--run', type=Path, required=True)
    registration_parser.add_argument('--mode', choices=('DIAGNOSTIC', 'ACCEPTANCE'), required=True)
    registration_parser.add_argument('--operation', choices=('probe', 'stack'), required=True)
    execution = sub.add_parser('execute')
    execution.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    result = {'prepare': installation.prepare, 'freeze': freeze, 'execute': execute}[args.command](args)
    print(json.dumps(result))
    return 1 if result.get('status') == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
