#!/usr/bin/env python3
"""Own one bounded component series inside the already delegated control leaf."""
import os
from pathlib import Path
import signal
import subprocess
import time

import probe_owner
from harness_common import clean_environment, digest, process_identity, read_private, record, write_private


def concrete_plan(root, manifest, launch):
    """Resolve only registered path expressions after actual kernel delegation exists."""
    plan = dict(launch['plan'])
    config = read_private(root/'.runtime/warm-pool/config.json')
    if launch['installation_root'] != manifest['input_root_sha256']:
        raise ValueError('latency_launch_installation_binding')
    group = Path(config['cgroupRoot'])
    info = group.stat()
    if info.st_dev != config['rootDevice'] or info.st_ino != config['rootInode']:
        raise ValueError('latency_concrete_cgroup_identity')
    plan.update(fixture=str(root/'.gate/latency-fixture.json'), cgroupRoot=str(group), cpuStat=str(group/'cpu.stat'))
    if digest(plan['fixture']) != plan['fixtureSha256']:
        raise ValueError('latency_concrete_fixture_changed')
    write_private(root/'.gate/evidence/latency-plan.json', plan)
    return plan


def command(root, manifest):
    """Select the one finite gate entrypoint using the exact captured test-class inventory."""
    target = root/'backend/target'
    classpath = ':'.join(map(str, (root/'.gate/probe-classes', target/'classes', target/'dependency/*', target/'solver/alloy.jar')))
    return [manifest['java']['executable'], '-Xms32m', '-Xmx1g', '-XX:+UseSerialGC',
            '-XX:ActiveProcessorCount=4', '-cp', classpath, 'dev.allow.backend.WarmLatencyMain',
            '--runtime-root', str(root), '--plan', str(root/'.gate/evidence/latency-plan.json'),
            '--report', str(root/'.gate/evidence/latency-java.json')]


def run(root, manifest, launch):
    """Keep full Java series evidence private and reap the exact child on every outcome."""
    evidence = root/'.gate/evidence'
    child, result = None, {'status': 'BLOCKED', 'started_monotonic_ns': time.monotonic_ns()}
    try:
        concrete_plan(root, manifest, launch)
        result['plan'] = record(evidence/'latency-plan.json')
        descriptor = os.open(evidence/'latency-private.log', os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as log:
            child = subprocess.Popen(command(root, manifest), cwd=root/'backend', env=clean_environment(root),
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, umask=0o077)
            result['probe_identity'] = process_identity(child.pid)
            write_private(evidence/'latency-started.json', result)
            result['log_bytes'] = probe_owner.bounded_output(child, log, 180)
        result['exit_code'] = child.returncode
        if (evidence/'latency-java.json').is_file():
            result['java_report'] = record(evidence/'latency-java.json')
        if child.returncode == 0 and 'java_report' in result:
            result['status'] = 'COMPLETE'
    except Exception as error:
        result['failure_class'] = type(error).__name__
    finally:
        if child is not None:
            try:
                probe_owner.terminate(child)
                result['probe_reaped'] = child.poll() is not None
            except Exception as error:
                result.update(status='BLOCKED', probe_reaped=False, reap_failure_class=type(error).__name__)
        result['finished_monotonic_ns'] = time.monotonic_ns()
        write_private(evidence/'latency-complete.json', result)


def main():
    """Hold the owner after completion so the outside controller observes terminal emptiness."""
    root = Path(__file__).resolve().parent.parent
    manifest = read_private(root/'.gate/manifest.json')
    launch = read_private(root/'.gate/evidence/latency-launch.json')
    os.umask(0o077)
    write_private(root/'.gate/evidence/owner.json', {'identity': process_identity(os.getpid()),
                  'input_root_sha256': manifest['input_root_sha256']})
    run(root, manifest, launch)
    while True:
        signal.pause()


if __name__ == '__main__':
    main()
