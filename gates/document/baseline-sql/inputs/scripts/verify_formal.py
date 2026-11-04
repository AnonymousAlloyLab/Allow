#!/usr/bin/env python3
"""Freeze and check the finite G1 proof supplement in two clean Lean builds.

This verifier is trusted orchestration. It establishes no Java/React refinement.
Exit 0: VERIFIED; 1: BLOCKED; 2: INFRASTRUCTURE_FAILURE.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
TRUST = ['Lean 4.34.1 kernel/compiler and bundled libraries',
         'propext, Quot.sound, Classical.choice', 'Lake', 'Python runtime and this verifier',
         'SHA-256 and collision resistance', 'OS/filesystem/process semantics', 'hardware',
         'interpretation of formal model vs requirements prose']

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def packed(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--run-id', required=True)
    parsed = args.parse_args()
    require(parsed.run_id.replace('-', '').replace('_', '').isalnum(), 'Invalid run id')
    output = ROOT / 'gates/g1/formal-runs' / parsed.run_id
    require(not output.exists(), 'Do not overwrite frozen evidence')
    output.mkdir(parents=True)
    supplement = json.loads((ROOT / 'spec/implementation-g1.json').read_text())
    expected = json.loads((ROOT / 'closure/theorem-types.json').read_text())
    additions = json.loads((ROOT / 'spec/implementation-g1-types.json').read_text())
    expected.update(additions)
    sources = sorted(p for p in (ROOT / 'formal').rglob('*.lean') if '.lake' not in p.parts)
    inputs = sources + [ROOT / p for p in ['formal/lean-toolchain', 'formal/lakefile.toml',
        'formal/lake-manifest.json', 'spec/allow-contract.json', 'spec/implementation-g1.json',
        'spec/implementation-g1-types.json', 'spec/slot-profile.json', 'closure/theorem-types.json',
        'scripts/verify_formal.py']]
    manifest = {'files': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted(inputs)]}
    root_hash = hashlib.sha256(packed(manifest)).hexdigest()
    save(output / 'manifest.json', manifest)
    registry = {'id': 'V-G1-FORMAL', 'sha256': sha(__file__),
        'exit_codes': {'VERIFIED': 0, 'BLOCKED': 1, 'INFRASTRUCTURE_FAILURE': 2},
        'expected_propositions': expected, 'trusted': TRUST,
        'pass_predicate': 'All expected propositions and allowed axioms pass two clean builds with identical artifacts/metadata and unchanged frozen inputs.',
        'nondeterministic_fields': ['temporary paths', 'build timings', 'run id'],
        'excluded': ['production implementation', 'parser correspondence', 'OS security', 'market or rights clearance']}
    save(output / 'verifier-registry.json', registry)
    # A source snapshot makes every run replayable after later authorized edits.
    for p in inputs:
        target = output / 'inputs' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    audit = 'import Allow\n' + '\n'.join('example : (' + t + ') := @' + s +
        '\n#print axioms ' + s for s, t in expected.items()) + '\n'
    report = {'closure_id': 'allow-g1-' + parsed.run_id, 'input_root_hash': root_hash,
        'supplement_sha256': sha(ROOT / 'spec/implementation-g1.json'), 'status': 'UNSET',
        'verifier_id': registry['id'], 'verifier_sha256': registry['sha256'],
        'environment': {'python': sys.version, 'platform': platform.platform()},
        'trusted': TRUST, 'propositions': len(expected), 'supplement_obligations': len(additions),
        'builds': [], 'blocking_reasons': [], 'infrastructure_errors': [],
        'boundary': 'Fixed finite Lean propositions, including six concrete witnesses; no implementation refinement.',
        'production_sources_at_freeze': len(list((ROOT / 'backend').rglob('*.java'))) + len(list((ROOT / 'frontend/src').rglob('*.ts*')))}
    try:
        import re
        require({o['symbol'] for o in supplement['formal_obligations']} == set(additions), 'Obligation mismatch')
        require(json.loads((ROOT / 'formal/lake-manifest.json').read_text())['packages'] == [], 'Undeclared Lean packages')
        for p in sources:
            require(not re.search(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)', p.read_text()), 'Forbidden proof escape')
        tool = Path.home() / '.elan/toolchains/leanprover--lean4---v4.34.1/bin'
        environment = os.environ.copy()
        environment['PATH'] = str(tool) + os.pathsep + environment.get('PATH', '')
        environment.pop('LEAN_PATH', None)
        for label in ['A', 'B']:
            with tempfile.TemporaryDirectory(prefix='allow-g1-lean-') as temp:
                work = Path(temp) / 'formal'
                shutil.copytree(output / 'inputs/formal', work)
                for command, logname in [([str(tool / 'lake'), 'build'], 'build'),
                                         ([str(tool / 'lake'), 'env', 'lean', 'Audit.lean'], 'audit')]:
                    if logname == 'audit':
                        (work / 'Audit.lean').write_text(audit)
                    result = subprocess.run(command, cwd=work, env=environment,
                        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
                    (output / (label + '-' + logname + '.log')).write_text(result.stdout)
                    require(result.returncode == 0 and 'warning:' not in result.stdout.lower(), label + '-' + logname + ' failed')
                axioms = set()
                for group in re.findall(r'depends on axioms: \[([^\]]*)\]', result.stdout):
                    axioms.update(x.strip() for x in group.split(',') if x.strip())
                require(axioms <= {'propext', 'Quot.sound', 'Classical.choice'}, 'Undeclared axiom')
                require(all(s in result.stdout for s in expected), 'Missing proof output')
                hashes = {str(p.relative_to(work)): sha(p) for p in sorted(work.rglob('*.olean'))}
                require(bool(hashes), 'No compiled proof artifacts')
                report['builds'].append({'artifacts': hashes, 'axioms': sorted(axioms),
                    'audit_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(), 'exit_code': 0})
        require(report['builds'][0] == report['builds'][1], 'NONDETERMINISM')
        require(all(sha(ROOT / f['path']) == f['sha256'] for f in manifest['files']), 'INPUT_MUTATION')
        report['status'] = 'VERIFIED'
    except AssertionError as error:
        report['status'] = 'BLOCKED'
        report['blocking_reasons'].append(str(error))
    except Exception as error:
        report['status'] = 'INFRASTRUCTURE_FAILURE'
        report['infrastructure_errors'].append(type(error).__name__ + ': ' + str(error))
    report['claims'] = [{'symbol': s, 'expected_proposition': t,
        'status': 'PASS' if report['status'] == 'VERIFIED' else 'BLOCK',
        'input_root_hash': root_hash, 'verifier_sha256': registry['sha256'],
        'evidence': ['A-audit.log', 'B-audit.log'], 'classification': 'PROVED_MODEL'} for s, t in expected.items()]
    report['determinism'] = 'PASS' if report['status'] == 'VERIFIED' else 'BLOCK'
    save(output / 'report.json', report)
    save(ROOT / 'gates/g1/formal-report.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'input_root_hash', 'propositions',
        'supplement_obligations', 'production_sources_at_freeze', 'blocking_reasons', 'infrastructure_errors']}, indent=2))
    return {'VERIFIED': 0, 'BLOCKED': 1, 'INFRASTRUCTURE_FAILURE': 2}[report['status']]

if __name__ == '__main__':
    raise SystemExit(main())
