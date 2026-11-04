#!/usr/bin/env python3
"""Profile actual bounded persistence CLI calls through the mandatory SQL proxy."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import uuid

from smoke_documents import encoded, digest, fingerprint
from verify_sql_runtime import read_status, runtime_identity

ROOT = Path(__file__).resolve().parents[1]


def call(operation, args):
    """Use the same executable, limits and environment as DocumentGateway."""
    nonce = str(uuid.uuid4())
    frame = {'protocol':1, 'requestId':nonce, 'operation':operation, 'args':args}
    command = ['/usr/bin/prlimit', '--as=2147483648', '--cpu=20', '--',
               str(ROOT/'.tools/retrieval-venv/bin/python'), '-m', 'allow_documents.cli']
    environment = {'PYTHONPATH':str(ROOT/'retrieval'),
                   'ALLOW_CORPUS_RUNTIME':str(ROOT/'.runtime/corpus'), 'LANGSMITH_TRACING':'false'}
    start = time.perf_counter_ns()
    result = subprocess.run(command, input=encoded(frame), capture_output=True, timeout=20,
                            check=True, cwd=ROOT, env=environment)
    elapsed = (time.perf_counter_ns()-start)/1000000
    assert len(result.stdout) <= 1572864
    response = json.loads(result.stdout)
    assert response['protocol'] == 1 and response['requestId'] == nonce and response['status'] == 'OK'
    return response['data'], elapsed


def identities(value):
    """Collect bounded fixture identities without exporting their values."""
    result = set()
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if isinstance(item.get('id'), str):
                result.add(item['id'])
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return sorted(result)


def main():
    """Retain three read and three ownership samples; no acceptance target is inferred."""
    files, source_root = fingerprint()
    status_path = ROOT/'.runtime/corpus/sql-proxy/status.json'
    before = read_status(status_path)
    assert runtime_identity(before)['status'] == 'PASS'
    listing, _ = call('list', {})
    candidates = [row for row in listing['documents'] if row['title'] == '500-node performance fixture']
    assert candidates, 'Run the authored full server fixture first'
    document = candidates[0]['documentId']
    accepted, _ = call('read', {'documentId':document, 'revision':None})
    module = accepted['artifact']['module']
    assert module is not None and len(module['nodes']) == 500
    wanted = identities(module)
    samples = {'read':[], 'ownedIds':[]}
    for _ in range(3):
        read_result, elapsed = call('read', {'documentId':document, 'revision':None})
        assert read_result == accepted
        samples['read'].append(elapsed)
        owned, elapsed = call('ownedIds', {'documentId':document, 'ids':wanted})
        assert sorted(owned['ids']) == wanted
        samples['ownedIds'].append(elapsed)
    after = read_status(status_path)
    runtime = runtime_identity(after, before)
    unchanged = fingerprint()[1] == source_root
    report = {'status':'PASS' if unchanged and runtime['status'] == 'PASS' else 'FAIL',
              'classification':'SMALL_COMPONENT_PROFILE_NOT_ACCEPTANCE_BENCHMARK',
              'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'samples_ms':samples,
              'fixture_nodes':500, 'owned_identity_count':len(wanted),
              'source_or_authority_exported':False, 'source_unchanged':unchanged,
              'source_sha256':files, 'input_root_sha256':source_root,
              'runtime_identity':runtime, 'verifier_sha256':digest(Path(__file__).read_bytes()),
              'limits':'Three samples per actual CLI operation on a shared host, including Python startup and proxy/database work; no latency-target acceptance claim.'}
    output = ROOT/'gates/document/persistence-profile-sealed.json'
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status', 'samples_ms', 'source_unchanged')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
