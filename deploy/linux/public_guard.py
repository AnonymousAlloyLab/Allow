"""Read-only prerequisite observations for the closed public replacement slot."""
import os
from pathlib import Path
import pwd
import selectors
import stat
import subprocess
import time

PUBLIC_ROOT = Path('/opt/allow-public')
LEGACY_ROOT = Path('/opt/allow')
CGROUP_ROOT = Path('/sys/fs/cgroup')
MOUNTINFO = Path('/proc/self/mountinfo')
PROPERTIES = ('LoadState', 'ActiveState', 'SubState', 'MainPID', 'UnitFileState', 'Job', 'ControlGroup')


def systemd_state():
    """Read fixed legacy properties with bounded time and bounded pipe consumption."""
    command = ['/usr/bin/systemctl', 'show', 'allow.service', '--no-pager',
               *('--property=' + key for key in PROPERTIES)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'})
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 5
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('Legacy unit metadata timed out')
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, min(4096, 16385 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(chunk)
                        if len(output) > 16384:
                            raise ValueError('Legacy unit metadata too large')
            if process.wait(timeout=max(0.01, deadline - time.monotonic())):
                raise ValueError('Legacy unit metadata unavailable')
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        process.stdout.close()
    values = {}
    for line in output.decode('utf-8', errors='strict').splitlines():
        key, separator, value = line.partition('=')
        if not separator or key not in PROPERTIES or key in values:
            raise ValueError('Ambiguous legacy unit metadata')
        values[key] = value
    if set(values) != set(PROPERTIES):
        raise ValueError('Incomplete legacy unit metadata')
    return values


def unified_cgroup_available():
    """Require a readable, canonical cgroup2 mount before treating a group as absent."""
    info = CGROUP_ROOT.lstat()
    if not stat.S_ISDIR(info.st_mode) or CGROUP_ROOT.resolve(strict=True) != CGROUP_ROOT:
        raise ValueError('Unified cgroup root unavailable')
    with MOUNTINFO.open('rb') as stream:
        raw = stream.read(1048577)
    if len(raw) > 1048576:
        raise ValueError('Mount metadata exceeds bound')
    matches = []
    for line in raw.decode('utf-8', errors='strict').splitlines():
        fields = line.split()
        if len(fields) < 10 or '-' not in fields:
            raise ValueError('Invalid mount metadata')
        separator = fields.index('-')
        if separator < 6 or len(fields) < separator + 4:
            raise ValueError('Incomplete mount metadata')
        if fields[4] == str(CGROUP_ROOT):
            matches.append(fields[separator + 1])
    if matches != ['cgroup2']:
        raise ValueError('Expected unified cgroup mount unavailable or ambiguous')
    controllers = CGROUP_ROOT / 'cgroup.controllers'
    if controllers.is_symlink():
        raise ValueError('Linked unified cgroup metadata')
    with controllers.open('rb') as stream:
        if len(stream.read(4097)) > 4096:
            raise ValueError('Unified cgroup metadata exceeds bound')


def empty_cgroup(value):
    """Observe an absent or empty reported unified cgroup without following links."""
    unified_cgroup_available()
    if value == '':
        return
    relative = Path(value)
    if not value.startswith('/') or value == '/' or '..' in relative.parts or str(relative) != value:
        raise ValueError('Invalid legacy cgroup')
    directory = CGROUP_ROOT / value[1:]
    for component in (directory, *directory.parents):
        if component == CGROUP_ROOT.parent:
            break
        if component.is_symlink():
            raise ValueError('Linked legacy cgroup')
    if not directory.exists():
        return
    if not directory.is_dir():
        raise ValueError('Invalid legacy cgroup directory')
    pending = [directory]
    count = 0
    members = 0
    deadline = time.monotonic() + 5
    while pending:
        current = pending.pop()
        count += 1
        if count > 1024 or time.monotonic() >= deadline:
            raise ValueError('Legacy cgroup inventory exceeds bound')
        procs = current / 'cgroup.procs'
        if procs.is_symlink():
            raise ValueError('Linked legacy process inventory')
        with procs.open('rb') as stream:
            if stream.read(4096).strip():
                raise ValueError('Legacy cgroup still contains processes')
        for child in current.iterdir():
            members += 1
            if members > 16384 or time.monotonic() >= deadline:
                raise ValueError('Legacy cgroup inventory exceeds bound')
            if child.is_symlink():
                raise ValueError('Linked legacy cgroup member')
            if child.is_dir():
                pending.append(child)


def reserved_public_uid():
    """Reserve the numeric public identity even when NSS gives it another name."""
    try:
        public_uid = pwd.getpwnam('allow-public').pw_uid
    except KeyError:
        return False
    return os.geteuid() == public_uid


def check(config, root):
    """Reject unsafe replacement prerequisites without creating runtime state."""
    if config.get('installation_slot', 'PRIMARY') == 'PRIMARY':
        if Path(root) == PUBLIC_ROOT or reserved_public_uid():
            raise ValueError('Reserved public root/account requires PUBLIC_REPLACEMENT')
        return
    if (config.get('installation_slot') != 'PUBLIC_REPLACEMENT' or
            config.get('access_mode') != 'ANONYMOUS' or config.get('transport') != 'wsl' or
            config.get('backend_port') != 18081 or config.get('tunnel_port') != 18081 or
            Path(root) != PUBLIC_ROOT):
        raise ValueError('Invalid public replacement tuple')
    public = pwd.getpwnam('allow-public')
    legacy = pwd.getpwnam('allow')
    if public.pw_uid == 0 or legacy.pw_uid == 0 or public.pw_uid == legacy.pw_uid or os.geteuid() != public.pw_uid:
        raise ValueError('Distinct dedicated public and legacy accounts required')
    for path, uid in ((PUBLIC_ROOT, public.pw_uid), (LEGACY_ROOT, legacy.pw_uid)):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or path.resolve(strict=True) != path or info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('Protected canonical installation directory required')
    # Separate tests matter: a combined mask would miss a grant of only one right.
    if any(os.access(LEGACY_ROOT, mode, effective_ids=True) for mode in (os.R_OK, os.W_OK, os.X_OK)):
        raise ValueError('Public account can access legacy installation')
    values = systemd_state()
    expected = {'LoadState': 'loaded', 'ActiveState': 'inactive', 'SubState': 'dead',
                'MainPID': '0', 'UnitFileState': 'disabled'}
    if any(values[key] != value for key, value in expected.items()) or values['Job'] not in ('', '0'):
        raise ValueError('Legacy unit must already be disabled and quiescent')
    empty_cgroup(values['ControlGroup'])
