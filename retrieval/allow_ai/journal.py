"""Content-free, permanently charged dispatch ledger for the isolated harness.

This local filesystem ledger is an operator trust boundary, not a production
cross-installation quota. Its lock must cover the entire network/runner lifetime.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat

from .provider import ProviderFailure

_STATUSES = frozenset({'DISPATCHED', 'COMPLETED', 'VERIFIED', 'INVALID_PROPOSAL',
                      'SCHEMA_INVALID', 'SOURCE_PARSE_INVALID', 'SOURCE_TYPE_INVALID',
                      'SOURCE_PROFILE_INVALID', 'REVIEW_READY', 'FAILED',
                      'OUTCOME_UNKNOWN', 'CANCELLED', 'EXPIRED', 'DENIED'})
_ID = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_FILENAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z')
_MAX_BYTES = 1048576
_RESERVATION = 50000
_CEILING = 100000


def _fail() -> None:
    """Raise a content-free fail-closed accounting outcome."""
    raise ProviderFailure('LEDGER_UNAVAILABLE')


def _pairs(pairs: list[tuple]) -> dict:
    """Reject duplicate keys in persisted state."""
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _secure_file(fd: int) -> None:
    """Require a regular owner-only file without additional hard links."""
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        _fail()
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
        _fail()


def _directory(path: Path) -> int:
    """Walk absolute directories without following any symlink ancestor."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            _fail()
        return fd
    except BaseException:
        os.close(fd)
        raise


def _validate(data: dict) -> None:
    """Check every persisted field before calculating authoritative reservations."""
    if not isinstance(data, dict) or set(data) != {'schema', 'operations'} or type(data['schema']) is not int or data['schema'] != 1:
        _fail()
    operations = data['operations']
    if not isinstance(operations, dict) or len(operations) > 1000:
        _fail()
    total = 0
    for operation, attempts in operations.items():
        if not _ID.fullmatch(operation) or not isinstance(attempts, list) or not 1 <= len(attempts) <= 2:
            _fail()
        for index, attempt in enumerate(attempts, 1):
            if not isinstance(attempt, dict) or set(attempt) != {'attempt', 'reserved', 'status'}:
                _fail()
            if type(attempt['attempt']) is not int or attempt['attempt'] != index:
                _fail()
            if type(attempt['reserved']) is not int or attempt['reserved'] != _RESERVATION:
                _fail()
            if attempt['status'] not in _STATUSES:
                _fail()
            total += attempt['reserved']
    if total > _CEILING:
        _fail()


class DispatchJournal:
    """Serialize an entire runner and preserve reservations through crash/restart."""

    def __init__(self, path: str | Path, *, root: str | Path | None = None):
        """Specify an existing private directory outside the project checkout."""
        self.path = Path(path)
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        self._dir = self._lock = None
        self._state = None
        self._active = set()
        self._poisoned = False

    def __enter__(self):
        """Acquire nonblocking exclusive ownership and validate durable state."""
        if self._dir is not None:
            _fail()
        try:
            if not self.path.is_absolute() or '..' in self.path.parts:
                _fail()
            if self.path == self.root or self.root in self.path.parents:
                _fail()
            if not _FILENAME.fullmatch(self.path.name) or len(str(self.path.parent)) > 1024:
                _fail()
            self._dir = _directory(self.path.parent)
            self._lock, fresh = self._open_lock()
            _secure_file(self._lock)
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._state = self._read(fresh)
            if fresh:
                self._write(self._state)
            return self
        except (OSError, ValueError, TypeError, ProviderFailure):
            self.__exit__(None, None, None)
            _fail()

    def __exit__(self, *_):
        """Release handles only after caller network/runner work has ended."""
        for name in ('_lock', '_dir'):
            fd = getattr(self, name)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)
        self._state = None
        self._active.clear()

    def _open_lock(self) -> tuple[int, bool]:
        """Distinguish initial creation from suspicious removal of existing state."""
        flags = os.O_RDWR | os.O_NOFOLLOW
        try:
            fd = os.open(self.path.name + '.lock', flags | os.O_CREAT | os.O_EXCL,
                         0o600, dir_fd=self._dir)
            os.fsync(self._dir)
            return fd, True
        except FileExistsError:
            return os.open(self.path.name + '.lock', flags, dir_fd=self._dir), False

    def _read(self, fresh: bool) -> dict:
        """Read bounded secure state; absence is the sole initialization condition."""
        try:
            fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self._dir)
        except FileNotFoundError:
            if not fresh:
                _fail()
            return {'schema': 1, 'operations': {}}
        try:
            _secure_file(fd)
            raw = os.read(fd, _MAX_BYTES + 1)
            if len(raw) > _MAX_BYTES:
                _fail()
            data = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs)
            _validate(data)
            return data
        except (ValueError, UnicodeError, RecursionError, TypeError):
            _fail()
        finally:
            os.close(fd)

    def _write(self, data: dict) -> None:
        """Atomically fsync reservations before any caller may dispatch."""
        name = '.ai-ledger-' + secrets.token_hex(12)
        fd = None
        try:
            raw = json.dumps(data, separators=(',', ':'), sort_keys=True).encode('ascii')
            if len(raw) > _MAX_BYTES:
                _fail()
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=self._dir)
            with os.fdopen(fd, 'wb', closefd=False) as target:
                target.write(raw)
                target.flush()
                os.fsync(fd)
            os.rename(name, self.path.name, src_dir_fd=self._dir, dst_dir_fd=self._dir)
            os.fsync(self._dir)
        except (OSError, ValueError, TypeError, ProviderFailure):
            self._poisoned = True
            _fail()
        finally:
            if fd is not None:
                os.close(fd)
            try:
                os.unlink(name, dir_fd=self._dir)
            except FileNotFoundError:
                pass
            except OSError:
                self._poisoned = True
                _fail()

    def claim(self, operation_id: str, attempt: int) -> None:
        """Consume one attempt permanently before opening the provider connection."""
        self._ready()
        if not isinstance(operation_id, str) or not _ID.fullmatch(operation_id):
            _fail()
        if type(attempt) is not int or attempt not in (1, 2):
            _fail()
        operations = self._state['operations']
        old = operations.get(operation_id, [])
        if (attempt == 1 and old) or (attempt == 2 and (len(old) != 1 or operation_id not in self._active)):
            raise ProviderFailure('DISPATCH_REPLAY')
        if attempt == 2 and old[0]['status'] != 'COMPLETED':
            raise ProviderFailure('DISPATCH_REPLAY')
        total = sum(item['reserved'] for items in operations.values() for item in items)
        if total + _RESERVATION > _CEILING or (not old and len(operations) >= 1000):
            raise ProviderFailure('BUDGET_EXHAUSTED')
        record = {'attempt': attempt, 'reserved': _RESERVATION, 'status': 'DISPATCHED'}
        data = {'schema': 1, 'operations': {**operations, operation_id: [*old, record]}}
        self._write(data)
        self._state = data
        self._active.add(operation_id)

    def finish(self, operation_id: str, attempt: int, status: str) -> None:
        """Store a sanitized terminal observation without ever refunding spend."""
        self._ready()
        if not isinstance(status, str) or status not in _STATUSES:
            _fail()
        operations = self._state['operations']
        old = operations.get(operation_id)
        if operation_id not in self._active or not old or type(attempt) is not int or attempt != len(old):
            _fail()
        records = [dict(item) for item in old]
        records[-1]['status'] = status
        data = {'schema': 1, 'operations': {**operations, operation_id: records}}
        self._write(data)
        self._state = data

    def _ready(self) -> None:
        """Deny use outside the exclusively owned, healthy context."""
        if self._dir is None or self._lock is None or self._state is None or self._poisoned:
            _fail()
