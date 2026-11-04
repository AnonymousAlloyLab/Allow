#!/usr/bin/env python3
"""Place one blocked caller-context supervisor in an owned service before exec."""
import argparse
import ctypes
import os
from pathlib import Path
import signal
import re
import subprocess
import sys
import time

import containment
from harness_common import clean_environment, command, process_identity, read_private, same_process, write_private


def security(pid):
    """Read the existing security context without selecting or changing any profile."""
    root = Path('/proc')/str(pid)
    fields = dict(line.split(':', 1) for line in (root/'status').read_text().splitlines())
    names = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb', 'NoNewPrivs', 'Seccomp')
    return {'profile': (root/'attr/current').read_text().strip(),
            'fields': {name: fields[name].strip() for name in names},
            'namespaces': {name: os.readlink(root/'ns'/name) for name in ('user', 'mnt', 'net', 'pid', 'cgroup')}}


def anchor(root):
    """Hold the owned unit open without launching any application process."""
    manifest = read_private(root/'.gate/manifest.json')
    write_private(root/'.gate/anchor.json', {'identity': process_identity(os.getpid()), 'security': security(os.getpid()),
                  'input_root_sha256': manifest['input_root_sha256'], 'unit': manifest['unit']})
    while True:
        signal.pause()


def gated(root, descriptor, parent, executable, arguments):
    """Exit on parent death/EOF; exec only after the controller's one-byte release."""
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise RuntimeError('parent_death_signal_failed')
    if os.getppid() != parent['pid'] or not same_process(parent):
        raise RuntimeError('gated_parent_absent')
    write_private(root/'.gate/gated.json', {'identity': process_identity(os.getpid()), 'security': security(os.getpid())})
    permitted = os.read(descriptor, 1)
    os.close(descriptor)
    if permitted != b'R' or os.getppid() != parent['pid'] or not same_process(parent):
        raise RuntimeError('gated_release_absent')
    os.execve(executable, [executable, *arguments], clean_environment(root))


def wait_gated(root, child, parent):
    """Require the exact blocked incarnation and caller context before attachment."""
    deadline = time.monotonic() + 5
    while not (root/'.gate/gated.json').exists():
        if child.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError('gated_startup_failed')
        time.sleep(.01)
    witness = read_private(root/'.gate/gated.json')
    identity = witness['identity']
    if identity != process_identity(child.pid) or not same_process(parent):
        raise ValueError('gated_identity_changed')
    if witness['security'] != security(parent['pid']):
        raise ValueError('gated_caller_context_changed')
    if len(list((Path('/proc')/str(child.pid)/'task').iterdir())) != 1:
        raise ValueError('gated_not_single_thread')
    return witness


def place(manifest, child, witness, invocation):
    """Attach only the exact owned blocked PID, then verify every thread before release."""
    identity = witness['identity']
    if not same_process(identity) or child.poll() is not None:
        raise ValueError('gated_identity_changed')
    os.sched_setaffinity(child.pid, {0, 1, 2, 3})
    root = Path(manifest['copied_root'])
    deadline = time.monotonic() + 5
    while not (root/'.gate/anchor.json').exists():
        if time.monotonic() >= deadline:
            raise ValueError('anchor_witness_deadline')
        time.sleep(.01)
    anchor_witness = read_private(root/'.gate/anchor.json')
    if anchor_witness['identity'] != process_identity(int(invocation['MainPID'])):
        raise ValueError('anchor_witness_incarnation')
    result = subprocess.run(['/usr/bin/busctl', '--user', 'call', 'org.freedesktop.systemd1',
             '/org/freedesktop/systemd1', 'org.freedesktop.systemd1.Manager',
             'AttachProcessesToUnit', 'ssau', manifest['unit'], '', '1', str(child.pid)],
            env=containment.user_manager_environment(), capture_output=True, timeout=15)
    write_private(root/'.gate/attach-method-private.json', {'exit_code': result.returncode,
                  'stdout': result.stdout.decode(errors='replace'), 'stderr': result.stderr.decode(errors='replace')})
    if result.returncode:
        raise ValueError('attach_method_failed')
    snapshot = containment.observe(manifest, [identity])
    if snapshot['unit']['InvocationID'] != invocation['InvocationID']:
        raise ValueError('attach_unit_incarnation_changed')
    if identity != process_identity(child.pid) or child.poll() is not None:
        raise ValueError('attached_identity_changed')
    if not any(row['pid'] == child.pid and row['start_ticks'] == identity['start_ticks'] for row in snapshot['processes']):
        raise ValueError('attached_supervisor_missing')
    if security(child.pid) != witness['security']:
        raise ValueError('attachment_changed_security_context')
    return snapshot


def launch(manifest, executable, arguments, seconds):
    """Start an owned anchor and release one attached supervisor only after containment checks."""
    root = Path(manifest['copied_root'])
    script = root/'.gate/attached_launch.py'
    invocation, read_end, write_end, child, released = None, None, None, None, False
    write_private(root/'.gate/attachment-intent.json', {'input_root_sha256': manifest['input_root_sha256'],
                  'unit': manifest['unit'], 'earliest_start_ticks': int(time.clock_gettime(time.CLOCK_BOOTTIME)*os.sysconf('SC_CLK_TCK'))})
    try:
        invocation = containment.launch(manifest, sys.executable, [script, 'anchor', '--root', root], seconds)
        read_end, write_end = os.pipe2(os.O_CLOEXEC)
        parent = process_identity(os.getpid())
        argv = [sys.executable, '-B', str(script), 'gated', '--root', str(root), '--fd', str(read_end),
                '--parent-pid', str(parent['pid']), '--parent-start', parent['start_ticks'], '--', str(executable), *map(str, arguments)]
        log = os.open(root/'.gate/attached-private.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(log, 'wb') as stream:
            child = subprocess.Popen(argv, pass_fds=(read_end,), env=clean_environment(root), stdout=stream, stderr=stream, umask=0o077)
        os.close(read_end)
        read_end = None
        witness = wait_gated(root, child, parent)
        snapshot = place(manifest, child, witness, invocation)
        write_private(root/'.gate/attached-launch.json', {'parent': parent, 'attached': witness, 'before_release': snapshot})
        if os.write(write_end, b'R') != 1:
            raise RuntimeError('gated_release_failed')
        released = True
        return invocation, child
    finally:
        if write_end is not None:
            os.close(write_end)
        if read_end is not None:
            os.close(read_end)
        if not released:
            failed_launch_cleanup(manifest, invocation, child)


def failed_launch_cleanup(manifest, invocation, child):
    """Reap only the controller-owned child and stop the exact unit on any pre-release failure."""
    report = {'status': 'UNKNOWN', 'child_reaped': child is None, 'unit': {'status': 'UNKNOWN'}}
    try:
        if child is not None:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
            report['child_reaped'] = True
    except Exception as error:
        report['child_failure_class'] = type(error).__name__
    finally:
        try:
            state, owner = reconcile_start(manifest, invocation)
            report['unit'] = containment.stop(manifest, [owner], state['InvocationID']) if state else {'status': 'PASS', 'unit_never_loaded': True}
        except Exception as error:
            report['unit_failure_class'] = type(error).__name__
    if report['child_reaped'] and report['unit']['status'] == 'PASS':
        report['status'] = 'PASS'
    write_private(Path(manifest['copied_root'])/'.gate/failed-attach-cleanup.json', report)
    if report['status'] != 'PASS':
        raise RuntimeError('failed_attachment_cleanup_unknown')


def reconcile_start(manifest, invocation):
    """Reconcile partial creation only with exact private anchor/incarnation evidence; never by name alone."""
    root = Path(manifest['copied_root'])
    state = containment.unit_properties(manifest['unit'])
    if state.get('LoadState') == 'not-found':
        raise ValueError('partial_launch_disappeared_without_empty_witness')
    if invocation is not None and invocation['InvocationID'] != state.get('InvocationID'):
        raise ValueError('partial_launch_invocation_changed')
    if state.get('Description') != 'allow-fresh:' + manifest['input_root_sha256'] or not re.fullmatch('[0-9a-f]{32}', state.get('InvocationID', '')):
        raise ValueError('partial_launch_ownership_unproven')
    owner = read_private(root/'.gate/anchor.json')
    intent = read_private(root/'.gate/attachment-intent.json')
    identity = owner['identity']
    if owner['unit'] != manifest['unit'] or owner['input_root_sha256'] != manifest['input_root_sha256']:
        raise ValueError('partial_launch_anchor_binding')
    if identity['pid'] != int(state['MainPID']) or not same_process(identity) or int(identity['start_ticks']) < intent['earliest_start_ticks']:
        raise ValueError('partial_launch_anchor_incarnation')
    expected = [sys.executable, str(root/'.gate/attached_launch.py'), 'anchor', '--root', str(root)]
    actual = (Path('/proc')/str(identity['pid'])/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
    if actual != [value.encode() for value in expected]:
        raise ValueError('partial_launch_anchor_command')
    write_private(root/'.gate/reconciled-start.json', {'unit': state, 'anchor': owner, 'intent': intent})
    return state, identity


def main():
    """Expose only the owned anchor and blocked shim entry points."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('anchor', 'gated'))
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--fd', type=int)
    parser.add_argument('--parent-pid', type=int)
    parser.add_argument('--parent-start')
    args, trailing = parser.parse_known_args()
    if args.operation == 'anchor':
        anchor(args.root)
    else:
        argv = trailing[1:] if trailing[:1] == ['--'] else trailing
        gated(args.root, args.fd, {'pid': args.parent_pid, 'start_ticks': args.parent_start}, argv[0], argv[1:])


if __name__ == '__main__':
    main()
