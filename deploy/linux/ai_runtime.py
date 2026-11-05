"""Provision the optional AI-only runtime from a pre-reviewed offline wheelhouse."""
import json
import os
from pathlib import Path
import subprocess


def provision(root, wheelhouse, runtime, env):
    """Create a fresh isolated runtime, hash-install locked wheels and attest it."""
    root, wheelhouse = Path(root), Path(wheelhouse)
    if not wheelhouse.is_absolute() or wheelhouse.resolve() != wheelhouse or not wheelhouse.is_dir():
        raise ValueError('AI wheelhouse must be an existing unlinked absolute directory')
    destination = root / '.tools/ai-venv'
    record = root / '.tools/ai-venv.inventory.json'
    if destination.exists() or destination.is_symlink() or record.exists() or record.is_symlink():
        raise ValueError('Existing AI runtime must not be overwritten')
    os.umask(0o077)
    subprocess.run(['/usr/bin/python3', '-m', 'venv', '--without-pip', str(destination)],
                   env=env, check=True, timeout=120)
    pip = root / '.tools/retrieval-venv/bin/python'
    command = [str(pip), '-I', '-B', '-m', 'pip', '--python', str(destination / 'bin/python'),
               'install', '--no-index', '--no-compile', '--only-binary=:all:', '--require-hashes',
               '--find-links', str(wheelhouse), '-r', str(root / 'retrieval/requirements-ai.lock')]
    subprocess.run(command, env=env, check=True, timeout=300)
    data = {'schema': 1, 'lock_sha256': runtime._hash(root / 'retrieval/requirements-ai.lock'),
            'files': runtime.inventory(destination)}
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(record, flags, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, sort_keys=True, separators=(',', ':'))
        stream.flush()
        os.fsync(stream.fileno())
    runtime.verify(root)
