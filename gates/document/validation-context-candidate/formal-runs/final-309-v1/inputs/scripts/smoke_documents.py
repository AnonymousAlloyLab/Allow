#!/usr/bin/env python3
"""Exercise the actual local document API with authored fixtures and private authority.

This is finite integration evidence, not a Java/SQL refinement proof or browser test.
Receipts and revisions are intentionally retained by the application's immutable policy.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from smoke_local import Client
from verify_sql_runtime import read_status, runtime_identity

ROOT = Path(__file__).resolve().parents[1]
API = '/api/v1/documents'
SOURCE = '// authored comment 😀\r\nsig A {}\r\npred Present { some A }\r\nassert Empty { no A }\r\nrun Present for 3 but 4 Int, 3 seq\r\ncheck Empty for 3 but 4 Int, 3 seq\r\n'


def encoded(value):
    """Produce deterministic test bytes without changing bytes during receipt retry."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def digest(value):
    """Bind exact bytes without exporting model content or launch authority."""
    return hashlib.sha256(value).hexdigest()


def fingerprint():
    """Bind this finite run to active implementation, contracts, locks and compiled classes."""
    names = ['backend/src', 'frontend/src', 'backend/target/classes', 'retrieval/allow_documents',
             'retrieval/allow_retrieval', 'db/document', 'spec', 'config']
    paths = [p for name in names for p in (ROOT/name).rglob('*') if p.is_file()
             and '__pycache__' not in p.parts and p.suffix != '.pyc'
             and not p.name.endswith('evidence.json')]
    paths += [Path(__file__), ROOT/'backend/pom.xml', ROOT/'frontend/package-lock.json']
    files = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(set(paths))}
    return files, digest(encoded(files))


class DocumentClient(Client):
    """Keep exact response and request bytes for HTTP idempotency assertions."""

    def raw(self, path, body=None, headers=None, authorized=True):
        """Send bounded original bytes and return status, parsed data and exact response."""
        values = {'Content-Type': 'application/json'}
        if authorized:
            values['Authorization'] = 'Bearer ' + self.token
        values.update(headers or {})
        request = urllib.request.Request(self.base + path, body, values)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, raw = response.status, response.read(1048577)
        except urllib.error.HTTPError as failure:
            status, raw = failure.code, failure.read(1048577)
        assert len(raw) <= 1048576, 'Response exceeded complete byte budget'
        return status, json.loads(raw) if raw.startswith(b'{') else None, raw

    def call(self, path, value=None, expected='OK'):
        """Require the exact closed protocol envelope and expected operation status."""
        status, result, raw = self.raw(path, encoded(value) if value is not None else None)
        assert status == 200, (path, status, result)
        assert set(result) == {'protocol', 'requestId', 'status', 'data'}
        assert result['protocol'] == 1 and str(uuid.UUID(result['requestId'])) == result['requestId']
        assert result['status'] == expected, (path, result['status'], result.get('data'))
        return result['data'], raw


def mutation(candidate, revision):
    """Create a unique original mutation intent for one authored candidate."""
    return {'idempotencyKey': str(uuid.uuid4()), 'expectedRevision': revision, 'candidate': candidate}


def artifact_content(artifact):
    """Select the exact fields that history copies must preserve without reprinting."""
    return {name: artifact[name] for name in ['mode', 'source', 'sourceHash', 'module', 'occurrences', 'trivia']}


def analyze(client, path, accepted, index):
    """Require actual sandboxed SAT evidence bound to every accepted identity field."""
    artifact = accepted['artifact']
    command = artifact['analysisDescriptors'][index]
    body = {'acceptedRevision': accepted['revision'], 'commandKey': command['commandKey'],
            'draftEpoch': 9, 'exactSourceHash': artifact['sourceHash']}
    submitted, _ = client.call(path+'/analyze', body, 'SUBMITTED')
    key = submitted['acceptedAnalysisKey']
    for name in ['artifactId', 'sourceHash', 'policyVersion', 'dependencyHash']:
        assert key[name] == artifact[name]
    assert key['options'] == command['options'] and key['commandKey'] == command['commandKey']
    deadline = time.monotonic()+15
    while True:
        result, _ = client.call(path+'/analysis/'+submitted['jobId'])
        assert result['acceptedAnalysisKey'] == key and result['historical'] is False
        job = result['job']
        assert job['analysisKey'] == key['jobAnalysisKey']
        if job['status'] not in ('QUEUED', 'RUNNING'):
            break
        assert time.monotonic() < deadline
        time.sleep(.1)
    assert job['status'] == 'SAT' and job['witness'] is not None, job['status']
    assert job['commandKind'] == command['kind']
    return submitted, {'status': job['status'], 'commandKind': job['commandKind'],
                       'canonicalStatus': job['canonical']['status']}


def main():
    """Check authority, typed edits, exact replay, real analysis and immutable history."""
    files, source_root = fingerprint()
    proxy_path = ROOT/'.runtime/corpus/sql-proxy/status.json'
    before = read_status(proxy_path)
    assert runtime_identity(before)['status'] == 'PASS'
    client = DocumentClient()
    checks = []
    for headers, authorized in [({}, False), ({'Authorization': 'Bearer wrong'}, True),
                                ({'Origin': 'https://hostile.invalid'}, True),
                                ({'Host': 'hostile.invalid'}, True)]:
        assert client.raw(API, headers=headers, authorized=authorized)[0] == 403
    for bad in [b'{"x":1,"x":2}', b'{"x":"\xc3"}', b'{"x":"\\ud800"}']:
        assert client.raw(API, bad)[0] == 400
    assert client.raw(API, b' '*262145)[0] == 400
    checks.append('Authority, Host, Origin, strict JSON/UTF-8 and complete request byte limit')
    create = {'idempotencyKey': str(uuid.uuid4()), 'title': 'Authored document integration'}
    initial, original = client.call(API, create, 'COMMITTED')
    assert initial['revision'] == 0 and initial['artifact']['source'] == ''
    assert client.raw(API, encoded(create))[2] == original
    assert client.call(API, dict(create, title='changed'), 'IDEMPOTENCY_CONFLICT')
    document = initial['documentId']
    path = API+'/'+urllib.parse.quote(document, safe='')
    assert client.raw(API+'?ignored=1', encoded(create))[0] == 400
    checks.append('Fresh revision zero, exact creation replay and conflicting intent/query denial')
    source_body = mutation({'mode': 'SOURCE', 'source': SOURCE}, 0)
    accepted, source_reply = client.call(path+'/commit', source_body, 'COMMITTED')
    assert accepted['revision'] == 1 and accepted['artifact']['mode'] == 'BLOCK_SUPPORTED'
    assert accepted['artifact']['source'] == SOURCE and accepted['artifact']['sourceHash'] == digest(SOURCE.encode())
    assert accepted['artifact']['trivia'] and accepted['artifact']['occurrences']
    assert client.raw(path+'/commit', encoded(source_body))[2] == source_reply
    reformatted = json.dumps(source_body, indent=2).encode()
    assert client.raw(path+'/commit', reformatted)[1]['status'] == 'IDEMPOTENCY_CONFLICT'
    assert client.raw(API+'/'+document+'/commit', encoded(source_body))[1]['status'] == 'IDEMPOTENCY_CONFLICT'
    checks.append('SOURCE→BLOCK exact Unicode/CRLF/comments/maps and byte/route-bound receipt replay')
    analyses = [analyze(client, path, accepted, i) for i in range(2)]
    checks.append('Real SAT4J run example and check counterexample bound to accepted descriptors')
    candidate = {'mode': 'BLOCK_SUPPORTED', 'module': copy.deepcopy(accepted['artifact']['module']),
                 'presentationCopies': []}
    for node in candidate['module']['nodes']:
        if node['tag'] == 'some_test':
            node['tag'] = 'no_test'
    preview_body = {'draftId': str(uuid.uuid4()), 'draftEpoch': 2, 'baseRevision': 1, 'candidate': candidate}
    preview, _ = client.call(path+'/validate', preview_body, 'VALIDATED')
    assert preview['requestHash'] == digest(encoded(preview_body)) and preview['draftEpoch'] == 2
    assert preview['proposedSourceHash'] == digest(preview['proposedSource'].encode())
    head, _ = client.call(path)
    assert head['revision'] == 1, 'Advisory validation changed accepted state'
    edited, _ = client.call(path+'/commit', mutation(candidate, 1), 'COMMITTED')
    assert edited['revision'] == 2 and '// authored comment 😀' in edited['artifact']['source']
    for submission, _ in analyses:
        old, _ = client.call(path+'/analysis/'+submission['jobId'])
        assert old['historical'] is True and old['acceptedAnalysisKey'] == submission['acceptedAnalysisKey']
    checks.append('Request-bound advisory preview does not commit; block edit preserves comment; old analysis labeled historical')
    invalid = copy.deepcopy(candidate)
    next(node for node in invalid['module']['nodes'] if node['tag'] == 'no_test')['tag'] = 'not'
    denial_body = mutation(invalid, 2)
    denied, denial_raw = client.call(path+'/commit', denial_body, 'REJECTED')
    assert denied['acceptedRevision'] == 2 and denied['code'] == 'TYPE_MISMATCH'
    assert client.raw(path+'/commit', encoded(denial_body))[2] == denial_raw
    stale, _ = client.call(path+'/commit', mutation(candidate, 1), 'REJECTED')
    assert stale['code'] == 'STALE_REVISION' and stale['acceptedRevision'] == 2
    assert client.call(path)[0]['revision'] == 2
    checks.append('Ill-typed candidate and stale revision reject without head advancement; denial replay exact')
    text = 'sig A {} run { some A } for 3'
    text_only, _ = client.call(path+'/commit', mutation({'mode': 'SOURCE', 'source': text}, 2), 'COMMITTED')
    assert text_only['artifact']['mode'] == 'TEXT_ONLY' and text_only['artifact']['module'] is None
    assert text_only['artifact']['source'] == text and not text_only['artifact']['occurrences']
    assert len(text_only['artifact']['analysisDescriptors']) == 1
    checks.append('Parser-valid unsupported source retains exact TEXT_ONLY content and analysis descriptors')
    current = text_only
    for target in (1, 0, 1):
        body = {'idempotencyKey': str(uuid.uuid4()), 'expectedRevision': current['revision'],
                'targetRevision': target, 'direction': 'UNDO' if target == 0 else 'REDO'}
        previous = current
        current, _ = client.call(path+'/history-copy', body, 'COMMITTED')
        old, _ = client.call(path+'?revision='+str(target))
        assert artifact_content(current['artifact']) == artifact_content(old['artifact'])
        assert current['revision'] == previous['revision']+1
        assert current['artifact']['artifactId'] != old['artifact']['artifactId']
    assert client.raw(path+'/commit', encoded(denial_body))[2] == denial_raw
    assert client.raw(path+'/commit', encoded(source_body))[2] == source_reply
    checks.append('History including revision zero revalidates unchanged content with fresh artifact; old receipts remain exact')
    state = {'documentId': document, 'path': path, 'headRevision': current['revision'],
             'identitySha256': digest((ROOT/'.runtime/documents/identity.json').read_bytes()),
             'artifact': current['artifact'], 'createBody': create, 'createResponse': original.decode(),
             'sourceBody': source_body, 'sourceResponse': source_reply.decode(), 'priorToken': client.token}
    state_path = ROOT/'.runtime/documents/http-restart-fixture.json'
    state_path.write_bytes(encoded(state)); state_path.chmod(0o600)
    time.sleep(.35)
    after = read_status(proxy_path)
    identity = runtime_identity(after, before)
    delta = after['clients']['allow-app']['accepted']-before['clients']['allow-app']['accepted']
    assert identity['status'] == 'PASS' and delta > 0
    assert fingerprint()[1] == source_root, 'Implementation changed during HTTP verification'
    report = {'status': 'PASS', 'classification': 'FINITE_ACTUAL_HTTP_TESTS_NOT_FORMAL_REFINEMENT',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
              'solver_outcomes': [item[1] for item in analyses], 'source_sha256': files,
              'input_root_sha256': source_root, 'sql_proxy_identity': identity, 'app_accepted_delta': delta,
              'browser_qa': 'SEPARATE_BROWSER_EVIDENCE_NOT_MEASURED_BY_THIS_SCRIPT', 'source_or_authority_exported': False}
    (ROOT/'gates/document/http-smoke.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'checks': len(checks), 'app_accepted_delta': delta}))


if __name__ == '__main__':
    main()
