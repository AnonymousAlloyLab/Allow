#!/usr/bin/env python3
"""Own every fresh server process inside the one reviewed transient service."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

from harness_common import clean_environment, process_identity, read_private, same_process, write_private


def private_run(root, label, argv, timeout):
    """Run a bounded copied helper, retaining all diagnostics only inside its private root."""
    path = root/'.gate/evidence'/f'{label}.log'
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        result = subprocess.run(list(map(str, argv)), cwd=root, env=clean_environment(root),
                                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise RuntimeError('owned_helper_failed_' + label)


def bootstrap(root):
    """Start only fresh copied PostgreSQL and route every SQL operation through SQLeanParser."""
    sys.path.insert(0, str(root/'scripts'))
    import bootstrap_corpus as corpus
    if corpus.ROOT != root or corpus.running():
        raise ValueError('fresh_owned_database_required')
    config = corpus.credentials()
    corpus.initialize(config)
    options = (f"-p 54329 -k {corpus.CLUSTER/'socket'} -h '' -c max_connections=20 "
               '-c shared_buffers=128MB -c work_mem=4MB -c maintenance_work_mem=64MB '
               '-c max_parallel_workers=0 -c unix_socket_permissions=0700 '
               '-c standard_conforming_strings=on -c max_prepared_transactions=0')
    corpus.run([corpus.PREFIX/'bin/pg_ctl', '-D', corpus.CLUSTER/'data', '-l',
                corpus.CLUSTER/'server.log', '-o', options, '-w', 'start'])
    corpus.start_proxy(config)
    corpus.sql('CREATE ROLE allow_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;', config)
    password = "'" + config['app_password'].replace("'", "''") + "'"
    corpus.sql('CREATE ROLE allow_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD ' + password + ';', config)
    corpus.sql('CREATE DATABASE allow_retrieval OWNER allow_owner;', config)
    corpus.sql('CREATE EXTENSION IF NOT EXISTS vector;', config, 'allow_retrieval')
    corpus.wait_context_ready()
    private_run(root, 'document-bootstrap', [root/'.tools/retrieval-venv/bin/python',
                root/'scripts/bootstrap_documents.py'], 90)
    return corpus


def spring_argv(root, manifest):
    """Launch the existing Spring entrypoint with exactly the preregistered server budgets."""
    return [manifest['java']['executable'], '-Xms128m', '-Xmx1024m', '-XX:MaxMetaspaceSize=256m',
            '-XX:ReservedCodeCacheSize=128m', '-XX:ActiveProcessorCount=4', '-cp',
            'target/classes:target/dependency/*', 'dev.allow.backend.AllowApplication',
            '--server.port=' + str(manifest['port']), '--server.address=127.0.0.1',
            '--server.tomcat.threads.max=16', '--server.tomcat.threads.min-spare=2',
            '--server.tomcat.max-connections=32', '--server.tomcat.accept-count=8',
            '--debug=false', '--trace=false', '--logging.level.root=WARN',
            '--logging.level.org.springframework=WARN', '--allow.corpus.root=' + str(root)]


def launch_spring(root, manifest):
    """Generate fresh local authority; never inherit or print a live bearer or URL."""
    token = secrets.token_urlsafe(32)
    path = root/'.runtime/launch.url'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(f'http://127.0.0.1:{manifest["port"]}/#token={token}\n')
    environment = clean_environment(root)
    environment['ALLOW_TOKEN'] = token
    descriptor = os.open(root/'.gate/evidence/spring.log',
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        child = subprocess.Popen(spring_argv(root, manifest), cwd=root/'backend', env=environment,
                                 stdout=stream, stderr=subprocess.STDOUT)
    return child, token


def http_health(port, token):
    """Use the real authorized documents read endpoint, not TCP-open readiness."""
    request = urllib.request.Request(f'http://127.0.0.1:{port}/api/v1/documents',
                                     headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(request, timeout=2) as response:
        value = json.loads(response.read(1048577))
        return response.status == 200 and set(value) == {'protocol', 'requestId', 'status', 'data'} \
            and value['protocol'] == 1 and value['status'] == 'OK'


def owns_document_lock(root, pid):
    """Bind the kernel's POSIX lock holder to the observed Spring incarnation."""
    info = (root/'.runtime/documents/server.lock').stat()
    device = f'{os.major(info.st_dev):02x}:{os.minor(info.st_dev):02x}:{info.st_ino}'
    for line in Path('/proc/locks').read_text().splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[1:4] == ['POSIX', 'ADVISORY', 'WRITE']:
            if fields[4] == str(pid) and fields[5] == device:
                return True
    return False


def wait_ready(root, manifest, corpus, spring, token):
    """Require loaded proxy input identity, context authority, HTTP readiness and server ownership."""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if spring.poll() is not None:
            raise RuntimeError('spring_exited_before_ready')
        try:
            owner = read_private(corpus.PROXY/'owner.json')
            proxy = process_identity(owner['pid'])
            good = proxy and proxy['start_ticks'] == owner['identity']['start_ticks']
            good = good and corpus.proxy_loaded(owner['pid'], corpus.proxy_inputs())
            if good and http_health(manifest['port'], token) and owns_document_lock(root, spring.pid):
                corpus.wait_context_ready()
                return {'spring': process_identity(spring.pid), 'proxy': proxy,
                        'postgres': process_identity(int((corpus.CLUSTER/'data/postmaster.pid').read_text().splitlines()[0])),
                        'supervisor': process_identity(os.getpid()), 'first_ready_monotonic_ns': time.monotonic_ns()}
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(.1)
    raise RuntimeError('stack_readiness_deadline')


def supervise(root, manifest):
    """Keep the owned stack alive for its external driver and fail closed on service loss."""
    corpus = bootstrap(root)
    spring, token = launch_spring(root, manifest)
    ready = wait_ready(root, manifest, corpus, spring, token)
    ready.update(input_root_sha256=manifest['input_root_sha256'], status='READY')
    write_private(root/'.gate/evidence/ready.json', ready)
    while True:
        if spring.poll() is not None or any(not same_process(ready[name]) for name in ('proxy', 'postgres')):
            raise RuntimeError('owned_service_lost')
        time.sleep(.2)


def main():
    """Run only from the copied manifest, with no environment-selected worker options."""
    root = Path(__file__).resolve().parent.parent
    manifest = read_private(root/'.gate/manifest.json')
    if manifest['copied_root'] != str(root):
        raise ValueError('owner_root_mismatch')
    os.environ.clear()
    os.environ.update(clean_environment(root))
    os.umask(0o077)
    write_private(root/'.gate/evidence/owner.json', {'identity': process_identity(os.getpid()),
                  'input_root_sha256': manifest['input_root_sha256'], 'started_monotonic_ns': time.monotonic_ns()})
    try:
        supervise(root, manifest)
    except BaseException as error:
        write_private(root/'.gate/evidence/failure.json', {'status': 'BLOCKED', 'class': type(error).__name__})
        raise SystemExit(1)


if __name__ == '__main__':
    main()
