#!/usr/bin/python3
"""Isolated verified-source entry for the private Allow deployment."""
import sys
if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
    raise SystemExit('Invoke with /usr/bin/python3 -I -B; no local imports are permitted')

import hashlib
import json
import os
from pathlib import Path
import stat
import types

ROOT = Path(__file__).absolute().parents[2]


def _protected(path, install=False):
    """Validate trust-anchor owners/modes before loading any application helper."""
    for item in reversed((path, *path.parents)):
        info = item.lstat()
        sticky = item != path and info.st_uid == 0 and stat.S_ISDIR(info.st_mode) and info.st_mode & stat.S_ISVTX
        if stat.S_ISLNK(info.st_mode) or info.st_uid not in (0, os.geteuid()):
            raise ValueError('Untrusted bootstrap path')
        if info.st_mode & 0o022 and not sticky:
            raise ValueError('Writable bootstrap path')
    if install and path.stat().st_uid != os.geteuid():
        raise ValueError('Installation must be service-owned')
    if not install and not path.is_file():
        raise ValueError('Bootstrap input must be regular')
    return path


def _verified_bootstrap():
    """Load only hash-checked source; local modules and cached bytecode are unused."""
    _protected(ROOT, install=True)
    manifest = _protected(ROOT / 'MANIFEST.json').read_bytes()
    expected = _protected(ROOT / 'MANIFEST.sha256').read_text().split()[0]
    if hashlib.sha256(manifest).hexdigest() != expected:
        raise ValueError('Manifest checksum mismatch')
    entries = json.loads(manifest)['files']
    path = _protected(ROOT / 'deploy/linux/trust.py')
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != entries['deploy/linux/trust.py']:
        raise ValueError('Bootstrap source mismatch')
    module = types.ModuleType('allow_deployment_trust')
    module.__file__ = str(path)
    exec(compile(source, str(path), 'exec'), module.__dict__)
    return module


trust = _verified_bootstrap()

import argparse
import secrets
import signal
import subprocess


def command(config, root=ROOT):
    """Construct the closed loopback backend command with no arbitrary JVM options."""
    args = ['/usr/bin/java', '-cp', 'target/classes:target/dependency/*',
            'dev.allow.backend.AllowApplication', '--server.address=127.0.0.1',
            f'--server.port={config["backend_port"]}', f'--allow.corpus.root={root}',
            f'--allow.deployment.origin={config["public_origin"]}',
            f'--allow.deployment.tunnel-host=127.0.0.1:{config["tunnel_port"]}',
            f'--allow.document.advisory-profile={config["advisory_profile"]}',
            f'--allow.access-mode={config.get("access_mode", "PRIVATE")}',
            '--debug=false', '--trace=false', '--logging.level.root=WARN',
            '--logging.level.org.springframework=WARN']
    return args + public_transport_bounds(config)


def public_transport_bounds(config):
    """Bound public HTTP transport occupancy independently of workspace admission."""
    if config.get('access_mode', 'PRIVATE') != 'ANONYMOUS':
        return []
    return ['--server.tomcat.threads.max=16', '--server.tomcat.threads.min-spare=2',
            '--server.tomcat.max-connections=64', '--server.tomcat.accept-count=16',
            '--server.tomcat.connection-timeout=5s', '--server.tomcat.keep-alive-timeout=5s',
            '--server.tomcat.max-keep-alive-requests=20', '--server.max-http-request-header-size=16KB']


def reap(backend):
    """Terminate and reap the backend before allowing SQL teardown."""
    if backend is None or backend.poll() is not None:
        return
    backend.terminate()
    try:
        backend.wait(timeout=15)
    except subprocess.TimeoutExpired:
        backend.kill()
        backend.wait(timeout=5)


def serve(config, root=ROOT):
    """Reject competitors before effects; own the entire startup/cleanup interval."""
    trust.public_guard(config, root)
    with trust.exclusive(root) as runtime:
        trust.initialized_marker(runtime / 'deployment-initialized.json')
        trust.verify_generated(root)
        return supervise(config, root, runtime)


def supervise(config, root, runtime):
    """Own stack cleanup; publish a launch capability only in the private profile."""
    backend, stopping, link_owned = None, False, False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        if backend is not None and backend.poll() is None:
            backend.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    env = trust.environment(root)
    token = secrets.token_urlsafe(32)
    env['ALLOW_TOKEN'] = token
    try:
        trust.run('scripts/bootstrap_corpus.py', 'start', root=root, timeout=90)
        if stopping:
            return 0
        if config.get('access_mode', 'PRIVATE') == 'PRIVATE':
            trust.private_write(runtime / 'launch.url', config['public_origin'] + '/#token=' + token + '\n')
            link_owned = True
        backend = subprocess.Popen(command(config, root), cwd=root / 'backend', env=env)
        if stopping:
            backend.terminate()
        while True:
            try:
                return backend.wait(timeout=1)
            except subprocess.TimeoutExpired:
                if stopping:
                    reap(backend)
                    return backend.returncode
    finally:
        reap(backend)
        try:
            trust.run('scripts/bootstrap_corpus.py', 'stop', root=root, timeout=45)
        finally:
            if link_owned:
                trust.checked_path(runtime / 'launch.url', private=True).unlink(missing_ok=True)


def main():
    """Verify executable inputs and target configuration before entering ownership."""
    os.umask(0o077)
    trust.verify_package(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = trust.load_config(args.config)
    trust.public_guard(config, ROOT)
    trust.prerequisites(ROOT)
    return serve(config)


if __name__ == '__main__':
    sys.exit(main())
