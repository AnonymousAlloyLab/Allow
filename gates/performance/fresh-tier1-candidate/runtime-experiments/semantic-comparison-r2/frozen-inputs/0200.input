"""Materialize deterministic public/synthetic frames before differential execution.

The shared checker corpus carries its original checker oracle independently of
the full worker result. Authoring observations never count as selection evidence.
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import uuid

from compare_responses import definitions, ID_FIELDS, ID_ARRAYS

ROOT = Path(__file__).resolve().parents[4]
NAMESPACE = uuid.UUID('d0837213-d460-491d-8a16-cfdbd57a782f')


def encoded(value):
    """Encode deterministic complete JSON bytes without a transport newline."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()


def identity(number, prefix='draft'):
    """Return a stable canonical UUID identity reserved for synthetic fixtures."""
    return f'{prefix}:00000000-0000-4000-8000-{number:012x}'


def base(source=''):
    """Build an integrity-checkable text artifact without claimed syntax projection."""
    return {'mode':'TEXT_ONLY', 'source':source, 'sourceHash':hashlib.sha256(source.encode()).hexdigest(),
            'module':None, 'occurrences':[], 'trivia':[]}


def frame(name, candidate, artifact=None, inventory=None, operation='VALIDATE'):
    """Create the exact closed private document envelope for one named fixture."""
    return {'protocol':1, 'requestId':str(uuid.uuid5(NAMESPACE,name)), 'operation':operation,
            'candidate':candidate, 'baseArtifact':base() if artifact is None else artifact,
            'ownedIdInventory':{} if inventory is None else inventory, 'policyVersion':'document-v1'}


def transform_ids(value, mapping, path=()):
    """Translate only declared module identity slots, leaving names and source literal."""
    if isinstance(value, dict):
        return {key:transform_ids(item,mapping,path+(key,)) for key,item in value.items()}
    if isinstance(value, list):
        return [transform_ids(item,mapping,path+(index,)) for index,item in enumerate(value)]
    if isinstance(value,str) and (path[-1] in ID_FIELDS or len(path)>1 and path[-2] in ID_ARRAYS):
        return mapping.get(value,value)
    return value


def owned(module, mixed=False):
    """Convert all or alternating definitions to fixed owned server identities."""
    rows = definitions(module)
    mapping = {ident:ident.replace('draft:','server:') for index,(_,_,ident) in enumerate(rows)
               if not mixed or index % 2 == 0}
    inventory = {mapping[ident]:kind for _,kind,ident in rows if ident in mapping}
    return transform_ids(module,mapping), inventory


def block(module):
    """Build a complete block candidate without presentation-copy shortcuts."""
    return {'mode':'BLOCK_SUPPORTED', 'module':module, 'presentationCopies':[]}


def blank_module():
    """Create a single-signature predicate skeleton for exact expression boundaries."""
    return {'version':1,'signatures':[{'tag':'signature','id':identity(10000),'name':'A','multiplicity':'set'}],
            'fields':[], 'predicates':[{'tag':'predicate','id':identity(10001),'name':'p','parameters':[],'bodyId':''}],
            'facts':[], 'assertions':[], 'commands':[], 'nodes':[]}


def append_node(module, tag, **references):
    """Allocate one synthetic expression definition and return its ID."""
    ident = identity(len(module['nodes'])+1)
    module['nodes'].append({'id':ident,'tag':tag,**references})
    return ident


def leaf(module):
    """Append a two-node well-typed formula suitable for a disjoint syntax forest."""
    ref = append_node(module,'signature_ref',targetId=module['signatures'][0]['id'])
    return append_node(module,'some_test',operandId=ref)


def balanced(module, count):
    """Construct a balanced ordered conjunction with exactly count disjoint leaves."""
    if count == 1:
        return leaf(module)
    left = balanced(module,count//2)
    right = balanced(module,count-count//2)
    return append_node(module,'and',leftId=left,rightId=right)


def boundary_module(count=None, depth=None):
    """Generate exact node count or root-relative depth with otherwise valid types."""
    module = blank_module()
    root = leaf(module) if depth else balanced(module,(count+1)//3)
    target = depth if depth else count
    while len(module['nodes']) < target:
        root = append_node(module,'not',operandId=root)
    module['predicates'][0]['bodyId'] = root
    return module


def source_fixtures():
    """Declare independent public source status/mode expectations and limits."""
    values = [
        ('source-supported','sig A {}','VALIDATED','BLOCK_SUPPORTED'),
        ('source-text-only','sig A, B {} run {} for 3','VALIDATED','TEXT_ONLY'),
        ('source-syntax','sig {','INVALID',None),
        ('source-unbound','sig A {} fact { some Missing }','INVALID',None),
        ('source-type','sig A {} pred p { A and A }','INVALID',None),
        ('source-import','open util/ordering[A]\nsig A {}','INVALID',None),
        ('source-fragment','sig A {} pred p { some ^(A -> A) }','VALIDATED','TEXT_ONLY'),
        ('source-trivia-crlf','// 😀 café\r\nsig A {}\r\n// between\r\npred p { /* root */ some A }\r\nrun p for 3 but 4 Int, 3 seq\r\n','VALIDATED','BLOCK_SUPPORTED'),
        ('source-uuid-literal','// server:00000000-0000-4000-8000-000000000001\nsig A {}','VALIDATED','BLOCK_SUPPORTED'),
    ]
    for length in (32767,32768,32769):
        prefix = 'sig A {}\n// é'
        source = prefix + 'x'*(length-len(prefix.encode()))
        values.append((f'source-utf8-{length}',source,'VALIDATED' if length<=32768 else 'INVALID',
                       'BLOCK_SUPPORTED' if length<=32768 else None))
    return values


def fixtures():
    """Yield a finite full-worker matrix with provenance and non-timing oracles."""
    corpus = json.loads((ROOT/'backend/src/test/resources/document-type-cases.json').read_text())
    for case in corpus['cases']:
        for variant in ('fresh','owned'):
            module, inventory = (case['module'],{}) if variant=='fresh' else owned(case['module'])
            name = f"typed-{case['caseId']}-{variant}"
            yield name,frame(name,block(module),inventory=inventory),{
                'family':'all46-constructors','expectedStatus':'VALIDATED' if case['expectedAccepted'] else 'INVALID',
                'checkerExpectedAccepted':case['expectedAccepted'],'checkerCase':case['caseId'],
                'checkerOracle':'backend/src/test/resources/document-type-cases.json'}
    sample = next(case['module'] for case in corpus['cases'] if case['caseId']=='some_test-positive')
    module, inventory = owned(sample,True)
    yield 'ids-mixed',frame('ids-mixed',block(module),inventory=inventory),{'family':'identity','expectedStatus':'VALIDATED'}
    for variant in ('missing','foreign','wrong-kind'):
        changed = copy.deepcopy(inventory)
        key = next(iter(changed))
        if variant=='missing': changed.pop(key)
        elif variant=='wrong-kind': changed[key]='command'
        else: changed = {identity(99999,'server'):'signature'}
        name = f'ids-{variant}'
        yield name,frame(name,block(module),inventory=changed),{'family':'identity','expectedStatus':'INVALID'}
    for name,source,status,mode in source_fixtures():
        yield name,frame(name,{'mode':'SOURCE','source':source}),{
            'family':'source','expectedStatus':status,'expectedMode':mode,'sourceUtf8Bytes':len(source.encode())}
    for family,values in (('nodes',(511,512,513)),('depth',(31,32,33))):
        for value in values:
            name = f'{family}-{value}'
            module = boundary_module(**({'count':value} if family=='nodes' else {'depth':value}))
            yield name,frame(name,block(module)),{'family':family,'expectedStatus':'INVALID' if value==values[-1] else 'VALIDATED',
                                               'expectedNodes':len(module['nodes'])}
    for name,source in (('history-text','sig A, B {} run {} for 3'),('history-supported-text','sig A {}')):
        yield name,frame(name,None,base(source),operation='REVALIDATE'),{
            'family':'history','expectedStatus':'VALIDATED','expectedMode':'TEXT_ONLY','historicalExact':True}
    artifact = base('sig A {}\n')
    module = blank_module()
    module['predicates']=[]
    module,inventory = owned(module)
    artifact.update(mode='BLOCK_SUPPORTED',module=module)
    yield 'history-block',frame('history-block',None,artifact,inventory,'REVALIDATE'),{
        'family':'history','expectedStatus':'VALIDATED','expectedMode':'BLOCK_SUPPORTED','historicalExact':True}
    for field,value in (('ownedIdInventory',[]),('policyVersion',''),('baseArtifact',None)):
        name = f'context-invalid-{field}'
        request = frame(name,{'mode':'SOURCE','source':'sig A {}'})
        request[field] = value
        yield name,request,{'family':'private-context','expectedStatus':'UNAVAILABLE'}
    for length in (2097151,2097152,2097153):
        name = f'private-frame-{length}'
        request = frame(name,{'mode':'SOURCE','source':'sig A {}','padding':''})
        request['candidate']['padding'] = 'x'*(length-len(encoded(request)))
        yield name,request,{'family':'private-frame','exactBytes':length,
                           'expectedStatus':'INVALID' if length==2097151 else None,
                           'expectedProbeReject':length>=2097152}


def derived_fixtures(directory):
    """Freeze baseline-authored valid outputs as source roundtrips and exact history.

    These are explicitly derived authoring fixtures, not independent evidence of
    the baseline implementation. Their checks add exact-source/history invariants.
    """
    directory = directory.resolve()
    report = json.loads((directory/'report.json').read_bytes())
    if report.get('mode')!='authoring' or report.get('status')!='PASS':
        raise ValueError('successful_baseline_authoring_required')
    for path in sorted(directory.glob('typed-*-positive-fresh-F0-private.json')):
        probe = json.loads(path.read_bytes())
        result = json.loads(base64.b64decode(probe['responseBase64']))['data']
        provenance = {'authoringOutputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                      'authoringOutputPath':str(path.relative_to(ROOT)),
                      'authoringReportSha256':hashlib.sha256((directory/'report.json').read_bytes()).hexdigest(),
                      'authoringInputsSha256':hashlib.sha256((directory/'inputs.json').read_bytes()).hexdigest(),
                      'authoringBuildIdentity':probe['buildIdentity'],
                      'derivation':'F0 authoring output, frozen before F1; not an independent parser oracle'}
        name = 'roundtrip-'+path.name.removesuffix('-fresh-F0-private.json')
        yield name,frame(name,{'mode':'SOURCE','source':result['source']}),{
            'family':'source-roundtrip','expectedStatus':'VALIDATED',**provenance}
        name = 'history-'+path.name.removesuffix('-fresh-F0-private.json')
        inventory = {ident:kind for _,kind,ident in definitions(result['module'])}
        yield name,frame(name,None,result,inventory,'REVALIDATE'),{
            'family':'history-derived','expectedStatus':'VALIDATED','historicalExact':True,**provenance}
    path = directory/'source-trivia-crlf-F0-private.json'
    probe = json.loads(path.read_bytes())
    result = json.loads(base64.b64decode(probe['responseBase64']))['data']
    inventory = {ident:kind for _,kind,ident in definitions(result['module'])}
    yield 'history-trivia-crlf',frame('history-trivia-crlf',None,result,inventory,'REVALIDATE'),{
        'family':'history-derived','expectedStatus':'VALIDATED','historicalExact':True,
        'authoringOutputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'authoringOutputPath':str(path.relative_to(ROOT)),
        'authoringReportSha256':hashlib.sha256((directory/'report.json').read_bytes()).hexdigest(),
        'authoringInputsSha256':hashlib.sha256((directory/'inputs.json').read_bytes()).hexdigest(),
        'authoringBuildIdentity':probe['buildIdentity'],
        'derivation':'Exact F0 authoring artifact; CRLF/Unicode/comment identity preserved as history.'}
    sources = {
        'sat':'sig Node { edge: set Node } pred p { some Node and all n: Node | n not in n.^edge } run p for 8 but exactly 8 Node',
        'unsat':'sig Node { edge: one Node } fact { all n: Node | n not in n.^edge } run {} for 8 but exactly 8 Node'}
    for classification,source in sources.items():
        for operation in ('VALIDATE','REVALIDATE'):
            for repeat in range(5):
                name = f'heavy-{classification}-{operation.lower()}-{repeat}'
                candidate = {'mode':'SOURCE','source':source} if operation=='VALIDATE' else None
                request = frame(name,candidate,base(source),operation=operation)
                yield name,request,{'family':'heavy-document-regression','expectedStatus':'VALIDATED',
                                   'solverFixtureExpectation':classification.upper(),'operation':operation,
                                   'historicalExact':operation=='REVALIDATE',
                                   'limitation':'Document parse/revalidation only; default WorkerMain solver independently tested.'}


def main():
    """Create an immutable-by-convention new fixture directory and digest inventory."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--derived-from',type=Path)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    rows = []
    selected = derived_fixtures(args.derived_from) if args.derived_from else fixtures()
    for name,request,oracle in selected:
        raw = encoded(request)
        path = args.output/f'{name}.json'
        path.write_bytes(raw)
        path.chmod(0o600)
        rows.append({'name':name,'path':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),**oracle})
    manifest = {'schemaVersion':1,'status':'AUTHORED_NOT_EXECUTED','fixtures':rows,
                'limitations':'Finite public/synthetic corpus; no universal JVM semantics or performance claim.'}
    (args.output/'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps({'status':'AUTHORED','fixtures':len(rows),'output':str(args.output)}))


if __name__ == '__main__':
    main()
