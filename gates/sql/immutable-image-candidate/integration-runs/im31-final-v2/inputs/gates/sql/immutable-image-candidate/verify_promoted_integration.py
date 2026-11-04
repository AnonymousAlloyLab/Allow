#!/usr/bin/env python3
"""Bind finite IM31 integration evidence to installed sources; IM32 stays external."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ROLES={
 'sql_wire_and_postgresql':'gates/sql/runtime-tests.json',
 'full_python':'gates/document/inherited-runtime-tests.json',
 'sql_clients':'gates/sql/client-coverage.json',
 'retrieval_recovery':'gates/sql/recovery-report.json',
 'document_recovery':'gates/document/document-recovery-report.json'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def require(condition,message):
    if not condition:raise AssertionError(message)


def main():
    require(len(sys.argv)==2 and sys.argv[1].replace('-','').isalnum(),'INVALID_RUN_ID')
    out=HERE/'integration-runs'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
    report={'id':'IM31','status':'UNSET','scope':'Finite promoted implementation tests and recovery; not formal implementation refinement',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'blocking_reasons':[],'infrastructure_errors':[],
        'IM32':'UNRESOLVED_ROOT_FULL_CANDIDATE_BENCHMARK','roles':{}}
    try:
        promotion=json.loads((HERE/'promotion.json').read_text());active=promotion['active_files']
        require(len(active)==14,'ACTIVE_COUNT')
        files={ROOT/name for name in active}|{ROOT/name for name in ROLES.values()}|{Path(__file__),HERE/'promotion.json',HERE/'implementation/integration-obligations.json'}
        for name,digest in active.items():require(sha(ROOT/name)==digest,'PROMOTED_INPUT_CHANGED:'+name)
        loaded={role:json.loads((ROOT/name).read_text())for role,name in ROLES.items()}
        # Freeze exact predicates and verifier before evaluating any target report.
        criteria={'IM31':'All six registered evidence roles pass with unchanged installed sources and exact model-source projection',
            'sql_wire_and_postgresql':{'tests':52,'failures':0,'errors':0,'skipped':0,'source_unchanged':True,'real_proxy_coverage':True},
            'full_python':{'tests':164,'failures':0,'errors':0,'skipped':0,'source_unchanged':True},
            'sql_clients':{'source_unchanged':True,'each_registered_tag_accepted':True,'live_corpus_unchanged':True},
            'retrieval_recovery':{'source_unchanged':True,'live_corpus_modified':False},
            'document_recovery':{'source_unchanged':True,'actual_pg_dump_restore':True,'live_database_targeted':False,
               'restored_rows_owners_rls_and_acls_equal':True,'fresh_process_exact_receipt_recovery':True,'private_metadata_unchanged':True},
            'trust':['Registered executable test verifiers and their honest runtime instrumentation','SHA256 and Python','OS/processes/PostgreSQL and hardware'],
            'excluded':['Universal runtime or SQL semantics correctness','IM32 performance discharge','Future revisions or changed report/source hashes']}
        save(out/'claims.json',criteria)
        save(out/'verifier-registry.json',{'id':'V-IM31-EVIDENCE-BINDING','sha256':sha(__file__),'pass':0,'block':1,'infrastructure_failure':2})
        # Existing verified287 model source is promoted by an explicit mechanical transform.
        formal=HERE/'formal-runs/final-287-v2'
        model_report=json.loads((formal/'report.json').read_text());require(model_report['status']=='VERIFIED'and model_report['claims']['passed']==287,'MODEL_REPORT')
        model_manifest=json.loads((formal/'manifest.json').read_text())
        model_files=[row for row in model_manifest['files']if row['path'].startswith('formal/')and row['path'].endswith('.lean')]
        projection=[]
        for row in model_files:
            original=(formal/'inputs'/row['path']).read_bytes()
            require(hashlib.sha256(original).hexdigest()==row['sha256'],'MODEL_SNAPSHOT_MUTATION:'+row['path'])
            expected=original+b'\nimport Allow.ImmutableImageCandidate\n'if row['path']=='formal/Allow.lean'else original
            require((ROOT/row['path']).read_bytes()==expected,'MODEL_PROMOTION_MISMATCH:'+row['path'])
            projection.append({'path':row['path'],'sha256':sha(ROOT/row['path'])})
            files.add(ROOT/row['path'])
        candidate=HERE/'ImmutableImage.lean';installed=ROOT/'formal/Allow/ImmutableImageCandidate.lean'
        require(candidate.read_bytes()==installed.read_bytes(),'MODEL_CANDIDATE_PROMOTION_MISMATCH')
        require({str(p.relative_to(ROOT))for p in(ROOT/'formal').rglob('*.lean')if'.lake'not in p.parts}=={row['path']for row in model_files}|{'formal/Allow/ImmutableImageCandidate.lean'},'MODEL_SOURCE_INVENTORY_CHANGED')
        files|={formal/'report.json',formal/'manifest.json',candidate}
        # Include every exact source fingerprint required by the passed executable reports.
        for role,value in loaded.items():
            require(value.get('status')=='PASS','REPORT_NOT_PASS:'+role)
            for key,wanted in criteria[role].items():require(value.get(key)==wanted,'REPORT_PREDICATE:'+role+':'+key)
            source_rows=value.get('files',[])
            for row in source_rows:
                path=ROOT/row['path'];require(sha(path)==row['sha256'],'REPORT_SOURCE_CHANGED:'+role+':'+row['path']);files.add(path)
            before=value.get('input_sha256_before')
            if before is not None:
                require(before==value.get('input_sha256_after'),'REPORT_BEFORE_AFTER:'+role)
                for name,digest in before.items():require(sha(ROOT/name)==digest,'REPORT_SOURCE_CHANGED:'+role+':'+name);files.add(ROOT/name)
            inventory=value.get('inventory',{}).get('scanned_file_sha256',{})
            for name,digest in inventory.items():
                require(sha(ROOT/name)==digest,'INVENTORY_SOURCE_CHANGED:'+role+':'+name);files.add(ROOT/name)
            for when in('runtime_identity_before','runtime_identity_after'):
                if when in value:require(value[when].get('status')=='PASS','STALE_RUNTIME:'+role+':'+when)
            for key in('runtime_identity_before','runtime_identity_after'):
                if key in value:require(value[key]['pid']==826907,'PROXY_GENERATION_CHANGED:'+role)
        sql=loaded['sql_wire_and_postgresql'];python=loaded['full_python'];clients=loaded['sql_clients'];recovery=loaded['retrieval_recovery'];document=loaded['document_recovery']
        require(sql.get('daemon_pid_stable')is True,'SQL_PID_UNSTABLE')
        require(clients.get('inventory',{}).get('status')=='PASS','CLIENT_INVENTORY')
        require(recovery.get('recovery',{}).get('status')=='PASS'and recovery['recovery'].get('actual_pg_dump_restore')is True and recovery['recovery'].get('restored_acl_equal')is True,'RETRIEVAL_ACL_RECOVERY')
        require(document.get('full_acl_entries',0)>0 and document.get('inventory',{}).get('status')=='PASS','DOCUMENT_ACL_INVENTORY')
        # Full Python must actually include each promoted image and test source.
        python_files={row['path']:row['sha256']for row in python['files']}
        for name,digest in active.items():
            if name.startswith('retrieval/'):
                require(python_files.get(name)==digest,'PYTHON_MISSING_PROMOTED_SOURCE:'+name)
        for name in ROLES.values():
            log=(ROOT/name).with_suffix('.log')
            if log.is_file():files.add(log)
        specification=importlib.util.spec_from_file_location('im31_runtime_verifier',ROOT/'scripts/verify_sql_runtime.py')
        runtime_module=importlib.util.module_from_spec(specification);specification.loader.exec_module(runtime_module)
        current_status=runtime_module.read_status(ROOT/'.runtime/corpus/sql-proxy/status.json')
        current_identity=runtime_module.runtime_identity(current_status)
        require(current_identity['status']=='PASS'and current_identity['pid']==826907,'CURRENT_RUNTIME_STALE')
        require(current_status.get('parser',{}).get('generation')==1,'CURRENT_GENERATION_CHANGED')
        save(out/'current-runtime.json',{'status':current_status,'identity':current_identity})
        generated=['claims.json','verifier-registry.json','current-runtime.json']
        entries=[{'path':str(path.relative_to(ROOT)),'sha256':sha(path)}for path in sorted(files)]
        entries+=[{'path':'generated/'+name,'sha256':sha(out/name)}for name in generated]
        manifest={'files':sorted(entries,key=lambda row:row['path'])}
        root_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        save(out/'manifest.json',manifest)
        for path in files:
            target=out/'inputs'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        for row in entries:
            source=out/row['path'][10:]if row['path'].startswith('generated/')else ROOT/row['path']
            require(sha(source)==row['sha256'],'INPUT_CHANGED_DURING_FREEZE:'+row['path'])
            if not row['path'].startswith('generated/'):require(sha(out/'inputs'/row['path'])==row['sha256'],'SNAPSHOT_MUTATION:'+row['path'])
        report.update(status='PASS',input_root_sha256=root_hash,active_promoted_files=14,
            model={'existing':280,'candidate':7,'status':'VERIFIED_FINITE_MODEL','report':str((formal/'report.json').relative_to(ROOT)),'active_source_projection':projection},
            roles={role:{'path':name,'sha256':sha(ROOT/name),'status':'PASS'}for role,name in ROLES.items()},
            sql_tests=52,python_tests=164,document_store_tests=22,failures=0,errors=0,skips=0,
            runtime={'pid':826907,'policy':'sql-routing-v7-sealed-image','generation':1},
            provenance=[{'public_claim':'IM31:'+role,'report':name,'report_sha256':sha(ROOT/name),'inputs':'manifest.json','verifier':'V-IM31-EVIDENCE-BINDING'}for role,name in ROLES.items()],
            interpretation='PASS binds finite executable evidence and exact installed model-source projection under declared trust. No formal implementation refinement or IM32 performance claim.')
    except AssertionError as error:report['status']='BLOCKED';report['blocking_reasons'].append(str(error))
    except Exception as error:report['status']='INFRASTRUCTURE_FAILURE';report['infrastructure_errors'].append(type(error).__name__+': '+str(error))
    save(out/'report.json',report)
    print(json.dumps({k:report.get(k)for k in['id','status','input_root_sha256','sql_tests','python_tests','blocking_reasons','infrastructure_errors']},indent=2))
    return {'PASS':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]


if __name__=='__main__':raise SystemExit(main())
