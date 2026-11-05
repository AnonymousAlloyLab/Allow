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


def provision(root=ROOT):
    """Provision hashed third-party dependencies, without downloading model weights."""
    trust.load_source('retrieval/bootstrap_ml.py', root).provision_runtime()


def initialize(root=ROOT, config=None):
    """Initialize only an empty owned installation while holding the deployment lock."""
    trust.public_guard(config or {}, root)
    with trust.exclusive(root) as runtime:
        marker = trust.checked_path(runtime / 'deployment-initialized.json', private=True)
        if marker.exists():
            trust.initialized_marker(marker)
            print('Existing initialized workspace preserved; no migration or reprovision performed.')
            return
        trust.require_fresh(root)
        original = os.environ.copy()
        clean = trust.environment(root)
        os.environ.clear()
        os.environ.update(clean)
        initialization_error = None
        try:
            provision(root)
            trust.run('scripts/bootstrap_corpus.py', 'build', root=root)
            trust.run('scripts/bootstrap_corpus.py', 'start', root=root)
            trust.run('scripts/bootstrap_corpus.py', 'migrate', root=root)
            trust.run('scripts/bootstrap_documents.py', root=root, python=root / '.tools/retrieval-venv/bin/python')
            trust.private_write(marker, json.dumps({'schema': 1, 'empty_private_store_initialized': True}) + '\n')
        except BaseException as error:
            initialization_error = error
            raise
        finally:
            try:
                trust.run('scripts/bootstrap_corpus.py', 'stop', root=root, timeout=45)
            except Exception as cleanup_error:
                if initialization_error is None:
                    raise
                initialization_error.add_note('SQL cleanup also failed: ' + type(cleanup_error).__name__)
            finally:
                os.environ.clear()
                os.environ.update(original)


def main():
    """Verify inputs before accepting an explicit fresh-store initialization request."""
    os.umask(0o077)
    trust.verify_package(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--initialize', action='store_true')
    args = parser.parse_args()
    config = trust.load_config(args.config)
    trust.public_guard(config, ROOT)
    trust.prerequisites(ROOT)
    if args.initialize:
        initialize(config=config)
    else:
        print('Package verified. Pass --initialize to provision this private installation.')


if __name__ == '__main__':
    main()
