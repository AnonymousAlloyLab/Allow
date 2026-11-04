"""Exact frozen fixture, document identity and raw bootstrap correspondence checks."""
import hashlib
import json
import math
from pathlib import Path
import uuid

from compare_responses import finite, identical, unique
from harness_common import digest, read_private
from workload_correspondence import checked_definitions, fresh_server_id, payload_hash, rewrite_ids, verify_committed_module


def require(condition, reason):
    """Reject setup evidence without printing private document/model bytes."""
    if not condition:
        raise ValueError('bootstrap_' + reason)


def encoded(value):
    """Match the frozen original HTTP serialization exactly."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def decode(raw):
    """Decode finite complete HTTP JSON without imposing the worker pipe's newline framing."""
    require(type(raw) is bytes and len(raw) <= 1048576, 'json_byte_budget')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                       parse_constant=lambda _: require(False, 'nonfinite_json'))
    finite(value)
    return value


def identifier(name):
    """Bind the original deterministic synthetic operation identities."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'allow:fresh-tier1:http:' + name))


def draft_module(fixture_module):
    """Rewrite only schema identity slots, preserving ID-looking literal values."""
    mapping = {ident: 'draft:'+ident.split(':', 1)[1] for _, _, ident in checked_definitions(fixture_module)}
    return rewrite_ids(fixture_module, mapping)


def envelope(raw, expected):
    """Check the complete closed protocol envelope with type-strict fields."""
    value = decode(raw)
    require(isinstance(value, dict) and set(value) == {'protocol', 'requestId', 'status', 'data'}, 'envelope')
    require(type(value['protocol']) is int and value['protocol'] == 1 and value['status'] == expected, 'protocol_status')
    require(type(value['requestId']) is str and str(uuid.UUID(value['requestId'])) == value['requestId'], 'request_uuid')
    require(isinstance(value['data'], dict), 'data_object')
    return value['data']


def record(evidence, label, expected, route, request):
    """Replay every exact bootstrap request/reply and its independently retained status/hash receipt."""
    raw = (evidence/(label+'-request.json')).read_bytes()
    reply = (evidence/(label+'-response.json')).read_bytes()
    timing = read_private(evidence/(label+'-timing.json'))
    require(raw == encoded(request), 'exact_'+label+'_request')
    require(timing['route'] == route and timing['expected_status'] == expected, 'setup_route_status')
    require(type(timing['http_status']) is int and timing['http_status'] == 200, 'setup_http_status')
    require(timing['request_sha256'] == hashlib.sha256(raw).hexdigest(), 'setup_request_hash')
    require(timing['response_sha256'] == hashlib.sha256(reply).hexdigest(), 'setup_response_hash')
    require(type(timing['response_bytes']) is int and timing['response_bytes'] == len(reply), 'setup_response_bytes')
    require(type(timing['elapsed_ms']) in (int, float) and math.isfinite(timing['elapsed_ms']) and timing['elapsed_ms'] > 0,
            'setup_elapsed_time')
    return envelope(reply, expected)


def committed(data, revision, source, manifest):
    """Bind the durable envelope and source; explicitly scope enrichment fields to schema/type checks."""
    require(set(data) == {'documentId', 'revision', 'sourceHash', 'policyVersion', 'artifact', 'idRemapping', 'provenance'},
            'committed_fields')
    require(fresh_server_id(data['documentId']) and type(data['revision']) is int and data['revision'] == revision,
            'document_revision')
    require(identical(data['provenance'], {'targetRevision': None, 'direction': None}), 'mutation_provenance')
    artifact = data['artifact']
    fields = {'artifactId', 'policyVersion', 'dependencyHash', 'mode', 'source', 'sourceHash', 'module',
              'occurrences', 'trivia', 'analysisDescriptors'}
    require(isinstance(artifact, dict) and set(artifact) == fields, 'artifact_fields')
    require(fresh_server_id(artifact['artifactId']) and artifact['mode'] == 'BLOCK_SUPPORTED', 'artifact_identity_mode')
    require(type(artifact['source']) is str and artifact['source'] == source, 'artifact_source')
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    require(data['sourceHash'] == artifact['sourceHash'] == source_hash, 'artifact_source_hash')
    require(type(data['policyVersion']) is str and data['policyVersion'] == artifact['policyVersion'], 'artifact_policy')
    require(all(type(artifact[name]) is list for name in ('occurrences', 'trivia', 'analysisDescriptors')), 'artifact_enrichment_types')
    if manifest is not None:
        require(artifact['dependencyHash'] == manifest['build_identity']['value'], 'artifact_build_identity')
    return artifact


def verify_setup(root, evidence, manifest=None):
    """Check exact accepted fixture before warmups, and identically during independent parent replay."""
    root, evidence = Path(root), Path(evidence)
    fixture_path = root/'gates/document/headless-preview-fixture.json'
    fixture = decode(fixture_path.read_bytes())
    expectation_path = root/'.gate/http-setup-expectation.json'
    expectation = read_private(expectation_path)
    require(expectation['status'] == 'FROZEN_BEFORE_MEASUREMENT', 'canonical_expectation_not_frozen')
    require(expectation['fixture_sha256'] == digest(fixture_path) and expectation['fixture_module_sha256'] == payload_hash(fixture['module']),
            'canonical_expectation_fixture_binding')
    require(expectation['printer_class_sha256'] == digest(root/'backend/target/classes/dev/allow/document/ModulePrinter.class'),
            'canonical_expectation_printer_binding')
    require(hashlib.sha256(expectation['source'].encode()).hexdigest() == expectation['source_sha256'], 'canonical_expectation_source_hash')
    created = record(evidence, 'create', 'COMMITTED', '/api/v1/documents',
                     {'idempotencyKey': identifier('create'), 'title': '500-node performance fixture'})
    empty = committed(created, 0, '', manifest)
    require(checked_definitions(empty['module']) == [] and identical(created['idRemapping'], {}), 'empty_revision_zero')
    route = '/api/v1/documents/'+created['documentId']
    body = {'idempotencyKey': identifier('commit'), 'expectedRevision': 0,
            'candidate': {'mode': 'BLOCK_SUPPORTED', 'module': draft_module(fixture['module']), 'presentationCopies': []}}
    accepted = record(evidence, 'commit', 'COMMITTED', route+'/commit', body)
    artifact = committed(accepted, 1, expectation['source'], manifest)
    require(accepted['documentId'] == created['documentId'], 'same_document')
    require(accepted['policyVersion'] == created['policyVersion'], 'same_policy')
    mapping = verify_committed_module(fixture['module'], artifact['module'], accepted['idRemapping'])
    require(mapping['nodes'] == 500, 'original_500_nodes')
    source_body = {'draftId': identifier('source'), 'draftEpoch': 0, 'baseRevision': 1,
                   'candidate': {'mode': 'SOURCE', 'source': fixture['source']}}
    source = record(evidence, 'source', 'VALIDATED', route+'/validate', source_body)
    verify_source(source, source_body, fixture['source'], expectation['source_setup_diagnostics'])
    metadata = {'status': 'PASS', 'fixture_sha256': digest(fixture_path), 'module_correspondence': mapping,
                'canonical_print_expectation_sha256': digest(expectation_path),
                'canonical_print_scope': 'F0 baseline-derived expectation; not an independent printer oracle',
                'raw_files': {path.name: digest(path) for path in sorted(evidence.glob('*-*.json'))
                              if path.name.split('-', 1)[0] in {'create', 'commit', 'source'}},
                'artifact_enrichment_scope': 'occurrences/trivia/analysisDescriptors checked as present arrays; exact values are outside this workload correspondence claim'}
    return route, artifact['module'], metadata


def verify_source(data, request, source, expected_diagnostics=None):
    """Bind SOURCE preview to the same revision/request and exact frozen fixture source bytes."""
    require(set(data) == {'requestHash', 'draftId', 'draftEpoch', 'baseRevision', 'supportMode', 'diagnostics',
                          'proposedSource', 'proposedSourceHash', 'sourceHash'}, 'source_preview_fields')
    require(all(identical(data[key], request[key]) for key in ('draftId', 'draftEpoch', 'baseRevision')), 'source_request_identity')
    expected_diagnostics = [] if expected_diagnostics is None else expected_diagnostics
    require(data['supportMode'] == 'BLOCK_SUPPORTED' and identical(data['diagnostics'], expected_diagnostics), 'source_support')
    require(data['requestHash'] == hashlib.sha256(encoded(request)).hexdigest(), 'source_request_hash')
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    require(type(data['proposedSource']) is str and data['proposedSource'] == source, 'source_preview_bytes')
    require(data['sourceHash'] == data['proposedSourceHash'] == source_hash, 'source_preview_hash')
