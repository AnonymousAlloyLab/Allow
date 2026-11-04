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
    coverage = all(counter_deltas.get(key, 0) > 0 for key in ('accepted', 'P', 'B', 'E', 'd'))
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
