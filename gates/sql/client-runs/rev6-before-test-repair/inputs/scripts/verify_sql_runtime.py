#!/usr/bin/env python3
"""Run finite SQL proxy wire and real PostgreSQL checks; skips never pass.

Invoke only after the canonical owned proxy and migrated database are running.
No source SQL, parameters or DSNs are included in the machine-readable report.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'retrieval'))
sys.path.insert(0, str(ROOT / 'retrieval/tests'))


class RealProxyTests(unittest.TestCase):
    """Real execution is separate from the independent synthetic wire peer."""
    def connect(self, autocommit=False):
        from allow_retrieval.sql_connections import connect, PROXY_DIRECTORY
        connection = connect(client='allow-tests', autocommit=autocommit)
        self.addCleanup(connection.close)
        self.assertEqual(Path(connection.info.host).resolve(),
                         PROXY_DIRECTORY.resolve(),
                         'real check bypassed the canonical owned proxy endpoint')
        return connection

    def test_bound_text_binary_and_implicit_transaction(self):
        connection = self.connect()
        authored = "'); SELECT set_config('client_encoding','SQL_ASCII',false); --"
        binary = b'\0\xffSQL\0\x80'
        self.assertEqual(connection.execute('SELECT %s::text, %s::bytea',
                                            (authored, binary)).fetchone(), (authored, binary))
        self.assertEqual(connection.info.transaction_status.name, 'INTRANS')
        connection.commit()
        self.assertEqual(connection.info.transaction_status.name, 'IDLE')
        connection.execute('SELECT 1')
        connection.rollback()
        self.assertEqual(connection.info.transaction_status.name, 'IDLE')
        self.assertEqual(connection.execute('SHOW client_encoding').fetchone()[0], 'UTF8')
        self.assertEqual(connection.execute('SHOW standard_conforming_strings').fetchone()[0], 'on')

    def test_real_prepared_statement_repeated_bindings(self):
        connection = self.connect()
        for value in ('first', 'second', 'third'):
            self.assertEqual(connection.execute('SELECT %s::text', (value,), prepare=True).fetchone(),
                             (value,))
        connection.commit()
        self.assertEqual(connection.execute('SELECT %s::text', ('after commit',), prepare=True).fetchone(),
                         ('after commit',))

    def test_native_prepare_execute_crosses_protocol_namespace_both_directions(self):
        from psycopg.pq import ExecStatus
        connection = self.connect(autocommit=True)
        backend = connection.pgconn
        self.assertEqual(backend.exec_(b'PREPARE NativeMix(int) AS SELECT $1 + 1').status,
                         ExecStatus.COMMAND_OK)
        native = backend.exec_(b'EXECUTE nativemix(40)')
        self.assertEqual(native.status, ExecStatus.TUPLES_OK)
        self.assertEqual(native.get_value(0, 0), b'41')
        bound = backend.exec_prepared(b'nativemix', [b'41'])
        self.assertEqual(bound.status, ExecStatus.TUPLES_OK)
        self.assertEqual(bound.get_value(0, 0), b'42')
        self.assertEqual(backend.prepare(b'from_protocol', b'SELECT $1::integer + 2', [23]).status,
                         ExecStatus.COMMAND_OK)
        executed = backend.exec_(b'EXECUTE from_protocol(40)')
        self.assertEqual(executed.status, ExecStatus.TUPLES_OK)
        self.assertEqual(executed.get_value(0, 0), b'42')

    def test_native_cache_cannot_create_target_in_new_connection(self):
        from psycopg.pq import ExecStatus, DiagnosticField
        connection = self.connect(autocommit=True)
        self.assertEqual(connection.pgconn.exec_(b'PREPARE cached AS SELECT 17').status,
                         ExecStatus.COMMAND_OK)
        self.assertEqual(connection.pgconn.exec_(b'EXECUTE cached').status, ExecStatus.TUPLES_OK)
        fresh = self.connect(autocommit=True)
        denied = fresh.pgconn.exec_(b'EXECUTE cached')
        self.assertEqual(denied.status, ExecStatus.FATAL_ERROR)
        self.assertEqual(denied.error_field(DiagnosticField.SQLSTATE), b'42601')

    def test_native_invalid_names_wrappers_and_expressions_denied(self):
        from psycopg.pq import ExecStatus, DiagnosticField
        sources = (b'PREPARE "quoted" AS SELECT 1',
                   b'PREPARE ' + b'a' * 64 + b' AS SELECT 1',
                   b'PREPARE s AS SELECT 1; SELECT 2',
                   b'EXECUTE s; EXECUTE s', b'EXPLAIN EXECUTE s',
                   b'CREATE TEMP TABLE t AS EXECUTE s',
                   b"PREPARE s AS SELECT set_config('client_encoding','SQL_ASCII',false)",
                   b"EXECUTE s(set_config('standard_conforming_strings','off',false))")
        for source in sources:
            with self.subTest(source=source):
                connection = self.connect(autocommit=True)
                rejected = connection.pgconn.exec_(source)
                self.assertEqual(rejected.status, ExecStatus.FATAL_ERROR)
                self.assertEqual(rejected.error_field(DiagnosticField.SQLSTATE), b'42601')

    def test_native_capacity_256_accepts_then_denies_257(self):
        from psycopg.pq import ExecStatus, DiagnosticField
        connection = self.connect(autocommit=True)
        for index in range(256):
            query = ('PREPARE s' + str(index) + ' AS SELECT 1').encode()
            self.assertEqual(connection.pgconn.exec_(query).status, ExecStatus.COMMAND_OK)
        overflow = connection.pgconn.exec_(b'PREPARE overflow AS SELECT 1')
        self.assertEqual(overflow.status, ExecStatus.FATAL_ERROR)
        self.assertEqual(overflow.error_field(DiagnosticField.SQLSTATE), b'42601')

    def test_real_protocol_statement_portal_63_byte_boundaries(self):
        import os
        import socket
        import test_sql_proxy as wire
        prefix = 's' * 63
        cases = (wire.parse('SELECT 2;', prefix + 'x'),
                 wire.bind('p' * 64, prefix), wire.execute('p' * 64),
                 wire.packet(b'C', b'S' + wire.cstring(prefix + 'x')),
                 wire.packet(b'D', b'P' + wire.cstring('p' * 64)))
        for authored in cases:
            with self.subTest(frame=authored[:20]):
                connection = self.connect(autocommit=True)
                stream = socket.socket(fileno=os.dup(connection.pgconn.socket))
                self.addCleanup(stream.close)
                stream.settimeout(8)
                stream.sendall(wire.packet(b'Q', wire.cstring('BEGIN')))
                wire.until(stream)
                stream.sendall(wire.parse('SELECT 1;', prefix))
                self.assertEqual(wire.receive(stream)[0], b'1')
                stream.sendall(wire.packet(b'S'))
                wire.until(stream)
                stream.sendall(wire.bind('p' * 63, prefix))
                self.assertEqual(wire.receive(stream)[0], b'2')
                stream.sendall(wire.execute('p' * 63) + wire.packet(b'S'))
                response = wire.until(stream)
                self.assertIn(b'C', [kind for kind, _ in response])
                stream.sendall(authored)
                try:
                    while True:
                        kind, _ = wire.receive(stream)
                        self.assertEqual(kind, b'E', 'overlong name returned success')
                except (EOFError, ConnectionResetError):
                    pass

    def test_failed_native_prepare_never_becomes_successful_execution(self):
        import psycopg
        from psycopg.pq import ExecStatus
        connection = self.connect(autocommit=True)
        failed = connection.pgconn.exec_(b'PREPARE failed AS SELECT authored_missing_column')
        self.assertEqual(failed.status, ExecStatus.FATAL_ERROR)
        try:
            executed = connection.pgconn.exec_(b'EXECUTE failed')
            self.assertEqual(executed.status, ExecStatus.FATAL_ERROR)
        except psycopg.Error:
            self.assertTrue(connection.closed)

    def test_indirect_pg_settings_change_closes_isolated_session(self):
        import psycopg
        from psycopg.pq import ExecStatus, DiagnosticField
        connection = self.connect(autocommit=True)
        changed = connection.pgconn.exec_(
            b"UPDATE pg_catalog.pg_settings SET setting='off' WHERE name='standard_conforming_strings'")
        self.assertEqual(changed.status, ExecStatus.FATAL_ERROR)
        self.assertEqual(changed.error_field(DiagnosticField.SQLSTATE), b'42601')
        try:
            subsequent = connection.pgconn.exec_(b"SELECT 'authored later query'")
            self.assertEqual(subsequent.status, ExecStatus.FATAL_ERROR)
        except psycopg.Error:
            self.assertTrue(connection.closed)
        safe = self.connect(autocommit=True)
        self.assertEqual(safe.execute('SHOW standard_conforming_strings').fetchone(), ('on',))

    def test_real_copy_roundtrip(self):
        connection = self.connect()
        connection.execute('CREATE TEMP TABLE allow_copy_fixture(value text)')
        authored = "SELECT 'SQL-looking COPY data';\tUnicode \u03bb\nsecond line"
        with connection.cursor().copy('COPY allow_copy_fixture(value) FROM STDIN') as writer:
            writer.write_row((authored,))
        self.assertEqual(connection.execute('SELECT value FROM allow_copy_fixture').fetchone(), (authored,))
        with connection.cursor().copy('COPY (SELECT value FROM allow_copy_fixture) TO STDOUT') as reader:
            rows = list(reader.rows())
        self.assertEqual(rows, [(authored.encode(),)])
        connection.rollback()

    def test_invalid_grammar_fails_and_safe_new_session_works(self):
        import psycopg
        connection = self.connect(autocommit=True)
        with self.assertRaises(psycopg.Error):
            connection.execute('SELEC 1')
        with self.assertRaises(psycopg.Error):
            connection.execute('SELECT 2')
        self.assertEqual(self.connect().execute('SELECT 3').fetchone(), (3,))

    def test_mode_change_pipeline_fails_before_following_query(self):
        import psycopg
        connection = self.connect(autocommit=True)
        with self.assertRaises(psycopg.Error):
            with connection.pipeline():
                connection.execute('SET standard_conforming_strings=off')
                connection.execute('SELECT 99')
        safe = self.connect()
        self.assertEqual(safe.execute('SHOW standard_conforming_strings').fetchone(), ('on',))
        self.assertEqual(safe.execute('SHOW client_encoding').fetchone(), ('UTF8',))

    def test_real_cancellation_interrupts_pg_sleep(self):
        import psycopg
        connection = self.connect(autocommit=True)
        observer = self.connect(autocommit=True)
        pid = connection.execute('SELECT pg_backend_pid()').fetchone()[0]
        outcome = []
        started = threading.Event()

        def sleepy():
            started.set()
            try:
                connection.execute('SELECT pg_sleep(6)')
                outcome.append('completed')
            except psycopg.errors.QueryCanceled:
                outcome.append('cancelled')
            except psycopg.Error:
                outcome.append('connection_error')

        thread = threading.Thread(target=sleepy, daemon=True)
        thread.start()
        self.assertTrue(started.wait(1))
        deadline = time.monotonic() + 4
        sleeping = False
        while time.monotonic() < deadline and thread.is_alive():
            row = observer.execute('SELECT wait_event FROM pg_stat_activity WHERE pid=%s', (pid,)).fetchone()
            if row and row[0] == 'PgSleep':
                sleeping = True
                break
            time.sleep(.03)
        try:
            self.assertTrue(sleeping, 'sleep never reached PostgreSQL')
            connection.cancel()
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive(), 'CancelRequest did not interrupt sleep')
            self.assertEqual(outcome, ['cancelled'])
            self.assertEqual(connection.execute('SELECT 1').fetchone(), (1,))
        finally:
            if thread.is_alive():
                connection.cancel()
                thread.join(timeout=7)


def fingerprint():
    """Bind authored proxy checks, implementation, policy, lock and parser identity."""
    paths = [Path(__file__), ROOT / 'retrieval/tests/test_sql_proxy.py',
             ROOT / 'spec/sql-stage.json', ROOT / 'config/sqlean-parser-lock.json']
    paths += list((ROOT / 'retrieval/allow_retrieval').glob('sql*.py'))
    files = [{'path': str(p.relative_to(ROOT)),
              'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(paths))]
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return files, digest


def read_status(path):
    """Treat missing or malformed daemon status as stale evidence, never a pass."""
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or not isinstance(value.get('clients'), dict):
            return {}
        return value
    except (OSError, ValueError):
        return {}


def runtime_identity(status, previous=None):
    """Bind startup-loaded sources and executable identity to current reviewed bytes."""
    reasons = []
    names = ('retrieval/allow_retrieval/sql_proxy.py',
             'retrieval/allow_retrieval/sql_guard.py', 'config/sqlean-parser-lock.json')
    expected_inputs = {}
    expected_binary = actual_binary = None
    try:
        expected_inputs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                           for name in names}
        lock = json.loads((ROOT / 'config/sqlean-parser-lock.json').read_text())
        expected_binary = lock['binary_sha256']
        actual_binary = hashlib.sha256((ROOT / '.tools/sqlean/sqlean_pg_grammar').read_bytes()).hexdigest()
        if actual_binary != expected_binary:
            reasons.append('parser_binary_not_locked')
        parser = status.get('parser', {})
        if not isinstance(parser, dict) or parser.get('binary_sha256') != expected_binary:
            reasons.append('daemon_parser_identity_mismatch')
        if not isinstance(parser, dict) or parser.get('profile') != lock.get('profile'):
            reasons.append('daemon_parser_profile_mismatch')
    except (OSError, ValueError, KeyError, TypeError):
        reasons.append('runtime_identity_input_unavailable')
    if status.get('loaded_inputs') != expected_inputs or not expected_inputs:
        reasons.append('daemon_loaded_inputs_mismatch')
    pid = status.get('pid')
    if type(pid) is not int or pid <= 0:
        reasons.append('invalid_daemon_pid')
    if previous is not None:
        if pid != previous.get('pid'):
            reasons.append('daemon_pid_changed')
        if status.get('started') != previous.get('started'):
            reasons.append('daemon_start_identity_changed')
    return {'status': 'STALE_RUNTIME' if reasons else 'PASS', 'reasons': reasons,
            'pid': pid, 'expected_loaded_inputs': expected_inputs,
            'expected_parser_binary_sha256': expected_binary,
            'actual_parser_binary_sha256': actual_binary}


def main():
    """Reject stale daemons before tests and bind passing evidence to a stable process."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'gates/sql/runtime-tests.json')
    args = parser.parse_args()
    files, before = fingerprint()
    counters_before = read_status(args.status)
    identity_before = runtime_identity(counters_before)
    log = io.StringIO()
    if identity_before['status'] == 'PASS':
        import test_sql_proxy
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(test_sql_proxy),
            unittest.defaultTestLoader.loadTestsFromTestCase(RealProxyTests)])
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    else:
        result = unittest.TestResult()
        log.write('STALE_RUNTIME: daemon identity preflight failed; no tests executed.\n')
    _, after = fingerprint()
    counters_after = read_status(args.status)
    identity_after = runtime_identity(counters_after, previous=counters_before)
    prior = counters_before.get('clients', {}).get('allow-tests', {})
    current = counters_after.get('clients', {}).get('allow-tests', {})
    counter_deltas = {key: current.get(key, 0) - prior.get(key, 0)
                      for key in set(prior) | set(current)}
    coverage = all(counter_deltas.get(key, 0) > 0 for key in ('accepted', 'Q', 'P', 'B', 'E', 'd'))
    cancel_delta = (counters_after.get('clients', {}).get('other', {}).get('cancel', 0) -
                    counters_before.get('clients', {}).get('other', {}).get('cancel', 0))
    coverage = coverage and cancel_delta > 0
    fresh = identity_before['status'] == identity_after['status'] == 'PASS'
    passed = result.wasSuccessful() and not result.skipped and before == after and coverage and fresh
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix('.log')
    log_path.write_text(log.getvalue())
    report = {'status': 'STALE_RUNTIME' if not fresh else ('PASS' if passed else 'FAIL'),
              'classification': 'FINITE_RUNTIME_CHECKS_NOT_FORMAL_REFINEMENT',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'tests': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped),
              'source_unchanged': before == after, 'input_root_sha256': before,
              'files': files, 'proxy_status_before': counters_before,
              'proxy_status_after': counters_after,
              'runtime_identity_before': identity_before,
              'runtime_identity_after': identity_after,
              'daemon_pid_stable': counters_before.get('pid') == counters_after.get('pid'),
              'allow_tests_counter_deltas': counter_deltas,
              'cancel_counter_delta': cancel_delta, 'real_proxy_coverage': coverage,
              'log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest(),
              'limits': ['Finite authored fixtures; no universal SQL/Python/protocol refinement',
                         'Per-client application/bootstrap/migration/dump/restore coverage requires separate evidence']}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(log.getvalue())
    print(json.dumps({k: report[k] for k in ('status', 'tests', 'failures', 'errors', 'skipped', 'source_unchanged')}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
