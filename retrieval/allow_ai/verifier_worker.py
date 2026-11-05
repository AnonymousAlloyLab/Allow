"""Private disposable verifier supervisor; invoked only by verification.py."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import uuid

JAVA_HOME = Path('/usr/lib/jvm/java-17-openjdk-amd64')
ALLOY_SHA256 = '6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d'
MAX_FRAME = 1048576
POLICY = 'allow-ai-synthetic-source-v1'


def digest(path):
    """Hash a trusted file without retaining its contents."""
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def identity(target):
    """Pin worker inputs and fixed executable helpers; system libraries are trusted."""
    if target.resolve() != target or not (target / 'classes/dev/allow/worker/DocumentWorkerMain.class').is_file():
        raise ValueError('build')
    classes = sorted(p for p in (target / 'classes').rglob('*') if p.is_file() and 'static' not in p.relative_to(target / 'classes').parts)
    jars = sorted((target / 'dependency').glob('*.jar'))
    solver = target / 'solver/alloy.jar'
    if not jars or digest(solver) != ALLOY_SHA256:
        raise ValueError('build')
    helpers = [Path(__file__), Path(__file__).with_name('verification.py'), Path('/usr/bin/prlimit'),
               Path('/usr/bin/bwrap'), Path('/usr/bin/python3'), JAVA_HOME / 'bin/java']
    result = hashlib.sha256()
    for path in classes + jars + [solver] + helpers:
        if path.is_symlink() and path not in helpers:
            raise ValueError('link')
        result.update(str(path).encode() + b'\0' + digest(path).encode() + b'\0')
    return result.hexdigest()


def _bounded(path, maximum):
    """Read a small kernel metadata file without accepting a final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        raw = os.read(fd, maximum + 1)
        if len(raw) > maximum:
            raise ValueError('metadata_size')
        return raw.decode('ascii')
    finally:
        os.close(fd)


def _canonical(value):
    """Require an unescaped canonical absolute kernel path."""
    if not value.startswith('/') or '\\' in value or value != str(Path(value)):
        raise ValueError('metadata_path')
    if any(part in ('.', '..') for part in value.split('/')):
        raise ValueError('metadata_path')
    return Path(value)


def _membership(cgroup, mountinfo):
    """Map the unique unified membership to its cgroup-v2 mount and relative path."""
    memberships = [line[3:] for line in cgroup.splitlines() if line.startswith('0::')]
    if len(memberships) != 1:
        raise ValueError('membership')
    member = _canonical(memberships[0])
    matches = []
    for line in mountinfo.splitlines():
        before, sep, after = line.partition(' - ')
        if not sep or not after.startswith('cgroup2 '):
            continue
        fields = before.split()
        if len(fields) < 6:
            raise ValueError('mountinfo')
        root, mount = _canonical(fields[3]), _canonical(fields[4])
        try:
            relative = member.relative_to(root)
        except ValueError:
            continue
        matches.append((len(root.parts), mount, relative))
    if not matches:
        raise ValueError('mountinfo')
    matches.sort(key=lambda item: item[0], reverse=True)
    if len(matches) > 1 and matches[0][0] == matches[1][0]:
        raise ValueError('ambiguous_mount')
    return matches[0][1], matches[0][2]


def _cgroup_limit(mount, relative):
    """Check each actual cgroup ancestor with symlink-free directory traversal."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    fds = [fd]
    try:
        for part in mount.parts[1:] + relative.parts:
            fd = os.open(part, flags, dir_fd=fd)
            fds.append(fd)
        mount_index = len(mount.parts) - 1
        for directory in reversed(fds[mount_index:]):
            file_fd = os.open('pids.max', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                raw = os.read(file_fd, 65).decode('ascii').strip()
            finally:
                os.close(file_fd)
            if raw == 'max':
                continue
            if not raw.isascii() or not raw.isdecimal() or len(raw) > 20:
                raise ValueError('pids_max')
            if int(raw) <= 512:
                return True
        return False
    finally:
        for opened in reversed(fds):
            os.close(opened)


def _cgroup_bounded():
    """Trust only current kernel-reported unified membership and a verified cap."""
    try:
        mount, relative = _membership(_bounded('/proc/self/cgroup', 65536),
                                      _bounded('/proc/self/mountinfo', 1048576))
        return _cgroup_limit(mount, relative)
    except (OSError, ValueError, UnicodeError):
        return False


def limits():
    """Require an unprivileged UID and apply the per-UID kernel process limit."""
    if os.getuid() == 0 or os.geteuid() != os.getuid():
        raise ValueError('uid')
    status = Path('/proc/self/status').read_text()
    if int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')), 16):
        raise ValueError('capabilities')
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FRAME, MAX_FRAME))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if not _cgroup_bounded():
        resource.setrlimit(resource.RLIMIT_NPROC, (512, 512))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def command(target):
    """Use fixed read-only mounts and unshared network for the Java worker."""
    cmd = ['/usr/bin/prlimit', '--as=2147483648', '--cpu=12', '--fsize=1048576', '--nofile=256',
           '/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--cap-drop', 'ALL']
    mounts = [(JAVA_HOME, str(JAVA_HOME)), ('/usr/lib/x86_64-linux-gnu', '/lib/x86_64-linux-gnu'),
              ('/usr/lib/x86_64-linux-gnu', '/usr/lib/x86_64-linux-gnu'), ('/lib64', '/lib64'),
              ('/etc/java-17-openjdk', '/etc/java-17-openjdk'), (target / 'classes', '/app/classes'),
              (target / 'dependency', '/app/dependency'), (target / 'solver/alloy.jar', '/app/solver.jar')]
    for src, dst in mounts:
        cmd += ['--ro-bind', str(src), dst]
    return cmd + ['--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev', '--chdir', '/tmp',
                  str(JAVA_HOME / 'bin/java'), '-Xmx512m', '-Xss512k', '-XX:+UseSerialGC',
                  '-XX:ActiveProcessorCount=2', '-XX:MaxMetaspaceSize=128m', '-XX:CompressedClassSpaceSize=64m',
                  '-XX:ReservedCodeCacheSize=48m', '-Djava.awt.headless=true', '-Dfile.encoding=UTF-8',
                  '-Djava.io.tmpdir=/tmp', '-cp', '/app/classes:/app/dependency/*:/app/solver.jar',
                  'dev.allow.worker.DocumentWorkerMain']


def unique(pairs):
    """Reject duplicate worker JSON keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate')
        result[key] = value
    return result


def run(request):
    """Validate exact source and return only bounded, content-free evidence."""
    limits()
    target = Path(request['target'])
    source = request['source']
    before = identity(target)
    if request['expected'] and before != request['expected']:
        return {'status': 'UNAVAILABLE', 'code': 'WORKER_BUILD_CHANGED'}
    nonce = str(uuid.uuid4())
    frame = {'protocol': 1, 'requestId': nonce, 'policyVersion': POLICY, 'operation': 'VALIDATE',
             'candidate': {'mode': 'SOURCE', 'source': source}, 'baseArtifact': {}, 'ownedIdInventory': {}}
    import tempfile
    with tempfile.TemporaryFile() as output:
        child = subprocess.run(command(target), input=(json.dumps(frame, ensure_ascii=True) + '\n').encode(),
                               stdout=output, stderr=subprocess.DEVNULL, env={}, close_fds=True, check=False)
        output.seek(0)
        raw = output.read(MAX_FRAME + 1)
    if identity(target) != before:
        return {'status': 'UNAVAILABLE', 'code': 'WORKER_BUILD_CHANGED'}
    return decode(raw, child.returncode, nonce, source, before)


def decode(raw, returncode, nonce, source, before):
    """Check the exact worker frame and return content-free evidence."""
    if returncode or len(raw) > MAX_FRAME or raw.count(b'\n') != 1 or not raw.endswith(b'\n'):
        raise ValueError('frame')
    value = json.loads(raw, object_pairs_hook=unique)
    if set(value) != {'protocol', 'requestId', 'status', 'data'} or type(value['protocol']) is not int or value['protocol'] != 1 or value['requestId'] != nonce or not isinstance(value['data'], dict):
        raise ValueError('protocol')
    data = value['data']
    if value['status'] == 'INVALID':
        codes = {'INVALID_DRAFT': 'SOURCE_PARSE_INVALID', 'TYPE_MISMATCH': 'SOURCE_TYPE_INVALID',
                 'UNBOUND_SYMBOL': 'SOURCE_TYPE_INVALID', 'UNSUPPORTED_FRAGMENT': 'SOURCE_PROFILE_INVALID'}
        if data.get('code') not in codes:
            raise ValueError('diagnostic')
        return {'status': 'INVALID', 'code': codes[data['code']], 'build': before}
    source_hash = hashlib.sha256(source.encode('utf-8')).hexdigest()
    if value['status'] != 'VALIDATED' or data.get('mode') not in ('BLOCK_SUPPORTED', 'TEXT_ONLY') or data.get('source') != source or data.get('sourceHash') != source_hash:
        raise ValueError('identity')
    if (data['mode'] == 'BLOCK_SUPPORTED' and not isinstance(data.get('module'), dict)) or (data['mode'] == 'TEXT_ONLY' and data.get('module') is not None):
        raise ValueError('projection')
    return {'status': 'VALIDATED', 'projection': data['mode'], 'source_hash': source_hash, 'build': before}


if __name__ == '__main__':
    try:
        request = json.loads(sys.stdin.buffer.read(131073))
        result = run(request)
    except Exception:
        result = {'status': 'UNAVAILABLE', 'code': 'WORKER_UNAVAILABLE'}
    sys.stdout.write(json.dumps(result, separators=(',', ':')) + '\n')
