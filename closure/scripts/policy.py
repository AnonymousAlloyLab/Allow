"""Frozen finite verifier policy shared by package preparation and execution."""
AUXILIARY = {
    'C20': 'Contract conforms to schema, retains six user invariants, and has unique frozen obligations.',
    'C21': 'Formal-kernel JSON deterministically regenerates the identical Lean constants.',
    'C22': 'Six concrete non-vacuity witnesses inhabit the frozen expected Lean propositions.',
    'C23': 'Two isolated clean builds agree on proof inventory, correspondence, projection and olean hashes.',
    'C24': 'Lean source and axiom audit contains no prohibited proof escapes or undeclared axioms.',
    'C25': 'Six council reports are bound to the final contract and requested model dispatch roster; opinions are not proof.'
}
WITNESSES = ['Allow.accepted_formula_witness', 'Allow.rejected_bad_drop_witness',
             'Allow.accepted_commit_witness', 'Allow.visible_evidence_witness',
             'Allow.admitted_pools_witness', 'Allow.nontrivial_canonical_witness']

def inputs(root):
    paths = []
    for pattern in ['spec/*.json', 'formal/*.lean', 'formal/Allow/*.lean',
                    'closure/*.json', 'closure/scripts/*.py', 'reviews/*.json']:
        paths.extend(p for p in root.glob(pattern) if p.name not in ['manifest.json', 'input-root.json'])
    paths.extend(root / 'formal' / p for p in ['lean-toolchain', 'lakefile.toml', 'lake-manifest.json'])
    return sorted(set(str(p.relative_to(root)) for p in paths))

def claim_records(contract, trust):
    obligations = contract['formal_obligations']
    result = []
    for o in obligations:
        result.append({'id': o['id'], 'statement': o['statement'], 'symbol': o['symbol'],
                       'claim_class': 'proof_compilation_with_expected_proposition',
                       'verifier': 'V-ALLOW-SPEC', 'severity': 'blocking',
                       'pass_condition': 'Both isolated Lean builds check the frozen expected proposition and allowed axioms.',
                       'block_conditions': ['missing_or_different_proposition', 'build_failure', 'undeclared_axiom'],
                       'trusted_dependencies': trust})
    for cid, statement in AUXILIARY.items():
        result.append({'id': cid, 'statement': statement, 'symbol': None,
                       'claim_class': 'mechanical_metadata_check', 'verifier': 'V-ALLOW-SPEC',
                       'severity': 'blocking', 'pass_condition': 'The registered deterministic verifier predicate returns true.',
                       'block_conditions': ['predicate_false', 'unresolved', 'missing_evidence'],
                       'trusted_dependencies': trust})
    return result

def provenance_records(claims, paths, trust):
    return [{'claim_id': c['id'], 'public_claim': c['statement'],
             'public_target': 'closure/claims.json#' + c['id'],
             'evidence_template': 'closure/runs/{run_id}/evidence/' + c['id'] + '.json',
             'verifier': 'V-ALLOW-SPEC', 'inputs': paths, 'trusted_dependencies': trust}
            for c in claims]
