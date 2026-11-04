#!/usr/bin/env python3
"""Measure the frozen 500-node authoritative HTTP workload without solver time.

This reports the original 300 ms target honestly; a failure does not relax it.
Browser rendering and manual accessibility have separate evidence.
"""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time
import uuid

from smoke_documents import API, DocumentClient, digest, encoded, fingerprint, mutation

ROOT = Path(__file__).resolve().parents[1]


def server_fingerprint():
    """Bind the HTTP validator, fixture, and all compiled BuildIdentity inputs."""
    files, _ = fingerprint()
    files = {name: value for name, value in files.items()
             if not name.startswith('frontend/')}
    dependencies = list((ROOT/'backend/target/dependency').glob('*.jar'))
    dependencies += [ROOT/'backend/target/solver/alloy.jar', Path(__file__)]
    for path in dependencies:
        files[str(path.relative_to(ROOT))] = digest(path.read_bytes())
    fixture = ROOT/'gates/document/headless-preview-fixture.json'
    files[str(fixture.relative_to(ROOT))] = digest(fixture.read_bytes())
    return files, digest(encoded(dict(sorted(files.items()))))


def percentile(values, quantile):
    """Use the predeclared nearest-rank quantile for finite latency samples."""
    import math
    return sorted(values)[max(0, math.ceil(len(values)*quantile)-1)]


def main():
    """Measure 100 warmups and 1000 serial edits through the actual public validator."""
    files, source_root = server_fingerprint()
    fixture_path = ROOT/'gates/document/headless-preview-fixture.json'
    fixture = json.loads(fixture_path.read_text())
    source = fixture['source']
    draft_module = json.loads(encoded(fixture['module']).decode().replace('server:', 'draft:'))
    client = DocumentClient()
    initial, _ = client.call(API, {'idempotencyKey': str(uuid.uuid4()),
                                   'title': '500-node performance fixture'}, 'COMMITTED')
    path = API+'/'+initial['documentId']
    initial_candidate = {'mode': 'BLOCK_SUPPORTED', 'module': draft_module, 'presentationCopies': []}
    accepted, _ = client.call(path+'/commit', mutation(initial_candidate, 0), 'COMMITTED')
    module = accepted['artifact']['module']
    assert module is not None and len(module['nodes']) == 500
    source_preview = {'draftId': str(uuid.uuid4()), 'draftEpoch': 0, 'baseRevision': 1,
                      'candidate': {'mode': 'SOURCE', 'source': source}}
    checked, _ = client.call(path+'/validate', source_preview, 'VALIDATED')
    assert checked['supportMode'] == 'BLOCK_SUPPORTED' and checked['proposedSource'] == source
    candidate = {'mode': 'BLOCK_SUPPORTED', 'module': copy.deepcopy(module), 'presentationCopies': []}
    leaves = [node for node in candidate['module']['nodes'] if node['tag'] == 'signature_ref']
    signatures = [signature['id'] for signature in module['signatures']]
    assert len(signatures) == 2
    draft = str(uuid.uuid4())
    samples, failures, initial_observations = [], [], []
    identity_checks = []
    checkpoint = ROOT/'gates/document/server-performance-progress.json'
    for event in range(1100):
        node = leaves[event % len(leaves)]
        node['targetId'] = signatures[1] if node['targetId'] == signatures[0] else signatures[0]
        body = {'draftId': draft, 'draftEpoch': event, 'baseRevision': 1, 'candidate': candidate}
        start = time.perf_counter_ns()
        status, result, _ = client.raw(path+'/validate', encoded(body))
        elapsed = (time.perf_counter_ns()-start)/1000000
        if event < 10:
            initial_observations.append(elapsed)
        if status != 200 or result['status'] != 'VALIDATED':
            failures.append({'event': event, 'http': status, 'status': result and result['status']})
        if event >= 100:
            samples.append(elapsed)
        if event % 100 == 99:
            identity_checks.append({'completed_events': event+1,
                                    'unchanged': server_fingerprint()[1] == source_root})
            progress = {'status': 'INCOMPLETE', 'completed_events': event+1,
                        'measured_events': len(samples), 'samples_ms': samples,
                        'failures': failures, 'input_root_sha256': source_root,
                        'verifier_sha256': digest(Path(__file__).read_bytes()),
                        'identity_checks': identity_checks,
                        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                        'note': 'Checkpoint only; no complete-run or target acceptance claim.'}
            pending = checkpoint.with_suffix('.json.tmp')
            pending.write_text(json.dumps(progress, indent=2)+'\n')
            pending.replace(checkpoint)
            print(json.dumps({'completed': event+1, 'measured': len(samples), 'failures': len(failures)}), flush=True)
    p95 = percentile(samples, .95)
    unchanged = (server_fingerprint()[1] == source_root
                 and all(check['unchanged'] for check in identity_checks))
    report = {'status': 'PASS' if not failures and unchanged and p95 < 300 else 'FAIL',
              'classification': 'MEASURED_AUTHORITATIVE_HTTP_LATENCY_NOT_BROWSER_PERFORMANCE',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'node_count': 500,
              'fixture': 'Shared balanced167-leaf conjunction; 500 expression nodes, initial depth10',
              'shared_fixture_path': str(fixture_path.relative_to(ROOT)),
              'shared_fixture_sha256': digest(fixture_path.read_bytes()),
              'actual_sandbox_block_500_nodes_committed': True,
              'actual_sandbox_source_500_nodes_supported': True,
              'fixture_source_sha256': digest(source.encode()), 'warmups': 100, 'events': 1000,
              'method': 'serial exact HTTP requests; nearest-rank percentiles; full scoped read, worker, response included',
              'target_p95_ms': 300, 'p50_ms': percentile(samples, .5), 'p95_ms': p95,
              'p99_ms': percentile(samples, .99), 'mean_ms': statistics.mean(samples),
              'min_ms': min(samples), 'max_ms': max(samples), 'samples_ms': samples, 'failures': failures,
              'initial_series': {'samples_ms': initial_observations,
                                 'scope': 'First ten validation edits after accepted fixture setup; separate from measured warm series.',
                                 'cold_server_start': 'NOT_MEASURED; server and SQL proxy already running; each validation launches a fresh sandbox JVM.'},
              'reference_host': {'platform': platform.platform(), 'machine': platform.machine(),
                                 'logical_cpus': os.cpu_count(), 'python': platform.python_version(),
                                 'java': subprocess.run(['java', '-version'], capture_output=True, text=True).stderr.strip()},
              'input_root_sha256': source_root, 'source_unchanged': unchanged, 'source_sha256': files,
              'identity_checks': identity_checks,
              'verifier_sha256': digest(Path(__file__).read_bytes()),
              'limitations': ['Shared local host; no exclusive host or portable performance claim.',
                              'HTTP-only input manifest excludes frontend source but includes compiled static assets because BuildIdentity hashes them; no browser behavior is measured.',
                              'No browser/frame latency measured.', 'The original target remains binding if this run fails.']}
    (ROOT/'gates/document/server-performance.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ['status', 'events', 'p50_ms', 'p95_ms', 'p99_ms', 'source_unchanged']}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
