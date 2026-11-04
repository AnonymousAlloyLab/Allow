"""Fixed read-only SQL and execution fences for private context/observer sessions.

ParserGate and the general ProtocolState remain mandatory independent gates.
This module validates ordering and exact templates; it does not observe cleanup,
authenticate ownership, inspect parameter values, or certify kernel/SQL absence.
"""
import re
import struct


CONTEXT_ISOLATION_SQL = 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'
CONTEXT_TIMEOUT_SQL = (
    'SET LOCAL statement_timeout = 1500',
    'SET LOCAL lock_timeout = 250',
    'SET LOCAL idle_in_transaction_session_timeout = 1000',
)
CONTEXT_SCOPE_SQL = (
    "SELECT set_config('allow.tenant',%s,true)",
    "SELECT set_config('allow.project',%s,true)",
    "SELECT set_config('allow.purpose',%s,true)",
)
CONTEXT_HEAD_SQL = 'SELECT head_revision FROM documents.document WHERE document_id=%s'
CONTEXT_BASE_SQL = (
    'SELECT r.revision,r.target_revision,r.direction,a.content FROM documents.revision r '
    'JOIN documents.artifact a USING(principal_id,workspace_id,document_id,artifact_id) '
    'WHERE r.document_id=%s AND r.revision=%s'
)
CONTEXT_HISTORY_SQL = 'SELECT content FROM documents.artifact WHERE document_id=%s'
OBSERVER_TIMEOUT_SQL = 'SET statement_timeout = 500'
OBSERVER_IDENTITY_SQL = (
    'SELECT pid, backend_start, datname, usename, application_name FROM pg_catalog.pg_stat_activity '
    'WHERE pid = %s AND datname = %s AND usename = %s AND application_name = %s'
)
# Observation callers fetch at most two rows and reject ambiguity. PostgreSQL's
# verified max_connections bounds this metadata; these exact reviewed templates
# deliberately do not claim a server-side LIMIT or streaming row bound.
OBSERVER_RECONCILE_SQL = (
    'SELECT pid, backend_start FROM pg_catalog.pg_stat_activity '
    'WHERE datname = %s AND usename = %s AND application_name = %s'
)
OBSERVER_PREFLIGHT_SQL = (
    "SELECT current_setting('max_connections'),current_setting('superuser_reserved_connections'),"
    "current_setting('reserved_connections'),current_setting('log_statement'),"
    "current_setting('log_min_duration_statement'),current_setting('log_min_duration_sample'),"
    "current_setting('log_transaction_sample_rate'),current_setting('log_parameter_max_length'),"
    "current_setting('log_parameter_max_length_on_error')"
)


def wire_sql(template):
    """Translate only our constant psycopg placeholders to exact numbered SQL bytes."""
    parts = template.split('%s')
    return ''.join(part + (f'${i + 1}' if i < len(parts) - 1 else '')
                   for i, part in enumerate(parts)).encode('ascii')


_CONTEXT_PREFIX = tuple(wire_sql(sql) for sql in (
    'BEGIN', CONTEXT_ISOLATION_SQL, *CONTEXT_TIMEOUT_SQL, *CONTEXT_SCOPE_SQL,
    CONTEXT_HEAD_SQL, CONTEXT_BASE_SQL,
))
_HISTORY = wire_sql(CONTEXT_HISTORY_SQL)
_OBSERVER_QUERIES = frozenset(wire_sql(sql) for sql in (
    OBSERVER_IDENTITY_SQL, OBSERVER_RECONCILE_SQL, OBSERVER_PREFLIGHT_SQL,
))
_SETTINGS = frozenset(wire_sql(sql) for sql in (*CONTEXT_TIMEOUT_SQL, OBSERVER_TIMEOUT_SQL))


class ContextProtocolError(ValueError):
    """Content-free rejection of a private session's SQL or execution ordering."""


def is_context_setting(sql):
    """Identify the newly admitted exact settings which ordinary sessions must deny."""
    return isinstance(sql, bytes) and sql in _SETTINGS


def _field(body, offset=0):
    """Read one wire string without interpreting bound data or emitting its contents."""
    end = body.find(b'\0', offset)
    if end < 0:
        raise ContextProtocolError('context_frame_invalid')
    return body[offset:end], end + 1


def _count(body, offset):
    """Read a bounded unsigned16 count with no partial-frame fallback."""
    if offset + 2 > len(body):
        raise ContextProtocolError('context_frame_invalid')
    return struct.unpack_from('!H', body, offset)[0], offset + 2


def _formats(body, offset):
    """Validate format codes and return their count and the next byte offset."""
    count, offset = _count(body, offset)
    for _ in range(count):
        value, offset = _count(body, offset)
        if value not in (0, 1):
            raise ContextProtocolError('context_frame_invalid')
    return count, offset


def _bind_count(body):
    """Require unnamed objects and well-formed opaque text/binary Bind parameters."""
    portal, offset = _field(body)
    statement, offset = _field(body, offset)
    if portal or statement:
        raise ContextProtocolError('context_named_object')
    formats, offset = _formats(body, offset)
    count, offset = _count(body, offset)
    if formats not in (0, 1, count):
        raise ContextProtocolError('context_frame_invalid')
    for _ in range(count):
        if offset + 4 > len(body):
            raise ContextProtocolError('context_frame_invalid')
        size = struct.unpack_from('!i', body, offset)[0]
        offset += 4
        if size < -1 or offset + max(size, 0) > len(body):
            raise ContextProtocolError('context_frame_invalid')
        offset += max(size, 0)
    _, offset = _formats(body, offset)
    if offset != len(body):
        raise ContextProtocolError('context_frame_invalid')
    return count


class StrictContextProtocol:
    """Allow one fully executed fixed statement per backend Ready cycle."""

    def __init__(self, role='context'):
        """Initialize a private role without admitting any SQL before startup Ready."""
        if role not in ('context', 'observer'):
            raise ContextProtocolError('context_role_invalid')
        self._role = role
        self._failed = False
        self._started = False
        self._terminated = False
        self._terminated_successfully = False
        self._committed = False
        self._cursor = 0
        self._observer_configured = False
        self._phase = 'startup'
        self._reset_cycle()

    @property
    def failed(self):
        """Expose sticky failure without allowing callers to clear a poisoned session."""
        return self._failed

    @property
    def success_ready(self):
        """Report confirmed successful COMMIT, before or after normal Terminate."""
        return self._committed and not self._failed

    @property
    def terminated_successfully(self):
        """Report Terminate only when preceded by the complete successful transaction."""
        return self._terminated_successfully and not self._failed

    def mark_failed(self):
        """Poison the generation after external parser, ownership, or deadline failure."""
        self._failed = True

    def _deny(self, code='context_sequence_invalid'):
        """Make every protocol denial sticky and expose no SQL or parameter content."""
        self.mark_failed()
        raise ContextProtocolError(code)

    def _reset_cycle(self):
        """Clear only per-statement acknowledgments, retaining session failure state."""
        self._sql = None
        self._extended = False
        self._parsed = False
        self._bound = False
        self._described = False
        self._description_seen = False
        self._command = False
        self._error = False
        self._parameters = 0

    def frontend(self, kind, body):
        """Validate every post-authentication frontend frame before it is forwarded."""
        try:
            self._frontend(kind, body)
        except (ContextProtocolError, ValueError, struct.error, TypeError):
            self._deny()

    def _frontend(self, kind, body):
        """Apply a closed frontend alphabet with a single pending execution cycle."""
        if self._terminated or not isinstance(body, bytes):
            self._deny()
        if kind == b'X':
            if body:
                self._deny()
            self._terminated_successfully = self.success_ready and self._phase == 'idle'
            self._terminated = True
            if not self._terminated_successfully:
                self.mark_failed()
            return
        if not self._started or self._committed:
            self._deny()
        if kind in (b'Q', b'P'):
            self._request(kind, body)
        elif (kind == b'S' and self._failed and self._extended and not body
              and self._phase in ('parse', 'bind', 'describe', 'execute')):
            self._phase = 'waiting'
        elif self._failed and self._sql != b'ROLLBACK':
            self._deny()
        else:
            self._control(kind, body)

    def _request(self, kind, body):
        """Match exact SQL at idle without advancing the expected execution cursor."""
        if self._phase != 'idle':
            self._deny()
        offset = 0
        if kind == b'P':
            name, offset = _field(body)
            if name:
                self._deny('context_named_object')
        sql, offset = _field(body, offset)
        parameters = len(re.findall(rb'\$[1-9][0-9]*', sql))
        if kind == b'P':
            count, offset = _count(body, offset)
            if count not in (0, parameters) or offset + count * 4 != len(body):
                self._deny()
        elif offset != len(body):
            self._deny()
        self._allow_sql(sql)
        self._reset_cycle()
        self._sql, self._parameters = sql, parameters
        self._extended = kind == b'P'
        self._phase = 'parse' if self._extended else 'waiting'

    def _allow_sql(self, sql):
        """Require the fixed transaction prelude and exact scoped read templates."""
        if self._role == 'context' and sql == b'ROLLBACK':
            self.mark_failed()
            return
        if self._failed:
            self._deny()
        if self._role == 'observer':
            allowed = _OBSERVER_QUERIES if self._observer_configured else {wire_sql(OBSERVER_TIMEOUT_SQL)}
        elif self._cursor < len(_CONTEXT_PREFIX):
            allowed = {_CONTEXT_PREFIX[self._cursor]}
        elif self._cursor == len(_CONTEXT_PREFIX):
            allowed = {_HISTORY, b'COMMIT'}
        else:
            allowed = {b'COMMIT'}
        if sql not in allowed:
            self._deny('context_sql_denied')

    def _control(self, kind, body):
        """Require one Bind, optional portal Describe, unlimited Execute, then Sync."""
        if kind == b'B' and self._phase == 'parse':
            if _bind_count(body) != self._parameters:
                self._deny()
            self._phase = 'bind'
        elif kind == b'D' and self._phase == 'bind' and body == b'P\0':
            self._described = True
            self._phase = 'describe'
        elif kind == b'E' and self._phase in ('bind', 'describe') and body == b'\0\0\0\0\0':
            self._phase = 'execute'
        elif kind == b'S' and self._phase == 'execute' and not body:
            self._phase = 'waiting'
        else:
            self._deny()

    def backend(self, kind, body):
        """Advance only on actual CommandComplete followed by the expected Ready."""
        try:
            self._backend(kind, body)
        except (ContextProtocolError, ValueError, struct.error, TypeError):
            self._deny()

    def _backend(self, kind, body):
        """Track acknowledgments while allowing trusted authentication/status frames."""
        if self._terminated or not isinstance(body, bytes):
            self._deny()
        if kind == b'E':
            self.mark_failed()
            self._error = True
            return
        if not self._started:
            self._startup(kind, body)
        elif kind in (b'N', b'S'):
            return
        elif kind == b'Z':
            self._ready(body)
        elif self._sql is None or self._error:
            self._deny()
        elif kind in (b'1', b'2', b'T', b'n', b'D'):
            self._result(kind, body)
        elif kind == b'C':
            self._complete(body)
        else:
            self._deny()

    def _startup(self, kind, body):
        """Accept exactly one initial idle Ready before any application statement."""
        if kind == b'Z' and body == b'I' and not self._failed:
            self._started, self._phase = True, 'idle'
        elif kind not in (b'R', b'S', b'K', b'N'):
            self._deny()

    def _result(self, kind, body):
        """Check acknowledgment order independently of asynchronously sent frames."""
        if self._command:
            self._deny()
        if kind == b'1':
            if not self._extended or self._parsed or body:
                self._deny()
            self._parsed = True
        elif kind == b'2':
            if not self._parsed or self._bound or self._phase == 'parse' or body:
                self._deny()
            self._bound = True
        elif self._extended and not self._bound:
            self._deny()
        elif kind in (b'T', b'n'):
            if self._description_seen or (self._extended and not self._described):
                self._deny()
            if kind == b'n' and (body or not self._extended):
                self._deny()
            self._description_seen = True
        elif not self._sql.startswith(b'SELECT ') or self._phase not in ('execute', 'waiting'):
            self._deny()

    def _complete(self, body):
        """Bind one backend completion tag to the exact admitted executing statement."""
        if self._command or self._phase not in ('execute', 'waiting'):
            self._deny()
        if self._extended and not (self._parsed and self._bound):
            self._deny()
        command = self._sql.split(b' ', 1)[0]
        valid = (re.fullmatch(rb'SELECT [0-9]+\x00', body) is not None
                 if command == b'SELECT' else body == command + b'\0')
        if not valid:
            self._deny()
        self._command = True

    def _ready(self, body):
        """Complete a cycle only after Sync/Q and the proper transaction status."""
        if self._phase != 'waiting' or body not in (b'I', b'T', b'E'):
            self._deny()
        if not self._error:
            expected = b'I' if self._role == 'observer' or self._sql in (b'COMMIT', b'ROLLBACK') else b'T'
            if not self._command or body != expected:
                self._deny()
            if not self._failed:
                self._advance()
        self._reset_cycle()
        self._phase = 'idle'

    def _advance(self):
        """Record a completed statement, never mere Parse or frontend execution intent."""
        if self._role == 'observer':
            self._observer_configured = True
        elif self._sql == b'COMMIT':
            self._committed = True
        else:
            self._cursor += 1
