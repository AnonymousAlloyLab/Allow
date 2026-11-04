#!/usr/bin/env python3
"""Original serial 500-node 100+1000 HTTP screen, preserving every attempted request/result."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid
import urllib.error
import urllib.request

from harness_common import digest, packed, read_private, write_private
from http_setup import draft_module, envelope, verify_setup


def encode(value):
    """Preserve the original benchmark's UTF-8 wire serialization policy."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def private_bytes(path, value):
    """Retain exact synthetic wire bytes under an exclusive owner-private file."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(value)


def identifier(name):
    """Fix synthetic intent IDs across independent fresh installations."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'allow:fresh-tier1:http:' + name))


def raw_http(client, route, wire):
    """Use the original bounded urllib transport, retaining bytes before any JSON validation."""
    request = urllib.request.Request(client.base+route, wire,
              {'Content-Type': 'application/json', 'Authorization': 'Bearer '+client.token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(1048577)
    except urllib.error.HTTPError as error:
        return error.code, error.read(1048577)


def bootstrap_call(client, route, body, expected, output, label):
    """Retain every setup attempt before validation, including failure responses and cold latency."""
    raw = encode(body)
    private_bytes(output/(label + '-request.json'), raw)
    receipt = {'route': route, 'expected_status': expected, 'request_sha256': hashlib.sha256(raw).hexdigest()}
    start = time.perf_counter_ns()
    try:
        wire = encode(body)
        status, response = raw_http(client, route, wire)
        receipt['elapsed_ms'] = (time.perf_counter_ns() - start) / 1000000
        private_bytes(output/(label + '-response.json'), response)
        receipt.update(http_status=status, response_sha256=hashlib.sha256(response).hexdigest(), response_bytes=len(response))
        if wire != raw or status != 200 or len(response) > 1048576:
            raise ValueError('bootstrap_encoding_or_http_status')
        data = envelope(response, expected)
        receipt['status'] = 'PASS'
        return data
    except BaseException as error:
        receipt.update(status='BLOCKED', failure_class=type(error).__name__)
        raise
    finally:
        receipt.setdefault('elapsed_ms', (time.perf_counter_ns() - start) / 1000000)
        write_private(output/(label + '-timing.json'), receipt)


def bootstrap(client, root, output):
    """Construct the original accepted 500-node state through real authorized HTTP only."""
    fixture = json.loads((root/'gates/document/headless-preview-fixture.json').read_text())
    module = draft_module(fixture['module'])
    created = bootstrap_call(client, '/api/v1/documents', {'idempotencyKey': identifier('create'),
                              'title': '500-node performance fixture'}, 'COMMITTED', output, 'create')
    path = '/api/v1/documents/' + created['documentId']
    initial = {'mode': 'BLOCK_SUPPORTED', 'module': module, 'presentationCopies': []}
    accepted = bootstrap_call(client, path + '/commit', {'idempotencyKey': identifier('commit'),
                               'expectedRevision': 0, 'candidate': initial}, 'COMMITTED', output, 'commit')
    module = accepted['artifact']['module']
    if len(module['nodes']) != 500 or type(accepted['revision']) is not int or accepted['revision'] != 1:
        raise ValueError('original_500_node_fixture_required')
    preview = {'draftId': identifier('source'), 'draftEpoch': 0, 'baseRevision': 1,
               'candidate': {'mode': 'SOURCE', 'source': fixture['source']}}
    checked = bootstrap_call(client, path + '/validate', preview, 'VALIDATED', output, 'source')
    if checked['supportMode'] != 'BLOCK_SUPPORTED' or checked['proposedSource'] != fixture['source']:
        raise ValueError('original_source_roundtrip_failed')
    route, module, correspondence = verify_setup(root, output, read_private(root/'.gate/manifest.json'))
    write_private(output/'setup-correspondence.json', correspondence)
    return route, module


def freeze_requests(root, output, route, module, manifest):
    """Materialize all exact per-start authorized requests before any warmup or measurement."""
    candidate = {'mode': 'BLOCK_SUPPORTED', 'module': copy.deepcopy(module), 'presentationCopies': []}
    leaves = [node for node in candidate['module']['nodes'] if node['tag'] == 'signature_ref']
    signatures = [row['id'] for row in module['signatures']]
    if len(signatures) != 2 or not leaves:
        raise ValueError('original_fixture_shape_required')
    rows = []
    for event in range(1100):
        node = leaves[event % len(leaves)]
        node['targetId'] = signatures[1] if node['targetId'] == signatures[0] else signatures[0]
        request = {'draftId': identifier('edits'), 'draftEpoch': event, 'baseRevision': 1, 'candidate': candidate}
        raw = encode(request)
        target = output/'requests'/f'{event:04d}.json'
        private_bytes(target, raw)
        rows.append({'event': event, 'phase': 'warmup' if event < 100 else 'measured',
                     'path': str(target.relative_to(output)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    value = {'installation_root_sha256': manifest['input_root_sha256'], 'route': route,
             'fixture_sha256': digest(root/'gates/document/headless-preview-fixture.json'), 'files': rows,
             'draft_id': identifier('edits'), 'warmups': 100, 'measured': 1000, 'nodes': 500}
    value['request_root_sha256'] = hashlib.sha256(packed(value)).hexdigest()
    write_private(output/'requests-manifest.json', value)
    return value


def check_response(status, value, request, raw):
    """Require full outer framing and the original request/source binding on each response."""
    if status != 200 or not isinstance(value, dict) or set(value) != {'protocol', 'requestId', 'status', 'data'}:
        raise ValueError('http_response_envelope')
    if type(value['protocol']) is not int or value['protocol'] != 1 or value['status'] != 'VALIDATED' or str(uuid.UUID(value['requestId'])) != value['requestId']:
        raise ValueError('http_response_protocol_status')
    data = value['data']
    expected = {'requestHash', 'draftId', 'draftEpoch', 'baseRevision', 'supportMode', 'diagnostics',
                'proposedSource', 'proposedSourceHash', 'sourceHash'}
    if set(data) != expected or data['supportMode'] != 'BLOCK_SUPPORTED' or data['diagnostics'] != []:
        raise ValueError('http_response_data_fields')
    if any(data[key] != request[key] for key in ('draftId', 'draftEpoch', 'baseRevision')):
        raise ValueError('http_response_request_identity')
    if type(data['draftEpoch']) is not int or type(data['baseRevision']) is not int:
        raise ValueError('http_response_exact_integer_identity')
    if data['requestHash'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('http_response_request_hash')
    source_hash = hashlib.sha256(data['proposedSource'].encode()).hexdigest()
    if data['proposedSourceHash'] != source_hash or data['sourceHash'] != source_hash:
        raise ValueError('http_response_source_hash')


def attempt(client, route, raw, row, output):
    """Retain elapsed time and every raw reply, including rejected/error attempts."""
    result = {'event': row['event'], 'phase': row['phase'], 'request_sha256': row['sha256']}
    request = json.loads(raw)
    response = None
    start = time.perf_counter_ns()
    try:
        wire = encode(request)
        status, response = raw_http(client, route + '/validate', wire)
        value = json.loads(response) if response.startswith(b'{') else None
        result['elapsed_ms'] = (time.perf_counter_ns() - start) / 1000000
        private_bytes(output/'responses'/f'{row["event"]:04d}.json', response)
        result.update(http_status=status, response_sha256=hashlib.sha256(response).hexdigest(), response_bytes=len(response))
        if wire != raw or len(response) > 1048576:
            raise ValueError('original_json_encoding_changed_frozen_request')
        check_response(status, value, request, wire)
        result['status'] = 'PASS'
    except BaseException as error:
        result.setdefault('elapsed_ms', (time.perf_counter_ns() - start) / 1000000)
        result.update(status='BLOCKED', failure_class=type(error).__name__)
        if response is not None and not (output/'responses'/f'{row["event"]:04d}.json').exists():
            private_bytes(output/'responses'/f'{row["event"]:04d}.json', response)
            result.update(http_status=status, response_sha256=hashlib.sha256(response).hexdigest(), response_bytes=len(response))
    return result


def measure(client, output, requests):
    """Run exactly the preregistered order; any failed attempt remains evidence and stops the run."""
    rows = []
    descriptor = os.open(output/'samples.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb', buffering=0) as stream:
        for row in requests['files']:
            raw = (output/row['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('materialized_request_mutation')
            sample = attempt(client, requests['route'], raw, row, output)
            stream.write(packed(sample) + b'\n')
            rows.append(sample)
            if sample['status'] != 'PASS':
                break
    return rows


def summarize(rows):
    """Use strict nearest-rank p95 with complete counts, never averages to rescue a run."""
    samples = [row['elapsed_ms'] for row in rows if row['phase'] == 'measured']
    failures = [row for row in rows if row['status'] != 'PASS']
    complete = len(rows) == 1100 and len(samples) == 1000
    p95 = sorted(samples)[math.ceil(len(samples) * .95) - 1] if samples else None
    return {'status': 'PASS' if complete and not failures and p95 < 300 else 'BLOCKED',
            'warmups': len(rows) - len(samples), 'measured': len(samples), 'required_warmups': 100,
            'required_measured': 1000, 'failures': failures, 'p95_ms': p95,
            'p50_ms': sorted(samples)[math.ceil(len(samples) * .5) - 1] if samples else None,
            'p99_ms': sorted(samples)[math.ceil(len(samples) * .99) - 1] if samples else None,
            'maximum_ms': max(samples) if samples else None, 'strict_p95_threshold_ms': 300,
            'samples': rows, 'memory_gate': 'Parent whole-stack verifier must require memory.peak<=5368709120'}


def main():
    """Accept only a copied private root; leave target-host acceptance explicitly open."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    manifest = read_private(root/'.gate/manifest.json')
    if manifest['copied_root'] != str(root):
        raise ValueError('driver_root_mismatch')
    sys.path.insert(0, str(root/'scripts'))
    from smoke_documents import DocumentClient
    evidence = arguments.output.parent/'http-private'
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    start = time.perf_counter_ns()
    client = DocumentClient()
    try:
        route, module = bootstrap(client, root, evidence)
    except BaseException as error:
        write_private(arguments.output, {'status': 'BLOCKED', 'stage': 'bootstrap', 'failure_class': type(error).__name__,
                      'input_root_sha256': manifest['input_root_sha256'], 'variant': manifest['variant'],
                      'warmups': 0, 'measured': 0, 'verifier_sha256': digest(Path(__file__)),
                      'classification': 'INFRASTRUCTURE_FAILURE_BEFORE_MEASUREMENT', 'target_acceptance': 'OPEN'})
        return 1
    requests = freeze_requests(root, evidence, route, module, manifest)
    bootstrap_ns = time.perf_counter_ns() - start
    report = summarize(measure(client, evidence, requests))
    report.update(input_root_sha256=manifest['input_root_sha256'], variant=manifest['variant'],
                  request_root_sha256=requests['request_root_sha256'], verifier_sha256=digest(Path(__file__)),
                  bootstrap_elapsed_ms=bootstrap_ns / 1000000, classification='TESTED_SCREEN_ONLY', target_acceptance='OPEN')
    report['first_request_elapsed_ms'] = read_private(evidence/'create-timing.json')['elapsed_ms']
    ready = read_private(root/'.gate/evidence/ready.json')
    owner = read_private(root/'.gate/unit-invocation.json')
    report['stack_first_ready_ms'] = (ready['first_ready_monotonic_ns'] - owner['launch_started_monotonic_ns']) / 1000000
    write_private(arguments.output, report)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
