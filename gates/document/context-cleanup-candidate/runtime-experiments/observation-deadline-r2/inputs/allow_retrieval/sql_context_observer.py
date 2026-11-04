"""One owned blocking libpq thread; observations return to the event-loop journal owner."""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .sql_connections import connect
from .sql_context_protocol import (OBSERVER_IDENTITY_SQL, OBSERVER_RECONCILE_SQL,
                                   OBSERVER_PREFLIGHT_SQL)


class ObserverUnavailable(RuntimeError):
    """The single observer cannot safely accept another operation."""


class ContextObserver:
    """Keep one connection and one pending call, without an unbounded executor queue."""

    def __init__(self, generation):
        self.tag = 'allow-context-observer:' + generation
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='allow-context-observer')
        self.pending = None
        self.connection = None

    async def call(self, method, *arguments, timeout=2.5):
        """Retain a timed-out thread reservation until the actual call finishes."""
        if self.pending is not None and not self.pending.done():
            raise ObserverUnavailable('observer_call_pending')
        if self.pending is not None:
            try:
                self.pending.result()
            except Exception:
                pass
        self.pending = self.executor.submit(method, *arguments)
        future = asyncio.wrap_future(self.pending)
        future.add_done_callback(consume_future)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except Exception:
            raise ObserverUnavailable('observer_unavailable') from None

    def probe(self):
        """Test configured app/database usability before creating an observer reservation."""
        with connect(client='allow-proxy-readiness', autocommit=True) as connection:
            return connection.execute('SELECT 1').fetchone() == (1,)

    def open(self):
        """Create the reserved connection and check settings through its exact SQL prelude."""
        if self.connection is not None:
            raise ObserverUnavailable('observer_already_open')
        self.connection = connect(client=self.tag, autocommit=True)
        self.connection.execute('SET statement_timeout = 500')
        values = self.connection.execute(OBSERVER_PREFLIGHT_SQL).fetchone()
        if not privacy_ready(values):
            raise ObserverUnavailable('observer_preflight_denied')
        pid = self.connection.info.backend_pid
        return self.identity(pid, 'allow_retrieval', 'allow_app', self.tag)

    def identity(self, pid, database, user, application):
        """Return at most two immutable metadata rows, never query text or bind values."""
        if self.connection is None:
            raise ObserverUnavailable('observer_not_open')
        rows = self.connection.execute(OBSERVER_IDENTITY_SQL, (pid, database, user, application)).fetchmany(2)
        return tuple(tuple(str(value) if index == 1 else value for index, value in enumerate(row)) for row in rows)

    def reconcile(self, database, user, application):
        """Look up an incomplete owned identity without granting PID-only authority."""
        if self.connection is None:
            raise ObserverUnavailable('observer_not_open')
        rows = self.connection.execute(OBSERVER_RECONCILE_SQL, (database, user, application)).fetchmany(2)
        return tuple((row[0], str(row[1])) for row in rows)

    def close(self):
        """Close the client transport; the manager separately observes backend exit."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def shutdown(self):
        """Stop new queued calls without pretending a running libpq call has exited."""
        self.executor.shutdown(wait=False, cancel_futures=True)


def privacy_ready(values):
    """Require the reviewed actual capacity and parameter-logging prerequisites."""
    if not isinstance(values, (tuple, list)) or len(values) != 9:
        return False
    maximum, reserved, additional, statement, duration, sample, rate, parameters, errors = values
    try:
        capacity = int(maximum) == 20 and int(reserved) == 3 and int(additional) == 0
        non_error_disabled = statement == 'none' and duration == '-1' and sample == '-1' and float(rate) == 0
        return capacity and int(errors) == 0 and (int(parameters) == 0 or non_error_disabled)
    except (TypeError, ValueError):
        return False


def consume_future(future):
    """Consume late private libpq failures without logging raw exception details."""
    if not future.cancelled():
        future.exception()
