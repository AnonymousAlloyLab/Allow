#!/usr/bin/env python3
"""Freeze and control the finite copied-stack gate; never benchmark without a bound release."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

import containment
import installation
from harness_common import (HERE, ROOT, digest, packed, process_identity, read_private, record,
                            root_hash, same_process, validate_root, write_private)


def read_run(path):
    """Require a private registered run directory, without trusting a supplied arbitrary unit."""
    path = path.resolve()
    if not path.is_relative_to(HERE/'runs') or path == HERE/'runs':
        raise ValueError('gate_registered_run_required')
    manifest = read_private(path/'manifest.json')
    validate_root(manifest['copied_root'])
    if root_hash(manifest) != manifest['input_root_sha256']:
        raise ValueError('manifest_root_mismatch')
    if not re.fullmatch(r'allow-ft1-[0-9a-f]{32}\.service', manifest['unit']):
        raise ValueError('unique_owned_unit_required')
    return path, manifest


def freeze_preflight(arguments):
    """Freeze finite expected predicates, probe/verifier bytes and tool identities before launch."""
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,40}', arguments.run_id):
        raise ValueError('run_id_invalid')
    run = HERE/'runs'/arguments.run_id
    run.mkdir(mode=0o700, parents=True, exist_ok=False)
    root = Path(tempfile.mkdtemp(prefix='allow-ft1-'))
    root.chmod(0o700)
    (root/'.gate').mkdir(mode=0o700)
    names = ('harness_common.py', 'containment.py', 'probe_owner.py', 'controller.py',
             'installation.py', 'preflight-registration.json')
    files = []
    for name in names:
        shutil.copy2(HERE/name, root/'.gate'/name)
        files.append(record(root/'.gate'/name, root))
    manifest = {'schema_version': '1.0', 'kind': 'CONTAINMENT_PREFLIGHT', 'run_id': arguments.run_id,
                'copied_root': str(root), 'unit': 'allow-ft1-' + uuid.uuid4().hex + '.service',
                'files': files, 'tools': [record(Path(name).resolve()) for name in
                ('/usr/bin/python3', '/usr/bin/systemctl', '/usr/bin/systemd-run', '/usr/bin/env')],
                'registration_sha256': digest(HERE/'preflight-registration.json'),
                'created_utc': datetime.now(timezone.utc).isoformat()}
    manifest['input_root_sha256'] = root_hash(manifest)
    write_private(run/'manifest.json', manifest)
    write_private(root/'.gate/manifest.json', manifest)
    return {'status': 'FROZEN_NOT_EXECUTED', 'run': str(run), 'input_root_sha256': manifest['input_root_sha256']}


def verify_preflight(manifest):
    """Reject any source, verifier, predicate or pinned executable change before the probe."""
    root = validate_root(manifest['copied_root'])
    for row in manifest['files']:
        if record(root/row['path'], root) != row or digest(HERE/Path(row['path']).name) != row['sha256']:
            raise ValueError('frozen_preflight_input_mutation')
    for row in manifest['tools']:
        if record(Path(row['path'])) != row:
            raise ValueError('preflight_tool_mutation')
    if manifest['registration_sha256'] != digest(HERE/'preflight-registration.json'):
        raise ValueError('preflight_predicate_mutation')
    if (root/'.gate/probe-owner.json').exists():
        raise ValueError('probe_run_already_started')
    return root


def host_observation(root):
    """Record pressure, CPU/storage identity and host context without reading unrelated app data."""
    fields = ('cpu', 'memory', 'io')
    info = root.stat()
    return {'kernel': platform.release(), 'machine': platform.machine(), 'logical_cpus': os.cpu_count(),
            'controller_affinity': sorted(os.sched_getaffinity(0)), 'loadavg': list(os.getloadavg()),
            'pressure': {name: Path('/proc/pressure', name).read_text().strip() for name in fields},
            'root_storage_device': {'major': os.major(info.st_dev), 'minor': os.minor(info.st_dev)},
            'cpu_model_lines': sorted(set(line for line in Path('/proc/cpuinfo').read_text().splitlines()
                                           if line.startswith(('model name', 'cpu family', 'model\t')))),
            'interpretation': 'Workstation screen only; actual 4vCPU/8GiB target acceptance remains OPEN'}


def collect(manifest, known, snapshots):
    """Append immutable point observations and retain every seen incarnation for cleanup."""
    snapshot = containment.observe(manifest, list(known.values()))
    for row in snapshot['processes']:
        identity = {key: row[key] for key in ('pid', 'start_ticks')}
        known[(identity['pid'], identity['start_ticks'])] = identity
    snapshots.append(snapshot)
    if containment.exhausted(snapshot):
        raise ValueError('oom_or_pids_exhaustion')
    return snapshot


def wait_witness(root, manifest, known, snapshots, probe):
    """Observe containment during bounded startup, requiring all exact ready owners in-group."""
    target = root/'.gate/probe-owner.json' if probe else root/'.gate/evidence/ready.json'
    deadline = time.monotonic() + (10 if probe else 180)
    while time.monotonic() < deadline:
        snapshot = collect(manifest, known, snapshots)
        if (root/'.gate/evidence/failure.json').exists():
            raise ValueError('owned_stack_startup_failed')
        if target.exists():
            value = read_private(target)
            names = ('supervisor', 'child') if probe else ('supervisor', 'spring', 'postgres', 'proxy')
            owners = [value[name] for name in names]
            if any(not same_process(owner) or (owner['pid'], owner['start_ticks']) not in known for owner in owners):
                raise ValueError('readiness_owner_missing_or_changed')
            return value
        time.sleep(.05 if probe else .25)
    raise ValueError('owned_readiness_deadline')


def registration(arguments, manifest):
    """Admit only a separately frozen fixture/comparator/driver package and explicit release."""
    release = json.loads(arguments.schedule_release.read_text())
    if release.get('status') != 'SCHEDULE_RELEASED' or release.get('other_performance_work_finished') is not True:
        raise ValueError('scheduling_hold_not_released')
    if release.get('installation_root_sha256') != manifest['input_root_sha256']:
        raise ValueError('scheduling_release_wrong_root')
    require_preflight(Path(release['containment_preflight_run']))
    if arguments.operation == 'stack-readiness':
        return None
    value = json.loads(arguments.runtime_registration.read_text())
    if value.get('status') != 'FROZEN_RUNTIME_INPUTS' or value.get('installation_root_sha256') != manifest['input_root_sha256']:
        raise ValueError('runtime_registration_root_missing')
    if release.get('runtime_registration_sha256') != digest(arguments.runtime_registration):
        raise ValueError('runtime_registration_not_released')
    for name in ('finite_semantics', 'comparator_negative_cases', 'p1_regressions'):
        if value.get('prerequisites', {}).get(name) != 'PASS':
            raise ValueError('runtime_prerequisite_not_passed_' + name)
    for row in value['files']:
        if digest(Path(row['path'])) != row['sha256']:
            raise ValueError('runtime_frozen_input_mismatch')
    driver = value['driver']
    if driver not in value['files'] or not Path(driver['path']).resolve().is_relative_to(HERE):
        raise ValueError('registered_gate_driver_required')
    return value


def require_preflight(run):
    """Bind preflight PASS to this exact current containment verifier and frozen predicates."""
    directory, frozen = read_run(run)
    report = read_private(directory/'report.json')
    if report.get('status') != 'PASS' or report.get('input_root_sha256') != frozen['input_root_sha256']:
        raise ValueError('containment_preflight_not_passed')
    if report.get('verifier_sha256') != digest(HERE/'controller.py'):
        raise ValueError('containment_preflight_verifier_stale')
    for row in frozen['files']:
        if digest(HERE/Path(row['path']).name) != row['sha256']:
            raise ValueError('containment_preflight_input_stale')
    cleanup = report.get('cleanup', {})
    if cleanup.get('status') != 'PASS' or cleanup.get('populated_zero_observed') is not True:
        raise ValueError('containment_preflight_cleanup_unproven')
    if not report.get('snapshots') or any(row['limits'] != containment.EXPECTED for row in report['snapshots']):
        raise ValueError('containment_preflight_limits_unproven')


def run_driver(root, run, manifest, bound, known, snapshots):
    """Keep the frozen load driver outside the server cgroup and retain all raw outputs."""
    from harness_common import clean_environment
    descriptor = os.open(run/'driver-private.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    argv = [str(root/'.tools/retrieval-venv/bin/python'), bound['driver']['path'],
            '--root', str(root), '--output', str(run/'driver-report.json')]
    with os.fdopen(descriptor, 'wb') as stream:
        child = subprocess.Popen(argv, cwd=root, env=clean_environment(root), stdout=stream, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 1200
        try:
            group = containment.unit_properties(manifest['unit'])['ControlGroup']
            if containment.pid_group(child.pid) == group or containment.pid_group(child.pid).startswith(group + '/'):
                raise ValueError('load_driver_inside_server_group')
            while child.poll() is None:
                collect(manifest, known, snapshots)
                if time.monotonic() >= deadline:
                    raise ValueError('driver_deadline')
                time.sleep(.25)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
    if child.returncode or not (run/'driver-report.json').is_file():
        raise ValueError('registered_driver_failed')
    report = read_private(run/'driver-report.json')
    if report.get('status') != 'PASS' or report.get('input_root_sha256') != manifest['input_root_sha256']:
        raise ValueError('driver_report_failed_or_unbound')
    return {'exit_code': child.returncode, 'report_sha256': digest(run/'driver-report.json')}


def execute(arguments):
    """Execute one frozen finite run and preserve unknown cleanup as a blocking result."""
    run, manifest = read_run(arguments.run)
    probe = arguments.operation == 'preflight'
    root = verify_preflight(manifest) if probe else installation.verify(manifest)
    bound = None if probe else registration(arguments, manifest)
    write_private(run/'execution-started.json', {'input_root_sha256': manifest['input_root_sha256'],
                  'verifier_sha256': digest(HERE/'controller.py'), 'operation': arguments.operation})
    report = {'status': 'BLOCKED', 'input_root_sha256': manifest['input_root_sha256'],
              'run_id': manifest['run_id'], 'verifier_sha256': digest(HERE/'controller.py'),
              'classification': 'TESTED_SCREEN_ONLY_NOT_RUNTIME_CLOSURE', 'host': host_observation(root),
              'target_acceptance': 'OPEN', 'snapshots': [], 'benchmark_executed': bound is not None}
    known, launched = {}, None
    try:
        python = '/usr/bin/python3' if probe else root/'.tools/retrieval-venv/bin/python'
        entrypoint = root/'.gate'/('probe_owner.py' if probe else 'stack_owner.py')
        launched = containment.launch(manifest, python, [entrypoint], 30 if probe else 1500)
        report['readiness'] = wait_witness(root, manifest, known, report['snapshots'], probe)
        if bound is not None:
            report['driver'] = run_driver(root, run, manifest, bound, known, report['snapshots'])
        collect(manifest, known, report['snapshots'])
        if not probe:
            installation.verify(manifest, fresh=False)
        if bound is not None and any(int(row['metrics'].get('memory.peak', 0)) > 5368709120 for row in report['snapshots']):
            raise ValueError('whole_stack_peak_exceeds_selection_gate')
        report['checks_passed_before_cleanup'] = True
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        report['blocking_reason'] = str(error) if type(error) is ValueError else 'registered_operation_failed'
    finally:
        finish_execution(run, root, manifest, launched, known, report)
    return {'report': str(run/'report.json'), 'status': report['status'], 'target_acceptance': 'OPEN'}


def finish_execution(run, root, manifest, launched, known, report):
    """Keep evidence even when cleanup loses authority or cannot observe an empty group."""
    write_private(run/'outcome-before-cleanup.json', report)
    try:
        state = launched or containment.unit_properties(manifest['unit'])
        if state.get('Description') == 'allow-fresh:' + manifest['input_root_sha256']:
            report['cleanup'] = containment.stop(manifest, list(known.values()), state['InvocationID'])
        else:
            report['cleanup'] = {'status': 'UNKNOWN', 'reason': 'no_owned_unit_incarnation'}
    except BaseException as error:
        report['cleanup'] = {'status': 'UNKNOWN', 'failure_class': type(error).__name__}
    if report.get('checks_passed_before_cleanup') and report['cleanup']['status'] == 'PASS':
        report['status'] = 'PASS'
    report['host_after'] = host_observation(root)
    report['boundary'] = 'Finite sampled containment/ownership evidence; not universal escape prevention or target acceptance.'
    write_private(run/'report.json', report)


def parser():
    """Expose preparation, separate freeze/probe, and guarded whole-stack operations."""
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='operation', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--run-id', required=True)
    prepare.add_argument('--source-ready', required=True, type=Path)
    freeze = commands.add_parser('preflight-freeze')
    freeze.add_argument('--run-id', required=True)
    for name in ('preflight', 'stack-readiness', 'stack'):
        operation = commands.add_parser(name)
        operation.add_argument('--run', required=True, type=Path)
        if name != 'preflight':
            operation.add_argument('--schedule-release', required=True, type=Path)
        if name == 'stack':
            operation.add_argument('--runtime-registration', required=True, type=Path)
    return result


def main():
    """Publish public paths and statuses only; private logs never enter terminal output."""
    arguments = parser().parse_args()
    operation = {'prepare': installation.prepare, 'preflight-freeze': freeze_preflight}.get(arguments.operation, execute)
    try:
        result = operation(arguments)
        print(json.dumps(result))
        if result.get('status') == 'BLOCKED':
            return 1
    except BaseException as error:
        print(json.dumps({'status': 'BLOCKED', 'failure_class': type(error).__name__,
                          'reason': str(error) if type(error) is ValueError else 'operation_failed'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
