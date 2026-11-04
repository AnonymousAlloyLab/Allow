"""Execution-order tests for the exact private SQL protocol, without a database."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from allow_retrieval.sql_context_protocol import (
    CONTEXT_ISOLATION_SQL, CONTEXT_TIMEOUT_SQL, CONTEXT_SCOPE_SQL,
    CONTEXT_HEAD_SQL, CONTEXT_BASE_SQL, CONTEXT_HISTORY_SQL,
    OBSERVER_TIMEOUT_SQL, OBSERVER_IDENTITY_SQL, OBSERVER_RECONCILE_SQL,
    OBSERVER_PREFLIGHT_SQL, StrictContextProtocol, ContextProtocolError,
    is_context_setting, wire_sql,
)

PREFIX = ('BEGIN', CONTEXT_ISOLATION_SQL, *CONTEXT_TIMEOUT_SQL, *CONTEXT_SCOPE_SQL,
          CONTEXT_HEAD_SQL, CONTEXT_BASE_SQL)


def parse(sql, name=b'', count=0):
    """Construct a complete Parse frame with optional explicit inferred parameter OIDs."""
    return name + b'\0' + wire_sql(sql) + b'\0' + struct.pack('!H', count) + b'\0' * (4 * count)


def bind(count=0, portal=b'', statement=b'', binary=False):
    """Build Bind data whose values must stay uninterpreted by the SQL policy."""
    formats = struct.pack('!HH', 1, 1) if binary else struct.pack('!H', 0)
    values = b''.join(struct.pack('!i', 4) + b'\xff\0;X' for _ in range(count))
    return portal + b'\0' + statement + b'\0' + formats + struct.pack('!H', count) + values + b'\0\0'


def ready(role='context'):
    """Complete only startup, leaving every SQL sequence obligation outstanding."""
    protocol = StrictContextProtocol(role)
    protocol.backend(b'R', b'\0\0\0\0')
    protocol.backend(b'K', b'\0' * 8)
    protocol.backend(b'Z', b'I')
    return protocol


def complete(protocol, sql, extended=False, describe=True, interleaved=False):
    """Drive one legal frontend/backend cycle, retaining an authentic wire order."""
    if extended:
        protocol.frontend(b'P', parse(sql, count=sql.count('%s')))
        if interleaved:
            protocol.backend(b'1', b'')
        protocol.frontend(b'B', bind(sql.count('%s'), binary=True))
        if interleaved:
            protocol.backend(b'2', b'')
        if describe:
            protocol.frontend(b'D', b'P\0')
        protocol.frontend(b'E', b'\0' * 5)
        protocol.frontend(b'S', b'')
        if not interleaved:
            protocol.backend(b'1', b'')
            protocol.backend(b'2', b'')
        if describe:
            protocol.backend(b'T' if sql.startswith('SELECT ') else b'n', b'')
    else:
        protocol.frontend(b'Q', wire_sql(sql) + b'\0')
    command = 'SELECT 0' if sql.startswith('SELECT ') else sql.split(' ', 1)[0]
    protocol.backend(b'C', command.encode() + b'\0')
    idle = sql in ('COMMIT', 'ROLLBACK') or protocol._role == 'observer'
    protocol.backend(b'Z', b'I' if idle else b'T')


class ContextProtocolTests(unittest.TestCase):
    """Prove attack traces fail closed and concrete legal cycles remain admitted."""

    def test_normal_transaction_needs_commit_ready_and_terminate(self):
        for history in (False, True):
            protocol = ready()
            for index, sql in enumerate(PREFIX):
                complete(protocol, sql, extended=index % 2 == 1, interleaved=index % 3 == 1)
            if history:
                complete(protocol, CONTEXT_HISTORY_SQL, extended=True, describe=False)
            protocol.frontend(b'Q', b'COMMIT\0')
            self.assertFalse(protocol.success_ready)
            protocol.backend(b'C', b'COMMIT\0')
            self.assertFalse(protocol.success_ready)
            protocol.backend(b'Z', b'I')
            self.assertTrue(protocol.success_ready)
            self.assertFalse(protocol.terminated_successfully)
            protocol.frontend(b'X', b'')
            self.assertTrue(protocol.terminated_successfully)
            self.assertFalse(protocol.failed)

    def test_startup_ready_is_required_exactly_once(self):
        with self.assertRaises(ContextProtocolError):
            StrictContextProtocol().frontend(b'Q', b'BEGIN\0')
        protocol = ready()
        with self.assertRaises(ContextProtocolError):
            protocol.backend(b'Z', b'I')
        self.assertTrue(protocol.failed)

    def test_parse_does_not_advance_the_sequence(self):
        protocol = ready()
        protocol.frontend(b'P', parse('BEGIN'))
        protocol.backend(b'1', b'')
        with self.assertRaises(ContextProtocolError):
            protocol.frontend(b'P', parse(CONTEXT_ISOLATION_SQL))
        self.assertTrue(protocol.failed)

    def test_no_next_sql_until_ready_even_after_commandcomplete(self):
        protocol = ready()
        protocol.frontend(b'Q', b'BEGIN\0')
        protocol.backend(b'C', b'BEGIN\0')
        with self.assertRaises(ContextProtocolError):
            protocol.frontend(b'Q', wire_sql(CONTEXT_ISOLATION_SQL) + b'\0')

    def test_out_of_order_or_modified_sql_denied(self):
        for sql in (CONTEXT_HEAD_SQL, 'COMMIT', 'BEGIN; SELECT 1', 'BEGIN;',
                    'SET LOCAL statement_timeout = 0', 'SELECT 1', 'COPY documents.artifact TO STDOUT'):
            with self.subTest(sql=sql):
                protocol = ready()
                with self.assertRaises(ContextProtocolError):
                    protocol.frontend(b'Q', wire_sql(sql) + b'\0')
                self.assertTrue(protocol.failed)

    def test_named_objects_and_parameter_mismatch_denied(self):
        attacks = ((b'P', parse('BEGIN', name=b'x')), (b'P', parse('BEGIN', count=1)))
        for kind, body in attacks:
            with self.assertRaises(ContextProtocolError):
                ready().frontend(kind, body)
        for body in (bind(portal=b'x'), bind(statement=b'x'), bind(1), bind() + b'x', b'\0'):
            protocol = ready()
            protocol.frontend(b'P', parse('BEGIN'))
            with self.assertRaises(ContextProtocolError):
                protocol.frontend(b'B', body)

    def test_repeated_bind_and_execute_denied(self):
        for attack in ('bind', 'execute'):
            protocol = ready()
            protocol.frontend(b'P', parse('BEGIN'))
            protocol.frontend(b'B', bind())
            if attack == 'execute':
                protocol.frontend(b'E', b'\0' * 5)
            with self.assertRaises(ContextProtocolError):
                protocol.frontend(b'B' if attack == 'bind' else b'E', bind() if attack == 'bind' else b'\0' * 5)

    def test_sync_order_and_limits(self):
        for kind, body in ((b'S', b''), (b'E', b'\0' + struct.pack('!I', 1)),
                           (b'H', b''), (b'C', b'P\0'), (b'D', b'S\0'),
                           (b'd', b'payload'), (b'Q', b'BEGIN\0')):
            protocol = ready()
            protocol.frontend(b'P', parse('BEGIN'))
            protocol.frontend(b'B', bind())
            with self.subTest(kind=kind, body=body), self.assertRaises(ContextProtocolError):
                protocol.frontend(kind, body)

    def test_omitted_sync_and_repeated_sync_fail(self):
        for omitted in (True, False):
            protocol = ready()
            protocol.frontend(b'P', parse('BEGIN'))
            protocol.frontend(b'B', bind())
            protocol.frontend(b'E', b'\0' * 5)
            protocol.backend(b'1', b'')
            protocol.backend(b'2', b'')
            protocol.backend(b'C', b'BEGIN\0')
            if omitted:
                with self.assertRaises(ContextProtocolError):
                    protocol.backend(b'Z', b'T')
            else:
                protocol.frontend(b'S', b'')
                with self.assertRaises(ContextProtocolError):
                    protocol.frontend(b'S', b'')

    def test_ready_requires_command_and_expected_transaction_state(self):
        for missing_command, status in ((True, b'T'), (False, b'I'), (False, b'E')):
            protocol = ready()
            protocol.frontend(b'Q', b'BEGIN\0')
            if not missing_command:
                protocol.backend(b'C', b'BEGIN\0')
            with self.assertRaises(ContextProtocolError):
                protocol.backend(b'Z', status)

    def test_backend_reorder_copy_and_wrong_completion_denied(self):
        for kind, body in ((b'C', b'COMMIT\0'), (b'2', b''), (b'G', b''),
                           (b's', b''), (b't', b''), (b'I', b'')):
            protocol = ready()
            protocol.frontend(b'P', parse('BEGIN'))
            protocol.frontend(b'B', bind())
            protocol.frontend(b'E', b'\0' * 5)
            protocol.frontend(b'S', b'')
            with self.subTest(kind=kind), self.assertRaises(ContextProtocolError):
                protocol.backend(kind, body)

    def test_error_rollback_and_terminate_never_restore_success(self):
        for extended in (False, True):
            protocol = ready()
            complete(protocol, 'BEGIN')
            protocol.frontend(b'Q', wire_sql(CONTEXT_ISOLATION_SQL) + b'\0')
            protocol.backend(b'E', b'Mprivate_parameter_marker\0\0')
            protocol.backend(b'Z', b'E')
            complete(protocol, 'ROLLBACK', extended=extended)
            protocol.frontend(b'X', b'')
            self.assertTrue(protocol.failed)
            self.assertFalse(protocol.success_ready)
            self.assertFalse(protocol.terminated_successfully)

    def test_external_failure_and_early_terminate_poison_success(self):
        protocol = ready()
        for sql in PREFIX:
            complete(protocol, sql)
        complete(protocol, 'COMMIT')
        protocol.mark_failed()
        protocol.frontend(b'X', b'')
        self.assertFalse(protocol.terminated_successfully)
        protocol = ready()
        protocol.frontend(b'X', b'')
        self.assertTrue(protocol.failed)

    def test_error_messages_do_not_disclose_sql_or_parameters(self):
        protocol = ready()
        with self.assertRaises(ContextProtocolError) as raised:
            protocol.frontend(b'Q', b'SELECT private_parameter_marker\0')
        self.assertNotIn('private_parameter_marker', str(raised.exception))
        self.assertNotIn('SELECT', str(raised.exception))

    def test_no_second_history_or_postcommit_execution(self):
        protocol = ready()
        for sql in (*PREFIX, CONTEXT_HISTORY_SQL):
            complete(protocol, sql)
        with self.assertRaises(ContextProtocolError):
            complete(protocol, CONTEXT_HISTORY_SQL)
        protocol = ready()
        for sql in (*PREFIX, 'COMMIT'):
            complete(protocol, sql)
        with self.assertRaises(ContextProtocolError):
            protocol.frontend(b'Q', b'BEGIN\0')

    def test_observer_requires_own_timeout_and_fixed_metadata_only(self):
        protocol = ready('observer')
        complete(protocol, OBSERVER_TIMEOUT_SQL)
        for index, sql in enumerate((OBSERVER_PREFLIGHT_SQL, OBSERVER_IDENTITY_SQL, OBSERVER_RECONCILE_SQL)):
            complete(protocol, sql, extended=True, interleaved=index % 2 == 0)
        self.assertFalse(protocol.failed)
        self.assertFalse(protocol.success_ready)
        for sql in ('SELECT query FROM pg_stat_activity', CONTEXT_HEAD_SQL, 'BEGIN', OBSERVER_TIMEOUT_SQL):
            candidate = ready('observer')
            complete(candidate, OBSERVER_TIMEOUT_SQL)
            with self.assertRaises(ContextProtocolError):
                complete(candidate, sql)
        with self.assertRaises(ContextProtocolError):
            complete(ready('observer'), OBSERVER_PREFLIGHT_SQL)

    def test_private_settings_helper_has_no_variant_escape(self):
        for sql in (*CONTEXT_TIMEOUT_SQL, OBSERVER_TIMEOUT_SQL):
            self.assertTrue(is_context_setting(sql.encode()))
        for sql in (b'SET statement_timeout = 0', b'SET LOCAL statement_timeout=1500',
                    b'SET LOCAL statement_timeout = 1500;', b'SELECT 1'):
            self.assertFalse(is_context_setting(sql))


if __name__ == '__main__':
    unittest.main()
