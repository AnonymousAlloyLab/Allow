#!/usr/bin/env python3
"""Check finite browser benchmark records; never infer cold, AT or server acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

from smoke_documents import fingerprint

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = '33975062c08d6b8fb7bf3cbe0f39cfaaeae3101d0e80154f2aaf0b33fce9dfb5'


def sha(path):
    """Hash exact source or evidence bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    """Read one retained JSON record without fabricating missing fields."""
    return json.loads(path.read_text())


def require(condition, reason):
    """Fail the bounded audit with a stable reason."""
    if not condition:
        raise ValueError(reason)


def verify_files(files):
    """Require every workspace-relative manifest entry to retain its exact bytes."""
    require(bool(files), 'EMPTY_MANIFEST')
    for name, expected in files.items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'UNSAFE_MANIFEST_PATH')
        require(sha(ROOT/path) == expected, 'INPUT_MUTATION:'+name)


def verify_identity(raw):
    """Check recorded checkpoints; the hashed runtime harness enforces intermediate continuity."""
    initial, fixture, final = (raw[key] for key in ('initialIdentity', 'fixtureIdentity', 'finalIdentity'))
    for field in ('documentId', 'acceptedRevision', 'headRevision', 'baseRevision', 'draftId'):
        require(initial[field] is not None and initial[field] == fixture[field] == final[field], 'IDENTITY_CHANGED:'+field)
    for field in ('contentGeneration', 'draftEpoch'):
        require(fixture[field] == initial[field]+1 and final[field] == fixture[field]+1100, 'EDIT_SEQUENCE_CHANGED:'+field)
    require(initial['commitSequence'] < fixture['commitSequence'] < final['commitSequence'], 'COMMIT_SEQUENCE')
    require(raw['continuityChecks'] == 1100, 'MISSING_CONTINUITY_CHECKS')
    advisory = raw['advisory']
    require(advisory['status'] == 'SETTLED_OBSERVED', 'ADVISORY_NOT_OBSERVED')
    for field in ('documentId', 'baseRevision', 'draftId', 'draftEpoch', 'contentGeneration'):
        require(advisory['identity'][field] == final[field], 'ADVISORY_IDENTITY:'+field)
    require(advisory['resource']['start'] >= raw['finalDispatchMs'], 'ADVISORY_PRECEDES_FINAL_EDIT')
    require(bool(advisory['notice']) and 'diagnostics' in advisory and 'rejectionDiagnostics' in advisory, 'MISSING_ADVISORY_OUTCOME')


def verify_context(raw, host):
    """Check recorded host/browser metadata and bounded resource coverage, without physical-display claims."""
    require(host['java_exit_code'] == 0 and host['ram_bytes'] > 0 and host['logical_cpus'] > 0, 'HOST_METADATA')
    require(host['cpu_model'] != 'unavailable' and bool(host['platform']) and bool(host['java_version']), 'HOST_METADATA')
    environment = raw['environment']
    for field in ('browser', 'hardwareConcurrency', 'deviceMemoryGiB', 'viewport', 'devicePixelRatio', 'screen', 'screenColorDepth', 'physicalDisplayRefresh'):
        require(field in environment, 'MISSING_BROWSER_CONTEXT:'+field)
    require(environment['visibility'] == 'visible' and not raw['visibility'] and not raw['errors'], 'BROWSER_INTERRUPTION')
    intervals = raw['refreshIntervalsMs']
    require(len(intervals) == 12 and all(math.isfinite(x) and x > 0 for x in intervals), 'FRAME_CONTEXT')
    coverage = raw['resourceCoverage']
    require(coverage['complete'] and coverage['supported'] and coverage['statusFieldSupported'] and coverage['droppedFieldObserved'], 'RESOURCE_COVERAGE_UNKNOWN')
    require(not coverage['browserBufferFull'] and not coverage['observerOverflow'] and coverage['droppedEntries'] == 0 and coverage['unknownStatusCount'] == 0, 'RESOURCE_COVERAGE_LOST')
    require(0 < coverage['entryCount'] == len(raw['resources']) <= coverage['limit'], 'RESOURCE_COUNT')
    require(all(type(row['responseStatus']) is int and row['responseStatus'] > 0 for row in raw['resources']), 'UNKNOWN_RESOURCE_STATUS')


def verify_run(out):
    """Check exact warm fixture, samples, installed build bindings and source restoration."""
    registration = read(out/'run-registration.json')
    require(registration == {'verifier_sha256': sha(Path(__file__)), 'protocol_sha256': PROTOCOL,
                             'warmup_events': 100, 'measured_events': 1000, 'nodes': 500,
                             'strict_p95_target_ms': 50}, 'REGISTRATION_CHANGED')
    require(sha(out/'registered-verifier.py') == sha(Path(__file__)) and sha(out/'protocol.json') == PROTOCOL, 'REGISTERED_INPUT_MUTATION')
    raw = read(out/'browser-result.json')
    require(raw['status'] == 'COMPLETE', 'INCOMPLETE_BROWSER_RUN')
    for key, length in [('samples', 1000), ('warmupSamples', 100)]:
        require(len(raw[key]) == length and all(type(x) in (float, int) and math.isfinite(x) and x >= 0 for x in raw[key]), 'INVALID_SAMPLES:'+key)
    fixture = raw['fixture']
    require(fixture['expressionNodes'] == 500 and fixture['maximumDepth'] <= 32 and fixture['sourceUtf8Bytes'] <= 32768, 'FIXTURE_BOUNDS')
    require(fixture['fileSha256'] == sha(ROOT/'gates/document/headless-preview-fixture.json'), 'FIXTURE_CHANGED')
    require(fixture['warmupEvents'] == 100 and fixture['measuredEvents'] == 1000, 'FIXTURE_COUNTS')
    authored = read(ROOT/'gates/document/headless-preview-fixture.json')
    source = authored['source'].encode('utf8')
    require(fixture['sourceUtf8Bytes'] == len(source) and fixture['sourceSha256'] == hashlib.sha256(source).hexdigest(), 'FIXTURE_SOURCE')
    for key, value in [('editSequenceSha256', authored['edits']), ('nodeIdsSha256', [node['id'] for node in authored['module']['nodes']])]:
        encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf8')
        require(fixture[key] == hashlib.sha256(encoded).hexdigest(), 'FIXTURE_SEQUENCE:'+key)
    verify_identity(raw)
    verify_context(raw, read(out/'host.json'))
    original = read(out/'source-manifest.json')
    require(fingerprint()[1] == original['input_root_sha256'], 'SOURCE_MANIFEST_CHANGED')
    verify_files(original['source_sha256'])
    verify_files(read(out/'harness-manifest.json'))
    assets = read(out/'build-evidence/asset-manifest.json')['files']
    verify_files(assets)
    installation = read(out/'installation.json')
    for name, expected in installation['installed'].items():
        relative = name.removeprefix('backend/target/classes/static/bench/')
        built = 'frontend/dist/benchmark/'+('bench/index.html' if relative == 'index.html' else relative)
        require(assets.get(built) == expected, 'INSTALLED_ASSET_MISMATCH:'+name)
    restoration = read(out/'restoration.json')
    require(restoration['status'] == 'PASS' and restoration['source_unchanged'] and restoration['static_restored'], 'RESTORATION_FAILED')
    protocol = ROOT/'gates/document/browser-benchmark-candidate/protocol.json'
    require(sha(protocol) == PROTOCOL, 'PROTOCOL_CHANGED')
    ordered = sorted(raw['samples'])
    for key, index in [('p50', 499), ('p95', 949), ('p99', 989)]:
        require(raw['statistics'][key] == ordered[index], 'PERCENTILE_MISMATCH:'+key)
    require(raw['statistics']['classification'] == ('PASS' if ordered[949] < 50 else 'FAIL'), 'CLASSIFICATION_MISMATCH')
    return raw, ordered


def main():
    """Record a bounded audit result even when evidence is incomplete or the target fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    args = parser.parse_args()
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.run_id)), 'INVALID_RUN_ID')
    out = ROOT/'gates/document/browser-benchmark-runs'/args.run_id
    result = {'status': 'INCOMPLETE', 'classification': 'FINITE_ACTUAL_BROWSER_WARM_PREVIEW_ONLY',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'verifier_sha256': sha(Path(__file__)),
              'protocol_sha256': PROTOCOL, 'cold_series': 'NOT_CONDUCTED',
              'limitations': ['Hashed harness assertions and browser records are trusted runtime test evidence, not a formal implementation refinement.',
                              'Two sequential animation callbacks do not establish physical display paint.',
                              'Server-host CPU/RAM is recorded separately; browser hardware affinity is not attested.',
                              'No cold-start, authoritative diagnostics, manual accessibility, complete G2/G3 or commercial acceptance claim.']}
    try:
        raw, samples = verify_run(out)
        result.update(status='PASS' if samples[949] < 50 else 'FAIL', nodes=500, warmup_events=100,
                      measured_events=1000, p50_ms=samples[499], p95_ms=samples[949], p99_ms=samples[989],
                      target_p95_ms=50, source_unchanged=True, static_restored=True,
                      input_root_sha256=read(out/'source-manifest.json')['input_root_sha256'])
    except (ValueError, KeyError, TypeError, OSError) as error:
        result['reason'] = str(error)
    result['evidence_sha256'] = {path.relative_to(out).as_posix():sha(path) for path in sorted(out.rglob('*'))
                                 if path.is_file() and path.name != 'report.json'}
    (out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status', 'p50_ms', 'p95_ms', 'p99_ms', 'reason') if key in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
