#!/usr/bin/python3
"""Exercise the actual analysis wire protocol across two builds on a disposable local service."""
import argparse
import json
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from test_ai_http import Client

SOURCE = '''sig Sample {}
pred Possible { some Sample }
pred Impossible { some Sample and no Sample }
run Possible for 3 but 4 Int, 3 seq
run Impossible for 3 but 4 Int, 3 seq
'''


def path_for(document):
    """Use the same encoded document identifier as the workbench."""
    return '/api/v1/documents/' + quote(document, safe='')


def save(client, path, revision, source):
    """Save one explicitly authored fixture revision."""
    return client.call(path + '/commit', {'expectedRevision': revision, 'idempotencyKey': str(uuid.uuid4()),
                       'candidate': {'mode': 'SOURCE', 'source': source}}, 'COMMITTED')


def seed(client):
    """Save two distinguishable commands on the previous backend."""
    doc = client.call('/api/v1/documents', {'title': 'Analysis upgrade fixture',
                      'idempotencyKey': str(uuid.uuid4())}, 'COMMITTED')
    return save(client, path_for(doc['documentId']), 0, SOURCE)


def analyze(client, path, accepted, index, expected, historical):
    """Submit the saved selection, verify its unchanged UI binding and poll to a solver verdict."""
    artifact = accepted['artifact']
    descriptor = artifact['analysisDescriptors'][index]
    intent = {'acceptedRevision': accepted['revision'], 'draftEpoch': 17, 'exactSourceHash': artifact['sourceHash'],
              'commandKey': descriptor['commandKey']}
    data = client.call(path + '/analyze', intent, 'SUBMITTED')
    key = data['acceptedAnalysisKey']
    assert all(key[k] == artifact[k] for k in ('artifactId', 'sourceHash', 'policyVersion', 'dependencyHash'))
    assert key['commandKey'] == descriptor['commandKey'] and key['options'] == descriptor['options']
    assert key['documentId'] == accepted['documentId'] and key['acceptedRevision'] == accepted['revision']
    assert key['draftEpoch'] == 17 and key['jobAnalysisKey'] == data['job']['analysisKey']
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = client.call(path + '/analysis/' + data['jobId'])
        assert response['acceptedAnalysisKey'] == key and response['historical'] is historical
        status = response['job']['status']
        if status not in ('RUNNING', 'QUEUED'):
            assert status == expected, (status, expected)
            return data['jobId'], key
        time.sleep(.25)
    raise AssertionError('Run analysis did not finish within the frontend polling deadline')


def reject_unbound(client, path, saved, source_hash, command_key):
    """An incorrect hash or command key must fail before the server accepts an analysis."""
    intent = {'acceptedRevision': saved['revision'], 'draftEpoch': 17, 'exactSourceHash': source_hash,
              'commandKey': command_key}
    try:
        client.call(path + '/analyze', intent, 'SUBMITTED')
    except AssertionError as error:
        assert str(error) == 'HTTP 400: INVALID_REQUEST', str(error)
    else:
        raise AssertionError('Accepted an unbound command selection')


def check(client, saved):
    """Exercise old head, historical revision, new policy head, and read-after-analysis."""
    path = path_for(saved['documentId'])
    artifact = saved['artifact']
    assert artifact['source'] == SOURCE and artifact['mode'] == 'BLOCK_SUPPORTED'
    original = client.call(path)
    assert original['artifact'] == artifact
    key = artifact['analysisDescriptors'][0]['commandKey']
    reject_unbound(client, path, saved, '0' * 64, key)
    reject_unbound(client, path, saved, artifact['sourceHash'], 'missing-command')
    empty = client.call(path + '?revision=0')
    assert empty['artifact']['analysisDescriptors'] == []
    reject_unbound(client, path, empty, empty['artifact']['sourceHash'], key)
    job_id, accepted_key = analyze(client, path, saved, 0, 'SAT', False)
    analyze(client, path, saved, 1, 'UNSAT', False)
    assert client.call(path) == original
    current = save(client, path, saved['revision'], SOURCE + '\n// New build fixture revision\n')
    assert current['artifact']['policyVersion'] != saved['artifact']['policyVersion']
    assert current['artifact']['dependencyHash'] != saved['artifact']['dependencyHash']
    previous = client.call(path + '/analysis/' + job_id)
    assert previous['historical'] is True and previous['acceptedAnalysisKey'] == accepted_key
    assert previous['job']['status'] == 'SAT'
    analyze(client, path, saved, 1, 'UNSAT', True)
    analyze(client, path, current, 0, 'SAT', False)
    analyze(client, path, current, 1, 'UNSAT', False)
    assert client.call(path)['artifact'] == current['artifact']
    assert client.call(path + '?revision=' + str(saved['revision']))['artifact'] == saved['artifact']


def main():
    """Run seed before the backend upgrade and check after it in the same disposable workspace."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['seed', 'check']); parser.add_argument('--base', required=True)
    parser.add_argument('--token-file', type=Path, required=True); parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    client = Client(args.base, args.token_file.read_text().strip())
    if args.phase == 'seed':
        with args.fixture.open('x') as output:
            json.dump(seed(client), output)
    else:
        check(client, json.loads(args.fixture.read_text()))
    print(args.phase + ' passed')


if __name__ == '__main__':
    main()
