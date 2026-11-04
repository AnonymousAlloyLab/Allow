#!/usr/bin/env python3
"""Finite frozen user-scope probe using unchanged real BubblewrapLauncher isolation."""
import argparse
import json
from pathlib import Path
import re
import sys
import time

import attached_preflight as shared
import containment
import controller
import scope_launch
from harness_common import HERE, digest, read_private, root_hash, validate_root, write_private

shared.PROGRAMS += ('scope_launch.py', 'scope_preflight.py', 'test_scope_launch.py', 'test_cleanup_capture.py')


def collect(manifest, known, snapshots):
    """Retain every observed scope incarnation and fail any kernel resource exhaustion."""
    snapshot = scope_launch.observe(manifest, list(known.values()))
    for row in snapshot['processes']:
        identity = {key: row[key] for key in ('pid', 'start_ticks')}
        known[(identity['pid'], identity['start_ticks'])] = identity
    snapshots.append(snapshot)
    if containment.exhausted(snapshot):
        raise ValueError('scope_oom_or_pids_exhaustion')


def execute(arguments):
    """Run one frozen idle placement, real sandbox worker and exact owned-group cleanup."""
    run = arguments.run.resolve()
    if not run.is_relative_to(HERE/'runs') or run == HERE/'runs':
        raise ValueError('registered_scope_run_required')
    manifest = read_private(run/'manifest.json')
    if manifest['kind'] != 'CALLER_CONTEXT_SCOPE_PREFLIGHT' or root_hash(manifest) != manifest['input_root_sha256']:
        raise ValueError('scope_manifest_root')
    if not re.fullmatch('allow-ft1-[0-9a-f]{32}\\.scope', manifest['unit']):
        raise ValueError('unique_scope_required')
    validate_root(manifest['copied_root'])
    root = shared.verify(manifest)
    write_private(run/'execution-started.json', {'input_root_sha256': manifest['input_root_sha256']})
    report = {'status': 'BLOCKED', 'input_root_sha256': manifest['input_root_sha256'],
              'classification': 'SCOPE_REAL_WORKER_PREFLIGHT_ONLY', 'benchmark_executed': False,
              'snapshots': [], 'verifier_sha256': digest(Path(__file__))}
    launched, child, known = None, None, {}
    try:
        launched, child = scope_launch.launch(manifest, sys.executable,
                           ['-B', root/'.gate/attached_preflight.py', 'owner', '--root', root], 90)
        deadline = time.monotonic() + 40
        while not (root/'.gate/worker-complete.json').exists():
            collect(manifest, known, report['snapshots'])
            if child.poll() is not None or time.monotonic() > deadline:
                raise ValueError('scope_worker_deadline_or_exit')
            time.sleep(.02)
        report['worker'] = shared.check_worker(root, manifest, known)
        report['placement'] = read_private(root/'.gate/scope-placement.json')
        report['owner'] = read_private(root/'.gate/scoped-owner.json')
        collect(manifest, known, report['snapshots'])
        shared.verify(manifest)
        report['checks_passed_before_cleanup'] = True
    except Exception as error:
        report['failure_class'] = type(error).__name__
        report['blocking_reason'] = str(error) if type(error) is ValueError else 'scope_preflight_failed'
    finally:
        controller.finish_execution(run, root, manifest, launched, known, report, child)
    return {'status': report['status'], 'report': str(run/'report.json')}


def main():
    """Separate scope registration from execution; print only bounded public report metadata."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('freeze', 'execute'))
    parser.add_argument('--run-id')
    parser.add_argument('--run', type=Path)
    parser.add_argument('--source-ready', type=Path)
    parser.add_argument('--tool-manifest', type=Path)
    args = parser.parse_args()
    args.scope = True
    result = shared.freeze(args) if args.operation == 'freeze' else execute(args)
    print(json.dumps(result))
    return 1 if result['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
