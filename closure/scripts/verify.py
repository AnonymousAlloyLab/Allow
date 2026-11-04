#!/usr/bin/env python3
"""Finite specification/model closure. No product or implementation correctness claim.

Exit 0 = VERIFIED; 1 = BLOCKED; 2 = INFRASTRUCTURE_FAILURE.
Every source of PASS is this hashed, explicitly trusted verifier and the pinned
Lean checker; reviewer opinions are never proof evidence.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import jsonschema
from project_contract import render
from policy import inputs, claim_records, provenance_records, WITNESSES

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def read(path):
    return json.loads(Path(path).read_text())

def write(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

class Block(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message

def require(ok, code, message):
    if not ok:
        raise Block(code, message)

def run(args, cwd, env, logpath):
    result = subprocess.run(args, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    logpath.write_text(result.stdout)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    require(re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id), 'VERIFIER_FAILURE', 'Invalid run ID')
    out = root / 'closure/runs' / args.run_id
    if out.exists():
        print('Refusing to overwrite immutable evidence run', file=sys.stderr)
        return 2
    out.mkdir(parents=True)
    config = read(root / 'closure/closure-config.json')
    claims = read(root / 'closure/claims.json')['claims']
    registry = read(root / 'closure/verifier-registry.json')
    tcb = read(root / 'closure/tcb.json')
    manifest = read(root / 'closure/manifest.json')
    root_hash = hashlib.sha256(canonical(manifest)).hexdigest()
    verifier_hash = digest(Path(__file__).resolve())
    envinfo = {'platform': platform.platform(), 'python': sys.version,
               'jsonschema': importlib.metadata.version('jsonschema'),
               'toolchain': config['toolchain']}
    statuses = {}
    builds = []
    errors, infra = [], []
    summary = {'schema_version': '1.0', 'closure_id': config['closure_id'],
               'timestamp': datetime.now(timezone.utc).isoformat(), 'input_root_hash': root_hash,
               'execution_environment': envinfo, 'status': 'UNSET'}

    def evidence(cid, raw, evidence_status='PASS', exit_code=0):
        e = {'schema_version': '1.0', 'closure_id': config['closure_id'], 'claim_id': cid,
             'input_root_hash': root_hash, 'verifier_id': 'V-ALLOW-SPEC',
             'verifier_hash': verifier_hash, 'execution_environment': envinfo,
             'raw_result': raw, 'exit_code': exit_code, 'status': evidence_status}
        write(out / 'evidence' / (cid + '.json'), e)
        statuses[cid] = evidence_status

    try:
        root_record = read(root / 'closure/input-root.json')
        require(root_record == {'closure_id': config['closure_id'], 'input_root_hash': root_hash},
                'INPUT_MUTATION', 'Manifest root mismatch')
        paths = [f['path'] for f in manifest['files']]
        require(paths == sorted(set(paths)), 'INPUT_MUTATION', 'Unsorted or duplicate manifest paths')
        require(paths == inputs(root), 'INPUT_MUTATION', 'Manifest does not cover the exact verification input set')
        for f in manifest['files']:
            path = root / f['path']
            require(path.is_file() and not path.is_symlink() and digest(path) == f['sha256'],
                    'INPUT_MUTATION', f['path'])
        require(registry['verifiers'][0]['sha256'] == verifier_hash,
                'STALE_OR_UNBOUND_EVIDENCE', 'Verifier hash differs')
        require(registry['verifiers'][0]['exit_codes'] == {'pass': 0, 'block': 1, 'infrastructure_failure': 2},
                'VERIFIER_FAILURE', 'Exit contract differs')
        for dep in tcb['trusted_components']:
            require(dep['classification'] == 'TRUSTED', 'UNDECLARED_DEPENDENCY', dep['id'])
            if 'path' in dep:
                require(digest(dep['path']) == dep['sha256'], 'INPUT_MUTATION', dep['path'])
        require({d['id'] for d in tcb['trusted_components']} == set(config['required_trust']),
                'UNDECLARED_DEPENDENCY', 'TCB set differs')
        contract = read(root / 'spec/allow-contract.json')
        schema = read(root / 'spec/allow-contract.schema.json')
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(contract, schema)
        obligations = contract['formal_obligations']
        require(claims == claim_records(contract, config['required_trust']),
                'CLAIM_MUTATION', 'Claim records differ from unique deterministic verifier policy')
        require(len({o['id'] for o in obligations}) == len(obligations),
                'AMBIGUOUS_CORRESPONDENCE', 'Duplicate obligation IDs')
        require(len({o['symbol'] for o in obligations}) == len(obligations),
                'AMBIGUOUS_CORRESPONDENCE', 'Duplicate theorem symbols')
        require([i['id'] for i in contract['user_invariants']] == ['U0','U1','U2','U3','U4','U5'],
                'UNMAPPED_IMPLEMENTATION_OBJECT', 'User invariant list differs')
        require(not contract['product']['implementation_authorized_in_this_phase'],
                'SCOPE_LEAK', 'Unexpected product implementation authorization')
        require({o['id']: o['symbol'] for o in obligations} == config['obligation_map'],
                'CLAIM_MUTATION', 'Obligation mapping differs from frozen configuration')
        evidence('C20', {'schema_valid': True, 'invariants': 6, 'unique_obligations': len(obligations)})
        require(render(contract) == (root / 'formal/Allow/Generated.lean').read_text(),
                'UNMAPPED_IMPLEMENTATION_OBJECT', 'JSON projection differs')
        evidence('C21', {'generated_projection_matches': True,
                         'projection_sha256': digest(root / 'formal/Allow/Generated.lean'),
                         'interpretation': 'Exact formal_kernel constants only; prose semantics are not compiled.'})

        leanfiles = sorted((root / 'formal').glob('**/*.lean'))
        leanfiles = [p for p in leanfiles if '.lake' not in p.parts]
        banned = r'(?m)^\s*(?:axiom|opaque|unsafe|partial)\b|\b(?:sorry|sorryAx|native_decide|implemented_by)\b'
        for p in leanfiles:
            # Comments are also conservatively checked: no hidden proof escape text.
            require(re.search(banned, p.read_text()) is None, 'VERIFIER_FAILURE',
                    'Forbidden proof escape in ' + str(p.relative_to(root)))
        require(read(root / 'formal/lake-manifest.json')['packages'] == [],
                'UNDECLARED_DEPENDENCY', 'External Lean packages present')
        require((root / 'formal/lean-toolchain').read_text().strip() == config['toolchain'],
                'INPUT_MUTATION', 'Toolchain version differs')
        witness_symbols = config['witness_symbols']
        require(witness_symbols == WITNESSES, 'MISSING_WITNESS', 'Witness inventory differs')
        symbols = [o['symbol'] for o in obligations] + witness_symbols
        expected_types = read(root / 'closure/theorem-types.json')
        require(set(expected_types) == set(symbols), 'UNMAPPED_IMPLEMENTATION_OBJECT', 'Expected proposition inventory differs')
        audit = 'import Allow\n' + '\n'.join(
            'example : (' + expected_types[s] + ') := @' + s + '\n#check ' + s +
            '\n#print axioms ' + s for s in symbols) + '\n'
        write(out / 'correspondence.json', [{'id': o['id'], 'symbol': o['symbol'],
             'scope': 'Lean theorem, not implementation refinement'} for o in obligations])
        (out / 'Audit.lean').write_text(audit)
        toolroot = Path(config['lean_installation'])
        require((toolroot / 'bin/lake').is_file(), 'UNDECLARED_DEPENDENCY', 'Pinned lake unavailable')
        env = os.environ.copy()
        env['PATH'] = str(toolroot / 'bin') + os.pathsep + env.get('PATH', '')
        env['ELAN_TOOLCHAIN'] = config['toolchain']
        env.pop('LEAN_PATH', None)
        all_outputs = []
        for label in ['A', 'B']:
            with tempfile.TemporaryDirectory(prefix='allow-proof-' + label + '-') as tmp:
                work = Path(tmp) / 'formal'
                work.mkdir()
                for f in manifest['files']:
                    if f['path'].startswith('formal/'):
                        target = work / Path(f['path']).relative_to('formal')
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(root / f['path'], target)
                result = run([str(toolroot / 'bin/lake'), 'build'], work, env, out / ('build-' + label + '.log'))
                require(result.returncode == 0 and 'warning:' not in result.stdout.lower(),
                        'CLEAN_BUILD_FAILURE', 'Build ' + label + ' failed or warned')
                (work / 'Audit.lean').write_text(audit)
                checked = run([str(toolroot / 'bin/lake'), 'env', 'lean', 'Audit.lean'],
                              work, env, out / ('audit-' + label + '.log'))
                require(checked.returncode == 0 and 'warning:' not in checked.stdout.lower(),
                        'VERIFIER_FAILURE', 'Theorem audit failed or warned in ' + label)
                axioms = set()
                for group in re.findall(r'depends on axioms: \[([^\]]*)\]', checked.stdout):
                    axioms.update(a.strip() for a in group.split(',') if a.strip())
                require(axioms <= set(config['allowed_axioms']), 'UNDECLARED_DEPENDENCY',
                        'Unexpected logical axiom: ' + repr(sorted(axioms)))
                for symbol in symbols:
                    require(symbol in checked.stdout, 'UNMAPPED_IMPLEMENTATION_OBJECT', symbol)
                artifacts = {str(p.relative_to(work)): digest(p) for p in
                             sorted((work / '.lake/build/lib/lean').rglob('*.olean'))}
                require(bool(artifacts), 'CLEAN_BUILD_FAILURE', 'No Lean artifacts')
                metadata = {
                    'proof_inventory': [{'symbol': s, 'expected_proposition': expected_types[s]} for s in symbols],
                    'correspondence': [{'id': o['id'], 'symbol': o['symbol'],
                                        'expected_proposition': expected_types[o['symbol']]} for o in obligations],
                    'provenance': provenance_records(claims, paths, config['required_trust']),
                    'claim_status_set': {o['id']: 'PASS' for o in obligations}}
                write(out / ('metadata-' + label + '.json'), metadata)
                result_data = {'label': label, 'input_root_hash': root_hash, 'exit_code': 0,
                               'artifacts': artifacts, 'axioms': sorted(axioms),
                               'audit_sha256': hashlib.sha256(checked.stdout.encode()).hexdigest(),
                               'projection_sha256': digest(work / 'Allow/Generated.lean'),
                               'correspondence_sha256': digest(out / 'correspondence.json'),
                               'metadata_sha256': hashlib.sha256(canonical(metadata)).hexdigest()}
                builds.append(result_data)
                all_outputs.append(checked.stdout)
        for field in ['artifacts', 'axioms', 'audit_sha256', 'projection_sha256', 'correspondence_sha256', 'metadata_sha256']:
            require(builds[0][field] == builds[1][field], 'NONDETERMINISM', field)
        for o in obligations:
            evidence(o['id'], {'symbol': o['symbol'], 'clean_builds': ['A', 'B'],
                     'audit_logs': ['audit-A.log', 'audit-B.log'], 'axioms': builds[0]['axioms'],
                     'classification': 'PROVED_MODEL', 'statement': o['statement']})
        evidence('C22', {'witnesses': witness_symbols, 'valid': len(witness_symbols),
                         'method': 'Named kernel-checked concrete acceptance/rejection proofs in both builds'})
        evidence('C23', {'clean_builds': builds, 'determinism': 'PASS',
                         'compared': ['proof inventory', 'compiled olean hashes', 'correspondence',
                                      'generated projection', 'logical axiom set']})
        evidence('C24', {'source_escape_scan': 'PASS', 'allowed_axioms': config['allowed_axioms'],
                         'observed_axioms': builds[0]['axioms'], 'external_lean_packages': 0})
        council = read(root / 'reviews/council-summary.json')
        contract_hash = digest(root / 'spec/allow-contract.json')
        expected = contract['review_council']['requested_models']
        require(set(council['members']) == set(expected), 'VERIFIER_FAILURE', 'Council roster mismatch')
        for seat, model in expected.items():
            m = council['members'][seat]
            require(m['dispatch_model'] == model and m['contract_sha256'] == contract_hash,
                    'STALE_OR_UNBOUND_EVIDENCE', 'Council binding for ' + seat)
            require(digest(root / m['report']) == m['report_sha256'],
                    'STALE_OR_UNBOUND_EVIDENCE', 'Council report hash for ' + seat)
            report_obj = read(root / m['report'])
            require(report_obj.get('final_review', {}).get('contract_sha256') == contract_hash,
                    'STALE_OR_UNBOUND_EVIDENCE',
                    'Final contract hash absent in reviewer report ' + seat)
            require(str(report_obj.get('reviewer', report_obj.get('reviewer_id'))).lower() == seat,
                    'STALE_OR_UNBOUND_EVIDENCE', 'Reviewer identity mismatch ' + seat)
        evidence('C25', {'report_count': 6, 'model_dispatches': expected,
                         'runtime_backend_identity': 'Not independently attested',
                         'classification': 'CHECKED_REVIEW_RECORDS_NOT_PROOF_EVIDENCE'})
        provenance = read(root / 'closure/provenance.json')
        require(provenance['bindings'] == provenance_records(claims, paths, config['required_trust']),
                'ORPHAN_CLAIM', 'Provenance must match complete public/evidence/input/trust bindings')
        claim_ids = {c['id'] for c in claims}
        require(set(statuses) == claim_ids, 'VERIFIER_NOT_RUN', 'Unrun or extra claims')
        require({p['claim_id'] for p in provenance['bindings']} == claim_ids,
                'ORPHAN_CLAIM', 'Provenance not total')
        require(len(provenance['bindings']) == len(claim_ids), 'ORPHAN_CLAIM', 'Ambiguous provenance')
        for p in provenance['bindings']:
            require(p['verifier'] == 'V-ALLOW-SPEC' and set(p['inputs']) <= set(paths)
                    and set(p['trusted_dependencies']) <= set(config['required_trust']),
                    'ORPHAN_CLAIM', 'Bad provenance binding ' + p['claim_id'])
        # Detect mutation during builds, including reviewer updates and verifier edits.
        for f in manifest['files']:
            require(digest(root / f['path']) == f['sha256'], 'INPUT_MUTATION', f['path'])
        summary['status'] = 'VERIFIED'
    except Block as err:
        errors.append({'code': err.code, 'message': err.message})
        summary['status'] = 'BLOCKED'
    except jsonschema.ValidationError as err:
        errors.append({'code': 'VERIFIER_FAILURE', 'message': 'Schema: ' + err.message})
        summary['status'] = 'BLOCKED'
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError) as err:
        infra.append({'code': 'INFRASTRUCTURE_ERROR', 'type': type(err).__name__, 'message': str(err)})
        summary['status'] = 'INFRASTRUCTURE_FAILURE'
    for claim in claims:
        if claim['id'] not in statuses:
            evidence(claim['id'], {'reason': 'Not discharged', 'blocking_reasons': errors,
                                  'infrastructure_errors': infra}, 'BLOCK', 1)
    total = len(claims)
    passed = sum(s == 'PASS' for s in statuses.values())
    ok = summary['status'] == 'VERIFIED'
    summary.update({
        'claims': {'total': total, 'passed': passed, 'blocked': total - passed, 'unresolved': 0},
        'correspondence': {'required_objects': len(config['obligation_map']),
                          'mapped_objects': len(config['obligation_map']) if ok else 0,
                          'unmapped_objects': 0 if ok else len(config['obligation_map']),
                          'ambiguous_objects': 0,
                          'implementation_objects': 0,
                          'interpretation': 'JSON constants and theorem inventory; no Java/React implementation exists.'},
        'witnesses': {'required': len(config['witness_symbols']),
                     'valid': len(config['witness_symbols']) if statuses.get('C22') == 'PASS' else 0,
                     'invalid': 0 if statuses.get('C22') == 'PASS' else len(config['witness_symbols'])},
        'builds': {'required': 2, 'passed': len(builds), 'records': builds},
        'determinism': {'required': True, 'status': 'PASS' if statuses.get('C23') == 'PASS' else 'BLOCK'},
        'provenance': {'public_claims': total, 'fully_bound': total if ok else 0,
                       'orphan_claims': 0 if ok else total},
        'dependencies': {'verified': ['formal model obligations'] if ok else [],
                         'trusted': config['required_trust'], 'undeclared': []},
        'blocking_reasons': errors, 'infrastructure_errors': infra,
        'closure_boundary': config['closure_boundary'],
        'decision': {'valid_states': ['VERIFIED', 'BLOCKED', 'INFRASTRUCTURE_FAILURE'],
                     'manual_override_allowed': False},
        'evidence_directory': str(out.relative_to(root))})
    write(out / 'closure-report.json', summary)
    write(root / 'closure/reports/closure-report.json', summary)
    print(json.dumps({'status': summary['status'], 'claims': summary['claims'],
                      'input_root_hash': root_hash, 'blocking_reasons': errors,
                      'infrastructure_errors': infra}, indent=2))
    return {'VERIFIED': 0, 'BLOCKED': 1, 'INFRASTRUCTURE_FAILURE': 2}[summary['status']]

if __name__ == '__main__':
    raise SystemExit(main())
