#!/usr/bin/env python3
"""Run one fixed semantic variant inside control; no HTTP or timing workload."""
import os
from pathlib import Path
import signal
import subprocess
import time

import probe_owner
from harness_common import clean_environment, digest, process_identity, read_private, write_private


def command(root, manifest, variant):
    """Select only the declared semantic probe and its finite registered variant."""
    if variant not in {'W0', 'W1'}:
        raise ValueError('semantic_variant_required')
    target = root/'backend/target'
    classpath = ':'.join(map(str, (root/'.gate/probe-classes', target/'classes', target/'dependency/*', target/'solver/alloy.jar')))
    return [manifest['java']['executable'], '-Xms32m', '-Xmx256m', '-XX:+UseSerialGC',
            '-XX:ActiveProcessorCount=4', '-cp', classpath, 'dev.allow.backend.WarmSemanticProbeMain',
            '--runtime-root', str(root), '--variant', variant, '--manifest', str(root/'.gate/semantic-fixtures.json'),
            '--report', str(root/'.gate/evidence/semantic-java.json')]


def run(root, manifest, launch):
    """Retain bounded private diagnostics and every incomplete execution attempt."""
    evidence = root/'.gate/evidence'
    descriptor = os.open(evidence/'semantic-private.log', os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    child, result = None, {'status': 'BLOCKED', 'variant': launch['variant'], 'started_monotonic_ns': time.monotonic_ns()}
    try:
        with os.fdopen(descriptor, 'wb') as log:
            child = subprocess.Popen(command(root, manifest, launch['variant']), cwd=root/'backend',
                                     env=clean_environment(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, umask=0o077)
            result['probe_identity'] = process_identity(child.pid)
            write_private(evidence/'semantic-started.json', result)
            result['log_bytes'] = probe_owner.bounded_output(child, log, 600)
        result['exit_code'] = child.returncode
        if (evidence/'semantic-java.json').is_file():
            result['java_report_sha256'] = digest(evidence/'semantic-java.json')
        if child.returncode == 0 and 'java_report_sha256' in result:
            result['status'] = 'COMPLETE'
    except Exception as error:
        result['failure_class'] = type(error).__name__
    finally:
        if child is not None:
            probe_owner.terminate(child)
            result['probe_reaped'] = child.poll() is not None
        result['finished_monotonic_ns'] = time.monotonic_ns()
        write_private(evidence/'semantic-complete.json', result)


def main():
    """Hold the owned scope open for independent terminal collection after the probe exits."""
    root = Path(__file__).resolve().parent.parent
    manifest = read_private(root/'.gate/manifest.json')
    launch = read_private(root/'.gate/evidence/semantic-launch.json')
    if launch['installation_root'] != manifest['input_root_sha256']:
        raise ValueError('semantic_launch_installation_binding')
    os.umask(0o077)
    write_private(root/'.gate/evidence/owner.json', {'identity': process_identity(os.getpid()),
                  'input_root_sha256': manifest['input_root_sha256']})
    run(root, manifest, launch)
    while True:
        signal.pause()


if __name__ == '__main__':
    main()
