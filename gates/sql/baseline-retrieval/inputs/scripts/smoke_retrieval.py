#!/usr/bin/env python3
"""Verify assembled Spring/React corpus retrieval without logging credentials or corpus contents."""
import hashlib
import json
import math
from pathlib import Path
import re
import time
from smoke_local import Client

ROOT = Path(__file__).resolve().parents[1]


def envelope(response):
    """Require a successful identity-bearing bridge response."""
    status, value = response
    assert status == 200 and value['protocol'] == 1 and value['status'] == 'OK', status
    assert re.fullmatch(r'[a-f0-9-]{36}', value['requestId'])
    return value['data']


def check_results(result, query):
    """Check returned candidate identity, ordering, score arithmetic and complete anonymous pools."""
    assert result['queryRecordId'] == query and result['exact'] is True
    weights = result['weights']
    assert len(weights) == 3 and all(math.isfinite(w) and w >= 0 for w in weights)
    assert abs(sum(weights) - 1) < 1e-9
    assert 0 < len(result['results']) <= 5
    keys = []
    for row in result['results']:
        assert row['recordId'] != query and row['modelId'] == result['modelId']
        assert row['evidenceOnly'] and row['representativeStatus'] == 'CHECKED'
        assert 3 <= row['positiveCount'] <= 5 and 3 <= row['negativeCount'] <= 5
        components = [row['canonicalSimilarity'], row['sharedPositive'], row['sharedNegative']]
        assert all(math.isfinite(x) and 0 <= x <= 1 for x in components)
        assert abs(sum(w * x for w, x in zip(weights, components)) - row['score']) < 1e-9
        if not row['contextCompatible']:
            assert row['sharedPositive'] == row['sharedNegative'] == 0
        assert set(row['structuredContent']) == {'context', 'predicate', 'positives', 'negatives'}
        assert len(row['structuredContent']['positives']) == row['positiveCount']
        assert len(row['structuredContent']['negatives']) == row['negativeCount']
        keys.append((-row['score'], row['recordId']))
    assert keys == sorted(keys)


def main():
    """Exercise authority, strict query inputs, actual vectors, structured retrieval and restart reads."""
    client = Client()
    status, shell = client.request('/', authorized=False)
    assert status == 200 and '<div id="root">' in shell
    scripts = re.findall(r'src="(/assets/[^\"]+\.js)"', shell)
    assert scripts and 'Find related predicates' in client.request(scripts[0], authorized=False)[1]
    for path in ['/api/corpus/status', '/api/corpus/records']:
        assert client.request(path, authorized=False)[0] == 403
        assert client.request(path, headers={'Origin': 'https://hostile.invalid'})[0] == 403
        assert client.request(path, headers={'Host': 'hostile.invalid'})[0] == 403
    counts = envelope(client.request('/api/corpus/status'))
    assert counts['full'] >= 12 and counts['vectors'] >= counts['full']
    records = envelope(client.request('/api/corpus/records'))['records']
    assert records
    query = records[0]['id']
    for bad in [{'recordId': query, 'limit': 0}, {'recordId': query, 'limit': 21},
                {'recordId': query, 'limit': 5, 'validated': True},
                {'recordId': query, 'limit': 5, 'vector': [1]}, {'recordId': 'bad', 'limit': 5}]:
        assert client.request('/api/corpus/search', bad)[0] == 400
    start = time.monotonic()
    result = envelope(client.request('/api/corpus/search', {'recordId': query, 'limit': 5}))
    elapsed = time.monotonic() - start
    check_results(result, query)
    repeated = envelope(client.request('/api/corpus/search', {'recordId': query, 'limit': 5}))
    assert result == repeated, 'A new bridge process must reproduce the same stored ranking'
    report = {'status': 'PASS', 'classification': 'ACTUAL_HTTP_INTEGRATION_NOT_FORMAL_REFINEMENT',
              'checks': ['Built corpus React controls served', 'Authority/Host/Origin enforced',
                         'Client vectors and validation flags rejected', 'Real stored pgvector retrieval',
                         'Full hierarchy and both pools returned', 'Scores and exact-context gates checked',
                         'New bridge process reproduces persisted ranking'],
              'full_records': counts['full'], 'published_vectors': counts['vectors'],
              'candidate_count': result['candidateCount'], 'returned': len(result['results']),
              'model_id': result['modelId'], 'weights': result['weights'],
              'single_request_seconds': elapsed,
              'response_sha256': hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest(),
              'browser_qa': 'NOT_RUN_NO_CONNECTED_BROWSER', 'source_or_authority_recorded': False}
    (ROOT/'gates/retrieval/http-smoke.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
