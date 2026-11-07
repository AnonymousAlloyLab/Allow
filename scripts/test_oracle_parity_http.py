#!/usr/bin/python3
"""Check oracle parity with authored fixtures on an explicit private loopback installation."""
import argparse
import copy
import json
from pathlib import Path
import time
import urllib.parse
import uuid
from test_ai_http import Client
from test_block_workbench_http import bound, categories, digest, file_side, rejected, same_request

SOURCE = 'sig Node {}\npred Candidate [items: set Node] { some items }\n'
ORACLE = 'sig Node {}\npred Reference [expected: set Node] { some expected }\n'
OPPOSITE = 'sig Node {}\npred Reference [expected: set Node] { no expected }\n'
VACUOUS = 'fact Impossible { some Node and no Node }\n'


def create(client, source, label):
    """Create and accept one synthetic document without modifying existing models."""
    title = label + ' ' + uuid.uuid4().hex[:8]
    initial = client.call('/api/v1/documents', {'idempotencyKey': str(uuid.uuid4()), 'title': title}, 'COMMITTED')
    path = '/api/v1/documents/' + urllib.parse.quote(initial['documentId'], safe='')
    accepted = client.call(path + '/commit', {'idempotencyKey': str(uuid.uuid4()),
               'expectedRevision': 0, 'candidate': {'mode': 'SOURCE', 'source': source}}, 'COMMITTED')
    assert accepted['artifact']['mode'] == 'BLOCK_SUPPORTED'
    return title, path, accepted


def payload(accepted, oracle):
    """Bind the checked current draft and a real predicate declaration to exact oracle bytes."""
    module = accepted['artifact']['module']
    target = next(item for item in module['predicates'] if item['name'] == 'Candidate')
    return {**bound(accepted), 'candidate': {'mode': 'BLOCK_SUPPORTED', 'module': module,
            'presentationCopies': []}, 'targetId': target['id'],
            'oracle': file_side(oracle, 'Reference'), 'scope': 3}


def parity(client, path, request, classification, statuses):
    """Require exact target/oracle identity and independently replayed four-category evidence."""
    result = client.call(path + '/oracle-parity', request)
    same_request(request, result)
    assert result['targetId'] == request['targetId']
    assert result['oracle'] == {key: request['oracle'][key] for key in ('sourceHash', 'predicate')}
    assert result['right'] == result['oracle']
    assert result['left']['predicate'] == 'Candidate'
    assert result['classification'] == classification
    categories(result, statuses)
    return result


def acceptance(base, token):
    """Exercise equality, difference, draft edits, vacuity, rejection and no-Save boundaries."""
    client = Client(base, token)
    title, path, accepted = create(client, SOURCE, 'Oracle parity browser fixture')
    request = payload(accepted, ORACLE)
    equal = {'both': 'SAT', 'leftOnly': 'UNSAT', 'rightOnly': 'UNSAT', 'neither': 'SAT'}
    different = {'both': 'UNSAT', 'leftOnly': 'SAT', 'rightOnly': 'SAT', 'neither': 'UNSAT'}
    parity(client, path, request, 'AGREEMENT', equal)
    parity(client, path, {**request, 'oracle': file_side(OPPOSITE, 'Reference')}, 'DISTINGUISHED', different)
    edited = copy.deepcopy(request)
    root = accepted['artifact']['module']['predicates'][0]['bodyId']
    next(node for node in edited['candidate']['module']['nodes'] if node['id'] == root)['tag'] = 'no_test'
    parity(client, path, edited, 'DISTINGUISHED', different)
    client.call(path + '/oracle-parity', {**request, 'targetId': root}, 'UNSUPPORTED')
    client.call(path + '/oracle-parity', {**request, 'oracle': file_side(ORACLE + 'fact Required { some Node }', 'Reference')}, 'UNSUPPORTED')
    client.call(path + '/oracle-parity', {**request, 'artifactId': 'stale-artifact'}, 'UNAVAILABLE')
    rejected(base, '', path + '/oracle-parity', {}, 403)
    rejected(base, token, path + '/oracle-parity', {**request, 'operation': 'SAVE'}, 400)
    rejected(base, token, path + '/oracle-parity', {**request, 'oracle': {**request['oracle'], 'sourceHash': '0' * 64}}, 400)
    after = client.call(path)
    assert after['revision'] == 1 and after['artifact']['sourceHash'] == digest(SOURCE)
    empty_title, empty_path, empty = create(client, SOURCE + VACUOUS, 'Oracle parity vacuity fixture')
    parity(client, empty_path, payload(empty, ORACLE + VACUOUS), 'NO_INSTANCES', dict.fromkeys(equal, 'UNSAT'))
    assert client.call(empty_path)['revision'] == 1
    return {'status': 'PASS', 'document_title': title, 'document_id': accepted['documentId'], 'vacuity_title': empty_title,
            'checks': ['nonvacuous bounded equality', 'both directional witnesses', 'unsaved candidate edits',
                       'exact oracle and target echo', 'predicate-only target rejection', 'background mismatch rejection',
                       'stale artifact rejection', 'authority required', 'closed body', 'exact oracle hash',
                       'vacuous context distinguished from equality', 'no automatic Save'], 'provider_calls': 0}


def main():
    """Require an explicit test target and keep the temporary authority out of reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    result = acceptance(args.base, args.token_file.read_text().strip())
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
