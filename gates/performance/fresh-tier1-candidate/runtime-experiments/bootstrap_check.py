#!/usr/bin/env python3
"""Frozen noncomparative original500 bootstrap check in the final owned scope lane."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import controller
import installation
import scope_launch
from harness_common import HERE, clean_environment, digest, read_private, write_private


def prepare(arguments):
    """Prepare a separately used fresh root and preregister exactly three HTTP setup attempts."""
    result = installation.prepare(arguments)
    run = HERE/'runs'/arguments.run_id
    manifest = read_private(run/'manifest.json')
    write_private(run/'bootstrap-registration.json', {'classification': 'BOOTSTRAP_ONLY_NOT_SELECTION_EVIDENCE',
                  'installation_root_sha256': manifest['input_root_sha256'], 'verifier_sha256': digest(Path(__file__)),
                  'expected': ['actual owned scoped stack ready', 'create revision0', 'commit exact original500 revision1',
                               'SOURCE exact fixture bytes', 'raw setup replay PASS', 'unchanged installed inputs',
                               'terminal counters and positive empty cleanup'],
                  'comparative_samples': 0, 'warmups': 0})
    return result


def driver(arguments):
    """Issue only the frozen bootstrap operations; this process stays outside the server scope."""
    root = arguments.root
    sys.path.insert(0, str(root/'scripts'))
    from smoke_documents import DocumentClient
    from http_driver import bootstrap
    from http_setup import verify_setup
    output = arguments.run/'http-private'
    output.mkdir(mode=0o700, exist_ok=False)
    result = {'status': 'BLOCKED', 'classification': 'BOOTSTRAP_ONLY_NOT_SELECTION_EVIDENCE', 'warmups': 0, 'measured': 0}
    try:
        bootstrap(DocumentClient(), root, output)
        _, _, receipt = verify_setup(root, output, read_private(root/'.gate/manifest.json'))
        result.update(status='PASS', correspondence=receipt)
    except Exception as error:
        result.update(failure_class=type(error).__name__, reason=str(error) if type(error) in (ValueError, AssertionError) else 'bootstrap_operation_failed')
    write_private(arguments.run/'bootstrap-driver.json', result)
    return result


def outside_driver(root, run, manifest, known, snapshots):
    """Observe stack descendants while the separate finite setup driver runs."""
    log = os.open(run/'bootstrap-driver-private.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(log, 'wb') as stream:
        child = subprocess.Popen([root/'.tools/retrieval-venv/bin/python', '-B', root/'.gate/bootstrap_check.py',
                                 'driver', '--root', root, '--run', run], cwd=root,
                                 env=clean_environment(root), stdout=stream, stderr=stream, umask=0o077)
        deadline = time.monotonic() + 100
        try:
            while child.poll() is None:
                controller.collect(manifest, known, snapshots)
                if time.monotonic() >= deadline:
                    raise ValueError('bootstrap_driver_deadline')
                time.sleep(.02)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
    result = read_private(run/'bootstrap-driver.json')
    if child.returncode or result.get('status') != 'PASS':
        raise ValueError('bootstrap_driver_failed')
    return result


def execute(arguments):
    """Run the frozen whole-stack/bootstrap obligations with no comparative measurements."""
    run, manifest = controller.read_run(arguments.run)
    root = installation.verify(manifest)
    registration = read_private(run/'bootstrap-registration.json')
    if registration['verifier_sha256'] != digest(Path(__file__)) or registration['installation_root_sha256'] != manifest['input_root_sha256']:
        raise ValueError('bootstrap_registration_changed')
    controller.require_preflight(arguments.preflight)
    write_private(run/'bootstrap-started.json', {'registration_sha256': digest(run/'bootstrap-registration.json'),
                  'preflight_report_sha256': digest(arguments.preflight/'report.json')})
    report = {'status': 'BLOCKED', 'input_root_sha256': manifest['input_root_sha256'],
              'classification': 'BOOTSTRAP_ONLY_NOT_SELECTION_EVIDENCE', 'benchmark_executed': False,
              'snapshots': [], 'verifier_sha256': digest(Path(__file__))}
    launched, launcher, known = None, None, {}
    try:
        launched, launcher = scope_launch.launch(manifest, root/'.tools/retrieval-venv/bin/python',
                                               [root/'.gate/stack_owner.py'], 300)
        report['readiness'] = controller.wait_witness(root, manifest, known, report['snapshots'], False)
        report['bootstrap'] = outside_driver(root, run, manifest, known, report['snapshots'])
        controller.collect(manifest, known, report['snapshots'])
        installation.verify(manifest, fresh=False)
        report['checks_passed_before_cleanup'] = True
    except Exception as error:
        report.update(failure_class=type(error).__name__, blocking_reason=str(error) if type(error) is ValueError else 'bootstrap_check_failed')
    finally:
        controller.finish_execution(run, root, manifest, launched, known, report, launcher)
    return {'status': report['status'], 'report': str(run/'report.json')}


def main():
    """Separate fresh preparation, frozen execution and outside-group setup driver."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'execute', 'driver'))
    parser.add_argument('--run-id')
    parser.add_argument('--source-ready', type=Path)
    parser.add_argument('--preflight', type=Path)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    result = {'prepare': prepare, 'execute': execute, 'driver': driver}[args.operation](args)
    if args.operation != 'driver':
        print(json.dumps(result))
    return 1 if result.get('status') == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
