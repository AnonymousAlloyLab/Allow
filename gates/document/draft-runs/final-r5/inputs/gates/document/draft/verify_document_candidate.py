#!/usr/bin/env python3
"""Isolated candidate formal verifier; does not authorize implementation or close G2/G3.

Run only after the draft specs and independent reviews are frozen. The caller must
supply their exact spec and wire SHA-256 values. A VERIFIED report means only that
the registered model propositions and witnesses pass the checks described below.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / 'gates/document/baseline-sql/manifest.json'
DOCUMENT = ROOT / 'gates/document/draft/Document.lean'
TYPES = ROOT / 'gates/document/draft/types.json'
SPEC = ROOT / 'spec/document-stage-draft.json'
WIRE = ROOT / 'spec/document-wire-draft.json'
UI = ROOT / 'spec/document-ui-draft.json'
ADAPTER = ROOT / 'spec/document-adapter-draft.json'
CANDIDATE = ROOT / 'gates/document/review-candidate-r5/manifest.json'
CANDIDATE_SHA256 = 'acda03535d825386234c3b8ce634159a4aaf700f7517ca7faf8163b4414baec2'
REVIEW_PATHS = [f'reviews/document-r5-{family}-{number}.json' for family in ('terra', 'sol', 'astra') for number in (1, 2)]
# These pins are deliberate: a reviewed model revision requires a new verifier review.
DOCUMENT_SHA256 = 'a9ce61793dc79676395211cd8e5d94c0e0767316755040224f63f2a1af3b3b07'
TYPES_SHA256 = 'fd0a31b549a8c20d079b960f68b306603b66aaed3facfd2e4a4bc302ea336109'
BASELINE_SHA256 = 'bdb2ac5172be46422cc386ea35ca0b6429e7576c428d54f197afe841f6e6665d'
INHERITED = ['closure/theorem-types.json', 'spec/implementation-g1-types.json',
             'spec/egraph-types.json', 'spec/retrieval-types.json', 'spec/sql-types.json']
INHERITED_HASHES = {
    'closure/theorem-types.json': '185a556d0d312148898ab92fed83b63ca8b6f6c835c22188137121b140f05166',
    'spec/implementation-g1-types.json': '1d2412397e4af7b78f145b884acd39685f4e5b49902b82b4a949b22c8364c753',
    'spec/egraph-types.json': '229a1d3b92b6713fa4f51291b16c353cf52df1370a41f3d9f860e0c79d01b5ed',
    'spec/retrieval-types.json': '27ba0b43b311aabc04d21f0ebac4fd2108c8db54056a7009586577613b0d3905',
    'spec/sql-types.json': '55db73baea89f6415455214ea3425a5c7caa79d812906a507f67acae7e6b50ac',
}
SURFACES = ('backend/', 'frontend/', 'retrieval/', 'db/', 'scripts/', 'config/', 'formal/')
DISCOVER = ('backend/src/', 'frontend/src/', 'retrieval/', 'db/', 'scripts/', 'config/', 'formal/')
SKIP_DIRS = {'__pycache__', '.lake', '.git', 'node_modules', 'target', 'build', 'dist',
             '.pytest_cache', '.mypy_cache', '.ruff_cache'}
ALLOWED_AXIOMS = {'propext', 'Quot.sound', 'Classical.choice'}
TRUST = ['Lean 4.34.1 kernel, elaborator, pretty printer and bundled libraries',
         'propext, Quot.sound, Classical.choice when reported', 'Lake',
         'Python and this verifier', 'SHA-256 collision resistance',
         'OS, filesystem, process isolation and hardware',
         'interpretation of model propositions and trusted adapter contracts']
BOUNDARY = ['No Alloy parser, printer, JSON decoder or source-position refinement',
            'No Java, Python or TypeScript implementation refinement',
            'No PostgreSQL transaction, RLS, workspace quota or linearizability proof',
            'No browser accessibility, screen-reader, deployment or G2/G3 closure',
            'Baseline guard cannot establish prior state of files absent from its manifest and discovery roots',
            'No claim that experimental infer is complete for all operators',
            'No proof that registered model propositions entail the full prose specification',
            'Parser-report admission and deterministic wire decoder are abstract trust boundaries']
ESCAPE = re.compile(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)')
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def active_surface(path):
    return path.startswith(SURFACES)


def production_snapshot():
    """Compare all frozen production/active-formal files and detect new files."""
    require(sha(BASELINE) == BASELINE_SHA256, 'Baseline manifest hash mismatch')
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    items = baseline['files']
    require(len(items) == 309 and len({x['path'] for x in items}) == len(items), 'Malformed baseline manifest')
    expected = {x['path']: x['sha256'] for x in items if active_surface(x['path'])}
    actual = {}
    for root in SURFACES:
        directory = ROOT / root.rstrip('/')
        if not directory.is_dir():
            continue
        for path in directory.rglob('*'):
            if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel not in expected and not rel.startswith(DISCOVER):
                continue
            if path.is_symlink():
                actual[rel] = 'SYMLINK'
            elif path.is_file():
                actual[rel] = sha(path)
    changed = sorted(p for p in expected.keys() | actual.keys() if expected.get(p) != actual.get(p))
    return expected, changed


def run_command(command, cwd, env, log):
    completed = subprocess.run(command, cwd=cwd, env=env, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    log.write_text(completed.stdout, encoding='utf-8')
    require(completed.returncode == 0, f'{log.name}: nonzero exit {completed.returncode}')
    require('warning:' not in completed.stdout.lower(), f'{log.name}: Lean warning')
    return completed.stdout


def check_axioms(output, symbols):
    """Every print must report a theorem, with no unregistered axioms."""
    for symbol in symbols:
        pattern = re.compile(r"^'" + re.escape(symbol) + r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*$", re.M)
        matches = list(pattern.finditer(output))
        require(len(matches) == 1, 'Missing or duplicate axiom report: ' + symbol)
        axioms = {x.strip() for x in (matches[0].group(1) or '').split(',') if x.strip()}
        require(axioms <= ALLOWED_AXIOMS, f'Unapproved axioms for {symbol}: {sorted(axioms)}')
    lines = [line for line in output.splitlines() if line.strip()]
    require(len(lines) == len(symbols), 'Unexpected output in axiom audit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True, help='new immutable run identifier')
    parser.add_argument('--spec-sha256', required=True, help='reviewed document-stage draft hash')
    parser.add_argument('--wire-sha256', required=True, help='reviewed document-wire draft hash')
    args = parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.run_id) is not None, 'Invalid run ID')
    for value in (args.spec_sha256, args.wire_sha256):
        require(re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'Invalid SHA-256 argument')
    output = ROOT / 'gates/document/draft-runs' / args.run_id
    require(not output.exists(), 'Run directory already exists')
    output.mkdir(parents=True)
    report = {'status': 'UNSET', 'run_id': args.run_id, 'builds': [], 'blocking_reasons': [],
              'infrastructure_errors': [], 'trusted': TRUST, 'boundary': BOUNDARY,
              'scope': 'Formal model audit only; council approval and original gates remain independent.'}
    try:
        require(sha(DOCUMENT) == DOCUMENT_SHA256, 'Frozen document Lean hash mismatch')
        require(sha(TYPES) == TYPES_SHA256, 'Frozen document type inventory hash mismatch')
        require(sha(SPEC) == args.spec_sha256, 'Document supplement hash mismatch')
        require(sha(WIRE) == args.wire_sha256, 'Document wire hash mismatch')
        require(sha(CANDIDATE) == CANDIDATE_SHA256, 'Candidate manifest mismatch')
        candidate = json.loads(CANDIDATE.read_text(encoding='utf-8'))
        frozen = candidate['inputs']
        wanted = {'spec/document-stage-draft.json', 'spec/document-wire-draft.json',
                  'spec/document-ui-draft.json', 'spec/document-adapter-draft.json',
                  'gates/document/draft/Document.lean', 'gates/document/draft/types.json'}
        require(set(frozen) == wanted and candidate['status'] == 'FROZEN_FOR_FINAL_COUNCIL' and candidate['stage'] == 'document-r5', 'Invalid frozen six-input manifest')
        require(all(sha(ROOT / path) == digest for path, digest in frozen.items()), 'Frozen candidate input mismatch')
        require(frozen['spec/document-stage-draft.json'] == args.spec_sha256 and frozen['spec/document-wire-draft.json'] == args.wire_sha256,
                'Caller hashes disagree with frozen manifest')
        for path in REVIEW_PATHS:
            require((ROOT / path).is_file(), 'Missing council review: ' + path)
            review = json.loads((ROOT / path).read_text(encoding='utf-8'))
            require(review.get('decision') in {'APPROVE_GAMEPLAN', 'APPROVE_GAMEPLAN_FOR_FORMAL_GATE'}, 'Council seat has not approved: ' + path)
            require(review.get('input_hashes') == frozen, 'Council review input hash mismatch: ' + path)
            family, number = Path(path).stem.rsplit('-', 2)[-2:]
            reviewer = str(review.get('reviewer', '')).lower()
            require(family in reviewer and re.search(r'\b' + number + r'\b', reviewer) is not None, 'Council seat identity mismatch: ' + path)
            require(not review.get('blocking_findings') and not review.get('blockers'), 'Council review contains unresolved blockers: ' + path)
        production, changes = production_snapshot()
        report['production_changes_at_start'] = changes
        require(not changes, 'Production or active formal differs from SQL baseline: ' + ', '.join(changes[:12]))
        expected = {}
        for name in INHERITED:
            require(sha(ROOT / name) == INHERITED_HASHES[name], 'Inherited theorem registry changed: ' + name)
            additions = json.loads((ROOT / name).read_text(encoding='utf-8'))
            require(not (set(additions) & set(expected)), 'Duplicate inherited theorem symbol')
            expected.update(additions)
        require(len(expected) == 112, 'Expected exactly 112 inherited propositions')
        inventory = json.loads(TYPES.read_text(encoding='utf-8'))
        require(inventory['source_sha256'] == DOCUMENT_SHA256, 'Inventory source mismatch')
        doc_types = inventory['theorem_types']
        require(isinstance(doc_types, dict) and len(doc_types) == 125, 'Expected exactly 125 document propositions')
        require(all(NAME.fullmatch(k) for k in doc_types), 'Invalid document theorem symbol')
        source = DOCUMENT.read_text(encoding='utf-8')
        declarations = re.findall(r'(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)', source)
        require(len(declarations) == len(set(declarations)) and set(declarations) == set(doc_types),
                'Document theorem registry does not exactly match declarations')
        matrix = inventory['typed_constructor_fixture_matrix']
        tags = {'signature_ref','field_ref','variable_ref','predicate_call','not','and','or','implies','iff',
                'some_test','no_test','one_test','lone_test','equal','subset','union','intersection',
                'difference','join','product','transpose','all_quant','some_quant'}
        require(set(matrix) == tags, 'The 23 constructor fixtures do not match the frozen palette')
        for fixture in matrix.values():
            require(set(fixture) == {'positive', 'negative'}, 'Incomplete constructor fixture')
            for theorem in fixture.values():
                require(theorem.split()[0] in doc_types, 'Fixture points to unregistered theorem')
        sources = [p for p in (ROOT / 'formal').rglob('*.lean') if '.lake' not in p.parts] + [DOCUMENT]
        for source_file in sources:
            require(not ESCAPE.search(source_file.read_text(encoding='utf-8')), 'Forbidden proof escape: ' + str(source_file.relative_to(ROOT)))
        require(json.loads((ROOT / 'formal/lake-manifest.json').read_text())['packages'] == [], 'Undeclared Lean packages')
        paths = {ROOT / x for x in production} | {ROOT / x for x in INHERITED} | {
            DOCUMENT, TYPES, SPEC, WIRE, UI, ADAPTER, CANDIDATE, BASELINE, Path(__file__).resolve()} | {ROOT / path for path in REVIEW_PATHS}
        entries = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in sorted(paths)]
        manifest = {'files': entries}
        root_hash = hashlib.sha256(canonical(manifest)).hexdigest()
        report.update({'input_root_hash': root_hash, 'inherited_propositions': len(expected),
                       'document_propositions': len(doc_types), 'fixture_families': len(matrix),
                       'verifier_sha256': sha(__file__), 'spec_sha256': args.spec_sha256,
                       'wire_sha256': args.wire_sha256, 'candidate_sha256': CANDIDATE_SHA256, 'baseline_sha256': BASELINE_SHA256})
        write_json(output / 'manifest.json', manifest)
        write_json(output / 'registry.json', {'inherited': expected, 'document': doc_types,
            'fixtures': matrix, 'trusted': TRUST, 'boundary': BOUNDARY})
        for item in entries:
            dest = output / 'inputs' / item['path']
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / item['path'], dest)
        inherited_audit = 'import Allow\n' + '\n'.join(
            'example : (' + proposition + ') := @' + symbol + '\n#print axioms ' + symbol
            for symbol, proposition in expected.items()) + '\n'
        doc_checks = source + '\n' + '\n'.join('#check Allow.DocumentDraft.' + n for n in doc_types) + '\n'
        doc_axioms = source + '\n' + '\n'.join('#print axioms Allow.DocumentDraft.' + n for n in doc_types) + '\n'
        expected_checks = '\n'.join(doc_types.values()) + '\n'
        tool = Path.home() / '.elan/toolchains/leanprover--lean4---v4.34.1/bin'
        require((tool / 'lean').is_file() and (tool / 'lake').is_file(), 'Pinned Lean toolchain unavailable')
        env = os.environ.copy()
        env['PATH'] = str(tool) + os.pathsep + env.get('PATH', '')
        env.pop('LEAN_PATH', None)
        for label in ('A', 'B'):
            with tempfile.TemporaryDirectory(prefix='allow-document-lean-') as tmp:
                work = Path(tmp) / 'formal'
                shutil.copytree(output / 'inputs/formal', work)
                for filename, contents in [('InheritedAudit.lean', inherited_audit),
                                           ('DocumentTypes.lean', doc_checks), ('DocumentAxioms.lean', doc_axioms)]:
                    (work / filename).write_text(contents, encoding='utf-8')
                run_command([str(tool / 'lake'), 'build'], work, env, output / f'{label}-build.log')
                inherited_out = run_command([str(tool / 'lake'), 'env', 'lean', 'InheritedAudit.lean'], work, env, output / f'{label}-inherited.log')
                check_axioms(inherited_out, list(expected))
                type_out = run_command([str(tool / 'lake'), 'env', 'lean', 'DocumentTypes.lean'], work, env, output / f'{label}-types.log')
                require(type_out == expected_checks, f'{label}: document theorem type mismatch')
                axiom_out = run_command([str(tool / 'lake'), 'env', 'lean', 'DocumentAxioms.lean'], work, env, output / f'{label}-axioms.log')
                check_axioms(axiom_out, ['Allow.DocumentDraft.' + n for n in doc_types])
                artifacts = {p.relative_to(work).as_posix(): sha(p) for p in sorted(work.rglob('*.olean'))}
                require(bool(artifacts), 'No Lean artifacts produced')
                report['builds'].append({'artifacts': artifacts, 'types_sha256': hashlib.sha256(type_out.encode()).hexdigest(),
                    'inherited_sha256': hashlib.sha256(inherited_out.encode()).hexdigest(),
                    'axioms_sha256': hashlib.sha256(axiom_out.encode()).hexdigest()})
        require(report['builds'][0] == report['builds'][1], 'NONDETERMINISM')
        require(all(sha(ROOT / x['path']) == x['sha256'] for x in entries), 'INPUT_MUTATION')
        _, final_changes = production_snapshot()
        require(not final_changes, 'Production changed during audit: ' + ', '.join(final_changes[:12]))
        report['status'] = 'VERIFIED'
    except AssertionError as exc:
        report['status'] = 'BLOCKED'
        report['blocking_reasons'].append(str(exc))
    except Exception as exc:
        report['status'] = 'INFRASTRUCTURE_FAILURE'
        report['infrastructure_errors'].append(type(exc).__name__ + ': ' + str(exc))
    write_json(output / 'report.json', report)
    print(json.dumps({k: report.get(k) for k in ('status', 'input_root_hash', 'inherited_propositions',
          'document_propositions', 'fixture_families', 'blocking_reasons', 'infrastructure_errors')}, indent=2))
    return {'VERIFIED': 0, 'BLOCKED': 1, 'INFRASTRUCTURE_FAILURE': 2}[report['status']]


if __name__ == '__main__':
    sys.exit(main())
