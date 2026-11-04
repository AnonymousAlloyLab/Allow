#!/usr/bin/env python3
"""Prepare and supervise a fresh P1 cluster; never operate the active workspace runtime."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3] if HERE.name == 'runtime-experiments' else HERE.parent
COPY_DIRECTORIES = ('retrieval', 'scripts', 'config', 'db', 'spec')


def packed(value):
    """Serialize public metadata deterministically for identity binding."""
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(path):
    """Hash a regular input without exposing its contents."""
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def write_private(path, value):
    """Create a new private evidence file, refusing overwrites and symlinks."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(json.dumps(value, indent=2).encode() + b'\n')


def clean_environment(root):
    """Use copied modules and canonical routes without inherited authority or PostgreSQL options."""
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('PG', 'ALLOW_', 'PYTHON', 'LANGSMITH_'))}
    environment.update(PYTHONPATH=str(root/'retrieval'), PYTHONDONTWRITEBYTECODE='1',
                       ALLOW_CORPUS_RUNTIME=str(root/'.runtime/corpus'), LANGSMITH_TRACING='false')
    return environment


def process_identity(pid):
    """Read Linux incarnation and parent, treating zombies as exited."""
    try:
        raw = Path('/proc', str(pid), 'stat').read_text()
        parts = raw[raw.rfind(')') + 2:].split()
        if parts[0] == 'Z':
            return None
        return {'pid': pid, 'start': parts[19], 'parent': int(parts[1])}
    except FileNotFoundError:
        return None


def owned_pidfd(identity):
    """Acquire a pidfd only while the exact observed process incarnation remains present."""
    if process_identity(identity['pid']) != identity:
        raise RuntimeError('process_identity_changed_before_pidfd')
    descriptor = os.pidfd_open(identity['pid'])
    if process_identity(identity['pid']) != identity:
        os.close(descriptor)
        raise RuntimeError('process_identity_changed_after_pidfd')
    return descriptor


def signal_owned(identity, value):
    """Signal one validated owned incarnation, never a bare numeric PID."""
    descriptor = owned_pidfd(identity)
    try:
        signal.pidfd_send_signal(descriptor, value)
    finally:
        os.close(descriptor)


def copy_sources(destination):
    """Copy finite source/configuration files, excluding caches and all existing runtime state."""
    rows = []
    for directory in COPY_DIRECTORIES:
        for source in sorted((ROOT/directory).rglob('*')):
            if '__pycache__' in source.parts or source.suffix in ('.pyc', '.pyo') or not source.is_file():
                continue
            if source.is_symlink():
                raise RuntimeError('source_symlink_rejected')
            relative = source.relative_to(ROOT)
            target = destination/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if source.stat().st_ino == target.stat().st_ino or digest(source) != digest(target):
                raise RuntimeError('copy_identity_failure')
            rows.append({'path': str(relative), 'sha256': digest(source)})
    return rows


def tooling(destination):
    """Link only existing managed executable installations; never alias a data/runtime directory."""
    aliases = {'.tools/retrieval-venv': ROOT/'.tools/retrieval-venv'}
    rows = []
    for relative, source in aliases.items():
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source.resolve(), target_is_directory=True)
        rows.append({'path': relative, 'resolved': str(source.resolve()), 'purpose': 'read-only managed tooling'})
    prefix = Path('.tools/retrieval/postgres')
    shutil.copytree(ROOT/prefix, destination/prefix, symlinks=False)
    copied = [path for path in (destination/prefix).rglob('*') if path.is_file()]
    extra = ['.tools/sqlean/sqlean_pg_grammar', '.tools/retrieval-downloads/postgresql-16.15.tar.bz2',
             '.tools/retrieval-downloads/pgvector-0.8.7.tar.gz']
    for relative in extra:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, target)
        copied.append(target)
    for target in sorted(copied):
        rows.append({'path': str(target.relative_to(destination)), 'sha256': digest(target),
                     'mode': stat.S_IMODE(target.stat().st_mode), 'size': target.stat().st_size})
    dependencies = [destination/'.tools/retrieval-venv/pyvenv.cfg', destination/'.tools/retrieval-venv/bin/python']
    for site in (destination/'.tools/retrieval-venv/lib').glob('python*/site-packages'):
        for pattern in ('psycopg*', 'typing_extensions*'):
            for package in site.glob(pattern):
                dependencies.extend([package] if package.is_file() else
                                    [path for path in package.rglob('*') if path.is_file() and '__pycache__' not in path.parts])
    for target in sorted(set(dependencies)):
        rows.append({'path': str(target.relative_to(destination)), 'sha256': digest(target),
                     'resolved': str(target.resolve()), 'size': target.stat().st_size})
    return rows


def verify_source_ready(path):
    """Validate the author's exact ready-source hashes before copying any production inputs."""
    receipt = json.loads(path.read_text())
    if receipt.get('status') != 'SOURCE_READY':
        raise ValueError('source_ready_status_required')
    rows = receipt.get('files')
    if isinstance(rows, dict):
        rows = [{'path': name, 'sha256': value} for name, value in rows.items()]
    if not isinstance(rows, list) or not rows:
        raise ValueError('source_ready_hash_inventory_required')
    observed = {}
    for row in rows:
        name = row['path']
        if name in observed or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('source_ready_inventory_path')
        if not re.fullmatch('[0-9a-f]{64}', row['sha256']) or digest(ROOT/name) != row['sha256']:
            raise ValueError('source_ready_input_mismatch')
        observed[name] = row['sha256']
    required = {str(path.relative_to(ROOT)) for pattern in
                ('retrieval/allow_documents/*.py', 'retrieval/allow_retrieval/sql*.py') for path in ROOT.glob(pattern)}
    required.update(('scripts/bootstrap_corpus.py', 'config/sqlean-parser-lock.json'))
    if not required.issubset(observed):
        raise ValueError('source_ready_inventory_incomplete')
    return observed


def prepare(arguments):
    """Freeze an isolated copy only after the root author supplies a source-ready receipt."""
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', arguments.run_id):
        raise ValueError('invalid_run_id')
    receipt = arguments.source_ready.resolve()
    if not receipt.is_file():
        raise ValueError('source_ready_receipt_required')
    ready_inputs = verify_source_ready(receipt)
    run = HERE/'runs'/arguments.run_id
    run.mkdir(mode=0o700, parents=True, exist_ok=False)
    destination = Path(tempfile.mkdtemp(prefix='allow-cc-'))
    destination.chmod(0o700)
    files = copy_sources(destination)
    installed_tools = tooling(destination)
    gate = destination/'.gate'
    gate.mkdir(mode=0o700)
    for source in sorted(HERE.glob('*.py')):
        shutil.copyfile(source, gate/source.name)
        files.append({'path': '.gate/'+source.name, 'sha256': digest(source)})
    for name in ('registration.json', 'quota-registration.json'):
        shutil.copyfile(HERE/name, gate/name)
        files.append({'path': '.gate/'+name, 'sha256': digest(HERE/name)})
    if any(digest(ROOT/name) != value for name, value in ready_inputs.items()):
        raise ValueError('source_ready_inputs_changed_during_copy')
    root_hash = hashlib.sha256(packed({'files': files, 'tooling': installed_tools, 'suite': arguments.suite})).hexdigest()
    manifest = {'schema_version': '1.0', 'run_id': arguments.run_id, 'copied_root': str(destination),
                'suite': arguments.suite,
                'created_utc': datetime.now(timezone.utc).isoformat(), 'files': files,
                'input_root_sha256': root_hash, 'tooling': installed_tools,
                'source_ready_receipt': str(receipt), 'source_ready_sha256': digest(receipt),
                'activation_sha256': digest(HERE.parent/'formal-activation.json'),
                'runtime_plan_sha256': digest(HERE.parent/'runtime-test-plan.json')}
    write_private(run/'manifest.json', manifest)
    write_private(destination/'.gate/manifest.json', manifest)
    print(json.dumps({'run_directory': str(run), 'copied_root': str(destination), 'input_root': root_hash}))


def check_installation(manifest):
    """Reject root aliasing, unsafe permissions, changed copy inputs or an existing live runtime."""
    root = Path(manifest['copied_root'])
    if root == ROOT or not root.name.startswith('allow-cc-') or root.parent != Path('/tmp'):
        raise ValueError('isolated_root_required')
    metadata = root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ValueError('isolated_root_permissions')
    identity = {'files': manifest['files'], 'tooling': manifest['tooling'], 'suite': manifest['suite']}
    if manifest.get('runtime_binding_version') == 1:
        identity.update({key: manifest[key] for key in
                         ('runtime_binding_version', 'managed_runtime_files', 'managed_runtime_links')})
    if hashlib.sha256(packed(identity)).hexdigest() != manifest['input_root_sha256']:
        raise ValueError('manifest_root_mismatch')
    if any(digest(root/row['path']) != row['sha256'] for row in manifest['files']):
        raise ValueError('copied_input_mutation')
    for row in manifest['tooling']:
        path = root/row['path']
        if 'sha256' in row and digest(path) != row['sha256']:
            raise ValueError('tooling_input_mutation')
        if 'resolved' in row and str(path.resolve()) != row['resolved']:
            raise ValueError('tooling_alias_changed')
        if 'mode' in row and stat.S_IMODE(path.stat().st_mode) != row['mode']:
            raise ValueError('tooling_mode_changed')
    if (root/'.runtime').exists():
        raise ValueError('fresh_runtime_required')
    return root


def private_command(command, root, output, timeout):
    """Run an owned bounded subprocess, retaining private diagnostics and public code only."""
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as log:
        child = subprocess.Popen(command, cwd=root, env=clean_environment(root), stdout=log, stderr=subprocess.STDOUT)
        try:
            returncode = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            write_private(output.with_suffix('.timeout.json'), {'status': 'TIMEOUT_BEFORE_EMERGENCY_CLEANUP'})
            owner = process_identity(child.pid)
            if owner is not None:
                signal_owned(owner, signal.SIGKILL)
            child.wait(timeout=3)
            raise
    if returncode:
        raise RuntimeError('owned_command_failed_' + str(returncode))
    return {'exit_code': returncode, 'log_sha256': digest(output)}


def owned_services(root):
    """Read only this fresh installation's process ownership files and validate exact arguments."""
    result = []
    owner = root/'.runtime/corpus/sql-proxy/owner.json'
    if owner.exists():
        value = json.loads(owner.read_text())
        current = process_identity(value['pid'])
        if current and current['start'] == value['identity']['start_ticks']:
            result.append(('proxy', current))
    pidfile = root/'.runtime/corpus/postgres/data/postmaster.pid'
    if pidfile.exists():
        pid = int(pidfile.read_text().splitlines()[0])
        current = process_identity(pid)
        argv = Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0') if current else []
        if current and str(root/'.runtime/corpus/postgres/data').encode() in argv:
            result.append(('postgres', current))
    return result


def cleanup(root):
    """Terminate only this installation's owned services; report emergency escalation separately."""
    records = []
    for label, identity in owned_services(root):
        signal_owned(identity, signal.SIGTERM)
        deadline = time.monotonic()+15
        while process_identity(identity['pid']) == identity and time.monotonic() < deadline:
            time.sleep(.05)
        emergency = process_identity(identity['pid']) == identity
        if emergency:
            signal_owned(identity, signal.SIGKILL)
            deadline = time.monotonic()+5
            while process_identity(identity['pid']) == identity and time.monotonic() < deadline:
                time.sleep(.05)
        records.append({'service': label, 'emergency_escalation': emergency,
                        'owned_identity_absent': process_identity(identity['pid']) != identity})
    return records


def execute(arguments):
    """Bootstrap and test only the frozen copied installation, then preserve every outcome."""
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('managed_python_with_pidfd_required_before_any_launch')
    run = arguments.run.resolve()
    if run.parent != HERE/'runs':
        raise ValueError('registered_run_required')
    manifest = json.loads((run/'manifest.json').read_text())
    root = check_installation(manifest)
    result = {'schema_version': '1.0', 'run_id': manifest['run_id'],
              'input_root_sha256': manifest['input_root_sha256'], 'status': 'INFRASTRUCTURE_FAILURE',
              'cases': [], 'execution_started_utc': datetime.now(timezone.utc).isoformat(),
              'whole_stack_containment': 'NOT_ASSESSED', 'target_hardware_acceptance': 'NOT_ASSESSED'}
    python = root/'.tools/retrieval-venv/bin/python'
    try:
        result['bootstrap'] = private_command([str(python), str(root/'scripts/bootstrap_corpus.py'), 'start'], root, run/'bootstrap-private.log', 90)
        suite = manifest.get('suite', 'smoke')
        driver = 'quota_probe.py' if suite == 'quota' else 'probe_runtime.py'
        result['probe'] = private_command([str(python), str(root/'.gate'/driver), '--root', str(root), '--output', str(run/'probe-report.json')], root, run/'probe-private.log', 1200 if suite == 'quota' else 180)
        probe = json.loads((run/'probe-report.json').read_text())
        result['cases'] = probe['cases']
        result['finite_subcases_passed'] = probe.get('finite_subcases_passed', False)
        result['status'] = probe['status']
    except BaseException as error:
        result['failure_class'] = type(error).__name__
        result['status'] = 'INFRASTRUCTURE_FAILURE'
        if (run/'probe-report.json').exists():
            result['cases'] = json.loads((run/'probe-report.json').read_text()).get('cases', [])
    finally:
        write_private(run/'outcome-before-cleanup.json', result)
        try:
            result['harness_cleanup'] = cleanup(root)
        except BaseException as error:
            result['cleanup_failure_class'] = type(error).__name__
        result['boundary'] = 'Only individually registered executed subcases; not the full33-case gate or production performance acceptance.'
        write_private(run/'report.json', result)
    print(json.dumps({'report': str(run/'report.json'), 'status': result['status'], 'case_count': len(result['cases'])}))


def main():
    """Expose prepare/execute operations with explicit immutable run directories."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='operation', required=True)
    first = commands.add_parser('prepare')
    first.add_argument('--run-id', required=True)
    first.add_argument('--source-ready', required=True, type=Path)
    first.add_argument('--suite', choices=('smoke', 'quota'), default='smoke')
    second = commands.add_parser('execute')
    second.add_argument('--run', required=True, type=Path)
    arguments = parser.parse_args()
    prepare(arguments) if arguments.operation == 'prepare' else execute(arguments)


if __name__ == '__main__':
    main()
