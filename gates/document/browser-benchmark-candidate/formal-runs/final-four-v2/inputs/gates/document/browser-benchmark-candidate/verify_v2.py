#!/usr/bin/env python3
"""Close four frozen abstract model claims under explicit trust, independently of runtime."""
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
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REL = 'gates/document/browser-benchmark-candidate/'
ID = 'allow-browser-benchmark-four-v2'
REVIEWS = [f'reviews/browser-benchmark-{family}-{seat}.json' for family in ('terra', 'sol', 'astra') for seat in (1, 2)]
PINS = {REL+'protocol.json':'33975062c08d6b8fb7bf3cbe0f39cfaaeae3101d0e80154f2aaf0b33fce9dfb5', REL+'BrowserBenchmarkProtocol.lean':'57d8512a8bd483ff9bfa76d43e66c0963a90c8b3b9eb7751b9ff89d2df48a49c'}
TOOL = Path.home()/'.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean'
TRUST = ['Lean 4.34.1 kernel, elaborator, pretty-printer and bundled libraries', 'propext, Quot.sound, Classical.choice only when audited', 'Python verifier and SHA256 collision resistance', 'operating system, filesystem and hardware']
EXCLUDED = ['browser or production runtime correspondence', 'actual commits, physical paint or user-facing correctness', 'percentile computation and input validity', 'the prior 267 claims and any future revision']


class Blocked(Exception):
    """A finite closure obligation failed or remained unresolved."""


def check(condition, message):
    if not condition:
        raise Blocked(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def execute(command, cwd, env, log):
    result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    log.write_text(result.stdout)
    check(result.returncode == 0 and 'warning:' not in result.stdout.lower(), 'CLEAN_BUILD_OR_AUDIT_FAILURE:'+log.name)
    return result.stdout


def main():
    out = HERE/'formal-runs'/'final-four-v2'
    if out.exists():
        raise RuntimeError('Run directory already exists; preserve existing evidence')
    out.mkdir(parents=True)
    report = {'schema_version':'1.0','closure_id':ID,'timestamp':datetime.now(timezone.utc).isoformat(),'status':'UNSET','input_root_hash':None,
              'claims':{'total':4,'passed':0,'blocked':0,'unresolved':4},'builds':{'required':2,'passed':0,'records':[]},
              'correspondence':{'required_objects':0,'mapped_objects':0,'unmapped_objects':0,'ambiguous_objects':0},
              'witnesses':{'required':0,'valid':0,'invalid':0},'determinism':{'required':True,'status':'UNSET'},
              'provenance':{'public_claims':4,'fully_bound':0,'orphan_claims':4},
              'dependencies':{'verified':[],'trusted':TRUST,'undeclared':[]},'blocking_reasons':[],'infrastructure_errors':[],
              'closure_boundary':{'verified_surface':['Four registered abstract Lean propositions only'], 'trusted_surface':TRUST,'excluded_surface':EXCLUDED,
                                  'interpretation':'VERIFIED applies only to this frozen finite model under the declared TCB.'},
              'decision':{'valid_states':['VERIFIED','BLOCKED','INFRASTRUCTURE_FAILURE'],'manual_override_allowed':False}}
    try:
        for path, pin in PINS.items():
            check(digest(ROOT/path)==pin,'INPUT_MUTATION:'+path)
        for path in REVIEWS:
            review=json.loads((ROOT/path).read_text())
            hashes=review.get('input_hashes',review.get('input_sha256',review.get('inputs_sha256')))
            check(review['decision']=='APPROVE_GAMEPLAN' and hashes==PINS,'MISSING_EXACT_APPROVAL:'+path)
        source=(ROOT/(REL+'BrowserBenchmarkProtocol.lean')).read_text()
        check(not re.search(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)',source),'FORBIDDEN_CONSTRUCT')
        types=json.loads((ROOT/(REL+'types.json')).read_text())
        check(len(types)==4 and set(types)==set(re.findall(r'(?m)^theorem\s+(\w+)',source)),'CLAIM_INVENTORY')
        check((ROOT/'formal/lean-toolchain').read_text().strip()=='leanprover/lean4:v4.34.1','TOOLCHAIN_MISMATCH')
        check(json.loads((ROOT/'formal/lake-manifest.json').read_text())['packages']==[],'UNDECLARED_DEPENDENCY')
        verifier_hash=digest(Path(__file__))
        claims=[{'id':name,'statement':statement,'class':'proof_compilation','verifier':'V-LEAN-EXACT',
                 'pass_condition':'Exact complete #check output and allowed axiom audit pass in both matching clean builds',
                 'block_conditions':['type mismatch','forbidden axiom','build failure','input mutation','nondeterminism'],
                 'dependencies':{'verified':[],'trusted':TRUST},'evidence':'evidence/'+name+'.json','public_claims':[name]} for name,statement in types.items()]
        config={'schema_version':'1.0','closure_id':ID,'unresolved_is_blocking':True,'warning_is_blocking':True,'manual_override_allowed':False,
                'required_clean_builds':2,'determinism_required':True,'network_allowed':False,'llm_final_verifier':False,
                'nondeterministic_fields':['timestamp','temporary paths'],'standalone_build':'Candidate imports no project modules; exact toolchain files are pinned but project formal tree is not built.'}
        provenance=[{'public_claim':name,'claim_id':name,'evidence':'evidence/'+name+'.json','verifier':'V-LEAN-EXACT',
                     'inputs':[REL+'BrowserBenchmarkProtocol.lean',REL+'types.json'],'trusted_dependencies':TRUST} for name in types]
        registry={'id':'V-LEAN-EXACT','implementation':REL+'verify_v2.py','implementation_sha256':verifier_hash,'claim_classes':['proof_compilation'],
                  'exit_codes':{'pass':0,'block':1,'infrastructure_failure':2,'other':'infrastructure_failure'}}
        for name,value in [('claims.json',claims),('config.json',config),('tcb.json',{'trusted':TRUST,'verified':[]}),('provenance.json',provenance),('verifier-registry.json',registry)]:
            save(out/name,value)
        originals=list(PINS)+REVIEWS+[REL+'types.json',REL+'verify_v2.py','formal/lean-toolchain','formal/lakefile.toml','formal/lake-manifest.json']
        generated=['claims.json','config.json','tcb.json','provenance.json','verifier-registry.json']
        entries=[{'path':p,'sha256':digest(ROOT/p)} for p in originals]+[{'path':'generated/'+p,'sha256':digest(out/p)} for p in generated]
        manifest={'schema_version':'1.0','files':sorted(entries,key=lambda row:row['path'])}
        root_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        save(out/'manifest.json',manifest);report['input_root_hash']=root_hash
        for path in originals:
            target=out/'inputs'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target)
        for path in generated:
            target=out/'inputs/generated'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/path,target)
        def rehash():
            for row in entries:
                path=row['path'];pin=row['sha256']
                original=out/path[10:] if path.startswith('generated/') else ROOT/path
                snapshot=out/'inputs'/path
                check(digest(original)==pin and digest(snapshot)==pin,'INPUT_MUTATION:'+path)
        rehash()
        env=dict(os.environ);env.pop('LEAN_PATH',None)
        environment={'os':platform.platform(),'python':sys.version,'lean':'4.34.1'}
        inventories=[]
        for label in ('A','B'):
            rehash()
            with tempfile.TemporaryDirectory(prefix='allow-browser-closure-') as temp:
                work=Path(temp);shutil.copyfile(out/'inputs'/(REL+'BrowserBenchmarkProtocol.lean'),work/'BrowserBenchmarkProtocol.lean')
                execute([str(TOOL),'-o','BrowserBenchmarkProtocol.olean','BrowserBenchmarkProtocol.lean'],work,env,out/(label+'-build.log'))
                env2=dict(env,LEAN_PATH=str(work)); audits={}
                for name,expected in types.items():
                    for kind,command in [('type','#check '),('axioms','#print axioms ')]:
                        (work/'Audit.lean').write_text('import BrowserBenchmarkProtocol\n'+command+name+'\n')
                        text=execute([str(TOOL),'Audit.lean'],work,env2,out/(label+'-'+name+'-'+kind+'.log'))
                        if kind=='type':
                            check(text==expected+'\n','EXACT_TYPE_MISMATCH:'+name)
                        else:
                            match=re.fullmatch(r"'"+re.escape(name)+r"' (?:does not depend on any axioms|depends on axioms: \[([^]]*)\])\n",text)
                            check(match is not None,'AXIOM_AUDIT_FORMAT:'+name)
                            used=set(match.group(1).split(', ')) if match.group(1) else set()
                            check(used <= {'propext','Quot.sound','Classical.choice'},'FORBIDDEN_AXIOM:'+name)
                        audits[name+'-'+kind]=hashlib.sha256(text.encode()).hexdigest()
                record={'input_root_hash':root_hash,'inventory':sorted(types),'artifact_sha256':digest(work/'BrowserBenchmarkProtocol.olean'),'audits':audits,
                        'claim_status':{name:'PASS' for name in types},'provenance_sha256':digest(out/'provenance.json')}
                inventories.append(record);report['builds']['records'].append(record);report['builds']['passed']+=1
        rehash();check(inventories[0]==inventories[1],'NONDETERMINISM')
        evidence_dir=out/'evidence';evidence_dir.mkdir()
        for name in types:
            save(evidence_dir/(name+'.json'),{'schema_version':'1.0','closure_id':ID,'claim_id':name,'input_root_hash':root_hash,
                 'verifier_id':'V-LEAN-EXACT','verifier_hash':verifier_hash,'execution_environment':environment,'exit_code':0,'status':'PASS',
                 'raw_result':'Exact type, allowed axioms and matching clean artifact/audits','logs':[f'{label}-{name}-{kind}.log' for label in ('A','B') for kind in ('type','axioms')]})
        rehash()
        check(all((out/item['evidence']).is_file() for item in provenance),'ORPHAN_CLAIM')
        report.update(status='VERIFIED',claims={'total':4,'passed':4,'blocked':0,'unresolved':0},determinism={'required':True,'status':'PASS'},provenance={'public_claims':4,'fully_bound':4,'orphan_claims':0})
    except Blocked as error:
        report['status']='BLOCKED';report['blocking_reasons'].append(str(error))
    except (OSError, RuntimeError, KeyError, ValueError, subprocess.SubprocessError) as error:
        report['status']='INFRASTRUCTURE_FAILURE';report['infrastructure_errors'].append(type(error).__name__+': '+str(error))
    save(out/'report.json',report)
    print(json.dumps({key:report[key] for key in ('status','closure_id','input_root_hash','claims','blocking_reasons','infrastructure_errors')},indent=2))
    return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]


if __name__=='__main__':
    sys.exit(main())
