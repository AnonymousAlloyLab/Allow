#!/usr/bin/env python3
"""Private evidence and exact Linux identities for the new one-use warm gate."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3] if HERE.name == 'runtime-experiments' else HERE.parent


def packed(value):
    """Return canonical finite JSON bytes used by all manifest roots."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(path):
    """Hash file bytes without displaying their potentially private contents."""
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def write_private(path, value):
    """Create immutable owner-private evidence without overwriting or following a link."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False).encode() + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def read_private(path):
    """Read only an owned private regular JSON document through a nonfollowing descriptor."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('private_regular_file_required')
        return json.load(stream)


def relative_name(name):
    """Reject absolute, traversal and runtime-bearing copy inventory names."""
    value = Path(name)
    if value.is_absolute() or not value.parts or any(p in ('..', '.runtime') for p in value.parts):
        raise ValueError('unsafe_input_inventory_path')
    return value


def regular(path):
    """Require a nonaliased regular source and reject symlink path components."""
    path = Path(path)
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError('mutable_input_symlink')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('nonregular_or_hardlinked_input')
    return info


def record(path, base=None):
    """Bind bytes, mode and length; callers explicitly classify aliases separately."""
    path = Path(path)
    info = path.stat()
    return {'path': str(path.relative_to(base) if base else path), 'sha256': digest(path),
            'size': info.st_size, 'mode': stat.S_IMODE(info.st_mode)}


def process_identity(pid):
    """Identify a Linux incarnation with start ticks; treat zombies as absent."""
    try:
        raw = Path('/proc', str(pid), 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        return None if fields[0] == 'Z' else {'pid': int(pid), 'start_ticks': fields[19]}
    except (FileNotFoundError, ProcessLookupError):
        return None


def same_process(identity):
    """Never infer continuing ownership from numeric PID equality alone."""
    return identity is not None and process_identity(identity['pid']) == identity


def security(pid):
    """Read the existing context without selecting or modifying security policy."""
    root = Path('/proc')/str(pid)
    fields = dict(line.split(':', 1) for line in (root/'status').read_text().splitlines())
    names = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb', 'NoNewPrivs', 'Seccomp')
    return {'profile': (root/'attr/current').read_text().strip(),
            'fields': {name: fields[name].strip() for name in names},
            'namespaces': {name: os.readlink(root/'ns'/name) for name in ('user', 'mnt', 'net', 'pid', 'cgroup')}}


def clean_environment(root):
    """Construct a finite environment without inherited credentials or JVM/Python overrides."""
    root = Path(root)
    return {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'PYTHONPATH': str(root/'retrieval'), 'PYTHONDONTWRITEBYTECODE': '1',
            'ALLOW_CORPUS_RUNTIME': str(root/'.runtime/corpus'), 'LANGSMITH_TRACING': 'false',
            'TMPDIR': str(root/'.gate/tmp')}


def command(argv, timeout=15, **options):
    """Run a finite explicit command and never return command diagnostics on failure."""
    result = subprocess.run([str(v) for v in argv], capture_output=True, text=True,
                            timeout=timeout, **options)
    if result.returncode:
        raise RuntimeError('bounded_command_failed_' + str(result.returncode))
    return result.stdout


def root_hash(manifest):
    """Bind the complete manifest except its self-referential digest field."""
    return hashlib.sha256(packed({k: v for k, v in manifest.items() if k != 'input_root_sha256'})).hexdigest()


def validate_root(root):
    """Require a unique short private physical root, never a mutable workspace alias."""
    root = Path(root)
    info = root.lstat()
    if root.parent != Path('/tmp') or not root.name.startswith('allow-wp-') or len(root.name) > 30:
        raise ValueError('short_gate_root_required')
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('private_owned_root_required')
    if root.resolve() != root:
        raise ValueError('root_alias_rejected')
    return root
