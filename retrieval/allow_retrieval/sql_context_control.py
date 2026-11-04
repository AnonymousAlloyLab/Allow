"""Bounded private lease status transport; it accepts no SQL or process control commands."""
import asyncio
import json
import os
from pathlib import Path
import socket
import stat

from .sql_context_identity import peer_identity
from .sql_context_journal import canonical_uuid, unique_pairs

MAX_FRAME = 8192


def decode_request(raw):
    """Require one bounded closed UTF-8 JSON request and a canonical operation identity."""
    if len(raw) > MAX_FRAME or not raw.endswith(b'\n') or raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('control_frame')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs,
                       parse_constant=invalid_constant)
    if not isinstance(value, dict) or type(value.get('protocol')) is not int or value['protocol'] != 1:
        raise ValueError('control_protocol')
    shapes = {'register': {'protocol', 'operation', 'nonce'},
              'awaitLease': {'protocol', 'operation', 'nonce', 'generation', 'leaseGeneration'},
              'status': {'protocol', 'operation'}}
    if value.get('operation') not in shapes or set(value) != shapes[value['operation']]:
        raise ValueError('control_shape')
    if value['operation'] != 'status' and not canonical_uuid(value['nonce']):
        raise ValueError('control_nonce')
    if value['operation'] == 'awaitLease':
        if not canonical_uuid(value['generation']) or type(value['leaseGeneration']) is not int:
            raise ValueError('control_generation')
        if not 1 <= value['leaseGeneration'] <= 9007199254740991:
            raise ValueError('control_generation')
    return value


def invalid_constant(_):
    """Refuse nonfinite JSON constants without incorporating private input in errors."""
    raise ValueError('control_constant')


async def read_request(reader):
    """Wait for client half-close under one deadline, rejecting a second complete frame."""
    try:
        await reader.readexactly(MAX_FRAME + 1)
    except asyncio.IncompleteReadError as end:
        return decode_request(end.partial)
    raise ValueError('control_frame_limit')


class ContextControl:
    """At most four bounded readers/waiters share the manager's serialized state."""

    def __init__(self, manager, path):
        self.manager, self.path = manager, Path(path)
        self.server = None
        self.handlers = set()

    def remove_stale_socket(self):
        """Remove only a private owned socket whose listener is positively unavailable."""
        if not self.path.exists() and not self.path.is_symlink():
            return
        info = self.path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError('control_socket_not_private')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            try:
                probe.connect(str(self.path))
            except ConnectionRefusedError:
                self.path.unlink()
                return
        raise ValueError('control_socket_already_exists')

    async def start(self):
        """Listen only adjacent to the canonical private SQL socket."""
        self.remove_stale_socket()
        self.server = await asyncio.start_unix_server(self.connected, path=str(self.path), limit=MAX_FRAME)
        self.path.chmod(0o600)

    async def connected(self, reader, writer):
        """Authenticate kernel peer identity before parsing one bounded private request."""
        current = asyncio.current_task()
        if len(self.handlers) >= 4:
            writer.close()
            await writer.wait_closed()
            return
        self.handlers.add(current)
        try:
            peer = peer_identity(writer)
            request = await asyncio.wait_for(read_request(reader), 2)
            result = await self.dispatch(request, peer)
            writer.write((json.dumps(result, separators=(',', ':')) + '\n').encode())
            await asyncio.wait_for(writer.drain(), 2)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, asyncio.TimeoutError):
            pass
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 2)
            except (OSError, asyncio.TimeoutError):
                pass
            self.handlers.discard(current)

    async def dispatch(self, request, peer):
        """Delegate only closed registration, bounded await or aggregate status operations."""
        if request['operation'] == 'status':
            return self.manager.status()
        if request['operation'] == 'register':
            return self.manager.register(request['nonce'], peer)
        return await self.manager.await_receipt(request, peer)

    async def close(self):
        """Stop admission and reap every owned control handler before unlinking the socket."""
        if self.server is not None:
            self.server.close()
        for task in tuple(self.handlers):
            task.cancel()
        await asyncio.gather(*self.handlers, return_exceptions=True)
        if self.server is not None:
            await self.server.wait_closed()
        self.path.unlink(missing_ok=True)
