#!/usr/bin/env python3
"""Observe and stop only one manifest-bound transient user service; never delegate controllers."""
import os
from pathlib import Path
import subprocess
import select
import time

from harness_common import clean_environment, command, process_identity, read_private, same_process, write_private

CGROUP = Path('/sys/fs/cgroup')
EXPECTED = {'cpu.max': '400000 100000', 'memory.high': '5368709120',
            'memory.max': '6442450944', 'memory.swap.max': '0', 'pids.max': '512'}
METRICS = ('cpu.stat', 'cpu.pressure', 'memory.current', 'memory.peak', 'memory.events',
           'memory.swap.current', 'memory.swap.events', 'memory.pressure', 'pids.current',
           'pids.peak', 'pids.events', 'cgroup.events', 'io.stat', 'io.pressure')


def unit_properties(unit):
    """Read a unit's ownership and cleanup properties without changing manager state."""
    output = command(['/usr/bin/systemctl', '--user', 'show', unit, '--property=Id,Description,'
                      'LoadState,ActiveState,SubState,ControlGroup,MainPID,InvocationID,KillMode,Result'])
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def properties(seconds):
    """Return the exact reviewed screen, not a claim about target-host equivalence."""
    return ['CPUQuota=400%', 'CPUQuotaPeriodSec=100ms', 'MemoryHigh=5368709120',
            'MemoryMax=6442450944', 'MemorySwapMax=0', 'TasksMax=512', 'CPUAffinity=0 1 2 3',
            'KillMode=control-group', 'TimeoutStopSec=15', 'SendSIGKILL=yes',
            'RuntimeMaxSec=' + str(seconds), 'UMask=0077', 'Restart=no', 'OOMPolicy=stop',
            'RemainAfterExit=yes']


def launch(manifest, executable, arguments, seconds):
    """Create one uniquely named service after checking that its name is unused."""
    unit = manifest['unit']
    if unit_properties(unit).get('LoadState') != 'not-found':
        raise ValueError('unit_name_already_exists')
    argv = ['/usr/bin/systemd-run', '--user', '--quiet', '--unit=' + unit, '--service-type=exec',
            '--description=allow-fresh:' + manifest['input_root_sha256'],
            '--working-directory=' + manifest['copied_root']]
    argv.extend('--property=' + value for value in properties(seconds))
    environment = clean_environment(manifest['copied_root'])
    argv.extend(['/usr/bin/env', '-i', *[key + '=' + environment[key] for key in sorted(environment)],
                 str(executable), *map(str, arguments)])
    launch_started = time.monotonic_ns()
    command(argv)
    state = unit_properties(unit)
    if state.get('Description') != 'allow-fresh:' + manifest['input_root_sha256']:
        raise ValueError('unit_manifest_ownership_mismatch')
    write_private(Path(manifest['copied_root'])/'.gate/unit-invocation.json',
                  {'invocation_id': state['InvocationID'], 'main_identity': process_identity(int(state['MainPID'])),
                   'launch_started_monotonic_ns': launch_started})
    return state


def group_path(state):
    """Reject nonunified, escaped and absent cgroup paths from manager state."""
    name = state.get('ControlGroup', '')
    path = CGROUP/name.lstrip('/')
    if not name.startswith('/') or '..' in Path(name).parts or not path.is_dir():
        raise ValueError('unit_cgroup_unavailable')
    return path


def pid_group(pid):
    """Read the unified group for one live observed process."""
    lines = Path('/proc', str(pid), 'cgroup').read_text().splitlines()
    matches = [line[3:] for line in lines if line.startswith('0::')]
    if len(matches) != 1:
        raise ValueError('unified_cgroup_required')
    return matches[0]


def members(path):
    """Enumerate all observed processes in the complete service subtree."""
    result = set()
    for file in [path/'cgroup.procs', *path.rglob('cgroup.procs')]:
        try:
            result.update(int(value) for value in file.read_text().split())
        except FileNotFoundError:
            continue
    return sorted(result)


def process_row(pid, group):
    """Check process and every observed thread placement and incarnation consistently."""
    before = process_identity(pid)
    if before is None:
        return None
    try:
        return live_process_row(before, group)
    except (FileNotFoundError, ProcessLookupError):
        if not same_process(before):
            return None
        raise


def live_process_row(before, group):
    """Tolerate confirmed exit races while preserving every live-placement failure."""
    pid = before['pid']
    current = pid_group(pid)
    threads = []
    for task in Path('/proc', str(pid), 'task').iterdir():
        try:
            threads.append({'tid': int(task.name), 'affinity': sorted(os.sched_getaffinity(int(task.name)))})
        except ProcessLookupError:
            continue
    if not same_process(before):
        return None
    if current != group and not current.startswith(group + '/'):
        raise ValueError('owned_process_escaped_cgroup')
    if not threads or any(row['affinity'] != [0, 1, 2, 3] for row in threads):
        raise ValueError('descendant_thread_affinity_mismatch')
    return dict(before, cgroup=current, threads=threads)


def observe(manifest, owned=()):
    """Require exact limits and all observed descendants, including previously seen owners."""
    state = unit_properties(manifest['unit'])
    if state.get('Description') != 'allow-fresh:' + manifest['input_root_sha256']:
        raise ValueError('unit_manifest_ownership_mismatch')
    if state.get('KillMode') != 'control-group':
        raise ValueError('kill_mode_mismatch')
    owner = read_private(Path(manifest['copied_root'])/'.gate/unit-invocation.json')
    if owner['invocation_id'] != state.get('InvocationID') or not same_process(owner['main_identity']):
        raise ValueError('unit_incarnation_changed')
    path = group_path(state)
    limits = {name: (path/name).read_text().strip() for name in EXPECTED}
    if limits != EXPECTED:
        raise ValueError('effective_cgroup_limits_mismatch')
    group = state['ControlGroup']
    if pid_group(os.getpid()) == group or pid_group(os.getpid()).startswith(group + '/'):
        raise ValueError('controller_must_remain_outside_server_group')
    pids = set(members(path)) | {row['pid'] for row in owned if same_process(row)}
    processes = [row for pid in sorted(pids) if (row := process_row(pid, group))]
    if int(state.get('MainPID', 0)) not in {row['pid'] for row in processes}:
        raise ValueError('supervisor_missing_from_group')
    return {'unit': state, 'limits': limits, 'processes': processes,
            'metrics': {name: (path/name).read_text().strip() for name in METRICS if (path/name).exists()},
            'observed_monotonic_ns': time.monotonic_ns()}


def counters(text):
    """Parse kernel counter files without accepting malformed or duplicate fields."""
    pairs = [line.split() for line in text.splitlines()]
    if any(len(row) != 2 for row in pairs) or len({row[0] for row in pairs}) != len(pairs):
        raise ValueError('invalid_kernel_counters')
    return {key: int(value) for key, value in pairs}


def exhausted(snapshot):
    """Fail a run on any OOM or task-budget exhaustion observed in its new group."""
    memory = counters(snapshot['metrics']['memory.events'])
    pids = counters(snapshot['metrics']['pids.events'])
    return any(memory.get(name, 0) for name in ('oom', 'oom_kill', 'oom_group_kill')) or pids.get('max', 0) != 0


def stop(manifest, owned, expected_invocation):
    """Stop one exact service incarnation and require explicit empty-group evidence."""
    state = unit_properties(manifest['unit'])
    if state.get('Description') != 'allow-fresh:' + manifest['input_root_sha256']:
        raise ValueError('cleanup_unit_ownership_mismatch')
    if state.get('InvocationID') != expected_invocation:
        raise ValueError('cleanup_unit_incarnation_changed')
    path = group_path(state)
    descriptor = os.open(path/'cgroup.events', os.O_RDONLY | os.O_CLOEXEC)
    try:
        return stop_observed(manifest, owned, descriptor)
    finally:
        os.close(descriptor)


def stop_observed(manifest, owned, descriptor):
    """Preserve UNKNOWN when a disappearing hierarchy prevents populated=0 observation."""
    watcher = select.poll()
    watcher.register(descriptor, select.POLLPRI | select.POLLERR)
    process = subprocess.Popen(['/usr/bin/systemctl', '--user', 'kill', '--signal=SIGTERM',
                                '--kill-whom=all', manifest['unit']],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline, empty, last = time.monotonic() + 15, False, None
    while time.monotonic() < deadline:
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            last = os.read(descriptor, 4096).decode()
            empty = empty or counters(last).get('populated') == 0
        except OSError:
            pass
        if empty and process.poll() is not None and all(not same_process(row) for row in owned):
            break
        watcher.poll(50)
    absent = all(not same_process(row) for row in owned)
    finished = process.poll() is not None
    stopped = subprocess.run(['/usr/bin/systemctl', '--user', 'stop', manifest['unit']],
                             capture_output=True, timeout=22)
    absent = all(not same_process(row) for row in owned)
    return {'status': 'PASS' if empty and absent and finished and process.returncode == 0 and stopped.returncode == 0 else 'UNKNOWN',
            'populated_zero_observed': empty, 'last_cgroup_events': last,
            'owned_identities_absent': absent, 'graceful_kill_exit_code': process.returncode,
            'stop_exit_code': stopped.returncode,
            'unit': unit_properties(manifest['unit'])}
