"""Isolated capability probe; never connects to PostgreSQL or edits production."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[3]
lock = json.loads((root/'config/sqlean-parser-lock.json').read_text())
fd = os.memfd_create('allow-parser-candidate', os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
try:
    with (root/'.tools/sqlean/sqlean_pg_grammar').open('rb') as source:
        while chunk := source.read(1048576):
            remaining = memoryview(chunk)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise RuntimeError('short write')
                remaining = remaining[written:]
    seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
    fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
    size = os.fstat(fd).st_size
    digest = hashlib.sha256()
    offset = 0
    while chunk := os.pread(fd, 1048576, offset):
        digest.update(chunk)
        offset += len(chunk)
    assert digest.hexdigest() == lock['binary_sha256']
    assert fcntl.fcntl(fd, fcntl.F_GET_SEALS) & seals == seals
    denials = {}
    for name, operation in (
        ('write', lambda: os.pwrite(fd, b'x', 0)),
        ('shrink', lambda: os.ftruncate(fd, size-1)),
        ('grow', lambda: os.ftruncate(fd, size+1)),
    ):
        try:
            operation()
        except OSError as exc:
            denials[name] = exc.errno
        else:
            raise AssertionError(name)
    # One parser invocation, not a database query and not a benchmark loop.
    start = time.perf_counter()
    proc = subprocess.Popen(['/usr/bin/prlimit', '--as=1073741824', '--cpu=6', '--core=0',
        '--fsize=16777216', '--', f'/proc/self/fd/{fd}', '--max-transitions', '1000000'],
        pass_fds=(fd,), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={'LEAN_NUM_THREADS':'1', 'PATH':'/usr/bin:/bin'})
    expected_object = os.fstat(fd)
    observed = False
    try:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError('child exited before identity observation')
            try:
                actual = os.stat(f'/proc/{proc.pid}/exe')
                if (actual.st_dev, actual.st_ino) == (expected_object.st_dev, expected_object.st_ino):
                    observed = True
                    break
            except FileNotFoundError:
                pass
            time.sleep(0.001)
        assert observed, 'actual parser executable object not observed'
        stdout, _ = proc.communicate(b'SELECT 1', timeout=5)
        result = subprocess.CompletedProcess(proc.args, proc.returncode, stdout)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    elapsed = time.perf_counter()-start
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert report['status'] == 'grammar-accepted' and report['sql'] == 'SELECT 1'
    print(json.dumps({'scope':'isolated capability witness, not production validation',
        'size': size, 'sha256':digest.hexdigest(), 'seals':seals,
        'mutation_denials_errno':denials, 'prlimit_inherited_fd_execution':True, 'actual_parser_proc_exe_inode_matches_memfd':observed,
        'parser_returncode':result.returncode, 'single_execution_seconds':elapsed,
        'limitations':['not a latency distribution','no closed/reused-fd/concurrency/race suite','dynamic loader remains trusted']}, indent=2))
finally:
    os.close(fd)
