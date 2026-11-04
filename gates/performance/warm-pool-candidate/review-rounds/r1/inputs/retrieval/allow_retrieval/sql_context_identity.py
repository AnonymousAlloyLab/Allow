"""Private Linux identities used by context leases, never numeric-PID kill authority."""
import os
from pathlib import Path
import socket
import struct


class IdentityUnavailable(ValueError):
    """The kernel identity could not be established without guessing."""


def boot_identity():
    """Return the current Linux boot identity or fail closed."""
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError as failure:
        raise IdentityUnavailable('process_identity_unavailable') from failure


def process_identity(pid):
    """Read an exact process generation; only ENOENT establishes absence."""
    if type(pid) is not int or pid < 1:
        raise IdentityUnavailable('invalid_process_identity')
    try:
        raw = Path('/proc', str(pid), 'stat').read_text()
        parts = raw[raw.rfind(')') + 2:].split()
        return {'bootId': boot_identity(), 'pid': pid, 'startTicks': parts[19],
                'parentPid': int(parts[1]), 'state': parts[0]}
    except FileNotFoundError:
        return None
    except (OSError, ValueError, IndexError) as failure:
        raise IdentityUnavailable('process_identity_unavailable') from failure


def kernel_record(pid):
    """Capture the stable fields needed to observe an observer backend's exit."""
    value = process_identity(pid)
    if value is None:
        raise IdentityUnavailable('process_identity_unavailable')
    return {key: value[key] for key in ('bootId', 'pid', 'startTicks')}


def identity_absent(record):
    """Distinguish positive old-generation absence from unreadable process metadata."""
    if not isinstance(record, dict) or set(record) != {'bootId', 'pid', 'startTicks'}:
        raise IdentityUnavailable('unknown_process_identity')
    if boot_identity() != record['bootId']:
        return True
    current = process_identity(record['pid'])
    return current is None or current['startTicks'] != record['startTicks']


def peer_identity(writer):
    """Read same-UID Unix peer credentials and its stable current process identity."""
    transport = writer.get_extra_info('socket')
    if transport is None:
        raise IdentityUnavailable('peer_identity_unavailable')
    pid, uid, _ = struct.unpack('3i', transport.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    if uid != os.geteuid():
        raise IdentityUnavailable('peer_identity_denied')
    value = process_identity(pid)
    if value is None or value['state'] == 'Z':
        raise IdentityUnavailable('peer_identity_unavailable')
    return value


def owner_record(peer):
    """Capture an application's actual peer and then-parent without caller supplied PIDs."""
    if peer['parentPid'] <= 1:
        raise IdentityUnavailable('parent_identity_unavailable')
    parent = process_identity(peer['parentPid'])
    again = process_identity(peer['pid'])
    if (parent is None or parent['state'] == 'Z' or again is None
            or again['startTicks'] != peer['startTicks'] or again['parentPid'] != parent['pid']):
        raise IdentityUnavailable('parent_identity_unavailable')
    return {'ownerPid': peer['pid'], 'ownerStart': peer['startTicks'],
            'parentPid': parent['pid'], 'parentStart': parent['startTicks']}


def owner_matches(entry, peer):
    """Match a private control caller to the original process generation."""
    return entry['ownerPid'] == peer['pid'] and entry['ownerStart'] == peer['startTicks']


def owner_alive(entry):
    """Require both recorded process generations to remain alive before success."""
    for prefix in ('owner', 'parent'):
        value = process_identity(entry[prefix + 'Pid'])
        if value is None or value['state'] == 'Z' or value['startTicks'] != entry[prefix + 'Start']:
            return False
    return True
