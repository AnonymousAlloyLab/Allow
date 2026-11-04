"""Exact definition identity/freshness checks under the document transaction lock."""
import uuid
from . import wire

KINDS = {'signatures':'signature','fields':'field','predicates':'predicate','facts':'fact',
         'assertions':'assertion','commands':'command','nodes':'expression'}


def add(result, node, kind, draft):
    """Add one globally unique definition of the expected stable kind."""
    if not isinstance(node,dict) or not isinstance(node.get('id'),str):
        raise ValueError('invalid_definition')
    identifier = node['id']
    if identifier.startswith('draft:') and draft:
        tail = identifier[6:]
        if str(uuid.UUID(tail)) != tail:
            raise ValueError('invalid_draft_id')
    else:
        wire.identifier(identifier)
    if identifier in result:
        raise ValueError('duplicate_definition')
    result[identifier] = kind


def definitions(module, draft=False):
    """Read definitions only, excluding references/source/trivia and registry order."""
    result = {}
    if module is None:
        return result
    if not isinstance(module,dict):
        raise ValueError('invalid_module')
    for collection,kind in KINDS.items():
        items = module.get(collection,[])
        if not isinstance(items,list):
            raise ValueError('invalid_definitions')
        for node in items:
            add(result,node,kind,draft)
            if collection == 'predicates':
                for parameter in node.get('parameters',[]):
                    add(result,parameter,'binder',draft)
            if collection == 'nodes' and 'binder' in node:
                add(result,node['binder'],'binder',draft)
    return result


def history(connection, document):
    """Scan bounded immutable history without creating a second authority index."""
    result = {}
    rows = connection.execute('SELECT content FROM documents.artifact WHERE document_id=%s',(document,))
    for row in rows:
        module = wire.decode(bytes(row['content']),wire.MAX_RESPONSE)['module']
        for identifier,kind in definitions(module).items():
            if identifier in result and result[identifier] != kind:
                raise ValueError('historical_kind_collision')
            result[identifier] = kind
    return result


def check(connection, row, original, artifact, outcome):
    """Bind raw definitions/remapping and reject even same-kind historical collisions."""
    if row['operation'] in ('CREATE','HISTORY_COPY'):
        return
    prior = history(connection,row['document_id'])
    current = definitions(artifact['module'])
    remapping = outcome.get('data',{}).get('idRemapping')
    if not isinstance(remapping,dict):
        raise ValueError('missing_remapping')
    candidate = original['candidate']
    if candidate['mode'] == 'SOURCE':
        if remapping or any(identifier in prior for identifier in current):
            raise ValueError('source_id_collision')
        return
    raw = definitions(candidate['module'],draft=True)
    expected = {}
    drafts = {identifier for identifier in raw if identifier.startswith('draft:')}
    if set(remapping) != drafts:
        raise ValueError('remapping_keys_mismatch')
    for identifier,kind in raw.items():
        if identifier.startswith('draft:'):
            assigned = wire.identifier(remapping[identifier])
            if assigned in prior or assigned in expected:
                raise ValueError('fresh_id_collision')
        else:
            assigned = identifier
            if prior.get(identifier) != kind:
                raise ValueError('foreign_or_changed_kind')
        if assigned in expected:
            raise ValueError('remapping_not_injective')
        expected[assigned] = kind
    if current != expected:
        raise ValueError('artifact_definitions_mismatch')
