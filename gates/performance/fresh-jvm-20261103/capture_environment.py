#!/usr/bin/env python3
"""Capture read-only workstation and current build facts for a future isolated experiment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
CGROUP_ROOT = Path('/sys/fs/cgroup')
SOURCE_FILES = (
    'backend/src/main/java/dev/allow/backend/BuildIdentity.java',
    'backend/src/main/java/dev/allow/backend/BubblewrapLauncher.java',
    'backend/src/main/java/dev/allow/backend/DocumentWorker.java',
    'backend/src/main/java/dev/allow/backend/FrameProcess.java',
    'backend/src/main/java/dev/allow/worker/DocumentWorkerMain.java',
    'backend/src/main/java/dev/allow/document/DocumentEngine.java',
    'backend/src/main/java/dev/allow/backend/DocumentValidationContext.java',
    'backend/src/main/java/dev/allow/backend/DocumentQueries.java',
    'scripts/run_local.py', 'scripts/bootstrap_corpus.py',
    'retrieval/allow_retrieval/sql_proxy.py',
    'retrieval/allow_retrieval/sql_guard.py',
    'retrieval/allow_retrieval/sql_image_config.py',
    'retrieval/allow_documents/store.py',
    'config/sqlean-parser-lock.json',
    'gates/planning/performance-remediation-20261103/contract.json',
    'gates/planning/performance-remediation-20261103/council-disposition.json',
    'gates/document/component-profiles/remaining-latency-options.json',
)


def command(arguments):
    """Run an explicit bounded read-only command and retain its return code."""
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=15)
    return {'arguments': arguments, 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def file_record(path):
    """Hash bytes without following a source-tree symlink silently."""
    if path.is_symlink():
        raise ValueError('Unexpected source symlink: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            digest.update(chunk)
    return {'path': str(path.relative_to(ROOT)), 'size': path.stat().st_size,
            'sha256': digest.hexdigest()}


def ancestors():
    """Read controller availability and limits without changing any hierarchy."""
    group = Path('/proc/self/cgroup').read_text().strip().split('::')[1]
    current = CGROUP_ROOT / group.lstrip('/')
    result = []
    names = ('cgroup.controllers', 'cgroup.subtree_control', 'cgroup.type', 'cpu.max',
             'cpuset.cpus.effective', 'memory.max', 'memory.high', 'memory.swap.max', 'pids.max')
    while current == CGROUP_ROOT or CGROUP_ROOT in current.parents:
        info = current.stat()
        row = {'path': str(current), 'uid': info.st_uid,
               'mode': oct(stat.S_IMODE(info.st_mode)), 'writable': os.access(current, os.W_OK)}
        for name in names:
            path = current / name
            if path.exists():
                row[name] = {'value': path.read_text().strip(), 'writable': os.access(path, os.W_OK)}
        result.append(row)
        if current == CGROUP_ROOT:
            break
        current = current.parent
    return result


def java_properties():
    """Read the installed JVM's own properties without loading Allow classes."""
    raw = command(['java', '-XshowSettings:properties', '-version'])
    values = {}
    for line in raw['stderr'].splitlines():
        if ' = ' in line:
            key, value = (part.strip() for part in line.split(' = ', 1))
            if key in ('java.home', 'java.runtime.version', 'java.vm.version', 'java.vendor'):
                values[key] = value
    if raw['exit_code'] or 'java.runtime.version' not in values:
        raise RuntimeError('JVM identity unavailable')
    return values


def build_identity(runtime_version):
    """Independently compute the current POSIX BuildIdentity byte sequence, not a Java proof."""
    target = ROOT / 'backend/target'
    paths = sorted(path for path in (target/'classes').rglob('*') if path.is_file())
    paths += sorted(path for path in (target/'dependency').rglob('*.jar') if path.is_file())
    paths.append(target/'solver/alloy.jar')
    digest = hashlib.sha256()
    inventory = []
    for path in paths:
        inventory.append(file_record(path))
        digest.update(str(path.relative_to(target)).encode('utf8'))
        digest.update(b'\0')
        with path.open('rb') as stream:
            while chunk := stream.read(8192):
                digest.update(chunk)
        digest.update(b'\0')
    digest.update(runtime_version.encode('utf8'))
    return {'algorithm': 'independent transcription of current BuildIdentity.java on POSIX',
            'java_runtime_version': runtime_version, 'value': digest.hexdigest(), 'files': inventory}


def observations():
    """Collect a finite environment snapshot without inspecting credentials or other app content."""
    java = java_properties()
    tools = ('systemd-run', 'systemctl', 'bwrap', 'prlimit', 'taskset', 'unshare', 'java', 'jcmd')
    return {'schema_version': '1.0', 'classification': 'READ_ONLY_OBSERVATION_NOT_ACCEPTANCE',
            'captured_utc': datetime.now(timezone.utc).isoformat(), 'uid': os.getuid(),
            'kernel': platform.release(), 'machine': platform.machine(),
            'cpu_affinity': sorted(os.sched_getaffinity(0)),
            'tools': {name: shutil.which(name) for name in tools}, 'java': java,
            'cgroup_ancestors': ancestors(),
            'user_delegation': command(['systemctl', 'show', 'user@1000.service',
                '--property=Delegate', '--property=DelegateControllers', '--property=ControlGroup',
                '--property=MemoryMax', '--property=CPUQuotaPerSecUSec']),
            'user_manager': command(['systemctl', '--user', 'show', '--property=ControlGroup']),
            'systemd_version': command(['systemd', '--version']),
            'cpu_topology': command(['lscpu', '--parse=CPU,CORE,SOCKET,NODE,ONLINE']),
            'memory': command(['free', '-b']),
            'build_identity': build_identity(java['java.runtime.version']),
            'sources': [file_record(ROOT/name) for name in SOURCE_FILES],
            'mutations': [], 'services_started': [], 'benchmarks_run': []}


def main():
    """Write one new gate-local observation; refuse existing output or another tree."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output.resolve()
    if not output.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError('Output must remain inside this gate directory')
    result = observations()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'observation': str(output), 'build_identity': result['build_identity']['value'],
                      'build_files': len(result['build_identity']['files']), 'benchmarks_run': 0}))


if __name__ == '__main__':
    main()
