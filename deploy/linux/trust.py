"""Verified source-only deployment policy helpers; third-party venv semantics are trusted."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import stat
import subprocess
import sys
import types

ROOT = Path(__file__).absolute().parents[2]
HELPER_SHA = '85f217246b6abeab699249f74e97abab586822678e7b573bbf5690588072dca0'


def digest(path):
    """Hash an already validated regular file."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_path(path, *, private=False, install=False, regular=False):
    """Require protected root/service-owned paths, allowing root sticky ancestors."""
    path = Path(os.path.abspath(path))
    uid = os.geteuid()
    for item in reversed((path, *path.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or info.st_uid not in (0, uid):
            raise ValueError('Untrusted owner or linked path: ' + str(item))
        sticky = item != path and info.st_uid == 0 and stat.S_ISDIR(info.st_mode) and info.st_mode & stat.S_ISVTX
        if info.st_mode & 0o022 and not sticky:
            raise ValueError('Writable installation component: ' + str(item))
    if path.exists():
        info = path.stat()
        if (private or install) and info.st_uid != uid:
            raise ValueError('Service-owned path required: ' + str(path))
        if private and (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1):
            raise ValueError('Private unlinked regular file required: ' + str(path))
        if regular and not stat.S_ISREG(info.st_mode):
            raise ValueError('Regular file required: ' + str(path))
    return path


def no_links(path):
    """Compatibility name for the stronger ownership and mode boundary."""
    return checked_path(path)


def unique_object(pairs):
    """Reject ambiguous duplicate JSON keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def manifest_entries(root=ROOT):
    """Read the trusted-transfer manifest after validating its paths and checksum."""
    checked_path(root, install=True)
    manifest = checked_path(root / 'MANIFEST.json', regular=True)
    checksum = checked_path(root / 'MANIFEST.sha256', regular=True)
    if digest(manifest) != checksum.read_text().split()[0]:
        raise ValueError('Manifest checksum mismatch')
    entries = json.loads(manifest.read_text(), object_pairs_hook=unique_object)['files']
    if not isinstance(entries, dict) or not entries:
        raise ValueError('Invalid manifest entries')
    return entries


def verify_file(name, entries, root=ROOT):
    """Bind one canonical manifest name to protected regular source bytes."""
    relative = Path(name)
    if relative.is_absolute() or str(relative) != name or '..' in relative.parts:
        raise ValueError('Unsafe manifest path')
    expected = entries[name]
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Invalid manifest digest')
    target = checked_path(root / name, regular=True)
    if not target.is_file() or digest(target) != expected:
        raise ValueError('Package integrity mismatch: ' + name)
    return target


def verify_inventory(entries, root=ROOT):
    """Close every application/bootstrap directory, including all bytecode caches."""
    immutable = ('backend/target', 'retrieval', 'scripts', 'config', '.tools/sqlean', 'deploy')
    if any(name.startswith('services/') for name in entries):
        immutable += ('services',)
    for directory in immutable:
        checked_path(root / directory)
        for installed in (root / directory).rglob('*'):
            checked_path(installed)
            if installed.name == '__pycache__' or installed.suffix in ('.pyc', '.pyo'):
                raise ValueError('Application bytecode/cache is forbidden')
            if installed.is_file() and str(installed.relative_to(root)) not in entries:
                if installed == root / 'deploy/instance.json':
                    checked_path(installed, private=True)
                else:
                    raise ValueError('Unlisted application/bootstrap input: ' + str(installed))


def verify_package(root=ROOT):
    """Verify shipped inputs before any application import, SQL or backend action."""
    entries = manifest_entries(root)
    for name in entries:
        verify_file(name, entries, root)
    verify_inventory(entries, root)
    parser = json.loads((root / 'config/sqlean-parser-lock.json').read_text())
    if digest(root / '.tools/sqlean/sqlean_pg_grammar') != parser['binary_sha256']:
        raise ValueError('Pinned parser mismatch')
    if digest(root / 'scripts/warm_worker_image.py') != HELPER_SHA:
        raise ValueError('Pinned worker helper mismatch')
    return entries


def load_source(name, root=ROOT):
    """Compile exact reverified source bytes, never import an application .pyc."""
    entries = verify_package(root)
    path = verify_file(name, entries, root)
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != entries[name]:
        raise ValueError('Source changed during loading')
    module = types.ModuleType('allow_deploy_' + path.stem)
    module.__file__ = str(path)
    exec(compile(source, str(path), 'exec'), module.__dict__)
    return module


def private_runtime(root=ROOT):
    """Create only an owned private runtime directory under the protected root."""
    checked_path(root, install=True)
    path = checked_path(root / '.runtime', install=True)
    if path.exists() and path.stat().st_mode & 0o077:
        raise ValueError('Runtime must already be private')
    path.mkdir(mode=0o700, exist_ok=True)
    return path


@contextlib.contextmanager
def exclusive(root=ROOT):
    """Hold the shared nonblocking lock through all initialization/service cleanup."""
    runtime = private_runtime(root)
    path = checked_path(runtime / 'deployment.lock', private=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_nlink != 1 or not stat.S_ISREG(info.st_mode):
            raise ValueError('Unsafe deployment lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield runtime
    finally:
        os.close(fd)


def require_fresh(root=ROOT):
    """Reject prior generated tools/state before executing any generated program."""
    runtime = private_runtime(root)
    for name in ('.tools/retrieval-venv', '.tools/retrieval', '.tools/retrieval-downloads'):
        path = checked_path(root / name)
        if path.exists():
            raise ValueError('Fresh initialization refuses existing generated tools: ' + name)
    if any(path.name != 'deployment.lock' for path in runtime.iterdir()):
        raise ValueError('Unknown runtime state; preserve and investigate manually')


def load_config(path):
    """Accept closed instance settings, preserving legacy private SSH configurations."""
    value = json.loads(checked_path(path, private=True).read_text(), object_pairs_hook=unique_object)
    required = {'public_origin', 'tunnel_port', 'backend_port', 'advisory_profile'}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - {'access_mode', 'transport', 'installation_slot', 'ai_mode', 'ai_ledger', 'ai_ceiling_micro_usd', 'ai_terms_version', 'ai_tariff_version', 'ai_key_file'}:
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
    value.setdefault('access_mode', 'PRIVATE')
    value.setdefault('transport', 'ssh')
    if value['access_mode'] not in ('PRIVATE', 'ANONYMOUS') or value['transport'] not in ('ssh', 'wsl'):
        raise ValueError('Unknown deployment profile')
    if value['transport'] == 'wsl' and (value['backend_port'] != 18081 or value['tunnel_port'] != 18081):
        raise ValueError('WSL requires matching fixed loopback ports')
    value.setdefault('installation_slot', 'PRIMARY')
    if value['installation_slot'] not in ('PRIMARY', 'PUBLIC_REPLACEMENT'):
        raise ValueError('Unknown installation slot')
    if value['installation_slot'] == 'PUBLIC_REPLACEMENT' and (
            value['access_mode'] != 'ANONYMOUS' or value['transport'] != 'wsl' or
            value['backend_port'] != 18081 or value['tunnel_port'] != 18081):
        raise ValueError('Invalid public replacement profile')
    validate_ai_config(value)
    return value


def validate_ai_config(value):
    """Require explicit private opt-in and closed, nonsecret AI settings."""
    mode = value.get('ai_mode', 'OFF')
    fields = {'ai_ledger', 'ai_ceiling_micro_usd', 'ai_terms_version', 'ai_tariff_version', 'ai_key_file'}
    if mode not in ('OFF', 'FIXTURE', 'REMOTE_ASSISTED'):
        raise ValueError('Unknown AI mode')
    if mode == 'OFF':
        if fields.intersection(value):
            raise ValueError('OFF does not accept AI settings')
        return
    if value['access_mode'] != 'PRIVATE':
        raise ValueError('AI requires private access')
    ledger = value.get('ai_ledger')
    if not isinstance(ledger, str) or not Path(ledger).is_absolute() or '..' in Path(ledger).parts or Path(ledger).is_relative_to(ROOT):
        raise ValueError('AI ledger requires an absolute path')
    amount = value.get('ai_ceiling_micro_usd', 100000)
    if type(amount) is not int or not 50000 <= amount <= 10000000:
        raise ValueError('Invalid AI lifetime ceiling')
    if mode == 'FIXTURE' and any(k in value for k in ('ai_key_file', 'ai_terms_version', 'ai_tariff_version')):
        raise ValueError('Fixture mode cannot receive remote settings')
    if mode == 'REMOTE_ASSISTED':
        for key in ('ai_key_file', 'ai_terms_version', 'ai_tariff_version'):
            if not isinstance(value.get(key), str) or not value[key] or len(value[key]) > 1024:
                raise ValueError('Missing AI remote setting')
        if (not Path(value['ai_key_file']).is_absolute() or '..' in Path(value['ai_key_file']).parts
                or Path(value['ai_key_file']).is_relative_to(ROOT)):
            raise ValueError('AI credential path must be absolute')


def reserved_public_uid():
    """Reserve the numeric public identity even when NSS gives it another name."""
    try:
        public_uid = pwd.getpwnam('allow-public').pw_uid
    except KeyError:
        return False
    return os.geteuid() == public_uid


def public_guard(config, root=ROOT):
    """Check the replacement slot before runtime ownership or provisioning effects."""
    if config.get('installation_slot', 'PRIMARY') == 'PRIMARY':
        if Path(root) == Path('/opt/allow-public') or reserved_public_uid():
            raise ValueError('Reserved public root/account requires PUBLIC_REPLACEMENT')
    else:
        load_source('deploy/linux/public_guard.py', root).check(config, root)


def prerequisites(root=ROOT):
    """Enforce the supported short canonical Ubuntu x86_64 installation profile."""
    root = checked_path(root, install=True)
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
    version = subprocess.run(['/usr/bin/java', '-version'], capture_output=True, text=True, check=True, env=environment(root))
    if not re.search(r'version "17[.\"]', version.stderr + version.stdout):
        raise ValueError('Java 17 required')
    probe = subprocess.run(['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--ro-bind', '/', '/', '/usr/bin/true'],
                           capture_output=True, timeout=15, env=environment(root))
    if probe.returncode:
        raise ValueError('bubblewrap user namespaces unavailable; configure Ubuntu policy explicitly')
    return root


def environment(root=ROOT):
    """Use fixed executables without inherited Python/JVM or PostgreSQL overrides."""
    allowed = {'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR'}
    value = {key: val for key, val in os.environ.items() if key in allowed}
    value['PATH'] = '/usr/bin:/bin'
    value['PYTHONPATH'] = str(root / 'retrieval')
    value['PYTHONDONTWRITEBYTECODE'] = '1'
    value['PYTHONNOUSERSITE'] = '1'
    return value


def run(script, *arguments, root=ROOT, python='/usr/bin/python3', timeout=1800):
    """Run a fixed installed helper with a clean environment."""
    return subprocess.run([str(python), '-B', '-s', str(root / script), *arguments], cwd=root,
                          env=environment(root), check=True, timeout=timeout)




def private_write(path, text):
    """Atomically replace an owned private file without hardlink/symlink exposure."""
    path = checked_path(path, private=True)
    checked_path(path.parent, install=True)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError('Private parent directory required')
    temporary = path.with_name(path.name + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def initialized_marker(path):
    """Require an owned private, explicit initialized-store marker without reset."""
    path = checked_path(path, private=True)
    value = json.loads(path.read_text(), object_pairs_hook=unique_object)
    if value != {'schema': 1, 'empty_private_store_initialized': True}:
        raise ValueError('Invalid initialization marker')


def generated_link(path, directory, kind):
    """Permit only normal managed-runtime interpreter/internal library links."""
    checked_path(path.parent)
    info = path.lstat()
    if info.st_uid != os.geteuid():
        raise ValueError('Generated link must be service-owned')
    relative = str(path.relative_to(directory))
    target = path.resolve(strict=True)
    if kind == 'venv':
        internal = target.is_relative_to(directory) and relative == 'lib64' and target == directory / 'lib'
        interpreter = relative in ('bin/python', 'bin/python3', 'bin/python3.12') and target == Path('/usr/bin/python3').resolve()
        allowed = internal or interpreter
    else:
        library = re.fullmatch(r'lib/(libpq|libecpg|libecpg_compat|libpgtypes)\.so(?:\.[0-9]+)?', relative)
        allowed = library and target.parent == directory / 'lib' and target.name.startswith(library[1] + '.so.')
    if not allowed:
        raise ValueError('Unexpected generated executable/library link')
    checked_path(target, regular=not target.is_dir())


def verify_generated(root=ROOT):
    """Check ownership/modes of freshly provisioned dependencies and retained state."""
    for suffix, kind in (('.tools/retrieval-venv', 'venv'), ('.tools/retrieval/postgres', 'postgres')):
        directory = checked_path(root / suffix, install=True)
        if not directory.is_dir():
            raise ValueError('Missing provisioned dependency runtime')
        for path in directory.rglob('*'):
            if path.is_symlink():
                generated_link(path, directory, kind)
            else:
                checked_path(path)
    runtime = private_runtime(root)
    for path in runtime.rglob('*'):
        checked_path(path, install=True)
        if path.stat().st_mode & 0o077:
            raise ValueError('Retained runtime entry must be private')
