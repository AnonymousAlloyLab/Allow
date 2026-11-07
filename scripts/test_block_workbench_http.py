#!/usr/bin/python3
"""Exercise real bounded comparison on an explicitly selected local test server."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from test_ai_http import Client

SOURCE = '''sig Node { edge: set Node }
sig Label {}
pred NodesPresent { some Node }
pred LabelsPresent { some Label }
pred NoEdges { no edge }
run NodesPresent for 3 but 4 Int, 3 seq
'''
LEFT = '''sig Node {}
pred Available [choices: set Node] { some choices }
'''
RIGHT = '''sig Node {}
pred Empty [selection: set Node] { no selection }
'''


def digest(value):
    """Hash exact UTF-8 source or request serialization without normalization."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def bound(accepted):
    """Bind ephemeral work to the authorized current artifact and fresh draft."""
    return {'draftId': str(uuid.uuid4()), 'draftEpoch': 1,
            'baseRevision': accepted['revision'], 'artifactId': accepted['artifact']['artifactId']}


def inspect(client, path, accepted, source):
    """Require parser-generated predicate choices bound to the exact uploaded bytes."""
    request = {**bound(accepted), 'source': source, 'sourceHash': digest(source)}
    response = client.call(path + '/comparison-model', request)
    assert response['sourceHash'] == digest(source)
    assert response['requestHash'] == digest(json.dumps(request, separators=(',', ':')))
    return response


def file_side(source, predicate):
    """Select one exact parsed name from an exact in-memory source."""
    return {'source': source, 'sourceHash': digest(source), 'predicate': predicate}


def same_request(request, response):
    """Check both content hash and human-readable identity before using evidence."""
    assert response['requestHash'] == digest(json.dumps(request, separators=(',', ':')))
    for key in ('draftId', 'draftEpoch', 'baseRevision', 'artifactId'):
        assert response[key] == request[key], key
    assert response['scope'] == request['scope']
    assert response['bitwidth'] == 4 and response['maxseq'] == 3


def categories(response, expected):
    """Require independent truth pairs and full evidence identities for SAT cases."""
    pairs = {'both': (True, True), 'leftOnly': (True, False),
             'rightOnly': (False, True), 'neither': (False, False)}
    assert set(response['categories']) == set(pairs)
    for name, status in expected.items():
        result = response['categories'][name]
        assert result['status'] == status, (name, result['status'])
        if status == 'SAT':
            assert (result['left'], result['right']) == pairs[name]
            assert result['witness']['states']
            assert len(result['evidenceHash']) == 64


def block_comparison(client, path, accepted):
    """Check actual independently satisfiable formulas and bounded identical arms."""
    module = accepted['artifact']['module']
    roots = {item['name']: item['bodyId'] for item in module['predicates']}
    request = {**bound(accepted), 'candidate': {'mode': 'BLOCK_SUPPORTED',
               'module': module, 'presentationCopies': []},
               'leftId': roots['NodesPresent'], 'rightId': roots['LabelsPresent'], 'scope': 3}
    result = client.call(path + '/compare', request)
    same_request(request, result)
    categories(result, dict.fromkeys(('both', 'leftOnly', 'rightOnly', 'neither'), 'SAT'))
    assert result['classification'] == 'DISTINGUISHED'
    identical = {**request, 'rightId': request['leftId']}
    result = client.call(path + '/compare', identical)
    same_request(identical, result)
    categories(result, {'both': 'SAT', 'leftOnly': 'UNSAT', 'rightOnly': 'UNSAT', 'neither': 'SAT'})
    assert result['classification'] == 'AGREEMENT'


def file_comparison(client, path, accepted):
    """Check parser selectors, shared set parameters and a mismatched background."""
    left = inspect(client, path, accepted, LEFT)
    right = inspect(client, path, accepted, RIGHT)
    assert [item['name'] for item in left['predicates']] == ['Available']
    assert [item['name'] for item in right['predicates']] == ['Empty']
    request = {**bound(accepted), 'left': file_side(LEFT, 'Available'),
               'right': file_side(RIGHT, 'Empty'), 'scope': 3}
    result = client.call(path + '/compare-models', request)
    same_request(request, result)
    categories(result, {'both': 'UNSAT', 'leftOnly': 'SAT', 'rightOnly': 'SAT', 'neither': 'UNSAT'})
    assert result['categories']['leftOnly']['assignment'][0]['tuples']
    assert result['categories']['rightOnly']['assignment'][0]['tuples'] == []
    mismatch = RIGHT + 'fact Required { some Node }\n'
    client.call(path + '/compare-models', {**request, 'right': file_side(mismatch, 'Empty')}, 'UNSUPPORTED')


def acceptance(client):
    """Create only an authored fixture and verify comparison never saves a model."""
    title = 'Reusable block comparison ' + uuid.uuid4().hex[:8]
    initial = client.call('/api/v1/documents', {'idempotencyKey': str(uuid.uuid4()), 'title': title}, 'COMMITTED')
    path = '/api/v1/documents/' + urllib.parse.quote(initial['documentId'], safe='')
    accepted = client.call(path + '/commit', {'idempotencyKey': str(uuid.uuid4()),
               'expectedRevision': 0, 'candidate': {'mode': 'SOURCE', 'source': SOURCE}}, 'COMMITTED')
    assert accepted['artifact']['mode'] == 'BLOCK_SUPPORTED'
    block_comparison(client, path, accepted)
    file_comparison(client, path, accepted)
    after = client.call(path)
    assert after['revision'] == 1 and after['artifact']['sourceHash'] == digest(SOURCE)
    return {'status': 'PASS', 'document_id': accepted['documentId'], 'document_title': title,
            'checks': ['all four real SAT categories', 'identical-arm bounded agreement',
                       'exact response binding', 'parser-derived file selectors',
                       'renamed shared set-valued parameters', 'empty assignment replay',
                       'background mismatch rejection', 'no automatic Save'],
            'accepted_revision_after_comparison': 1, 'provider_calls': 0}


def rejected(base, token, path, body, expected):
    """Require an HTTP rejection without printing credentials or source content."""
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(base + path,
              data=json.dumps(body, separators=(',', ':')).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15):
            raise AssertionError('Unexpectedly accepted a rejected request')
    except urllib.error.HTTPError as failure:
        assert failure.code == expected, failure.code


def boundary_checks(base, token, result):
    """Probe authority, closed inputs and exact source/artifact freshness over HTTP."""
    client = Client(base, token)
    path = '/api/v1/documents/' + urllib.parse.quote(result['document_id'], safe='')
    accepted = client.call(path)
    request = {**bound(accepted), 'source': LEFT, 'sourceHash': digest(LEFT)}
    for route in ('compare', 'comparison-model', 'compare-models'):
        rejected(base, '', path + '/' + route, {}, 403)
    rejected(base, token, path + '/comparison-model', {**request, 'operation': 'SAVE'}, 400)
    rejected(base, token, path + '/comparison-model', {**request, 'sourceHash': '0' * 64}, 400)
    rejected(base, token, path + '/comparison-model', {**request, 'draftEpoch': '1'}, 400)
    client.call(path + '/comparison-model', {**request, 'artifactId': 'stale-artifact'}, 'UNAVAILABLE')
    assert client.call(path)['revision'] == accepted['revision']
    return ['all comparison routes require authority', 'unknown fields rejected',
            'mismatched source hash rejected', 'numeric coercion rejected',
            'stale artifact rejected without saving']


def main():
    """Run only against an explicit disposable loopback target and private capability."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    token = args.token_file.read_text().strip()
    result = acceptance(Client(args.base, token))
    result['checks'].extend(boundary_checks(args.base, token, result))
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'document_id'}))


if __name__ == '__main__':
    main()
