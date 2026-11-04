#!/usr/bin/env python3
"""Verify only the inactive fresh-tier1 model after exact-input council review.

No production code is installed; JVM semantics/performance are not proved. Invocation: python verify_fresh_model.py RUN --execute.
The canonical review manifest and all six approvals must exist before execution.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEATS = {f'{family}-{number}' for family in ('terra', 'sol', 'astra') for number in (1, 2)}
OWNED = ('FreshTier1.lean', 'Audit.lean', 'types.json', 'claims.json',
         'model-closure-config.json', 'verify_fresh_model.py', 'inherited-anchors.json', 'experiment.json', 'source-evidence.json')


def packed(value):
    """Use one explicit canonical JSON encoding for manifest roots."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def sha(path):
    """Bind bytes, rather than modification times or inode identity."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    """Unknown or mismatched evidence blocks this finite model run."""
    if not condition:
        raise AssertionError(message)


def read(path):
    """Reject duplicate JSON keys in closure inputs."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'DUPLICATE_JSON_KEY:' + key)
            result[key] = value
        return result
    require(Path(path).is_file(), 'MISSING_REQUIRED_INPUT:' + str(path))
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=unique)
    except json.JSONDecodeError as error:
        raise AssertionError('INVALID_JSON_INPUT:' + str(path)) from error


def save(path, value):
    """Write a new immutable run artifact under its unique run directory."""
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def workspace_path(name):
    """Allow only ordinary workspace-relative manifest paths."""
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts, 'INVALID_PATH:' + name)
    resolved = (ROOT / path).resolve()
    require(resolved.is_relative_to(ROOT), 'OUTSIDE_WORKSPACE:' + name)
    return resolved


def input_snapshot(out):
    """Check the frozen manifest and council, then snapshot every reviewed input."""
    pins = read(HERE / 'review-input-pins.json')
    rows = pins['files']
    require(rows and len({row['path'] for row in rows}) == len(rows), 'EMPTY_OR_DUPLICATE_INPUTS')
    root_hash = hashlib.sha256(packed(rows)).hexdigest()
    require(root_hash == pins['input_root_sha256'], 'MANIFEST_ROOT_MISMATCH')
    paths = {row['path'] for row in rows}
    for name in OWNED + ('contract.json',):
        require(str((HERE / name).relative_to(ROOT)) in paths, 'UNPINNED_REQUIRED_INPUT:' + name)
    anchors = read(HERE / 'inherited-anchors.json')
    evidence = read(HERE / 'source-evidence.json')
    for row in anchors['files'] + evidence['files']:
        require(row in rows, 'UNPINNED_INHERITED_ANCHOR:' + row['path'])
    for row in rows:
        source = workspace_path(row['path'])
        require(sha(source) == row['sha256'], 'INPUT_MUTATION:' + row['path'])
        target = out / 'inputs' / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    reviews = []
    for seat in sorted(SEATS):
        path = ROOT / 'reviews' / ('fresh-tier1-' + seat + '.json')
        review = read(path)
        require(review['reviewer'] == seat, 'WRONG_REVIEWER:' + seat)
        require(review['decision'] == 'APPROVE_IMPLEMENTATION_CONTRACT', 'IMPLEMENTATION_CONTRACT_NOT_APPROVED:' + seat)
        require(review['package_root_sha256'] == root_hash, 'STALE_REVIEW:' + seat)
        target = out / 'reviews' / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        reviews.append({'seat': seat, 'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    save(out / 'manifest.json', pins)
    save(out / 'reviews.json', reviews)
    return pins, reviews


def inherited_anchor(base, out):
    """Check the frozen active309 anchors without claiming to reprove them."""
    anchors = read(base / 'inherited-anchors.json')
    for row in anchors['files']:
        require(sha(out / 'inputs' / row['path']) == row['sha256'], 'INHERITED_SNAPSHOT_MUTATION:' + row['path'])
    report = read(out / 'inputs' / anchors['report_path'])
    require(report['status'] == 'VERIFIED' and report['claims']['total'] == 309 and
            report['claims']['passed'] == 309, 'INVALID_INHERITED_REPORT')
    require(report['input_root_hash'] == anchors['report_input_root_hash'], 'INHERITED_ROOT_MISMATCH')
    for dependency in anchors['supplement_reports']:
        supplement = read(out / 'inputs' / dependency['path'])
        require(supplement['status'] == 'VERIFIED' and
                supplement['claims']['total'] == dependency['claims'] and
                supplement['claims']['passed'] == dependency['claims'] and
                supplement['input_root_hash'] == dependency['input_root_hash'],
                'INVALID_SUPPLEMENT_ANCHOR:' + dependency['path'])
    return {'status': 'UNCHANGED_ANCHORS_CHECKED_NOT_REPROVED', 'propositions': 309,
            'supplements_checked_not_reproved': anchors['supplement_reports'],
            'report_path': anchors['report_path'], 'report_input_root_hash': anchors['report_input_root_hash'],
            'anchor_count': len(anchors['files'])}


def source_inventory(base, config):
    """Freeze full declarations through elaborated types, never split at :=."""
    source = (base / 'FreshTier1.lean').read_text()
    forbidden = r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)|debug\.skipKernelTC'
    require(re.search(forbidden, source) is None, 'UNREGISTERED_PROOF_ESCAPE')
    names = ['Allow.FreshTier1.' + name for name in re.findall(r'^theorem (\w+)', source, re.M)]
    types = read(base / 'types.json')['claims']
    claims = read(base / 'claims.json')['claims']
    require(len(names) == config['candidate_claim_count'], 'CLAIM_COUNT_MISMATCH')
    require(len({row['id'] for row in claims}) == len(claims), 'DUPLICATE_CLAIM_IDS')
    require(names == [row['theorem'] for row in types], 'TYPE_INVENTORY_MISMATCH')
    require([(row['id'], row['theorem']) for row in types] ==
            [(row['id'], row['theorem']) for row in claims], 'PROVENANCE_MISMATCH')
    audit = 'import FreshTier1\nset_option format.width 1000000\nset_option pp.universes true\n'
    audit += ''.join('#check @' + name + '\n#print axioms ' + name + '\n' for name in names)
    require((base / 'Audit.lean').read_text() == audit, 'AUDIT_COMMANDS_MISMATCH')
    witnesses = config['witness_theorems']
    require(len(witnesses) == 2 and len(set(witnesses)) == 2 and set(witnesses) <= set(names),
            'MISSING_OR_DUPLICATE_WITNESS')
    expected = ''.join(row['exact_check_output'] + '\n' + row['exact_axiom_output'] + '\n' for row in types)
    for row in types:
        declaration = row['exact_axiom_output']
        if 'depends on axioms: [' in declaration:
            raw = declaration.split('depends on axioms: [', 1)[1].removesuffix(']')
            axioms = {re.sub(r'\.\{.*\}', '', value.strip()) for value in raw.split(',')}
            require(axioms <= set(config['allowed_axioms']), 'UNDECLARED_AXIOM:' + row['theorem'])
        else:
            require(declaration == "'" + row['theorem'] + "' does not depend on any axioms", 'BAD_AXIOM_RECORD')
    return types, claims, expected


def clean_build(base, out, ordinal, config, expected):
    """Compile from a fresh directory with only frozen source plus trusted Lean Std."""
    lean = Path(config['lean_binary'])
    require(sha(lean) == config['lean_binary_sha256'], 'LEAN_BINARY_MUTATION')
    version = subprocess.run([str(lean), '--version'], text=True, capture_output=True, check=True).stdout.strip()
    require(version == config['lean_version'], 'LEAN_VERSION_MISMATCH')
    result_dir = out / ('build-' + str(ordinal))
    result_dir.mkdir()
    with tempfile.TemporaryDirectory(prefix='allow-fresh-tier1-') as temp:
        directory = Path(temp)
        for name in ('FreshTier1.lean', 'Audit.lean'):
            shutil.copyfile(base / name, directory / name)
        env = {'PATH': os.environ.get('PATH', ''), 'LEAN_PATH': str(directory), 'LC_ALL': 'C.UTF-8'}
        outputs = []
        for name in ('FreshTier1', 'Audit'):
            command = [str(lean), '-DwarningAsError=true', '-o', name + '.olean', name + '.lean']
            run = subprocess.run(command, cwd=directory, env=env, text=True, capture_output=True, timeout=120)
            (result_dir / (name + '.stdout')).write_text(run.stdout)
            (result_dir / (name + '.stderr')).write_text(run.stderr)
            require(run.returncode == 0 and not run.stderr, 'CLEAN_BUILD_FAILURE:' + name)
            outputs.append(run.stdout)
        require(outputs[0] == '', 'UNEXPECTED_MODEL_OUTPUT')
        require(outputs[1] == expected, 'ACTUAL_TYPE_OR_AXIOM_MISMATCH')
        artifacts = {name: sha(directory / name) for name in ('FreshTier1.olean', 'Audit.olean')}
        for name in artifacts:
            shutil.copyfile(directory / name, result_dir / name)
        record = {'status': 'PASS', 'exit_code': 0, 'artifacts': artifacts,
                  'audit_sha256': hashlib.sha256(outputs[1].encode()).hexdigest(), 'lean_version': version}
        save(result_dir / 'result.json', record)
        return record


def execute(run_id):
    """Return one finite model closure state; leave the production aggregate untouched."""
    require(re.fullmatch(r'[A-Za-z0-9_-]+', run_id) is not None, 'INVALID_RUN_ID')
    out = HERE / 'formal-runs' / run_id
    out.mkdir(parents=True, exist_ok=False)
    report = {'closure_id': 'ALLOW-FRESH-TIER1-MODEL-' + run_id,
              'timestamp': datetime.now(timezone.utc).isoformat(), 'status': 'BLOCKED',
              'classification': 'INACTIVE_ABSTRACT_FRESH_TIER1_MODEL_ONLY',
              'blocking_reasons': [], 'infrastructure_errors': [], 'builds': [],
              'execution_environment': {'python': platform.python_version(), 'platform': platform.platform()},
              'verifier_sha256': sha(__file__)}
    try:
        pins, reviews = input_snapshot(out)
        base = out / 'inputs' / HERE.relative_to(ROOT)
        config = read(base / 'model-closure-config.json')
        types, claims, expected = source_inventory(base, config)
        baseline = inherited_anchor(base, out)
        report.update({'input_root_hash': pins['input_root_sha256'], 'reviews': reviews,
                       'trusted': config['trusted'], 'excluded': config['excluded'],
                       'inherited_baseline': baseline,
                       'correspondence': {'status': 'OUT_OF_SCOPE', 'reason': 'No production implementation is proved or activated.'}})
        for ordinal in (1, 2):
            report['builds'].append(clean_build(base, out, ordinal, config, expected))
        require(report['builds'][0] == report['builds'][1], 'NONDETERMINISM')
        for row in pins['files']:
            require(sha(workspace_path(row['path'])) == row['sha256'], 'INPUT_MUTATION:' + row['path'])
        for review in reviews:
            require(sha(ROOT / review['path']) == review['sha256'], 'REVIEW_MUTATION:' + review['seat'])
        report.update({'status': 'VERIFIED', 'claims': {'total': len(types), 'passed': len(types), 'blocked': 0, 'unresolved': 0},
                       'determinism': 'PASS', 'witnesses': {'required': 2, 'valid': 2},
                       'provenance': {'public_claims': len(claims), 'fully_bound': len(claims), 'orphan_claims': 0},
                       'active_formal_count': 'UNCHANGED_309_NOT_REPROVED_BY_THIS_RUN'})
        save(out / 'provenance.json', [{'claim_id': row['id'], 'theorem': row['theorem'],
             'input_root_hash': pins['input_root_sha256'], 'evidence': ['build-1/Audit.stdout', 'build-2/Audit.stdout'],
             'verifier_sha256': report['verifier_sha256'], 'trust': config['trusted']} for row in claims])
    except AssertionError as error:
        report['blocking_reasons'].append(str(error))
    except (ValueError, KeyError, TypeError) as error:
        report['blocking_reasons'].append('INVALID_INPUT_SCHEMA:' + type(error).__name__ + ':' + str(error))
    except (OSError, subprocess.SubprocessError) as error:
        report['status'] = 'INFRASTRUCTURE_FAILURE'
        report['infrastructure_errors'].append(type(error).__name__ + ':' + str(error))
    save(out / 'report.json', report)
    print(json.dumps({key: report.get(key) for key in ('status', 'input_root_hash', 'claims', 'blocking_reasons', 'infrastructure_errors')}))
    return 0 if report['status'] == 'VERIFIED' else 1 if report['status'] == 'BLOCKED' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('--execute', action='store_true', required=True)
    arguments = parser.parse_args()
    raise SystemExit(execute(arguments.run_id))
