#!/usr/bin/env python3
"""Install and restore isolated test assets on the existing authenticated Spring origin.

Browser interaction and result capture remain separate. This never relaxes API authority.
"""
import argparse
import difflib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess

from smoke_documents import fingerprint

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT/'backend/target/classes/static'
DESTINATION = STATIC/'bench'


def digest(path):
    """Hash exact bytes for installation and restoration identity."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    """Bind every file in a task-owned tree by workspace-relative path."""
    return {p.relative_to(ROOT).as_posix(): digest(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}


def save(path, value):
    """Persist a public test report without launch authority or model bodies."""
    path.write_text(json.dumps(value, indent=2)+'\n')


def require_server_stopped():
    """Refuse asset mutation while this workspace's build-pinned server is alive."""
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            command = (process/'cmdline').read_bytes().split(b'\0')
            if b'dev.allow.backend.AllowApplication' in command:
                assert (process/'cwd').resolve() != ROOT/'backend', 'Stop the workspace server before changing static assets'
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue


def build_evidence(out, bundle):
    """Bind fresh transformation and generated assets, never copy an old asset manifest."""
    evidence = ROOT/'gates/document/browser-benchmark-candidate/build-evidence'
    target = out/'build-evidence'
    target.mkdir()
    original = (evidence/'DocumentWorkbench.original.txt').read_text()
    transformed = (evidence/'DocumentWorkbench.transformed.txt').read_text()
    assert original == (ROOT/'frontend/src/DocumentWorkbench.tsx').read_text()
    anchor = '  const {view,controller}=useController(props.token);'
    expected = "import {useBenchmarkCommit} from '../bench/bridge';\n" + original.replace(anchor, anchor+'\n  useBenchmarkCommit(controller,view);')
    assert original.count(anchor) == 1 and transformed == expected
    for name in ['DocumentWorkbench.original.txt', 'DocumentWorkbench.transformed.txt', 'hashes.json']:
        shutil.copyfile(evidence/name, target/name)
    difference = difflib.unified_diff(original.splitlines(True), transformed.splitlines(True), fromfile='production', tofile='instrumented')
    (target/'DocumentWorkbench.diff').write_text(''.join(difference))
    save(target/'asset-manifest.json', {'status': 'BUILT_BEFORE_INSTALL',
                                      'files': inventory(ROOT/'frontend/bench') | inventory(bundle)})


def install(out):
    """Add only a new bench subtree; preserve all existing production static bytes."""
    require_server_stopped()
    assert not out.exists() and not DESTINATION.exists(), 'Run or bench subtree already exists'
    bundle = ROOT/'frontend/dist/benchmark'
    assert (bundle/'bench/index.html').is_file(), 'Build the isolated bench Vite entry first'
    out.mkdir(parents=True)
    verifier = ROOT/'scripts/verify_browser_benchmark.py'
    protocol = ROOT/'gates/document/browser-benchmark-candidate/protocol.json'
    shutil.copyfile(verifier, out/'registered-verifier.py')
    shutil.copyfile(protocol, out/'protocol.json')
    save(out/'run-registration.json', {'verifier_sha256': digest(verifier),
                                      'protocol_sha256': digest(protocol),
                                      'warmup_events': 100, 'measured_events': 1000,
                                      'nodes': 500, 'strict_p95_target_ms': 50})
    prior = inventory(STATIC)
    sources, source_root = fingerprint()
    build_evidence(out, bundle)
    save(out/'source-manifest.json', {'input_root_sha256': source_root, 'source_sha256': sources})
    save(out/'harness-manifest.json', inventory(ROOT/'frontend/bench'))
    DESTINATION.mkdir()
    shutil.copytree(bundle/'assets', DESTINATION/'assets')
    shutil.copyfile(bundle/'bench/index.html', DESTINATION/'index.html')
    report = {'status': 'INSTALLED_TEST_ONLY', 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'preexisting_static': prior, 'installed': inventory(DESTINATION),
              'original_source_root': source_root, 'platform': platform.platform(),
              'java': subprocess.run(['java', '-version'], capture_output=True, text=True).stderr.strip(),
              'api_authority_changed': False, 'installer_sha256': digest(Path(__file__))}
    save(out/'installation.json', report)
    print('Benchmark installed. Start a fresh server, then use its private launch link with /bench/index.html.')


def restore(out):
    """Remove only unchanged installed test files and require original byte identity."""
    require_server_stopped()
    report = json.loads((out/'installation.json').read_text())
    assert inventory(DESTINATION) == report['installed'], 'Installed test assets changed; inspect before cleanup'
    prior = {name: value for name, value in inventory(STATIC).items()
             if not name.startswith('backend/target/classes/static/bench/')}
    assert prior == report['preexisting_static'], 'Production static files changed during test'
    shutil.rmtree(DESTINATION)
    current = fingerprint()[1]
    unchanged = current == report['original_source_root']
    save(out/'restoration.json', {'status': 'PASS' if unchanged else 'INPUT_MUTATION',
                                 'static_restored': inventory(STATIC) == prior,
                                 'source_unchanged': unchanged, 'current_input_root': current,
                                 'installer_sha256': digest(Path(__file__))})
    assert unchanged, 'Inputs changed during browser benchmark; result cannot close acceptance'
    print('Original static bytes and source manifest restored and matched')


def main():
    """Require a new explicit run name and one reversible asset lifecycle operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['install', 'restore'])
    parser.add_argument('run_id')
    args = parser.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', args.run_id), 'Invalid run ID'
    out = ROOT/'gates/document/browser-benchmark-runs'/args.run_id
    (install if args.operation == 'install' else restore)(out)


if __name__ == '__main__':
    main()
