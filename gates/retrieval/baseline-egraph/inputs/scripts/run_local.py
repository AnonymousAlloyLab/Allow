#!/usr/bin/env python3
"""Launch the local workbench with a fresh private capability, never a shared server."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def private_write(path, value):
    """Replace a mode-0600 launcher file without following a planted symlink."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags, 0o600), 'w') as stream:
        stream.write(value)
    path.chmod(0o600)

def main():
    """Validate local prerequisites and supervise the Spring process until interruption."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--show-url', action='store_true', help='Display the local bearer launch link intentionally')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit('Choose an unprivileged port between 1024 and 65535')
    if not shutil.which('bwrap') or not shutil.which('prlimit'):
        raise SystemExit('Linux bubblewrap and prlimit are required; no unsandboxed fallback')
    target = ROOT / 'backend/target'
    required = ['classes/static/index.html', 'solver/alloy.jar', 'dependency']
    if any(not (target / path).exists() for path in required):
        raise SystemExit('Run python3 scripts/build.py first')
    runtime = ROOT / '.runtime'
    runtime.mkdir(mode=0o700, exist_ok=True)
    runtime.chmod(0o700)
    token = secrets.token_urlsafe(32)
    url = f'http://127.0.0.1:{args.port}/#token={token}'
    private_write(runtime / 'launch.url', url + '\n')
    environment = os.environ.copy()
    environment['ALLOW_TOKEN'] = token
    command = ['java', '-cp', 'target/classes:target/dependency/*',
               'dev.allow.backend.AllowApplication', f'--server.port={args.port}', '--server.address=127.0.0.1',
               '--debug=false', '--trace=false', '--logging.level.root=WARN',
               '--logging.level.org.springframework=WARN']
    print(url if args.show_url else 'Private launch link written to .runtime/launch.url', flush=True)
    process = subprocess.Popen(command, cwd=ROOT / 'backend', env=environment)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        return process.wait(timeout=15)

if __name__ == '__main__':
    sys.exit(main())
