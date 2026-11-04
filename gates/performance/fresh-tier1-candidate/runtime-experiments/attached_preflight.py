#!/usr/bin/env python3
"""Freeze and test caller-context attachment plus unchanged real worker isolation."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import attached_launch
import containment
import controller
import installation
from harness_common import HERE, clean_environment, digest, process_identity, read_private, record, root_hash, write_private

PROGRAMS = ('attached_preflight.py', 'attached_launch.py', 'containment.py', 'controller.py',
            'installation.py', 'harness_common.py', 'test_attached_launch.py')


def freeze(arguments):
    """Freeze all expected predicates, actual worker bytes and tool context before execution."""
    run = HERE/'runs'/arguments.run_id
    run.mkdir(mode=0o700, exist_ok=False)
    root = Path(tempfile.mkdtemp(prefix='allow-ft1-'))
    (root/'.gate/tmp').mkdir(mode=0o700, parents=True)
    for name in PROGRAMS:
        shutil.copy2(HERE/name, root/'.gate'/name)
    source = json.loads(arguments.source_ready.read_text())
    for row in source['probe_classes']:
        copied = root/'.gate/probe-classes'/row['path']
        copied.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(Path(source['backend_target']['path'])/'test-classes'/row['path'], copied)
    existing = read_private(arguments.tool_manifest)
    frame = HERE/'fixtures-final-r2/source-supported.json'
    shutil.copy2(frame, root/'.gate/frame.json')
    scope = getattr(arguments, 'scope', False)
    manifest = {'kind': 'CALLER_CONTEXT_SCOPE_PREFLIGHT' if scope else 'ATTACHED_CALLER_CONTEXT_PREFLIGHT', 'run_id': arguments.run_id,
                'copied_root': str(root), 'unit': 'allow-ft1-'+uuid.uuid4().hex+('.scope' if scope else '.service'),
                'files': [record(root/'.gate'/name, root) for name in (*PROGRAMS, 'frame.json')] +
                         [record(root/'.gate/probe-classes'/row['path'], root) for row in source['probe_classes']],
                'tooling': existing['tooling'], 'java': existing['java'],
                'backend_target': source['backend_target'], 'probe_classes': source['probe_classes'],
                'build_identity': installation.build_identity(Path(source['backend_target']['path']).parent.parent,
                                                              existing['java']['runtime_version'])['value'],
                'source_ready': record(arguments.source_ready), 'busctl': record(Path('/usr/bin/busctl').resolve()),
                'scope_tools': [record(Path('/usr/bin/taskset').resolve())] if scope else [],
                'scope_protocol': {'delegation': False, 'affinity': 'trusted taskset before scope creation; every thread verified before release',
                                   'umask': 'Popen0077', 'release': 'private exact owner+root+invocation record',
                                   'application_exec': 'only after exact kernel scope limits and placement verification'} if scope else None,
                'caller_context': attached_launch.security(os.getpid()),
                'policy_inputs': [record(Path(name)) for name in ('/etc/apparmor.d/chatgpt', '/etc/apparmor.d/unprivileged_userns')],
                'expected': {'limits': containment.EXPECTED, 'affinity': [0, 1, 2, 3], 'same_caller_context': True,
                 'before_release_all_threads_contained': True, 'worker_outcome': 'COMPLETE_RESPONSE',
                 'worker_status': 'VALIDATED', 'worker_exit_code': 0, 'worker_reaped': True,
                 'cleanup': 'explicit populated=0 and all observed incarnations absent',
                 'production_changes': False, 'security_policy_changes': False, 'benchmark': False}}
    manifest['input_root_sha256'] = root_hash(manifest)
    write_private(root/'.gate/manifest.json', manifest)
    write_private(run/'manifest.json', manifest)
    return {'status': 'FROZEN_NOT_EXECUTED', 'run': str(run), 'root': manifest['input_root_sha256']}


def verify(manifest):
    """Require exact frozen target, probe, tooling and programs, with no source substitution."""
    root = Path(manifest['copied_root'])
    if read_private(root/'.gate/manifest.json') != manifest:
        raise ValueError('owned_manifest_changed')
    for row in manifest['files']:
        if record(root/row['path'], root) != row:
            raise ValueError('preflight_copied_input_changed')
        if Path(row['path']).name in PROGRAMS and digest(HERE/Path(row['path']).name) != row['sha256']:
            raise ValueError('preflight_verifier_changed')
    for row in [manifest['busctl'], manifest['source_ready'], *manifest['policy_inputs'], *manifest.get('scope_tools', [])]:
        if record(Path(row['path'])) != row:
            raise ValueError('preflight_absolute_input_changed')
    target = Path(manifest['backend_target']['path'])
    for row in manifest['backend_target']['files']:
        if record(target/row['path'], target) != row:
            raise ValueError('preflight_backend_changed')
    for row in manifest['probe_classes']:
        if record(target/'test-classes'/row['path'], target/'test-classes') != row:
            raise ValueError('preflight_probe_changed')
    installation.verify_tools(manifest['tooling'])
    if attached_launch.security(os.getpid()) != manifest['caller_context']:
        raise ValueError('preflight_caller_context_changed')
    return root


def owner(root):
    """Run the unchanged real launcher only after verified service placement."""
    manifest = read_private(root/'.gate/manifest.json')
    target = Path(manifest['backend_target']['path'])
    classpath = os.pathsep.join(map(str, [root/'.gate/probe-classes', target/'classes', target/'dependency/*']))
    argv = [manifest['java']['executable'], '-Xms128m', '-Xmx1024m', '-XX:MaxMetaspaceSize=256m',
            '-XX:ReservedCodeCacheSize=128m', '-XX:ActiveProcessorCount=4', '-cp', classpath,
            'dev.allow.backend.FreshTier1ProbeMain', '--target', str(target), '--profile', 'F0',
            '--input', str(root/'.gate/frame.json'), '--output', str(root/'.gate/worker-private.json')]
    with (root/'.gate/probe-private.log').open('xb') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=stream, timeout=30, env=clean_environment(root))
    write_private(root/'.gate/worker-complete.json', {'exit_code': result.returncode, 'owner': process_identity(os.getpid())})
    while True:
        time.sleep(1)


def check_worker(root, manifest, known):
    """Check the complete finite frame and successful actual worker exit/reaping."""
    completed = read_private(root/'.gate/worker-complete.json')
    outcome = read_private(root/'.gate/worker-private.json')
    if outcome.get('buildIdentity') != manifest['build_identity'] or outcome.get('inputSha256') != digest(root/'.gate/frame.json'):
        raise ValueError('actual_worker_frozen_input_binding')
    if outcome.get('profile') != 'DEFAULT' or outcome.get('workerPid') not in {row['pid'] for row in known.values()}:
        raise ValueError('actual_worker_containment_witness_missing')
    if completed['exit_code'] or outcome.get('outcome') != 'COMPLETE_RESPONSE':
        raise ValueError('actual_worker_launch_failed')
    if outcome.get('reaped') is not True or outcome.get('workerExitCode') != 0 or outcome.get('noWorkerStarted') is not False:
        raise ValueError('actual_worker_reap_failed')
    raw = base64.b64decode(outcome['responseBase64'], validate=True)
    if len(raw) != outcome['responseBytes'] or hashlib.sha256(raw).hexdigest() != outcome['responseSha256']:
        raise ValueError('actual_worker_response_integrity')
    response = json.loads(raw)
    if response.get('status') != 'VALIDATED':
        raise ValueError('actual_worker_response_status')
    return {key: value for key, value in outcome.items() if key != 'responseBase64'}


def execute(arguments):
    """Execute one preregistered finite attachment/worker/cleanup witness without load work."""
    run, manifest = controller.read_run(arguments.run)
    root = verify(manifest)
    write_private(run/'execution-started.json', {'input_root_sha256': manifest['input_root_sha256']})
    report = {'status': 'BLOCKED', 'input_root_sha256': manifest['input_root_sha256'],
              'classification': 'ATTACHMENT_WORKER_PREFLIGHT_ONLY', 'benchmark_executed': False,
              'snapshots': [], 'verifier_sha256': digest(Path(__file__))}
    launched, child, known = None, None, {}
    try:
        launched, child = attached_launch.launch(manifest, sys.executable,
                           ['-B', root/'.gate/attached_preflight.py', 'owner', '--root', root], 90)
        deadline = time.monotonic() + 40
        while not (root/'.gate/worker-complete.json').exists():
            controller.collect(manifest, known, report['snapshots'])
            if child.poll() is not None or time.monotonic() > deadline:
                raise ValueError('attached_worker_deadline_or_exit')
            time.sleep(.02)
        report['worker'] = check_worker(root, manifest, known)
        report['attachment'] = read_private(root/'.gate/attached-launch.json')
        report['anchor'] = read_private(root/'.gate/anchor.json')
        controller.collect(manifest, known, report['snapshots'])
        verify(manifest)
        report['checks_passed_before_cleanup'] = True
    except Exception as error:
        report['failure_class'] = type(error).__name__
        report['blocking_reason'] = str(error) if type(error) is ValueError else 'attachment_preflight_failed'
    finally:
        controller.finish_execution(run, root, manifest, launched, known, report)
        if child is not None:
            child.wait(timeout=5)
    return {'status': report['status'], 'report': str(run/'report.json')}


def main():
    """Keep authoring, execution and the placed worker owner separate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('freeze', 'execute', 'owner'))
    parser.add_argument('--run-id')
    parser.add_argument('--run', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--source-ready', type=Path)
    parser.add_argument('--tool-manifest', type=Path)
    args = parser.parse_args()
    result = {'freeze': freeze, 'execute': execute, 'owner': lambda value: owner(value.root)}[args.operation](args)
    if result is not None:
        print(json.dumps(result))
        return 0 if result['status'] != 'BLOCKED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
