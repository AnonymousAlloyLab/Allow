#!/usr/bin/env python3
"""Bind executed document evidence while keeping original product gates explicit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from record_implementation import inventory, save, unit_suites
from record_retrieval import sources

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'gates/document'


def sha(path):
    """Bind exact public bytes without including private runtime data."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    """Require an actual machine-readable result; missing evidence never passes."""
    return json.loads((ROOT/path).read_text())


def current(files):
    """Require the execution-time inputs relevant to each finite test to remain unchanged."""
    assert files, 'Missing input identity'
    rows = files.items() if isinstance(files, dict) else ((row['path'], row['sha256']) for row in files)
    for path, expected in rows:
        assert sha(ROOT/path) == expected, 'Stale evidence input: '+path


def formal(base, count, activation=None, context_activation=None):
    """Check the exact frozen snapshot and installed formal and contract inputs."""
    result = json.loads((base/'report.json').read_text())
    assert result['status'] == 'VERIFIED' and result['claims']['total'] == count
    assert result['claims']['passed'] == count and result['claims']['unresolved'] == 0
    determinism = result['determinism']
    assert len(result['builds']) == 2 and (determinism == 'PASS' or isinstance(determinism, dict) and determinism.get('status') == 'PASS')
    manifest = json.loads((base/'manifest.json').read_text())
    assert manifest['schema_version'] == '1.0' and manifest['files']
    encoded = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    assert hashlib.sha256(encoded).hexdigest() == result['input_root_hash']
    for row in manifest['files']:
        path = (base/row['path'].removeprefix('generated/') if row['path'].startswith('generated/')
                else base/'inputs'/row['path'])
        assert sha(path) == row['sha256'], 'Formal snapshot changed: '+row['path']
        if row['path'].startswith(('formal/', 'spec/')) and row['path'] != 'formal/Allow.lean':
            assert sha(ROOT/row['path']) == row['sha256'], 'Active formal/contract differs: '+row['path']
    aggregate = (base/'inputs/formal/Allow.lean').read_bytes()
    suffix = {280: b'\nimport Allow.PartialTypes\n', 287: b'\nimport Allow.ImmutableImageCandidate\n', 309: b'\nimport Allow.ValidationContextCandidate\n'}[count]
    assert (ROOT/'formal/Allow.lean').read_bytes() == aggregate + suffix
    assert sha(ROOT/'formal/Allow/PartialTypes.lean') == sha(base/'inputs/gates/document/partial-types-candidate/PartialTypes.lean') if count == 280 else True
    if count == 287:
        assert activation, '287 is candidate-only without explicit promotion evidence'
        receipt = json.loads(activation.read_text())
        assert receipt['status'] == 'PROMOTED' and receipt['formal_report_sha256'] == sha(base/'report.json')
        assert receipt['active_files'] and receipt['sql_policy'] == 'sql-routing-v7-sealed-image'
        current(receipt['active_files'])
        assert 'formal/Allow/ImmutableImageCandidate.lean' in receipt['active_files']
        assert sha(ROOT/'formal/Allow/ImmutableImageCandidate.lean') == sha(base/'inputs/gates/sql/immutable-image-candidate/ImmutableImage.lean')
    if count == 309:
        assert context_activation, '309 requires formal activation evidence'
        receipt = json.loads(context_activation.read_text())
        assert receipt['status'] == 'FORMAL_AND_CONTRACT_INSTALLED_BEFORE_PRODUCTION_CHANGES'
        assert receipt['formal_report_sha256'] == sha(base/'report.json')
        assert receipt['input_root_sha256'] == result['input_root_hash']
        required = {'formal/Allow.lean', 'formal/Allow/ValidationContextCandidate.lean',
                    'spec/document-validation-context.json'}
        assert set(receipt['active_files']) == required
        current(receipt['active_files'])
        assert sha(ROOT/'formal/Allow/ValidationContextCandidate.lean') == sha(base/'inputs/gates/document/validation-context-candidate/ValidationContext.lean')
        assert sha(ROOT/'spec/document-validation-context.json') == sha(base/'inputs/gates/document/validation-context-candidate/contract.json')
    return result


def bound_log(path, manifest, marker, prefixes):
    """Bind a separately executed log to its captured source manifest and content."""
    meta = json.loads(manifest.read_text())
    assert meta['log_sha256'] == sha(path) and meta['source_sha256']
    current(meta['source_sha256'])
    for prefix in prefixes:
        assert any(name.startswith(prefix) for name in meta['source_sha256']), 'Missing source scope: '+prefix
    text = path.read_text()
    assert marker in text, 'Missing successful completion marker'
    return text


def browser(run_id):
    """Require a completed auditable warm series for this exact UI and harness."""
    assert re.fullmatch(r'[A-Za-z0-9_-]+', run_id)
    base = OUT/'browser-benchmark-runs'/run_id
    report = json.loads((base/'report.json').read_text())
    assert report['status'] in ('PASS', 'FAIL')
    assert report['measured_events'] == 1000 and report['warmup_events'] == 100 and report['nodes'] == 500
    assert report['source_unchanged'] and report['static_restored']
    sources = json.loads((base/'source-manifest.json').read_text())
    assert sources['input_root_sha256'] == report['input_root_sha256']
    assert any(k.startswith('frontend/src/') for k in sources['source_sha256'])
    current(sources['source_sha256'])
    harness = json.loads((base/'harness-manifest.json').read_text())
    assert any(k.startswith('frontend/bench/') for k in harness)
    current(harness)
    evidence = report['evidence_sha256']
    assert evidence and report['verifier_sha256'] == sha(ROOT/'scripts/verify_browser_benchmark.py')
    for name, expected in evidence.items():
        rel = Path(name)
        assert not rel.is_absolute() and '..' not in rel.parts
        assert sha(base/rel) == expected, 'Browser evidence changed: '+name
    from verify_browser_benchmark import verify_run
    raw, ordered = verify_run(base)
    assert report['p95_ms'] == ordered[949]
    assert report['status'] == ('PASS' if ordered[949] < 50 else 'FAIL')
    return report


def reports():
    """Require actual finite runtime outcomes without upgrading headless or failed latency evidence."""
    paths = {
        'http': ('gates/document/http-smoke.json', 'source_sha256'),
        'restart': ('gates/document/restart-report.json', 'source_sha256'),
        'store': ('db/document/runtime-evidence.json', 'source_sha256'),
        'recovery': ('gates/document/document-recovery-report.json', 'input_sha256_before'),
        'null_start': ('gates/document/store-null-start-recovery-report.json', 'input_sha256'),
        'python': ('gates/document/inherited-runtime-tests.json', 'files'),
        'retrieval_http': ('gates/retrieval/http-smoke.json', 'input_files'),
        'sql_inventory': ('gates/document/sql-client-inventory.json', 'input_sha256')}
    results = {}
    for label, (path, key) in paths.items():
        result = read(path)
        assert result['status'] == 'PASS', path
        current(result[key])
        results[label] = result
    results['performance'] = read('gates/document/server-performance.json')
    current(results['performance']['source_sha256'])
    assert results['performance']['events'] == 1000 and results['performance']['warmups'] == 100
    assert results['performance']['source_unchanged'] and not results['performance']['failures']
    results['headless'] = read('gates/document/headless-preview-performance.json')
    current(results['headless']['source_hashes'])
    assert not results['headless']['typed_fixture_inventory']['gaps']
    assert results['headless']['fixture']['expression_nodes'] == 500
    return results, [value[0] for value in paths.values()]


def gate_inventory(performance, count):
    """Keep inherited milestone dependencies and external acceptance separate from local tests."""
    return {
        'G0': {'state':'FINITE_MODEL_VERIFIED','propositions':count,'clean_builds':2},
        'G1': {'state':'LOCAL_TECHNICAL_CHECKS_PASSED_RIGHTS_OPEN',
               'remaining':['Dependency redistribution and license reconciliation']},
        'G2': {'state':'IMPLEMENTATION_TESTED_BROWSER_ACCEPTANCE_INCOMPLETE',
               'tested':['23 typed constructors and46 shared Java/TypeScript cases','Durable commits, exact retries and history',
                         'Actual process restart and full-ACL database recovery'],
               'remaining':['Manual browser/pointer/keyboard and named assistive-technology acceptance',
                            'Universal implementation refinement is not claimed']},
        'G3': {'state':'IMPLEMENTATION_TESTED_ACCEPTANCE_OPEN',
               'tested':['Exact Unicode/CRLF source and verified occurrences','BLOCK/TEXT_ONLY transitions and historical evidence',
                         '500-node ordered associative reconstruction under actual sandbox'],
               'remaining':['Cold browser preview series and full browser interaction/manual accessibility acceptance',
                            'Authoritative diagnostic latency target remains '+performance['status']],
               'authoritative_latency_target':performance['status']},
        'G4': {'state':'BOUNDED_SOLVER_AND_PAIRED_POOLS_TESTED_DEPENDENCIES_OPEN',
               'remaining':['Inherited product acceptance']},
        'G5': {'state':'LOCAL_LEARNED_RETRIEVAL_AND_RECOVERY_TESTED_DEPENDENCIES_OPEN',
               'remaining':['Inherited product acceptance']},
        'G6': {'state':'NO_GO','remaining':['Dependency/dataset commercial rights','Accessibility/performance acceptance',
                                         'Consenting customer task pilot and support economics']}}


def main():
    """Record current local implementation evidence without claiming every original gate closed."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-build-log', type=Path, required=True)
    parser.add_argument('--full-build-manifest', type=Path, required=True)
    parser.add_argument('--backend-build-log', type=Path, required=True)
    parser.add_argument('--backend-build-manifest', type=Path, required=True)
    parser.add_argument('--frontend-test-log', type=Path, required=True)
    parser.add_argument('--frontend-test-manifest', type=Path, required=True)
    parser.add_argument('--style-log', type=Path, required=True)
    parser.add_argument('--style-manifest', type=Path, required=True)
    parser.add_argument('--browser-run-id', required=True)
    parser.add_argument('--formal-count', type=int, choices=(280, 287, 309), default=280)
    parser.add_argument('--sql-promotion-receipt', type=Path)
    parser.add_argument('--context-formal-activation', type=Path)
    parser.add_argument('--context-evidence', type=Path, action='append', default=[])
    args = parser.parse_args()
    log = bound_log(args.full_build_log, args.full_build_manifest, 'Local build and tests passed.', ('backend/', 'frontend/', 'scripts/'))
    assert 'BUILD SUCCESS' in log and '0 Checkstyle violations' in log
    backend = bound_log(args.backend_build_log, args.backend_build_manifest, 'BUILD SUCCESS', ('backend/',))
    frontend_log = bound_log(args.frontend_test_log, args.frontend_test_manifest, 'Tests', ('frontend/src/',))
    style_log = bound_log(args.style_log, args.style_manifest, 'Style checker self-tests:', ('backend/', 'frontend/', 'scripts/'))
    frontend = re.search(r'Tests\s+(\d+) passed',frontend_log)
    style = re.search(r'Style checker self-tests: (\d+) JS/TS cases and (\d+) Java cases passed',style_log)
    assert frontend and style
    bases = {280: OUT/'partial-types-candidate/formal-runs/final-280-v1',
             287: ROOT/'gates/sql/immutable-image-candidate/formal-runs/final-287-v2',
             309: OUT/'validation-context-candidate/formal-runs/final-309-v1'}
    base = bases[args.formal_count]
    proof = formal(base, args.formal_count, args.sql_promotion_receipt, args.context_formal_activation)
    warm = browser(args.browser_run_id)
    runtime, evidence_paths = reports()
    suites = unit_suites()
    assert all(not int(row.get('failures',0)) and not int(row.get('errors',0)) for row in suites)
    save(OUT/'java-tests.json',suites)
    shutil.copyfile(args.full_build_log,OUT/'build.log')
    files = sources()
    save(OUT/'implementation-manifest.json',{'files':files})
    evidence_paths += ['gates/document/server-performance.json','gates/document/headless-preview-performance.json',
                      'gates/document/build.log','gates/document/java-tests.json',
                      str((base/'report.json').relative_to(ROOT)),
                      'gates/document/associativity-amendment/council.json','reviews/document-assoc-runtime-astra-1.json']
    browser_base = OUT/'browser-benchmark-runs'/args.browser_run_id
    evidence_paths += [str((browser_base/name).relative_to(ROOT)) for name in
                       ('report.json', 'run-registration.json', 'source-manifest.json',
                        'harness-manifest.json', 'build-evidence/asset-manifest.json',
                        'registered-verifier.py', 'protocol.json')]
    evidence_paths += ['scripts/verify_browser_benchmark.py',
                       'gates/document/browser-benchmark-candidate/protocol.json']
    evidence_paths += [str(path.resolve().relative_to(ROOT)) for path in
                       (args.full_build_log, args.full_build_manifest, args.backend_build_log,
                        args.backend_build_manifest, args.frontend_test_log, args.frontend_test_manifest,
                        args.style_log, args.style_manifest)]
    if args.sql_promotion_receipt:
        evidence_paths.append(str(args.sql_promotion_receipt.resolve().relative_to(ROOT)))
    if args.context_formal_activation:
        evidence_paths.append(str(args.context_formal_activation.resolve().relative_to(ROOT)))
    if args.formal_count == 309:
        evidence_paths += ['gates/document/validation-context-candidate/'+name for name in
                           ('contract.json', 'runtime-test-plan.json', 'review-input-pins.json',
                            'closure-runner-config.json', 'verify_model_closure.py')]
        evidence_paths += ['reviews/validation-context-'+seat+'.json' for seat in
                           ('terra-1', 'terra-2', 'sol-1', 'sol-2', 'astra-1', 'astra-2')]
    evidence_paths += [str(path.resolve().relative_to(ROOT)) for path in args.context_evidence]
    evidence_paths = list(dict.fromkeys(evidence_paths))
    result = {'status':'LOCAL_DOCUMENT_IMPLEMENTATION_TESTED_WITH_OPEN_PRODUCT_GATES',
              'classification':'FINITE_EXECUTED_IMPLEMENTATION_TESTS_NOT_FORMAL_REFINEMENT',
              'recorded_utc':datetime.now(timezone.utc).isoformat(),
              'source_files':len(files),'source_root_sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'evidence':inventory([ROOT/path for path in evidence_paths]),
              'checks':{'formal_model_propositions':args.formal_count,'clean_formal_builds':2,
                        'backend_tests':sum(int(row['tests']) for row in suites),'frontend_tests':int(frontend[1]),
                        'shared_java_typescript_cases':46,'document_store_tests':runtime['store']['tests'],
                        'all_retrieval_document_python_tests':runtime['python']['tests'],
                        'style_js_ts_fixtures':int(style[1]),'style_java_fixtures':int(style[2]),
                        'actual_http':'PASS','server_crash_restart':'PASS','full_acl_database_restore':'PASS',
                        'sql_client_inventory':'PASS','retrieval_http':'PASS'},
              'latency':{key:runtime['performance'][key] for key in ['status','events','p50_ms','p95_ms','p99_ms','target_p95_ms']},
              'original_gates':gate_inventory(runtime['performance'], args.formal_count),
              'browser_acceptance':'INCOMPLETE',
              'browser_warm':{'run_id':args.browser_run_id,'status':warm['status'],'p95_ms':warm['p95_ms']},
              'browser_cold_and_named_assistive_technology':'NOT_ESTABLISHED',
              'trusted':proof.get('trusted',proof.get('dependencies', {}).get('trusted', []))+['Alloy/Kodkod/SAT4J','Java/TypeScript/Python adapters',
                                          'PostgreSQL/pgvector and SQLeanParser grammar CLI'],
              'excluded':['Universal runtime refinement','Full Alloy semantic normal forms','Unbounded solver validity',
                          'Browser/accessibility acceptance','Public deployment or commercial distribution'],
              'interpretation':'Proof closure certifies only frozen formal model propositions. Tests and performance measurements support their stated finite fixtures.'}
    save(OUT/'implementation-report.json',result)
    print(json.dumps({'status':result['status'],'checks':result['checks'],'latency':result['latency']},indent=2))


if __name__ == '__main__':
    main()
