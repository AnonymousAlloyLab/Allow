#!/usr/bin/env python3
"""Build pinned local PostgreSQL/pgvector and manage only Allow's private cluster."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools/retrieval'
PREFIX = TOOLS / 'postgres'
RUNTIME = ROOT / '.runtime/corpus'
CLUSTER = RUNTIME / 'postgres'
DOWNLOADS = ROOT / '.tools/retrieval-downloads'
PACKAGES = [
    ('postgresql-16.15.tar.bz2', 'https://ftp.postgresql.org/pub/source/v16.15/postgresql-16.15.tar.bz2',
     'c1575341fa7bd40f5274ea465b34390f4dc64cdd0770af327005caaeb9f6b7ed'),
    ('pgvector-0.8.7.tar.gz', 'https://codeload.github.com/pgvector/pgvector/tar.gz/f37c13f68b57d2c3472b2214fbcff699d6d34876',
     '83d673c3b287cddbf3879f86215f043f2c2b56c69d37b2a77504910db1ed6e56')]


def run(arguments, cwd=None, env=None, text=None):
    """Run a bounded command; diagnostics remain in a private build log, never credentials."""
    result = subprocess.run([str(x) for x in arguments], cwd=cwd, env=env, input=text,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    if result.returncode:
        raise RuntimeError(f'{Path(arguments[0]).name} failed ({result.returncode}): {result.stdout[-3000:]}')
    return result.stdout


def archive(name, url, expected):
    """Download official source and require its frozen SHA-256 before extraction."""
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    target = DOWNLOADS / name
    if not target.exists():
        with urllib.request.urlopen(url, timeout=60) as source, target.open('wb') as output:
            while chunk := source.read(1048576):
                output.write(chunk)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError('Pinned source archive digest mismatch: ' + name)
    return target


def unpack(path):
    """Extract only regular files/directories under the pinned source's single root."""
    destination = TOOLS / 'src'
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as source:
        members = source.getmembers()
        for entry in members:
            resolved = (destination / entry.name).resolve()
            if not resolved.is_relative_to(destination.resolve()) or not (entry.isfile() or entry.isdir()):
                raise ValueError('Unexpected archive entry')
        source.extractall(destination, members=members)
    return destination / members[0].name.split('/')[0]


def build():
    """Compile pinned sources into an isolated prefix; no system install or service changes."""
    TOOLS.mkdir(parents=True, exist_ok=True)
    sources = [archive(*item) for item in PACKAGES]
    if (PREFIX / 'bin/postgres').exists() and (PREFIX / 'lib/vector.so').exists():
        return
    log = []
    postgres, vector = [unpack(path) for path in sources]
    log.append(run(['./configure', '--prefix=' + str(PREFIX), '--without-icu',
                    '--without-readline', '--without-zlib', '--without-openssl'], cwd=postgres))
    log.append(run(['make', '-j8'], cwd=postgres))
    log.append(run(['make', 'install'], cwd=postgres))
    configuration = 'PG_CONFIG=' + str(PREFIX / 'bin/pg_config')
    log.append(run(['make', '-j8', configuration, 'OPTFLAGS='], cwd=vector))
    log.append(run(['make', 'install', configuration], cwd=vector))
    (TOOLS / 'build.log').write_text('\n'.join(log))
    inventory = {'postgres': '16.15', 'pgvector': '0.8.7', 'sources': [
        {'name': name, 'url': url, 'sha256': digest} for name, url, digest in PACKAGES]}
    (TOOLS / 'versions.json').write_text(json.dumps(inventory, indent=2) + '\n')


def migrate():
    """Apply versioned repository migrations to the dedicated database."""
    config = credentials()
    for path in sorted((ROOT / 'db/migrations').glob('*.sql')):
        sql(path.read_text(), config, 'allow_retrieval')
    print('Applied Allow corpus migrations.')


def private_json(path, value):
    """Write local credentials with private permissions and an atomic replacement."""
    temporary = path.with_suffix('.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def credentials():
    """Create stable private local credentials; never return them through logs or stdout."""
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = RUNTIME / 'database.json'
    if path.exists():
        return json.loads(path.read_text())
    admin_password, app_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    common = f'host={CLUSTER / "socket"} port=54329'
    value = {'admin_dsn': common + ' dbname=allow_retrieval user=allow_admin password=' + admin_password,
             'app_dsn': common + ' dbname=allow_retrieval user=allow_app password=' + app_password,
             'admin_password': admin_password, 'app_password': app_password}
    private_json(path, value)
    return value


def initialize(config):
    """Initialize only the workspace cluster with SCRAM authentication and a private socket."""
    CLUSTER.mkdir(mode=0o700, parents=True, exist_ok=True)
    (CLUSTER / 'socket').mkdir(mode=0o700, exist_ok=True)
    if (CLUSTER / 'data/PG_VERSION').exists():
        return
    password_file = CLUSTER / '.initial-password'
    fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(config['admin_password'])
    try:
        run([PREFIX / 'bin/initdb', '-D', CLUSTER / 'data', '--username=allow_admin',
             '--pwfile=' + str(password_file), '--auth-local=scram-sha-256',
             '--auth-host=scram-sha-256', '--no-locale', '-E', 'UTF8'])
    finally:
        password_file.unlink()


def running():
    """Check this data directory's pg_ctl status without inspecting unrelated PostgreSQL services."""
    if not (CLUSTER / 'data/PG_VERSION').exists():
        return False
    result = subprocess.run([str(PREFIX / 'bin/pg_ctl'), '-D', str(CLUSTER / 'data'), 'status'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    return result.returncode == 0


def sql(query, config, database='postgres'):
    """Execute fixed bootstrap SQL with private credentials supplied only through the environment."""
    environment = os.environ.copy()
    environment['PGPASSWORD'] = config['admin_password']
    return run([PREFIX / 'bin/psql', '-X', '-v', 'ON_ERROR_STOP=1', '-A', '-t',
                '-h', CLUSTER / 'socket', '-p', '54329', '-U', 'allow_admin', '-d', database],
               env=environment, text=query)


def start():
    """Start authenticated loopback-only PostgreSQL and create the dedicated database and roles."""
    build()
    config = credentials()
    initialize(config)
    if not running():
        options = f"-p 54329 -k {CLUSTER / 'socket'} -h 127.0.0.1 -c max_connections=20 -c shared_buffers=64MB"
        run([PREFIX / 'bin/pg_ctl', '-D', CLUSTER / 'data', '-l', CLUSTER / 'server.log',
             '-o', options, '-w', 'start'])
    if sql("SELECT 1 FROM pg_roles WHERE rolname='allow_owner';", config).strip() != '1':
        sql('CREATE ROLE allow_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;', config)
    if sql("SELECT 1 FROM pg_roles WHERE rolname='allow_app';", config).strip() != '1':
        sql("CREATE ROLE allow_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '" + config['app_password'] + "';", config)
    if sql("SELECT 1 FROM pg_database WHERE datname='allow_retrieval';", config).strip() != '1':
        sql('CREATE DATABASE allow_retrieval OWNER allow_owner;', config)
    sql('CREATE EXTENSION IF NOT EXISTS vector;', config, 'allow_retrieval')
    print(json.dumps({'status': 'RUNNING', 'postgres': '16.15', 'pgvector': '0.8.7',
                      'port': 54329, 'credentials': 'private runtime configuration'}))


def main():
    """Offer explicit workspace-only build, start, stop and status actions."""
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['build', 'start', 'migrate', 'stop', 'status'])
    operation = parser.parse_args().operation
    if operation == 'build':
        build()
    elif operation == 'start':
        start()
    elif operation == 'migrate':
        migrate()
    elif operation == 'stop' and running():
        run([PREFIX / 'bin/pg_ctl', '-D', CLUSTER / 'data', '-m', 'fast', '-w', 'stop'])
        print('Stopped Allow corpus PostgreSQL.')
    elif operation in ['status', 'stop']:
        print('RUNNING' if running() else 'STOPPED')


if __name__ == '__main__':
    main()
