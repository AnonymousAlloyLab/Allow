#!/usr/bin/python3
"""Explicit local fixture acceptance; creates only an authored test document."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

SOURCE = '// fixture comment retained until explicit apply\nsig VisibleNode {}\npred VisiblePresent { some VisibleNode }\nrun VisiblePresent for 3 but 4 Int, 3 seq\n'


class Client:
    """Use an operator-supplied local token without logging request headers."""

    def __init__(self, base, token):
        """Keep the ephemeral capability only in private memory."""
        if not base.startswith('http://127.0.0.1:'):
            raise ValueError('Only a local test installation is supported')
        self._base, self._token = base, token

    def call(self, path, body=None, expected='OK'):
        """Require the expected authenticated response without dumping source data."""
        raw = None if body is None else json.dumps(body, separators=(',', ':')).encode()
        headers = {'Authorization': 'Bearer ' + self._token, 'Content-Type': 'application/json'}
        req = urllib.request.Request(self._base + path, data=raw, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read(1048577))
        except urllib.error.HTTPError as failure:
            result = json.loads(failure.read(1048577))
            raise AssertionError('HTTP ' + str(failure.code) + ': ' + result.get('status', 'unknown')) from None
        if result['status'] != expected:
            raise AssertionError('Unexpected status: ' + result['status'])
        return result['data']


def job_request(accepted):
    """Bind the authored current source to the actual accepted artifact identity."""
    artifact = accepted['artifact']
    return {'requestId': str(uuid.uuid4()), 'documentId': accepted['documentId'],
            'baseRevision': accepted['revision'], 'draftId': str(uuid.uuid4()),
            'draftEpoch': 1, 'contentGeneration': 1, 'artifactId': artifact['artifactId'],
            'sourceHash': artifact['sourceHash'], 'candidate': {'mode': 'SOURCE', 'source': SOURCE},
            'intent': 'Keep the model and declaration structure.', 'kind': 'SOURCE_EDIT'}


def wait_job(client, job_id):
    """Poll only until a consent boundary or terminal result; never auto-dispatch."""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        job = client.call('/api/ai/v1/jobs/' + job_id)
        if job['status'] not in ('CREATING', 'GENERATING', 'VERIFYING'):
            return job
        time.sleep(0.1)
    raise AssertionError('Job did not reach a boundary')


def consent(client, job):
    """Approve this authored fixture's exact visible payload once."""
    assert job['status'] == 'AWAITING_DISCLOSURE', job['status'] + ':' + str(job.get('code'))
    payload = job['payload']
    assert hashlib.sha256(payload.encode()).hexdigest() == job['payloadHash']
    assert all(text not in payload for text in ('VisibleNode', 'VisiblePresent', 'fixture comment'))
    client.call('/api/ai/v1/jobs/' + job['id'] + '/disclosure',
                {name: job[name] for name in ('binding', 'attempt', 'payloadHash', 'termsVersion')})


def acceptance(client):
    """Check real Spring/IPC/LangGraph/scoped Java verification without saving AI output."""
    assert client.call('/api/ai/v1/config')['mode'] == 'FIXTURE'
    title = 'AI integration fixture ' + uuid.uuid4().hex[:8]
    initial = client.call('/api/v1/documents', {'idempotencyKey': str(uuid.uuid4()),
                                             'title': title}, 'COMMITTED')
    path = '/api/v1/documents/' + urllib.parse.quote(initial['documentId'], safe='')
    accepted = client.call(path + '/commit', {'idempotencyKey': str(uuid.uuid4()),
                 'expectedRevision': 0, 'candidate': {'mode': 'SOURCE', 'source': SOURCE}}, 'COMMITTED')
    body = job_request(accepted)
    job = client.call('/api/ai/v1/jobs', body, 'SUBMITTED')
    replay = client.call('/api/ai/v1/jobs', body, 'SUBMITTED')
    assert replay['id'] == job['id']
    first = wait_job(client, job['id'])
    consent(client, first)
    second = wait_job(client, job['id'])
    assert second['attempt'] == 2 and second['payloadHash'] != first['payloadHash']
    consent(client, second)
    ready = wait_job(client, job['id'])
    assert ready['status'] == 'REVIEW_READY', ready['status'] + ':' + str(ready.get('code'))
    proposal = ready['proposal']
    assert 'VisibleNode' in proposal['source'] and 'Slot0' not in proposal['source']
    assert client.call(path)['revision'] == 1
    approval = {'binding': ready['binding'], 'proposalHash': proposal['proposalHash']}
    receipt = client.call('/api/ai/v1/jobs/' + job['id'] + '/approve', approval)
    repeated = client.call('/api/ai/v1/jobs/' + job['id'] + '/approve', approval)
    assert receipt == repeated
    assert receipt['sourceHash'] == hashlib.sha256(receipt['source'].encode()).hexdigest()
    assert client.call(path)['revision'] == 1
    return {'status': 'PASS', 'document_id': accepted['documentId'], 'document_title': title, 'attempts': 2,
            'projection': proposal['projection'], 'accepted_revision_after_approval': 1,
            'checks': ['exact create replay', 'anonymous payload excludes display names/comments',
                       'fresh consent after real failed Alloy verification', 'restored display names',
                       'scoped Java validation', 'idempotent apply receipt', 'no automatic Save'],
            'remote_provider_called': False}


def main():
    """Require explicit disposable local target and write content-free acceptance evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = acceptance(Client(args.base, args.token_file.read_text().strip()))
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'document_id'}))


if __name__ == '__main__':
    main()
