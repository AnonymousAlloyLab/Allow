"""Installation-bound lifetime accounting, reusing the reviewed file ownership lane."""
import json
import os

from allow_ai.journal import DispatchJournal, _MAX_BYTES, _ID, _RESERVATION, _pairs, _secure_file, _validate, _fail
from allow_ai.provider import ProviderFailure


class IntegrationJournal(DispatchJournal):
    """Persist one immutable configured ceiling without resetting prior reservations."""

    def __init__(self, path, *, ceiling=100000, profile='REMOTE_ASSISTED', root=None):
        """Accept a bounded operator ceiling, never a browser-selected budget."""
        if type(ceiling) is not int or not 50000 <= ceiling <= 10000000:
            _fail()
        if profile not in ('FIXTURE', 'REMOTE_ASSISTED'):
            _fail()
        self._ceiling = ceiling
        self._profile = profile
        super().__init__(path, root=root)

    def _read(self, fresh):
        """Read the bound ceiling before exposing the legacy in-memory record shape."""
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
            value = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs)
            return self._checked(value)
        except (ValueError, UnicodeError, RecursionError, TypeError):
            _fail()
        finally:
            os.close(fd)

    def _checked(self, value):
        """Validate each operation independently and enforce the aggregate bound."""
        if type(value) is not dict or set(value) != {'schema', 'ceiling', 'profile', 'operations'}:
            _fail()
        if type(value['schema']) is not int or value['schema'] != 2:
            _fail()
        if type(value['ceiling']) is not int or value['ceiling'] != self._ceiling:
            _fail()
        if value['profile'] != self._profile:
            _fail()
        operations = value['operations']
        if type(operations) is not dict or len(operations) > 1000:
            _fail()
        total = 0
        for name, attempts in operations.items():
            _validate({'schema': 1, 'operations': {name: attempts}})
            total += sum(attempt['reserved'] for attempt in attempts)
        if total > self._ceiling:
            _fail()
        return {'schema': 1, 'operations': operations}

    def _write(self, data):
        """Bind the same configured ceiling in every atomic durable replacement."""
        value = {'schema': 2, 'ceiling': self._ceiling, 'profile': self._profile, 'operations': data['operations']}
        self._checked(value)
        super()._write(value)

    def claim(self, operation_id, attempt):
        """Reserve a consumed attempt before dispatch, including across restarts."""
        self._ready()
        if not isinstance(operation_id, str) or not _ID.fullmatch(operation_id):
            _fail()
        if type(attempt) is not int or attempt not in (1, 2):
            _fail()
        operations = self._state['operations']
        old = operations.get(operation_id, [])
        if attempt == 1 and old or attempt == 2 and (len(old) != 1 or operation_id not in self._active):
            raise ProviderFailure('DISPATCH_REPLAY')
        if attempt == 2 and old[0]['status'] != 'COMPLETED':
            raise ProviderFailure('DISPATCH_REPLAY')
        total = sum(item['reserved'] for items in operations.values() for item in items)
        if total + _RESERVATION > self._ceiling or not old and len(operations) >= 1000:
            raise ProviderFailure('BUDGET_EXHAUSTED')
        record = {'attempt': attempt, 'reserved': _RESERVATION, 'status': 'DISPATCHED'}
        data = {'schema': 1, 'operations': {**operations, operation_id: [*old, record]}}
        self._write(data)
        self._state = data
        self._active.add(operation_id)
