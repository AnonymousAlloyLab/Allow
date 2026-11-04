#!/usr/bin/env python3
"""Finite P1 mechanism subcases on a fresh copied installation and synthetic document only."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid


def save(path, value):
    """Create private evidence once; never replace an earlier failure record."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def normalized(value):
    """Encode database values for hashing without printing row data."""
    if isinstance(value, (bytes, memoryview)):
        return {'bytes': bytes(value).hex()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalized(item) for item in value]
    return value


def snapshot():
    """Hash every document table through the canonical SQLeanParser route."""
    from allow_documents.migration import TABLES
    from allow_retrieval.sql_connections import connect
    from psycopg import sql
    from psycopg.rows import dict_row
    result = {}
    with connect(admin=True, client='allow-tests', row_factory=dict_row) as connection:
        for table in TABLES:
            rows = connection.execute(sql.SQL('SELECT * FROM documents.{}').format(sql.Identifier(table))).fetchall()
            values = sorted(json.dumps(normalized(row), sort_keys=True, separators=(',', ':')) for row in rows)
            result[table] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(values).encode()).hexdigest()}
    return result


def control(root):
    """Read only bounded public aggregate status from the new proxy's private control socket."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(3)
        stream.connect(str(root/'.runtime/corpus/sql-proxy/socket/context.sock'))
        stream.sendall(b'{"protocol":1,"operation":"status"}\n')
        stream.shutdown(socket.SHUT_WR)
        result = bytearray()
        while block := stream.recv(8193-len(result)):
            result.extend(block)
            if len(result) > 8192:
                raise ValueError('control_reply_limit')
        return json.loads(result)


def ready(root, timeout=10):
    """Wait a bounded interval for the actual new proxy's context readiness."""
    deadline = time.monotonic()+timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = control(root)
            if last.get('status') == 'READY':
                return last
        except (OSError, ValueError):
            pass
        time.sleep(.05)
    raise RuntimeError('isolated_context_not_ready')


def fixture(root):
    """Create one synthetic accepted-storage document using the actual admission/finalization path."""
    from allow_documents import identity, migration
    from allow_documents.store import Store
    migration.migrate()
    identity.provision()
    sys.path.insert(0, str(root/'scripts'))
    import document_recovery_test as helpers
    store = Store()
    assert store.initialize('authored-document-recovery-v1')['status'] == 'READY'
    document, _, _ = helpers.commit(store)
    document, _, _ = helpers.commit(store, document=document, revision=0, label='CleanupFixture')
    current = store.read({'documentId': document, 'revision': 1})
    identifier = current['artifact']['module']['signatures'][0]['id']
    return {'document': document, 'revision': 1, 'artifact': current['artifact'], 'owned_id': identifier}


class JournalTrace:
    """Observe public-safe lifecycle fields; keep exact backend identity in private trace only."""
    def __init__(self, root, nonce):
        """Bind polling to one owned nonce and a bounded journal path."""
        self.path = root/'.runtime/corpus/sql-proxy/context-state.json'
        self.nonce = nonce
        self.events = []
        self.bound = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.poll, daemon=True)

    def poll(self):
        """Record changed phases without ever retaining BackendKeyData or scope values."""
        previous = None
        while not self.stop.wait(.002):
            try:
                entry = json.loads(self.path.read_text()).get('context')
                if not entry or entry.get('nonce') != self.nonce:
                    continue
                if entry.get('backendStart'):
                    self.bound = {key: entry[key] for key in ('backendPid', 'backendStart', 'database', 'user', 'applicationName')}
                state = (entry['phase'], entry['failed'], entry['successPermitted'])
                if state != previous:
                    self.events.append({'phase': state[0], 'failed': state[1], 'successPermitted': state[2], 'monotonic_ns': time.monotonic_ns()})
                    previous = state
            except (OSError, ValueError, KeyError):
                continue

    def finish(self):
        """Join the owned observer thread before writing its immutable evidence."""
        self.stop.set()
        self.thread.join(timeout=1)
        if self.thread.is_alive():
            raise RuntimeError('journal_trace_thread_did_not_exit')


def absence(bound, nonce):
    """Observe exact backend identity through fresh ordinary canonical autocommit snapshots."""
    from allow_retrieval.sql_connections import connect
    from psycopg.rows import dict_row
    with connect(client='allow-tests', autocommit=True, row_factory=dict_row) as connection:
        if bound:
            rows = connection.execute('SELECT pid, backend_start, datname, usename, application_name FROM pg_catalog.pg_stat_activity WHERE pid=%s AND datname=%s AND usename=%s AND application_name=%s',
                (bound['backendPid'], bound['database'], bound['user'], bound['applicationName'])).fetchall()
            expected_start = datetime.fromisoformat(bound['backendStart'])
            matching = [row for row in rows if row['backend_start'] == expected_start]
            return not matching, bool(rows), True
        rows = connection.execute('SELECT pid, backend_start FROM pg_catalog.pg_stat_activity WHERE datname=%s AND usename=%s AND application_name=%s',
            ('allow_retrieval', 'allow_app', 'allow-document-context:'+nonce)).fetchall()
        return not rows, bool(rows), False


def child_command(root, mode, directory):
    """Use actual CLI for normal tests and a declared copied-process wrapper for fault telemetry."""
    python = str(root/'.tools/retrieval-venv/bin/python')
    limits = ['/usr/bin/prlimit', '--as=2147483648', '--cpu=20', '--']
    if mode == 'normal':
        return limits + [python, '-m', 'allow_documents.cli']
    if mode == 'quota':
        return limits + [python, str(root/'.gate/quota_child.py'), '--directory', str(directory)]
    result = limits + [python, str(root/'.gate/probe_child.py'), '--directory', str(directory)]
    if mode in ('wall-decode', 'kill-decode'):
        result.append('--barrier')
    if mode == 'wall-register':
        result.append('--registration-stall')
    if mode == 'wall-connected':
        result.append('--paced-selects')
    return result


def await_barrier(process, directory):
    """Require an actually reached history-decoded barrier before applying any fault."""
    deadline = time.monotonic()+8
    while time.monotonic() < deadline and process.poll() is None:
        if (directory/'barrier.json').exists():
            return json.loads((directory/'barrier.json').read_text())
        time.sleep(.01)
    raise RuntimeError('declared_barrier_not_reached')


def fault(process, mode, directory):
    """Inject only the registered wall delay or a PIDFD-owned CLI kill at decoded history."""
    if mode not in ('wall-decode', 'wall-register', 'kill-decode'):
        return None
    event = await_barrier(process, directory)
    if mode in ('wall-decode', 'wall-register'):
        time.sleep(3.3)
        (directory/'release').touch(mode=0o600)
    else:
        from experiment import process_identity, signal_owned
        owner = process_identity(process.pid)
        if owner is None:
            raise RuntimeError('child_exit_before_pidfd_fault')
        signal_owned(owner, signal.SIGKILL)
    return {'phase': event['phase'], 'injection': mode, 'monotonic_ns': time.monotonic_ns()}


def run_cli(root, value, ids, mode, directory):
    """Collect exact CLI output and bound lifecycle evidence without echoing private fixtures."""
    directory.mkdir(mode=0o700)
    if mode == 'quota' and value.get('focus_id'):
        save(directory/'quota-control.json', {'focus_id': value['focus_id']})
    nonce = str(uuid.uuid4())
    frame = {'protocol': 1, 'requestId': nonce, 'operation': 'validationContext',
             'args': {'documentId': value['document'], 'revision': value['revision'], 'ids': ids}}
    trace = JournalTrace(root, nonce)
    command = child_command(root, mode, directory)
    started = time.monotonic_ns()
    trace.thread.start()
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        process.stdin.write(json.dumps(frame).encode()+b'\n')
        process.stdin.close()
        process.stdin = None
        injected = fault(process, mode, directory)
        output, errors = process.communicate(timeout=12)
    except BaseException as error:
        save(directory/'failure-before-emergency.json', {'failure_class': type(error).__name__,
                                                        'child_alive': process.poll() is None})
        if process.poll() is None:
            from experiment import process_identity, signal_owned
            owner = process_identity(process.pid)
            if owner is not None:
                signal_owned(owner, signal.SIGKILL)
            process.communicate(timeout=3)
        raise
    finally:
        trace.finish()
    finished = time.monotonic_ns()
    save(directory/'trace-private.json', {'events': trace.events, 'bound_identity': trace.bound})
    save(directory/'wire-private.json', {'input': frame, 'stdout': output.decode('utf8', 'replace'), 'stderr': errors.decode('utf8', 'replace')})
    outcome = json.loads(output) if output.strip() else None
    absent, present, exact = absence(trace.bound, nonce)
    return {'exit_code': process.returncode, 'elapsed_ms': (finished-started)/1000000,
            'command': command, 'fixture_sha256': hashlib.sha256(json.dumps(frame, sort_keys=True).encode()).hexdigest(),
            'stdout_sha256': hashlib.sha256(output).hexdigest(), 'stderr_sha256': hashlib.sha256(errors).hexdigest(),
            'outcome': outcome, 'nonce': nonce, 'backend_absent': absent,
            'absence_was_exact_bound_identity': exact, 'matching_name_still_present': present,
            'events': trace.events, 'injected': injected, 'stderr_empty': not errors}


def assess(root, value, ids, mode, directory, subcase, check_durable=True):
    """Apply the frozen predicate for one narrow mechanism subcase and preserve failure first."""
    before = snapshot() if check_durable else None
    record = {'claim_id': 'CC05' if mode == 'normal' else {'lock': 'CC09', 'wall-decode': 'CC11', 'wall-register': 'CC11', 'wall-connected': 'CC11', 'kill-decode': 'CC12'}[mode],
              'subcase': subcase, 'status': 'BLOCK', 'scope': 'Python context mechanism only; Java/worker path not exercised'}
    manifest = json.loads((root/'.gate/manifest.json').read_text())
    registration = json.loads((root/'.gate/registration.json').read_text())
    specification = next(case for case in registration['cases'] if case['subcase'] == subcase)
    record.update(run_id=manifest['run_id'], input_root_sha256=manifest['input_root_sha256'],
                  verifier_id='INITIAL-CONTEXT-MECHANISMS', verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  expected_predicate=specification['predicate'])
    observed = run_cli(root, value, ids, mode, directory)
    outcome = observed.pop('outcome')
    nonce = observed.pop('nonce')
    record['observed'] = observed
    record['durable_unchanged'] = snapshot() == before if check_durable else None
    success = bool(outcome and outcome.get('status') == 'OK')
    if mode == 'normal':
        expected = {'documentId': value['document'], 'baseRevision': value['revision'], 'headObserved': value['revision'],
                    'artifact': value['artifact'], 'ownedIdInventory': {value['owned_id']: 'signature'} if value['owned_id'] in ids else {}}
        record['exact_envelope'] = outcome == {'protocol': 1, 'requestId': nonce, 'status': 'OK', 'data': expected}
        passed = record['exact_envelope'] and observed['exit_code'] == 0 and observed['backend_absent']
    else:
        telemetry = json.loads((directory/'telemetry.json').read_text()) if (directory/'telemetry.json').exists() else {}
        record['sqlstates'] = telemetry.get('sqlstates', [])
        state = control(root)
        record['context_status_after'] = state
        record['no_success_output'] = not success
        retained = state.get('contextOccupied') is True
        passed = not success and (observed['backend_absent'] or retained)
        if mode == 'lock':
            passed = passed and '55P03' in record['sqlstates']
        if mode == 'kill-decode':
            passed = passed and observed['exit_code'] == -signal.SIGKILL
        if mode == 'wall-register':
            events = observed['events']
            reserved = next((event for event in events if event['phase'] == 'RESERVED'), None)
            cleaned = next((event for event in events if event['phase'] == 'CLEAN' and event['failed']), None)
            forbidden = any(event['phase'] in ('CONNECTING', 'KEYED', 'BOUND') for event in events)
            elapsed = (cleaned['monotonic_ns']-reserved['monotonic_ns'])/1000000 if reserved and cleaned else None
            record['reserved_to_failed_clean_ms'] = elapsed
            passed = passed and not forbidden and elapsed is not None and elapsed >= 2900
        if mode == 'wall-connected':
            pauses = telemetry.get('pauses', [])
            retired = next((event for event in observed['events'] if event['phase'] == 'RETIRING'), None)
            fourth = pauses[3] if len(pauses) == 4 else None
            offset = (retired['monotonic_ns']-fourth['started_ns'])/1000000 if retired and fourth else None
            record['pause_trace'] = pauses
            record['fourth_pause_before_retirement_ms'] = offset
            passed = passed and offset is not None and 0 <= offset < 1000 and '25P03' not in record['sqlstates']
            passed = passed and [pause['template'] for pause in pauses] == [0, 1, 2, 3]
            passed = passed and all(0 <= pause['finished_ns']-pause['started_ns'] < 1000000000 for pause in pauses)
    record['mechanism_predicate'] = passed
    record['status'] = 'PASS' if passed and record['durable_unchanged'] else 'BLOCK'
    save(directory/('case.json' if check_durable else 'outcome-before-lock-release.json'), record)
    return record


def lock_case(root, value, directory):
    """Hold a foreign owned lock until the timeout outcome has been recorded, then release normally."""
    from allow_retrieval.sql_connections import connect
    before = snapshot()
    with connect(admin=True, client='allow-tests') as connection:
        connection.execute('LOCK TABLE documents.document IN ACCESS EXCLUSIVE MODE')
        record = assess(root, value, [value['owned_id']], 'lock', directory, 'actual-lock-timeout', False)
    record['durable_unchanged'] = snapshot() == before
    record['status'] = 'PASS' if record['mechanism_predicate'] and record['durable_unchanged'] else 'BLOCK'
    save(directory/'case.json', record)
    return record


def environment(root):
    """Bind loaded source, managed client versions and canonical public endpoint identity."""
    import psycopg
    from psycopg import pq
    from allow_retrieval.sql_connections import connect, PROXY_DIRECTORY
    status = json.loads((root/'.runtime/corpus/sql-proxy/status.json').read_text())
    sys.path.insert(0, str(root/'scripts'))
    import bootstrap_corpus
    if status.get('loaded_inputs') != bootstrap_corpus.proxy_inputs():
        raise RuntimeError('loaded_source_inventory_mismatch')
    if status.get('parser', {}).get('policy') != 'sql-routing-v8-context-leases':
        raise RuntimeError('loaded_policy_mismatch')
    argv = Path('/proc', str(status['pid']), 'cmdline').read_bytes().split(b'\0')
    if not argv or Path(argv[0].decode()) != root/'.tools/retrieval-venv/bin/python':
        raise RuntimeError('proxy_managed_interpreter_mismatch')
    with connect(client='allow-tests', autocommit=True) as connection:
        version = connection.execute('SHOW server_version').fetchone()[0]
        assert connection.info.host == str(PROXY_DIRECTORY)
        if not version.startswith('16.15'):
            raise RuntimeError('postgres_version_mismatch')
    return {'python': sys.version, 'python_executable': sys.executable, 'psycopg': psycopg.__version__,
            'libpq_version': pq.version(), 'postgres_version': version,
            'loaded_inputs': status.get('loaded_inputs'), 'parser': status.get('parser'),
            'context_status': control(root), 'kernel': os.uname().release,
            'pidfd_supported': hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')}


def main():
    """Run only registered finite subcases, preserving the first failing mechanism outcome."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    from allow_retrieval.common import ROOT as installed_root
    if installed_root != root or root == Path('/home/augustus/Allow'):
        raise RuntimeError('copied_runtime_required')
    cases = []
    report = {'schema_version': '1.0', 'status': 'INFRASTRUCTURE_FAILURE', 'cases': cases}
    try:
        ready(root)
        report['environment'] = environment(root)
        value = fixture(root)
        all_ids = sorted({value['owned_id']} | {'server:'+str(uuid.uuid4()) for _ in range(4095)})
        variants = [('normal-empty', [], 'normal'), ('normal-owned', [value['owned_id']], 'normal'),
                    ('normal-4096-ids', all_ids, 'normal'), ('actual-lock-timeout', None, 'lock'),
                    ('wall-before-connect', [value['owned_id']], 'wall-register'),
                    ('wall-during-connected-work', [value['owned_id']], 'wall-connected'),
                    ('wall-after-decode', [value['owned_id']], 'wall-decode'),
                    ('cli-kill-after-decode', [value['owned_id']], 'kill-decode')]
        for name, ids, mode in variants:
            ready(root)
            directory = arguments.output.parent/name
            case = lock_case(root, value, directory) if mode == 'lock' else assess(root, value, ids, mode, directory, name)
            cases.append(case)
            if case['status'] != 'PASS':
                break
        report['finite_subcases_passed'] = len(cases) == len(variants) and all(c['status'] == 'PASS' for c in cases)
        report['status'] = 'BLOCKED'
        report['blocking_reasons'] = ['Full33-case runtime surface and two implementation builds are not executed by this initial harness.']
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        report['status'] = 'INFRASTRUCTURE_FAILURE'
        raise
    finally:
        report['boundary'] = 'Eight initial registered mechanism subcases, not the33-case closure. No Java validation path or full permitted-history fixture is included.'
        save(arguments.output, report)


if __name__ == '__main__':
    main()
