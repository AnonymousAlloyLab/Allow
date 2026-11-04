#!/usr/bin/env python3
"""Proposal: preserve287 exact inherited model claims plus this candidate's claims.

Final execution is deliberately opt-in and requires six exact frozen approvals:
  python verify_model_closure.py RUN_ID --execute

closure-runner-config.json must contain candidate_claim_count and reviews (six
{seat,path} entries). Optional guards adds individual workspace-relative files.
review-input-pins.json uses {files:[{path,sha256}],input_root_sha256}, with root
SHA256(canonical compact UTF8 JSON of files). Runner/config/source/type inventory
and every non-derived top-level candidate JSON/Markdown input must be review-pinned. No run is
performed by importing this module. This proves model compilation only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CANDIDATE_SOURCE = HERE/'ValidationContext.lean'
CANDIDATE_TYPES = HERE/'candidate-type-inventory.json'
CANDIDATE_MODULE = 'Allow.ValidationContextCandidate'
CONFIG = HERE/'closure-runner-config.json'
REVIEW_PINS = HERE/'review-input-pins.json'
ANCHOR = ROOT/'gates/sql/immutable-image-candidate/formal-runs/final-287-v2'
ANCHOR_ROOT = '0bfe0fb7b2dcbc16e6d0337193f3b8c4e78615749f3af670d9e5058d05ae9113'
ANCHOR_REPORT_SHA256 = 'd9c471c0ee68550ad110649bdb8f86c3e581ecf30a1acb2cf25aabe696c31c4a'
INHERITED = ['closure/theorem-types.json','spec/implementation-g1-types.json',
             'spec/egraph-types.json','spec/retrieval-types.json','spec/sql-types.json']
REGISTRIES = [
 ('document','Allow.DocumentDraft','formal/Allow/Document.lean','gates/document/draft/types.json',125),
 ('order','Allow.DocumentOrder','formal/Allow/FieldOrder.lean','gates/document/order-amendment/types.json',14),
 ('associativity','Allow.DocumentAssociativity','formal/Allow/Associativity.lean','gates/document/associativity-amendment/types.json',16),
 ('partial','Allow.DocumentPartialTypes','formal/Allow/PartialTypes.lean','gates/document/partial-types-candidate/types.json',13)]
IMAGE_TYPES = ROOT/'gates/sql/immutable-image-candidate/candidate-type-inventory.json'
IMAGE_SOURCE = ROOT/'formal/Allow/ImmutableImageCandidate.lean'
SEATS = {family+'-'+str(seat) for family in ('terra','sol','astra') for seat in (1,2)}
GUARD_DIRECTORIES = ('backend/src','frontend/src','retrieval/allow_documents',
                     'retrieval/allow_retrieval','db/document','config','spec','scripts')
ALLOWED_AXIOMS = {'propext','Quot.sound','Classical.choice'}
ESCAPE = re.compile(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)|debug\.skipKernelTC')
TRUST = ['Lean4.34.1 kernel/elaborator/pretty-printer and bundled libraries',
         'propext, Quot.sound and Classical.choice only when reported by the axiom audit',
         'Pinned Lake/Python verifier and SHA256 collision resistance',
         'Operating system/filesystem/processes and hardware',
         'Interpretation of abstract model definitions; no implementation correspondence']
EXCLUDED = ['Python/Java/PostgreSQL implementation refinement or end-to-end transaction correctness',
            'SQLean grammar implementation, wire framing and subprocess execution correctness',
            'Fresh isolated JVM enforcement, real repeatable-read/read-only behavior and protocol I/O',
            'Runtime resource bounds, privacy, performance300ms target and production promotion']


def require(condition,reason):
    if not condition:
        raise AssertionError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def packed(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def pairs_unique(pairs):
    result = {}
    for key,value in pairs:
        require(key not in result,'DUPLICATE_JSON_FIELD:'+key)
        result[key] = value
    return result


def read(path):
    return json.loads(Path(path).read_text(),object_pairs_hook=pairs_unique)


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def workspace_path(name):
    path = Path(name)
    require('..' not in path.parts,'INVALID_INPUT_PATH:'+name)
    relative = path.relative_to(ROOT) if path.is_absolute() else path
    require(relative.parts and relative.as_posix()!='.','INVALID_INPUT_PATH:'+name)
    require((ROOT/relative).resolve().is_relative_to(ROOT),'INPUT_OUTSIDE_WORKSPACE:'+name)
    return ROOT/relative


def formal_inventory():
    return sorted(path for path in (ROOT/'formal').rglob('*.lean') if '.lake' not in path.parts)


def guard_inventory(config):
    """Freeze complete source inventories, not only an incomplete listed-file subset."""
    paths = {workspace_path(name) for name in config.get('guards',[])}
    for name in GUARD_DIRECTORIES:
        paths.update(path for path in (ROOT/name).rglob('*') if path.is_file()
                     and '__pycache__' not in path.parts and path.suffix!='.pyc')
    return sorted(paths)


def proxy_identity():
    """A continuity guard only; daemon behavior is explicitly not a proved property."""
    ready = ROOT/'.runtime/corpus/sql-proxy/ready.json'
    value = read(ready)
    pid = value['pid']
    require(type(pid) is int and pid>0,'INVALID_PROXY_PID')
    process = Path('/proc')/str(pid)
    return {'ready_sha256':sha(ready),'pid':pid,
        'process_start_ticks':(process/'stat').read_text().rsplit(')',1)[1].split()[19],
        'executable_sha256':sha(process/'exe'),'cmdline_sha256':sha(process/'cmdline')}


def checked_inventory(path,source,namespace,expected_count):
    """Accept only the actual complete default-pretty-printer #check inventory."""
    value = read(path)
    require(value['source_sha256']==sha(source),'TYPE_SOURCE_MISMATCH:'+str(source))
    symbols = value['symbols']
    require(isinstance(symbols,list) and len(symbols)==len(set(symbols))==expected_count,
            'TYPE_SYMBOL_COUNT:'+str(path))
    if 'theorem_types' in value:
        require(set(value['theorem_types'])==set(symbols),'TYPE_INVENTORY_KEYS:'+str(path))
        rows = {symbol:value['theorem_types'][symbol] for symbol in symbols}
    else:
        prefix = re.escape(namespace)+r'\.'
        blocks = re.findall(r'(?m)^'+prefix+r'[\s\S]*?(?=^'+prefix+r'|\Z)',value['exact_check_output'])
        rows = {block.split()[0]:block.rstrip('\n') for block in blocks}
        require(len(rows)==len(blocks) and set(rows)==set(symbols),'TYPE_BLOCKS:'+str(path))
        rows = {symbol:rows[symbol] for symbol in symbols}
    require(value['exact_check_output']=='\n'.join(rows.values())+'\n','TYPE_OUTPUT_FRAMING:'+str(path))
    declarations = re.findall(r'(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)',source.read_text())
    require(len(declarations)==len(set(declarations))==expected_count,'THEOREM_DECLARATION_COUNT:'+str(source))
    require(set(rows)=={namespace+'.'+name for name in declarations},'THEOREM_COVERAGE:'+str(source))
    require(all(isinstance(text,str) and re.match(re.escape(symbol)+r'(?:\s|:)',text) for symbol,text in rows.items()),
            'TYPE_SYMBOL_PREFIX:'+str(path))
    return rows


def anchored_inherited():
    """Retain the actual287 meanings and original proof definitions, without wrappers."""
    require(sha(ANCHOR/'report.json')==ANCHOR_REPORT_SHA256,'ANCHOR_REPORT_CHANGED')
    report = read(ANCHOR/'report.json')
    manifest = read(ANCHOR/'manifest.json')
    require(report['status']=='VERIFIED' and report['claims']['passed']==287,'ANCHOR_NOT_VERIFIED')
    require(hashlib.sha256(packed(manifest)).hexdigest()==report['input_root_hash']==ANCHOR_ROOT,'ANCHOR_ROOT_CHANGED')
    entries = {entry['path']:entry['sha256'] for entry in manifest['files']}
    require(sha(ANCHOR/'claims.json')==entries['generated/claims.json'],'ANCHOR_CLAIMS_CHANGED')
    claims = read(ANCHOR/'claims.json')
    expected = {claim['symbol']:claim['statement'] for claim in claims}
    require(len(claims)==len(expected)==287,'ANCHOR_CLAIM_COUNT')
    paths = {ANCHOR/'report.json',ANCHOR/'manifest.json',ANCHOR/'claims.json'}
    inherited_sources = set()
    for name,digest in entries.items():
        if not name.startswith('formal/'):
            continue
        snapshot = ANCHOR/'inputs'/name
        require(sha(snapshot)==digest,'ANCHOR_SNAPSHOT_CHANGED:'+name)
        paths.add(snapshot)
        if name=='formal/Allow.lean':
            wanted = snapshot.read_bytes()+b'\nimport Allow.ImmutableImageCandidate\n'
            require((ROOT/name).read_bytes()==wanted,'INHERITED_AGGREGATE_CHANGED')
        else:
            require(sha(ROOT/name)==digest,'INHERITED_SOURCE_CHANGED:'+name)
        if name.endswith('.lean'):
            inherited_sources.add(ROOT/name)
    image_snapshot_name = 'gates/sql/immutable-image-candidate/ImmutableImage.lean'
    image_snapshot = ANCHOR/'inputs'/image_snapshot_name
    require(sha(image_snapshot)==entries[image_snapshot_name]==sha(IMAGE_SOURCE),'INHERITED_IMAGE_MODEL_CHANGED')
    paths.add(image_snapshot)
    inherited_sources.add(IMAGE_SOURCE)
    require(set(formal_inventory())==inherited_sources,'INHERITED_FORMAL_INVENTORY_CHANGED')
    groups = {}
    inherited = {}
    for name in INHERITED:
        rows = read(ROOT/name)
        require(not set(rows)&set(inherited),'DUPLICATE_INHERITED_SYMBOL')
        inherited.update(rows)
        paths.add(ROOT/name)
    require(len(inherited)==112,'INHERITED_BASE_COUNT')
    groups['inherited'] = inherited
    for group,namespace,source,types,count in REGISTRIES:
        value = read(ROOT/types)
        require(value['source_sha256']==sha(ROOT/source),'REGISTRY_SOURCE_MISMATCH:'+source)
        rows = value['theorem_types']
        names = re.findall(r'(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)',(ROOT/source).read_text())
        require(len(rows)==len(names)==len(set(names))==count and set(names)==set(rows),'REGISTRY_COVERAGE:'+group)
        groups[group] = {namespace+'.'+name:text for name,text in rows.items()}
        paths.add(ROOT/types)
    groups['image'] = checked_inventory(IMAGE_TYPES,IMAGE_SOURCE,'Allow.ImmutableImageCandidate',7)
    paths.add(IMAGE_TYPES)
    actual = {symbol:text for rows in groups.values() for symbol,text in rows.items()}
    require(len(actual)==287 and actual==expected,'INHERITED287_EXACT_MEANINGS_CHANGED')
    return groups,paths


def check_reviews(config):
    pins_payload = REVIEW_PINS.read_bytes()
    pins = json.loads(pins_payload,object_pairs_hook=pairs_unique)
    require(hashlib.sha256(packed(pins['files'])).hexdigest()==pins['input_root_sha256'],'REVIEW_ROOT_MISMATCH')
    expected = {}
    for row in pins['files']:
        path = workspace_path(row['path'])
        key = path.relative_to(ROOT).as_posix()
        require(key not in expected,'DUPLICATE_REVIEW_INPUT:'+key)
        require(sha(path)==row['sha256'],'REVIEW_INPUT_CHANGED:'+key)
        expected[key] = row['sha256']
    required = {Path(__file__),CONFIG,CANDIDATE_SOURCE,CANDIDATE_TYPES}
    required.update(path for path in HERE.iterdir() if path.is_file() and path.suffix in {'.json','.md'} and path!=REVIEW_PINS and not path.name.endswith('manifest.json'))
    require({str(path.relative_to(ROOT)) for path in required}<=set(expected),'UNREVIEWED_CANDIDATE_INPUT')
    seats = config['reviews']
    require(len(seats)==6 and {seat['seat'] for seat in seats}==SEATS,'SIX_COUNCIL_SEATS_REQUIRED')
    paths = {ROOT/name for name in expected}|{REVIEW_PINS,CONFIG}
    reviewed_hashes = dict(expected)
    reviewed_hashes[str(REVIEW_PINS.relative_to(ROOT))] = hashlib.sha256(pins_payload).hexdigest()
    review_paths = set()
    for seat in seats:
        path = workspace_path(seat['path'])
        require(path not in review_paths,'DUPLICATE_REVIEW_PATH')
        review_paths.add(path)
        payload = path.read_bytes()
        value = json.loads(payload,object_pairs_hook=pairs_unique)
        normalized = {}
        for name,digest in value['input_hashes'].items():
            key = workspace_path(name).relative_to(ROOT).as_posix()
            require(key in expected and key not in normalized,'INVALID_REVIEW_INPUT:'+key)
            normalized[key] = digest
        require(value.get('reviewer')==seat['seat'],'REVIEWER_SEAT_MISMATCH:'+str(path))
        require(value['decision']=='APPROVE_GAMEPLAN' and normalized==expected
                and value['input_root_sha256']==pins['input_root_sha256'],'MISSING_EXACT_APPROVAL:'+str(path))
        paths.add(path)
        reviewed_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest()
    return paths,reviewed_hashes


def execute(command,work,environment,log):
    result = subprocess.run(command,cwd=work,env=environment,stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,text=True,timeout=180)
    log.write_text(result.stdout)
    require(result.returncode==0,'CLEAN_BUILD_FAILURE:'+log.name)
    require('warning:' not in result.stdout.lower(),'WARNING:'+log.name)
    return result.stdout


def check_axioms(output,symbols):
    for symbol in symbols:
        pattern = re.compile(r"^'"+re.escape(symbol)+r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*$",re.M)
        matches = list(pattern.finditer(output))
        require(len(matches)==1,'AXIOM_REPORT_MISSING_OR_DUPLICATE:'+symbol)
        actual = {name.strip() for name in (matches[0].group(1) or '').split(',') if name.strip()}
        require(actual<=ALLOWED_AXIOMS,'UNDECLARED_AXIOM:'+symbol)
    require(len([line for line in output.splitlines() if line.strip()])==len(symbols),'EXTRA_AXIOM_OUTPUT')


def check_inputs(out,entries,formal,guards,identity,config,reviewed_hashes):
    for entry in entries:
        path = out/entry['path'][10:] if entry['path'].startswith('generated/') else ROOT/entry['path']
        require(sha(path)==entry['sha256'],'INPUT_MUTATION:'+entry['path'])
        if not entry['path'].startswith('generated/'):
            require(sha(out/'inputs'/entry['path'])==entry['sha256'],'SNAPSHOT_MUTATION:'+entry['path'])
    for name,digest in reviewed_hashes.items():
        require(sha(ROOT/name)==digest and sha(out/'inputs'/name)==digest,'REVIEWED_BYTES_CHANGED:'+name)
    anchored_inherited()  # Recheck exact original meanings/sources after snapshot freezing.
    require(formal_inventory()==formal,'FORMAL_INVENTORY_CHANGED')
    require(guard_inventory(config)==guards,'PRODUCTION_SOURCE_INVENTORY_CHANGED')
    require(proxy_identity()==identity,'PROXY_CONTINUITY_CHANGED')


def clean_build(label,out,groups,tool,environment,root_hash):
    with tempfile.TemporaryDirectory(prefix='allow-validation-context-model-') as temporary:
        work = Path(temporary)/'formal'
        shutil.copytree(out/'inputs/formal',work)
        target = work/'Allow/ValidationContextCandidate.lean'
        shutil.copyfile(out/'inputs'/CANDIDATE_SOURCE.relative_to(ROOT),target)
        with (work/'Allow.lean').open('a') as stream:
            stream.write('\nimport '+CANDIDATE_MODULE+'\n')
        execute([str(tool/'lake'),'build'],work,environment,out/f'{label}-build.log')
        audits = {}
        for group,rows in groups.items():
            types = 'import Allow\n'+('\n'.join('example : ('+text+') := @'+symbol for symbol,text in rows.items())
                if group=='inherited' else '\n'.join('#check '+symbol for symbol in rows))+'\n'
            for kind,text in [('types',types),('axioms','import Allow\n'+'\n'.join('#print axioms '+symbol for symbol in rows)+'\n')]:
                (work/'Audit.lean').write_text(text)
                output = execute([str(tool/'lake'),'env','lean','Audit.lean'],work,environment,out/f'{label}-{group}-{kind}.log')
                if kind=='axioms':
                    check_axioms(output,list(rows))
                elif group!='inherited':
                    require(output=='\n'.join(rows.values())+'\n','EXACT_TYPE_MISMATCH:'+group)
                audits[group+'-'+kind] = hashlib.sha256(output.encode()).hexdigest()
        artifacts = {path.relative_to(work).as_posix():sha(path) for path in sorted(work.rglob('*.olean'))}
        require('.lake/build/lib/lean/Allow/ValidationContextCandidate.olean' in artifacts,'MISSING_CANDIDATE_ARTIFACT')
        statuses = {group+':'+symbol:'PASS' for group,rows in groups.items() for symbol in rows}
        return {'label':label,'input_root_hash':root_hash,'artifact_sha256':artifacts,'audit_sha256':audits,
                'proof_inventory':list(statuses),'claim_status':statuses,'correspondence':{'required_objects':0},
                'provenance_claim_ids':list(statuses)}


def run(run_id):
    out = HERE/'formal-runs'/run_id
    require(not out.exists(),'EXISTING_RUN')
    out.mkdir(parents=True,mode=0o700)
    report = {'schema_version':'1.0','closure_id':'allow-validation-context-'+run_id,
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'UNSET','input_root_hash':None,
        'claims':{'inherited':287,'candidate':None,'total':None,'passed':0,'blocked':0,'unresolved':None},
        'builds':[],'determinism':{'required':True,'status':'UNSET'},'blocking_reasons':[],'infrastructure_errors':[],
        'correspondence':{'required_objects':0,'mapped_objects':0,'unmapped_objects':0,'ambiguous_objects':0},
        'dependencies':{'verified':[],'trusted':TRUST,'undeclared':[]},
        'closure_boundary':{'verified_surface':['Frozen exact inherited287 propositions and candidate propositions'],
            'trusted_surface':TRUST,'excluded_surface':EXCLUDED,
            'interpretation':'VERIFIED applies only to this finite model-compilation surface under declared TCB. It does not establish implementation refinement or latency acceptance.'}}
    try:
        config = read(CONFIG)
        count = config['candidate_claim_count']
        require(type(count) is int and 0<count<=1000,'INVALID_CANDIDATE_COUNT')
        report['claims'].update(candidate=count,total=287+count,unresolved=287+count)
        paths,reviewed_hashes = check_reviews(config)
        groups,inherited_paths = anchored_inherited()
        paths |= inherited_paths
        groups['context'] = checked_inventory(CANDIDATE_TYPES,CANDIDATE_SOURCE,CANDIDATE_MODULE,count)
        symbols = [symbol for rows in groups.values() for symbol in rows]
        require(len(symbols)==len(set(symbols))==287+count,'CLAIM_SYMBOL_COVERAGE')
        formal = formal_inventory()
        require(not (ROOT/'formal/Allow/ValidationContextCandidate.lean').exists(),'CANDIDATE_ALREADY_INSTALLED')
        for path in formal+[CANDIDATE_SOURCE]:
            require(not ESCAPE.search(path.read_text()),'FORBIDDEN_PROOF_ESCAPE:'+str(path))
        require(read(ROOT/'formal/lake-manifest.json')['packages']==[],'UNDECLARED_LEAN_PACKAGE')
        guards = guard_inventory(config)
        identity = proxy_identity()
        save(out/'preimplementation-guards.json',{'files':[str(path.relative_to(ROOT)) for path in guards],
                                                'proxy_identity':identity})
        paths |= set(formal)|set(guards)|{ROOT/'.runtime/corpus/sql-proxy/ready.json',Path(__file__)}
        paths |= {ROOT/'formal'/name for name in ('lean-toolchain','lakefile.toml','lake-manifest.json')}
        claims = [{'id':group+':'+symbol,'symbol':symbol,'statement':text,
            'claim_class':'proof_compilation_with_expected_proposition' if group=='inherited' else 'proof_compilation_with_exact_printed_type',
            'verifier':'V-VALIDATION-CONTEXT-LEAN','pass_condition':'Exact registered proposition/type and allowed axiom closure pass in both reproducible clean builds, with frozen inputs/inventories unchanged',
            'block_conditions':['type mismatch','undeclared axiom','missing witness proposition','build failure','input mutation','nondeterminism'],
            'witness':bool('witness' in symbol or '.fixture_' in symbol),'trusted_dependencies':TRUST,'severity':'blocking'}
            for group,rows in groups.items() for symbol,text in rows.items()]
        save(out/'claims.json',claims)
        save(out/'tcb.json',{'trusted':TRUST,'excluded':EXCLUDED,'allowed_axioms':sorted(ALLOWED_AXIOMS)})
        save(out/'config.json',{'closure_id':report['closure_id'],'required_clean_builds':2,
            'warning_is_blocking':True,'unresolved_is_blocking':True,'manual_override_allowed':False,
            'network_allowed_during_verification':False,'llm_as_verifier':False,
            'transformation':'Copy only candidate Lean file into fresh formal tree and append its import; retain all inherited definitions',
            'determinism_required':['artifact_sha256','audit_sha256','proof_inventory','claim_status','correspondence','provenance_claim_ids'],
            'nondeterministic_fields':['timestamps','temporary paths','build durations']})
        tool = Path.home()/'.elan/toolchains/leanprover--lean4---v4.34.1/bin'
        save(out/'verifier-registry.json',{'id':'V-VALIDATION-CONTEXT-LEAN','implementation_sha256':sha(__file__),
            'executable':str(Path(__file__).relative_to(ROOT)),'toolchain':'Lean4.34.1',
            'tool_executable_sha256':{name:sha(tool/name) for name in ('lean','lake')},
            'exit_codes':{'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}})
        provenance = [{'public_claim':claim['id'],'claim_id':claim['id'],'evidence':'evidence.json',
            'verifier':'V-VALIDATION-CONTEXT-LEAN','inputs':'manifest.json','trusted_dependencies':TRUST} for claim in claims]
        save(out/'provenance-targets.json',provenance)
        generated = ['claims.json','tcb.json','config.json','verifier-registry.json','provenance-targets.json','preimplementation-guards.json']
        entries = [{'path':str(path.relative_to(ROOT)),'sha256':sha(path)} for path in sorted(paths)]
        entries += [{'path':'generated/'+name,'sha256':sha(out/name)} for name in generated]
        manifest = {'schema_version':'1.0','files':sorted(entries,key=lambda entry:entry['path'])}
        root_hash = hashlib.sha256(packed(manifest)).hexdigest()
        report['input_root_hash'] = root_hash
        save(out/'manifest.json',manifest)
        for path in paths:
            target = out/'inputs'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
            shutil.copyfile(path,target)
        check_inputs(out,entries,formal,guards,identity,config,reviewed_hashes)
        environment = dict(os.environ,PATH=str(tool)+':/usr/bin:/bin')
        for name in ('LEAN_PATH','LEAN_SRC_PATH','LEAN_SYSROOT','LAKE_HOME','LAKE_OVERRIDE_LEAN'):
            environment.pop(name,None)
        report['environment'] = {'platform':platform.platform(),'python':platform.python_version(),'lean':'4.34.1'}
        for label in ('A','B'):
            check_inputs(out,entries,formal,guards,identity,config,reviewed_hashes)
            report['builds'].append(clean_build(label,out,groups,tool,environment,root_hash))
        a,b = report['builds']
        for key in ('artifact_sha256','audit_sha256','proof_inventory','claim_status','correspondence','provenance_claim_ids'):
            require(a[key]==b[key],'NONDETERMINISM:'+key)
        check_inputs(out,entries,formal,guards,identity,config,reviewed_hashes)
        evidence = [{'closure_id':report['closure_id'],'claim_id':claim['id'],'input_root_hash':root_hash,
            'verifier_id':'V-VALIDATION-CONTEXT-LEAN','verifier_sha256':sha(__file__),'execution_environment':report['environment'],
            'status':'PASS','exit_code':0,'raw_result':'Exact proposition/types and allowed axioms in two reproducible clean builds',
            'logs':[f'{label}-{claim["id"].split(":")[0]}-{kind}.log' for label in ('A','B') for kind in ('types','axioms')]}
            for claim in claims]
        save(out/'evidence.json',evidence)
        save(out/'provenance.json',provenance)
        report['claims'].update(passed=287+count,unresolved=0)
        witnesses = sum(claim['witness'] for claim in claims)
        report['witnesses'] = {'required':witnesses,'valid':witnesses,'invalid':0,
            'scope':'Registered explicit witness propositions compile; no runtime witnesses claimed'}
        report['provenance'] = {'public_claims':len(claims),'fully_bound':len(claims),'orphan_claims':0}
        report['determinism']['status'] = 'PASS'
        report['status'] = 'VERIFIED'
    except AssertionError as error:
        report['status']='BLOCKED'
        report['blocking_reasons'].append(str(error))
    except Exception as error:
        report['status']='INFRASTRUCTURE_FAILURE'
        report['infrastructure_errors'].append(type(error).__name__+': '+str(error))
    save(out/'report.json',report)
    print(json.dumps({key:report[key] for key in ('status','input_root_hash','claims','blocking_reasons','infrastructure_errors')},indent=2))
    return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('--execute',action='store_true',help='Explicit root authorization after frozen six-seat approval')
    args = parser.parse_args()
    parser.error('Final execution requires --execute and prior root authorization') if not args.execute else None
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.run_id) is not None,'INVALID_RUN_ID')
    return run(args.run_id)


if __name__=='__main__':
    raise SystemExit(main())
