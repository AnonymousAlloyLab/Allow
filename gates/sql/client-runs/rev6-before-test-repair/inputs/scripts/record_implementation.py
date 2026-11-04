#!/usr/bin/env python3
"""Bind the observed local build/test evidence to files without claiming formal refinement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'gates/g1'

def digest(path):
    """Hash exact existing bytes, never secret launch files."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    """Write readable JSON with deterministic member order."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def inventory(paths):
    """Describe a sorted finite set of local inputs without following symlinks."""
    result = []
    for path in sorted(set(paths)):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f'Nonregular input: {path}')
        result.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path)})
    return result

def unit_suites():
    """Preserve testcase names/counts, excluding environment properties from Surefire XML."""
    suites = []
    for path in sorted((ROOT / 'backend/target/surefire-reports').glob('TEST-*.xml')):
        tree = ET.parse(path).getroot()
        suite = {key: tree.attrib[key] for key in ['name', 'tests', 'failures', 'errors', 'skipped']}
        suite['testcases'] = [item.attrib['name'] for item in tree.findall('testcase')]
        suite['original_xml_sha256'] = digest(path)
        assert all(int(suite[key]) == 0 for key in ['failures', 'errors', 'skipped']), suite
        suites.append(suite)
    assert suites, 'No Surefire evidence'
    return suites

def council():
    """Bind all six requested reviewer seats and preserve each snapshot's original verdict."""
    reports = {}
    for seat in ['terra-1', 'terra-2', 'sol-1', 'sol-2', 'astra-1', 'astra-2']:
        path = ROOT / f'reviews/g1-implementation-{seat}.json'
        data = json.loads(path.read_text())
        final = data.get('final_review', data.get('final_disposition', {}))
        reports[seat] = {'requested_model': 'gpt-6-astra' if seat.startswith('astra') else
            'gpt-6.1-' + seat.split('-')[0], 'report': str(path.relative_to(ROOT)),
            'sha256': digest(path), 'initial_or_current_verdict': data['verdict'],
            'final_disposition': final}
    result = {'classification': 'ADVISORY_REVIEW_NOT_PROOF', 'seats': reports,
        'limits': 'Requested dispatch model identities recorded; provider runtime not independently attested. Reports retain reviewed snapshot hashes and disclose reviewer-authored remediation.',
        'resolution': {'strict_json_coercion': 'Fixed; HTTP and worker-protocol negative tests pass',
            'forged_drop_and_stale_cancel': 'Fixed; typed reference and deferred-response tests pass',
            'missing_canonical_fixtures': 'Six durable scope/framing/exact-byte tests pass',
            'broad_style_exclusions': 'Exact known roots only; authored nested-path fixtures pass',
            'default_java_style_fixtures': 'Pinned verified CLI required by default build; 13 cases pass',
            'jdk_binary_identity': 'Documented limitation: runtime version string, not JDK binary hashes',
            'linux_layout_and_inventory_threshold': 'Documented host-path and old 256 KiB inventory-threshold limits',
            'browser_and_commercial_gates': 'Remain open; no acceptance or clearance inferred'}}
    save(ROOT / 'reviews/g1-implementation-council.json', result)

def sources():
    """Collect authored implementation, contract, proof and review inputs, excluding secrets/vendor/builds."""
    paths = [ROOT / name for name in ['README.md', 'backend/README.md', 'backend/pom.xml',
        'frontend/index.html', 'frontend/package.json', 'frontend/package-lock.json',
        'frontend/tsconfig.json', '.cursor/rules/allow-development.mdc', '.gitignore']]
    for directory in ['backend/src', 'frontend/src', 'config', 'spec', 'docs', 'reviews']:
        paths.extend(path for path in (ROOT / directory).rglob('*') if path.is_file())
    paths.extend((ROOT / 'scripts').glob('*.py'))
    paths.extend((ROOT / 'scripts').glob('*.mjs'))
    paths.extend((ROOT / 'formal/Allow').glob('*.lean'))
    paths.extend(ROOT / name for name in ['formal/Allow.lean', 'formal/lean-toolchain',
        'formal/lakefile.toml', 'formal/lake-manifest.json', 'gates/g1/formal-report.json'])
    return inventory(paths)

def main():
    """Require successful actual evidence, then record its finite scope and unresolved gates."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-log', required=True, type=Path)
    args = parser.parse_args()
    log = args.build_log.read_text()
    assert 'BUILD SUCCESS' in log and 'Local build and tests passed.' in log
    assert '0 Checkstyle violations' in log
    style = re.search(r'Style checker self-tests: (\d+) JS/TS cases and (\d+) Java cases passed', log)
    frontend = re.search(r'Tests\s+(\d+) passed', log)
    assert style and int(style[2]) > 0 and frontend
    smoke = json.loads((OUTPUT / 'http-smoke.json').read_text())
    assert smoke['status'] == 'PASS'
    formal = json.loads((OUTPUT / 'formal-report.json').read_text())
    frozen = json.loads((OUTPUT / 'formal-runs/supplement-r4/manifest.json').read_text())
    assert all(digest(ROOT / item['path']) == item['sha256'] for item in frozen['files'])
    suites = unit_suites()
    save(OUTPUT / 'java-tests.json', suites)
    shutil.copyfile(args.build_log, OUTPUT / 'build.log')
    council()
    files = sources()
    manifest = {'files': files, 'hashing': 'SHA-256 of sorted compact JSON file-entry array; report and manifest excluded'}
    root_hash = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    save(OUTPUT / 'implementation-manifest.json', manifest)
    evidence = inventory([OUTPUT / name for name in ['build.log', 'java-tests.json', 'http-smoke.json',
        'dependencies.json', 'npm-audit.json', 'formal-report.json']])
    artifacts = inventory(list((ROOT / 'backend/target/classes').rglob('*.class'))
        + [path for path in (ROOT / 'frontend/dist').rglob('*') if path.is_file()])
    report = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'DEVELOPMENT_SLICE_TESTED_WITH_OPEN_ACCEPTANCE_GATES',
        'classification': 'IMPLEMENTATION_TEST_EVIDENCE_NOT_FORMAL_REFINEMENT',
        'source_input_root_sha256': root_hash, 'source_files': len(files), 'evidence': evidence,
        'compiled_artifacts': artifacts,
        'checks': {'backend_tests': sum(int(item['tests']) for item in suites),
            'frontend_tests': int(frontend[1]), 'style_js_ts_fixtures': int(style[1]),
            'style_java_fixtures': int(style[2]), 'checkstyle': 'PASS', 'typescript_build': 'PASS',
            'http_integration': 'PASS', 'npm_audit_total': json.loads((OUTPUT / 'npm-audit.json').read_text())['metadata']['vulnerabilities']['total'],
            'formal_model_propositions': formal['propositions'], 'formal_clean_builds': len(formal['builds']),
            'formal_sources_unchanged_since_preimplementation_freeze': True},
        'gates': {'G1_development_foundation': 'TESTED', 'G1_commercial_clearance': 'OPEN',
            'G2_initial_subset': 'IMPLEMENTED_WITH_BROWSER_ACCEPTANCE_OPEN',
            'G2_full_palette_and_roundtrip': 'NOT_IMPLEMENTED',
            'G3_live_code_and_canonical_profile': 'STRUCTURAL_SLOT_SUBSET_ONLY; FULL_GATE_OPEN',
            'G4_solver_evidence_pools': 'SINGLE_RUN_RESULTS_ONLY; POOLS_NOT_IMPLEMENTED',
            'G5_vector_corpus': 'NOT_IMPLEMENTED', 'G6_commercial_pilot': 'NOT_CLEARED'},
        'open_items': ['No browser surface: real keyboard/drop/visual QA not run',
            'No universal parser-to-slot or Java/TypeScript refinement proof',
            'Style checks cannot prove documentation meaning, single responsibility or absence of mutable object escapes',
            'JDK version is recorded; exact JDK binaries/libraries not fingerprinted',
            'Sandbox paths currently require the documented Debian/Ubuntu-style host layout',
            'Alloy/component redistribution and dataset usage rights remain unresolved',
            'No vector database, dataset ingestion, e-graph saturation, LLM or production deployment'],
        'runtime': {'mode': 'local single-user memory-only jobs', 'preview_after_checks': 'STOPPED'},
        'dataset_sources_used_in_tests': False, 'launch_capability_recorded': False}
    save(OUTPUT / 'implementation-report.json', report)
    print(json.dumps({'status': report['status'], 'checks': report['checks'], 'source_input_root_sha256': root_hash}, indent=2))

if __name__ == '__main__':
    main()
