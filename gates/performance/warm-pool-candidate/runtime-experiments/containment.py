#!/usr/bin/env python3
"""Observe and stop one manifest-bound delegated warm experiment scope."""
import os
from pathlib import Path
import subprocess
import select
import stat
import time

from harness_common import clean_environment, command, process_identity, read_private, same_process, write_private

CGROUP = Path('/sys/fs/cgroup')
EXPECTED = {'cpu.max': '400000 100000', 'memory.high': '5368709120',
            'memory.max': '6442450944', 'memory.swap.max': '0', 'pids.max': '512'}
METRICS = ('cpu.stat', 'cpu.pressure', 'memory.current', 'memory.peak', 'memory.events',
           'memory.swap.current', 'memory.swap.events', 'memory.pressure', 'pids.current',
           'pids.peak', 'pids.events', 'cgroup.events', 'io.stat', 'io.pressure')


def user_manager_environment():
    """Use only the owned fixed local user-manager socket; never inherit a remote bus route."""
    directory = Path('/run/user')/str(os.getuid())
    bus = directory/'bus'
    parent, socket = directory.lstat(), bus.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise ValueError('user_manager_directory_ownership')
    if not stat.S_ISSOCK(socket.st_mode) or socket.st_uid != os.getuid() or directory.resolve() != directory:
        raise ValueError('user_manager_socket_ownership')
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'XDG_RUNTIME_DIR': str(directory),
            'DBUS_SESSION_BUS_ADDRESS': 'unix:path=' + str(bus)}


def unit_properties(unit):
    """Read a unit's ownership and cleanup properties without changing manager state."""
    output = command(['/usr/bin/systemctl', '--user', 'show', unit, '--property=Id,Description,'
                      'LoadState,ActiveState,SubState,ControlGroup,MainPID,InvocationID,KillMode,Delegate,Result'],
                     env=user_manager_environment())
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def properties(seconds):
    """Return the exact reviewed screen, not a claim about target-host equivalence."""
    return ['CPUQuota=400%', 'CPUQuotaPeriodSec=100ms', 'MemoryHigh=5368709120',
            'MemoryMax=6442450944', 'MemorySwapMax=0', 'TasksMax=512', 'CPUAffinity=0 1 2 3',
            'KillMode=control-group', 'TimeoutStopSec=15', 'SendSIGKILL=yes',
            'RuntimeMaxSec=' + str(seconds), 'UMask=0077', 'Restart=no', 'OOMPolicy=stop',
            'RemainAfterExit=yes']


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
            groups = [line[3:] for line in (task/'cgroup').read_text().splitlines() if line.startswith('0::')]
            if len(groups) != 1 or not (groups[0] == group or groups[0].startswith(group+'/')):
                raise ValueError('owned_thread_escaped_cgroup')
            threads.append({'tid': int(task.name), 'affinity': sorted(os.sched_getaffinity(int(task.name))),
                            'cgroup': groups[0]})
        except (FileNotFoundError, ProcessLookupError):
            continue
    if not same_process(before):
        return None
    if current != group and not current.startswith(group + '/'):
        raise ValueError('owned_process_escaped_cgroup')
    if not threads or any(row['affinity'] != [0, 1, 2, 3] for row in threads):
        raise ValueError('descendant_thread_affinity_mismatch')
    return dict(before, cgroup=current, threads=threads)


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
    if not {'oom', 'oom_kill', 'oom_group_kill'} <= set(memory) or 'max' not in pids:
        raise ValueError('required_resource_counter_missing')
    return any(memory[name] for name in ('oom', 'oom_kill', 'oom_group_kill')) or pids['max'] != 0


def stop(manifest, owned, expected_invocation):
    """Stop one exact service incarnation and require explicit empty-group evidence."""
    state = unit_properties(manifest['unit'])
    if state.get('Description') != 'allow-warm:' + manifest['input_root_sha256']:
        raise ValueError('cleanup_unit_ownership_mismatch')
    if state.get('InvocationID') != expected_invocation:
        raise ValueError('cleanup_unit_incarnation_changed')
    path = group_path(state)
    descriptors = {}
    try:
        for name in ('cgroup.events', 'memory.peak', 'memory.events', 'pids.events', 'pids.peak', 'cpu.stat'):
            descriptors[name] = os.open(path/name, os.O_RDONLY | os.O_CLOEXEC)
        return stop_observed(manifest, owned, descriptors)
    finally:
        for descriptor in descriptors.values():
            os.close(descriptor)


def descriptor_text(descriptor):
    """Read an already-owned kernel counter descriptor without resolving a replacement group."""
    os.lseek(descriptor, 0, os.SEEK_SET)
    return os.read(descriptor, 16384).decode().strip()


def terminal_resources(descriptors):
    """Capture final counters after an explicit empty event; read failure remains incomplete."""
    return {'metrics': {name: descriptor_text(descriptor) for name, descriptor in descriptors.items()
                        if name != 'cgroup.events'}, 'observed_monotonic_ns': time.monotonic_ns()}


def removed_after_empty(empty, absent, stop_code, final):
    """Recognize only a vanished unit after the positively observed owned-group empty event."""
    return empty is True and absent is True and stop_code == 5 and final.get('LoadState') == 'not-found'


def stop_observed(manifest, owned, descriptors):
    """Own the outside systemctl child through every observation or unit-stop failure."""
    process = subprocess.Popen(['/usr/bin/systemctl', '--user', 'kill', '--signal=SIGTERM',
                                '--kill-whom=all', manifest['unit']],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=user_manager_environment())
    progress = {'stop_attempted': False}
    report = {'status': 'UNKNOWN'}
    try:
        report = observe_stop_command(manifest, owned, descriptors, process, progress)
    except Exception as error:
        report['observation_failure_class'] = type(error).__name__
        if not progress['stop_attempted']:
            try:
                stopped = subprocess.run(['/usr/bin/systemctl', '--user', 'stop', manifest['unit']],
                                         capture_output=True, timeout=22, env=user_manager_environment())
                report['emergency_stop_exit_code'] = stopped.returncode
            except Exception as stop_error:
                report['emergency_stop_failure_class'] = type(stop_error).__name__
    finally:
        report['control_command_cleanup'] = reap_control_command(process)
        cleanup = report['control_command_cleanup']
        if cleanup['forced'] or not cleanup['reaped']:
            report['status'] = 'UNKNOWN'
    return report


def reap_control_command(process):
    """Bounded reap of the exact outside Popen; forced completion cannot establish PASS."""
    result = {'pid': process.pid, 'forced': False, 'reaped': False, 'original_exit_code': process.poll()}
    try:
        if process.poll() is None:
            result['forced'] = True
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            result['forced'] = True
            process.kill()
            process.wait(timeout=3)
        result['reaped'] = True
        result['final_exit_code'] = process.returncode
    except Exception as error:
        result['failure_class'] = type(error).__name__
    return result


def observe_stop_command(manifest, owned, descriptors, process, progress):
    """Preserve the original signal completion and explicit empty/counter observations."""
    watcher = select.poll()
    descriptor = descriptors['cgroup.events']
    watcher.register(descriptor, select.POLLPRI | select.POLLERR)
    deadline, empty, last, terminal = time.monotonic() + 15, False, None, None
    while time.monotonic() < deadline:
        try:
            last = descriptor_text(descriptor)
            empty = empty or counters(last).get('populated') == 0
            if empty and terminal is None:
                terminal = terminal_resources(descriptors)
        except OSError:
            pass
        if empty and process.poll() is not None and all(not same_process(row) for row in owned):
            break
        watcher.poll(50)
    absent = all(not same_process(row) for row in owned)
    finished = process.poll() is not None
    progress['stop_attempted'] = True
    stopped = subprocess.run(['/usr/bin/systemctl', '--user', 'stop', manifest['unit']],
                             capture_output=True, timeout=22, env=user_manager_environment())
    absent = all(not same_process(row) for row in owned)
    final = unit_properties(manifest['unit'])
    removed = removed_after_empty(empty, absent, stopped.returncode, final)
    stopped_ok = stopped.returncode == 0 or removed
    complete = terminal is not None
    resources_ok = complete and not exhausted(terminal)
    return {'status': 'PASS' if empty and absent and resources_ok and finished and process.returncode == 0 and stopped_ok else 'UNKNOWN',
            'populated_zero_observed': empty, 'last_cgroup_events': last,
            'terminal_resources': terminal, 'terminal_resources_complete': complete,
            'terminal_resource_limits_passed': resources_ok,
            'owned_identities_absent': absent, 'graceful_kill_exit_code': process.returncode,
            'stop_exit_code': stopped.returncode,
            'stop_disposition': 'already_removed_after_explicit_empty' if removed else 'stop_command',
            'unit': final}
