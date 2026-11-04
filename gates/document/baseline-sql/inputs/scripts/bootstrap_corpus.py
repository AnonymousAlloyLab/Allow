#!/usr/bin/env python3
"""Build pinned local PostgreSQL/pgvector and manage only Allow's private cluster."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import shlex
import socket
import time
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools/retrieval'
PREFIX = TOOLS / 'postgres'
RUNTIME = ROOT / '.runtime/corpus'
CLUSTER = RUNTIME / 'postgres'
PROXY = RUNTIME / 'sql-proxy'
PROXY_SOCKET = PROXY / 'socket/.s.PGSQL.54329'
BACKEND_SOCKET = CLUSTER / 'socket/.s.PGSQL.54329'
DOWNLOADS = ROOT / '.tools/retrieval-downloads'
PACKAGES = [
    ('postgresql-16.15.tar.bz2', 'https://ftp.postgresql.org/pub/source/v16.15/postgresql-16.15.tar.bz2',
     'c1575341fa7bd40f5274ea465b34390f4dc64cdd0770af327005caaeb9f6b7ed'),
    ('pgvector-0.8.7.tar.gz', 'https://codeload.github.com/pgvector/pgvector/tar.gz/f37c13f68b57d2c3472b2214fbcff699d6d34876',
     '83d673c3b287cddbf3879f86215f043f2c2b56c69d37b2a77504910db1ed6e56')]


def run(arguments, cwd=None, env=None, text=None, sensitive=False):
    """Run a bounded command; diagnostics remain in a private build log, never credentials."""
    result = subprocess.run([str(x) for x in arguments], cwd=cwd, env=env, input=text,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    if result.returncode:
        detail = '' if sensitive else ': '+result.stdout[-3000:]
        raise RuntimeError(f'{Path(arguments[0]).name} failed ({result.returncode})'+detail)
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
    """Use the explicit schema helper; the opaque 004 baseline is not executable."""
    environment=clean_environment()
    environment['PYTHONPATH']=str(ROOT/'retrieval')
    result=run([ROOT/'.tools/retrieval-venv/bin/python','-m','allow_retrieval.migration'],
               cwd=ROOT,env=environment,sensitive=True)
    print(result.strip())


def private_json(path, value):
    """Write local credentials with private permissions and an atomic replacement."""
    temporary = path.with_suffix('.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os,'O_NOFOLLOW',0), 0o600)
    os.fchmod(fd,0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def credentials():
    """Keep stable passwords, but replace every client route with the owned proxy."""
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    path=RUNTIME/'database.json'
    if path.is_symlink():raise RuntimeError('Credential symlink rejected')
    value=json.loads(path.read_text()) if path.exists() else {
        'admin_password':secrets.token_urlsafe(32),'app_password':secrets.token_urlsafe(32)}
    def quoted(text):return "'"+str(text).replace('\\','\\\\').replace("'","\\'")+"'"
    common='host='+quoted(PROXY_SOCKET.parent)+' port=54329'
    for role in ('admin','app'):
        value[role+'_dsn']=common+' dbname=allow_retrieval user=allow_'+role+' password='+quoted(value[role+'_password'])
    private_json(path,value)
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


def clean_environment():
    """Remove ambient libpq settings before every owned client or daemon launch."""
    return {k:v for k,v in os.environ.items() if not k.startswith('PG') and not k.startswith('ALLOW_RETRIEVAL_')}


def sql(query, config, database='postgres', tag='allow-bootstrap'):
    """Send fixed SQL only to the parser proxy, without exposing error source text."""
    environment=clean_environment()
    environment.update(PGPASSWORD=config['admin_password'],PGAPPNAME=tag,PGCLIENTENCODING='UTF8',
                       PGSSLMODE='disable',PGGSSENCMODE='disable',PGOPTIONS='')
    return run([PREFIX/'bin/psql','-X','-v','ON_ERROR_STOP=1','-A','-t',
                '-h',PROXY_SOCKET.parent,'-p','54329','-U','allow_admin','-d',database],
               env=environment,text=query,sensitive=True)


def process_identity(pid):
    """Read start ticks and argv, preventing process-ID reuse from granting ownership."""
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();fields=raw[raw.rfind(')')+2:].split()
        if fields[0]=='Z':return None
        command=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        return {'start_ticks':fields[19],'command':[v.decode() for v in command if v]}
    except (OSError,IndexError,UnicodeError):return None


def stop_proxy():
    """Stop only a daemon whose recorded PID, start time and exact argv still match."""
    owner_path=PROXY/'owner.json'
    if not owner_path.exists():return
    owner=json.loads(owner_path.read_text());pid=owner['pid']
    current=process_identity(pid)
    if current is not None:
        if pid<=1 or current!=owner['identity'] or os.getpgid(pid)!=pid:
            raise RuntimeError('Proxy process ownership mismatch')
        os.killpg(pid,signal.SIGTERM)
        deadline=time.monotonic()+10
        while process_identity(pid) is not None and time.monotonic()<deadline:time.sleep(.05)
        if process_identity(pid) is not None:raise RuntimeError('Owned proxy did not stop')
    owner_path.unlink(missing_ok=True)



def proxy_inputs():
    """Hash every policy/program input that a reusable daemon must have loaded."""
    names=('retrieval/allow_retrieval/sql_proxy.py','retrieval/allow_retrieval/sql_guard.py','config/sqlean-parser-lock.json')
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}


def proxy_loaded(pid,expected):
    """Bind published startup inputs to the same owned live process."""
    try:
        status=json.loads((PROXY/'status.json').read_text())
        return status.get('pid')==pid and status.get('loaded_inputs')==expected
    except (OSError,ValueError):return False

def start_proxy(config):
    """Launch the owned daemon, await its identity-bound ready file and parsed SELECT."""
    PROXY.mkdir(mode=0o700,parents=True,exist_ok=True);PROXY.chmod(0o700)
    PROXY_SOCKET.parent.mkdir(mode=0o700,exist_ok=True);PROXY_SOCKET.parent.chmod(0o700)
    owner_path=PROXY/'owner.json';expected=proxy_inputs()
    if owner_path.exists():
        owner=json.loads(owner_path.read_text())
        if process_identity(owner['pid'])==owner['identity']:
            if proxy_loaded(owner['pid'],expected):
                sql('SELECT 1;',config,tag='allow-proxy-readiness');return
            stop_proxy()
        else:owner_path.unlink()
    if PROXY_SOCKET.exists():
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as probe:
            try:probe.connect(str(PROXY_SOCKET))
            except (ConnectionRefusedError,FileNotFoundError):PROXY_SOCKET.unlink(missing_ok=True)
            else:raise RuntimeError('Unowned proxy socket is active')
    ready=PROXY/'ready.json';ready.unlink(missing_ok=True)
    command=['/usr/bin/python3','-m','allow_retrieval.sql_proxy','--backend',str(BACKEND_SOCKET),
             '--listen',str(PROXY_SOCKET),'--status',str(PROXY/'status.json'),'--ready',str(ready)]
    env=clean_environment();env['PYTHONPATH']=str(ROOT/'retrieval')
    fd=os.open(PROXY/'proxy.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'ab') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True)
    identity=process_identity(process.pid)
    if identity is None:raise RuntimeError('Proxy launch failed')
    private_json(owner_path,{'pid':process.pid,'identity':identity,'loaded_inputs':expected})
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Owned proxy exited before readiness')
        if ready.exists():
            state=json.loads(ready.read_text())
            if state.get('pid')==process.pid and state.get('listen')==str(PROXY_SOCKET) and proxy_loaded(process.pid,expected):
                sql('SELECT 1;',config,tag='allow-proxy-readiness');return
        time.sleep(.05)
    stop_proxy();raise RuntimeError('Proxy readiness deadline exceeded')


def backend_is_private():
    """Confirm the actual postmaster launch disabled TCP and uses the owned socket."""
    try:
        args=shlex.split((CLUSTER/'data/postmaster.opts').read_text())
        return args[args.index('-h')+1]=='' and args[args.index('-k')+1]==str(CLUSTER/'socket')
    except (OSError,ValueError,IndexError):return False


def start():
    """Start owned PostgreSQL, then the parser proxy, then admitted bootstrap SQL."""
    build();config=credentials();initialize(config)
    if running() and not backend_is_private():
        stop_proxy()
        run([PREFIX/'bin/pg_ctl','-D',CLUSTER/'data','-m','fast','-w','stop'])
    if not running():
        options=f"-p 54329 -k {CLUSTER/'socket'} -h '' -c max_connections=20 -c shared_buffers=64MB -c unix_socket_permissions=0700 -c standard_conforming_strings=on -c max_prepared_transactions=0"
        run([PREFIX/'bin/pg_ctl','-D',CLUSTER/'data','-l',CLUSTER/'server.log','-o',options,'-w','start'])
    start_proxy(config)
    if sql("SELECT 1 FROM pg_roles WHERE rolname='allow_owner';",config).strip()!='1':
        sql('CREATE ROLE allow_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;',config)
    if sql("SELECT 1 FROM pg_roles WHERE rolname='allow_app';",config).strip()!='1':
        password="'"+config['app_password'].replace("'","''")+"'"
        sql('CREATE ROLE allow_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '+password+';',config)
    if sql("SELECT 1 FROM pg_database WHERE datname='allow_retrieval';",config).strip()!='1':
        sql('CREATE DATABASE allow_retrieval OWNER allow_owner;',config)
    sql('CREATE EXTENSION IF NOT EXISTS vector;',config,'allow_retrieval')
    print(json.dumps({'status':'RUNNING','postgres':'16.15','pgvector':'0.8.7','routing':'SQLEAN_PROXY','tcp':False}))


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
    elif operation == 'stop':
        stop_proxy()
        if running():run([PREFIX/'bin/pg_ctl','-D',CLUSTER/'data','-m','fast','-w','stop'])
        print('Stopped owned Allow proxy and PostgreSQL.')
    elif operation in ['status', 'stop']:
        print('RUNNING' if running() else 'STOPPED')


if __name__ == '__main__':
    main()
