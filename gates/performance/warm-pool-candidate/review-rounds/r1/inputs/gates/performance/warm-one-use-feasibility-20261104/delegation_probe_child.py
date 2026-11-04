#!/usr/bin/env python3
"""Bounded infrastructure-only probe inside its new delegated user scope."""
import json
import os
from pathlib import Path
import select
import sys
import time


def save(path, value):
    """Write one private immutable observation."""
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def identity(pid):
    """Read exact Linux PID/start ticks for a live probe incarnation."""
    raw = Path('/proc', str(pid), 'stat').read_text()
    return {'pid': pid, 'start_ticks': raw[raw.rfind(')')+2:].split()[19]}


def main():
    """Create a worker slot, place a pipe-blocked child before exec, reap, prove empty and remove."""
    os.umask(0o077)
    output = Path(sys.argv[1])
    unit = sys.argv[2]
    group_name = Path('/proc/self/cgroup').read_text().strip().split('::')[1]
    if not group_name.endswith('/'+unit):
        raise RuntimeError('unexpected_scope_placement')
    group = Path('/sys/fs/cgroup'+group_name)
    if set(group.joinpath('cgroup.procs').read_text().split()) != {str(os.getpid())}:
        raise RuntimeError('scope_has_unowned_members')
    result = {'status': 'BLOCKED', 'probe_identity': identity(os.getpid()), 'group': str(group),
              'scope_uid': group.stat().st_uid, 'scope_mode': oct(group.stat().st_mode&0o777),
              'controllers': (group/'cgroup.controllers').read_text().strip(),
              'limits': {name:(group/name).read_text().strip() for name in ('cpu.max','memory.max','memory.swap.max','pids.max')}}
    owner, slot = group/'owner', group/'worker'
    owner.mkdir()
    (owner/'cgroup.procs').write_text(str(os.getpid()))
    if (group/'cgroup.procs').read_text().strip():
        raise RuntimeError('delegate_root_not_empty')
    (group/'cgroup.subtree_control').write_text('+cpu +memory +pids')
    slot.mkdir()
    limits = {'cpu.max':'100000 100000','memory.max':'67108864','memory.swap.max':'0','pids.max':'8'}
    for name, value in limits.items():
        (slot/name).write_text(value)
    read_end, write_end = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(write_end)
        if os.read(read_end, 1) != b'x':
            os._exit(91)
        os.close(read_end)
        actual = Path('/proc/self/cgroup').read_text().strip().split('::')[1]
        if actual != group_name+'/worker':
            os._exit(92)
        os.execve('/usr/bin/sleep', ['sleep', '.2'], {'PATH':'/usr/bin:/bin'})
    os.close(read_end)
    child_identity = identity(child)
    (slot/'cgroup.procs').write_text(str(child))
    before_exec = Path('/proc',str(child),'cgroup').read_text().strip()
    result['child_identity'] = child_identity
    result['child_group_before_exec'] = before_exec
    result['slot_limits'] = {name:(slot/name).read_text().strip() for name in limits}
    result['slot_uid'] = slot.stat().st_uid
    result['slot_populated_before_exec'] = (slot/'cgroup.events').read_text().strip()
    save(output/'ready-for-exec.json', result)
    os.write(write_end,b'x')
    os.close(write_end)
    waited, status = os.waitpid(child,0)
    result['child_exit_status'] = status
    result['child_reaped'] = waited == child and not Path('/proc',str(child)).exists()
    result['slot_events_after_reap'] = (slot/'cgroup.events').read_text().strip()
    result['slot_members_after_reap'] = (slot/'cgroup.procs').read_text().strip()
    if status != 0 or 'populated 0' not in result['slot_events_after_reap'] or result['slot_members_after_reap']:
        raise RuntimeError('worker_slot_not_proven_empty')
    slot.rmdir()
    result['slot_deleted_after_positive_empty'] = not slot.exists()
    (group/'cgroup.subtree_control').write_text('-cpu -memory -pids')
    (group/'cgroup.procs').write_text(str(os.getpid()))
    result['owner_events_after_self_move'] = (owner/'cgroup.events').read_text().strip()
    if 'populated 0' not in result['owner_events_after_self_move']:
        raise RuntimeError('owner_subgroup_not_empty')
    owner.rmdir()
    result.update(status='PASS', no_allow_executable_or_model=True, production_or_shared_service_mutation=False)
    save(output/'probe-result.json',result)
    deadline = time.monotonic()+5
    while not (output/'allow-exit').exists() and time.monotonic()<deadline:
        time.sleep(.01)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
