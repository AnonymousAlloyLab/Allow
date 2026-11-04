#!/usr/bin/env python3
"""Freeze and run complete regressions in a new synthetic installation only.

No performance selection is made. All database SQL, including migrations and
backup/restore fixtures, uses the copied production SQLeanParser route. Shared
services, credentials, data and compiled artifacts are never mutated.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request

import experiment as support

HERE = Path(__file__).resolve().parent
ROOT = support.ROOT
JAVA = Path('/usr/lib/jvm/java-17-openjdk-amd64/bin/java')


def runtime_links(root):
    """Bind literal aliases and resolutions throughout the managed interpreter installation."""
    managed = root/'.tools/retrieval-venv'
    paths = [managed, *managed.rglob('*')]
    return [{'path': str(path.relative_to(root)), 'target': os.readlink(path),
             'resolved': str(path.resolve())} for path in sorted(paths) if path.is_symlink()]


def copy_file(source, target, expected=None):
    """Copy one regular immutable input with an optional previously frozen digest."""
    before = support.digest(source)
    if source.is_symlink() or (expected is not None and before != expected):
        raise ValueError('unapproved_copy_input')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if support.digest(target) != before or support.digest(source) != before:
        raise ValueError('copy_input_mutated')
    return before


def prepare(args):
    """Pin P1 sources, default compiled target, local models, tooling and test commands."""
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', args.run_id) or not 1024 <= args.port <= 65535:
        raise ValueError('invalid_registered_run_or_port')
    ready = args.source_ready.resolve()
    support.verify_source_ready(ready)
    target_receipt_raw = args.target_ready.read_bytes()
    target_receipt = json.loads(target_receipt_raw)['backend_target']
    run = HERE/'runs'/args.run_id
    run.mkdir(parents=True, mode=0o700, exist_ok=False)
    root = Path(tempfile.mkdtemp(prefix='allow-cc-'))
    root.chmod(0o700)
    files = support.copy_sources(root)
    tools = support.tooling(root)
    for row in target_receipt['files']:
        relative = 'backend/target/' + row['path']
        digest = copy_file(Path(target_receipt['path'])/row['path'], root/relative, row['sha256'])
        files.append({'path': relative, 'sha256': digest})
    extras = [p for folder in ('backend/src', 'frontend/src') for p in (ROOT/folder).rglob('*') if p.is_file()]
    extras += [ROOT/'backend/pom.xml', ROOT/'frontend/package-lock.json']
    extras += [p for p in (ROOT/'.tools/retrieval/models').glob('*') if p.is_file()]
    for source in sorted(extras):
        relative = str(source.relative_to(ROOT))
        files.append({'path': relative, 'sha256': copy_file(source, root/relative)})
    for source in sorted(HERE.glob('*.py')):
        relative = '.gate/' + source.name
        files.append({'path': relative, 'sha256': copy_file(source, root/relative)})
    plan = args.registration.resolve()
    files.append({'path': '.gate/regression-registration.json',
                  'sha256': copy_file(plan, root/'.gate/regression-registration.json')})
    managed_runtime = ROOT/'.tools/retrieval-venv'
    managed_files = []
    for source in sorted(managed_runtime.rglob('*')):
        if not source.is_file():
            continue
        relative = str(source.relative_to(ROOT))
        managed_files.append(relative)
        tools.append({'path': relative, 'sha256': support.digest(source),
                      'resolved': str(source.resolve()), 'size': source.stat().st_size})
    tools.append({'path': str(JAVA), 'sha256': support.digest(JAVA), 'resolved': str(JAVA.resolve())})
    support.verify_source_ready(ready)
    if args.target_ready.read_bytes() != target_receipt_raw:
        raise ValueError('target_receipt_changed_during_copy')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    manifest = {'schema_version': '1.0', 'run_id': args.run_id, 'suite': 'complete-regressions',
                'copied_root': str(root), 'files': files, 'tooling': tools, 'port': args.port,
                'created_utc': datetime.now(timezone.utc).isoformat(),
                'source_ready_sha256': support.digest(ready),
                'target_ready_sha256': support.digest(args.target_ready),
                'target_file_count': len(target_receipt['files']),
                'runtime_binding_version': 1,
                'managed_runtime_files': sorted(managed_files),
                'managed_runtime_links': runtime_links(root),
                'java': str(JAVA), 'profile': 'DEFAULT',
                'boundary': 'Complete finite regressions only; not timing, all33 closure or shared activation.'}
    manifest['input_root_sha256'] = hashlib.sha256(support.packed(
        {key: manifest[key] for key in ('files', 'tooling', 'suite', 'runtime_binding_version',
                                       'managed_runtime_files', 'managed_runtime_links')})).hexdigest()
    support.write_private(run/'manifest.json', manifest)
    support.write_private(root/'.gate/manifest.json', manifest)
    print(json.dumps({'run': str(run), 'copied_root': str(root), 'input_root': manifest['input_root_sha256']}))


def command(root, run, name, argv, timeout):
    """Execute one finite owned command, preserving nonzero outcomes before cleanup."""
    log_path = run/(name + '-private.log')
    descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    environment = support.clean_environment(root)
    environment.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='4',
                       OPENBLAS_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false')
    started = time.monotonic()
    with os.fdopen(descriptor, 'wb') as log:
        child = subprocess.Popen(list(map(str, argv)), cwd=root, env=environment,
                                 stdout=log, stderr=subprocess.STDOUT)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            support.write_private(run/(name + '-timeout.json'), {'status': 'TIMEOUT_BEFORE_CLEANUP'})
            owner = support.process_identity(child.pid)
            if owner:
                support.signal_owned(owner, signal.SIGKILL)
            child.wait(timeout=5)
            raise
    return {'name': name, 'exit_code': code, 'elapsed_seconds': time.monotonic()-started,
            'log_sha256': support.digest(log_path), 'status': 'PASS' if code == 0 else 'BLOCKED'}


def launch_spring(root, run, manifest, label):
    """Launch a bounded default Spring JVM with new authority scoped to this copied root."""
    token = secrets.token_urlsafe(32)
    temporary = root/'.runtime/launch.new'
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(f'http://127.0.0.1:{manifest["port"]}/#token={token}\n')
    os.replace(temporary, root/'.runtime/launch.url')
    environment = support.clean_environment(root)
    environment['ALLOW_TOKEN'] = token
    argv = [manifest['java'], '-Xms128m', '-Xmx1024m', '-XX:MaxMetaspaceSize=256m',
            '-XX:ReservedCodeCacheSize=128m', '-XX:ActiveProcessorCount=4', '-cp',
            'target/classes:target/dependency/*', 'dev.allow.backend.AllowApplication',
            '--server.port='+str(manifest['port']), '--server.address=127.0.0.1',
            '--server.tomcat.threads.max=16', '--server.tomcat.threads.min-spare=2',
            '--server.tomcat.max-connections=32', '--server.tomcat.accept-count=8',
            '--debug=false', '--trace=false', '--logging.level.root=WARN',
            '--logging.level.org.springframework=WARN', '--allow.corpus.root='+str(root)]
    descriptor = os.open(run/(label+'-private.log'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        child = subprocess.Popen(argv, cwd=root/'backend', env=environment, stdout=stream, stderr=subprocess.STDOUT)
    return child, support.process_identity(child.pid), token


def wait_spring(manifest, child, token):
    """Require authorized real documents readiness, never mere TCP-open readiness."""
    deadline = time.monotonic()+60
    request = urllib.request.Request(f'http://127.0.0.1:{manifest["port"]}/api/v1/documents',
                                     headers={'Authorization': 'Bearer '+token})
    while time.monotonic() < deadline and child.poll() is None:
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                value = json.loads(response.read(1048577))
                if response.status == 200 and value.get('status') == 'OK':
                    return
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    raise RuntimeError('owned_spring_not_ready')


def stop_spring(child, identity, crash=False):
    """Signal and reap only the recorded owned Spring incarnation."""
    if child.poll() is None:
        support.signal_owned(identity, signal.SIGKILL if crash else signal.SIGTERM)
    try:
        child.wait(timeout=15)
        escalation = False
    except subprocess.TimeoutExpired:
        support.signal_owned(identity, signal.SIGKILL)
        child.wait(timeout=5)
        escalation = True
    return {'owned_identity_absent': support.process_identity(identity['pid']) != identity,
            'exit_code': child.returncode, 'intentional_crash': crash, 'emergency_escalation': escalation}


def execute(args):
    """Run the registered sequence, stopping at a failed regression and retaining every result."""
    run = args.run.resolve()
    if run.parent != HERE/'runs':
        raise ValueError('registered_run_required')
    manifest_raw = (run/'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    root = support.check_installation(manifest)
    if runtime_links(root) != manifest['managed_runtime_links']:
        raise ValueError('managed_runtime_links_changed_before_execution')
    observed = sorted(str(p.relative_to(root)) for p in (root/'.tools/retrieval-venv').rglob('*') if p.is_file())
    if observed != manifest['managed_runtime_files']:
        raise ValueError('managed_runtime_membership_changed_before_execution')
    python = root/'.tools/retrieval-venv/bin/python'
    report = {'status': 'INFRASTRUCTURE_FAILURE', 'run_id': manifest['run_id'],
              'input_root_sha256': manifest['input_root_sha256'], 'steps': [],
              'manifest_sha256_before_execution': hashlib.sha256(manifest_raw).hexdigest(),
              'p1_33_case_acceptance': 'BLOCKED', 'shared_runtime_modified': False}
    spring = owner = None
    steps = [('bootstrap', [python, root/'scripts/bootstrap_corpus.py', 'start'], 90),
             ('migrate', [python, root/'scripts/bootstrap_corpus.py', 'migrate'], 90),
             ('initialize-retrieval', [python, '-c', 'from allow_retrieval.database import Repository; Repository().initialize()'], 30),
             ('bootstrap-documents', [python, root/'scripts/bootstrap_documents.py'], 90),
             ('python-all', [python, root/'.gate/regression_tests.py', run/'python-tests.json'], 900),
             ('sql-runtime', [python, root/'scripts/verify_sql_runtime.py', '--status', root/'.runtime/corpus/sql-proxy/status.json', '--output', run/'sql-runtime.json'], 300),
             ('sql-clients-and-retrieval-recovery', [python, root/'scripts/verify_sql_clients.py'], 300),
             ('document-recovery', [python, root/'scripts/document_recovery_test.py'], 300)]
    try:
        for name, argv, timeout in steps:
            result = command(root, run, name, argv, timeout)
            report['steps'].append(result)
            if result['status'] != 'PASS':
                report['status'] = 'BLOCKED'
                raise RuntimeError('registered_step_failed:'+name)
        spring, owner, token = launch_spring(root, run, manifest, 'spring-first')
        wait_spring(manifest, spring, token)
        result = command(root, run, 'http-smoke', [python, root/'scripts/smoke_documents.py'], 300)
        report['steps'].append(result)
        if result['status'] != 'PASS':
            report['status'] = 'BLOCKED'
            raise RuntimeError('registered_http_smoke_failed')
        report['spring_crash'] = stop_spring(spring, owner, crash=True)
        spring = owner = None
        spring, owner, token = launch_spring(root, run, manifest, 'spring-restarted')
        wait_spring(manifest, spring, token)
        result = command(root, run, 'http-restart', [python, root/'scripts/verify_document_restart.py'], 180)
        report['steps'].append(result)
        report['status'] = result['status']
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        report['failure_step'] = str(error) if isinstance(error, RuntimeError) else 'private diagnostics retained'
    finally:
        support.write_private(run/'outcome-before-cleanup.json', report)
        if spring is not None and owner is not None:
            report['spring_cleanup'] = stop_spring(spring, owner)
        try:
            report['service_cleanup'] = support.cleanup(root)
            if any(x['emergency_escalation'] or not x['owned_identity_absent']
                   for x in report['service_cleanup']):
                report['status'] = 'BLOCKED'
        except BaseException as error:
            report['cleanup_failure_class'] = type(error).__name__
            report['status'] = 'INFRASTRUCTURE_FAILURE'
        report['source_mutation'] = [row['path'] for row in manifest['files']
                                     if support.digest(root/row['path']) != row['sha256']]
        if report['source_mutation']:
            report['status'] = 'BLOCKED'
        report['tooling_mutation'] = [row['path'] for row in manifest['tooling']
                                     if 'sha256' in row and support.digest(root/row['path']) != row['sha256']]
        observed = sorted(str(p.relative_to(root)) for p in (root/'.tools/retrieval-venv').rglob('*') if p.is_file())
        report['managed_runtime_inventory_unchanged'] = observed == manifest['managed_runtime_files']
        report['managed_runtime_links_unchanged'] = runtime_links(root) == manifest['managed_runtime_links']
        if (report['tooling_mutation'] or not report['managed_runtime_inventory_unchanged']
                or not report['managed_runtime_links_unchanged']):
            report['status'] = 'BLOCKED'
        report['manifest_unchanged_after_execution'] = (run/'manifest.json').read_bytes() == manifest_raw
        if not report['manifest_unchanged_after_execution']:
            report['status'] = 'BLOCKED'
        report['copied_artifacts'] = []
        for relative in ('gates/sql/client-coverage.json', 'gates/sql/recovery-report.json',
                         'gates/document/document-recovery-report.json', 'gates/document/http-smoke.json',
                         'gates/document/restart-report.json'):
            source = root/relative
            if source.exists():
                target = run/source.name
                shutil.copy2(source, target)
                target.chmod(0o600)
                report['copied_artifacts'].append({'path': target.name, 'sha256': support.digest(target)})
        report['boundary'] = 'Finite current regressions; default profile, no timing selection, no all33 closure or shared service promotion.'
        support.write_private(run/'report.json', report)
    print(json.dumps({'status': report['status'], 'steps': len(report['steps']), 'report': str(run/'report.json')}))


def main():
    """Expose separate immutable prepare and execute operations."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='operation', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--run-id', required=True)
    prepare_parser.add_argument('--target-ready', type=Path, required=True)
    prepare_parser.add_argument('--source-ready', type=Path, required=True)
    prepare_parser.add_argument('--registration', type=Path, required=True)
    prepare_parser.add_argument('--port', type=int, default=18183)
    prepare_parser.add_argument('--source-root', type=Path,
                                help='Explicit staged source root; never reuse an existing runtime.')
    execute_parser = commands.add_parser('execute')
    execute_parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'prepare' and args.source_root is not None:
        global ROOT
        ROOT = args.source_root.resolve(strict=True)
        if (ROOT/'.runtime').exists():
            raise ValueError('staged_source_runtime_not_allowed')
        support.ROOT = ROOT
    prepare(args) if args.operation == 'prepare' else execute(args)


if __name__ == '__main__':
    main()
