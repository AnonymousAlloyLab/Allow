"""Bind a committed benchmark graph to its frozen input, permitting only fresh IDs.

The checker does not infer graph equivalence or use node count as a substitute
for content. Definition positions, edge order, names, types and literals remain
exact. Its schema dependency must be frozen with this module before a trial.
"""
import hashlib
import json
import uuid

from compare_responses import check_module, definitions, id_slot, identical, server_id


def require(condition, reason):
    """Reject malformed evidence without including graph content in the exception."""
    if not condition:
        raise ValueError('workload_' + reason)


def payload_hash(value):
    """Hash a canonical JSON value while preserving JSON number and boolean types."""
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def rewrite_ids(value, mapping, path=('data', 'module')):
    """Rewrite only schema-declared identity slots; leave ID-looking literals intact."""
    if isinstance(value, dict):
        return {key: rewrite_ids(item, mapping, path + (key,)) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_ids(item, mapping, path + (index,)) for index, item in enumerate(value)]
    if isinstance(value, str) and id_slot(path):
        require(value in mapping, 'undeclared_reference')
        return mapping[value]
    return value


def fresh_server_id(value):
    """Recognize only canonical server identities containing RFC4122 version-four UUIDs."""
    return (server_id(value) and uuid.UUID(value[7:]).version == 4
            and uuid.UUID(value[7:]).variant == uuid.RFC_4122)


def checked_definitions(module):
    """Require the closed module schema and unique definitions before reading identities."""
    require(isinstance(module, dict), 'module_required')
    try:
        check_module(module)
        return definitions(module)
    except (AssertionError, KeyError, TypeError, AttributeError, ValueError):
        raise ValueError('workload_module_schema') from None


def verify_committed_module(fixture_module, committed_module, id_remapping):
    """Verify exact input-to-commit correspondence and return hash-bound mapping metadata."""
    declared = checked_definitions(fixture_module)
    actual = checked_definitions(committed_module)
    require(isinstance(id_remapping, dict), 'remapping_object')
    draft_ids = {}
    for _, _, ident in declared:
        require(isinstance(ident, str) and ident.startswith(('server:', 'draft:')), 'fixture_id')
        canonical = 'server:' + ident.split(':', 1)[1]
        require(fresh_server_id(canonical), 'fixture_canonical_uuid')
        draft_ids[ident] = 'draft:' + canonical[7:]
    require(len(set(draft_ids.values())) == len(declared), 'draft_alias_collision')
    require(set(id_remapping) == set(draft_ids.values()), 'exact_remapping_keys')
    values = list(id_remapping.values())
    require(all(fresh_server_id(value) for value in values), 'generated_id')
    require(len(set(values)) == len(values), 'noninjective_remapping')
    originals = {'server:' + ident.split(':', 1)[1] for ident in draft_ids}
    require(not set(values).intersection(originals), 'generated_alias_fixture')
    mapping = {ident: id_remapping[draft] for ident, draft in draft_ids.items()}
    resolved = [(position, kind, mapping[ident]) for position, kind, ident in declared]
    require(resolved == actual, 'definition_positions')
    expected = rewrite_ids(fixture_module, mapping)
    require(identical(expected, committed_module), 'complete_module_changed')
    return {'status': 'PASS', 'definitions': len(declared), 'nodes': len(fixture_module['nodes']),
            'fixture_module_sha256': payload_hash(fixture_module),
            'committed_module_sha256': payload_hash(committed_module),
            'id_remapping_sha256': payload_hash(id_remapping),
            'permitted_change': 'Fresh IDs in closed schema slots only; exact definition/reference bijection.'}
