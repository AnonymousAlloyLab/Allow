"""One event-loop owner durably replaces both bounded cleanup reservations together."""
import copy
import json
import os
from pathlib import Path
import stat
import threading
import uuid

MAX_BYTES = 65536
PHASES = {'RESERVED', 'CONNECTING', 'KEYED', 'BOUND', 'RETIRING', 'UNKNOWN', 'CLEAN'}
FIELDS = {'generation', 'leaseGeneration', 'nonce', 'ownerPid', 'ownerStart', 'parentPid',
          'parentStart', 'database', 'user', 'applicationName', 'phase', 'backendPid',
          'backendKey', 'backendStart', 'kernelIdentity', 'failed', 'successPermitted', 'opened'}


class JournalUnavailable(ValueError):
    """Durable ownership cannot be read or updated safely."""


def unique_pairs(pairs):
    """Reject duplicate fields instead of silently losing a prior reservation."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise JournalUnavailable('duplicate_journal_field')
        result[key] = value
    return result


def canonical_uuid(value):
    """Check a canonical UUID without permitting coercion or arbitrary startup tags."""
    return isinstance(value, str) and str(uuid.UUID(value)) == value


def validate_entry(entry, kind):
    """Validate the closed durable schema before an entry can confer ownership."""
    if entry is None:
        return
    if not isinstance(entry, dict) or set(entry) != FIELDS or entry['phase'] not in PHASES:
        raise JournalUnavailable('invalid_journal_entry')
    if not all(canonical_uuid(entry[key]) for key in ('generation', 'nonce')):
        raise JournalUnavailable('invalid_journal_identity')
    if type(entry['leaseGeneration']) is not int or not 1 <= entry['leaseGeneration'] <= 9007199254740991:
        raise JournalUnavailable('invalid_journal_generation')
    for key in ('ownerPid', 'parentPid'):
        if type(entry[key]) is not int or entry[key] < 1:
            raise JournalUnavailable('invalid_journal_owner')
    if any(not isinstance(entry[key], str) or not entry[key].isdigit() for key in ('ownerStart', 'parentStart')):
        raise JournalUnavailable('invalid_journal_owner')
    prefix = 'allow-document-context:' if kind == 'context' else 'allow-context-observer:'
    suffix = entry['nonce'] if kind == 'context' else entry['generation']
    if entry['database'] != 'allow_retrieval' or entry['user'] != 'allow_app' or entry['applicationName'] != prefix + suffix:
        raise JournalUnavailable('invalid_journal_scope')
    if any(type(entry[key]) is not bool for key in ('failed', 'successPermitted', 'opened')):
        raise JournalUnavailable('invalid_journal_flags')
    if entry['successPermitted'] and (entry['failed'] or entry['phase'] != 'CLEAN'):
        raise JournalUnavailable('invalid_journal_success')
    if entry['backendPid'] is not None and (type(entry['backendPid']) is not int or entry['backendPid'] < 1):
        raise JournalUnavailable('invalid_backend_identity')
    if entry['backendKey'] is not None:
        raw = bytes.fromhex(entry['backendKey'])
        if len(raw) != 8 or int.from_bytes(raw[:4], 'big') != entry['backendPid']:
            raise JournalUnavailable('invalid_backend_key')
    if entry['backendStart'] is not None and (not isinstance(entry['backendStart'], str) or not entry['backendStart']):
        raise JournalUnavailable('invalid_backend_start')
    identity = entry['kernelIdentity']
    if identity is not None and (not isinstance(identity, dict) or set(identity) != {'bootId', 'pid', 'startTicks'}
            or identity['pid'] != entry['backendPid'] or not canonical_uuid(identity['bootId'])
            or not isinstance(identity['startTicks'], str) or not identity['startTicks'].isdigit()):
        raise JournalUnavailable('invalid_kernel_identity')
    if entry['phase'] in {'KEYED', 'BOUND'} and entry['backendKey'] is None:
        raise JournalUnavailable('missing_backend_key')
    if entry['phase'] == 'BOUND' and entry['backendStart'] is None:
        raise JournalUnavailable('missing_backend_start')
    has_backend = any(entry[key] is not None for key in ('backendPid', 'backendKey', 'backendStart', 'kernelIdentity'))
    if not entry['opened'] and has_backend:
        raise JournalUnavailable('impossible_unopened_identity')
    if entry['phase'] == 'RESERVED' and (entry['opened'] or has_backend or entry['failed']):
        raise JournalUnavailable('impossible_reserved_phase')
    if entry['phase'] == 'CONNECTING' and (not entry['opened'] or has_backend):
        raise JournalUnavailable('impossible_connecting_phase')
    if entry['phase'] in {'KEYED', 'BOUND'} and (not entry['opened'] or entry['failed']):
        raise JournalUnavailable('impossible_bound_phase')
    if entry['backendStart'] is not None and entry['backendPid'] is None:
        raise JournalUnavailable('incomplete_backend_start')
    if kind == 'context' and entry['kernelIdentity'] is not None:
        raise JournalUnavailable('unexpected_kernel_authority')
    if kind == 'observer' and entry['phase'] in {'KEYED', 'BOUND'} and entry['kernelIdentity'] is None:
        raise JournalUnavailable('missing_observer_identity')
    if entry['phase'] == 'UNKNOWN' and not entry['failed']:
        raise JournalUnavailable('unknown_must_fail_closed')
    if entry['phase'] == 'CLEAN' and entry['opened']:
        required = entry['backendStart'] if kind == 'context' else entry['kernelIdentity']
        if required is None or entry['backendPid'] is None:
            raise JournalUnavailable('uncertified_clean_identity')
    if entry['successPermitted'] and (kind != 'context' or not entry['opened'] or entry['backendKey'] is None):
        raise JournalUnavailable('uncertified_success')


class ContextJournal:
    """Serial, no-await whole-state mutations prevent context/observer lost updates."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'context-state.json'
        self.marker = self.directory / 'context-initialized'
        self.owner = threading.get_ident()
        self.value = {'version': 1, 'counter': 0, 'context': None, 'observer': None}
        self.failed = False
        try:
            self.initialize()
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            self.failed = True

    def private(self, path, directory=False):
        """Require an owned non-symlink private filesystem object."""
        value = path.lstat()
        expected = stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode)
        if not expected or value.st_uid != os.geteuid() or stat.S_IMODE(value.st_mode) != (0o700 if directory else 0o600):
            raise JournalUnavailable('journal_not_private')

    def initialize(self):
        """Load retained state conservatively; initialize journal before the marker."""
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.private(self.directory, True)
        if self.marker.exists() or self.marker.is_symlink():
            self.private(self.marker)
            if not self.path.exists():
                raise JournalUnavailable('initialized_journal_missing')
        if self.path.exists() or self.path.is_symlink():
            self.private(self.path)
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise JournalUnavailable('journal_limit')
            candidate = json.loads(raw, object_pairs_hook=unique_pairs)
            self.validate(candidate)
            self.value = candidate
        else:
            self.write(self.value)
        if not self.marker.exists():
            fd = os.open(self.marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(b'1\n')
                stream.flush()
                os.fsync(stream.fileno())
            self.sync_directory()

    def validate(self, value):
        """Check the entire state so replacing one reservation cannot erase another."""
        if (not isinstance(value, dict) or set(value) != {'version', 'counter', 'context', 'observer'}
                or type(value['version']) is not int or value['version'] != 1):
            raise JournalUnavailable('invalid_journal')
        if type(value['counter']) is not int or not 0 <= value['counter'] <= 9007199254740991:
            raise JournalUnavailable('invalid_journal_counter')
        for kind in ('context', 'observer'):
            validate_entry(value[kind], kind)
            if value[kind] is not None and value[kind]['leaseGeneration'] > value['counter']:
                raise JournalUnavailable('invalid_journal_counter')

    def sync_directory(self):
        """Make rename/marker durability explicit before releasing authority."""
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def write(self, value):
        """Atomically persist one bounded complete state with no asynchronous interleave."""
        if threading.get_ident() != self.owner or self.failed:
            raise JournalUnavailable('journal_owner_unavailable')
        self.validate(value)
        raw = (json.dumps(value, separators=(',', ':'), sort_keys=True) + '\n').encode()
        if len(raw) > MAX_BYTES:
            raise JournalUnavailable('journal_limit')
        temporary = self.directory / ('context-state.' + uuid.uuid4().hex + '.tmp')
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
            self.sync_directory()
            self.value = copy.deepcopy(value)
        except (OSError, ValueError):
            self.failed = True
            raise
        finally:
            temporary.unlink(missing_ok=True)

    def replace(self, kind, entry, *, advance=False):
        """Replace one entry from the latest whole state, never an old worker snapshot."""
        value = copy.deepcopy(self.value)
        value[kind] = copy.deepcopy(entry)
        if advance:
            value['counter'] += 1
        self.write(value)

    def entry(self, kind):
        """Return a copy so callers cannot mutate durable ownership without persistence."""
        return copy.deepcopy(self.value[kind])
