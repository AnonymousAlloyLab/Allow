#!/usr/bin/env python3
"""Frozen copied-stack failure diagnosis; never comparative or selection evidence."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import containment
import controller
import installation
import stack_owner
from harness_common import (HERE, clean_environment, digest, process_identity, read_private, record,
                            same_process, write_private)

CHANGED = ('backend/src/main/java/dev/allow/backend/DocumentController.java',
           'backend/src/main/java/dev/allow/backend/FrameProcess.java',
           'backend/target/classes/dev/allow/backend/DocumentController.class',
           'backend/target/classes/dev/allow/backend/FrameProcess.class')


def instrument(root, java, rows, run):
    """Declare and compile only two private diagnostic insertions in a new copied target."""
    before = {row['path']: row['sha256'] for row in rows}
    edits = [(CHANGED[0], 'ResponseEntity<byte[]> failure(Exception failure) throws IOException {',
              'ResponseEntity<byte[]> failure(Exception failure) throws IOException {\n        failure.printStackTrace(System.err);'),
             (CHANGED[1], '            error.get(2, TimeUnit.SECONDS);',
              '            byte[] diagnosticError = error.get(2, TimeUnit.SECONDS);'),
             (CHANGED[1], '            writer.get(2, TimeUnit.SECONDS);',
              '            if (child.exitValue() != 0) {\n                System.err.write(bytes);\n'
              '                System.err.write(diagnosticError);\n            }\n'
              '            writer.get(2, TimeUnit.SECONDS);')]
    for name, old, new in edits:
        source = (root/name).read_text()
        if source.count(old) != 1:
            raise ValueError('diagnostic_exact_patch_anchor')
        (root/name).write_text(source.replace(old, new, 1))
    compile_diagnostics(root, java, run)
    changed = sorted(name for name, value in before.items() if digest(root/name) != value)
    if changed != sorted(CHANGED):
        raise ValueError('diagnostic_unexpected_source_class_delta')
    frame = HERE/'fixtures-final-r2/source-supported.json'
    copied = root/'.gate/diagnostic-source-supported.json'
    shutil.copyfile(frame, copied)
    rows.append(record(copied, root))
    return {'classification': 'DIAGNOSTIC_ONLY_NOT_SELECTION_EVIDENCE',
            'delta': [{'path': name, 'before_sha256': before[name], 'after_sha256': digest(root/name)} for name in changed],
            'frame': {'path': str(copied.relative_to(root)), 'sha256': digest(frame)},
            'behavior': 'Private exception trace and existing bounded stdout/stderr retention on nonzero child exit only; actual launch/fences/flags/deadlines/reap unchanged'}


def compile_diagnostics(root, java, run):
    """Compile only the copied controller/transport with fixed Java17 options and bounded logs."""
    target = root/'backend/target'
    with tempfile.TemporaryDirectory(prefix='allow-ft1-diag-javac-') as temporary:
        work = Path(temporary)
        (work/'classes').mkdir()
        (work/'empty').mkdir()
        argv = [str(Path(java['home'])/'bin/javac'), '--release', '17', '-g', '-parameters', '-proc:none',
                '-implicit:none', '-encoding', 'UTF-8', '-sourcepath', str(work/'empty'), '-classpath',
                os.pathsep.join(map(str, [target/'classes', target/'solver/alloy.jar', *sorted((target/'dependency').glob('*.jar'))])),
                '-d', str(work/'classes'), str(root/CHANGED[0]), str(root/CHANGED[1])]
        result = subprocess.run(argv, capture_output=True, timeout=60, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        save_bytes(run/'diagnostic-javac.stdout', result.stdout)
        save_bytes(run/'diagnostic-javac.stderr', result.stderr)
        if result.returncode:
            raise ValueError('diagnostic_compilation_failed')
        outputs = [path for path in (work/'classes').rglob('*') if path.is_file()]
        names = {str(path.relative_to(work/'classes')) for path in outputs}
        expected = {'dev/allow/backend/DocumentController.class', 'dev/allow/backend/FrameProcess.class',
                    'dev/allow/backend/FrameProcess$Writer.class'}
        if names != expected:
            raise ValueError('diagnostic_compiler_output_inventory')
        for path in outputs:
            destination = target/'classes'/path.relative_to(work/'classes')
            if path.name == 'FrameProcess$Writer.class':
                command = [str(Path(java['home'])/'bin/javap'), '-c', '-p']
                left = subprocess.run(command+[str(destination)], capture_output=True, check=True, timeout=15).stdout
                right = subprocess.run(command+[str(path)], capture_output=True, check=True, timeout=15).stdout
                if left != right:
                    raise ValueError('diagnostic_nested_writer_instructions_changed')
                continue
            destination.write_bytes(path.read_bytes())


def save_bytes(path, data):
    """Write exact bounded private diagnostics without exposing their contents."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)


def prepare(arguments):
    """Freeze fresh diagnostic source/target/frame/bytecode inputs before starting any service."""
    run = HERE/'runs'/arguments.run_id
    result = installation.prepare(arguments, transform=lambda root, java, rows: instrument(root, java, rows, run))
    manifest = read_private(run/'manifest.json')
    registration = {'classification': 'DIAGNOSTIC_ONLY_NOT_SELECTION_EVIDENCE',
                    'installation_root_sha256': manifest['input_root_sha256'],
                    'verifier_sha256': digest(Path(__file__)), 'expected_http_attempts_max': 3,
                    'required_observations': ['r2 actual launch/FrameProcess outcome and owned reap',
                                              'create and original500 commit raw private replies',
                                              'private copied-controller exception/transport stderr',
                                              'exact containment and explicit empty-group cleanup'],
                    'worker_flags_or_deadlines_changed': False, 'production_modified': False}
    write_private(run/'diagnostic-registration.json', registration)
    return result


def probe(root, manifest):
    """Run the fixed r2 probe through the actual launcher and transport in the service group."""
    classpath = os.pathsep.join(map(str, [root/'.gate/probe-classes', root/'backend/target/classes',
                                        root/'backend/target/dependency/*']))
    argv = [manifest['java']['executable'], '-Xms128m', '-Xmx1024m', '-XX:MaxMetaspaceSize=256m',
            '-XX:ReservedCodeCacheSize=128m', '-XX:ActiveProcessorCount=4', '-cp', classpath,
            'dev.allow.backend.FreshTier1ProbeMain', '--target', str(root/'backend/target'), '--profile', 'F0',
            '--input', str(root/'.gate/diagnostic-source-supported.json'),
            '--output', str(root/'.gate/evidence/direct-worker.json')]
    stack_owner.private_run(root, 'direct-worker', argv, 30)


def owner(arguments):
    """Start the fresh stack plus a fixed worker witness under one owned cgroup."""
    root = arguments.root.resolve()
    manifest = read_private(root/'.gate/manifest.json')
    os.environ.clear()
    os.environ.update(clean_environment(root))
    os.umask(0o077)
    write_private(root/'.gate/evidence/owner.json', {'identity': process_identity(os.getpid()),
                  'input_root_sha256': manifest['input_root_sha256'], 'started_monotonic_ns': time.monotonic_ns()})
    try:
        corpus = stack_owner.bootstrap(root)
        probe(root, manifest)
        spring, token = stack_owner.launch_spring(root, manifest)
        ready = stack_owner.wait_ready(root, manifest, corpus, spring, token)
        ready.update(status='READY', input_root_sha256=manifest['input_root_sha256'])
        write_private(root/'.gate/evidence/ready.json', ready)
        while spring.poll() is None and all(same_process(ready[name]) for name in ('proxy', 'postgres')):
            time.sleep(.2)
        raise RuntimeError('diagnostic_owned_service_lost')
    except Exception as error:
        write_private(root/'.gate/evidence/failure.json', {'class': type(error).__name__, 'status': 'BLOCKED'})
        save_bytes(root/'.gate/evidence/owner-trace-private.log', traceback.format_exc().encode())
        raise SystemExit(1)


def http_attempt(client, route, body, expected, output, name):
    """Retain every setup request/reply before validating status, including the observed 503."""
    from http_driver import encode
    raw = encode(body)
    save_bytes(output/(name+'-request.json'), raw)
    code, reply, response = client.raw(route, raw)
    save_bytes(output/(name+'-response.json'), response)
    observed = {'name': name, 'http_status': code, 'status': reply.get('status') if isinstance(reply, dict) else None,
                'request_sha256': digest(output/(name+'-request.json')), 'response_sha256': digest(output/(name+'-response.json'))}
    return observed, reply['data'] if code == 200 and isinstance(reply, dict) and reply.get('status') == expected else None


def http_setup(root, run):
    """Reproduce only original synthetic creation, commit and optional SOURCE setup; no load loop."""
    sys.path.insert(0, str(root/'scripts'))
    from smoke_documents import DocumentClient
    from http_driver import encode, identifier
    output = run/'diagnostic-http-private'
    fixture = json.loads((root/'gates/document/headless-preview-fixture.json').read_text())
    client = DocumentClient()
    body = {'idempotencyKey': identifier('create'), 'title': '500-node performance fixture'}
    first, created = http_attempt(client, '/api/v1/documents', body, 'COMMITTED', output, 'create')
    rows = [first]
    if created is None:
        return rows
    route = '/api/v1/documents/' + created['documentId']
    module = json.loads(encode(fixture['module']).decode().replace('server:', 'draft:'))
    body = {'idempotencyKey': identifier('commit'), 'expectedRevision': 0,
            'candidate': {'mode': 'BLOCK_SUPPORTED', 'module': module, 'presentationCopies': []}}
    second, committed = http_attempt(client, route+'/commit', body, 'COMMITTED', output, 'commit')
    rows.append(second)
    if committed is not None:
        body = {'draftId': identifier('source'), 'draftEpoch': 0, 'baseRevision': 1,
                'candidate': {'mode': 'SOURCE', 'source': fixture['source']}}
        third, _ = http_attempt(client, route+'/validate', body, 'VALIDATED', output, 'source')
        rows.append(third)
    return rows


def execute(arguments):
    """Execute the frozen diagnostic with explicit readiness, private observations and owned cleanup."""
    run, manifest = controller.read_run(arguments.run)
    root = installation.verify(manifest, fresh=True)
    registration = read_private(run/'diagnostic-registration.json')
    if not manifest.get('diagnostic') or registration['verifier_sha256'] != digest(Path(__file__)):
        raise ValueError('frozen_diagnostic_required')
    if registration['installation_root_sha256'] != manifest['input_root_sha256']:
        raise ValueError('diagnostic_root_binding')
    controller.require_preflight(arguments.preflight)
    write_private(run/'diagnostic-started.json', {'registration_sha256': digest(run/'diagnostic-registration.json'),
                  'preflight_manifest_sha256': digest(arguments.preflight/'manifest.json')})
    report = {'status': 'BLOCKED', 'run_id': manifest['run_id'], 'input_root_sha256': manifest['input_root_sha256'],
              'classification': 'DIAGNOSTIC_ONLY_NOT_SELECTION_EVIDENCE', 'verifier_sha256': digest(Path(__file__)),
              'snapshots': [], 'benchmark_executed': False, 'host': controller.host_observation(root)}
    known, launched = {}, None
    try:
        launched = containment.launch(manifest, root/'.tools/retrieval-venv/bin/python',
                                     [root/'.gate/diagnostic_stack.py', 'owner', '--root', root], 300)
        report['readiness'] = controller.wait_witness(root, manifest, known, report['snapshots'], False)
        report['http_attempts'] = http_setup(root, run)
        report['worker_probe'] = read_private(root/'.gate/evidence/direct-worker.json')
        controller.collect(manifest, known, report['snapshots'])
        installation.verify(manifest, fresh=False)
        report['checks_passed_before_cleanup'] = True
    except Exception as error:
        report['failure_class'] = type(error).__name__
        report['blocking_reason'] = str(error) if type(error) is ValueError else 'diagnostic_operation_failed'
        save_bytes(run/'diagnostic-controller-private.log', traceback.format_exc().encode())
    finally:
        controller.finish_execution(run, root, manifest, launched, known, report)
    return {'report': str(run/'report.json'), 'status': report['status'], 'classification': report['classification']}


def main():
    """Expose distinct authoring/execution/owned-supervisor actions; print no private content."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'execute', 'owner'))
    parser.add_argument('--run-id')
    parser.add_argument('--source-ready', type=Path)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--preflight', type=Path)
    arguments = parser.parse_args()
    try:
        result = {'prepare': prepare, 'execute': execute, 'owner': owner}[arguments.operation](arguments)
        if result is not None:
            print(json.dumps(result))
        return 1 if result is not None and result.get('status') == 'BLOCKED' else 0
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'failure_class': type(error).__name__,
                          'reason': str(error) if type(error) is ValueError else 'diagnostic_failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
