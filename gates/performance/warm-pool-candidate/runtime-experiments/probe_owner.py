#!/usr/bin/env python3
"""Run one registered gate Java probe inside control and retain bounded private output."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

from harness_common import clean_environment, digest, process_identity, read_private, write_private


def command(root, manifest):
    """Use only explicitly copied production and gate-probe class bytes."""
    target = root/'backend/target'
    classpath = ':'.join(map(str, (root/'.gate/probe-classes', target/'classes', target/'dependency/*', target/'solver/alloy.jar')))
    return [manifest['java']['executable'], '-Xms32m', '-Xmx256m', '-XX:+UseSerialGC',
            '-XX:ActiveProcessorCount=4', '-cp', classpath, 'dev.allow.backend.WarmPoolProbeMain',
            '--runtime-root', str(root), '--cases', str(root/'.gate/probe-cases.json'),
            '--report', str(root/'.gate/evidence/java-probe.json')]


def bounded_output(child, log, seconds):
    """Drain a fixed private diagnostic allowance without printing model or frame data."""
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)
    deadline, count, eof = time.monotonic()+seconds, 0, False
    try:
        while not eof or child.poll() is None:
            if time.monotonic() >= deadline:
                raise TimeoutError('probe_original_deadline')
            for key, _ in selector.select(min(.1, max(0, deadline-time.monotonic()))):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    eof = True
                    selector.unregister(key.fileobj)
                    continue
                count += len(chunk)
                if count > 262144:
                    raise ValueError('probe_private_log_limit')
                log.write(chunk)
        child.wait(timeout=1)
        return count
    finally:
        selector.close()


def terminate(child):
    """Reap the exact Popen child; whole-tree cleanup remains the outer scope owner."""
    if child.poll() is None:
        child.terminate()
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=3)
    if child.stdout is not None:
        child.stdout.close()


def run(root, manifest):
    """Preserve a complete attempt even when probe transport or Java execution fails."""
    evidence = root/'.gate/evidence'
    descriptor = os.open(evidence/'java-probe-private.log', os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    child, result = None, {'status': 'BLOCKED', 'started_monotonic_ns': time.monotonic_ns()}
    try:
        with os.fdopen(descriptor, 'wb') as log:
            child = subprocess.Popen(command(root, manifest), cwd=root/'backend', env=clean_environment(root),
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, umask=0o077)
            result['probe_identity'] = process_identity(child.pid)
            write_private(evidence/'probe-started.json', result)
            result['log_bytes'] = bounded_output(child, log, 180)
        result['exit_code'] = child.returncode
        if child.returncode == 0 and (evidence/'java-probe.json').is_file():
            result.update(status='COMPLETE', java_report_sha256=digest(evidence/'java-probe.json'))
    except Exception as error:
        result['failure_class'] = type(error).__name__
    finally:
        if child is not None:
            terminate(child)
            result['probe_reaped'] = child.poll() is not None
        result['finished_monotonic_ns'] = time.monotonic_ns()
        write_private(evidence/'probe-complete.json', result)


def main():
    """Keep the scope owner alive after finite work until the outside controller reaps it."""
    root = Path(__file__).resolve().parent.parent
    manifest = read_private(root/'.gate/manifest.json')
    os.umask(0o077)
    (root/'.gate/evidence').mkdir(mode=0o700, exist_ok=True)
    write_private(root/'.gate/evidence/owner.json', {'identity': process_identity(os.getpid()),
                  'input_root_sha256': manifest['input_root_sha256']})
    run(root, manifest)
    while True:
        signal.pause()


if __name__ == '__main__':
    main()
