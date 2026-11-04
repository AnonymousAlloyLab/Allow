#!/usr/bin/env python3
"""Bind final egraph implementation evidence to exact sources without claiming refinement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from record_implementation import inventory, save, unit_suites

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'gates/egraph'


def sha(path):
    """Hash exact files, excluding launch capability state."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest():
    """Capture the finite current source set; exclude generated builds and historical snapshots."""
    paths = [ROOT / name for name in ['README.md', '.gitignore', '.cursor/rules/allow-development.mdc',
        'backend/README.md', 'backend/pom.xml', 'frontend/index.html', 'frontend/package.json',
        'frontend/package-lock.json', 'frontend/tsconfig.json', 'formal/Allow.lean', 'formal/lean-toolchain',
        'formal/lakefile.toml', 'formal/lake-manifest.json', 'gates/egraph/formal-report.json']]
    for directory in ['backend/src', 'frontend/src', 'spec', 'config', 'docs', 'reviews']:
        paths.extend(path for path in (ROOT / directory).rglob('*') if path.is_file())
    paths.extend((ROOT / 'formal/Allow').glob('*.lean'))
    paths.extend((ROOT / 'scripts').glob('*.py'))
    paths.extend((ROOT / 'scripts').glob('*.mjs'))
    return inventory(paths)


def root_review():
    """Preserve implementation findings and their regression evidence as review, not proof."""
    save(ROOT / 'reviews/egraph-runtime-root.json', {
        'classification': 'IMPLEMENTATION_REVIEW_AND_TEST_RESOLUTION_NOT_FORMAL_PROOF',
        'findings': [
            {'id': 'EG-R01', 'finding': 'Record-valued preview data changed byte order after cross-JVM generic-map reconstruction',
             'resolution': 'Alphabetical property and map serialization; strict canonical-frame equality retained',
             'tests': ['JsonWireEGraphTest.genericPreviewRoundTripKeepsCanonicalFrame', 'WorkerIntegrationTest']},
            {'id': 'EG-R02', 'finding': 'Original wire depth140 could reject valid term depth100 because arrays and objects each add nesting',
             'resolution': 'Transport depth300, with independent term/proof depth128 and byte caps retained',
             'tests': ['JsonWireEGraphTest.admittedProofDepthSurvivesTransport', 'JsonWireEGraphTest.excessiveWireNestingStillRejects']},
            {'id': 'EG-R03', 'finding': 'Registry was self-hashed but not checked against the proved catalog pin before parsing',
             'resolution': 'Exact private approved SHA-256 pin checked before parser; tampered-byte regression',
             'tests': ['RuleCatalogTest']},
            {'id': 'EG-R04', 'finding': 'Public Rewrite constructor could retain caller-owned mutable pattern nodes',
             'resolution': 'Defensive copies on constructor inputs and accessor outputs', 'tests': ['RuleCatalogTest']},
            {'id': 'EG-R05', 'finding': 'Graph preview boundary counted an omitted node, hiding truncation at49nodes',
             'resolution': 'Count only added nodes; explicit preview truncation', 'tests': ['EGraphEngineTest', 'HTTP graph preview inspection']},
            {'id': 'EG-R06', 'finding': 'Nested IFF lowering and aggregate output sizing needed limits before expansion/allocation',
             'resolution': 'Occurrence-cost guard and capped aggregate output sink with OUTPUT_LIMIT sentinel',
             'tests': ['IslandAdapterTest']}
        ],
        'related_review': 'reviews/egraph-runtime-astra-1.json',
        'remaining': ['Browser extension unavailable; no manual keyboard/drop/visual QA',
            'No Java/parser/OS refinement proof or commercial clearance'],
        'execution_authority': 'gates/egraph/implementation-report.json and its bound test evidence'})


def main():
    """Require actual successful build/HTTP evidence and unchanged formal inputs, then bind outputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-log', required=True, type=Path)
    args = parser.parse_args()
    log = args.build_log.read_text()
    assert 'BUILD SUCCESS' in log and 'Local build and tests passed.' in log
    assert '0 Checkstyle violations' in log
    style = re.search(r'Style checker self-tests: (\d+) JS/TS cases and (\d+) Java cases passed', log)
    frontend = re.search(r'Tests\s+(\d+) passed', log)
    assert style and frontend and int(style[2]) > 0
    formal = json.loads((OUTPUT / 'formal-report.json').read_text())
    frozen = json.loads((OUTPUT / 'formal-runs/supplement-r2/manifest.json').read_text())
    assert formal['status'] == 'VERIFIED' and len(formal['builds']) == 2
    assert all(sha(ROOT / item['path']) == item['sha256'] for item in frozen['files'])
    assert not formal['production_changes_at_freeze']
    smoke = json.loads((OUTPUT / 'http-smoke.json').read_text())
    assert smoke['status'] == 'PASS'
    suites = unit_suites()
    save(OUTPUT / 'java-tests.json', suites)
    shutil.copyfile(args.build_log, OUTPUT / 'build.log')
    root_review()
    files = source_manifest()
    root_hash = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    save(OUTPUT / 'implementation-manifest.json', {'files': files,
        'hashing': 'SHA-256 of sorted compact file-entry JSON array; manifest/report/evidence outputs excluded'})
    evidence = inventory([OUTPUT / name for name in ['build.log', 'java-tests.json', 'http-smoke.json',
        'formal-report.json', 'dependencies.json', 'npm-audit.json']])
    artifacts = inventory([path for path in (ROOT / 'frontend/dist').rglob('*') if path.is_file()]
        + [path for path in (ROOT / 'backend/target/classes').rglob('*') if path.is_file()])
    report = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'EGRAPH_IMPLEMENTATION_TESTED_BROWSER_ACCEPTANCE_OPEN',
        'classification': 'IMPLEMENTATION_TEST_EVIDENCE_NOT_FORMAL_REFINEMENT',
        'source_input_root_sha256': root_hash, 'source_files': len(files),
        'evidence': evidence, 'compiled_artifacts': artifacts,
        'checks': {'backend_tests': sum(int(suite['tests']) for suite in suites),
            'frontend_tests': int(frontend[1]), 'style_js_ts_fixtures': int(style[1]),
            'style_java_fixtures': int(style[2]), 'checkstyle': 'PASS', 'typescript_build': 'PASS',
            'http_integration': 'PASS', 'catalog_rules': formal['catalog_mappings'],
            'formal_model_propositions': formal['model_propositions'],
            'new_formal_propositions': formal['new_model_propositions'],
            'formal_rule_assignments': formal['finite_rule_assignments'], 'formal_clean_builds': 2,
            'formal_inputs_unchanged': True,
            'npm_audit_total': json.loads((OUTPUT / 'npm-audit.json').read_text())['metadata']['vulnerabilities']['total']},
        'implemented': ['Typed hash-consing and deterministic union-find',
            'Checked congruence rebuild and generic e-matching', '34 pinned proved-rule schemas',
            'Bounded saturation and finite positive-cost extraction',
            'Separate bounded certificate replay before semantic merges and published results',
            'Occurrence-based Alloy adapter with full nominal schemas and opaque unsupported nodes',
            'Preserved anonymous v1 structural bytes/features and visible source names',
            'Read-only multi-island UI with graph links, costs and certificate inspection/download'],
        'open_acceptance': ['Browser inventory remained empty after runtime reset; Chrome creation unavailable',
            'Manual keyboard/drag/drop/visual and assistive-technology checks not executed',
            'No universal parser-to-IR, Java/TypeScript, union-find or OS refinement proof',
            'Complete Alloy equivalence/canonical normalization is not implemented',
            'JDK runtime version remains fingerprinted rather than exact JDK binary/library bytes',
            'Dependency redistribution and dataset usage rights remain unresolved',
            'Vector persistence, corpus ingestion and LLM/RAG integration remain later stages'],
        'runtime': {'mode': 'local single-user isolated workers', 'owned_preview_after_checks': 'STOPPED'},
        'datasets_ingested': False, 'external_embedding_calls': False, 'new_runtime_dependencies': False,
        'launch_capability_recorded': False}
    save(OUTPUT / 'implementation-report.json', report)
    print(json.dumps({'status': report['status'], 'checks': report['checks'],
        'source_input_root_sha256': root_hash}, indent=2))

if __name__ == '__main__':
    main()
