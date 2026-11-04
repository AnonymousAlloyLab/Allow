"""Compare complete private worker responses with schema-scoped generated-ID bijections.

This is a finite test oracle, not semantic equivalence of JVM implementations.
Source bytes, diagnostics, offsets, old identities and reference edges stay exact.
"""
import copy
import hashlib
import json
import math
import re
import uuid

ID = re.compile(r'server:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')
COLLECTIONS = {'signatures':'signature','fields':'field','predicates':'predicate',
               'facts':'fact','assertions':'assertion','commands':'command','nodes':'expression'}
ID_FIELDS = {'id','targetId','ownerSignatureId','predicateId','bodyId','operandId',
             'leftId','rightId','signatureId'}
ID_ARRAYS = {'rangeColumns','columns','arguments'}
RESULT_FIELDS = {'mode','source','sourceHash','module','occurrences','trivia',
                 'analysisDescriptors','diagnostics','idRemapping'}


def require(condition, reason):
    """Fail a comparison deterministically without printing model content."""
    if not condition:
        raise AssertionError(reason)


def unique(pairs):
    """Reject duplicate JSON keys before a decoder can erase a discrepancy."""
    value = {}
    for key, item in pairs:
        require(key not in value, 'DUPLICATE_JSON_FIELD')
        value[key] = item
    return value


def decode(raw):
    """Read a single exact UTF8 private response with finite JSON values."""
    require(isinstance(raw, bytes) and raw.endswith(b'\n') and len(raw) <= 1048577,
            'RESPONSE_FRAMING')
    require(b'\n' not in raw[:-1] and b'\r' not in raw, 'MULTIPLE_RESPONSE_LINES')
    def nonfinite(_):
        raise AssertionError('NONFINITE_JSON')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    finite(value)
    return value


def finite(value):
    """Reject nonfinite decoded numbers including overflow such as 1e9999."""
    if isinstance(value,dict):
        for item in value.values(): finite(item)
    elif isinstance(value,list):
        for item in value: finite(item)
    elif isinstance(value,float):
        require(math.isfinite(value),'NONFINITE_JSON')


def identical(left, right):
    """Compare JSON values without Python's boolean/integer/float coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left,dict):
        return left.keys()==right.keys() and all(identical(left[key],right[key]) for key in left)
    if isinstance(left,list):
        return len(left)==len(right) and all(identical(a,b) for a,b in zip(left,right))
    return left==right


def definitions(module):
    """Enumerate declared identities by stable typed structural positions."""
    if module is None:
        return []
    require(isinstance(module, dict), 'MODULE_SHAPE')
    rows = []
    for collection, kind in COLLECTIONS.items():
        require(isinstance(module.get(collection), list), 'MODULE_COLLECTION')
        for index, item in enumerate(module[collection]):
            prefix = (collection, index)
            rows.append((prefix + ('id',), kind, item['id']))
            if collection == 'predicates':
                for number, parameter in enumerate(item['parameters']):
                    rows.append((prefix + ('parameters',number,'id'), 'binder', parameter['id']))
            if collection == 'nodes' and 'binder' in item:
                rows.append((prefix + ('binder','id'), 'binder', item['binder']['id']))
    require(len({row[2] for row in rows}) == len(rows), 'DUPLICATE_DEFINITION_ID')
    return rows


def server_id(value):
    """Require canonical server UUIDs only where generated identities are declared."""
    return isinstance(value,str) and ID.fullmatch(value) is not None and str(uuid.UUID(value[7:])) == value[7:]


def check_response(value, frame):
    """Validate the closed top-level/result schema and independent source digest."""
    require(isinstance(value,dict) and set(value) == {'protocol','requestId','status','data'}, 'RESPONSE_SHAPE')
    require(type(value['protocol']) is int and value['protocol'] == 1, 'RESPONSE_PROTOCOL')
    require(value['requestId'] == frame['requestId'], 'RESPONSE_NONCE')
    require(value['status'] in {'VALIDATED','INVALID','UNAVAILABLE'}, 'RESPONSE_STATUS')
    data = value['data']
    require(isinstance(data,dict), 'RESPONSE_DATA')
    if value['status'] == 'UNAVAILABLE':
        require(data == {}, 'UNAVAILABLE_SHAPE')
    elif value['status'] == 'INVALID':
        require(set(data) == {'code','diagnostics'} and isinstance(data['diagnostics'],list), 'INVALID_SHAPE')
        require(isinstance(data['code'],str) and bool(data['code']), 'INVALID_CODE')
        check_diagnostics(data['diagnostics'])
    else:
        require(set(data) == RESULT_FIELDS, 'VALIDATED_SHAPE')
        require(isinstance(data['source'],str), 'SOURCE_TYPE')
        require(hashlib.sha256(data['source'].encode()).hexdigest() == data['sourceHash'], 'SOURCE_HASH')
        require(data['mode'] in {'BLOCK_SUPPORTED','TEXT_ONLY'}, 'SUPPORT_MODE')
        require((data['module'] is None) == (data['mode'] == 'TEXT_ONLY'), 'MODULE_MODE')
        require(all(isinstance(data[key],list) for key in ('occurrences','trivia','analysisDescriptors','diagnostics')),
                'RESULT_ARRAYS')
        require(isinstance(data['idRemapping'],dict), 'REMAPPING_SHAPE')
        check_module(data['module'])
        check_metadata(data)


def closed(value, fields):
    """Require a schema object to contain exactly its registered field names."""
    require(isinstance(value,dict) and set(value) == set(fields.split()), 'CLOSED_MODULE_SHAPE')


def integer(value):
    """Accept JSON integer scalars without boolean or floating-point coercion."""
    require(type(value) is int,'INTEGER_REQUIRED')


def strings(value):
    """Require an explicitly typed string array in the released identity grammar."""
    require(isinstance(value,list) and all(isinstance(item,str) for item in value),'STRING_ARRAY_REQUIRED')


def check_diagnostics(items):
    """Keep the worker's closed diagnostic schema exact and free of normalization."""
    for item in items:
        closed(item,'code message')
        require(all(isinstance(item[key],str) for key in item),'DIAGNOSTIC_TYPES')


def check_metadata(data):
    """Validate closed locations, trivia anchors, descriptors and diagnostic records."""
    check_diagnostics(data['diagnostics'])
    for item in data['occurrences']:
        closed(item,'nodeId role occurrenceId startUtf16 endUtf16')
        require(all(isinstance(item[key],str) for key in ('nodeId','role','occurrenceId')),'OCCURRENCE_TYPES')
        require(item['role'] in {'expression','operator','reference','binder'},'OCCURRENCE_ROLE')
        require(item['occurrenceId']==item['nodeId']+':'+item['role'],'OCCURRENCE_ID')
        integer(item['startUtf16']); integer(item['endUtf16'])
    for index,item in enumerate(data['trivia']):
        closed(item,'commentId order startByte endByte anchor')
        require(isinstance(item['commentId'],str),'TRIVIA_ID_TYPE')
        for key in ('order','startByte','endByte'): integer(item[key])
        require(item['order']==index,'TRIVIA_ORDER')
        anchor = item['anchor']
        shapes = {'module-leading':'kind','module-trailing':'kind','orphan':'kind',
                  'declaration':'kind side declarationId','binder':'kind side binderId',
                  'expression':'kind side nodeId role'}
        require(isinstance(anchor,dict) and anchor.get('kind') in shapes,'ANCHOR_KIND')
        closed(anchor,shapes[anchor['kind']])
        require(all(isinstance(value,str) for value in anchor.values()),'ANCHOR_TYPES')
    for item in data['analysisDescriptors']:
        fields = 'index kind label options' + (' irCommandId' if data['mode']=='BLOCK_SUPPORTED' else '')
        closed(item,fields)
        integer(item['index'])
        require(isinstance(item['label'],str) and item['kind'] in {'run','check'},'COMMAND_TYPES')
        if 'irCommandId' in item: require(isinstance(item['irCommandId'],str),'COMMAND_ID_TYPE')
        check_options(item['options'])


def check_options(options):
    """Require exact parser command options including sentinel integers and scopes."""
    numbers = 'overall bitwidth maxseq minprefix maxprefix maxstring expects'
    closed(options,numbers+' scopes additionalExactScopes')
    for key in numbers.split(): integer(options[key])
    require(isinstance(options['scopes'],list),'SCOPES_ARRAY')
    strings(options['additionalExactScopes'])
    for scope in options['scopes']:
        closed(scope,'signatureLabel isExact startingScope endingScope increment')
        require(isinstance(scope['signatureLabel'],str) and type(scope['isExact']) is bool,'SCOPE_TYPES')
        for key in ('startingScope','endingScope','increment'): integer(scope[key])


def check_module(module):
    """Reject unknown nested module fields rather than widening ID normalization."""
    if module is None:
        return
    closed(module,'version signatures fields predicates facts assertions commands nodes')
    require(type(module['version']) is int and module['version']==1,'MODULE_VERSION')
    shapes = {'signature':'tag id name multiplicity','field':'tag id name ownerSignatureId rangeColumns multiplicity',
              'predicate':'tag id name parameters bodyId','fact':'tag id name bodyId','assertion':'tag id name bodyId',
              'run':'tag id targetId uniformScope bitwidth maxseq','check':'tag id targetId uniformScope bitwidth maxseq',
              'predicate_call':'tag id predicateId arguments','all_quant':'tag id binder bodyId',
              'some_quant':'tag id binder bodyId'}
    for tag in ('signature_ref','field_ref','variable_ref'):
        shapes[tag] = 'tag id targetId'
    for tag in ('not','some_test','no_test','one_test','lone_test','transpose'):
        shapes[tag] = 'tag id operandId'
    for tag in ('and','or','implies','iff','equal','subset','union','intersection','difference','join','product'):
        shapes[tag] = 'tag id leftId rightId'
    for collection in COLLECTIONS:
        require(isinstance(module[collection],list), 'MODULE_COLLECTION')
        for item in module[collection]:
            require(item.get('tag') in shapes, 'MODULE_TAG')
            allowed = ({'run','check'} if collection=='commands' else
                       set(shapes)-{'signature','field','predicate','fact','assertion','run','check'}
                       if collection=='nodes' else {COLLECTIONS[collection]})
            require(item['tag'] in allowed,'COLLECTION_TAG')
            closed(item,shapes[item['tag']])
            for key,value in item.items():
                if key in {'uniformScope','bitwidth','maxseq'}: integer(value)
                elif key in ID_ARRAYS: strings(value)
                elif key not in {'parameters','binder'}: require(isinstance(value,str),'MODULE_SCALAR_TYPE')
            require(isinstance(item.get('parameters',[]),list),'PARAMETERS_ARRAY')
            for parameter in item.get('parameters',[]):
                closed(parameter,'tag id name columns')
                require(all(isinstance(parameter[key],str) for key in ('tag','id','name')),'PARAMETER_TYPES')
                require(parameter['tag']=='parameter','PARAMETER_TAG')
                strings(parameter['columns'])
            if 'binder' in item:
                closed(item['binder'],'id name signatureId')
                require(all(isinstance(value,str) for value in item['binder'].values()),'BINDER_TYPES')


def mapping_for(left, right, frame):
    """Derive injective typed correspondence without inferring it from reference edges."""
    old = set(frame['ownedIdInventory'])
    base = frame['baseArtifact']
    if isinstance(base,dict):
        old.update(row[2] for row in definitions(base.get('module')))
        old.update(item['commentId'] for item in base.get('trivia',[]))
    pairs, inverse = {}, {}
    def bind(a, b):
        require(server_id(a) and server_id(b), 'NONCANONICAL_GENERATED_ID')
        if a in old or b in old:
            require(a == b, 'EXISTING_ID_CHANGED')
            return
        require(all(uuid.UUID(value[7:]).version==4 and uuid.UUID(value[7:]).variant==uuid.RFC_4122
                    for value in (a,b)), 'FRESH_ID_NOT_UUID4')
        require(a not in pairs or pairs[a] == b, 'INCONSISTENT_ID_MAPPING')
        require(b not in inverse or inverse[b] == a, 'NONINJECTIVE_ID_MAPPING')
        pairs[a], inverse[b] = b, a
    first, second = left['idRemapping'], right['idRemapping']
    require(set(first) == set(second), 'REMAPPING_KEYS_CHANGED')
    candidate = frame.get('candidate')
    if isinstance(candidate,dict) and candidate.get('mode') == 'BLOCK_SUPPORTED':
        declared = definitions(candidate['module'])
        expected = {row[2] for row in declared if row[2].startswith('draft:')}
        require(set(first) == expected, 'REMAPPING_DEFINITIONS_MISSING')
        for result in (left,right):
            actual = definitions(result['module'])
            resolved = [(position,kind,result['idRemapping'].get(ident,ident)) for position,kind,ident in declared]
            require(resolved==actual,'CANDIDATE_DEFINITION_IDENTITY_CHANGED')
    else:
        require(not first, 'UNEXPECTED_REMAPPING')
    for key in first:
        require(first[key] not in old and second[key] not in old, 'FRESH_REMAPPING_ALIASES_EXISTING_ID')
        bind(first[key],second[key])
    a, b = definitions(left['module']), definitions(right['module'])
    require([(p,k) for p,k,_ in a] == [(p,k) for p,k,_ in b], 'DEFINITION_SHAPE_CHANGED')
    for (_,_,x),(_,_,y) in zip(a,b):
        bind(x,y)
    require(len(left['trivia']) == len(right['trivia']), 'TRIVIA_COUNT_CHANGED')
    for result in (left, right):
        ids = [row[2] for row in definitions(result['module'])]
        ids.extend(item['commentId'] for item in result['trivia'])
        require(len(ids) == len(set(ids)), 'DUPLICATE_TRIVIA_OR_DEFINITION_ID')
    for x,y in zip(left['trivia'],right['trivia']):
        bind(x['commentId'],y['commentId'])
    return pairs


def id_slot(path):
    """Permit normalization only in documented module, location and metadata ID fields."""
    if len(path) < 3 or path[0] != 'data':
        return False
    if path[1] == 'module':
        return path[-1] in ID_FIELDS or len(path) >= 4 and path[-2] in ID_ARRAYS
    if path[1] == 'idRemapping' and len(path) == 3:
        return True
    if path[1] == 'occurrences':
        return len(path) == 4 and path[-1] == 'nodeId'
    if path[1] == 'analysisDescriptors':
        return len(path) == 4 and path[-1] == 'irCommandId'
    if path[1] == 'trivia':
        return (len(path) == 4 and path[-1] == 'commentId' or len(path) == 5
                and path[-2] == 'anchor' and path[-1] in {'nodeId','declarationId','binderId'})
    return False


def normalize(value, mapping, path=()):
    """Translate declared ID values while retaining all literals, offsets, arrays and fields."""
    if isinstance(value,dict):
        return {key:normalize(item,mapping,path+(key,)) for key,item in value.items()}
    if isinstance(value,list):
        return [normalize(item,mapping,path+(index,)) for index,item in enumerate(value)]
    if isinstance(value,str):
        if id_slot(path):
            return mapping.get(value,value)
        if len(path) == 4 and path[:2] == ('data','occurrences') and path[-1] == 'occurrenceId':
            ident, separator, role = value.rpartition(':')
            require(separator and role in {'expression','operator','reference','binder'}, 'OCCURRENCE_ID')
            return mapping.get(ident,ident)+':'+role
        require(value not in mapping, 'GENERATED_ID_OUTSIDE_SCHEMA')
    return value


def compare(left, right, frame):
    """Require complete output equality after an independently constrained ID bijection."""
    check_response(left,frame)
    check_response(right,frame)
    require(left['status'] == right['status'], 'STATUS_CHANGED')
    mapping = mapping_for(left['data'],right['data'],frame) if left['status'] == 'VALIDATED' else {}
    require(identical(normalize(copy.deepcopy(left),mapping),right), 'COMPLETE_RESPONSE_CHANGED')
    return {'status':'PASS','normalized_generated_ids':len(mapping),'full_response_equal':True}
