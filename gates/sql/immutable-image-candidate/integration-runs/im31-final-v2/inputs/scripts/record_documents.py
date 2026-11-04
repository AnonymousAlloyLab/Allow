#!/usr/bin/env python3
"""Bind executed document evidence while keeping original product gates explicit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

from record_implementation import inventory, save, unit_suites
from record_retrieval import sources

ROOT = Path(__file__).resolve().parents[1]
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


def formal():
    """Verify retained formal evidence and the exact candidate installed after its release."""
    base = OUT/'associativity-amendment/formal-runs/final-267-v2'
    result = json.loads((base/'report.json').read_text())
    assert result['status'] == 'VERIFIED' and result['claims'] == {'total':267,'passed':267,'unresolved':0}
    assert len(result['builds']) == 2 and result['determinism'] == 'PASS'
    manifest = json.loads((base/'manifest.json').read_text())
    for row in manifest['files']:
        path = base/row['path'][10:] if row['path'].startswith('generated/') else base/'inputs'/row['path']
        assert sha(path) == row['sha256'], 'Formal snapshot changed'
    for name, original in [('Document','draft/Document.lean'), ('FieldOrder','order-amendment/FieldOrder.lean'),
                           ('Associativity','associativity-amendment/Associativity.lean')]:
        assert sha(ROOT/f'formal/Allow/{name}.lean') == sha(OUT/original)
    return result


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


def gate_inventory(performance):
    """Keep inherited milestone dependencies and external acceptance separate from local tests."""
    return {
        'G0': {'state':'FINITE_MODEL_VERIFIED','propositions':267,'clean_builds':2},
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
               'remaining':['Browser rendering latency and interaction acceptance'],
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
    parser.add_argument('--build-log', type=Path, required=True)
    args = parser.parse_args()
    log = args.build_log.read_text()
    assert 'BUILD SUCCESS' in log and 'Local build and tests passed.' in log and '0 Checkstyle violations' in log
    frontend = re.search(r'Tests\s+(\d+) passed',log)
    style = re.search(r'Style checker self-tests: (\d+) JS/TS cases and (\d+) Java cases passed',log)
    assert frontend and style
    proof = formal()
    runtime, evidence_paths = reports()
    suites = unit_suites()
    assert all(not int(row.get('failures',0)) and not int(row.get('errors',0)) for row in suites)
    save(OUT/'java-tests.json',suites)
    shutil.copyfile(args.build_log,OUT/'build.log')
    files = sources()
    save(OUT/'implementation-manifest.json',{'files':files})
    evidence_paths += ['gates/document/server-performance.json','gates/document/headless-preview-performance.json',
                      'gates/document/build.log','gates/document/java-tests.json',
                      'gates/document/associativity-amendment/formal-runs/final-267-v2/report.json',
                      'gates/document/associativity-amendment/council.json','reviews/document-assoc-runtime-astra-1.json']
    result = {'status':'LOCAL_DOCUMENT_IMPLEMENTATION_TESTED_WITH_OPEN_PRODUCT_GATES',
              'classification':'FINITE_EXECUTED_IMPLEMENTATION_TESTS_NOT_FORMAL_REFINEMENT',
              'recorded_utc':datetime.now(timezone.utc).isoformat(),
              'source_files':len(files),'source_root_sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'evidence':inventory([ROOT/path for path in evidence_paths]),
              'checks':{'formal_model_propositions':267,'clean_formal_builds':2,
                        'backend_tests':sum(int(row['tests']) for row in suites),'frontend_tests':int(frontend[1]),
                        'shared_java_typescript_cases':46,'document_store_tests':runtime['store']['tests'],
                        'all_retrieval_document_python_tests':runtime['python']['tests'],
                        'style_js_ts_fixtures':int(style[1]),'style_java_fixtures':int(style[2]),
                        'actual_http':'PASS','server_crash_restart':'PASS','full_acl_database_restore':'PASS',
                        'sql_client_inventory':'PASS','retrieval_http':'PASS'},
              'latency':{key:runtime['performance'][key] for key in ['status','events','p50_ms','p95_ms','p99_ms','target_p95_ms']},
              'original_gates':gate_inventory(runtime['performance']),
              'browser_acceptance':'INCOMPLETE_AS_EXPLICITLY_ACCEPTED_BY_USER',
              'trusted':proof['trusted']+['Alloy/Kodkod/SAT4J','Java/TypeScript/Python adapters',
                                          'PostgreSQL/pgvector and SQLeanParser grammar CLI'],
              'excluded':['Universal runtime refinement','Full Alloy semantic normal forms','Unbounded solver validity',
                          'Browser/accessibility acceptance','Public deployment or commercial distribution'],
              'interpretation':'Proof closure certifies only frozen formal model propositions. Tests and performance measurements support their stated finite fixtures.'}
    save(OUT/'implementation-report.json',result)
    print(json.dumps({'status':result['status'],'checks':result['checks'],'latency':result['latency']},indent=2))


if __name__ == '__main__':
    main()
