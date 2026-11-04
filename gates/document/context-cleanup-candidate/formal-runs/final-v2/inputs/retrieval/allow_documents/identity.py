"""Owner-private durable principal/workspace/launch identity and process fences."""
import json
import os
from pathlib import Path
import stat
import uuid
from allow_retrieval.common import ROOT

DIRECTORY = ROOT / '.runtime/documents'


def private(path, directory=False):
    """Reject symlinks, foreign owners and nonprivate filesystem permissions."""
    item = path.lstat()
    expected = 0o700 if directory else 0o600
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(item.st_mode) or item.st_uid != os.getuid() or stat.S_IMODE(item.st_mode) != expected:
        raise ValueError('identity_not_private')


def load(directory=DIRECTORY):
    """Load established durable identity; runtime never silently reprovisions it."""
    for component in (directory, *directory.parents):
        if component.is_symlink():
            raise ValueError('identity_symlink_component')
    private(directory, True)
    target = directory / 'identity.json'
    private(target)
    handle = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(handle, 'rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('identity_limit')
    value = json.loads(raw)
    if set(value) != {'version', 'principalId', 'workspaceId', 'logicalLaunchId'} or value['version'] != 1:
        raise ValueError('identity_corrupt')
    for key in ('principalId', 'workspaceId', 'logicalLaunchId'):
        if str(uuid.UUID(value[key])) != value[key]:
            raise ValueError('identity_corrupt')
    return value


def provision(directory=DIRECTORY):
    """Create private metadata exclusively; bootstrap first checks nonempty storage."""
    directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.mkdir(mode=0o700, exist_ok=True)
    private(directory, True)
    if (directory / 'identity.json').exists():
        return load(directory)
    value = {'version': 1, 'principalId': str(uuid.uuid4()), 'workspaceId': str(uuid.uuid4()),
             'logicalLaunchId': str(uuid.uuid4())}
    target = directory / 'identity.json'
    handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(handle, 'wb') as stream:
        stream.write(json.dumps(value).encode()); stream.flush(); os.fsync(stream.fileno())
    parent = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return value


def process_start(pid):
    """Return Linux process start ticks without confusing spaces in comm fields."""
    if type(pid) is not int or pid < 1:
        raise ValueError('invalid_process')
    try:
        raw = Path('/proc').joinpath(str(pid), 'stat').read_text()
        parts = raw[raw.rfind(')') + 2:].split()
        if parts[0] == 'Z':
            return None
        return parts[19]
    except FileNotFoundError:
        return None


def alive(pid, start):
    """PID reuse never establishes ownership of an old admission generation."""
    return process_start(pid) == start
