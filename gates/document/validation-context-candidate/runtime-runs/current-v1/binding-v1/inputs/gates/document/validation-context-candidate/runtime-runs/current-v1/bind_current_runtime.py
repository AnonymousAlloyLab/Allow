"""Bind current186/52 runtime evidence and309 formal-source projection, not all VC gates."""
from datetime import datetime, timezone
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'retrieval')]
ROLES={
 'python':'gates/document/inherited-runtime-tests.json',
 'sql':'gates/sql/runtime-tests.json',
 'clients':'gates/sql/client-coverage.json',
 'retrieval_recovery':'gates/sql/recovery-report.json',
 'document_recovery':'gates/document/document-recovery-report.json',
 'inventory':'gates/document/sql-client-inventory.json',
 'document_tests':'db/document/runtime-evidence.json',
 'null_start':'gates/document/store-null-start-recovery-report.json'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def require(condition,message):
    if not condition:raise AssertionError(message)
def module(name,path):
    specification=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(specification);specification.loader.exec_module(result);return result


def test_members(log,source,module_name):
    """Match actual test headers/results, including unittest's second-line docstrings."""
    headers=list(re.finditer(r'(?m)^(test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\)',log))
    actual={}
    for index,header in enumerate(headers):
        block=log[header.start():headers[index+1].start()if index+1<len(headers)else len(log)]
        if '... ok' in block:actual[header.group(2)]=block
    expected=[]
    for cls in ast.parse(source.read_text()).body:
        if isinstance(cls,ast.ClassDef):
            for method in cls.body:
                if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))and method.name.startswith('test_'):
                    expected.append(module_name+'.'+cls.name+'.'+method.name)
    require(len(expected)==22 and len(set(expected))==22 and all(name in actual for name in expected),'TEST_MEMBERSHIP:'+module_name)
    return expected


def main():
    require(len(sys.argv)==2 and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sys.argv[1]),'INVALID_RUN_ID')
    out=HERE/sys.argv[1];out.mkdir(parents=True,mode=0o700,exist_ok=False)
    report={'status':'UNSET','classification':'CURRENT_STAGE_FINITE_RUNTIME_EVIDENCE_NOT_FULL_VC_CLOSURE',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'blocking_reasons':[],'infrastructure_errors':[],
        'out_of_scope':['VC19 large-history memory/wall profile','HTTP/browser/restart and candidate full server latency benchmark','Universal implementation refinement or complete product gate closure']}
    try:
        criteria={'python':{'tests':186,'failures':0,'errors':0,'skipped':0,'source_unchanged':True},
            'sql':{'tests':52,'failures':0,'errors':0,'skipped':0,'source_unchanged':True,'real_proxy_coverage':True,'daemon_pid_stable':True},
            'clients':{'source_unchanged':True,'each_registered_tag_accepted':True,'live_corpus_unchanged':True},
            'retrieval_recovery':{'source_unchanged':True,'live_corpus_modified':False},
            'document_recovery':{'source_unchanged':True,'actual_pg_dump_restore':True,'live_database_targeted':False,
                'restored_rows_owners_rls_and_acls_equal':True,'fresh_process_exact_receipt_recovery':True,'private_metadata_unchanged':True},
            'inventory':{'source_unchanged':True},'document_tests':{'tests':22,'failures':0,'errors':0,'skipped':0,'source_unchanged':True},
            'null_start':{'tests':1,'failures':0,'errors':0,'skipped':0,'source_unchanged':True},
            'all_statuses':'PASS','exact_current_inventories':['fullPython','SQLruntime','client','documentRecovery','staticInventory'],
            'context_tests':22,'model_propositions':309,'proxy_pid':826907,'proxy_generation':1,
            'trust':['Registered test executables and truthful instrumentation','Lean4.34.1 finite-model checker and allowed axioms','Python/SHA256','OS/kernel/PostgreSQL/processes/hardware']}
        save(out/'claims.json',criteria)
        save(out/'verifier-registry.json',{'id':'V-CURRENT-VALIDATION-CONTEXT-RUNTIME-BINDING','sha256':sha(Path(__file__)),'exit_codes':{'PASS':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}})
        loaded={role:read(ROOT/path)for role,path in ROLES.items()}
        required={Path(__file__),HERE/'refresh_document_test_evidence.py'}|{ROOT/path for path in ROLES.values()}
        for role,value in loaded.items():
            require(value['status']=='PASS','NOT_PASS:'+role)
            for key,wanted in criteria[role].items():require(value.get(key)==wanted,'PREDICATE:'+role+':'+key)
            for field in('runtime_identity_before','runtime_identity_after'):
                if field in value:require(value[field]['status']=='PASS'and value[field]['pid']==826907,'STALE_DAEMON:'+role)
            source=value.get('input_sha256_before')
            if source is not None:require(source==value.get('input_sha256_after'),'SOURCE_CHANGED:'+role)
            for rows in [value.get('files',[]),value.get('input_sha256_before',{}),value.get('input_sha256',{}),value.get('source_sha256',{}),value.get('inventory',{}).get('scanned_file_sha256',{})]:
                items=((row['path'],row['sha256'])for row in rows)if isinstance(rows,list)else rows.items()
                for name,digest in items:
                    require(sha(ROOT/name)==digest,'CURRENT_SOURCE_CHANGED:'+role+':'+name);required.add(ROOT/name)
        corpus=module('current_context_corpus',ROOT/'scripts/verify_corpus_runtime.py')
        current_python,python_root=corpus.fingerprint()
        require(current_python==loaded['python']['files']and python_root==loaded['python']['input_root_sha256'],'PYTHON_COMPLETE_INVENTORY_CHANGED')
        sql=module('current_context_sql',ROOT/'scripts/verify_sql_runtime.py')
        current_sql,sql_root=sql.fingerprint()
        require(current_sql==loaded['sql']['files']and sql_root==loaded['sql']['input_root_sha256'],'SQL_COMPLETE_INVENTORY_CHANGED')
        clients=module('current_context_clients',ROOT/'scripts/verify_sql_clients.py')
        current_clients=clients.fingerprint()
        require(current_clients==loaded['clients']['input_sha256_before']==loaded['inventory']['input_sha256'],'CLIENT_COMPLETE_INVENTORY_CHANGED')
        current_inventory=clients.inventory()
        require(current_inventory==loaded['clients']['inventory']==loaded['document_recovery']['inventory']==loaded['inventory']['inventory'],'STATIC_AST_INVENTORY_CHANGED')
        recovery=module('current_context_document_recovery',ROOT/'scripts/document_recovery_test.py')
        require(recovery.inputs()==loaded['document_recovery']['input_sha256_before'],'DOCUMENT_RECOVERY_COMPLETE_INVENTORY_CHANGED')
        require(loaded['clients']['inventory']['status']=='PASS','CLIENT_AST_STATUS')
        require(loaded['retrieval_recovery']['recovery']['status']=='PASS'and loaded['retrieval_recovery']['recovery']['actual_pg_dump_restore']and loaded['retrieval_recovery']['recovery']['restored_acl_equal'],'RETRIEVAL_ACL_FAILED')
        require(loaded['document_recovery']['full_acl_entries']>0,'DOCUMENT_ACL_EMPTY')
        pylog=ROOT/'gates/document/inherited-runtime-tests.log';log=pylog.read_text();required.add(pylog)
        context_members=test_members(log,ROOT/'retrieval/tests/test_validation_context.py','test_validation_context')
        document_members=test_members(log,ROOT/'retrieval/tests/test_documents.py','test_documents')
        require(loaded['document_tests']['tested_symbols']==document_members,'DOCUMENT_SUBSET_MEMBERSHIP')
        null='test_documents.DocumentSQLTests.test_reaped_worker_without_captured_start_ticks_requires_absent_pid'
        require(loaded['null_start']['tested_symbols']==[null]and null in document_members,'NULL_START_TEST_MEMBERSHIP')
        for role in('document_tests','null_start'):
            evidence=loaded[role]['evidence']
            require(evidence['full_suite_tests']==186 and evidence['full_suite_report_sha256']==sha(ROOT/'gates/document/inherited-runtime-tests.json')and evidence['full_suite_log_sha256']==sha(pylog),'SUBSET_EVIDENCE_STALE:'+role)
            require(loaded[role]['subset_timing']=='NOT_SEPARATELY_MEASURED'and loaded[role]['subset_proxy_counter_attribution']=='NOT_MEASURED','SUBSET_OVERCLAIM')
        # Inherit309 by exact installed definitions/import transformation, not by reopening old287 stage.
        activation=read(CANDIDATE/'formal-activation.json');formal=CANDIDATE/'formal-runs/final-309-v1';model=read(formal/'report.json')
        require(model['status']=='VERIFIED'and model['claims']['passed']==309,'MODEL309_NOT_VERIFIED')
        require(sha(formal/'report.json')==activation['formal_report_sha256'],'MODEL_ACTIVATION_REPORT_CHANGED')
        for name,digest in activation['active_files'].items():require(sha(ROOT/name)==digest,'FORMAL_ACTIVATION_CHANGED:'+name);required.add(ROOT/name)
        formal_manifest=read(formal/'manifest.json');original_names=set()
        for row in formal_manifest['files']:
            name=row['path']
            if not name.startswith('formal/')or not name.endswith('.lean'):continue
            snapshot=formal/'inputs'/name;require(sha(snapshot)==row['sha256'],'MODEL309_SNAPSHOT_CHANGED')
            expected=snapshot.read_bytes()+b'\nimport Allow.ValidationContextCandidate\n'if name=='formal/Allow.lean'else snapshot.read_bytes()
            require((ROOT/name).read_bytes()==expected,'MODEL309_DEFINITION_CHANGED:'+name)
            original_names.add(name);required|={snapshot,ROOT/name}
        current_names={str(path.relative_to(ROOT))for path in(ROOT/'formal').rglob('*.lean')if'.lake'not in path.parts}
        require(current_names==original_names|{'formal/Allow/ValidationContextCandidate.lean'},'MODEL309_CURRENT_INVENTORY_CHANGED')
        require((ROOT/'formal/Allow/ValidationContextCandidate.lean').read_bytes()==(CANDIDATE/'ValidationContext.lean').read_bytes(),'MODEL309_CANDIDATE_COPY_CHANGED')
        build=CANDIDATE/'final-build/build-manifest.json';build_data=read(build)
        for name,digest in build_data['source_sha256'].items():require(sha(ROOT/name)==digest,'BUILD_BOUND_SOURCE_CHANGED:'+name);required.add(ROOT/name)
        require(sha(CANDIDATE/'final-build/build.log')==build_data['log_sha256'],'BUILD_LOG_CHANGED')
        status=sql.read_status(ROOT/'.runtime/corpus/sql-proxy/status.json');identity=sql.runtime_identity(status)
        require(identity['status']=='PASS'and identity['pid']==826907 and status['parser']['generation']==1,'CURRENT_RUNTIME_STALE')
        require(status['parser']['policy']=='sql-routing-v7-sealed-image','PARSER_POLICY_CHANGED')
        save(out/'current-runtime.json',{'published':status,'identity':identity})
        required|={CANDIDATE/'formal-activation.json',formal/'report.json',formal/'manifest.json',CANDIDATE/'ValidationContext.lean',build,CANDIDATE/'final-build/build.log'}
        for path in list(required):
            if path.suffix=='.json'and path.with_suffix('.log').is_file():required.add(path.with_suffix('.log'))
        entries=[{'path':str(path.relative_to(ROOT)),'sha256':sha(path)}for path in sorted(required)]
        entries += [{'path':'generated/'+name,'sha256':sha(out/name)}for name in['claims.json','verifier-registry.json','current-runtime.json']]
        manifest={'files':sorted(entries,key=lambda row:row['path'])};root_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        save(out/'manifest.json',manifest)
        for path in required:
            target=out/'inputs'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        for row in entries:
            original=out/row['path'][10:]if row['path'].startswith('generated/')else ROOT/row['path']
            require(sha(original)==row['sha256'],'INPUT_MUTATION:'+row['path'])
            if not row['path'].startswith('generated/'):require(sha(out/'inputs'/row['path'])==row['sha256'],'SNAPSHOT_MUTATION:'+row['path'])
        report.update(status='PASS',input_root_sha256=root_hash,python_tests=186,new_validation_context_tests=22,existing_document_tests=22,sql_tests=52,
            failures=0,errors=0,skips=0,formal_model_propositions=309,formal_scope='Exact installed model-definition projection; no Java/Python implementation refinement',
            context_test_symbols=context_members,document_test_symbols=document_members,
            complete_current_inventories={'python':python_root,'sql':sql_root,'clients':True,'static_ast':True,'document_recovery':True,'build_inputs':len(build_data['source_sha256'])},
            runtime={'pid':826907,'generation':1,'policy':'sql-routing-v7-sealed-image'},
            roles={role:{'path':path,'sha256':sha(ROOT/path),'status':'PASS'}for role,path in ROLES.items()},
            interpretation='Finite currently bound runtime/recovery checks and309-model source projection passed. VC19 profiling, HTTP/browser and final latency gate remain separately registered obligations.')
    except AssertionError as error:report['status']='BLOCKED';report['blocking_reasons'].append(str(error))
    except Exception as error:report['status']='INFRASTRUCTURE_FAILURE';report['infrastructure_errors'].append(type(error).__name__+': '+str(error))
    save(out/'report.json',report)
    print(json.dumps({key:report.get(key)for key in['status','input_root_sha256','python_tests','new_validation_context_tests','sql_tests','blocking_reasons','infrastructure_errors']},indent=2))
    return {'PASS':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]


if __name__=='__main__':raise SystemExit(main())
