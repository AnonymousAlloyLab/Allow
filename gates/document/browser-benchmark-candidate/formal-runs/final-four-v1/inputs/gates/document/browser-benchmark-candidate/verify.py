#!/usr/bin/env python3
"""Verify four frozen abstract claims, not browser/runtime correspondence."""
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
HERE = Path(__file__).resolve().parent
REL = 'gates/document/browser-benchmark-candidate/'
REVIEWS = [f'reviews/browser-benchmark-{family}-{seat}.json' for family in ('terra', 'sol', 'astra') for seat in (1, 2)]
PINS = {REL+'protocol.json': '33975062c08d6b8fb7bf3cbe0f39cfaaeae3101d0e80154f2aaf0b33fce9dfb5', REL+'BrowserBenchmarkProtocol.lean': '57d8512a8bd483ff9bfa76d43e66c0963a90c8b3b9eb7751b9ff89d2df48a49c'}
TOOL = Path.home()/'.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    if result.returncode or 'warning:' in result.stdout.lower():
        raise RuntimeError('Command failed: '+result.stdout)
    return result.stdout


def main():
    out = HERE/'formal-runs'/'final-four-v1'
    if out.exists():
        raise RuntimeError('Run already exists')
    for path, pin in PINS.items():
        assert digest(ROOT/path) == pin, 'Candidate changed: '+path
    for path in REVIEWS:
        review = json.loads((ROOT/path).read_text())
        assert review['decision'] == 'APPROVE_GAMEPLAN' and review.get('input_hashes', review.get('input_sha256', review.get('inputs_sha256'))) == PINS, 'Approval mismatch: '+path
    paths = list(PINS)+REVIEWS+[REL+'types.json', REL+'verify.py', 'formal/lean-toolchain', 'formal/lakefile.toml', 'formal/lake-manifest.json']
    assert (ROOT/'formal/lean-toolchain').read_text().strip() == 'leanprover/lean4:v4.34.1'
    assert json.loads((ROOT/'formal/lake-manifest.json').read_text())['packages'] == []
    source = (ROOT/(REL+'BrowserBenchmarkProtocol.lean')).read_text()
    assert not re.search(r'\b(sorry|sorryAx|native_decide|implemented_by)\b|(?m:^\s*(axiom|unsafe|opaque|partial)\b)', source)
    registry = json.loads((ROOT/(REL+'types.json')).read_text())
    assert len(registry) == 4 and set(registry) == set(re.findall(r'(?m)^theorem\s+(\w+)', source))
    out.mkdir(parents=True)
    manifest = {path:digest(ROOT/path) for path in paths}
    for path in paths:
        target = out/'inputs'/path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/path, target)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    root_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    def check():
        for path, pin in manifest.items():
            assert digest(ROOT/path) == pin and digest(out/'inputs'/path) == pin, 'Input mutation: '+path
    check()
    builds = []
    env = dict(os.environ); env.pop('LEAN_PATH', None)
    for label in ('A', 'B'):
        check()
        with tempfile.TemporaryDirectory(prefix='allow-browser-model-') as temp:
            work = Path(temp)
            shutil.copyfile(out/'inputs'/(REL+'BrowserBenchmarkProtocol.lean'), work/'BrowserBenchmarkProtocol.lean')
            build = run([str(TOOL), '-o', 'BrowserBenchmarkProtocol.olean', 'BrowserBenchmarkProtocol.lean'], work, env)
            audit = 'import BrowserBenchmarkProtocol\n'+''.join('#check '+name+'\n#print axioms '+name+'\n' for name in registry)
            (work/'Audit.lean').write_text(audit)
            env2 = dict(env, LEAN_PATH=str(work))
            text = run([str(TOOL), 'Audit.lean'], work, env2)
            for name, expected in registry.items():
                assert expected in text, 'Exact type mismatch: '+name
            groups = re.findall(r'depends on axioms: \[([^]]*)\]', text)
            assert all(set(g.split(', ')) <= {'propext', 'Quot.sound', 'Classical.choice'} for g in groups)
            assert text.count('depends on axioms:')+text.count('does not depend on any axioms') == 4
            (out/(label+'-audit.log')).write_text(text)
            (out/(label+'-build.log')).write_text(build)
            builds.append({'olean_sha256':digest(work/'BrowserBenchmarkProtocol.olean'), 'audit_sha256':digest(out/(label+'-audit.log'))})
    check()
    assert builds[0] == builds[1], 'Non-deterministic artifact or audit'
    report = {'status':'VERIFIED', 'input_root_hash':root_hash, 'registered_claims':4, 'passed':4, 'builds':builds, 'trust':['Lean 4.34.1 kernel, elaborator and bundled libraries', 'reported allowed axioms only', 'Python verifier, SHA256, operating system and hardware'], 'scope':'Four abstract propositions only; phase count theorem is algebra over oneEdit.length, not a trace-length theorem. External p95 and validity are assumed; no runtime, browser, UI, percentile or prior 267-claim correspondence.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('BLOCKED_OR_INFRASTRUCTURE_FAILURE: '+str(error), file=sys.stderr)
        sys.exit(1)
