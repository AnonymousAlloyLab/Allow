#!/usr/bin/env python3
"""Bind completed finite image checks and measurement; keep failed product target open."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def require(condition,reason):
    if not condition:raise AssertionError(reason)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def benchmark(path,producer):
    """Recompute declared statistics and target status without changing the threshold."""
    report=json.loads(path.read_text())
    require(sha(producer)==report['verifier_sha256'],'BENCHMARK_VERIFIER_CHANGED:'+str(path))
    require(report['warmups']==100 and report['events']==1000,'BENCHMARK_COUNTS:'+str(path))
    samples=report['samples_ms'];require(len(samples)==1000 and all(type(x)in(int,float)and math.isfinite(x)and x>=0 for x in samples),'SAMPLES_INVALID')
    require(report['failures']==[] and report['source_unchanged']is True,'INCOMPLETE_OR_INVALID_REQUESTS')
    require(report['target_p95_ms']==300,'ORIGINAL_TARGET_CHANGED')
    ordered=sorted(samples)
    for key,q in [('p50_ms',.5),('p95_ms',.95),('p99_ms',.99)]:
        require(report[key]==ordered[math.ceil(len(samples)*q)-1],'PERCENTILE_MISMATCH:'+key)
    require(report['status']==('PASS'if report['p95_ms']<300 else'FAIL'),'TARGET_STATUS_MISSTATED')
    require(report['identity_checks']==[{'completed_events':event,'unchanged':True}for event in range(100,1101,100)],'INCOMPLETE_CHECKPOINTS')
    progress=json.loads(path.with_name('server-performance-progress.json').read_text())
    require(progress['completed_events']==1100 and progress['measured_events']==1000 and progress['samples_ms']==samples and progress['failures']==[],'INCOMPLETE_PROGRESS')
    require(progress['input_root_sha256']==report['input_root_sha256']and progress['verifier_sha256']==report['verifier_sha256'],'PROGRESS_IDENTITY_MISMATCH')
    return report


def main():
    require(len(sys.argv)==2 and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sys.argv[1]),'INVALID_RUN_ID')
    out=HERE/'completion-runs'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
    result={'status':'UNSET','classification':'FINITE_SQL_IMAGE_OBLIGATIONS_NOT_PRODUCT_LATENCY_CLOSURE',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'blocking_reasons':[],'infrastructure_errors':[],
        'product_latency':{'status':'UNSET','original_target_p95_ms':300,'gate':'OPEN'}}
    try:
        plan_path=HERE/'runtime-test-plan.json';plan=json.loads(plan_path.read_text())
        reviews=json.loads((HERE/'review-input-pins.json').read_text())
        pinned={row['path']:row['sha256']for row in reviews['files']}
        require(sha(plan_path)==pinned[str(plan_path.relative_to(ROOT))],'FROZEN_PLAN_CHANGED')
        row=next(row for row in plan['tests']if row['id']=='IM32')
        require(row['pass_condition']=='complete baseline and candidate read ownedIds report failures samplecounts inputhashes','IM32_PREDICATE_CHANGED')
        criteria={'IM32':row,'target_handling':'Retain report status from original p95<300ms predicate; complete measurement never means target acceptance',
            'IM01_IM30_IM33_IM56':'All54 original unit IDs present exactly once as ok in the current full164-test run',
            'IM31':'Existing exact current-input integration binding passes; no unresolved runtime source inventories',
            'scope':'Frozen56 SQL-image obligations; original product latency300ms gate remains independent and binding',
            'trusted':['Registered benchmark/test verifiers and runtime instrumentation','Python/SHA256','OS/kernel/processes/PostgreSQL/hardware'],
            'excluded':['Universal implementation refinement','Exclusive-host or portable performance','Product completion when target fails']}
        save(out/'claims.json',criteria)
        save(out/'verifier-registry.json',{'id':'V-SQL-IMAGE-COMPLETION','sha256':sha(__file__),'exit_codes':{'PASS':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}})
        base=ROOT/'gates/document/server-benchmark-runs/rev6-stable-v1'
        candidate=ROOT/'gates/document/server-benchmark-runs/sealed-v1'
        baseline=benchmark(base/'server-performance.json',base/'verifier.py')
        measured=benchmark(candidate/'server-performance.json',candidate/'verifier.py')
        compare=['warmups','events','node_count','shared_fixture_sha256','fixture_source_sha256','method','target_p95_ms','verifier_sha256','reference_host']
        require(all(baseline[key]==measured[key]for key in compare),'BENCHMARK_COMPARISON_CONTEXT_CHANGED')
        producer=module('image_completion_benchmark',ROOT/'scripts/benchmark_documents.py')
        current_files,current_root=producer.server_fingerprint()
        require(current_files==measured['source_sha256']and current_root==measured['input_root_sha256'],'CANDIDATE_BENCHMARK_CURRENT_INVENTORY_CHANGED')
        require(sha(ROOT/'scripts/benchmark_documents.py')==measured['verifier_sha256'],'CURRENT_BENCHMARK_VERIFIER_CHANGED')
        profile_path=ROOT/'gates/document/persistence-profile-sealed.json';profile=json.loads(profile_path.read_text())
        require(profile['status']=='PASS'and profile['source_unchanged']is True and profile['fixture_nodes']==500,'PROFILE_FAILED')
        require(profile['runtime_identity']['status']=='PASS','PROFILE_RUNTIME_STALE')
        require(set(profile['samples_ms'])=={'read','ownedIds'}and all(len(values)==3 and all(type(value)in(int,float)and math.isfinite(value)and value>=0 for value in values)for values in profile['samples_ms'].values()),'PROFILE_INCOMPLETE')
        profile_producer=ROOT/'scripts/profile_document_persistence.py'
        require(sha(profile_producer)==profile['verifier_sha256'],'PROFILE_VERIFIER_CHANGED')
        smoke=module('image_completion_smoke',ROOT/'scripts/smoke_documents.py')
        profile_files,profile_root=smoke.fingerprint()
        require(profile_files==profile['source_sha256']and profile_root==profile['input_root_sha256'],'PROFILE_CURRENT_INVENTORY_CHANGED')
        integration=HERE/'integration-runs/im31-final-v3'
        im31=json.loads((integration/'report.json').read_text());require(im31['status']=='PASS','IM31_UNRESOLVED')
        im31_manifest=json.loads((integration/'manifest.json').read_text())
        for entry in im31_manifest['files']:
            original=integration/entry['path'][10:]if entry['path'].startswith('generated/')else ROOT/entry['path']
            require(sha(original)==entry['sha256'],'IM31_INPUT_CHANGED:'+entry['path'])
            if not entry['path'].startswith('generated/'):
                require(sha(integration/'inputs'/entry['path'])==entry['sha256'],'IM31_SNAPSHOT_CHANGED')
        # Recompute complete inventories again to detect extras since IM31 binding.
        full=module('image_completion_full',ROOT/'scripts/verify_corpus_runtime.py')
        full_report=json.loads((ROOT/'gates/document/inherited-runtime-tests.json').read_text())
        files,root=full.fingerprint();require(files==full_report['files']and root==full_report['input_root_sha256'],'FULL_PYTHON_CURRENT_INVENTORY_CHANGED')
        sql=module('image_completion_sql',ROOT/'scripts/verify_sql_runtime.py')
        sql_report=json.loads((ROOT/'gates/sql/runtime-tests.json').read_text())
        sql_files,sql_root=sql.fingerprint();require(sql_files==sql_report['files']and sql_root==sql_report['input_root_sha256'],'SQL_CURRENT_INVENTORY_CHANGED')
        clients=module('image_completion_clients',ROOT/'scripts/verify_sql_clients.py')
        require(clients.fingerprint()==json.loads((ROOT/'gates/sql/client-coverage.json').read_text())['input_sha256_before'],'CLIENT_CURRENT_INVENTORY_CHANGED')
        raw_log=(ROOT/'gates/document/inherited-runtime-tests.log').read_text()
        identifiers=re.findall(r'(?m)^test_(IM[0-9]{2})_.*\.\.\. ok$',raw_log)
        required={entry['id']for entry in plan['tests']} - {'IM31','IM32'}
        require(len(identifiers)==54 and len(set(identifiers))==54 and set(identifiers)==required,'ORIGINAL_UNIT_OBLIGATIONS_UNRESOLVED')
        state=sql.read_status(ROOT/'.runtime/corpus/sql-proxy/status.json');identity=sql.runtime_identity(state)
        require(identity['status']=='PASS'and state.get('parser',{}).get('policy')=='sql-routing-v7-sealed-image','CURRENT_RUNTIME_STALE')
        promotion=json.loads((HERE/'promotion.json').read_text())
        for name,digest in promotion['active_files'].items():require(sha(ROOT/name)==digest,'PROMOTED_INPUT_CHANGED:'+name)
        memory_path=ROOT/'.runtime/sql-image-stage/resource-probe.json'
        memory=json.loads(memory_path.read_text())
        require(memory['memfd_backing_bytes']==136492600 and '1073741824'in memory['parser_limits'],
                'MEMORY_OR_CHILD_AS_REPORT_MISMATCH')
        require(all(key in memory['proxy_fixture_rollup_bytes']for key in('Rss','Pss','Pss_Shmem')),
                'MEMORY_ACCOUNTING_INCOMPLETE')
        live_memory={}
        for line in (Path('/proc')/str(identity['pid'])/'smaps_rollup').read_text().splitlines():
            parts=line.split()
            if len(parts)==3 and parts[1].isdigit()and parts[2]=='kB':live_memory[parts[0].rstrip(':')]=int(parts[1])*1024
        save(out/'current-memory.json',{'scope':'point-in-time active proxy RSS/PSS versus separate immutable backing size; no aggregate cap claim',
            'proxy_pid':identity['pid'],'proxy_rollup_bytes':live_memory,'known_pinned_memfd_backing_bytes':136492600,
            'child_rlimit_as_bytes':1073741824,'child_measurement_artifact':str(memory_path.relative_to(ROOT)),
            'note':'Unmapped memfd backing pages are additional system shmem, not all represented in proxy RSS. Child AS is independent of parent/system backing.'})
        required_files={memory_path,Path(__file__),plan_path,HERE/'review-input-pins.json',HERE/'contract.json',HERE/'contract.md',HERE/'promotion.json',
            HERE/'implementation/integration-obligations.json',integration/'report.json',integration/'manifest.json',profile_path,profile_producer,
            ROOT/'scripts/benchmark_documents.py',ROOT/'gates/document/inherited-runtime-tests.json',ROOT/'gates/document/inherited-runtime-tests.log',ROOT/'gates/sql/runtime-tests.json'}
        required_files|={ROOT/name for name in promotion['active_files']}
        required_files|={path for folder in(base,candidate)for path in folder.iterdir()if path.is_file()}
        required_files|={ROOT/name for name in current_files}|{ROOT/name for name in profile_files}
        required_files|={ROOT/entry['path']for entry in files}
        save(out/'current-runtime.json',{'published':state,'identity':identity})
        manifest_rows=[{'path':str(path.relative_to(ROOT)),'sha256':sha(path)}for path in sorted(required_files)]
        manifest_rows += [{'path':'generated/'+name,'sha256':sha(out/name)}for name in['claims.json','verifier-registry.json','current-runtime.json','current-memory.json']]
        manifest={'files':sorted(manifest_rows,key=lambda row:row['path'])}
        input_root=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        save(out/'manifest.json',manifest)
        for path in required_files:
            target=out/'inputs'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        for entry in manifest_rows:
            original=out/entry['path'][10:]if entry['path'].startswith('generated/')else ROOT/entry['path']
            require(sha(original)==entry['sha256'],'INPUT_MUTATION:'+entry['path'])
            if not entry['path'].startswith('generated/'):require(sha(out/'inputs'/entry['path'])==entry['sha256'],'SNAPSHOT_MUTATION:'+entry['path'])
        matrix=[{'id':entry['id'],'status':'PASS','evidence':'full Python164-test log'if entry['id']not in{'IM31','IM32'}else('im31-final-v3 current integration report'if entry['id']=='IM31'else'completed100+1000 benchmark pair and actual3+3 CLI profile'),'scope':'Finite registered predicate only'}for entry in plan['tests']]
        result.update(status='PASS',input_root_sha256=input_root,obligations={'total':56,'passed':56,'unresolved':0},matrix=matrix,
            IM31={'status':'PASS','report':str((integration/'report.json').relative_to(ROOT))},
            IM32={'status':'PASS','classification':'COMPLETE_MEASUREMENT_NOT_LATENCY_TARGET_ACCEPTANCE','warmups_per_run':100,'measured_per_run':1000,'request_failures':0,'profile_samples_per_operation':3},
            benchmark={'baseline_p95_ms':baseline['p95_ms'],'candidate_p50_ms':measured['p50_ms'],'candidate_p95_ms':measured['p95_ms'],'candidate_p99_ms':measured['p99_ms'],
              'p95_reduction_percent':100*(1-measured['p95_ms']/baseline['p95_ms']),'same_verifier_fixture_counts_method_host':True,'shared_host_only':True},
            product_latency={'status':measured['status'],'original_target_p95_ms':300,'measured_p95_ms':measured['p95_ms'],'gate':'OPEN'if measured['status']=='FAIL'else'PASSED'},
            runtime={'policy':'sql-routing-v7-sealed-image','pid':identity['pid'],'generation':state['parser']['generation']},
            memory={'pinned_backing_bytes':136492600,'proxy_rss_bytes':live_memory['Rss'],'proxy_pss_bytes':live_memory['Pss'],'child_rlimit_as_bytes':1073741824,'artifact':'current-memory.json'},
            interpretation='PASS closes only the original56 finite SQL-image obligations under declared trust. The original product300ms target remains FAIL and its gate OPEN. No universal runtime refinement or complete product claim.')
    except AssertionError as error:result['status']='BLOCKED';result['blocking_reasons'].append(str(error))
    except Exception as error:result['status']='INFRASTRUCTURE_FAILURE';result['infrastructure_errors'].append(type(error).__name__+': '+str(error))
    save(out/'report.json',result)
    print(json.dumps({key:result.get(key)for key in['status','input_root_sha256','obligations','IM32','product_latency','blocking_reasons','infrastructure_errors']},indent=2))
    return {'PASS':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[result['status']]


if __name__=='__main__':raise SystemExit(main())
