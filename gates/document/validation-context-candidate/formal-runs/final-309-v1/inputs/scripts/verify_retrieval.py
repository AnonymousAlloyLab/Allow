#!/usr/bin/env python3
"""Verify a frozen retrieval supplement and retained exact rule mappings in two clean Lean builds.

The registered verifier is trusted orchestration; it proves no Java refinement.
Exit 0 VERIFIED, 1 BLOCKED, 2 INFRASTRUCTURE_FAILURE. Existing runs are immutable.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TRUST = ['Lean 4.34.1 kernel/compiler and bundled libraries', 'propext, Quot.sound, Classical.choice',
    'Lake', 'Python and this verifier/generator', 'SHA-256 collision resistance',
    'OS/filesystem/process semantics', 'hardware', 'interpretation of model versus specification prose']
OPS = {'BOOL': {'TRUE': ('truth', 0), 'FALSE': ('falsity', 0), 'NOT': ('not', 1),
    'AND': ('and', 2), 'OR': ('or', 2)}, 'REL': {'EMPTY': ('empty', 0),
    'UNION': ('union', 2), 'INTER': ('inter', 2), 'DIFF': ('diff', 2)}}

def sha(path):
    """Hash one exact input file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def packed(value):
    """Serialize metadata deterministically for integrity binding."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def save(path, value):
    """Store readable bound metadata with a final newline."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def require(condition, message):
    """Fail closed on a registered finite obligation."""
    if not condition:
        raise AssertionError(message)

def variables(pattern):
    """Extract only the closed pattern-variable alphabet."""
    if isinstance(pattern, str):
        require(pattern in ['p', 'q', 'r'], 'Unknown pattern variable')
        return {pattern}
    require(isinstance(pattern, list) and bool(pattern), 'Invalid pattern constructor')
    result = set()
    for child in pattern[1:]:
        result |= variables(child)
    return result

def term(pattern, family):
    """Translate a closed pattern into a typed Lean constructor expression."""
    if isinstance(pattern, str):
        variables(pattern)
        return pattern
    require(pattern[0] in OPS[family], 'Wrong operator family')
    constructor, arity = OPS[family][pattern[0]]
    require(len(pattern) == arity + 1, 'Wrong operator arity')
    prefix = 'Allow.Formula' if family == 'BOOL' else 'Allow.EGraph.RelExpr'
    children = ''.join(' (' + term(child, family) + ')' for child in pattern[1:])
    return prefix + '.' + constructor + children

def evaluate(pattern, values):
    """Interpret each rule independently as a Boolean or one-tuple relation algebra."""
    if isinstance(pattern, str):
        return values[pattern]
    op = pattern[0]
    args = [evaluate(child, values) for child in pattern[1:]]
    if op == 'TRUE': return True
    if op in ['FALSE', 'EMPTY']: return False
    if op == 'NOT': return not args[0]
    if op in ['AND', 'INTER']: return args[0] and args[1]
    if op in ['OR', 'UNION']: return args[0] or args[1]
    if op == 'DIFF': return args[0] and not args[1]
    raise AssertionError('Unknown evaluator operator')

def rule_audit(catalog):
    """Generate exact Lean constructor correspondence and independent finite truth checks."""
    proofs = ['namespace Allow.EGraphCatalog']
    ids, constructors = set(), set()
    cases = 0
    for rule in catalog['rules']:
        identifier, family = rule['id'], rule['family']
        require(re.fullmatch('[A-Z][A-Z0-9_]*', identifier) is not None, 'Invalid rule ID')
        require(identifier not in ids and rule['lean_constructor'] not in constructors, 'Ambiguous rule mapping')
        require(rule['orientation'] == 'forward' and family in OPS, 'Unknown rule orientation/family')
        ids.add(identifier); constructors.add(rule['lean_constructor'])
        lhs, rhs = rule['left'], rule['right']
        names = sorted(variables(lhs))
        require(variables(rhs) <= set(names), 'Unbound RHS variable')
        left, right = term(lhs, family), term(rhs, family)
        ast = 'Allow.Formula' if family == 'BOOL' else 'Allow.EGraph.RelExpr'
        derivation = 'Allow.EGraph.Derivation' if family == 'BOOL' else 'Allow.EGraph.RelDerivation'
        constructor = rule['lean_constructor']
        require(re.fullmatch('(Certificate|Rule|RelRule)\.[A-Za-z]+', constructor) is not None, 'Invalid Lean constructor')
        qualified = ('Allow.' if constructor.startswith('Certificate.') else 'Allow.EGraph.') + constructor
        application = qualified + ''.join(' ' + name for name in names)
        if constructor.startswith('Certificate.'):
            application = 'Allow.EGraph.Rule.base (' + application + ')'
        binders = (' (' + ' '.join(names) + ' : ' + ast + ' n)') if names else ''
        proofs.append(f'theorem {identifier} {{n : Nat}}{binders} : {derivation} (({left}) : {ast} n) (({right}) : {ast} n) := .rule ({application})')
        proofs.append('#print axioms Allow.EGraphCatalog.' + identifier)
        for assignment in itertools.product([False, True], repeat=3):
            value = dict(zip(['p', 'q', 'r'], assignment))
            require(evaluate(lhs, value) == evaluate(rhs, value), 'Unsound finite rule: ' + identifier)
            cases += 1
    proofs.append('end Allow.EGraphCatalog')
    require(len(ids) == 34, 'Frozen rule count mismatch')
    require(evaluate(['DIFF', 'p', 'q'], {'p': True, 'q': False}) !=
            evaluate(['DIFF', 'q', 'p'], {'p': True, 'q': False}), 'Negative oracle failed')
    return '\n'.join(proofs), sorted(ids), cases

def baseline_changes():
    """Observe production changes relative to the preserved egraph snapshot before first implementation."""
    manifest = json.loads((ROOT / 'gates/retrieval/baseline-egraph/implementation-manifest.json').read_text())
    expected = {item['path']: item['sha256'] for item in manifest['files']
        if item['path'].startswith(('backend/src/', 'frontend/src/'))}
    actual = {str(p.relative_to(ROOT)): sha(p) for directory in ['backend/src', 'frontend/src']
        for p in (ROOT / directory).rglob('*') if p.is_file()}
    return sorted(path for path in expected.keys() | actual.keys() if expected.get(path) != actual.get(path))

def main():
    """Freeze inputs, audit all claims, preserve two clean-build results and apply the decision rule."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--require-baseline', action='store_true')
    args = parser.parse_args()
    require(re.fullmatch('[A-Za-z0-9_-]+', args.run_id) is not None, 'Invalid run ID')
    output = ROOT / 'gates/retrieval/formal-runs' / args.run_id
    require(not output.exists(), 'Never overwrite an existing run')
    output.mkdir(parents=True)
    expected = {}
    for name in ['closure/theorem-types.json', 'spec/implementation-g1-types.json', 'spec/egraph-types.json', 'spec/retrieval-types.json']:
        expected.update(json.loads((ROOT / name).read_text()))
    additions = json.loads((ROOT / 'spec/retrieval-types.json').read_text())
    supplement = json.loads((ROOT / 'spec/retrieval-stage.json').read_text())
    catalog = json.loads((ROOT / 'spec/egraph-rules.json').read_text())
    sources = sorted(p for p in (ROOT / 'formal').rglob('*.lean') if '.lake' not in p.parts)
    inputs = sources + [ROOT / name for name in ['formal/lean-toolchain', 'formal/lakefile.toml',
        'formal/lake-manifest.json', 'spec/allow-contract.json', 'spec/implementation-g1.json',
        'spec/implementation-g1-types.json', 'spec/slot-profile.json', 'closure/theorem-types.json',
        'spec/egraph-stage.json', 'spec/egraph-types.json', 'spec/egraph-rules.json',
        'spec/retrieval-stage.json', 'spec/retrieval-types.json',
        'scripts/verify_retrieval.py', 'gates/retrieval/baseline-egraph/implementation-manifest.json']]
    manifest = {'files': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted(inputs)]}
    root_hash = hashlib.sha256(packed(manifest)).hexdigest()
    save(output / 'manifest.json', manifest)
    for path in inputs:
        copy = output / 'inputs' / path.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
    registry = {'id': 'V-RETRIEVAL-FORMAL', 'sha256': sha(__file__), 'trusted': TRUST,
        'exit_codes': {'VERIFIED': 0, 'BLOCKED': 1, 'INFRASTRUCTURE_FAILURE': 2},
        'propositions': expected, 'rules': catalog['rules'],
        'pass_predicate': 'Every exact proposition, generated catalog constructor mapping, finite rule assignment and permitted axiom check passes twice with identical proof artifacts/audit metadata and no changed inputs.',
        'nondeterministic_fields': ['temporary paths', 'build timings', 'run ID'],
        'excluded': ['Java/TypeScript refinement', 'parser correspondence', 'union-find correctness',
            'matcher completeness', 'OS security', 'commercial or dataset rights',
            'solver/instance projection faithfulness', 'learned retrieval quality', 'float/SQL/transaction refinement']}
    save(output / 'verifier-registry.json', registry)
    report = {'closure_id': 'allow-retrieval-' + args.run_id, 'input_root_hash': root_hash,
        'supplement_sha256': sha(ROOT / 'spec/retrieval-stage.json'), 'rules_sha256': sha(ROOT / 'spec/egraph-rules.json'),
        'status': 'UNSET', 'verifier_id': registry['id'], 'verifier_sha256': registry['sha256'],
        'environment': {'python': sys.version, 'platform': platform.platform()}, 'trusted': TRUST,
        'model_propositions': len(expected), 'new_model_propositions': len(additions), 'builds': [],
        'blocking_reasons': [], 'infrastructure_errors': [], 'baseline_required': args.require_baseline,
        'production_changes_at_freeze': baseline_changes(), 'boundary': registry['excluded']}
    try:
        require({o['symbol'] for o in supplement['formal_obligations']} == set(additions), 'Obligation mismatch')
        if args.require_baseline:
            require(not report['production_changes_at_freeze'], 'Production changed before formal freeze')
        require(json.loads((ROOT / 'formal/lake-manifest.json').read_text())['packages'] == [], 'Undeclared Lean packages')
        for source in sources:
            require(not re.search(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)', source.read_text()), 'Forbidden proof escape')
        rules, identifiers, cases = rule_audit(catalog)
        audit = 'import Allow\n' + '\n'.join('example : (' + proposition + ') := @' + symbol +
            '\n#print axioms ' + symbol for symbol, proposition in expected.items()) + '\n' + rules + '\n'
        (output / 'Audit.lean').write_text(audit)
        report['catalog_mappings'] = len(identifiers)
        report['finite_rule_assignments'] = cases
        tool = Path.home() / '.elan/toolchains/leanprover--lean4---v4.34.1/bin'
        environment = os.environ.copy()
        environment['PATH'] = str(tool) + os.pathsep + environment.get('PATH', '')
        environment.pop('LEAN_PATH', None)
        for label in ['A', 'B']:
            with tempfile.TemporaryDirectory(prefix='allow-retrieval-lean-') as temporary:
                work = Path(temporary) / 'formal'
                shutil.copytree(output / 'inputs/formal', work)
                (work / 'Audit.lean').write_text(audit)
                for command, name in [([str(tool / 'lake'), 'build'], 'build'),
                        ([str(tool / 'lake'), 'env', 'lean', 'Audit.lean'], 'audit')]:
                    result = subprocess.run(command, cwd=work, env=environment, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
                    (output / f'{label}-{name}.log').write_text(result.stdout)
                    require(result.returncode == 0 and 'warning:' not in result.stdout.lower(), f'{label}-{name} failed')
                axioms = set()
                for group in re.findall(r'depends on axioms: \[([^\]]*)\]', result.stdout):
                    axioms.update(item.strip() for item in group.split(',') if item.strip())
                require(axioms <= {'propext', 'Quot.sound', 'Classical.choice'}, 'Undeclared axiom')
                require(all(symbol in result.stdout for symbol in expected), 'Missing theorem audit')
                require(all('Allow.EGraphCatalog.' + symbol in result.stdout for symbol in identifiers), 'Missing rule mapping')
                artifacts = {str(p.relative_to(work)): sha(p) for p in sorted(work.rglob('*.olean'))}
                require(bool(artifacts), 'Missing proof artifacts')
                report['builds'].append({'artifacts': artifacts, 'axioms': sorted(axioms),
                    'audit_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(), 'exit_code': 0})
        require(report['builds'][0] == report['builds'][1], 'NONDETERMINISM')
        require(all(sha(ROOT / item['path']) == item['sha256'] for item in manifest['files']), 'INPUT_MUTATION')
        report['status'] = 'VERIFIED'
    except AssertionError as error:
        report['status'] = 'BLOCKED'; report['blocking_reasons'].append(str(error))
    except Exception as error:
        report['status'] = 'INFRASTRUCTURE_FAILURE'; report['infrastructure_errors'].append(type(error).__name__ + ': ' + str(error))
    report['claims'] = [{'symbol': symbol, 'expected_proposition': proposition,
        'status': 'PASS' if report['status'] == 'VERIFIED' else 'BLOCK', 'classification': 'PROVED_MODEL',
        'input_root_hash': root_hash, 'verifier_sha256': registry['sha256'],
        'evidence': ['A-audit.log', 'B-audit.log']} for symbol, proposition in expected.items()]
    report['determinism'] = 'PASS' if report['status'] == 'VERIFIED' else 'BLOCK'
    save(output / 'report.json', report)
    save(ROOT / 'gates/retrieval/formal-report.json', report)
    print(json.dumps({key: report.get(key) for key in ['status', 'input_root_hash', 'model_propositions',
        'new_model_propositions', 'catalog_mappings', 'finite_rule_assignments', 'production_changes_at_freeze',
        'blocking_reasons', 'infrastructure_errors']}, indent=2))
    return {'VERIFIED': 0, 'BLOCKED': 1, 'INFRASTRUCTURE_FAILURE': 2}[report['status']]

if __name__ == '__main__':
    sys.exit(main())
