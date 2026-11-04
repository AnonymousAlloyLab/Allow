"""Await proxy-owned database cleanup before exposing a validation snapshot.

The private control channel supplies resource receipts, never document authority.
SQL still uses the canonical SQLeanParser connection factory exclusively.
"""
from contextlib import contextmanager
import os
import socket
import stat
import time
import uuid

from allow_retrieval import sql_connections
from . import wire

MAX_CONTROL = 8192
BASE_FIELDS = {'protocol', 'status', 'generation', 'leaseGeneration', 'nonce'}


def canonical_nonce(value):
    """Require a canonical private request UUID before acquiring any resource."""
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('invalid_nonce')
    return value


def control_path():
    """Use only the owned private socket next to the canonical SQL endpoint."""
    path = sql_connections.PROXY_DIRECTORY / 'context.sock'
    for item, mode, predicate in ((path.parent, 0o700, stat.S_ISDIR),
                                   (path, 0o600, stat.S_ISSOCK)):
        info = item.lstat()
        if not predicate(info.st_mode) or stat.S_IMODE(info.st_mode) != mode:
            raise RuntimeError('context_control_unavailable')
        if info.st_uid != os.geteuid():
            raise RuntimeError('context_control_unavailable')
    return path


def exchange(frame):
    """Send one bounded EOF-delimited frame and read one bounded closed reply."""
    raw = wire.encode(frame) + b'\n'
    if len(raw) > MAX_CONTROL:
        raise RuntimeError('context_control_unavailable')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        deadline = time.monotonic() + 8
        stream.settimeout(8)
        stream.connect(str(control_path()))
        stream.sendall(raw)
        stream.shutdown(socket.SHUT_WR)
        chunks, size = [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError('context_control_unavailable')
            stream.settimeout(remaining)
            chunk = stream.recv(min(4096, MAX_CONTROL + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_CONTROL:
                raise RuntimeError('context_control_unavailable')
    return wire.decode(b''.join(chunks), MAX_CONTROL)


def validate_reply(value, nonce, clean=False, registration=None):
    """Bind a success receipt to this peer's registered proxy and lease generation."""
    expected = BASE_FIELDS | ({'successPermitted'} if clean else set())
    if not isinstance(value, dict) or set(value) != expected:
        raise RuntimeError('context_receipt_unavailable')
    if type(value['protocol']) is not int or value['protocol'] != 1:
        raise RuntimeError('context_receipt_unavailable')
    if value['status'] != ('CLEAN' if clean else 'REGISTERED') or value['nonce'] != nonce:
        raise RuntimeError('context_receipt_unavailable')
    try:
        canonical_nonce(value['generation'])
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError('context_receipt_unavailable') from None
    generation = value['leaseGeneration']
    if type(generation) is not int or not 1 <= generation <= 9007199254740991:
        raise RuntimeError('context_receipt_unavailable')
    if clean and type(value['successPermitted']) is not bool:
        raise RuntimeError('context_receipt_unavailable')
    if registration is not None and any(value[key] != registration[key]
                                        for key in ('generation', 'leaseGeneration', 'nonce')):
        raise RuntimeError('context_receipt_unavailable')
    return value


def register(nonce):
    """Acquire an exclusive lease before libpq can open a context backend."""
    canonical_nonce(nonce)
    frame = {'protocol': 1, 'operation': 'register', 'nonce': nonce}
    try:
        return validate_reply(exchange(frame), nonce)
    except Exception:
        raise RuntimeError('context_lease_unavailable') from None


def await_cleanup(registration):
    """Require positive CLEAN evidence; EOF, timeout and UNKNOWN never certify it."""
    frame = {key: registration[key] for key in ('generation', 'leaseGeneration', 'nonce')}
    frame.update(protocol=1, operation='awaitLease')
    try:
        return validate_reply(exchange(frame), registration['nonce'], True, registration)
    except Exception:
        raise RuntimeError('context_cleanup_unavailable') from None


@contextmanager
def connection(nonce, row_factory):
    """Stage caller output until transaction close and its successful cleanup receipt.

On a caller error, cleanup still completes before the original error escapes.
A poisoned CLEAN receipt frees resources but cannot authorize normal success.
"""
    registration = register(nonce)
    completed = False
    current = None
    try:
        current = sql_connections.connect(client='allow-document-context:' + nonce,
                                          row_factory=row_factory)
        yield current
        current.commit()
        completed = True
    finally:
        # Closing a failed read-only connection rolls its transaction back at PG.
        # Do not issue ROLLBACK into a retired channel and overwrite the first error.
        try:
            if current is not None:
                current.close()
        finally:
            receipt = await_cleanup(registration)
        if completed and receipt['successPermitted'] is not True:
            raise RuntimeError('context_validation_retired')
