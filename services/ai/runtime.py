"""Attest the isolated AI Python runtime before starting its interpreter."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


def _hash(path):
    """Stream a regular installed file into an exact digest."""
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def _secure(path):
    """Reject nonowned or group/other writable runtime entries."""
    info = path.lstat()
    if info.st_uid != os.geteuid() or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022):
        raise ValueError('unsafe_ai_runtime')
    return info


def _link(path, runtime):
    """Allow only venv interpreter links and the standard lib64 alias."""
    name = str(path.relative_to(runtime))
    target = path.resolve(strict=True)
    interpreter = name in ('bin/python', 'bin/python3', 'bin/python3.12') and target == Path('/usr/bin/python3').resolve()
    alias = name == 'lib64' and target == runtime / 'lib'
    if not (interpreter or alias):
        raise ValueError('linked_ai_runtime')
    return 'link:' + os.readlink(path)


def inventory(runtime):
    """Enumerate every regular file and approved link; disallow startup hooks."""
    runtime = Path(runtime)
    _secure(runtime)
    if not runtime.is_dir() or runtime.is_symlink():
        raise ValueError('missing_ai_runtime')
    files = {}
    for directory, directories, names in os.walk(runtime, followlinks=False):
        for name in sorted(directories + names):
            path = Path(directory) / name
            info = _secure(path)
            relative = str(path.relative_to(runtime))
            if stat.S_ISLNK(info.st_mode):
                files[relative] = _link(path, runtime)
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise ValueError('linked_ai_file')
                if path.suffix in ('.pth', '.pyc', '.pyo') or path.name in ('sitecustomize.py', 'usercustomize.py'):
                    raise ValueError('ai_startup_hook')
                files[relative] = _hash(path)
            elif not stat.S_ISDIR(info.st_mode):
                raise ValueError('ai_runtime_type')
    return files


def verify(root):
    """Verify lock identity and exact private runtime inventory before Python exec."""
    root = Path(root)
    if sys.version_info[:2] != (3, 12):
        raise ValueError('ai_python_version')
    _secure(root / '.tools')
    if (root / '.tools').is_symlink() or not (root / '.tools').is_dir():
        raise ValueError('unsafe_ai_tools')
    runtime = root / '.tools/ai-venv'
    record = root / '.tools/ai-venv.inventory.json'
    info = _secure(record)
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
        raise ValueError('unsafe_ai_inventory')
    if info.st_size > 16777216:
        raise ValueError('oversized_ai_inventory')
    data = json.loads(record.read_text())
    if set(data) != {'schema', 'lock_sha256', 'files'} or data['schema'] != 1:
        raise ValueError('invalid_ai_inventory')
    if data['lock_sha256'] != _hash(root / 'retrieval/requirements-ai.lock'):
        raise ValueError('ai_lock_changed')
    if 'include-system-site-packages = false' not in (runtime / 'pyvenv.cfg').read_text():
        raise ValueError('ai_system_site_enabled')
    if inventory(runtime) != data['files']:
        raise ValueError('ai_runtime_changed')
    site = runtime / 'lib/python3.12/site-packages'
    if not site.is_dir() or site.is_symlink():
        raise ValueError('missing_ai_site')
    return site
