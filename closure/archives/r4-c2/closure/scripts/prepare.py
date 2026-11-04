#!/usr/bin/env python3
"""Freeze an explicit specification-model closure candidate before verification.

Run only before the first verification or with a new closure ID after a change.
Reports/evidence from earlier candidates are immutable and are never reused.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

from policy import inputs, claim_records, provenance_records, WITNESSES

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write(p, data):
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--closure-id', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    c = json.loads((root / 'spec/allow-contract.json').read_text())
    chash = digest(root / 'spec/allow-contract.json')
    council = {'contract_id': c['contract_id'], 'contract_revision': c['revision'],
               'contract_sha256': chash, 'classification': 'ADVISORY_DESIGN_REVIEW',
               'dispatch_attestation': 'Parent collaboration tool calls supplied these model IDs; runtime backend identity is not independently attested.',
               'members': {}, 'implementation_authorized': False, 'commercial_release_cleared': False}
    for seat, model in c['review_council']['requested_models'].items():
        path = root / 'reviews' / (seat + '.json')
        report = json.loads(path.read_text())
        final = report['final_review']
        if final.get('contract_sha256') != chash:
            raise ValueError('Stale/missing final review for ' + seat)
        council['members'][seat] = {'dispatch_model': model, 'contract_sha256': chash,
             'report': str(path.relative_to(root)), 'report_sha256': digest(path),
             'final_verdict': final['verdict']}
    write(root / 'reviews/council-summary.json', council)
    leanroot = Path.home() / '.elan/toolchains/leanprover--lean4---v4.34.1'
    tcb = [
        {'id': 'T-LEAN', 'name': 'Pinned Lean 4.34.1 kernel, elaborator/compiler and bundled Init/Std libraries',
         'path': str(leanroot / 'bin/lean'), 'sha256': digest(leanroot / 'bin/lean'),
         'version': subprocess.check_output([str(leanroot / 'bin/lean'), '--version'], text=True).strip()},
        {'id': 'T-LOGIC', 'name': 'Standard Lean logical axioms propext, Quot.sound and Classical.choice'},
        {'id': 'T-LAKE', 'name': 'Pinned Lake build driver and trusted installed toolchain dependencies',
         'path': str(leanroot / 'bin/lake'), 'sha256': digest(leanroot / 'bin/lake')},
        {'id': 'T-PYTHON', 'name': 'CPython interpreter, standard library and linked runtime libraries',
         'path': sys.executable, 'sha256': digest(sys.executable), 'version': sys.version},
        {'id': 'T-SCHEMA', 'name': 'jsonschema validator and installed dependencies',
         'version': importlib.metadata.version('jsonschema')},
        {'id': 'T-VERIFIER', 'name': 'Frozen Python verifier, projection, preparation and policy scripts; correctness of orchestration is trusted, not formally proved'},
        {'id': 'T-HASH', 'name': 'Python hashlib SHA-256 implementation and collision resistance'},
        {'id': 'T-OS', 'name': 'OS, filesystem, process isolation and execution semantics', 'version': platform.platform()},
        {'id': 'T-HARDWARE', 'name': 'Execution hardware'},
        {'id': 'T-INTERPRETATION', 'name': 'Human interpretation of JSON prose and theorem statements; source elaboration, key serialization, auth and witness-validation interpretations explicitly excluded from implementation proof'}
    ]
    for item in tcb:
        item['classification'] = 'TRUSTED'
        item['justification'] = 'Outside the proved Lean model; declared reliance for this finite verification run.'
    write(root / 'closure/tcb.json', {'trusted_components': tcb})
    trust = [t['id'] for t in tcb]
    config = {
        'schema_version': '1.0', 'closure_id': args.closure_id,
        'status_policy': {'unresolved_is_blocking': True, 'warning_is_blocking': True, 'manual_override_allowed': False},
        'toolchain': c['formal_kernel']['lean_toolchain'], 'lean_installation': str(leanroot),
        'required_clean_builds': 2, 'required_trust': trust,
        'obligation_map': {o['id']: o['symbol'] for o in c['formal_obligations']},
        'witness_symbols': WITNESSES, 'allowed_axioms': ['propext', 'Quot.sound', 'Classical.choice'],
        'network': {'allowed_during_verification': False, 'enforcement': 'No external Lean packages or network operations invoked; OS network isolation is not certified.'},
        'llm': {'candidate_generation_only': True, 'proof_authority': False, 'final_verifier': False},
        'determinism': {'required': True, 'artifacts': ['*.olean', 'proof/audit output', 'projection', 'correspondence', 'provenance', 'claim_status_set'],
                        'excluded_nondeterministic_fields': ['temporary build directory', 'wall-clock timings in build logs', 'report timestamp', 'run ID', 'trace/cache metadata', '.ilean editor metadata']},
        'manifest_policy': 'All source/config/schema/claims/TCB/provenance/registry/review inputs selected by frozen policy.inputs. manifest.json excludes itself; input-root.json is a derived root binding and excluded to avoid self-reference. Reports/runs/build outputs are outputs, not inputs.',
        'closure_boundary': {
            'verified_surface': ['19 frozen Lean model propositions and six concrete witnesses', 'exact JSON formal_kernel projection', 'schema/proof-inventory binding, two clean deterministic builds', 'six final council records and specified model dispatches, not subjective approval as proof'],
            'trusted_surface': trust,
            'excluded_surface': ['any product implementation or runtime refinement', 'full Alloy relational/temporal semantics, parser, printer, SAT4J/Kodkod correctness', 'serialization/atom semantic identity, auth and witness validator implementation', 'UI, SQL/RLS, performance, process security and deployment', 'licensing clearance, market demand and commercial release', 'future revisions and unlisted claims'],
            'interpretation': 'VERIFIED means closure only of the frozen finite specification/model surface under declared trust; not assumption-free correctness or production readiness.'}
    }
    write(root / 'closure/closure-config.json', config)
    claims = claim_records(c, trust)
    write(root / 'closure/claims.json', {'claims': claims})
    write(root / 'closure/verifier-registry.json', {'verifiers': [{
        'id': 'V-ALLOW-SPEC', 'executable': 'closure/scripts/verify.py',
        'sha256': digest(root / 'closure/scripts/verify.py'),
        'claim_classes': ['proof_compilation_with_expected_proposition', 'mechanical_metadata_check'],
        'exit_codes': {'pass': 0, 'block': 1, 'infrastructure_failure': 2},
        'unexpected_exit_policy': 'INFRASTRUCTURE_FAILURE; never PASS'}]})
    # Materialize the provenance path before enumerating the complete input set.
    write(root / 'closure/provenance.json', {'bindings': []})
    paths = inputs(root)
    write(root / 'closure/provenance.json', {'bindings': provenance_records(claims, paths, trust)})
    manifest = {'schema_version': '1.0', 'files': [{'path': p, 'sha256': digest(root / p)} for p in paths]}
    write(root / 'closure/manifest.json', manifest)
    root_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    write(root / 'closure/input-root.json', {'closure_id': args.closure_id, 'input_root_hash': root_hash})
    print(json.dumps({'closure_id': args.closure_id, 'input_root_hash': root_hash,
                      'claims': len(claims), 'inputs': len(paths)}, indent=2))

if __name__ == '__main__':
    main()
