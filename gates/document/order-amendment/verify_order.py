#!/usr/bin/env python3
"""Bounded two-clean-build verification of 251 registered model propositions.

No runtime, Java, browser, Alloy or database correspondence is proved.
"""
import hashlib, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'gates/document/draft/verify_document_candidate.py'
sp = importlib.util.spec_from_file_location('document_formal_helpers', BASE)
helpers = importlib.util.module_from_spec(sp)
sp.loader.exec_module(helpers)
SPEC = 'spec/document-field-order.json'
ORDER = 'gates/document/order-amendment/FieldOrder.lean'
ORDER_TYPES = 'gates/document/order-amendment/types.json'
DOC = 'formal/Allow/Document.lean'
DOC_DRAFT = 'gates/document/draft/Document.lean'
DOC_TYPES = 'gates/document/draft/types.json'
CHECKER = 'backend/src/main/java/dev/allow/document/ModuleChecker.java'
PINS = {SPEC:'9943997f71d63e9f4666b80299b3d25bcb3d5237e5aea673bbc7b3bbb6115870',
 ORDER:'6bebf364f90286cbea205d488073cef5bb1bfda099b138e7c41b699be5b9e3a0',
 ORDER_TYPES:'8bd4640dc2b7cf0a178a08b5de02e9f20cdaf7a0d128471202711833f9e14563',
 DOC:'a9ce61793dc79676395211cd8e5d94c0e0767316755040224f63f2a1af3b3b07',
 DOC_DRAFT:'a9ce61793dc79676395211cd8e5d94c0e0767316755040224f63f2a1af3b3b07',
 DOC_TYPES:'fd0a31b549a8c20d079b960f68b306603b66aaed3facfd2e4a4bc302ea336109',
 CHECKER:'71a6d42375a4a2e6067d45ea81288e7d088ed796ccb8f8b6a05a0840bf1cab77'}
REVIEWS=[f'reviews/document-order-{family}-{seat}.json' for family in ('terra','sol','astra') for seat in (1,2)]
TRUST=['Lean 4.34.1 kernel, elaborator, pretty printer and bundled libraries',
 'propext, Quot.sound, Classical.choice when reported','Lake','Python verifier and imported helper',
 'SHA-256 collision resistance','OS, filesystem, processes, hardware',
 'interpretation of the formal model and published statement boundaries']
EXCLUDED=['Java/TypeScript/SQL refinement, runtime correctness and ordering guard implementation',
 'Alloy parser/printer correspondence, browser accessibility, original G2/G3 and commercial release',
 'production inputs other than the exact pre-guard ModuleChecker are outside this proof run']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(x,msg):
 if not x:raise AssertionError(msg)
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def packed(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def cmd(c,cwd,env,log):
 r=subprocess.run(c,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 log.write_text(r.stdout,encoding='utf-8');require(r.returncode==0,'CLEAN_BUILD_FAILURE: '+log.name);require('warning:' not in r.stdout.lower(),'VERIFIER_FAILURE warning: '+log.name);return r.stdout

def main():
 require(len(sys.argv)==2 and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sys.argv[1]),'Invalid run id')
 run=sys.argv[1];out=ROOT/'gates/document/order-amendment/formal-runs'/run;require(not out.exists(),'Run exists');out.mkdir(parents=True)
 report={'schema_version':'1.0','closure_id':'document-order-'+run,'status':'UNSET','timestamp':datetime.now(timezone.utc).isoformat(),
 'input_root_hash':'','claims':{'total':251,'passed':0,'blocked':0,'unresolved':251},
 'correspondence':{'required_objects':0,'mapped_objects':0,'unmapped_objects':0,'ambiguous_objects':0,'note':'No implementation correspondence claimed'},
 'witnesses':{'required':0,'valid':0,'invalid':0},'builds':{'required':2,'passed':0,'records':[]},
 'determinism':{'required':True,'status':'UNSET'},'provenance':{'public_claims':251,'fully_bound':0,'orphan_claims':0},
 'dependencies':{'verified':[],'trusted':TRUST,'undeclared':[]},'blocking_reasons':[],'infrastructure_errors':[],
 'closure_boundary':{'verified_surface':['Exact 112 inherited, 125 document and 14 field-order Lean theorem types under pinned input'],
 'trusted_surface':TRUST,'excluded_surface':EXCLUDED,'interpretation':'Finite model claims only under declared trust.'},
 'decision':{'valid_states':['VERIFIED','BLOCKED','INFRASTRUCTURE_FAILURE'],'manual_override_allowed':False}}
 try:
  require(all(sha(ROOT/p)==h for p,h in PINS.items()),'INPUT_MUTATION: required source/checker hash')
  approved={p:PINS[p] for p in (SPEC,ORDER,ORDER_TYPES)}
  for p in REVIEWS:
   r=json.loads((ROOT/p).read_text()); require(r.get('decision')=='APPROVE_GAMEPLAN' and r.get('input_hashes')==approved,'CLAIM_MUTATION or missing approval: '+p)
  expected={}
  for p in helpers.INHERITED:
   require(sha(ROOT/p)==helpers.INHERITED_HASHES[p],'INPUT_MUTATION inherited registry: '+p)
   part=json.loads((ROOT/p).read_text());require(not(set(expected)&set(part)),'CLAIM_MUTATION duplicate inherited theorem');expected.update(part)
  dt=json.loads((ROOT/DOC_TYPES).read_text())['theorem_types']; ot=json.loads((ROOT/ORDER_TYPES).read_text())['theorem_types']
  require((len(expected),len(dt),len(ot))==(112,125,14),'CLAIM_MUTATION theorem counts')
  require(json.loads((ROOT/DOC_TYPES).read_text())['source_sha256']==PINS[DOC],'CLAIM_MUTATION document type source')
  require(json.loads((ROOT/ORDER_TYPES).read_text())['source_sha256']==PINS[ORDER],'CLAIM_MUTATION order type source')
  for source,types in [(DOC,dt),(ORDER,ot)]:
   text=(ROOT/source).read_text();names=re.findall(r'(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)',text)
   require(len(names)==len(set(names)) and set(names)==set(types),'CLAIM_MUTATION registry: '+source)
  formal=[p for p in (ROOT/'formal').rglob('*.lean') if '.lake' not in p.parts]
  for f in formal+[ROOT/ORDER]:require(not helpers.ESCAPE.search(f.read_text()),'VERIFIER_FAILURE forbidden construct: '+str(f))
  require(json.loads((ROOT/'formal/lake-manifest.json').read_text())['packages']==[],'UNDECLARED_DEPENDENCY Lean packages')
  inputs=set(formal)|{ROOT/'formal/lean-toolchain',ROOT/'formal/lakefile.toml',ROOT/'formal/lake-manifest.json',ROOT/ORDER,ROOT/ORDER_TYPES,ROOT/DOC_DRAFT,ROOT/DOC_TYPES,ROOT/SPEC,ROOT/CHECKER,Path(__file__).resolve(),BASE}|{ROOT/p for p in REVIEWS+helpers.INHERITED}
  entries=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sorted(inputs)]
  claims=[]
  for prefix,registry in [('inherited',expected),('document',dt),('order',ot)]:
   for symbol,statement in registry.items():claims.append({'id':prefix+':'+symbol,'statement':statement,'verifier':'V-LEAN-EXACT','claim_class':'proof_compilation','scope':'frozen formal model','pass_condition':'exact statement/type and allowed axioms checked in both clean builds','witness':symbol.split('.')[-1].startswith('witness_')})
  require(len({c['id'] for c in claims})==251,'CLAIM_MUTATION duplicate identifiers')
  report['witnesses']['required']=sum(c['witness'] for c in claims)
  save(out/'claims.json',claims);save(out/'tcb.json',{'trusted_components':TRUST,'excluded':EXCLUDED})
  save(out/'verifier-registry.json',{'id':'V-LEAN-EXACT','sha256':sha(__file__),'helper_sha256':sha(BASE),'claim_classes':['proof_compilation'],'exit_codes':{'pass':0,'block':1,'infrastructure_failure':2},'nondeterministic_fields':['timestamp','temporary paths','build duration'],'predicate':'all exact statements, allowed axiom reports and artifacts agree in two isolated builds with unchanged input root'})
  save(out/'config.json',{'schema_version':'1.0','required_clean_builds':2,'determinism_required':True,'manual_override':False,'network_required':False,'claim_scope':'formal model only'})
  for generated in ('claims.json','tcb.json','verifier-registry.json','config.json'):entries.append({'path':'generated/'+generated,'sha256':sha(out/generated)})
  entries.sort(key=lambda x:x['path']);manifest={'schema_version':'1.0','files':entries};root=hashlib.sha256(packed(manifest)).hexdigest();report['input_root_hash']=root;save(out/'manifest.json',manifest)
  for item in entries:
   if item['path'].startswith('generated/'):continue
   dest=out/'inputs'/item['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/item['path'],dest)
  audit='import Allow\n'+'\n'.join('example : ('+v+') := @'+k+'\n#print axioms '+k for k,v in expected.items())+'\n'
  doc_checks='import Allow.Document\n'+'\n'.join('#check Allow.DocumentDraft.'+n for n in dt)+'\n'
  doc_axioms='import Allow.Document\n'+'\n'.join('#print axioms Allow.DocumentDraft.'+n for n in dt)+'\n'
  order_source=(out/'inputs'/ORDER).read_text();order_checks=order_source+'\n'+'\n'.join('#check Allow.DocumentOrder.'+n for n in ot)+'\n';order_axioms=order_source+'\n'+'\n'.join('#print axioms Allow.DocumentOrder.'+n for n in ot)+'\n'
  tool=Path.home()/'.elan/toolchains/leanprover--lean4---v4.34.1/bin';require((tool/'lake').is_file(),'VERIFIER_FAILURE missing pinned Lean')
  env=os.environ.copy();env['PATH']=str(tool)+os.pathsep+env.get('PATH','');env.pop('LEAN_PATH',None)
  report['environment']={'python':sys.version,'platform':platform.platform(),'toolchain':'leanprover/lean4:v4.34.1'}
  for label in ('A','B'):
   with tempfile.TemporaryDirectory(prefix='allow-order-clean-') as tmp:
    work=Path(tmp)/'formal';shutil.copytree(out/'inputs/formal',work)
    for file,contents in [('InheritedAudit.lean',audit),('DocumentTypes.lean',doc_checks),('DocumentAxioms.lean',doc_axioms),('OrderTypes.lean',order_checks),('OrderAxioms.lean',order_axioms)]: (work/file).write_text(contents,encoding='utf-8')
    outputs={};outputs['build']=cmd([str(tool/'lake'),'build'],work,env,out/f'{label}-build.log')
    for key,file in [('inherited','InheritedAudit.lean'),('document_types','DocumentTypes.lean'),('document_axioms','DocumentAxioms.lean'),('order_types','OrderTypes.lean'),('order_axioms','OrderAxioms.lean')]:outputs[key]=cmd([str(tool/'lake'),'env','lean',file],work,env,out/f'{label}-{key}.log')
    helpers.check_axioms(outputs['inherited'],list(expected));helpers.check_axioms(outputs['document_axioms'],['Allow.DocumentDraft.'+n for n in dt]);helpers.check_axioms(outputs['order_axioms'],['Allow.DocumentOrder.'+n for n in ot])
    require(outputs['document_types']=='\n'.join(dt.values())+'\n','VERIFIER_FAILURE document exact types');require(outputs['order_types']=='\n'.join(ot.values())+'\n','VERIFIER_FAILURE order exact types')
    artifacts={p.relative_to(work).as_posix():sha(p) for p in sorted(work.rglob('*.olean'))};require(artifacts,'CLEAN_BUILD_FAILURE no artifacts')
    digests={key:hashlib.sha256(value.encode()).hexdigest() for key,value in outputs.items() if key!='build'}
    report['builds']['records'].append({'label':label,'artifacts':artifacts,'audit_hashes':digests,'input_root_hash':root});report['builds']['passed']+=1
  a,b=report['builds']['records'];require(a['artifacts']==b['artifacts'] and a['audit_hashes']==b['audit_hashes'],'NONDETERMINISM')
  for item in entries:
   current=out/item['path'].replace('generated/','',1) if item['path'].startswith('generated/') else ROOT/item['path']
   require(sha(current)==item['sha256'],'INPUT_MUTATION: '+item['path'])
  require({p.relative_to(ROOT).as_posix() for p in (ROOT/'formal').rglob('*.lean') if '.lake' not in p.parts}=={p.relative_to(ROOT).as_posix() for p in formal},'INPUT_MUTATION: Lean source inventory')
  report['determinism']['status']='PASS';report['claims'].update({'passed':251,'unresolved':0});report['witnesses']['valid']=report['witnesses']['required'];report['provenance']['fully_bound']=251
  evidence=[]
  for c in claims:
   evidence.append({'claim_id':c['id'],'closure_id':report['closure_id'],'input_root_hash':root,'verifier_id':'V-LEAN-EXACT','verifier_hash':sha(__file__),'environment':report['environment'],'raw_result':'exact type and allowed axioms checked in clean builds A and B','exit_code':0,'status':'PASS','logs':['A-inherited.log','B-inherited.log'] if c['id'].startswith('inherited:') else (['A-document_types.log','B-document_types.log','A-document_axioms.log','B-document_axioms.log'] if c['id'].startswith('document:') else ['A-order_types.log','B-order_types.log','A-order_axioms.log','B-order_axioms.log'])})
  save(out/'evidence.json',evidence);save(out/'provenance.json',[{'public_claim':c['id'],'claim_id':c['id'],'evidence':'evidence.json','verifier':'V-LEAN-EXACT','inputs':['manifest.json'],'trusted_dependencies':TRUST} for c in claims]);report['status']='VERIFIED'
 except AssertionError as e:
  report['status']='BLOCKED';report['blocking_reasons'].append(str(e));report['claims']['blocked']=1;report['claims']['unresolved']=250
 except Exception as e:
  report['status']='INFRASTRUCTURE_FAILURE';report['infrastructure_errors'].append(type(e).__name__+': '+str(e))
 save(out/'report.json',report);print(json.dumps({'status':report['status'],'input_root_hash':report['input_root_hash'],'claims':report['claims'],'builds':report['builds']['passed'],'blocking_reasons':report['blocking_reasons'],'infrastructure_errors':report['infrastructure_errors']},indent=2));return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]
if __name__=='__main__':sys.exit(main())
