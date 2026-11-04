#!/usr/bin/python3
"""Supervise the existing backend and private SQL stack within one service cgroup."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup as deployment_setup

ROOT = Path(__file__).resolve().parents[2]


def private_write(path, text):
    """Replace a private capability file without following a symlink."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(text)


def command(config, root=ROOT):
    """Construct a closed backend command; no operator-supplied JVM arguments."""
    return ['/usr/bin/java', '-cp', 'target/classes:target/dependency/*',
            'dev.allow.backend.AllowApplication', '--server.address=127.0.0.1',
            f'--server.port={config["backend_port"]}', f'--allow.corpus.root={root}',
            f'--allow.deployment.origin={config["public_origin"]}',
            f'--allow.deployment.tunnel-host=127.0.0.1:{config["tunnel_port"]}',
            f'--allow.document.advisory-profile={config["advisory_profile"]}',
            '--debug=false', '--trace=false',
            '--logging.level.root=WARN', '--logging.level.org.springframework=WARN']


def main():
    """Start SQL before backend, rotate bearer each launch, then reap in reverse order."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = deployment_setup.load_config(args.config)
    deployment_setup.verify_package()
    deployment_setup.prerequisites()
    runtime = deployment_setup.no_links(ROOT / '.runtime')
    marker = deployment_setup.no_links(runtime / 'deployment-initialized.json')
    if not marker.is_file() or not json.loads(marker.read_text()).get('empty_private_store_initialized'):
        raise ValueError('Run setup.py --initialize first')
    runtime.chmod(0o700)
    stopping = False
    backend = None

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        if backend is not None and backend.poll() is None:
            backend.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    env = deployment_setup.environment()
    token = secrets.token_urlsafe(32)
    env['ALLOW_TOKEN'] = token
    try:
        deployment_setup.run('scripts/bootstrap_corpus.py', 'start', timeout=90)
        if stopping:
            return 0
        private_write(runtime / 'launch.url', config['public_origin'] + '/#token=' + token + '\n')
        backend = subprocess.Popen(command(config), cwd=ROOT / 'backend', env=env)
        if stopping:
            backend.terminate()
        while True:
            try:
                return backend.wait(timeout=1)
            except subprocess.TimeoutExpired:
                if stopping:
                    try:
                        return backend.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        backend.kill()
                        return backend.wait(timeout=5)
    finally:
        if backend is not None and backend.poll() is None:
            backend.terminate()
            try:
                backend.wait(timeout=15)
            except subprocess.TimeoutExpired:
                backend.kill()
                backend.wait(timeout=5)
        deployment_setup.run('scripts/bootstrap_corpus.py', 'stop', timeout=45)
        link = runtime / 'launch.url'
        if link.exists() and not link.is_symlink():
            link.unlink()


if __name__ == '__main__':
    sys.exit(main())
