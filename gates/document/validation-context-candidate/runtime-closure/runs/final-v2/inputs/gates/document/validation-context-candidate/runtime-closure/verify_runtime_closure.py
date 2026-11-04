"""Strict finite26 runtime evidence binder. Missing planned cases remain BLOCKED.

--freeze registers verifier/mapping/current inputs before --execute evaluates them.
No new SQL, test, compiler or benchmark execution occurs here.
"""
import argparse,ast,hashlib,importlib.util,json,math,re,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as XML
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent;CANDIDATE=HERE.parent
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'retrieval')]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
read=lambda path:json.loads(Path(path).read_text())
pack=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def require(value,why):
 if not value:raise AssertionError(why)
def mod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def collect():
 mapping=read(HERE/'case-mapping-r2.json');paths={Path(__file__),HERE/'case-mapping-r2.json',CANDIDATE/'runtime-test-plan.json',CANDIDATE/'contract.json',CANDIDATE/'review-input-pins.json'}
 for value in mapping['records'].values():
  for field in ['source','result_report','raw_log','result_xml','build_manifest','path']:
   if field in value:paths.add(ROOT/value[field])
 for directory in ['runtime-checks','runtime-profiles/vc19-r1','final-build']:
  paths|={path for path in(CANDIDATE/directory).rglob('*')if path.is_file()and'__pycache__'not in path.parts}
 for name in ['gates/document/server-benchmark-runs/validation-context-v1/server-performance.json','gates/document/server-benchmark-runs/validation-context-v1/verifier.py','gates/document/server-benchmark-runs/validation-context-v1/server-performance-progress.json','gates/document/server-benchmark-runs/sealed-v1/server-performance.json']:
  paths.add(ROOT/name)
 for name in ['gates/document/inherited-runtime-tests.json','gates/sql/runtime-tests.json','gates/sql/client-coverage.json','gates/document/document-recovery-report.json']:
  value=read(ROOT/name);paths.add(ROOT/name)
  for field in ['files','input_sha256_before']:
   rows=value.get(field,[]);items=((x['path'],x['sha256'])for x in rows)if isinstance(rows,list)else rows.items()
   paths|={ROOT/p for p,_ in items}
 for path in list(paths):
  if path.suffix=='.json'and path.with_suffix('.log').is_file():paths.add(path.with_suffix('.log'))
 return paths

def freeze():
 path=HERE/'registration-r3.json';require(not path.exists(),'EXISTING_REGISTRATION')
 files=[{'path':str(path.relative_to(ROOT)),'sha256':sha(path)}for path in sorted(collect())]
 save(path,{'id':'V-VALIDATION-CONTEXT-RUNTIME-R2','files':files,'input_root_sha256':hashlib.sha256(pack(files)).hexdigest(),
  'claim_set':'case-mapping-r2.json','decision':'BLOCKED for any remaining required case or failed check; product300ms acceptance always separate',
  'trusted':['Registered executable test/probe verifiers and instrumentation','Finite assertion/source interpretation in frozen case mapping (not formal semantic correspondence)','Python/XML/JSON/SHA256','OS/kernel/PostgreSQL/libpq/JVM/Lean and hardware'],
  'excluded':['Universal implementation refinement','Unexecuted literal cases','Cold/manualaccessibility','Automatic backend lifetime bound after killed client','Product300ms acceptance if actualtargetfails']})
 print(json.dumps({'registered':str(path),'input_root_sha256':read(path)['input_root_sha256']}))

def py_ok(value):
 log=(ROOT/value['raw_log']).read_text();pattern=r'(?m)^'+re.escape(value['symbol'].split('.')[-1])+r' \('+re.escape(value['symbol'])+r'\)'
 hits=list(re.finditer(pattern,log));require(len(hits)==1,'PY_TEST_MISSING:'+value['symbol'])
 rest=log[hits[0].end():];block=re.split(r'(?m)^test_',rest,maxsplit=1)[0]
 require('... ok'in block,'PY_TEST_NOT_OK:'+value['symbol'])
 source=ROOT/value['source'];body='\n'.join(source.read_text().splitlines()[value['line']-1:value['end_line']])+'\n'
 require(sha(source)==value['source_sha256']and hashlib.sha256(body.encode()).hexdigest()==value['body_sha256'],'PY_ASSERTIONS_CHANGED')

def java_ok(value):
 require(sha(ROOT/value['source'])==value['source_sha256'],'JAVA_ASSERTIONS_CHANGED')
 suite=XML.parse(ROOT/value['result_xml']).getroot();cases=[case for case in suite.findall('testcase')if case.get('name')==value['method']and case.get('classname')==value['class']]
 require(len(cases)==1 and not any(cases[0].find(x)is not None for x in ['failure','error','skipped']),'JAVA_CASE_NOT_OK:'+value['method'])
 build=read(ROOT/value['build_manifest']);require(build['source_sha256'].get(value['source'])==value['source_sha256'],'JAVA_BUILD_UNBOUND')

def benchmark():
 folder=ROOT/'gates/document/server-benchmark-runs/validation-context-v1';r=read(folder/'server-performance.json');b=read(ROOT/'gates/document/server-benchmark-runs/sealed-v1/server-performance.json')
 require(r['warmups']==100 and r['events']==1000 and len(r['samples_ms'])==1000 and not r['failures']and r['source_unchanged'],'BENCHMARK_INCOMPLETE')
 require(r['target_p95_ms']==300 and r['status']==('PASS'if r['p95_ms']<300 else'FAIL'),'TARGET_MISSTATED')
 for name,q in [('p50_ms',.5),('p95_ms',.95),('p99_ms',.99)]:require(r[name]==sorted(r['samples_ms'])[math.ceil(1000*q)-1],'PERCENTILE')
 require(r['identity_checks']==[{'completed_events':n,'unchanged':True}for n in range(100,1101,100)],'CHECKPOINTS')
 require(sha(folder/'verifier.py')==r['verifier_sha256'],'BENCHMARK_VERIFIER')
 for key in ['warmups','events','node_count','shared_fixture_sha256','fixture_source_sha256','method','verifier_sha256','target_p95_ms']:require(r[key]==b[key],'BENCHMARK_CONTEXT:'+key)
 m=mod('vc_benchmark',ROOT/'scripts/benchmark_documents.py');files,root=m.server_fingerprint();require(files==r['source_sha256']and root==r['input_root_sha256'],'BENCHMARK_SOURCE_STALE')
 return {'measurement':'COMPLETE','status':r['status'],'p95_ms':r['p95_ms'],'original_target_p95_ms':300,'gate':'OPEN'if r['status']=='FAIL'else'PASSED','baseline_p95_ms':b['p95_ms'],'measured_p95_improvement_ms':b['p95_ms']-r['p95_ms']}

def supplemental():
 py=read(CANDIDATE/'runtime-checks/python/r2/runs/run-20261103T223426Z/report.json');require(py['status']=='PASS'and py['owned_fixture_database_dropped']and py['proxy_identity_unchanged'],'PY_SUPP_FAIL')
 checks=py['checks'];require(all(c['status']=='PASS'for c in checks.values())and len(checks)==7,'PY_GROUPS')
 p1=checks['P01_protocol_order']['evidence'];require(p1['commands']==['BEGIN','mode','tenant','project','purpose','head','base','history','COMMIT']and p1['connection_closed']and p1['durable_unchanged'],'ACTUAL_TRACE')
 p2=checks['P02_first_scope_race']['evidence'];require(p2['base_immutable']and p2['new_identity_visible_only_in_new_snapshot']and p2['old_head']==1 and p2['new_head']==2,'FIRST_SCOPE_RACE')
 p3=checks['P03_encoded_size']['evidence'];require(p3['maximum_valid_compact_args_bytes']==188512 and all(x['sql_calls']==0 for x in p3['adversarial_invalid_id_cases']),'ARGS_BOUNDARY')
 p5=checks['P05_staged_faults']['evidence'];require(len(p5['cases'])==22 and all(x['status']=='UNAVAILABLE'and x['durable_unchanged']for x in p5['cases']),'FAULT_MATRIX')
 for key in ['P06_actual_cancel','P07_actual_timeout']:
  x=checks[key]['evidence'];require(x['owned_process_reaped']and x['owned_backend_absent']and x['durable_after_equal'],'CANCEL_OR_TIMEOUT')
 require(checks['P07_actual_timeout']['evidence']['cleanup_cancel_needed']is True,'LIFECYCLE_DISCLOSURE')
 handoff=read(CANDIDATE/'runtime-checks/python/handoff-r1.json');require(handoff['status']=='FINITE_SUPPLEMENTAL_CHECKS_PASS_WITH_EXPLICIT_LIFECYCLE_LIMITATION'and handoff['active_sources_match_all_preregistered_hashes_after_execution'],'AUTH_HANDOFF')
 for row in handoff['files']:require(sha(ROOT/row['path'])==row['sha256'],'PY_HANDOFF_HASH')
 for name in ['result','head-result','sequence-result','actual-sequence-result','ownership-result']:
  x=read(CANDIDATE/f'runtime-checks/java/{name}.json');require(x['status']=='PASS'and x['inputs_unchanged']and x['temporary_output_removed'],'JAVA_SUPP_FAIL:'+name)
  require(all(c['exit_code']==0 for c in x['commands']),'JAVA_SUPP_COMMAND:'+name)
 x=read(CANDIDATE/'runtime-checks/java/actual-sequence-result.json')['commands'][-1]['stdout'];pids=re.findall(r'worker_pid=(\d+)',x);require(len(pids)==2 and len(set(pids))==2 and x.count('launcher_command=')==2,'ACTUAL_WORKER_SEQUENCE')
 commands=re.findall(r'(?m)^launcher_command=(.*)$',x);require(commands[0]==commands[1],'LAUNCH_FLAGS_CHANGED')
 x=read(CANDIDATE/'runtime-checks/java/ownership-result.json')['commands'][-1]['stdout'];require(all(t in x for t in ['missing status=INVALID','foreign status=INVALID','wrong-kind status=INVALID','positive status=VALIDATED']),'WORKER_OWNERSHIP')
 # Source fact: every history SQL call is syntactically inside `if wanted`.
 source=ast.parse((ROOT/'retrieval/allow_documents/store.py').read_text());cls=next(x for x in source.body if isinstance(x,ast.ClassDef)and x.name=='Store');fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef)and x.name=='_history_inventory')
 guard=next(x for x in fn.body if isinstance(x,ast.If)and isinstance(x.test,ast.Name)and x.test.id=='wanted')
 all_calls=[x for x in ast.walk(fn)if isinstance(x,ast.Call)];inside=[x for x in ast.walk(guard)if isinstance(x,ast.Call)];require(all(x in inside for x in all_calls),'EMPTY_HISTORY_GUARD')
 return {'python_groups':7,'r2_scenarios':40,'auth_strengthened_repeats':2,'main_python_count':186,'main_java_count':189,'composition':'Actual SQL COMMIT/closedconnection + actual bridgeexit/twofreshworkers, not monolithic HTTP trace'}

def execute(run):
 out=HERE/'runs'/run;out.mkdir(parents=True,mode=0o700,exist_ok=False)
 result={'status':'UNSET','classification':'FINITE_RUNTIME_EVIDENCE_NOT_FORMAL_IMPLEMENTATION_REFINEMENT','blocking_reasons':[],'infrastructure_errors':[]}
 try:
  reg=read(HERE/'registration-r3.json');require(hashlib.sha256(pack(reg['files'])).hexdigest()==reg['input_root_sha256'],'REGISTRATION_ROOT')
  for row in reg['files']:require(sha(ROOT/row['path'])==row['sha256'],'INPUT_MUTATION:'+row['path'])
  save(out/'registration.json',reg)
  for row in reg['files']:
   target=out/'inputs'/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/row['path'],target)
  mapping=read(HERE/'case-mapping-r2.json');plan=read(CANDIDATE/'runtime-test-plan.json');require(mapping['frozen_plan_sha256']==sha(CANDIDATE/'runtime-test-plan.json')and len(mapping['obligations'])==26,'PLAN_CHANGED')
  for value in mapping['records'].values():
   if value['kind']=='python_test':py_ok(value)
   elif value['kind']=='junit_test':java_ok(value)
   else:require(sha(ROOT/value['path'])==value['sha256'],'REPORT_CHANGED:'+value['path'])
  result['supplemental']=supplemental();result['product_latency']=benchmark()
  corpus=mod('vc_corpus',ROOT/'scripts/verify_corpus_runtime.py');files,root=corpus.fingerprint();p=read(ROOT/'gates/document/inherited-runtime-tests.json');require(files==p['files']and root==p['input_root_sha256']and p['tests']==186 and not any(p[x]for x in ['failures','errors','skipped']),'PYTHON_INVENTORY')
  sql=mod('vc_sql',ROOT/'scripts/verify_sql_runtime.py');files,root=sql.fingerprint();p=read(ROOT/'gates/sql/runtime-tests.json');require(files==p['files']and root==p['input_root_sha256']and p['tests']==52 and p['status']=='PASS','SQL_INVENTORY')
  client=mod('vc_clients',ROOT/'scripts/verify_sql_clients.py');require(client.fingerprint()==read(ROOT/'gates/sql/client-coverage.json')['input_sha256_before'],'CLIENT_INVENTORY')
  state=sql.read_status(ROOT/'.runtime/corpus/sql-proxy/status.json');identity=sql.runtime_identity(state);require(identity['status']=='PASS'and identity['pid']==826907 and state['parser']['generation']==1,'RUNTIME_IDENTITY')
  rows=[]
  for row in mapping['obligations']:
   item=dict(row,status='BLOCKED'if row['remaining_required_cases']else'CHECKED_FINITE_EVIDENCE');rows.append(item)
  gaps=[dict(obligation=row['id'],**gap)for row in rows for gap in row['remaining_required_cases']]
  result.update(input_root_sha256=reg['input_root_sha256'],obligations={'total':26,'checked':sum(row['status']=='CHECKED_FINITE_EVIDENCE'for row in rows),'blocked':sum(row['status']=='BLOCKED'for row in rows)},matrix=rows,remaining_required_cases=gaps,material_limitations=mapping['material_limitations'],trust=reg['trusted'],excluded=reg['excluded'])
  if gaps:result['blocking_reasons']=[gap['gap_id']for gap in gaps]
  for row in reg['files']:require(sha(ROOT/row['path'])==row['sha256']and sha(out/'inputs'/row['path'])==row['sha256'],'STALE_EVIDENCE:'+row['path'])
  result['status']='BLOCKED'if gaps else'VERIFIED'
 except AssertionError as error:result['status']='BLOCKED';result['blocking_reasons'].append(str(error))
 except Exception as error:result['status']='INFRASTRUCTURE_FAILURE';result['infrastructure_errors'].append(type(error).__name__+': '+str(error))
 save(out/'report.json',result);print(json.dumps({k:result.get(k)for k in ['status','input_root_sha256','obligations','blocking_reasons','infrastructure_errors','product_latency']},indent=2))
 return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[result['status']]

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--freeze',action='store_true');parser.add_argument('--execute',metavar='RUN_ID');args=parser.parse_args()
 if args.freeze:freeze()
 elif args.execute:sys.exit(execute(args.execute))
 else:parser.error('choose --freeze or --execute RUN_ID')
