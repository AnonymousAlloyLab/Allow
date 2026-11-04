#!/usr/bin/python3
"""Verify and explicitly provision a fresh private deployment; never imports corpus data."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    """Hash one regular package input."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def no_links(path):
    """Reject symlinks in every existing path component."""
    path = Path(os.path.abspath(path))
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError('Symlink paths are unsupported')
    return path


def verify_package(root=ROOT):
    """Check every frozen shipped file, manifest checksum, parser and helper pin."""
    root = no_links(root)
    manifest = no_links(root / 'MANIFEST.json')
    expected = no_links(root / 'MANIFEST.sha256').read_text().split()[0]
    if digest(manifest) != expected:
        raise ValueError('Manifest checksum mismatch')
    entries = json.loads(manifest.read_text())['files']
    for name, expected_hash in entries.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe manifest path')
        target = no_links(root / relative)
        if not target.is_file() or digest(target) != expected_hash:
            raise ValueError('Package integrity mismatch: ' + name)
    immutable = ('backend/target', 'retrieval/allow_retrieval', 'retrieval/allow_documents',
                 'scripts', 'config', '.tools/sqlean')
    for directory in immutable:
        for installed in (root / directory).rglob('*'):
            if installed.is_symlink():
                raise ValueError('Linked immutable input')
            if installed.is_file() and '__pycache__' not in installed.parts:
                if str(installed.relative_to(root)) not in entries:
                    raise ValueError('Unlisted executable/configuration input')
    parser = json.loads((root / 'config/sqlean-parser-lock.json').read_text())
    if digest(root / '.tools/sqlean/sqlean_pg_grammar') != parser['binary_sha256']:
        raise ValueError('Pinned parser mismatch')
    if digest(root / 'scripts/warm_worker_image.py') != '85f217246b6abeab699249f74e97abab586822678e7b573bbf5690588072dca0':
        raise ValueError('Pinned worker helper mismatch')
    return entries


def load_config(path):
    """Accept only the four closed public instance settings."""
    value = json.loads(no_links(path).read_text())
    if not isinstance(value, dict) or set(value) != {'public_origin', 'tunnel_port', 'backend_port', 'advisory_profile'}:
        raise ValueError('Unexpected instance settings')
    origin = value['public_origin']
    if not isinstance(origin, str):
        raise ValueError('HTTPS origin must be a string')
    match = re.fullmatch(r'https://([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)(?::([0-9]+))?', origin)
    if not match:
        raise ValueError('Exact HTTPS DNS origin required')
    labels = match[1].split('.')
    if len(labels) < 2 or len(match[1]) > 253 or all(label.isdigit() for label in labels) or any(
            not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels):
        raise ValueError('Invalid DNS origin')
    if match[2] and (not 1 <= int(match[2]) <= 65535 or str(int(match[2])) != match[2] or int(match[2]) == 443):
        raise ValueError('Invalid or noncanonical public port')
    for key in ('backend_port', 'tunnel_port'):
        if type(value[key]) is not int or not 1024 <= value[key] <= 65535:
            raise ValueError('Unprivileged port required')
    if value['advisory_profile'] not in ('DEFAULT', 'DOCUMENT_ADVISORY_TIER1'):
        raise ValueError('Unknown advisory profile')
    return value


def prerequisites(root=ROOT):
    """Enforce the supported short canonical Ubuntu x86_64 installation profile."""
    root = no_links(root)
    if os.geteuid() == 0:
        raise ValueError('Run as the dedicated unprivileged service account')
    if len(str(root).encode()) > 55 or re.search(r'[^/A-Za-z0-9_.-]', str(root)):
        raise ValueError('Use a short canonical installation path, such as /opt/allow')
    if platform.machine() != 'x86_64' or sys.version_info[:2] != (3, 12):
        raise ValueError('x86_64 CPython 3.12 required')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID', '').strip('"') != 'ubuntu' or release.get('VERSION_ID', '').strip('"') != '24.04':
        raise ValueError('Supported target is Ubuntu 24.04 x86_64')
    for name in ('/usr/bin/python3', '/usr/bin/bwrap', '/usr/bin/prlimit', '/usr/bin/java', 'make', 'gcc', 'bison', 'flex'):
        if not shutil.which(name):
            raise ValueError('Missing prerequisite: ' + name)
    version = subprocess.run(['/usr/bin/java', '-version'], capture_output=True, text=True, check=True)
    if not re.search(r'version "17[.\"]', version.stderr + version.stdout):
        raise ValueError('Java 17 required')
    probe = subprocess.run(['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--ro-bind', '/', '/', '/usr/bin/true'],
                           capture_output=True, timeout=15)
    if probe.returncode:
        raise ValueError('bubblewrap user namespaces unavailable; configure Ubuntu policy explicitly')
    return root


def environment(root=ROOT):
    """Use fixed executables without inherited Python/JVM or PostgreSQL overrides."""
    allowed = {'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR'}
    value = {key: val for key, val in os.environ.items() if key in allowed}
    value['PATH'] = '/usr/bin:/bin'
    value['PYTHONPATH'] = str(root / 'retrieval')
    return value


def run(script, *arguments, root=ROOT, python='/usr/bin/python3', timeout=1800):
    """Run a fixed installed helper with a clean environment."""
    return subprocess.run([str(python), str(root / script), *arguments], cwd=root,
                          env=environment(root), check=True, timeout=timeout)


def provision(root=ROOT):
    """Provision dependencies only; model download is deliberately separate."""
    spec = importlib.util.spec_from_file_location('allow_deploy_bootstrap_ml', root / 'retrieval/bootstrap_ml.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.provision_runtime()


def main():
    """Require explicit initialization; preserve any existing workspace on rerun."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--initialize', action='store_true', help='Explicitly create/migrate the private store')
    args = parser.parse_args()
    load_config(args.config)
    verify_package()
    prerequisites()
    if not args.initialize:
        print('Package verified. Pass --initialize to provision this private installation.')
        return
    runtime = ROOT / '.runtime'
    no_links(runtime)
    marker = runtime / 'deployment-initialized.json'
    if marker.exists():
        print('Existing initialized workspace preserved; no migration or reprovision performed.')
        return
    if runtime.exists() and any(runtime.iterdir()):
        raise ValueError('Unrecognized existing runtime; preserve it and investigate manually')
    runtime.mkdir(mode=0o700, exist_ok=True)
    runtime.chmod(0o700)
    original = os.environ.copy()
    clean = environment()
    os.environ.clear()
    os.environ.update(clean)
    initialization_error = None
    try:
        provision()
        run('scripts/bootstrap_corpus.py', 'build')
        run('scripts/bootstrap_corpus.py', 'start')
        run('scripts/bootstrap_corpus.py', 'migrate')
        run('scripts/bootstrap_documents.py', python=ROOT / '.tools/retrieval-venv/bin/python')
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as output:
            json.dump({'schema': 1, 'empty_private_store_initialized': True}, output)
    except BaseException as error:
        initialization_error = error
        raise
    finally:
        try:
            run('scripts/bootstrap_corpus.py', 'stop', timeout=45)
        except Exception as cleanup_error:
            if initialization_error is None:
                raise
            initialization_error.add_note('SQL cleanup also failed: ' + type(cleanup_error).__name__)
        finally:
            os.environ.clear()
            os.environ.update(original)


if __name__ == '__main__':
    main()
