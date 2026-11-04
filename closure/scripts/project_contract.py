#!/usr/bin/env python3
"""Deterministic translation of the explicitly designated JSON formal kernel.

This is not a natural-language-to-Lean compiler. Unknown nodes/rules fail closed.
"""
import argparse
import json
from pathlib import Path

NODES = dict(zip(
    ['hole', 'truth', 'ref', 'not', 'and', 'or', 'implies', 'union', 'some', 'exists'],
    ['hole', 'truth', 'ref', 'not', 'and', 'or', 'implies', 'union', 'someRel', 'existsRel']))
RULES = dict(zip(
    ['and_comm', 'and_assoc', 'and_idem', 'or_comm', 'or_assoc', 'or_idem', 'double_not', 'de_morgan'],
    ['andComm', 'andAssoc', 'andIdem', 'orComm', 'orAssoc', 'orIdem', 'doubleNot', 'deMorgan']))
FIELDS = {'version', 'type_policy', 'raw_nodes', 'canonical_atom_limit', 'rewrite_rules',
          'solver_statuses', 'trusted_analysis_label', 'rag_enabled', 'production_release_enabled',
          'lean_toolchain'}

def render(contract):
    k = contract['formal_kernel']
    if set(k) != FIELDS:
        raise ValueError('Unknown or missing formal-kernel fields')
    def string(s):
        if not isinstance(s, str) or any(ord(ch) < 32 or ord(ch) > 126 for ch in s):
            raise ValueError('Kernel strings must be printable ASCII')
        return json.dumps(s)
    def boolean(b):
        if type(b) is not bool:
            raise ValueError('Expected Boolean')
        return 'true' if b else 'false'
    def tags(values, mapping):
        if len(set(values)) != len(values):
            raise ValueError('Duplicate tag')
        return '[' + ', '.join('.' + mapping[v] for v in values) + ']'
    if type(k['canonical_atom_limit']) is not int or not 1 <= k['canonical_atom_limit'] <= 8:
        raise ValueError('Invalid canonical atom limit')
    statuses = {s: s for s in ['SAT', 'UNSAT', 'UNKNOWN', 'TIMEOUT', 'CANCELLED', 'ERROR']}
    return '\n'.join([
        '-- Generated only from spec/allow-contract.json formal_kernel; do not hand edit.',
        'import Allow.Kernel', '', 'namespace Allow', '',
        'def generatedKernel : KernelConfig where',
        '  version := ' + string(k['version']),
        '  typePolicy := ' + string(k['type_policy']),
        '  nodes := ' + tags(k['raw_nodes'], NODES),
        '  atomLimit := ' + str(k['canonical_atom_limit']),
        '  rules := ' + tags(k['rewrite_rules'], RULES),
        '  statuses := ' + tags(k['solver_statuses'], statuses),
        '  analysisLabel := ' + string(k['trusted_analysis_label']),
        '  ragEnabled := ' + boolean(k['rag_enabled']),
        '  releaseEnabled := ' + boolean(k['production_release_enabled']),
        '  toolchain := ' + string(k['lean_toolchain']), '', 'end Allow', ''])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    contract = json.loads((args.root / 'spec/allow-contract.json').read_text())
    target = args.root / 'formal/Allow/Generated.lean'
    content = render(contract)
    if args.check:
        if target.read_text() != content:
            raise SystemExit('Generated Lean projection differs from JSON')
    else:
        target.write_text(content)

if __name__ == '__main__':
    main()
