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


def main():
    """Verify the replacement package and observe prerequisites without side effects."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    trust.verify_package(ROOT)
    config = trust.load_config(args.config)
    if config['installation_slot'] != 'PUBLIC_REPLACEMENT':
        raise ValueError('This check requires PUBLIC_REPLACEMENT')
    trust.public_guard(config, ROOT)
    print('Public replacement prerequisites observed; native acceptance remains open.')


if __name__ == '__main__':
    main()
