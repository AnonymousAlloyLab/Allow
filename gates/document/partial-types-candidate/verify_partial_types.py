#!/usr/bin/env python3
"""Verify 280 exact formal propositions in two fresh pinned Lean builds.

This registers model compilation only. Parser/runtime correspondence is excluded.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'gates/document/draft/verify_document_candidate.py'
module_spec = importlib.util.spec_from_file_location('prior_document_verifier', BASE)
helpers = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(helpers)
PINS = {'gates/document/partial-types-candidate/contract.json': '1d286937e571071160ee3f4494c99f451edd3a983b73b3e21d6565b6b29ff216', 'gates/document/partial-types-candidate/PartialTypes.lean': 'b7fb8ab650de500be591f13b5ffd296728daf94d7cb3977090c77f8af9a747f7', 'gates/document/partial-types-candidate/types.json': 'dbd4d0d4d9697de048c163d193fad5663a7e4ddec65ff486d65d4a4b38cf554a', 'gates/document/partial-types-candidate/tests-plan.json': '88a00a18b730b6a6fbddf2b98167cc283a8055c0806892158897925d8dcd26be'}
PARENT_PINS = {
    'formal/Allow/Document.lean': 'a9ce61793dc79676395211cd8e5d94c0e0767316755040224f63f2a1af3b3b07',
    'gates/document/draft/types.json': 'fd0a31b549a8c20d079b960f68b306603b66aaed3facfd2e4a4bc302ea336109',
    'formal/Allow/FieldOrder.lean': '6bebf364f90286cbea205d488073cef5bb1bfda099b138e7c41b699be5b9e3a0',
    'gates/document/order-amendment/types.json': '8bd4640dc2b7cf0a178a08b5de02e9f20cdaf7a0d128471202711833f9e14563',
    'spec/document-stage-draft.json': '957b8a798ebaaa2b824433305e6cdbd965d9422acb94482b9dba11db291f2368',
    'spec/document-wire-draft.json': '12de31cd26209ddc2dfb628520cf8f0bb61cadacec6c9dd3cb8571d0e573f08a',
    'spec/document-ui-draft.json': '5358d97fb8ccb755a1182223e81cfbd08eff3d7c06a39922474ae8fd20c1a66c',
    'spec/document-adapter-draft.json': 'ea0047534c4c811d87b99ed25460366d1ddec9c55d5f8f52109d8be70621a4a0',
    'spec/document-field-order.json': '9943997f71d63e9f4666b80299b3d25bcb3d5237e5aea673bbc7b3bbb6115870'}
PARENT_PINS.update({'spec/document-associativity.json': 'b7a60034b650bb75dc8a1d160d8312ccbc3f8d1449b2554290e0db9748045d1b', 'formal/Allow/Associativity.lean': 'b0e003ebd07a530eabec1edd241f17a940505fb538e870a2ce3015bbe2849316', 'gates/document/associativity-amendment/types.json': '0d8f95224108d094f8c54df6a7f6fdd260faa2ea61e42aca02dcaf09556efce7'})
REGISTRIES = [
    ('document', 'Allow.DocumentDraft', 'formal/Allow/Document.lean', 'gates/document/draft/types.json', 125),
    ('order', 'Allow.DocumentOrder', 'formal/Allow/FieldOrder.lean', 'gates/document/order-amendment/types.json', 14),
    ('associativity', 'Allow.DocumentAssociativity', 'formal/Allow/Associativity.lean',
     'gates/document/associativity-amendment/types.json', 16)]
REGISTRIES.append(('partial', 'Allow.DocumentPartialTypes', 'gates/document/partial-types-candidate/PartialTypes.lean', 'gates/document/partial-types-candidate/types.json', 13))
REVIEWS = [f'reviews/document-partial-types-{family}-{seat}.json' for family in ('terra','sol','astra') for seat in (1,2)]
TRUST = ['Lean4.34.1 kernel, elaborator, pretty-printer and bundled libraries',
         'propext, Quot.sound and Classical.choice only when reported by the axiom audit',
         'Lake, Python verifier and pinned inherited helper', 'SHA256 collision resistance',
         'Operating system, filesystem, processes and hardware', 'Interpretation of the abstract formal model']
EXCLUDED = ['Java/TypeScript/SQL refinement and implementation correctness',
            'Alloy parser/printer and concrete source-map correspondence',
            'Generic weighted-subtree depth, actual JVM stack safety and latency',
            'Browser/accessibility acceptance, complete G2/G3 and commercial release']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def execute(command, cwd, environment, log):
    result = subprocess.run(command, cwd=cwd, env=environment, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=180)
    log.write_text(result.stdout)
    require(result.returncode == 0, 'CLEAN_BUILD_FAILURE:'+log.name)
    require('warning:' not in result.stdout.lower(), 'WARNING:'+log.name)
    return result.stdout


def registries():
    """Retain every inherited exact statement and mechanically enumerate all new theorem names."""
    inherited = {}
    for name in helpers.INHERITED:
        require(sha(ROOT/name) == helpers.INHERITED_HASHES[name], 'INHERITED_REGISTRY_CHANGED:'+name)
        rows = json.loads((ROOT/name).read_text())
        require(not set(rows).intersection(inherited), 'DUPLICATE_INHERITED')
        inherited.update(rows)
    require(len(inherited) == 112, 'INHERITED_COUNT')
    groups = {'inherited': inherited}
    for label, namespace, source, path, count in REGISTRIES:
        registry = json.loads((ROOT/path).read_text())
        require(sha(ROOT/source) == registry['source_sha256'], 'REGISTRY_SOURCE_CHANGED:'+source)
        rows = registry['theorem_types']
        names = re.findall(r'(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)', (ROOT/source).read_text())
        require(len(rows) == count and len(names) == len(set(names)) and set(names) == set(rows), 'REGISTRY_COVERAGE:'+label)
        groups[label] = {namespace+'.'+key: value for key, value in rows.items()}
    return groups


def clean_build(label, out, groups, tool, environment):
    """Build only preserved inputs; install the candidate into the fresh formal tree explicitly."""
    with tempfile.TemporaryDirectory(prefix='allow-associativity-clean-') as temporary:
        work = Path(temporary)/'formal'
        shutil.copytree(out/'inputs/formal', work)
        shutil.copyfile(out/'inputs/gates/document/partial-types-candidate/PartialTypes.lean', work/'Allow/PartialTypes.lean')
        with (work/'Allow.lean').open('a') as stream:
            stream.write('\nimport Allow.PartialTypes\n')
        execute([str(tool/'lake'), 'build'], work, environment, out/f'{label}-build.log')
        audits = {}
        for group, rows in groups.items():
            types = 'import Allow\n'
            if group == 'inherited':
                types += '\n'.join('example : ('+statement+') := @'+name for name, statement in rows.items())+'\n'
            else:
                types += '\n'.join('#check '+name for name in rows)+'\n'
            axioms = 'import Allow\n'+'\n'.join('#print axioms '+name for name in rows)+'\n'
            for kind, source in [('types',types), ('axioms',axioms)]:
                filename = group+'-'+kind+'.lean'
                (work/filename).write_text(source)
                output = execute([str(tool/'lake'),'env','lean',filename], work, environment, out/f'{label}-{group}-{kind}.log')
                if kind == 'axioms':
                    helpers.check_axioms(output, list(rows))
                elif group != 'inherited':
                    require(output == '\n'.join(rows.values())+'\n', 'EXACT_TYPE_MISMATCH:'+group)
                audits[group+'-'+kind] = hashlib.sha256(output.encode()).hexdigest()
        artifacts = {p.relative_to(work).as_posix(): sha(p) for p in sorted(work.rglob('*.olean'))}
        require('Allow/PartialTypes.olean' in {p.replace('.lake/build/lib/lean/', '') for p in artifacts}, 'MISSING_CANDIDATE_ARTIFACT')
        return {'label': label, 'artifact_sha256': artifacts, 'audit_sha256': audits}


def check_inputs(out, entries):
    """Verify original and preserved bytes; the frozen snapshot is the only build source."""
    for row in entries:
        if row['path'].startswith('generated/'):
            require(sha(out/row['path'][10:]) == row['sha256'], 'GENERATED_INPUT_MUTATION:'+row['path'])
        else:
            require(sha(ROOT/row['path']) == row['sha256'], 'INPUT_MUTATION:'+row['path'])
            require(sha(out/'inputs'/row['path']) == row['sha256'], 'SNAPSHOT_MUTATION:'+row['path'])


def approval_inputs(review):
    """Canonicalize exact workspace paths without accepting aliases or duplicate inputs."""
    result = {}
    for name, digest in review['input_hashes'].items():
        path = Path(name)
        canonical = path.relative_to(ROOT).as_posix() if path.is_absolute() else path.as_posix()
        require(canonical in PINS and canonical not in result, 'INVALID_REVIEW_INPUT:'+name)
        result[canonical] = digest
    return result


def main():
    """Freeze finite claims, trust and verifiers before compiling; unknown or stale evidence blocks."""
    require(len(sys.argv) == 2 and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sys.argv[1]), 'INVALID_RUN_ID')
    out = HERE/'formal-runs'/sys.argv[1]
    require(not out.exists(), 'EXISTING_RUN')
    out.mkdir(parents=True)
    report = {'closure_id': 'allow-document-partial-types-'+sys.argv[1], 'status': 'UNSET',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'input_root_hash': None,
              'claims': {'total':280,'passed':0,'unresolved':280}, 'builds': [],
              'blocking_reasons': [], 'infrastructure_errors': [], 'trusted': TRUST, 'excluded': EXCLUDED,
              'correspondence': {'required':0,'note':'Formal compilation only; no implementation correspondence claim'},
              'interpretation': 'VERIFIED applies only to the frozen280-proposition model surface under declared trust.'}
    try:
        for path, expected in (PINS | PARENT_PINS).items():
            require(sha(ROOT/path) == expected, 'INPUT_MUTATION:'+path)
        for path in REVIEWS:
            review = json.loads((ROOT/path).read_text())
            require(review['decision'] == 'APPROVE_GAMEPLAN' and approval_inputs(review) == PINS, 'MISSING_EXACT_APPROVAL:'+path)
        groups = registries()
        guards = json.loads((HERE/'preimplementation-guards.json').read_text())['source_sha256']
        for path, expected in guards.items():
            require(sha(ROOT/path) == expected, 'PREIMPLEMENTATION_GUARD_CHANGED:'+path)
        formal = [p for p in (ROOT/'formal').rglob('*.lean') if '.lake' not in p.parts]
        for path in formal+[HERE/'PartialTypes.lean']:
            require(not helpers.ESCAPE.search(path.read_text()), 'FORBIDDEN_CONSTRUCT:'+str(path))
        require(json.loads((ROOT/'formal/lake-manifest.json').read_text())['packages'] == [], 'UNDECLARED_LEAN_PACKAGE')
        paths = set(formal)|{ROOT/p for p in PINS | PARENT_PINS}|{ROOT/p for p in REVIEWS}|{ROOT/p for p in guards}
        paths |= {ROOT/p for p in helpers.INHERITED}|{ROOT/r[3] for r in REGISTRIES}
        paths |= {Path(__file__), BASE, HERE/'preimplementation-guards.json', HERE/'lean-inventory.json', ROOT/'gates/document/headless-preview-fixture.json'}
        paths |= {ROOT/'formal'/p for p in ['lean-toolchain','lakefile.toml','lake-manifest.json']}
        claims = [{'id':group+':'+name,'statement':statement,'verifier':'V-LEAN-EXACT',
                   'pass_condition':'Exact registered type and allowed axiom closure pass in both matching clean builds',
                   'witness': 'witness' in name or '.fixture_' in name}
                  for group, rows in groups.items() for name, statement in rows.items()]
        require(len(claims) == len({c['id'] for c in claims}) == 280, 'CLAIM_COUNT')
        save(out/'claims.json', claims)
        save(out/'tcb.json', {'trusted':TRUST,'excluded':EXCLUDED})
        save(out/'config.json', {'required_clean_builds':2,'determinism':True,'manual_override':False,
                                'transformation':'Copy pinned candidate to Allow/PartialTypes.lean and append its import in fresh build only',
                                'nondeterministic':['timestamp','temporary paths','build duration']})
        save(out/'verifier-registry.json', {'id':'V-LEAN-EXACT','implementation_sha256':sha(__file__),
                                         'helper_sha256':sha(BASE),'exit_codes':{'pass':0,'block':1,'infrastructure_failure':2}})
        entries = [{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sorted(paths)]
        entries += [{'path':'generated/'+name,'sha256':sha(out/name)} for name in ['claims.json','tcb.json','config.json','verifier-registry.json']]
        manifest = {'schema_version':'1.0','files':sorted(entries,key=lambda row:row['path'])}
        root = hashlib.sha256(packed(manifest)).hexdigest()
        report['input_root_hash'] = root
        save(out/'manifest.json',manifest)
        for path in paths:
            target = out/'inputs'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path,target)
        check_inputs(out, entries)
        tool = Path.home()/'.elan/toolchains/leanprover--lean4---v4.34.1/bin'
        environment = dict(os.environ, PATH=str(tool)+os.pathsep+os.environ.get('PATH',''))
        environment.pop('LEAN_PATH',None)
        report['environment'] = {'platform':platform.platform(),'python':sys.version,'lean':'4.34.1'}
        for label in ('A','B'):
            check_inputs(out, entries)
            report['builds'].append(clean_build(label,out,groups,tool,environment))
        a,b = report['builds']
        require(a['artifact_sha256'] == b['artifact_sha256'] and a['audit_sha256'] == b['audit_sha256'], 'NONDETERMINISM')
        check_inputs(out, entries)
        require(set(formal) == {p for p in (ROOT/'formal').rglob('*.lean') if '.lake' not in p.parts}, 'FORMAL_INVENTORY_CHANGED')
        report.update(status='VERIFIED', determinism='PASS', witnesses={'required':sum(c['witness'] for c in claims),'all_checked':True})
        report['claims'].update(passed=280,unresolved=0)
        evidence = [{'closure_id':report['closure_id'],'claim_id':c['id'],'input_root_hash':root,
                     'verifier_id':'V-LEAN-EXACT','verifier_sha256':sha(__file__),'environment':report['environment'],
                     'status':'PASS','exit_code':0,'raw_result':'Exact types, allowed axioms and reproducible compiled artifacts in two clean builds',
                     'logs':[f'{label}-{c["id"].split(":")[0]}-{kind}.log' for label in ('A','B') for kind in ('types','axioms')]}
                    for c in claims]
        save(out/'evidence.json',evidence)
        save(out/'provenance.json',[{'public_claim':c['id'],'claim_id':c['id'],'evidence':'evidence.json',
                                    'verifier':'V-LEAN-EXACT','inputs':'manifest.json','trusted':TRUST} for c in claims])
    except AssertionError as failure:
        report['status']='BLOCKED';report['blocking_reasons'].append(str(failure))
    except Exception as failure:
        report['status']='INFRASTRUCTURE_FAILURE';report['infrastructure_errors'].append(type(failure).__name__+': '+str(failure))
    save(out/'report.json',report)
    print(json.dumps({key:report[key] for key in ['status','input_root_hash','claims','blocking_reasons','infrastructure_errors']},indent=2))
    return {'VERIFIED':0,'BLOCKED':1,'INFRASTRUCTURE_FAILURE':2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
