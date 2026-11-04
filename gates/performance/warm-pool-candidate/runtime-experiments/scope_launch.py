#!/usr/bin/env python3
"""Owned transient scope preserving the caller's existing namespace permissions."""
import argparse
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import containment
import delegation
from harness_common import clean_environment, process_identity, read_private, same_process, security, write_private


def properties(seconds):
    """Declare exact scope budgets and kill semantics with private delegation and unchanged security policy."""
    return [item for item in containment.properties(seconds)
            if not item.startswith(('CPUAffinity=', 'UMask=', 'Restart=', 'RemainAfterExit='))] + ['Delegate=yes']


def gated(root, executable, arguments):
    """Publish an idle owned witness; no application exec until verified placement release."""
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise RuntimeError('scope_parent_death_signal_failed')
    intent = read_private(root/'.gate/scope-intent.json')
    identity = process_identity(os.getpid())
    parent = process_identity(os.getppid())
    witness = {'identity': identity, 'parent': parent, 'security': security(os.getpid()),
               'input_root_sha256': intent['input_root_sha256']}
    write_private(root/'.gate/scoped-owner.json', witness)
    deadline = time.monotonic() + 10
    await_release_file(root/'.gate/scope-configure.json', intent, parent, deadline)
    configure = read_private(root/'.gate/scope-configure.json')
    if configure != {'owner': identity, 'input_root_sha256': intent['input_root_sha256']}:
        raise ValueError('scope_configure_wrong_owner')
    write_private(root/'.gate/delegation-ready.json', delegation.configure(root))
    while not (root/'.gate/scope-release.json').exists():
        if not same_process(intent['controller']) or not same_process(parent) or time.monotonic() >= deadline:
            raise RuntimeError('scope_release_absent')
        time.sleep(.01)
    release = read_private(root/'.gate/scope-release.json')
    placed = read_private(root/'.gate/unit-invocation.json')
    if release['owner'] != identity or release['input_root_sha256'] != intent['input_root_sha256']:
        raise ValueError('scope_release_wrong_owner')
    if release['invocation_id'] != placed['invocation_id'] or containment.pid_group(os.getpid()) != placed['control_group']+'/control':
        raise ValueError('scope_release_wrong_invocation_or_group')
    if sorted(os.sched_getaffinity(0)) != [0, 1, 2, 3]:
        raise ValueError('scope_release_affinity_changed')
    if not same_process(intent['controller']) or not same_process(parent) or time.monotonic() >= deadline:
        raise RuntimeError('scope_parent_absent_before_exec')
    os.execve(executable, [executable, *arguments], clean_environment(root))


def await_release_file(path, intent, parent, deadline):
    """Wait under the original idle budget without any application or image work."""
    while not path.exists():
        if not same_process(intent['controller']) or not same_process(parent) or time.monotonic() >= deadline:
            raise RuntimeError('scope_release_absent')
        time.sleep(.01)


def unit_state(manifest, expected_invocation=None):
    """Require one exact newly owned scope and retained invocation, never a reused name."""
    state = containment.unit_properties(manifest['unit'])
    if state.get('Description') != 'allow-warm:' + manifest['input_root_sha256']:
        raise ValueError('scope_root_description_mismatch')
    if expected_invocation is not None and state.get('InvocationID') != expected_invocation:
        raise ValueError('scope_invocation_changed')
    if state.get('KillMode') != 'control-group':
        raise ValueError('scope_kill_mode_mismatch')
    if state.get('Delegate') != 'yes':
        raise ValueError('scope_delegation_required')
    return state


def observe(manifest, owned=()):
    """Verify actual scope limits and every live observed descendant/thread, with explicit supervisor."""
    root = Path(manifest['copied_root'])
    witness = read_private(root/'.gate/unit-invocation.json')
    state = unit_state(manifest, witness['invocation_id'])
    owner = witness['main_identity']
    if not same_process(owner):
        raise ValueError('scope_supervisor_incarnation_changed')
    path = containment.group_path(state)
    limits = {name: (path/name).read_text().strip() for name in containment.EXPECTED}
    if limits != containment.EXPECTED:
        raise ValueError('scope_effective_limits_mismatch')
    group = state['ControlGroup']
    topology = delegation.verify(root, path, owner)
    if containment.pid_group(os.getpid()) == group or containment.pid_group(os.getpid()).startswith(group+'/'):
        raise ValueError('scope_controller_inside_server_group')
    pids = set(containment.members(path)) | {row['pid'] for row in owned if same_process(row)}
    processes = [row for pid in sorted(pids) if (row := containment.process_row(pid, group))]
    if owner['pid'] not in {row['pid'] for row in processes}:
        raise ValueError('scope_supervisor_missing')
    return {'unit': state, 'limits': limits, 'processes': processes, 'supervisor_identity': owner,
            'launch_lane': 'owned_delegated_scope_v1', 'topology': topology,
            'metrics': {name: (path/name).read_text().strip() for name in containment.METRICS if (path/name).exists()},
            'observed_monotonic_ns': time.monotonic_ns()}


def launch(manifest, executable, arguments, seconds):
    """Create a private scope and release the blocked owner only after exact kernel checks."""
    root = Path(manifest['copied_root'])
    if containment.unit_properties(manifest['unit']).get('LoadState') != 'not-found':
        raise ValueError('scope_name_already_exists')
    intent = {'controller': process_identity(os.getpid()), 'input_root_sha256': manifest['input_root_sha256'],
              'security': security(os.getpid()), 'started_monotonic_ns': time.monotonic_ns()}
    write_private(root/'.gate/scope-intent.json', intent)
    argv = ['/usr/bin/taskset', '-c', '0-3', '/usr/bin/systemd-run', '--user', '--scope', '--quiet',
            '--unit='+manifest['unit'], '--description=allow-warm:'+manifest['input_root_sha256']]
    argv.extend('--property='+value for value in properties(seconds))
    environment = clean_environment(root)
    argv.extend(['/usr/bin/env', '-i', *[key+'='+environment[key] for key in sorted(environment)],
                 sys.executable, '-B', str(root/'.gate/scope_launch.py'), '--root', str(root),
                 '--', str(executable), *map(str, arguments)])
    log = os.open(root/'.gate/scope-private.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    child, state, released = None, None, False
    try:
        with os.fdopen(log, 'wb') as stream:
            child = subprocess.Popen(argv, cwd=root, env=containment.user_manager_environment(),
                                     stdout=stream, stderr=stream, umask=0o077)
        state, snapshot = await_placement(root, manifest, child, intent)
        write_private(root/'.gate/scope-placement.json', snapshot)
        write_private(root/'.gate/scope-release.json', {'owner': read_private(root/'.gate/scoped-owner.json')['identity'],
                      'input_root_sha256': manifest['input_root_sha256'], 'invocation_id': state['InvocationID']})
        released = True
        return state, child
    except Exception as error:
        write_private(root/'.gate/scope-launch-failure.json', {'class': type(error).__name__, 'message': str(error)[:1024]})
        raise
    finally:
        if not released:
            failed_cleanup(root, manifest, child, state)


def await_placement(root, manifest, child, intent):
    """Require the blocked owner's exact inherited context and actual in-group thread placement."""
    deadline = time.monotonic() + 5
    while not (root/'.gate/scoped-owner.json').exists():
        if child.poll() is not None or time.monotonic() >= deadline:
            raise ValueError('scope_owner_start_failed')
        time.sleep(.01)
    witness = read_private(root/'.gate/scoped-owner.json')
    if witness['input_root_sha256'] != manifest['input_root_sha256'] or not same_process(witness['identity']):
        raise ValueError('scope_owner_identity_mismatch')
    launcher = process_identity(child.pid)
    direct_exec = witness['identity'] == launcher and witness['parent'] == intent['controller']
    direct_child = witness['parent'] == launcher
    if not (direct_exec or direct_child):
        raise ValueError('scope_owner_parent_not_owned_launcher')
    state = unit_state(manifest)
    write_private(root/'.gate/unit-invocation.json', {'invocation_id': state['InvocationID'],
                  'main_identity': witness['identity'], 'control_group': state['ControlGroup'],
                  'launcher_identity': launcher, 'launch_model': 'direct_exec' if direct_exec else 'direct_child',
                  'launch_started_monotonic_ns': intent['started_monotonic_ns']})
    if witness['security'] != intent['security']:
        raise ValueError('scope_caller_context_changed')
    path = containment.group_path(state)
    if containment.pid_group(witness['identity']['pid']) != state['ControlGroup']:
        raise ValueError('scope_initial_owner_membership')
    if {name: (path/name).read_text().strip() for name in containment.EXPECTED} != containment.EXPECTED:
        raise ValueError('scope_initial_kernel_limits')
    containment.process_row(witness['identity']['pid'], state['ControlGroup'])
    write_private(root/'.gate/scope-configure.json', {'owner': witness['identity'],
                  'input_root_sha256': intent['input_root_sha256']})
    while not (root/'.gate/delegation-ready.json').exists():
        if child.poll() is not None or time.monotonic() >= deadline:
            raise ValueError('delegated_configuration_deadline_or_exit')
        time.sleep(.01)
    snapshot = observe(manifest, [witness['identity']])
    return state, snapshot


def failed_cleanup(root, manifest, child, state):
    """Retain UNKNOWN without a proven invocation; always reap the controller's own launcher."""
    report = {'status': 'UNKNOWN', 'unit': {'status': 'UNKNOWN'}, 'launcher_reaped': child is None}
    try:
        if (root/'.gate/unit-invocation.json').exists():
            witness = read_private(root/'.gate/unit-invocation.json')
            report['unit'] = containment.stop(manifest, [witness['main_identity']], witness['invocation_id'])
    except Exception as error:
        report['unit_failure_class'] = type(error).__name__
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
                report['launcher_reaped'] = True
            except Exception as error:
                report['launcher_failure_class'] = type(error).__name__
    if report['unit']['status'] == 'PASS' and report['launcher_reaped']:
        report['status'] = 'PASS'
    write_private(root/'.gate/scope-failed-cleanup.json', report)


def main():
    """Run only the fixed idle scope gate before the explicit parent release."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args, rest = parser.parse_known_args()
    argv = rest[1:] if rest[:1] == ['--'] else rest
    gated(args.root, argv[0], argv[1:])


if __name__ == '__main__':
    main()
