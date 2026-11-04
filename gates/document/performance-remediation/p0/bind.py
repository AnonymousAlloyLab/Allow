#!/usr/bin/env python3
"""Fresh26-obligation binding of unchanged active inputs, inherited evidence and P0 probes."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OLD = ROOT/'gates/document/validation-context-candidate/runtime-closure'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def save(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')


def require(condition,code):
    if not condition: raise AssertionError(code)


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def freeze(report_path):
    """Bind exact evidence and verifier before evaluating any26-case discharge."""
    destination = HERE/'binder-registration.json'
    require(not destination.exists(),'EXISTING_REGISTRATION')
    old = read(OLD/'registration-r3.json')
    paths = {ROOT/item['path'] for item in old['files']}
    paths |= {OLD/'registration-r3.json',OLD/'runs/final-v2/report.json',Path(__file__)}
    paths |= {Path(item['path']) for item in read(HERE/'r1/registration.json')['files']}
    paths |= {path for path in (HERE/'r1').rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    files = [{'path':str(path),'sha256':sha(path)} for path in sorted(paths)]
    registration = {'id':'V-ALLOW-P0-26-BINDER-R1','files':files,
        'input_root_sha256':hashlib.sha256(pack(files)).hexdigest(),
        'registered_at':datetime.now(timezone.utc).isoformat(),'probe_report':str(report_path.resolve()),
        'prior_report':str(OLD/'runs/final-v2/report.json'),
        'finite_claims':'Unchanged26 runtime-test obligations; execute inherited registered result/source checks and add RP01/RP02/PUBLIC-NESTING/RP03 assertions to the three literal gaps.',
        'pass_condition':'All inherited555input hashes still match; all inherited source/result assertions still pass; all4P0groups match their frozen exact assertions; no remaining required case; proof/test/benchmark reports retain original counts/status.',
        'block_condition':'Any missing/stale/failed/unbound evidence, source mutation, changed target, unresolved required case or checker assertion.',
        'trust':read(HERE/'r1/protocol.json')['trust'],
        'excluded':read(HERE/'r1/protocol.json')['excluded'],
        'builds':'Two new isolated Java probe compiles plus exact pinned inherited two309formal builds; no main-suite or Lean rerun claimed.',
        'provenance':'Each unchanged matrix row retains original evidence_refs. VC01adds RP01/RP02, VC13adds RP02/PUBLIC-NESTING, VC14adds RP03, all resolving to the preregistered P0 report and verifier. Runtime finite evidence is not universal implementation correspondence.',
        'exit_codes':{'0':'VERIFIED','1':'BLOCKED','2':'INFRASTRUCTURE_FAILURE'}}
    save(destination,registration)
    print(json.dumps({'registered':str(destination),'root':registration['input_root_sha256'],'files':len(files)}))


def verify_files(registration):
    require(hashlib.sha256(pack(registration['files'])).hexdigest() == registration['input_root_sha256'],'REGISTRATION_ROOT')
    for item in registration['files']:
        require(sha(Path(item['path'])) == item['sha256'],'INPUT_MUTATION:'+item['path'])


def inherited(verifier):
    """Reexecute the prior verifier's concrete predicates against unchanged current bytes."""
    reg = read(OLD/'registration-r3.json')
    require(hashlib.sha256(verifier.pack(reg['files'])).hexdigest() == reg['input_root_sha256'],'INHERITED_ROOT')
    for item in reg['files']:
        require(sha(ROOT/item['path']) == item['sha256'],'INHERITED_INPUT_MUTATION:'+item['path'])
    mapping = read(OLD/'case-mapping-r2.json')
    require(mapping['frozen_plan_sha256'] == sha(OLD.parent/'runtime-test-plan.json'),'INHERITED_PLAN')
    for value in mapping['records'].values():
        if value['kind'] == 'python_test': verifier.py_ok(value)
        elif value['kind'] == 'junit_test': verifier.java_ok(value)
        else: require(sha(ROOT/value['path']) == value['sha256'],'INHERITED_REPORT:'+value['path'])
    supplemental = verifier.supplemental(); latency = verifier.benchmark()
    corpus = verifier.mod('p0_corpus',ROOT/'scripts/verify_corpus_runtime.py')
    files,root = corpus.fingerprint(); value = read(ROOT/'gates/document/inherited-runtime-tests.json')
    require(files == value['files'] and root == value['input_root_sha256'] and value['tests'] == 186
            and not any(value[key] for key in ('failures','errors','skipped')),'PYTHON_INVENTORY')
    sql = verifier.mod('p0_sql',ROOT/'scripts/verify_sql_runtime.py')
    files,root = sql.fingerprint(); value = read(ROOT/'gates/sql/runtime-tests.json')
    require(files == value['files'] and root == value['input_root_sha256'] and value['tests'] == 52
            and value['status'] == 'PASS','SQL_INVENTORY')
    clients = verifier.mod('p0_clients',ROOT/'scripts/verify_sql_clients.py')
    require(clients.fingerprint() == read(ROOT/'gates/sql/client-coverage.json')['input_sha256_before'],'SQL_CLIENTS')
    state = sql.read_status(ROOT/'.runtime/corpus/sql-proxy/status.json')
    identity = sql.runtime_identity(state)
    require(identity['status'] == 'PASS' and identity['pid'] == 826907 and state['parser']['generation'] == 1,'PROXY_IDENTITY')
    return mapping,supplemental,latency,reg['input_root_sha256']


def probe(report_path):
    """Mechanically inspect every new literal boundary/fault case and its preregistration."""
    result = read(report_path); registration = read(HERE/'r1/registration.json')
    verify_files(registration)
    require(result['status'] == 'PASS' and result['inputs_unchanged']
            and result['shared_proxy_identity_unchanged'],'P0_NOT_PASS')
    require(result['input_root_sha256'] == registration['input_root_sha256']
            and result['verifier_sha256'] == sha(HERE/'r1/probe.py'),'P0_UNBOUND')
    require(result['main_test_counts'] == {'java':189,'python':186},'MAIN_COUNT_INFLATION')
    checks = result['checks']
    require(set(checks) == {'RP01','RP02','PUBLIC-NESTING','RP03'}
            and all(item['status'] == 'PASS' for item in checks.values()),'P0_GROUPS')
    sizes = checks['RP01']['evidence']['cases']
    require([item['bytes_including_newline'] for item in sizes] == [3145727,3145728,3145729],'CLI_SIZES')
    require([item['nonce_captured'] for item in sizes] == [True,True,False],'CLI_GUARD')
    nesting = checks['RP02']['evidence']['cases']
    require([item['independent_depth'] for item in nesting] == [95,96,97],'DEPTH_COUNT')
    require([item['decoded'] for item in nesting] == [True,True,False]
            and nesting[2]['decoder_reason'] == 'json_depth','DEPTH_GUARD')
    malformed = checks['RP02']['evidence']['malformed']
    require(set(malformed) == {'utf8','bom','duplicates'},'MALFORMED_CONTROLS')
    for item in sizes+nesting+list(malformed.values()):
        require(item['status'] == 'ERROR' and item['literal_cli']['reaped']
                and item['observed_cli']['reaped'] and item['observed_cli']['telemetry']
                == {'sql_connect_attempts':0,'subprocess_launches':0},'REJECTION_SIDE_EFFECT')
    java = checks['PUBLIC-NESTING']['evidence']; builds = java['builds']
    require(java['style_exit'] == 0 and java['deterministic'] and java['temporary_outputs_removed']
            and len(builds) == 2 and builds[0]['class_sha256'] == builds[1]['class_sha256']
            and builds[0]['stdout'] == builds[1]['stdout'],'CLEAN_PROBE_BUILDS')
    expected = ''.join('depth='+str(value)+' decoded='+str(value<=300).lower()
                       +' shapeRejected='+str(value<=300).lower()+'\n' for value in (95,96,97,299,300,301))
    require(builds[0]['stdout'] == expected,'PUBLIC_DEPTH_BOUNDARY')
    faults = checks['RP03']['evidence']
    require(faults['owned_fixture_database_dropped'] and len(faults['cases']) == 2,'OWNED_DB_CLEANUP')
    require([item['mode'] for item in faults['cases']] == ['service-stop','child-kill'],'FAULT_CASES')
    for item in faults['cases']:
        require(item['status'] == 'UNAVAILABLE' and not item['partial_context'] and not item['mutation_uncertainty']
                and item['proxy_reaped'] and item['context_reaped'] and item['owned_parser_shutdown_complete']
                and item['durable_unchanged'] and len(item['telemetry']['connection_attempts']) == 1
                and item['telemetry']['alternate_routes'] == 0,'FAULT_RESULT')
    killed = faults['cases'][1]['parser_child']
    require(killed['uncached'] and killed['sealed_executable'] and killed['start_ticks']
            and killed['exact_target_sha256'] == hashlib.sha256(
                b'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY').hexdigest(),'ACTUAL_PARSER_CHILD')
    require(faults['cases'][1]['isolated_counters']['rejected'] == 1,'PARSER_DENIAL_NOT_OBSERVED')
    return {'report':str(report_path.relative_to(ROOT)),'sha256':sha(report_path),
            'input_root_sha256':registration['input_root_sha256'],'groups':4,
            'new_main_suite_tests':0,'two_clean_probe_builds':True,
            'no_worker_scope':'Actual CLI failure + inherited Java failure-before-construction evidence; compositional, not new HTTP trace.'}


def execute(name):
    """Produce a fresh strict26-case result without editing any historical report."""
    folder = HERE/'binder-runs'/name; folder.mkdir(parents=True,exist_ok=False)
    result = {'status':'UNSET','classification':'FINITE_RUNTIME_EVIDENCE_NOT_FORMAL_IMPLEMENTATION_REFINEMENT',
              'blocking_reasons':[],'infrastructure_errors':[]}
    try:
        registration = read(HERE/'binder-registration.json'); verify_files(registration)
        save(folder/'registration.json',registration)
        verifier = module('p0_inherited_verifier',OLD/'verify_runtime_closure.py')
        mapping,supplemental,latency,oldroot = inherited(verifier)
        new = probe(Path(registration['probe_report']))
        prior = read(OLD/'runs/final-v2/report.json')
        require(prior['status'] == 'BLOCKED' and prior['obligations'] == {'total':26,'checked':23,'blocked':3},'PRIOR_CASE_SURFACE')
        resolved = {'VC01':['RP01','RP02'],'VC13':['RP02','PUBLIC-NESTING'],'VC14':['RP03']}
        rows = []
        for original in mapping['obligations']:
            row = dict(original)
            if row['id'] in resolved:
                row['prior_missing_cases'] = row['remaining_required_cases']
                row['remaining_required_cases'] = []
                row['evidence_refs'] = row['evidence_refs']+['p0:'+name for name in resolved[row['id']]]
                row['covered_cases'] = row['covered_cases']+[
                    read(HERE/'r1/protocol.json')['claims'][index]['pass'] for index,value in enumerate(
                        ['RP01','RP02','PUBLIC-NESTING','RP03']) if value in resolved[row['id']]]
                row['audit_status'] = 'SUPPORTED_FINITE_EVIDENCE'
            row['status'] = 'BLOCKED' if row['remaining_required_cases'] else 'CHECKED_FINITE_EVIDENCE'
            rows.append(row)
        require(len(rows) == 26 and all(row['status'] == 'CHECKED_FINITE_EVIDENCE' for row in rows),'REMAINING_CASES')
        verify_files(registration)
        result.update(status='VERIFIED',closure_id=registration['id'],input_root_sha256=registration['input_root_sha256'],
            obligations={'total':26,'checked':26,'blocked':0},matrix=rows,remaining_required_cases=[],
            inherited_evidence={'prior_status':'BLOCKED','prior_checked':23,'prior_input_root_sha256':oldroot,
                                'current_hashes_rechecked':555,'result_predicates_reexecuted':True},
            supplemental=supplemental,p0=new,product_latency=latency,trust=registration['trust'],excluded=registration['excluded'],
            material_limitations=mapping['material_limitations']+[
                'P0 parser fault observations stop at actual Python context failure. Java no-worker behavior uses inherited component tests and unchanged source ordering, not a new monolithic HTTP trace.',
                'Private Python root/key/value/list edge cap96 and public Jackson container cap300 are distinct.',
                'Probe revisions and counts do not enlarge main189Java/186Python suites or active309formal surface.'],
            builds={'new_probe_clean_builds':2,'new_probe_deterministic':True,'formal':'Inherited exact309model two-build evidence; no new formal build claimed'},
            interpretation='VERIFIED covers only the frozen finite26runtime evidence obligations under declared trust. The300ms product gate remains FAIL and P1 backend cleanup remains unresolved.')
    except AssertionError as failure:
        result.update(status='BLOCKED'); result['blocking_reasons'].append(str(failure))
    except Exception as failure:
        result.update(status='INFRASTRUCTURE_FAILURE'); result['infrastructure_errors'].append(type(failure).__name__)
    save(folder/'report.json',result)
    print(json.dumps({key:result.get(key) for key in ('status','input_root_sha256','obligations','blocking_reasons','infrastructure_errors','product_latency')},indent=2))
    return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[result['status']]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--freeze',type=Path); parser.add_argument('--execute')
    args = parser.parse_args()
    if args.freeze: freeze(args.freeze)
    elif args.execute: sys.exit(execute(args.execute))
    else: parser.error('explicit freeze or execute required')
