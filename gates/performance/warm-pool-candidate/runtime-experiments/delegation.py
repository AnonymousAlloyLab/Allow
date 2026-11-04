"""Create only the new scope's control leaf and bind its runtime configuration."""
import os
from pathlib import Path
import stat

import containment
from harness_common import packed, read_private, write_private

CONTROLLERS = {'cpu', 'memory', 'pids'}


def identity(path):
    """Bind one canonical owned cgroup directory by device and inode."""
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or path.resolve() != path:
        raise ValueError('delegated_group_ownership_or_alias')
    return {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino}


def require_controllers(path):
    """Require the finite delegated controller subset without modifying ancestors."""
    available = set((path/'cgroup.controllers').read_text().split())
    enabled = set((path/'cgroup.subtree_control').read_text().split())
    if not CONTROLLERS <= available or not CONTROLLERS <= enabled:
        raise ValueError('delegated_controllers_missing')
    return {'available': sorted(available), 'enabled': sorted(enabled)}


def configure(root):
    """Move the sole trusted bootstrap into control before starting any application."""
    manifest = read_private(root/'.gate/manifest.json')
    group = containment.pid_group(os.getpid())
    path = containment.CGROUP/group.lstrip('/')
    if path.name != manifest['unit'] or (path/'cgroup.procs').read_text().split() != [str(os.getpid())]:
        raise ValueError('delegated_bootstrap_not_sole_scope_member')
    if len(list(Path('/proc/self/task').iterdir())) != 1:
        raise ValueError('delegated_bootstrap_not_single_thread')
    if {name: (path/name).read_text().strip() for name in containment.EXPECTED} != containment.EXPECTED:
        raise ValueError('delegated_root_limits_before_application')
    original = identity(path)
    if not CONTROLLERS <= set((path/'cgroup.controllers').read_text().split()):
        raise ValueError('delegated_controllers_unavailable')
    (path/'control').mkdir(mode=0o700)
    (path/'control/cgroup.procs').write_text(str(os.getpid()))
    if (path/'cgroup.procs').read_text().strip() or containment.pid_group(os.getpid()) != group+'/control':
        raise ValueError('delegated_control_move_failed')
    (path/'cgroup.subtree_control').write_text('+cpu +memory +pids')
    topology = {'root': original, 'control': identity(path/'control'), 'controllers': require_controllers(path)}
    config = {'schema': 1, 'cgroupRoot': str(path), 'rootDevice': original['device'], 'rootInode': original['inode']}
    write_private(root/'.runtime/warm-pool/config.json', config)
    (root/'.runtime/warm-pool/journal').mkdir(mode=0o700)
    return topology


def verify(root, path, owner):
    """Require persistent empty root, exact config and owner placement in control."""
    topology = read_private(root/'.gate/delegation-ready.json')
    if identity(path) != topology['root'] or identity(path/'control') != topology['control']:
        raise ValueError('delegated_group_identity_changed')
    if (path/'cgroup.procs').read_text().strip():
        raise ValueError('delegated_root_has_processes')
    if containment.pid_group(owner['pid']) != '/'+str(path.relative_to(containment.CGROUP))+'/control':
        raise ValueError('delegated_supervisor_outside_control')
    expected = {'schema': 1, 'cgroupRoot': str(path), 'rootDevice': topology['root']['device'], 'rootInode': topology['root']['inode']}
    if packed(read_private(root/'.runtime/warm-pool/config.json')) != packed(expected):
        raise ValueError('delegated_config_mismatch')
    controllers = require_controllers(path)
    return dict(topology, controllers=controllers, root_processes=[])
