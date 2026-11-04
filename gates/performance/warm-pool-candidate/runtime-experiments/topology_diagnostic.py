#!/usr/bin/env python3
"""Freeze and run one Python-only delegated-topology development diagnostic."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import containment
import scope_launch
from harness_common import HERE, digest, read_private, record, root_hash, validate_root, write_private

PROGRAMS = ('harness_common.py', 'containment.py', 'delegation.py', 'scope_launch.py', 'topology_diagnostic.py')
TOOLS = ('/usr/bin/python3', '/usr/bin/systemd-run', '/usr/bin/systemctl', '/usr/bin/taskset', '/usr/bin/env',
         '/etc/apparmor.d/chatgpt', '/etc/apparmor.d/unprivileged_userns')
HOLD = 'import signal; signal.pause()'


def freeze(run_id):
    """Bind finite trusted launch inputs and expectations before creating any unit."""
    if not run_id.startswith('topology-dev-') or '/' in run_id or '..' in run_id:
        raise ValueError('diagnostic_run_id_required')
    run = HERE/'runs'/run_id
    run.mkdir(mode=0o700, parents=True, exist_ok=False)
    root = Path(tempfile.mkdtemp(prefix='allow-wp-'))
    (root/'.gate/tmp').mkdir(mode=0o700, parents=True)
    rows = []
    for name in PROGRAMS:
        shutil.copy2(HERE/name, root/'.gate'/name)
        rows.append(record(root/'.gate'/name, root))
    value = {'kind': 'PYTHON_ONLY_TOPOLOGY_DEVELOPMENT_DIAGNOSTIC', 'copied_root': str(root),
             'unit': 'allow-wp-'+uuid.uuid4().hex+'.scope', 'files': rows,
             'tools': [dict(record(Path(name).resolve()), invocation=name) for name in TOOLS],
             'hold_program': HOLD, 'limits': containment.EXPECTED,
             'predicates': ['empty_scope_root', 'exact_control_owner', 'exact_runtime_config',
                            'all_observed_thread_affinity', 'caller_context_preserved',
                            'positive_empty_and_terminal_counters', 'owned_incarnations_absent'],
             'trusted': ['Linux kernel', 'systemd user manager', 'Python interpreter and standard library'],
             'no_allow_jvm_sql_model_or_performance_execution': True, 'acceptance_evidence': False}
    value['input_root_sha256'] = root_hash(value)
    write_private(root/'.gate/manifest.json', value)
    write_private(run/'manifest.json', value)
    return {'status': 'FROZEN_NOT_EXECUTED', 'run': str(run), 'input_root_sha256': value['input_root_sha256']}


def verify(manifest):
    """Check original and copied programs, exact tools and explicit finite predicates."""
    root = validate_root(manifest['copied_root'])
    if root_hash(manifest) != manifest['input_root_sha256'] or manifest['hold_program'] != HOLD:
        raise ValueError('diagnostic_input_root')
    for row in manifest['files']:
        if record(root/row['path'], root) != row or digest(HERE/Path(row['path']).name) != row['sha256']:
            raise ValueError('diagnostic_program_changed')
    for row in manifest['tools']:
        if str(Path(row['invocation']).resolve()) != row['path'] or record(Path(row['path'])) != {k:v for k,v in row.items() if k != 'invocation'}:
            raise ValueError('diagnostic_tool_changed')
    return root


def execute(run):
    """Run no application payload; collect two snapshots then stop only the owned scope."""
    run = run.resolve(strict=True)
    if not run.is_relative_to(HERE/'runs'):
        raise ValueError('diagnostic_run_path')
    manifest = read_private(run/'manifest.json')
    root = verify(manifest)
    write_private(run/'execution-started.json', {'input_root_sha256': manifest['input_root_sha256']})
    report = {'status': 'BLOCKED', 'classification': manifest['kind'], 'acceptance_evidence': False,
              'input_root_sha256': manifest['input_root_sha256'], 'snapshots': []}
    state, child, owned = None, None, []
    try:
        state, child = scope_launch.launch(manifest, '/usr/bin/python3', ['-B', '-c', HOLD], 30)
        for _ in range(2):
            snapshot = scope_launch.observe(manifest, owned)
            report['snapshots'].append(snapshot)
            owned = [{key: row[key] for key in ('pid', 'start_ticks')} for row in snapshot['processes']]
            if containment.exhausted(snapshot):
                raise ValueError('diagnostic_resource_exhaustion')
        verify(manifest)
        report['checks_passed'] = True
    except Exception as error:
        report['failure_class'] = type(error).__name__
        report['reason'] = str(error) if type(error) is ValueError else 'diagnostic_failed'
    finally:
        cleanup(root, manifest, state, child, owned, report)
        write_private(run/'report.json', report)
    return {'status': report['status'], 'report': str(run/'report.json')}


def cleanup(root, manifest, state, child, owned, report):
    """Retain physical cleanup uncertainty and always reap the exact launcher."""
    try:
        if state is not None:
            report['cleanup'] = containment.stop(manifest, owned, state['InvocationID'])
        else:
            report['cleanup'] = read_private(root/'.gate/scope-failed-cleanup.json')['unit']
    except Exception as error:
        report['cleanup'] = {'status': 'UNKNOWN', 'class': type(error).__name__}
    finally:
        if child is not None:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
            report['launcher_reaped'] = child.poll() is not None
    if report.get('checks_passed') is True and report['cleanup']['status'] == 'PASS' and report.get('launcher_reaped') is True:
        report['status'] = 'PASS'


def main():
    """Keep registration and execution separate; never overwrite historical diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('freeze', 'execute'))
    parser.add_argument('--run-id')
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    result = freeze(args.run_id) if args.operation == 'freeze' else execute(args.run)
    print(json.dumps(result))
    return 1 if result['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
