"""Adversarial finite tests for benchmark fixture-to-commit identity correspondence."""
import copy
import json
from pathlib import Path
import unittest
import uuid

from compare_responses import definitions
from workload_correspondence import verify_committed_module


class WorkloadCorrespondenceTests(unittest.TestCase):
    """Reject changed graphs, aliases and permissive equality despite matching node counts."""

    def setUp(self):
        """Load the original frozen 500-node workload and assign deterministic fresh IDs."""
        root = Path(__file__).resolve().parents[4]
        self.fixture = json.loads((root / 'gates/document/headless-preview-fixture.json').read_text())['module']
        self.remapping = {}
        original = {}
        for index, (_, _, ident) in enumerate(definitions(self.fixture)):
            target = 'server:' + str(uuid.UUID(int=10000 + index, version=4))
            self.remapping['draft:' + ident.split(':', 1)[1]] = target
            original[ident] = target
        self.committed = json.loads(json.dumps(self.fixture))
        self.replace_fixture_values(self.committed, original)

    def replace_fixture_values(self, value, mapping):
        """Prepare a synthetic positive response independently of the production normalizer."""
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and item in mapping:
                    value[key] = mapping[item]
                else:
                    self.replace_fixture_values(item, mapping)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str) and item in mapping:
                    value[index] = mapping[item]
                else:
                    self.replace_fixture_values(item, mapping)

    def rejected(self, module=None, mapping=None, fixture=None):
        """Require an explicit rejection from any mutated input combination."""
        with self.assertRaises(ValueError):
            verify_committed_module(self.fixture if fixture is None else fixture,
                                    self.committed if module is None else module,
                                    self.remapping if mapping is None else mapping)

    def test_original_500_node_graph(self):
        """A complete fresh-ID remapping preserves the exact original workload."""
        result = verify_committed_module(self.fixture, self.committed, self.remapping)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['nodes'], 500)
        self.assertEqual(result['definitions'], 504)

    def test_same_size_wrong_edge(self):
        """A changed signature reference cannot pass merely because 500 nodes remain."""
        changed = copy.deepcopy(self.committed)
        changed['nodes'][0]['targetId'] = changed['signatures'][1]['id']
        self.rejected(module=changed)

    def test_swapped_operand_order(self):
        """Commutative operators still retain the original ordered benchmark edges."""
        changed = copy.deepcopy(self.committed)
        node = next(item for item in changed['nodes'] if item['tag'] == 'and')
        node['leftId'], node['rightId'] = node['rightId'], node['leftId']
        self.rejected(module=changed)

    def test_swapped_definition_order(self):
        """Reordered declarations are not silently accepted as an equivalent graph."""
        changed = copy.deepcopy(self.committed)
        changed['signatures'].reverse()
        self.rejected(module=changed)

    def test_alias_missing_surplus_and_swapped_mapping(self):
        """Remapping must be complete, injective and agree with each definition position."""
        keys = list(self.remapping)
        missing = dict(self.remapping); missing.pop(keys[0])
        surplus = dict(self.remapping, extra=self.remapping[keys[0]])
        alias = dict(self.remapping); alias[keys[1]] = alias[keys[0]]
        swapped = dict(self.remapping)
        swapped[keys[0]], swapped[keys[1]] = swapped[keys[1]], swapped[keys[0]]
        for mapping in (missing, surplus, alias, swapped):
            self.rejected(mapping=mapping)

    def test_duplicate_definition(self):
        """A duplicate output identity fails before complete graph comparison."""
        changed = copy.deepcopy(self.committed)
        changed['nodes'][1]['id'] = changed['nodes'][0]['id']
        self.rejected(module=changed)

    def test_generated_ids_reuse_fixture_uuid(self):
        """Changing only draft prefixes cannot count as fresh server identity allocation."""
        mapping = {key: 'server:' + key[6:] for key in self.remapping}
        originals = {ident: 'server:' + ident.split(':', 1)[1] for _, _, ident in definitions(self.fixture)}
        committed = copy.deepcopy(self.fixture)
        self.replace_fixture_values(committed, originals)
        with self.assertRaisesRegex(ValueError, 'workload_generated_alias_fixture'):
            verify_committed_module(self.fixture, committed, mapping)

    def test_tags_literals_and_unknown_fields(self):
        """Tags, visible names and closed schema fields are never normalized away."""
        variants = []
        for key, value in (('tag', 'field_ref'), ('surplus', 'ignored')):
            changed = copy.deepcopy(self.committed); changed['nodes'][0][key] = value
            variants.append(changed)
        changed = copy.deepcopy(self.committed); changed['signatures'][0]['name'] = 'Changed'
        variants.append(changed)
        for module in variants:
            self.rejected(module=module)

    def test_exact_scalar_types(self):
        """Boolean and floating-point aliases cannot satisfy integer workload fields."""
        for value in (True, 1.0):
            changed = copy.deepcopy(self.committed); changed['version'] = value
            self.rejected(module=changed)

    def test_canonical_generated_identity(self):
        """Uppercase, draft, non-v4, non-string and malformed targets are rejected."""
        key = next(iter(self.remapping))
        for value in ('server:' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'test')),
                      'server:FFFFFFFF-FFFF-4FFF-8FFF-FFFFFFFFFFFF', 'draft:' + str(uuid.uuid4()),
                      'server:invalid', True, None):
            mapping = dict(self.remapping); mapping[key] = value
            self.rejected(mapping=mapping)

    def test_undeclared_reference_in_both_inputs(self):
        """Identically malformed dangling references cannot establish correspondence."""
        fixture = copy.deepcopy(self.fixture); committed = copy.deepcopy(self.committed)
        fixture['nodes'][0]['targetId'] = 'server:' + str(uuid.uuid4())
        committed['nodes'][0]['targetId'] = fixture['nodes'][0]['targetId']
        self.rejected(module=committed, fixture=fixture)

    def test_literal_looks_like_identity(self):
        """Even an ID-looking name remains exact and is never replaced by remapping."""
        fixture = copy.deepcopy(self.fixture); committed = copy.deepcopy(self.committed)
        literal = fixture['nodes'][0]['id']
        fixture['signatures'][0]['name'] = literal
        committed['signatures'][0]['name'] = literal
        verify_committed_module(fixture, committed, self.remapping)
        committed['signatures'][0]['name'] = committed['nodes'][0]['id']
        self.rejected(module=committed, fixture=fixture)

    def test_missing_module_and_cross_prefix_collision(self):
        """Absent modules and server/draft IDs that collapse to one draft are rejected."""
        with self.assertRaises(ValueError):
            verify_committed_module(None, self.committed, self.remapping)
        fixture = copy.deepcopy(self.fixture)
        fixture['signatures'][0]['id'] = 'server:' + fixture['nodes'][0]['id'][6:]
        self.rejected(fixture=fixture)


if __name__ == '__main__':
    unittest.main()
