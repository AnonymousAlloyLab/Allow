"""Independent durable revocation log. Every repository operation holds its lock."""
import contextlib
import fcntl
import json
import os
import uuid
from pathlib import Path
from .common import RUNTIME, canonical, digest, private_write

class Quarantined(RuntimeError):
    pass

class Journal:
    def __init__(self, directory=None):
        self.directory = Path(directory or RUNTIME / 'journal')
        self.path = self.directory / 'revocations.jsonl'

    @contextlib.contextmanager
    def lock(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.is_symlink():
            raise Quarantined('journal_directory_symlink')
        self.directory.chmod(0o700)
        fd = os.open(self.directory / 'journal.lock', os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield self
        finally:
            os.close(fd)

    def initialize(self):
        header = {'seq': 0, 'previous': 'GENESIS', 'journal_id': str(uuid.uuid4()), 'action': 'INITIALIZE'}
        header['hash'] = digest(header)
        private_write(self.path, (canonical(header) + '\n').encode())
        directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def read(self):
        if self.path.is_symlink() or not self.path.is_file():
            raise Quarantined('missing_journal')
        data = self.path.read_bytes()
        if not data.endswith(b'\n') or len(data) > 64 * 1024 * 1024:
            raise Quarantined('truncated_or_oversized_journal')
        previous, events, identity = 'GENESIS', [], None
        try:
            for seq, line in enumerate(data.splitlines()):
                event = json.loads(line)
                claimed = event.pop('hash')
                if event['seq'] != seq or event['previous'] != previous or digest(event) != claimed:
                    raise ValueError('chain')
                if seq == 0:
                    identity = event['journal_id']
                    if event['action'] != 'INITIALIZE':
                        raise ValueError('header')
                elif event.get('journal_id') != identity or event.get('action') not in ('REVOKE_RECORD', 'REVOKE_MODEL'):
                    raise ValueError('action')
                event['hash'] = claimed
                events.append(event)
                previous = claimed
        except (ValueError, KeyError, TypeError) as exc:
            raise Quarantined('corrupt_journal') from exc
        if not events:
            raise Quarantined('empty_journal')
        return events

    def append(self, action, target, tenant, project, reason):
        events = self.read()
        last = events[-1]
        event = {'seq': last['seq'] + 1, 'previous': last['hash'], 'journal_id': last['journal_id'],
                 'action': action, 'target': target, 'tenant': tenant, 'project': project, 'reason': reason}
        event['hash'] = digest(event)
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0))
        try:
            payload = (canonical(event) + '\n').encode()
            if os.write(fd, payload) != len(payload):
                raise Quarantined('journal_partial_write')
            os.fsync(fd)
        finally:
            os.close(fd)
        return event
