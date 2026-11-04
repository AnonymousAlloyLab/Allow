#!/usr/bin/env python3
"""Materialize the approved nonce-free original500 component fixture once."""
import argparse
import hashlib
import json
from pathlib import Path

from harness_common import HERE, ROOT, digest, packed, record, write_private
from http_setup import draft_module
from workload_correspondence import checked_definitions, payload_hash


def materialize():
    """Keep all original graph bytes except the declared definition/reference ID rewrite."""
    original = ROOT/'gates/document/headless-preview-fixture.json'
    historical = HERE/'http-setup-expectation.json'
    seed = HERE/'fixtures/semantic/typed-signature_ref-positive-fresh.json'
    fixture, expectation, prior = [json.loads(p.read_text()) for p in (original, historical, seed)]
    if expectation['fixture_sha256'] != digest(original) or expectation['fixture_module_sha256'] != payload_hash(fixture['module']):
        raise ValueError('latency_fixture_historical_correspondence')
    module = draft_module(fixture['module'])
    if len(module['nodes']) != 500 or len(checked_definitions(module)) != len(checked_definitions(fixture['module'])):
        raise ValueError('latency_original_500_required')
    base = {'mode': 'TEXT_ONLY', 'module': None, 'occurrences': [], 'source': '',
            'sourceHash': hashlib.sha256(b'').hexdigest(), 'trivia': []}
    if prior['baseArtifact'] != base or prior['ownedIdInventory'] != {} or prior['policyVersion'] != 'document-v1':
        raise ValueError('latency_empty_context_seed')
    template = {'protocol': 1, 'operation': 'VALIDATE', 'candidate': {'mode': 'BLOCK_SUPPORTED',
                'module': module, 'presentationCopies': []}, 'baseArtifact': base,
                'ownedIdInventory': {}, 'policyVersion': prior['policyVersion']}
    expected = {'schema': 1, 'source': expectation['source'], 'source_sha256': expectation['source_sha256'],
                'nodes': 500, 'headless_fixture_sha256': digest(original),
                'printer_class_sha256': expectation['printer_class_sha256'],
                'authoring_provenance': {'fixture': record(original), 'canonical_expectation': record(historical),
                                        'context_seed': record(seed), 'draft_transform': record(HERE/'http_setup.py'),
                                        'scope': 'Historical F0-derived canonical printer expectation; no independent printer oracle'}}
    if hashlib.sha256(expected['source'].encode()).hexdigest() != expected['source_sha256']:
        raise ValueError('latency_expected_source_hash')
    write_private(HERE/'latency-fixture.json', template)
    write_private(HERE/'latency-expected.json', expected)
    return {'fixture': record(HERE/'latency-fixture.json'), 'expected': record(HERE/'latency-expected.json')}


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(materialize()))
