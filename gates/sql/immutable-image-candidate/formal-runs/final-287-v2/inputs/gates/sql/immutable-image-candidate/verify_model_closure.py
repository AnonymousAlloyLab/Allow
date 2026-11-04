#!/usr/bin/env python3
"""Finite287-proposition model closure. No production implementation correspondence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TRUST = ['Lean4.34.1 kernel/elaborator/pretty-printer and bundled libraries',
         'propext, Quot.sound, Classical.choice when reported by the axiom audit',
         'Lake, Python3, this hashed verifier and SHA256 collision resistance',
         'OS filesystem/process isolation and hardware', 'Interpretation of abstract model definitions']
EXCLUDED = ['Linux syscall and immutable-image implementation correspondence',
            'Python SQL/protocol implementation, parser correspondence, PostgreSQL execution',
            'Revision6 live-path integrity preservation', 'Performance/memory and production promotion']
REGISTRIES = [
 ('document','Allow.DocumentDraft','formal/Allow/Document.lean','gates/document/draft/types.json',125),
 ('order','Allow.DocumentOrder','formal/Allow/FieldOrder.lean','gates/document/order-amendment/types.json',14),
 ('associativity','Allow.DocumentAssociativity','formal/Allow/Associativity.lean','gates/document/associativity-amendment/types.json',16),
 ('partial','Allow.DocumentPartialTypes','formal/Allow/PartialTypes.lean','gates/document/partial-types-candidate/types.json',13)]
INHERITED = ['closure/theorem-types.json','spec/implementation-g1-types.json','spec/egraph-types.json','spec/retrieval-types.json','spec/sql-types.json']
ALLOWED = {'propext','Quot.sound','Classical.choice'}
ESCAPE = re.compile(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def packed(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def require(condition,reason):
    if not condition:
        raise AssertionError(reason)

def runtime_identity():
    path=ROOT/'.runtime/corpus/sql-proxy/ready.json'
    ready=json.loads(path.read_text()); pid=ready['pid']; proc=Path('/proc')/str(pid)
    # Counters/status are intentionally excluded: the baseline remains live.
    return {'ready_sha256':sha(path),'pid':pid,'process_start_ticks':proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
            'exe_sha256':sha(proc/'exe'),'cmdline_sha256':sha(proc/'cmdline')}

def exact_groups():
    groups={}; inherited={}
    for name in INHERITED:
        rows=json.loads((ROOT/name).read_text())
        require(not set(rows)&set(inherited),'DUPLICATE_INHERITED');inherited.update(rows)
    require(len(inherited)==112,'INHERITED_COUNT');groups['inherited']=inherited
    for label,namespace,source,registry,count in REGISTRIES:
        data=json.loads((ROOT/registry).read_text());rows=data['theorem_types']
        require(sha(ROOT/source)==data['source_sha256'],'REGISTRY_SOURCE_CHANGED:'+source)
        names=re.findall(r'(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)',(ROOT/source).read_text())
        require(len(rows)==count and len(names)==len(set(names)) and set(names)==set(rows),'REGISTRY_COVERAGE:'+label)
        groups[label]={namespace+'.'+k:v for k,v in rows.items()}
    inventory=json.loads((HERE/'existing-type-inventory.json').read_text())
    require(groups==inventory['groups'],'EXISTING_INVENTORY_MISMATCH')
    candidate=json.loads((HERE/'candidate-type-inventory.json').read_text())
    require(sha(HERE/'ImmutableImage.lean')==candidate['source_sha256'],'CANDIDATE_SOURCE_CHANGED')
    blocks=re.findall(r'(?m)^Allow\.ImmutableImageCandidate\.[\s\S]*?(?=^Allow\.ImmutableImageCandidate\.|\Z)',candidate['exact_check_output'])
    rows={block.split()[0]:block.rstrip('\n') for block in blocks}
    names=re.findall(r'(?m)^theorem\s+(\w+)',(HERE/'ImmutableImage.lean').read_text())
    require(len(rows)==7 and set(rows)==set(candidate['symbols'])=={'Allow.ImmutableImageCandidate.'+n for n in names},'CANDIDATE_COVERAGE')
    groups['image']=rows
    require(sum(map(len,groups.values()))==287,'CLAIM_COUNT')
    return groups

def execute(command,work,environment,log):
    result=subprocess.run(command,cwd=work,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
    log.write_text(result.stdout)
    require(result.returncode==0,'CLEAN_BUILD_FAILURE:'+log.name)
    require('warning:'not in result.stdout.lower(),'WARNING:'+log.name)
    return result.stdout

def axioms(output,symbols):
    for symbol in symbols:
        pattern=re.compile(r"^'"+re.escape(symbol)+r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*$",re.M)
        hits=list(pattern.finditer(output));require(len(hits)==1,'AXIOM_REPORT:'+symbol)
        used={x.strip()for x in(hits[0].group(1)or'').split(',')if x.strip()}
        require(used<=ALLOWED,'UNDECLARED_AXIOM:'+symbol)
    require(len([x for x in output.splitlines()if x.strip()])==len(symbols),'EXTRA_AXIOM_OUTPUT')

def check_inputs(out,entries,identity):
    for row in entries:
        original=(out/row['path'][10:])if row['path'].startswith('generated/')else ROOT/row['path']
        require(sha(original)==row['sha256'],'INPUT_MUTATION:'+row['path'])
        if not row['path'].startswith('generated/'):
            require(sha(out/'inputs'/row['path'])==row['sha256'],'SNAPSHOT_MUTATION:'+row['path'])
    require(runtime_identity()==identity,'ACTIVE_PROXY_IDENTITY_CHANGED')

def clean_build(label,out,groups,tool,environment,root_hash):
    with tempfile.TemporaryDirectory(prefix='allow-image-model-')as temporary:
        work=Path(temporary)/'formal';shutil.copytree(out/'inputs/formal',work)
        shutil.copyfile(out/'inputs'/HERE.relative_to(ROOT)/'ImmutableImage.lean',work/'Allow/ImmutableImageCandidate.lean')
        with(work/'Allow.lean').open('a')as stream:stream.write('\nimport Allow.ImmutableImageCandidate\n')
        execute([str(tool/'lake'),'build'],work,environment,out/f'{label}-build.log')
        audits={}
        for group,rows in groups.items():
            source='import Allow\n'+('\n'.join('example : ('+typ+') := @'+name for name,typ in rows.items())if group=='inherited'else'\n'.join('#check '+name for name in rows))+'\n'
            for kind,text in [('types',source),('axioms','import Allow\n'+'\n'.join('#print axioms '+name for name in rows)+'\n')]:
                (work/'Audit.lean').write_text(text)
                output=execute([str(tool/'lake'),'env','lean','Audit.lean'],work,environment,out/f'{label}-{group}-{kind}.log')
                if kind=='axioms':axioms(output,list(rows))
                elif group!='inherited':require(output=='\n'.join(rows.values())+'\n','EXACT_TYPE_MISMATCH:'+group)
                audits[group+'-'+kind]=hashlib.sha256(output.encode()).hexdigest()
        artifacts={p.relative_to(work).as_posix():sha(p)for p in sorted(work.rglob('*.olean'))}
        require('.lake/build/lib/lean/Allow/ImmutableImageCandidate.olean'in artifacts,'MISSING_CANDIDATE_ARTIFACT')
        statuses={group+':'+name:'PASS'for group,rows in groups.items()for name in rows}
        return {'label':label,'input_root_hash':root_hash,'artifact_sha256':artifacts,'audit_sha256':audits,
                'claim_status':statuses,'proof_inventory':list(statuses),'correspondence':{'required':0},'provenance_claim_ids':list(statuses)}

def main():
    require(len(sys.argv)==2 and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sys.argv[1]),'INVALID_RUN_ID')
    out=HERE/'formal-runs'/sys.argv[1];require(not out.exists(),'EXISTING_RUN');out.mkdir(parents=True)
    report={'schema_version':'1.0','closure_id':'allow-sql-image-'+sys.argv[1],'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'status':'UNSET','input_root_hash':None,'claims':{'total':287,'passed':0,'blocked':0,'unresolved':287},'builds':[],
            'determinism':{'required':True,'status':'UNSET'},'blocking_reasons':[],'infrastructure_errors':[],
            'dependencies':{'trusted':TRUST,'verified':[],'undeclared':[]},'correspondence':{'required_objects':0,'mapped_objects':0,'unmapped_objects':0,'ambiguous_objects':0},
            'closure_boundary':{'verified_surface':['287 exact model propositions under frozen source tree'],'trusted_surface':TRUST,'excluded_surface':EXCLUDED,
             'interpretation':'VERIFIED applies only to the frozen finite model surface under declared TCB, not runtime or production correctness.'}}
    try:
        pins=json.loads((HERE/'review-input-pins.json').read_text());expected={r['path']:r['sha256']for r in pins['files']}
        require(len(expected)==9,'REVIEW_PIN_COUNT')
        for path,digest in expected.items():require(sha(ROOT/path)==digest,'REVIEW_INPUT_CHANGED:'+path)
        reviews=[]
        for family in('terra','sol','astra'):
            for seat in(1,2):
                path=ROOT/f'reviews/sql-image-{family}-{seat}-r2.json';review=json.loads(path.read_text())
                normalized={}
                for name,digest in review['input_hashes'].items():
                    rp=Path(name);require('..'not in rp.parts,'INVALID_REVIEW_PATH')
                    key=rp.relative_to(ROOT).as_posix()if rp.is_absolute()else rp.as_posix()
                    require(key in expected and key not in normalized,'INVALID_REVIEW_INPUT:'+key);normalized[key]=digest
                require(review['decision']=='APPROVE_GAMEPLAN'and normalized==expected and review['input_root_sha256']==pins['input_root_sha256'],'MISSING_EXACT_APPROVAL:'+str(path))
                reviews.append(path)
        groups=exact_groups();identity=runtime_identity()
        formal=sorted(p for p in(ROOT/'formal').rglob('*.lean')if'.lake'not in p.parts)
        for path in formal+[HERE/'ImmutableImage.lean']:require(not ESCAPE.search(path.read_text()),'FORBIDDEN_CONSTRUCT:'+str(path))
        require(json.loads((ROOT/'formal/lake-manifest.json').read_text())['packages']==[],'UNDECLARED_LEAN_PACKAGE')
        guards=['retrieval/allow_retrieval/sql_guard.py','retrieval/allow_retrieval/sql_proxy.py','config/sqlean-parser-lock.json','.runtime/corpus/sql-proxy/ready.json']
        guard_values={name:sha(ROOT/name)for name in guards};save(out/'preimplementation-guards.json',{'source_sha256':guard_values,'runtime_identity':identity})
        paths=set(formal)|{ROOT/path for path in expected}|set(reviews)|{ROOT/p for p in guards+INHERITED}
        paths|={ROOT/r[3]for r in REGISTRIES}|{Path(__file__),HERE/'review-input-pins.json'}|{ROOT/'formal'/p for p in['lean-toolchain','lakefile.toml','lake-manifest.json']}
        claims=[{'id':group+':'+name,'statement':statement,'claim_class':'proof_compilation_with_exact_proposition','symbol':name,'verifier':'V-SQL-IMAGE-LEAN',
                 'pass_condition':'Both clean builds pass exact type and allowed axiom checks; artifacts and metadata identical; all frozen inputs unchanged',
                 'block_conditions':['type mismatch','unapproved axiom','build failure','input mutation','nondeterminism'],
                 'trusted_dependencies':TRUST,'witness':bool('witness'in name or'.fixture_'in name),'severity':'blocking'}for group,rows in groups.items()for name,statement in rows.items()]
        save(out/'claims.json',claims);save(out/'tcb.json',{'trusted':TRUST,'excluded':EXCLUDED})
        save(out/'config.json',{'schema_version':'1.0','closure_id':report['closure_id'],'required_clean_builds':2,'manual_override_allowed':False,
         'unresolved_is_blocking':True,'warning_is_blocking':True,'network_allowed_during_verification':False,'llm_as_verifier':False,
         'transformation':'Copy candidate to Allow/ImmutableImageCandidate.lean and append import in fresh copied formal tree only',
         'determinism_required':['proof_inventory','correspondence','provenance_claim_ids','claim_status','artifact_sha256','audit_sha256'],
         'nondeterministic_fields':['timestamps','temporary paths','build duration']})
        tool=Path.home()/'.elan/toolchains/leanprover--lean4---v4.34.1/bin'
        save(out/'verifier-registry.json',{'id':'V-SQL-IMAGE-LEAN','executable':str(Path(__file__).relative_to(ROOT)),'implementation_sha256':sha(__file__),
          'exit_codes':{'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2},'toolchain':'Lean4.34.1','tool_executable_sha256':{name:sha(tool/name)for name in['lean','lake']}})
        provenance=[{'public_claim':c['id'],'claim_id':c['id'],'evidence':'evidence.json','verifier':'V-SQL-IMAGE-LEAN','inputs':'manifest.json','trusted_dependencies':TRUST}for c in claims]
        save(out/'provenance-targets.json',provenance)
        generated=['claims.json','tcb.json','config.json','verifier-registry.json','provenance-targets.json','preimplementation-guards.json']
        entries=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in sorted(paths)]+[{'path':'generated/'+n,'sha256':sha(out/n)}for n in generated]
        manifest={'schema_version':'1.0','files':sorted(entries,key=lambda row:row['path'])};root_hash=hashlib.sha256(packed(manifest)).hexdigest()
        report['input_root_hash']=root_hash;save(out/'manifest.json',manifest)
        for path in paths:
            target=out/'inputs'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        check_inputs(out,entries,identity)
        environment=dict(os.environ,PATH=str(tool)+os.pathsep+os.environ.get('PATH',''));environment.pop('LEAN_PATH',None)
        report['environment']={'platform':platform.platform(),'python':sys.version,'lean':'4.34.1'}
        for label in('A','B'):
            check_inputs(out,entries,identity);report['builds'].append(clean_build(label,out,groups,tool,environment,root_hash))
        a,b=report['builds']
        for key in['artifact_sha256','audit_sha256','claim_status','proof_inventory','correspondence','provenance_claim_ids']:require(a[key]==b[key],'NONDETERMINISM:'+key)
        check_inputs(out,entries,identity)
        require(formal==sorted(p for p in(ROOT/'formal').rglob('*.lean')if'.lake'not in p.parts),'FORMAL_INVENTORY_CHANGED')
        evidence=[{'closure_id':report['closure_id'],'claim_id':c['id'],'input_root_hash':root_hash,'verifier_id':'V-SQL-IMAGE-LEAN','verifier_sha256':sha(__file__),
           'execution_environment':report['environment'],'status':'PASS','exit_code':0,'raw_result':'Exact type and allowed axioms in both reproducible clean builds',
           'logs':[f'{label}-{c["id"].split(":")[0]}-{kind}.log'for label in('A','B')for kind in('types','axioms')]}for c in claims]
        save(out/'evidence.json',evidence);save(out/'provenance.json',provenance)
        report['claims'].update(passed=287,unresolved=0);report['determinism']['status']='PASS'
        report['witnesses']={'required':sum(c['witness']for c in claims),'valid':sum(c['witness']for c in claims),'invalid':0,'scope':'Registered concrete witness propositions compile; no runtime witnesses claimed'}
        report['provenance']={'public_claims':287,'fully_bound':287,'orphan_claims':0};report['status']='VERIFIED'
    except AssertionError as error:report['status']='BLOCKED';report['blocking_reasons'].append(str(error))
    except Exception as error:report['status']='INFRASTRUCTURE_FAILURE';report['infrastructure_errors'].append(type(error).__name__+': '+str(error))
    save(out/'report.json',report)
    print(json.dumps({k:report[k]for k in['status','input_root_hash','claims','blocking_reasons','infrastructure_errors']},indent=2))
    return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]

if __name__=='__main__':raise SystemExit(main())
