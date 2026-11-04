#!/usr/bin/env python3
"""Bind executed SQL/retrieval evidence without claiming implementation refinement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from record_implementation import inventory, save, unit_suites

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'gates/retrieval'


def sha(path):
    """Hash exact evidence or public source bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name):
    """Load an existing machine-readable result; absence never means success."""
    return json.loads((ROOT/name).read_text())


def current(files):
    """Require each recorded input to still match its execution-time bytes."""
    assert files, 'missing evidence inputs'
    entries = files.items() if isinstance(files, dict) else ((x['path'], x['sha256']) for x in files)
    assert all(sha(ROOT/path) == digest for path, digest in entries), 'stale evidence inputs'


def sources():
    """Inventory authored code, locks, contracts and documentation, excluding private data."""
    paths = []
    for directory in ['backend/src', 'frontend/src', 'db', 'retrieval', 'spec', 'config', 'docs', 'reviews', 'scripts']:
        paths.extend(p for p in (ROOT/directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths.extend((ROOT/'formal/Allow').glob('*.lean'))
    paths.extend(ROOT/name for name in ['README.md', '.gitignore', 'backend/pom.xml',
        'frontend/package.json', 'frontend/package-lock.json', 'formal/Allow.lean',
        'formal/lakefile.toml', 'formal/lake-manifest.json', 'formal/lean-toolchain'])
    return inventory(paths)


def checked_reports():
    """Require fresh, passed runtime reports and the unchanged final formal surface."""
    formal = read('gates/sql/formal-runs/final-rev6/report.json')
    assert formal['status'] == 'VERIFIED' and len(formal['builds']) == 2
    assert formal['builds'][0] == formal['builds'][1] and not formal['production_changes_at_freeze']
    current(read('gates/sql/formal-runs/final-rev6/manifest.json')['files'])
    reports = {}
    for name in ['gates/retrieval/runtime-tests.json', 'gates/sql/runtime-tests.json',
                 'gates/sql/client-coverage.json', 'gates/sql/recovery-report.json',
                 'gates/retrieval/http-smoke.json']:
        report = read(name)
        assert report['status'] == 'PASS' and report['source_unchanged'], name
        current(report.get('files', report.get('input_files', report.get('input_sha256_before', {}))))
        if 'tests' in report:
            assert report['tests'] > 0 and not any(report[k] for k in ['failures', 'errors', 'skipped'])
        reports[name] = report
    assert reports['gates/sql/recovery-report.json']['recovery']['restored_acl_equal']
    assert reports['gates/sql/client-coverage.json']['each_registered_tag_accepted']
    return formal, reports


def gate_inventory():
    """Retain original milestone dependencies and unresolved acceptance honestly."""
    return {
        'G0': {'state': 'FINITE_MODEL_VERIFIED', 'evidence': 'gates/sql/formal-runs/final-rev6/report.json'},
        'G1': {'state': 'TECHNICAL_CHECKS_PASSED_RIGHTS_OPEN', 'remaining': ['Dependency redistribution/license reconciliation']},
        'G2': {'state': 'OPEN', 'remaining': ['Full typed document transactions and palette', 'Durable edit idempotency/undo', 'Manual browser and assistive-technology acceptance']},
        'G3': {'state': 'OPEN', 'remaining': ['Complete occurrence maps and supported-fragment round trips', 'Full document mode transitions']},
        'G4': {'state': 'BOUNDED_SOLVER_AND_PAIRED_POOLS_TESTED_DEPENDENCIES_OPEN', 'remaining': ['Inherited complete document/provenance acceptance']},
        'G5': {'state': 'LOCAL_RETRIEVAL_AND_RECOVERY_TESTED_DEPENDENCIES_OPEN', 'remaining': ['Inherited G2/G3/G4 gates']},
        'G6': {'state': 'NO_GO', 'remaining': ['Dataset and dependency commercial rights', 'Manual accessibility acceptance', 'Customer task pilot and support economics']}}


def main():
    """Require actual successful evidence and save a finite, explicitly bounded report."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-log', type=Path, required=True)
    args = parser.parse_args()
    log = args.build_log.read_text()
    assert 'BUILD SUCCESS' in log and 'Local build and tests passed.' in log
    assert '0 Checkstyle violations' in log
    style = re.search(r'Style checker self-tests: (\d+) JS/TS cases and (\d+) Java cases passed', log)
    frontend = re.search(r'Tests\s+(\d+) passed', log)
    assert style and frontend
    formal, reports = checked_reports()
    pilot = read('retrieval/pilot-summary.json')
    assert pilot['quality_gate'] == 'PASS' and pilot['integrity_passed']
    assert reports['gates/retrieval/http-smoke.json']['model_id'] == pilot['learned_model_id']
    dependency = read('retrieval/dependency-security.json')['after']
    assert dependency['known_vulnerabilities'] == 0
    assert sha(ROOT/dependency['audit_file']) == dependency['audit_file_sha256']
    suites = unit_suites()
    save(OUTPUT/'java-tests.json', suites)
    shutil.copyfile(args.build_log, OUTPUT/'build.log')
    files = sources()
    save(OUTPUT/'implementation-manifest.json', {'files': files})
    evidence = inventory([ROOT/name for name in reports] + [OUTPUT/'build.log', OUTPUT/'java-tests.json',
        ROOT/'gates/sql/formal-report.json', ROOT/'retrieval/pilot-summary.json',
        ROOT/'retrieval/dependency-security.json', ROOT/'reviews/sql-council.json'])
    report = {'status': 'LOCAL_RETRIEVAL_AND_SQL_TESTED_WITH_OPEN_PRODUCT_GATES',
        'classification': 'FINITE_IMPLEMENTATION_TESTS_NOT_FORMAL_REFINEMENT',
        'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'source_input_root_sha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'source_files': len(files), 'evidence': evidence,
        'checks': {'formal_model_propositions': formal['model_propositions'], 'clean_formal_builds': 2,
            'backend_tests': sum(int(x['tests']) for x in suites), 'frontend_tests': int(frontend[1]),
            'style_js_ts_fixtures': int(style[1]), 'style_java_fixtures': int(style[2]),
            'retrieval_python_tests': reports['gates/retrieval/runtime-tests.json']['tests'],
            'sql_wire_and_postgresql_tests': reports['gates/sql/runtime-tests.json']['tests'],
            'full_acl_backup_restore': 'PASS', 'http_stored_vector_retrieval': 'PASS'},
        'pilot': pilot, 'original_gates': gate_inventory(),
        'trusted': formal['trusted'] + ['Alloy/Kodkod/SAT4J', 'PostgreSQL and pgvector', 'SQLean grammar CLI and pinned lexer assumptions', 'Python/Java/TypeScript adapters and local pretrained encoder'],
        'excluded': ['Universal implementation refinement', 'Complete Alloy canonical normal forms',
            'Unbounded solver soundness', 'Browser/manual accessibility acceptance', 'Commercial release clearance'],
        'interpretation': 'Proof closure applies only to the frozen Lean surface under its TCB. Runtime results are finite executed checks. Learned pilot non-regression is not broad semantic retrieval quality.'}
    save(OUTPUT/'implementation-report.json', report)
    save(ROOT/'gates/sql/implementation-report.json', {**report, 'pilot': None})
    print(json.dumps({'status': report['status'], 'checks': report['checks']}, indent=2))


if __name__ == '__main__':
    main()
