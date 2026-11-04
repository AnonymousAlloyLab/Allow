#!/usr/bin/env python3
"""Preregistered P0 probes, isolated owned processes and parser-routed test database."""
from contextlib import ExitStack
from datetime import datetime, timezone
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'retrieval'), str(ROOT/'scripts')]
from psycopg import sql
from psycopg.conninfo import make_conninfo
from allow_documents import cli, identity, migration, store as store_module, wire
from allow_documents.store import Store
from allow_retrieval import sql_connections, sql_image, sql_proxy
from allow_retrieval.sql_guard import ParserGate
import document_recovery_test as fixtures

MODE = 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'
SHARED_STATUS = ROOT/'.runtime/corpus/sql-proxy/status.json'
NONCE = '00000000-0000-4000-8000-000000000001'


def save(path, value):
    """Write only authored or sanitized finite evidence."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def read(path):
    """Load one locally owned structured artifact."""
    return json.loads(path.read_text())


def sha(path):
    """Identify exact file bytes without publishing their contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packed(value):
    """Canonicalize the registration manifest for independent root verification."""
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def verify():
    """Fail before execution if any preregistered source or dependency changed."""
    registration = read(HERE/'registration.json')
    assert hashlib.sha256(packed(registration['files'])).hexdigest() == registration['input_root_sha256']
    for item in registration['files']:
        assert sha(Path(item['path'])) == item['sha256'], 'INPUT_MUTATION:'+item['path']
    return registration


def frame(args=None):
    """Build the exact closed validationContext transport shape."""
    return {'protocol':1, 'requestId':NONCE, 'operation':'validationContext', 'args':args or {
        'documentId':'server:'+NONCE, 'revision':0, 'ids':[]}}


def depth(value):
    """Independently count root zero, dictionary keys/values and list-item edges recursively."""
    if isinstance(value, dict):
        return 1+max((depth(part) for pair in value.items() for part in pair), default=-1)
    if isinstance(value, list):
        return 1+max((depth(part) for part in value), default=-1)
    return 0


def shared_identity():
    """Exclude asynchronous counters while preserving the shared proxy's complete identity."""
    value = read(SHARED_STATUS)
    parser = {key:value['parser'][key] for key in (
        'generation','snapshot_sha256','binary_sha256','configuration_sha256',
        'mapping_sha256','identity_mode','policy','profile')}
    return {key:value[key] for key in ('pid','started','loaded_inputs')} | {'parser':parser}


def environment():
    """Match private CLI environment without ambient credentials or database overrides."""
    return {'PYTHONPATH':str(ROOT/'retrieval'), 'ALLOW_CORPUS_RUNTIME':str(ROOT/'.runtime/corpus'),
            'LANGSMITH_TRACING':'false'}


def process(command, raw, telemetry=None):
    """Execute and reap one actual private CLI with its unchanged resource ceilings."""
    child = subprocess.Popen(['/usr/bin/prlimit','--as=2147483648','--cpu=20','--']+command,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=ROOT, env=environment())
    start = identity.process_start(child.pid)
    output, errors = child.communicate(raw, timeout=20)
    assert child.returncode == 0 and not errors, 'CLI_EXECUTION_FAILURE'
    assert not identity.alive(child.pid, start), 'CLI_NOT_REAPED'
    assert output.endswith(b'\n') and output.count(b'\n') == 1 and len(output) <= 1572865
    result = wire.decode(output, 1572865)
    assert set(result) == {'protocol','requestId','status','data'}
    return result, {'pid':child.pid,'start_ticks':start,'reaped':True,'output_bytes':len(output),
                    'telemetry':read(telemetry) if telemetry else None}


def audited_cli(path):
    """Run actual CLI main with fail-loud observation of attempted SQL and child creation."""
    counts = {'sql_connect_attempts':0,'subprocess_launches':0}
    def forbidden(*args, **kwargs):
        counts['sql_connect_attempts'] += 1
        raise RuntimeError('probe_forbidden_sql')
    def audit(event, arguments):
        if event == 'subprocess.Popen':
            counts['subprocess_launches'] += 1
            raise RuntimeError('probe_forbidden_process')
    sys.addaudithook(audit)
    try:
        with patch.object(store_module, 'connect', forbidden):
            cli.main()
    finally:
        save(path, counts)


def cli_case(raw, expected_nonce, directory, label):
    """Compare literal installed CLI and observed CLI; require rejection before SQL/worker."""
    actual, ownership = process([sys.executable,'-m','allow_documents.cli'], raw)
    telemetry = directory/(label+'-telemetry.json')
    observed, observation = process([sys.executable,str(__file__),'--audit-cli',str(telemetry)], raw, telemetry)
    assert actual == observed, 'INSTRUMENTATION_CHANGED_RESULT'
    assert actual == {'protocol':1,'requestId':expected_nonce,'status':'ERROR','data':{'reason':'invalid_request'}}
    assert observation['telemetry'] == {'sql_connect_attempts':0,'subprocess_launches':0}
    return {'literal_cli':ownership,'observed_cli':observation,'bytes_including_newline':len(raw),
            'status':actual['status'],'nonce_captured':actual['requestId'] is not None,
            'input_sha256':hashlib.sha256(raw).hexdigest()}


def wire_boundaries(directory):
    """Exercise below/exact/above 3 MiB total input with one explicit terminal newline."""
    rows = []
    for amount in (wire.MAX_INPUT-1, wire.MAX_INPUT, wire.MAX_INPUT+1):
        value = frame(); value['padding'] = ''
        base = json.dumps(value, separators=(',',':')).encode()
        value['padding'] = 'x'*(amount-1-len(base))
        raw = json.dumps(value, separators=(',',':')).encode()+b'\n'
        assert len(raw) == amount and raw.count(b'\n') == 1
        expected = NONCE if amount <= wire.MAX_INPUT else None
        row = cli_case(raw, expected, directory, 'size-'+str(amount))
        row['guard'] = 'closed_fields' if expected else 'input_limit_before_nonce'
        rows.append(row)
    return {'cases':rows,'fixture':'structurally adversarial extra-field frame; not valid context args',
            'java_gateway_guard':'encoded bytes >=3145728 denied; FrameProcess adds one newline'}


def nesting_boundaries(directory):
    """Separate depth acceptance from downstream invalid identity-list rejection."""
    rows = []
    for target in (95,96,97):
        nested = 0
        for _ in range(target-2): nested = [nested]
        value = frame(); value['args']['ids'] = nested
        assert depth(value) == target, 'INDEPENDENT_DEPTH_MISMATCH'
        raw = json.dumps(value, separators=(',',':')).encode()+b'\n'
        try:
            wire.decode(raw)
            decoded = True; reason = None
        except ValueError as failure:
            decoded = False; reason = str(failure)
        assert decoded == (target <= 96) and reason == (None if target <= 96 else 'json_depth')
        row = cli_case(raw, NONCE if decoded else None, directory, 'depth-'+str(target))
        row.update(independent_depth=target, decoded=decoded, decoder_reason=reason)
        rows.append(row)
    malformed = {'utf8':b'\xff\n','bom':b'\xef\xbb\xbf{}\n',
                 'duplicates':b'{"requestId":"'+NONCE.encode()+b'","requestId":"x"}\n'}
    extras = {name:cli_case(raw,None,directory,name) for name,raw in malformed.items()}
    return {'cases':rows,'malformed':extras,'root_depth':0,'dictionary_keys_counted':True,
            'public_codec':'separate Java probe; Jackson container cap300 is not Python scalar-edge cap96'}


class ObservedGate(ParserGate):
    """Real parser gate with an owned pre-input suspension solely for deterministic kill."""
    def __init__(self, marker):
        super().__init__(); self.marker = marker

    def validate(self, source, *, cancel=None):
        if source != MODE.encode(): return super().validate(source, cancel=cancel)
        key = (self._config.digest, self._config.generation, source)
        assert key not in self._cache, 'TARGET_WAS_CACHED'
        original = subprocess.Popen
        def launch(*args, **kwargs):
            child = original(*args, **kwargs)
            deadline = time.monotonic()+2
            while time.monotonic() < deadline:
                try: executable = os.readlink(f'/proc/{child.pid}/exe')
                except FileNotFoundError: executable = ''
                if 'memfd:' in executable: break
                time.sleep(.001)
            assert 'memfd:' in executable, 'SEALED_PARSER_EXEC_NOT_OBSERVED'
            os.kill(child.pid, signal.SIGSTOP)
            save(self.marker, {'pid':child.pid,'start_ticks':identity.process_start(child.pid),
                 'uncached':True,'sealed_executable':True,'exact_target_sha256':hashlib.sha256(source).hexdigest()})
            return child
        with patch.object(sql_image.subprocess,'Popen',side_effect=launch):
            return super().validate(source, cancel=cancel)


async def proxy_child(configuration):
    """Serve an owned real parser proxy chained only to the canonical shared parser proxy."""
    data = read(configuration)
    gate = ObservedGate(Path(data['marker'])) if data['mode'] == 'child-kill' else ParserGate()
    server = sql_proxy.ProxyServer(sql_connections.PROXY_SOCKET,Path(data['listen']),Path(data['status']),gate)
    loop = asyncio.get_running_loop()
    for name in (signal.SIGTERM,signal.SIGINT): loop.add_signal_handler(name,server.stopping.set)
    await server.run()


def context_child(configuration):
    """Use actual CLI/Store with scoped test data and validated owned proxy endpoint seam."""
    data = read(configuration)
    route = fixtures.TemporaryRoute(data['database'])
    isolated = Path(data['listen']).parent
    dsn = make_conninfo(route.app,host=str(isolated))
    calls = []
    def connection(*args, **kwargs):
        assert not args, 'EXPLICIT_UNEXPECTED_DSN'
        kwargs.pop('client',None)
        calls.append({'endpoint':'owned isolated parser -> canonical parser','client':'allow-recovery'})
        return sql_connections.connect(dsn,allow_temporary=True,client='allow-recovery',**kwargs)
    try:
        with patch.object(sql_connections,'PROXY_DIRECTORY',isolated), \
                patch.object(store_module,'connect',connection), \
                patch.object(cli,'Store',return_value=Store(data['scope'])):
            cli.main()
    finally:
        save(Path(data['telemetry']),{'connection_attempts':calls,'alternate_routes':0})


def await_file(path, child, seconds=15):
    """Bound owned process readiness and never mistake its death for success."""
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        if path.exists(): return
        assert child.poll() is None, 'OWNED_CHILD_DIED_BEFORE_MARKER'
        time.sleep(.005)
    raise AssertionError('OWNED_MARKER_TIMEOUT')


def stop(child):
    """Terminate and reap only a subprocess handle created by this probe."""
    if child.poll() is None:
        child.terminate()
        try: child.wait(timeout=8)
        except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)


def parser_fault(mode, name, scope, args, directory):
    """Perform a literal private service stop or SIGKILL of its exact active parser child."""
    with tempfile.TemporaryDirectory(prefix='allow-p0-') as temporary:
        folder = Path(temporary); listen = folder/'.s.PGSQL.54329'
        configuration = folder/'configuration.json'; marker = folder/'parser.json'
        data = {'mode':mode,'listen':str(listen),'status':str(folder/'status.json'),
                'marker':str(marker),'database':name,'scope':scope,'telemetry':str(folder/'context.json')}
        save(configuration,data); configuration.chmod(0o600)
        proxy = subprocess.Popen([sys.executable,str(__file__),'--proxy-child',str(configuration)],
                                 stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=environment())
        proxy_start = identity.process_start(proxy.pid); child = None; killed = None
        try:
            await_file(listen,proxy)
            assert read(folder/'status.json')['parser']['cache_entries'] == 0
            if mode == 'service-stop':
                stop(proxy)
                assert proxy.returncode == 0 and not listen.exists(), 'SERVICE_STOP_FAILED'
            child = subprocess.Popen([sys.executable,str(__file__),'--context-child',str(configuration)],
                                     stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment())
            child_start = identity.process_start(child.pid)
            child.stdin.write(wire.encode(frame(args))+b'\n'); child.stdin.close(); child.stdin = None
            if mode == 'child-kill':
                await_file(marker,proxy)
                killed = read(marker)
                assert identity.alive(killed['pid'],killed['start_ticks']), 'PARSER_OWNERSHIP_LOST'
                assert Path(f"/proc/{killed['pid']}/stat").read_text().split(') ',1)[1].split()[1] == str(proxy.pid)
                os.kill(killed['pid'],signal.SIGKILL)
            raw, errors = child.communicate(timeout=15)
            assert child.returncode == 0 and not errors, 'CONTEXT_CHILD_FAILED'
            reply = wire.decode(raw,1572865)
            assert reply == {'protocol':1,'requestId':NONCE,'status':'UNAVAILABLE',
                             'data':{'reason':'document_runtime_unavailable'}}, 'PARTIAL_OR_WRONG_FAILURE'
            assert not identity.alive(child.pid,child_start), 'CONTEXT_NOT_REAPED'
            if killed:
                assert not identity.alive(killed['pid'],killed['start_ticks']), 'PARSER_NOT_REAPED'
            stop(proxy)
            assert not identity.alive(proxy.pid,proxy_start) and not listen.exists(), 'PROXY_NOT_REAPED'
            assert not proxy.stderr.read(), 'PROXY_DIAGNOSTIC'
            status = read(folder/'status.json'); telemetry = read(folder/'context.json')
            if killed:
                assert status['clients']['allow-recovery']['rejected'] == 1
                assert status['parser']['reserved_execution_descriptors'] == 0
            assert status['parser']['shutdown_complete'] and status['active'] == 0
            assert len(telemetry['connection_attempts']) == 1 and telemetry['alternate_routes'] == 0
            return {'mode':mode,'status':reply['status'],'partial_context':False,'mutation_uncertainty':False,
                    'proxy_pid':proxy.pid,'proxy_start_ticks':proxy_start,'proxy_reaped':True,
                    'context_pid':child.pid,'context_start_ticks':child_start,'context_reaped':True,
                    'parser_child':killed,'owned_parser_shutdown_complete':True,'telemetry':telemetry,
                    'isolated_counters':status['clients']['allow-recovery'],
                    'worker_nonlaunch':'CLI contains no worker factory; inherited Java context-failure ordering is composition, not new HTTP trace'}
        finally:
            if killed and identity.alive(killed['pid'],killed['start_ticks']): os.kill(killed['pid'],signal.SIGKILL)
            if child is not None: stop(child)
            stop(proxy); proxy.stderr.close()


def parser_checks(directory):
    """Provision and delete only one registered owned database through canonical SQLeanParser."""
    name = 'allow_recovery_'+uuid.uuid4().hex
    route = fixtures.TemporaryRoute(name)
    scope = {key:str(uuid.uuid4()) for key in ('principalId','workspaceId','logicalLaunchId')}
    created = False; rows = []; report = {}
    try:
        with sql_connections.connect(admin=True,client='allow-recovery-control',autocommit=True) as connection:
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name))); created = True
        with ExitStack() as stack:
            route.install(stack); migration.migrate(); store = Store(scope)
            assert store.initialize('authored-document-recovery-v1')['status'] == 'READY'
            document,_,_ = fixtures.commit(store)
            args = {'documentId':document,'revision':0,'ids':[]}
            assert store.validation_context(args)['documentId'] == document
            before = fixtures.snapshot(route.admin)
            for mode in ('service-stop','child-kill'):
                row = parser_fault(mode,name,scope,args,directory)
                assert fixtures.snapshot(route.admin) == before, 'DURABLE_MUTATION'
                row['durable_unchanged'] = True; rows.append(row)
                save(directory/'parser-progress.json',{'cases':rows})
            report.update(cases=rows, durable_before=before, positive_control='actual Store context succeeds before faults')
    finally:
        if created:
            with sql_connections.connect(admin=True,client='allow-recovery-control',autocommit=True) as connection:
                connection.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
                report['owned_fixture_database_dropped'] = connection.execute(
                    'SELECT count(*) FROM pg_database WHERE datname=%s',(name,)).fetchone()[0] == 0
            save(directory/'database-cleanup.json',{'owned_fixture_database_dropped':report['owned_fixture_database_dropped']})
    assert report['owned_fixture_database_dropped']
    return report


def java_builds(directory):
    """Run style once and two isolated clean compiles/executions with deterministic class bytes."""
    registration = read(HERE/'registration.json'); classpath = registration['java_classpath']
    source = HERE/'java/dev/allow/backend/PublicNestingProbe.java'
    command = ['/usr/bin/java','-jar',str(ROOT/'.tools/checkstyle-10.21.2-all.jar'),
               '-c',str(ROOT/'config/checkstyle.xml'),str(source)]
    checked = subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert checked.returncode == 0, 'JAVA_STYLE_FAILURE:'+checked.stdout
    rows = []
    for index in (1,2):
        with tempfile.TemporaryDirectory(prefix='allow-p0-java-') as temporary:
            compile_command = ['/usr/bin/javac','-cp',classpath,'-d',temporary,str(source),
                str(ROOT/'backend/src/main/java/dev/allow/backend/DocumentJson.java'),
                str(ROOT/'backend/src/main/java/dev/allow/worker/JsonWire.java')]
            compiled = subprocess.run(compile_command,capture_output=True,text=True,timeout=30)
            assert compiled.returncode == 0, 'JAVA_COMPILE_FAILURE'
            result = subprocess.run(['/usr/bin/java','-cp',temporary+':'+classpath,
                                    'dev.allow.backend.PublicNestingProbe'],capture_output=True,text=True,timeout=15)
            assert result.returncode == 0 and not result.stderr, 'JAVA_NESTING_FAILURE'
            hashes = {str(path.relative_to(temporary)):sha(path) for path in sorted(Path(temporary).rglob('*.class'))}
            rows.append({'build':index,'compile_exit':0,'execution_exit':0,'stdout':result.stdout,'class_sha256':hashes})
    assert rows[0]['class_sha256'] == rows[1]['class_sha256'] and rows[0]['stdout'] == rows[1]['stdout']
    return {'style_exit':0,'builds':rows,'deterministic':True,'temporary_outputs_removed':True}


def run():
    """Execute the frozen finite suite, preserve every failed run and sanitize exceptions."""
    registration = verify(); started = shared_identity()
    directory = HERE/'runs'/datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%SZ')
    directory.mkdir(parents=True,exist_ok=False)
    report = {'status':'RUNNING','input_root_sha256':registration['input_root_sha256'],
              'verifier_sha256':sha(Path(__file__)),'checks':{},'main_test_counts':{'java':189,'python':186}}
    save(directory/'registration.json',registration)
    try:
        for label,operation in [('RP01',wire_boundaries),('RP02',nesting_boundaries),
                                ('PUBLIC-NESTING',java_builds),('RP03',parser_checks)]:
            evidence = operation(directory)
            report['checks'][label] = {'status':'PASS','evidence':evidence}
            save(directory/'report.json',report)
        verify()
        assert shared_identity() == started, 'SHARED_PROXY_MUTATED'
        report.update(status='PASS',inputs_unchanged=True,shared_proxy_identity_unchanged=True,
                      shared_proxy_identity=started)
    except BaseException as failure:
        report.update(status='FAIL',failure_type=type(failure).__name__,failure_stage=label)
        frames = []; trace = failure.__traceback__
        while trace:
            frames.append({'file':Path(trace.tb_frame.f_code.co_filename).name,'line':trace.tb_lineno,
                           'function':trace.tb_frame.f_code.co_name}); trace = trace.tb_next
        report['failure_frames'] = frames
        if isinstance(failure,AssertionError): report['assertion'] = str(failure)[:2000]
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    save(directory/'report.json',report)
    print(json.dumps({'status':report['status'],'report':str(directory/'report.json'),'sha256':sha(directory/'report.json')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--execute',action='store_true')
    parser.add_argument('--audit-cli',type=Path); parser.add_argument('--proxy-child',type=Path)
    parser.add_argument('--context-child',type=Path); arguments = parser.parse_args()
    if arguments.audit_cli: audited_cli(arguments.audit_cli)
    elif arguments.proxy_child: asyncio.run(proxy_child(arguments.proxy_child))
    elif arguments.context_child: context_child(arguments.context_child)
    elif arguments.execute: sys.exit(run())
    else: parser.error('explicit registered operation required')
