"""Owned disposable native HTTP/SQL/sandbox acceptance; tokens remain only in memory."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path('/tmp/allow-anonymous-sql-r1')
BUILD = Path('/tmp/allow-anonymous-build/backend')
EVIDENCE = Path('/home/augustus/Allow/gates/deployment/anonymous-v1')
PORT = 18095
ORIGIN = 'https://allow.alloy4.fun'
sys.path.insert(0, str(ROOT / 'retrieval'))
from allow_documents.store import Store
from allow_documents import lifecycle

checks = []
tokens = []
private_token = secrets.token_urlsafe(32)


def record(name, passed, status=None):
    checks.append({'check': name, 'pass': bool(passed), 'http_status': status})
    print(name, 'PASS' if passed else 'FAIL', status if status is not None else '', flush=True)
    if not passed:
        raise AssertionError(name)


def request(method, path, token=None, value=None, origin=True, raw=None):
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=30)
    headers = {'Host': f'127.0.0.1:{PORT}'}
    if origin:
        headers['Origin'] = ORIGIN
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    body = raw if raw is not None else (json.dumps(value, separators=(',', ':')).encode() if value is not None else None)
    if body is not None:
        headers['Content-Type'] = 'application/json'
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    content = response.read(1572865)
    if len(content) > 1572864:
        raise RuntimeError('response_limit')
    status, response_headers = response.status, dict(response.getheaders())
    connection.close()
    try:
        data = json.loads(content) if content else None
    except ValueError:
        data = None
    return status, data, content, response_headers


def denied(name, method, path, token=None, value=None):
    status, data, _, _ = request(method, path, token, value)
    logical_denial = status == 200 and isinstance(data, dict) and data.get('status') == 'NOT_FOUND'
    safe = (status >= 400 or logical_denial) and not (isinstance(data, dict) and ('artifact' in data.get('data', {}) or 'documents' in data.get('data', {})))
    record(name, safe, status)
    if logical_denial:
        checks[-1]['protocol_status'] = 'NOT_FOUND'


def private_snapshot():
    with Store().transaction() as connection:
        rows = connection.execute('SELECT * FROM documents.workspace').fetchall()
    identity = ROOT / '.runtime/documents/identity.json'
    return hashlib.sha256(identity.read_bytes()).hexdigest(), hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def enrollment():
    status, data, _, headers = request('POST', '/api/public/workspaces', value={})
    record('enrollment_success_' + str(len(tokens) + 1), status == 201 and isinstance(data, dict) and isinstance(data.get('token'), str), status)
    token = data['token']
    tokens.append(token)
    record('enrollment_private_headers_' + str(len(tokens)), 'no-store' in headers.get('Cache-Control', ''))
    return token


def create(token, key):
    intent = {'idempotencyKey': key, 'title': 'Disposable acceptance'}
    status, data, content, _ = request('POST', '/api/v1/documents', token, intent)
    record('document_create_' + str(tokens.index(token) + 1), status == 200 and data.get('status') == 'COMMITTED', status)
    return data['data']['documentId'], intent, content


def await_job(token, job):
    for _ in range(60):
        status, data, _, _ = request('GET', '/api/jobs/' + job, token)
        if status != 200:
            raise AssertionError('own_job_poll_status')
        if data.get('status') not in ('QUEUED', 'RUNNING'):
            return data
        time.sleep(0.1)
    raise AssertionError('job_poll_timeout')


def exercise():
    status, config, _, _ = request('GET', '/api/public/config', origin=False)
    record('public_config_nonsecret', status == 200 and config.get('mode') == 'ANONYMOUS' and 'token' not in config, status)
    status, _, _, _ = request('POST', '/api/public/workspaces', value={}, origin=False)
    record('enrollment_requires_origin', status == 403, status)
    status, _, _, _ = request('POST', '/api/public/workspaces', value={'scope': 'forged'})
    record('enrollment_closed_empty_body', status == 400, status)
    status, _, _, _ = request('POST', '/api/public/workspaces?alias=1', value={})
    record('enrollment_no_query', status == 403, status)
    status, _, _, _ = request('POST', '/api/public/workspaces', private_token, {})
    record('enrollment_no_bearer_authority', status == 403, status)
    a, b = enrollment(), enrollment()
    record('separate_capabilities', a != b)
    denied('private_launch_token_rejected', 'GET', '/api/v1/documents', private_token)
    denied('public_corpus_disabled', 'GET', '/api/corpus/status', a)
    key = uuid.uuid4().hex
    first, intent, first_reply = create(a, key)
    second, _, second_reply = create(b, key)
    record('same_key_distinct_documents', first != second and first_reply != second_reply)
    for token, expected in ((a, first_reply), (b, second_reply)):
        status, _, content, _ = request('POST', '/api/v1/documents', token, intent)
        record('scope_receipt_replay_' + str(tokens.index(token) + 1), status == 200 and content == expected, status)
    encoded = first.replace(':', '%3A')
    for suffix in (encoded, first):
        status, data, _, _ = request('GET', '/api/v1/documents/' + suffix, a)
        record('own_document_read_' + ('encoded' if suffix == encoded else 'literal'), status == 200 and data.get('data', {}).get('documentId') == first, status)
    denied('foreign_document_read', 'GET', '/api/v1/documents/' + encoded, b)
    denied('foreign_history_read', 'GET', '/api/v1/documents/' + encoded + '?revision=0', b)
    candidate = {'mode': 'SOURCE', 'source': 'sig A {}\nrun { some A } for 2'}
    advisory = {'draftId': str(uuid.uuid4()), 'draftEpoch': 1, 'baseRevision': 0, 'candidate': candidate}
    status, data, _, _ = request('POST', '/api/v1/documents/' + encoded + '/validate', a, advisory)
    record('source_advisory_real_sandbox', status == 200 and data.get('status') not in ('UNAVAILABLE', 'INVALID_REQUEST') and 'supportMode' in data.get('data', {}), status)
    commit = {'idempotencyKey': uuid.uuid4().hex, 'expectedRevision': 0, 'candidate': candidate}
    status, accepted, _, _ = request('POST', '/api/v1/documents/' + encoded + '/commit', a, commit)
    record('source_save_real_sandbox', status == 200 and accepted.get('status') == 'COMMITTED' and accepted.get('data', {}).get('revision') == 1, status)
    denied('foreign_commit_receipt', 'POST', '/api/v1/documents/' + encoded + '/commit', b, commit)
    history = {'idempotencyKey': uuid.uuid4().hex, 'expectedRevision': 0, 'targetRevision': 0, 'direction': 'UNDO'}
    denied('foreign_history_mutation', 'POST', '/api/v1/documents/' + encoded + '/history-copy', b, history)
    denied('foreign_validation_context', 'POST', '/api/v1/documents/' + encoded + '/validate', b, advisory)
    foreign = {'mode': 'BLOCK_SUPPORTED', 'module': accepted['data']['artifact']['module'], 'presentationCopies': []}
    status, result, _, _ = request('POST', '/api/v1/documents/' + second.replace(':', '%3A') + '/commit', b,
                                  {'idempotencyKey': uuid.uuid4().hex, 'expectedRevision': 0, 'candidate': foreign})
    record('foreign_identifier_inventory_rejected', status >= 400 or result.get('status') != 'COMMITTED', status)
    status, unchanged, _, _ = request('GET', '/api/v1/documents/' + second.replace(':', '%3A'), b)
    record('foreign_rejection_no_revision_change', status == 200 and unchanged.get('data', {}).get('headRevision') == 0, status)
    source_job = {'source': candidate['source'], 'commandIndex': 0, 'revision': 1, 'epoch': 1, 'operation': 'ANALYZE'}
    status, job, _, _ = request('POST', '/api/jobs', a, source_job)
    record('owned_solver_submission', status == 200 and isinstance(job.get('jobId'), str), status)
    job_id = job['jobId']
    denied('foreign_job_poll', 'GET', '/api/jobs/' + job_id, b)
    denied('foreign_job_cancel', 'DELETE', '/api/jobs/' + job_id, b)
    result = await_job(a, job_id)
    record('own_solver_completed_not_foreign_cancelled', result.get('status') not in ('ERROR', 'CANCELLED', 'TIMEOUT'))
    status, _, _, _ = request('DELETE', '/api/jobs/' + job_id, a)
    record('own_job_cancel_authorized', status == 200, status)
    artifact = accepted['data']['artifact']
    descriptors = artifact.get('analysisDescriptors', [])
    record('accepted_analysis_descriptor_available', bool(descriptors))
    selection = {'acceptedRevision': 1, 'commandKey': descriptors[0]['commandKey'], 'draftEpoch': 1, 'exactSourceHash': artifact['sourceHash']}
    status, analysis, _, _ = request('POST', '/api/v1/documents/' + encoded + '/analyze', a, selection)
    record('accepted_solver_submission', status == 200 and analysis.get('status') == 'SUBMITTED', status)
    accepted_job = analysis['data']['jobId']
    denied('foreign_accepted_analysis_poll', 'GET', '/api/v1/documents/' + encoded + '/analysis/' + accepted_job, b)
    await_job(a, accepted_job)
    status, own_analysis, _, _ = request('GET', '/api/v1/documents/' + encoded + '/analysis/' + accepted_job, a)
    record('own_accepted_analysis_poll', status == 200 and own_analysis.get('status') not in ('UNAVAILABLE', 'INVALID_REQUEST'), status)
    enrollment()
    enrollment()
    status, _, _, _ = request('POST', '/api/public/workspaces', value={})
    record('fifth_session_capacity_denied', status == 429, status)
    for index, token in enumerate(tokens):
        status, _, _, _ = request('DELETE', '/api/public/workspaces/current', token)
        record('end_session_' + str(index + 1), status == 204, status)
        status, _, _, _ = request('GET', '/api/v1/documents', token)
        record('ended_capability_immediate_401_' + str(index + 1), status == 401, status)
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        if lifecycle.listing()['workspaces'] == []:
            record('retired_registry_eventually_empty', True)
            return
        time.sleep(1)
    record('retired_registry_eventually_empty', False)


def main():
    os.umask(0o077)
    if any((EVIDENCE / name).exists() for name in ('http-r3-report.json', 'http-r3-server.log')):
        raise RuntimeError('preserve_existing_http_evidence_before_retry')
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', PORT))
    baseline = private_snapshot()
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT), 'ALLOW_TOKEN': private_token,
           'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
    server_log = EVIDENCE / 'http-r3-server.log'
    process = None
    started = time.monotonic()
    failure = None
    try:
        with server_log.open('w') as output:
            process = subprocess.Popen(['/usr/bin/java', '-cp', 'target/classes:target/dependency/*',
                'dev.allow.backend.AllowApplication', '--allow.access-mode=ANONYMOUS',
                '--allow.corpus.root=' + str(ROOT), '--allow.deployment.origin=' + ORIGIN,
                f'--allow.deployment.tunnel-host=127.0.0.1:{PORT}', f'--server.port={PORT}',
                '--server.address=127.0.0.1', '--allow.document.advisory-profile=DOCUMENT_ADVISORY_TIER1'],
                cwd=BUILD, env=env, stdout=output, stderr=subprocess.STDOUT)
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('server_startup_failed')
                try:
                    if request('GET', '/api/public/config', origin=False)[0] == 200:
                        break
                except OSError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError('server_startup_timeout')
            exercise()
    except Exception as error:
        failure = type(error).__name__ + ':' + str(error)
    finally:
        if process is not None and process.poll() is None:
            for token in tokens:
                try:
                    request('DELETE', '/api/public/workspaces/current', token)
                except Exception:
                    pass
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        record('private_control_unchanged', private_snapshot() == baseline)
        for token in tokens + [private_token]:
            if token and token in server_log.read_text():
                raise RuntimeError('token_found_in_server_log')
        report = {'schema': 1, 'status': 'PASS' if failure is None else 'FAIL', 'failure_category': failure,
            'scope': 'Native isolated loopback HTTP + real SQL/parser/sandbox; NOT Windows/IIS/TLS/domain acceptance',
            'root': str(ROOT), 'backend': str(BUILD), 'port': PORT, 'checks': checks,
            'elapsed_seconds': round(time.monotonic() - started, 3), 'no_tokens_persisted': True,
            'server_stopped': process is None or process.poll() is not None}
        (EVIDENCE / 'http-r3-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if failure is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
