"""Finite bootstrap correspondence and raw-failure retention checks."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import http_driver
import http_setup as subject
from harness_common import HERE, read_private, write_private


class SetupTests(unittest.TestCase):
    """Reject changed document/source/graph bindings before any warmups."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-ft1-setup-test-')
        self.root = Path(self.temporary.name)
        self.evidence = self.root/'evidence'
        self.evidence.mkdir()
        fixture_path = self.root/'gates/document/headless-preview-fixture.json'
        fixture_path.parent.mkdir(parents=True)
        fixture_path.write_bytes((HERE.parents[3]/'gates/document/headless-preview-fixture.json').read_bytes())
        self.fixture = json.loads(fixture_path.read_bytes())
        self.block_source = 'canonical block form\n'+self.fixture['source']
        printer = self.root/'backend/target/classes/dev/allow/document/ModulePrinter.class'
        printer.parent.mkdir(parents=True)
        printer.write_bytes(b'finite test printer')
        write_private(self.root/'.gate/http-setup-expectation.json', {'status': 'FROZEN_BEFORE_MEASUREMENT',
                      'fixture_sha256': subject.digest(fixture_path),
                      'fixture_module_sha256': subject.payload_hash(self.fixture['module']),
                      'printer_class_sha256': subject.digest(printer), 'source': self.block_source,
                      'source_sha256': hashlib.sha256(self.block_source.encode()).hexdigest(), 'source_setup_diagnostics': []})
        self.manifest = {'build_identity': {'value': 'a'*64}}
        self.document = 'server:'+str(uuid.UUID(int=99999, version=4))
        self.route = '/api/v1/documents/'+self.document
        declared = subject.checked_definitions(self.fixture['module'])
        mapping = {ident: 'server:'+str(uuid.UUID(int=index+100000, version=4)) for index, (_, _, ident) in enumerate(declared)}
        self.module = subject.rewrite_ids(self.fixture['module'], mapping)
        remapping = {'draft:'+ident.split(':', 1)[1]: value for ident, value in mapping.items()}
        empty = {key: 1 if key == 'version' else [] for key in self.fixture['module']}
        self.created = self.accepted(0, '', empty, {})
        self.committed = self.accepted(1, self.block_source, self.module, remapping)

    def tearDown(self):
        self.temporary.cleanup()

    def accepted(self, revision, source, module, remapping):
        value = hashlib.sha256(source.encode()).hexdigest()
        artifact = {'artifactId': 'server:'+str(uuid.UUID(int=50000+revision, version=4)),
                    'policyVersion': 'test', 'dependencyHash': 'a'*64, 'mode': 'BLOCK_SUPPORTED',
                    'source': source, 'sourceHash': value, 'module': module,
                    'occurrences': [], 'trivia': [], 'analysisDescriptors': []}
        return {'documentId': self.document, 'revision': revision, 'sourceHash': value, 'policyVersion': 'test',
                'artifact': artifact, 'idRemapping': remapping, 'provenance': {'targetRevision': None, 'direction': None}}

    def wire(self, label, route, request, status, data):
        reply = subject.encoded({'protocol': 1, 'requestId': str(uuid.UUID(int=80000, version=4)), 'status': status, 'data': data})
        with patch.object(http_driver, 'raw_http', return_value=(200, reply)):
            http_driver.bootstrap_call(None, route, request, status, self.evidence, label)

    def records(self):
        self.wire('create', '/api/v1/documents', {'idempotencyKey': subject.identifier('create'),
                  'title': '500-node performance fixture'}, 'COMMITTED', self.created)
        self.wire('commit', self.route+'/commit', {'idempotencyKey': subject.identifier('commit'), 'expectedRevision': 0,
                  'candidate': {'mode': 'BLOCK_SUPPORTED', 'module': subject.draft_module(self.fixture['module']),
                                'presentationCopies': []}}, 'COMMITTED', self.committed)
        request = {'draftId': subject.identifier('source'), 'draftEpoch': 0, 'baseRevision': 1,
                   'candidate': {'mode': 'SOURCE', 'source': self.fixture['source']}}
        value = hashlib.sha256(self.fixture['source'].encode()).hexdigest()
        data = {'draftId': request['draftId'], 'draftEpoch': 0, 'baseRevision': 1, 'supportMode': 'BLOCK_SUPPORTED',
                'diagnostics': [], 'proposedSource': self.fixture['source'], 'proposedSourceHash': value,
                'sourceHash': value, 'requestHash': hashlib.sha256(subject.encoded(request)).hexdigest()}
        self.wire('source', self.route+'/validate', request, 'VALIDATED', data)

    def test_valid_original_fixture(self):
        self.records()
        route, module, receipt = subject.verify_setup(self.root, self.evidence, self.manifest)
        self.assertEqual(route, self.route)
        self.assertEqual(receipt['module_correspondence']['nodes'], 500)
        self.assertEqual(module, self.module)

    def test_different_document_rejected(self):
        self.committed['documentId'] = 'server:'+str(uuid.UUID(int=88888, version=4))
        self.records()
        with self.assertRaisesRegex(ValueError, 'same_document'):
            subject.verify_setup(self.root, self.evidence, self.manifest)

    def test_bool_revision_rejected(self):
        self.committed['revision'] = True
        self.records()
        with self.assertRaisesRegex(ValueError, 'document_revision'):
            subject.verify_setup(self.root, self.evidence, self.manifest)

    def test_different_committed_source_rejected(self):
        self.committed['artifact']['source'] += '\n'
        self.records()
        with self.assertRaisesRegex(ValueError, 'artifact_source'):
            subject.verify_setup(self.root, self.evidence, self.manifest)

    def test_different_build_rejected(self):
        self.committed['artifact']['dependencyHash'] = 'b'*64
        self.records()
        with self.assertRaisesRegex(ValueError, 'artifact_build_identity'):
            subject.verify_setup(self.root, self.evidence, self.manifest)

    def test_same_node_count_wrong_edge_rejected(self):
        node = next(row for row in self.module['nodes'] if row['tag'] == 'signature_ref')
        node['targetId'] = self.module['signatures'][1]['id'] if node['targetId'] == self.module['signatures'][0]['id'] else self.module['signatures'][0]['id']
        self.records()
        with self.assertRaises(ValueError):
            subject.verify_setup(self.root, self.evidence, self.manifest)

    def test_failure_raw_reply_and_attempt_retained(self):
        raw = b'{"status":"UNAVAILABLE"}'
        with patch.object(http_driver, 'raw_http', return_value=(503, raw)):
            with self.assertRaises(ValueError):
                http_driver.bootstrap_call(None, '/synthetic', {}, 'COMMITTED', self.evidence, 'commit')
        self.assertEqual((self.evidence/'commit-response.json').read_bytes(), raw)
        self.assertEqual(read_private(self.evidence/'commit-timing.json')['http_status'], 503)

    def test_malformed_raw_reply_retained(self):
        raw = b'{broken'
        with patch.object(http_driver, 'raw_http', return_value=(200, raw)):
            with self.assertRaises(Exception):
                http_driver.bootstrap_call(None, '/synthetic', {}, 'COMMITTED', self.evidence, 'commit')
        self.assertEqual((self.evidence/'commit-response.json').read_bytes(), raw)

    def test_changed_source_preview_rejected(self):
        request = {'draftId': subject.identifier('source'), 'draftEpoch': 0, 'baseRevision': 1,
                   'candidate': {'mode': 'SOURCE', 'source': self.fixture['source']}}
        value = hashlib.sha256(self.block_source.encode()).hexdigest()
        data = {'draftId': request['draftId'], 'draftEpoch': 0, 'baseRevision': 1, 'supportMode': 'BLOCK_SUPPORTED',
                'diagnostics': [], 'proposedSource': self.block_source, 'proposedSourceHash': value,
                'sourceHash': value, 'requestHash': hashlib.sha256(subject.encoded(request)).hexdigest()}
        with self.assertRaisesRegex(ValueError, 'source_preview_bytes'):
            subject.verify_source(data, request, self.fixture['source'])

    def test_changed_source_notice_rejected(self):
        request = {'draftId': subject.identifier('source'), 'draftEpoch': 0, 'baseRevision': 1,
                   'candidate': {'mode': 'SOURCE', 'source': self.fixture['source']}}
        value = hashlib.sha256(self.fixture['source'].encode()).hexdigest()
        expected = [{'code': 'LOCATION_UNAVAILABLE', 'message': 'Some source locations are unavailable.'}]
        changed = [{'code': 'LOCATION_UNAVAILABLE', 'message': 'changed'}]
        data = {'draftId': request['draftId'], 'draftEpoch': 0, 'baseRevision': 1, 'supportMode': 'BLOCK_SUPPORTED',
                'diagnostics': changed, 'proposedSource': self.fixture['source'], 'proposedSourceHash': value,
                'sourceHash': value, 'requestHash': hashlib.sha256(subject.encoded(request)).hexdigest()}
        with self.assertRaisesRegex(ValueError, 'source_support'):
            subject.verify_source(data, request, self.fixture['source'], expected)


if __name__ == '__main__':
    unittest.main()
