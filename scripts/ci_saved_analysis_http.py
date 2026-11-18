#!/usr/bin/env python3
"""Run old-release/current-build HTTP analysis against an isolated real SQL store.

Requires a completed backend build, Linux namespaces/bubblewrap, Debian OpenJDK
17, and Python 3.10+. Without --postgres-prefix/--python, also requires a C build
toolchain, make, Python venv, and network access for pinned dependencies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'dist/allow-iis-wsl-anonymous-20261104-r5.zip'
RELEASE_SHA256 = 'ad6ffe042a677775d52962211ff8685fbf2ea834fd7ff7a36e3e600c153c0c78'


def run(command, root, **kwargs):
    """Run one bounded provisioning or acceptance step in the disposable tree."""
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('ALLOW_', 'PG', 'PYTHONPATH', 'PYTHONOPTIMIZE'))}
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    subprocess.run([str(value) for value in command], cwd=root, check=True,
                   timeout=1800, env=environment, **kwargs)


def provision(root, args):
    """Copy inputs, authenticate the old release, and provision private dependencies."""
    for name in ('retrieval', 'config', 'db', 'scripts'):
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('classes', 'dependency', 'solver'):
        target = Path('backend/target') / name
        shutil.copytree(ROOT / target, root / target)
    release = ROOT / RELEASE
    if hashlib.sha256(release.read_bytes()).hexdigest() != RELEASE_SHA256:
        raise RuntimeError('Historical release digest mismatch')
    with zipfile.ZipFile(release) as archive:
        for entry in archive.infolist():
            if entry.filename.startswith('backend/target/'):
                destination = root / 'old' / entry.filename
            elif entry.filename.startswith('.tools/sqlean/'):
                destination = root / entry.filename
            else:
                continue
            if not destination.resolve().is_relative_to(root.resolve()):
                raise RuntimeError('Unsafe release path')
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(entry))
    binary = root / '.tools/sqlean/sqlean_pg_grammar'
    lock = json.loads((root / 'config/sqlean-parser-lock.json').read_text())
    if hashlib.sha256(binary.read_bytes()).hexdigest() != lock['binary_sha256']:
        raise RuntimeError('Packaged parser digest mismatch')
    binary.chmod(0o755)
    environment = root / '.tools/retrieval-venv'
    if args.python:
        # Keep the complete external environment read-only; do not rewrite it.
        environment.symlink_to(args.python.absolute().parent.parent, target_is_directory=True)
    else:
        run(['/usr/bin/python3', '-m', 'venv', environment], root)
        run([environment / 'bin/python', '-m', 'pip', 'install', 'psycopg[binary]==3.2.3', 'typing-extensions==4.16.0'], root)
    if args.postgres_prefix:
        shutil.copytree(args.postgres_prefix, root / '.tools/retrieval/postgres')
    run([environment / 'bin/python', '-I', '-c',
         'import fcntl,os; assert hasattr(os, "pidfd_open"); '
         'assert hasattr(fcntl, "F_SEAL_SEAL")'], root)
    return environment / 'bin/python'


def stop(process):
    """Reap the backend before switching builds or removing its private tree."""
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        raise RuntimeError('Backend did not terminate cleanly')


def startup_failure(name, log, reason):
    """Report startup exception types while keeping private arguments and log text out of CI."""
    with log.open('rb') as stream:
        stream.seek(max(0, log.stat().st_size - 32768))
        errors = re.findall(rb'\b([\w.]+(?:Exception|Error)):', stream.read())
    classes = ', '.join(dict.fromkeys(error.decode('ascii') for error in errors[-5:]))
    return RuntimeError(f'{name} backend {reason}' + (f' ({classes})' if classes else ''))


def phase(root, backend, name, port, token):
    """Start one immutable build and execute the actual HTTP regression phase."""
    base = 'http://127.0.0.1:' + str(port)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('ALLOW_', 'SPRING_', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS'))}
    environment['ALLOW_TOKEN'] = token
    command = ['java', '-cp', 'target/classes:target/dependency/*',
               'dev.allow.backend.AllowApplication', '--allow.corpus.root=' + str(root),
               '--server.address=127.0.0.1', '--server.port=' + str(port),
               '--allow.access-mode=PRIVATE', '--allow.document.advisory-profile=DEFAULT']
    log = root / (name + '.log')
    with log.open('wb') as output:
        process = subprocess.Popen(command, cwd=backend, env=environment, stdout=output, stderr=output)
        try:
            deadline = time.monotonic() + 60
            request = urllib.request.Request(base + '/api/config', headers={'Authorization': 'Bearer ' + token})
            while True:
                if process.poll() is not None:
                    raise startup_failure(name, log, 'exited with status ' + str(process.returncode))
                try:
                    with urllib.request.urlopen(request, timeout=2) as response:
                        if response.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    pass
                if time.monotonic() > deadline:
                    raise startup_failure(name, log, 'readiness timed out')
                time.sleep(.2)
            run([sys.executable, root / 'scripts/test_saved_analysis_upgrade.py', name,
                 '--base', base, '--token-file', root / 'token', '--fixture', root / 'fixture.json'], root)
        finally:
            stop(process)


def main():
    """Own all disposable state and require both real-build HTTP phases to pass."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres-prefix', type=Path, help='Read-only prebuilt pinned PostgreSQL/pgvector prefix')
    parser.add_argument('--python', type=Path, help='Read-only managed venv bin/python with psycopg 3.2.3/libpq 170000')
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Run as a non-root user; PostgreSQL refuses root')
    with tempfile.TemporaryDirectory(prefix='allow-http-', dir='/tmp') as directory:
        root = Path(directory)
        python = provision(root, args)
        token = secrets.token_urlsafe(32)
        (root / 'token').write_text(token)
        (root / 'token').chmod(0o600)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        bootstrap = root / 'scripts/bootstrap_corpus.py'
        try:
            print('Starting disposable PostgreSQL and locked SQLean proxy', flush=True)
            run([sys.executable, bootstrap, 'start'], root)
            run([sys.executable, bootstrap, 'migrate'], root)
            run([python, root / 'scripts/bootstrap_documents.py'], root)
            phase(root, root / 'old/backend', 'seed', port, token)
            phase(root, root / 'backend', 'check', port, token)
            print('PASS: historical release/current build HTTP saved-analysis lifecycle', flush=True)
        finally:
            run([sys.executable, bootstrap, 'stop'], root)


if __name__ == '__main__':
    main()
