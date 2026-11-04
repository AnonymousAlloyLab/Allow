#!/usr/bin/env python3
"""Registered finite validation-context gap probes; authored temporary database only.

All actual database connections use the unchanged canonical SQLeanParser helper.
The fault seams are private to this process and never alter a server, credentials,
production source, persisted parser policy, or an existing application's scope.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT/'retrieval'), str(ROOT/'scripts')]
import psycopg
from psycopg import pq, sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from allow_documents import cli, migration, store as store_module, wire
from allow_documents.store import Store
from allow_retrieval.sql_connections import connect, configured_dsn, PROXY_DIRECTORY, PORT
import document_recovery_test as fixtures

HERE = Path(__file__).resolve().parent
STATUS = ROOT/'.runtime/corpus/sql-proxy/status.json'
MODE = 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'
STAGES = ('mode','tenant','project','purpose','head','base','history','exit')


def dump(path, value):
    """Write one bounded, deterministic gate artifact using no private source bytes."""
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')


def sha(path):
    """Return exact bytes' identity for source and result pinning."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status():
    """Read the proxy's public sanitized counters and sealed generation identity."""
    return json.loads(STATUS.read_text())


def sealed(value):
    """Select runtime identity fields that may not change during these probes."""
    return {key:value[key] for key in ('pid','started','loaded_inputs','parser') if key!='parser'} | {
        'parser':{key:value['parser'][key] for key in ('generation','snapshot_sha256','binary_sha256',
                  'configuration_sha256','mapping_sha256','identity_mode','policy','profile')}}


def counters(value, client='allow-recovery'):
    """Select only numeric protocol counters for the probe's dedicated client tag."""
    return value.get('clients',{}).get(client,{})


def delta(before, after):
    """Subtract monotonically increasing sanitized counters without SQL or parameters."""
    return {key:after.get(key,0)-before.get(key,0) for key in sorted(set(before)|set(after))}


def await_counter(before, key, minimum=1):
    """Allow the proxy's asynchronous status publication a bounded two-second window."""
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        current=counters(status())
        if current.get(key,0)-before.get(key,0)>=minimum:
            return delta(before,current)
        time.sleep(.02)
    raise AssertionError('required_proxy_counter_not_observed:'+key)


def scope():
    """Generate an unrelated ephemeral principal, workspace, and launch identity."""
    return {key:str(uuid.uuid4()) for key in ('principalId','workspaceId','logicalLaunchId')}


def frame(args):
    """Build a closed nonce-bound authored validation-context request."""
    return {'protocol':1,'requestId':str(uuid.uuid4()),'operation':'validationContext','args':args}


def invoke(store, request):
    """Run the unchanged CLI codec and dispatch against private byte streams."""
    output=io.BytesIO()
    with ExitStack() as stack:
        stack.enter_context(patch.object(cli,'Store',return_value=store))
        stack.enter_context(patch.object(cli.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(wire.encode(request)))))
        stack.enter_context(patch.object(cli.sys,'stdout',SimpleNamespace(buffer=output)))
        cli.main()
    raw=output.getvalue()
    assert raw.endswith(b'\n') and raw.count(b'\n')==1 and len(raw)<=1572865
    result=wire.decode(raw,1572865)
    assert result['requestId']==request.get('requestId')
    return result, len(raw)


def unavailable(result):
    """Require the read-only typed failure with no partial context or mutation claim."""
    assert result['status']=='UNAVAILABLE', result['status']
    assert result['data']=={'reason':'document_runtime_unavailable'}
    assert 'artifact' not in result['data'] and 'ownedIdInventory' not in result['data']


def stage_of(statement):
    """Classify only fixed production context statements; never publish their values."""
    if statement==MODE:return 'mode'
    if not isinstance(statement,str):return None
    for key in ('tenant','project','purpose'):
        if statement.startswith("SELECT set_config('allow."+key+"'"):return key
    if statement.startswith('SELECT head_revision FROM documents.document'):return 'head'
    if statement.startswith('SELECT r.revision,r.target_revision,r.direction,a.content'):return 'base'
    if statement=='SELECT content FROM documents.artifact WHERE document_id=%s':return 'history'
    return None


class CorruptCursor:
    """Replace only a returned authored content field to exercise the decoder boundary."""
    def __init__(self, cursor):
        """Retain the actually executed proxy-backed cursor."""
        self.cursor=cursor

    def fetchone(self):
        """Return a malformed synthetic content blob after the actual base query."""
        row=dict(self.cursor.fetchone());row['content']=b'{';return row

    def __iter__(self):
        """Corrupt one history row and retain the actual cursor iteration semantics."""
        for index,row in enumerate(self.cursor):
            yield dict(row,content=b'{') if index==0 else row


class ObservedConnection:
    """Local adapter around a real canonical connection for explicit fault injection."""
    def __init__(self, connection, control):
        """Record ownership and optional post-authentication libpq trace destination."""
        self.connection=connection;self.control=control;self.active=False
        self.tracefile=tempfile.TemporaryFile() if control.get('trace') else None
        self.tracefd=None
        if self.tracefile is not None:
            self.tracefd=os.dup(self.tracefile.fileno())
            connection.pgconn.trace(self.tracefd)
            connection.pgconn.set_trace_flags(pq.Trace.SUPPRESS_TIMESTAMPS|pq.Trace.REGRESS_MODE)

    def __enter__(self):
        """Preserve the real connection's context entry."""
        self.connection.__enter__();return self

    def before(self, stage):
        """Inject a declared private fault only at the selected context stage."""
        control=self.control
        if control.get('stage')!=stage:return
        control['injected']=control.get('injected',0)+1
        fault=control.get('fault')
        if fault=='parser':self.connection.execute('SELEC 1')
        if fault=='transport':
            self.connection.close()
            if stage=='exit':self.connection.commit()
        if fault=='sleep':
            dump(Path(control['marker']),{'backend_pid':self.connection.info.backend_pid,'stage':stage})
            self.connection.execute('SELECT pg_sleep(60)')

    def execute(self, statement, *args, **kwargs):
        """Execute actual SQL, then apply the first-snapshot barrier or decode seam."""
        stage=stage_of(statement)
        if stage=='mode':self.active=True
        if self.active:
            self.control.setdefault('stages',[]).append(stage)
            self.before(stage)
        result=self.connection.execute(statement,*args,**kwargs)
        if self.active and stage=='tenant' and self.control.get('barrier'):
            self.control['entered'].set()
            assert self.control['resume'].wait(10), 'first_scope_barrier_timeout'
        if self.active and self.control.get('fault')=='decode' and self.control.get('stage')==stage:
            return CorruptCursor(result)
        return result

    def __exit__(self, kind, value, traceback):
        """Preserve real rollback/commit/close and collect trace only after closure."""
        try:
            if self.active and kind is None:
                self.control.setdefault('stages',[]).append('exit')
                self.before('exit')
            return self.connection.__exit__(kind,value,traceback)
        except BaseException:
            self.connection.close()
            raise
        finally:
            self.control['closed']=bool(self.connection.closed)
            if self.tracefile is not None:
                self.tracefile.seek(0);raw=self.tracefile.read()
                self.control['protocol_raw']=raw
                self.tracefile.close()
                try:os.close(self.tracefd)
                except OSError:pass


class Route(fixtures.TemporaryRoute):
    """Temporary database routing with local observability, never a proxy bypass."""
    def __init__(self,name):
        """Reuse validated temporary DSNs and start with no fault enabled."""
        super().__init__(name);self.control=None

    def connect(self,*args,**kwargs):
        """Use real authenticated canonical transport, optionally failing one login."""
        if self.control and self.control.get('fault')=='auth' and not kwargs.get('admin'):
            wrong=make_conninfo(self.app,password='authored-intentionally-invalid-password-'+uuid.uuid4().hex)
            try:
                return connect(wrong,allow_temporary=True,client='allow-recovery',row_factory=dict_row)
            except psycopg.OperationalError as failure:
                self.control['actual_auth_error']=type(failure).__name__
                self.control['sqlstate']=failure.sqlstate
                raise
        connection=super().connect(*args,**kwargs)
        if self.control is None:return connection
        self.control['endpoint']={'host':connection.info.host,'port':str(connection.info.port),
            'application_name':connection.info.get_parameters().get('application_name'),
            'database_kind':'owned_temporary_database'}
        return ObservedConnection(connection,self.control)


def durable(route):
    """Hash every owned document table, including full receipts, admissions and quotas."""
    return fixtures.snapshot(route.admin)


def parse_trace(raw):
    """Reduce actual post-auth protocol frames to closed stage tags and message counts."""
    commands=[];complete=[];counts={}
    for line in raw.decode('utf-8').splitlines():
        fields=line.split('\t')
        assert len(fields)>=3
        direction,kind=fields[0],fields[2]
        counts[direction+':'+kind]=counts.get(direction+':'+kind,0)+1
        strings=re.findall(r'"((?:[^"\\]|\\.)*)"','\t'.join(fields[3:]))
        if direction=='F' and kind in ('Query','Parse'):
            command=strings[0 if kind=='Query' else 1]
            tag=command if command in ('BEGIN','COMMIT') else stage_of(command.replace('$1','%s').replace('$2','%s'))
            assert tag is not None, 'unrecognized_authored_protocol_statement'
            commands.append(tag)
        if direction=='B' and kind=='CommandComplete':complete.extend(strings)
    expected=['BEGIN','mode','tenant','project','purpose','head','base','history','COMMIT']
    assert commands==expected, commands
    assert complete[0]=='BEGIN' and complete[-1]=='COMMIT'
    return {'commands':commands,'frame_counts':counts,'command_completions':complete,
            'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),
            'raw_retention':'private temporary file deleted; only sanitized stage tags retained'}


def trace_check(route,store,args):
    """VC02/22: observe actual driver BEGIN, isolation, all scopes, data, and COMMIT."""
    before=counters(status());state=durable(route);control={'trace':True};route.control=control
    try:
        result,_=invoke(store,frame(args));assert result['status']=='OK'
    finally:route.control=None
    assert control['closed'] and state==durable(route)
    trace=parse_trace(control.pop('protocol_raw'))
    endpoint=control['endpoint']
    assert endpoint['host']==str(PROXY_DIRECTORY) and endpoint['port']==PORT
    assert endpoint['application_name']=='allow-recovery'
    trace.update(endpoint=endpoint,proxy_counter_delta=await_counter(before,'accepted',9),
                 durable_unchanged=True,connection_closed=True)
    return trace


def first_scope_race(route,store,args):
    """VC06: commit between first tenant SELECT and the remaining scope settings."""
    entered=threading.Event();resume=threading.Event()
    future_artifact=fixtures.artifact('AfterFirstScope')
    new_id=future_artifact['module']['signatures'][0]['id']
    wanted=dict(args,ids=sorted(args['ids']+[new_id]))
    control={'barrier':True,'entered':entered,'resume':resume};route.control=control
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending=executor.submit(store.validation_context,wanted)
        assert entered.wait(5), 'first_scope_not_reached'
        assert control['stages']==['mode','tenant']
        route.control=None
        try:
            with patch.object(fixtures,'artifact',return_value=future_artifact):
                fixtures.commit(Store(store.scope),args['documentId'],1,'AfterFirstScope')
        finally:resume.set()
        old=pending.result(timeout=10)
    current=store.validation_context(wanted)
    assert old['headObserved']==1 and new_id not in old['ownedIdInventory']
    assert current['headObserved']==2 and current['ownedIdInventory'][new_id]=='signature'
    assert old['artifact']==current['artifact'] and old['baseRevision']==current['baseRevision']==0
    return {'barrier_after':'first tenant SELECT returned, before project SELECT',
            'old_head':1,'new_head':2,'base_immutable':True,'new_identity_visible_only_in_new_snapshot':True}


def size_checks(store,document):
    """VC13: prove reachable maximum bytes and test exact/over invalid-ID guards."""
    ids=['server:'+str(uuid.UUID(int=index+1)) for index in range(4096)]
    valid={'documentId':document,'revision':9007199254740991,'ids':ids}
    assert len(wire.encode(valid))<wire.MAX_REQUEST
    assert len(store._context_arguments(valid)[2])==4096
    cases=[]
    for size,expected in ((262144,'invalid_server_id'),(262145,'ids_limit')):
        args={'documentId':document,'revision':9007199254740991,'ids':['']}
        args['ids']=['x'*(size-len(wire.encode(args)))]
        assert len(wire.encode(args))==size
        with patch.object(store_module,'connect') as blocked:
            try:store.validation_context(args)
            except ValueError as failure:
                reason=str(failure)
            else:raise AssertionError('invalid_size_fixture_accepted')
            blocked.assert_not_called()
        assert reason==expected,(size,reason)
        cases.append({'encoded_args_bytes':size,'reason':reason,'sql_calls':0})
    return {'maximum_valid_compact_args_bytes':len(wire.encode(valid)),
            'maximum_ids':4096,'document_id_bytes':43,'identity_bytes':43,
            'revision_digits':16,'positive_256KiB_boundary':'unreachable for the closed canonical shape',
            'adversarial_invalid_id_cases':cases}


def shape_checks(store,args):
    """VC01: add missing outer, container, and argument-key negative cases."""
    good=frame(args);cases=[]
    for key in good:cases.append(('outer_missing_'+key,{k:v for k,v in good.items() if k!=key}))
    for value in (None,[],0,'fixture'):cases.append(('args_'+type(value).__name__,dict(good,args=value)))
    for key in args:cases.append(('args_missing_'+key,dict(good,args={k:v for k,v in args.items() if k!=key})))
    output=[]
    with patch.object(store_module,'connect') as blocked:
        for label,request in cases:
            result,_=invoke(store,request)
            assert result['status']=='ERROR'
            output.append({'case':label,'status':'ERROR'})
        blocked.assert_not_called()
    return {'cases':output,'sql_calls':0}


def fault_checks(route,store,args):
    """VC14/18: distinguish real parser/auth rejection from local transport/decode seams."""
    cases=[(fault,stage) for fault in ('parser','transport') for stage in STAGES]
    cases += [('decode','base'),('decode','history'),('auth','connect')]
    output=[]
    for fault,stage in cases:
        before=durable(route);counter=counters(status());control={'fault':fault,'stage':stage}
        route.control=control
        try:result,byte_count=invoke(store,frame(args));unavailable(result)
        finally:route.control=None
        assert durable(route)==before
        if fault!='auth':assert control.get('injected')==1 and control['closed']
        detail={'fault':fault,'stage':stage,'status':'UNAVAILABLE','response_bytes':byte_count,
                'durable_unchanged':True,'actual_or_injected':{
                    'parser':'real proxy rejects fixed invalid SQL injected before declared stage',
                    'auth':'real proxy login rejected using transient synthetic wrong password',
                    'transport':'local owned connection close injected before declared stage',
                    'decode':'real query then synthetic malformed authored content'}[fault]}
        if fault=='parser':detail['proxy_counter_delta']=await_counter(counter,'rejected')
        if fault=='auth':
            assert control.get('actual_auth_error')=='OperationalError'
            detail['driver_exception']='OperationalError';detail['sqlstate']=control['sqlstate']
            detail['proxy_counter_delta']=await_counter(counter,'connections')
        output.append(detail)
    for fault,stage in (('parser','mode'),('parser','base'),('auth','connect')):
        control={'fault':fault,'stage':stage};before=durable(route);route.control=control
        try:result,_=invoke(store,frame(dict(args,ids=[])));unavailable(result)
        finally:route.control=None
        assert durable(route)==before
        output.append({'fault':fault,'stage':stage,'empty_ids':True,'status':'UNAVAILABLE','durable_unchanged':True})
    return {'cases':output,'literal_parser_shutdown':'not performed; this probe does not claim that coverage',
            'transaction_exit_transport':'connection closes before real context exit; no success frame published'}


def owned_backend(route,pid,cancel=False):
    """Inspect or cancel only the exact PID in this helper's owned temporary database."""
    with connect(route.admin,admin=True,allow_temporary=True,client='allow-recovery-control',row_factory=dict_row) as c:
        row=c.execute('SELECT pid,datname,wait_event FROM pg_stat_activity WHERE pid=%s',(pid,)).fetchone()
        if row is None:return None
        assert row['datname']==route.name,'foreign_backend_forbidden'
        if cancel:assert c.execute('SELECT pg_cancel_backend(%s)',(pid,)).fetchone()['pg_cancel_backend']
        return {'present':True,'wait_event':row['wait_event']}


def child_main(configuration):
    """Run unchanged CLI in a capped owned process with a declared blocking-read seam."""
    value=json.loads(configuration.read_text());route=Route(value['database'])
    route.control={'fault':'sleep','stage':'history','marker':value['marker']}
    with ExitStack() as stack:
        route.install(stack)
        stack.enter_context(patch.object(cli,'Store',return_value=Store(value['scope'])))
        cli.main()


def interruption(route,store,args,directory,kind):
    """VC18: real query cancellation or20s CLI timeout, exact state and cleanup checks."""
    marker=directory/(kind+'-marker.json');configuration=directory/(kind+'-private-config.json')
    dump(configuration,{'database':route.name,'scope':store.scope,'marker':str(marker)})
    os.chmod(configuration,0o600)
    before=durable(route);start=time.monotonic()
    command=['prlimit','--as=2147483648','--cpu=20','--',sys.executable,str(Path(__file__)),
             '--child',str(configuration)]
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=output,stderr=errors,
                                 cwd=ROOT,start_new_session=True)
        process.stdin.write(wire.encode(frame(args)));process.stdin.close()
        try:
            while not marker.exists() and process.poll() is None and time.monotonic()-start<5:time.sleep(.01)
            assert marker.exists(),'child_did_not_reach_blocking_read'
            pid=json.loads(marker.read_text())['backend_pid']
            while time.monotonic()-start<7:
                observed=owned_backend(route,pid)
                if observed and observed['wait_event']=='PgSleep':break
                time.sleep(.02)
            assert observed and observed['wait_event']=='PgSleep','blocking_SQL_not_observed'
            if kind=='cancel':
                owned_backend(route,pid,cancel=True);process.wait(timeout=5)
            else:
                try:process.wait(timeout=max(.001,20-(time.monotonic()-start)))
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                else:raise AssertionError('timeout_child_exited_early')
            elapsed=time.monotonic()-start
            output.seek(0);raw=output.read(1572866);errors.seek(0);diagnostic=errors.read(65537)
            assert not diagnostic,'unexpected_child_stderr'
            if kind=='cancel':
                assert process.returncode==0;unavailable(wire.decode(raw,1572865))
            else:assert process.returncode==-signal.SIGKILL and raw==b''
            cleanup_cancelled=False
            if owned_backend(route,pid) is not None:
                owned_backend(route,pid,cancel=True);cleanup_cancelled=True
            deadline=time.monotonic()+5
            while owned_backend(route,pid) is not None and time.monotonic()<deadline:time.sleep(.02)
            assert owned_backend(route,pid) is None,'owned_backend_survived_cleanup'
        finally:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
            configuration.unlink(missing_ok=True);marker.unlink(missing_ok=True)
    assert durable(route)==before
    return {'kind':kind,'elapsed_seconds':elapsed,'returncode':process.returncode,
            'response_bytes':len(raw),'response_status':'UNAVAILABLE' if kind=='cancel' else 'no frame; supervisor timeout',
            'blocking_read_observed':'PgSleep','cancel_mechanism':'SQL pg_cancel_backend through canonical proxy',
            'cleanup_cancel_needed':cleanup_cancelled,'owned_process_reaped':True,'owned_backend_absent':True,
            'durable_before':before,'durable_after_equal':True,'caps':{'wall_seconds':20,'cpu_seconds':20,'as_bytes':2147483648}}


def verify_registration():
    """Refuse execution unless every preregistered source and protocol hash matches."""
    value=json.loads((HERE/'registration.json').read_text())
    for item in value['files']:assert sha(ROOT/item['path'])==item['sha256'],item['path']
    canonical=json.dumps(value['files'],sort_keys=True,separators=(',',':')).encode()
    assert hashlib.sha256(canonical).hexdigest()==value['input_root_sha256']
    return value['input_root_sha256']


def traceback_items(item):
    """Yield frame locations only; never expose locals or arbitrary exception text."""
    while item is not None:
        yield item
        item=item.tb_next


def run():
    """Execute the finite registered suite and unconditionally drop only its database."""
    root=verify_registration();run_id=datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%SZ')
    directory=HERE/'runs'/run_id;directory.mkdir(parents=True,exist_ok=False)
    name='allow_recovery_'+uuid.uuid4().hex;route=Route(name);runtime_before=status()
    report={'status':'RUNNING','input_root_sha256':root,'checks':{},'run_id':run_id,
            'scope':'supplemental gate-local probes; existing186Python/189Java counts unchanged',
            'fixture_semantics':'authored storage-shaped artifact; no independent Alloy validation claim'}
    created=False
    try:
        with connect(configured_dsn(True),admin=True,client='allow-recovery-control',autocommit=True) as c:
            c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)));created=True
        with ExitStack() as stack:
            route.install(stack);migration.migrate();store=Store(scope())
            assert store.initialize('authored-document-recovery-v1')['status']=='READY'
            document,_,_=fixtures.commit(store)
            _,_,outcome=fixtures.commit(store,document,0,'BeforeFirstScope')
            initial=wire.decode(outcome)['data']['artifact']['module']['signatures'][0]['id']
            args={'documentId':document,'revision':0,'ids':[initial]}
            checks=(('P01_protocol_order',lambda:trace_check(route,store,args)),
                    ('P02_first_scope_race',lambda:first_scope_race(route,store,args)),
                    ('P03_encoded_size',lambda:size_checks(store,document)),
                    ('P04_closed_shapes',lambda:shape_checks(store,args)),
                    ('P05_staged_faults',lambda:fault_checks(route,store,args)),
                    ('P06_actual_cancel',lambda:interruption(route,store,args,directory,'cancel')),
                    ('P07_actual_timeout',lambda:interruption(route,store,args,directory,'timeout')))
            for label,check in checks:
                started=time.monotonic();result=check()
                report['checks'][label]={'status':'PASS','seconds':time.monotonic()-started,'evidence':result}
                dump(directory/'report.json',report)
        report['status']='PASS'
    except BaseException as failure:
        report['status']='FAIL';report['failure_type']=type(failure).__name__
        report['failure_stage']=label if 'label' in locals() else 'setup'
        report['failure_frames']=[{'file':str(Path(item.tb_frame.f_code.co_filename).name),'line':item.tb_lineno,'function':item.tb_frame.f_code.co_name} for item in traceback_items(failure.__traceback__)]
        if isinstance(failure,ValueError) and re.fullmatch(r'[a-z_]{1,80}',str(failure)):report['reason']=str(failure)
        # Assertions are authored identifiers only; unknown exception text can contain secrets.
        if isinstance(failure,AssertionError):report['assertion']=str(failure)[:300]
    finally:
        route.control=None
        if created:
            with connect(configured_dsn(True),admin=True,client='allow-recovery-control',autocommit=True) as c:
                c.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
                absent=c.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(name,)).fetchone()[0]==0
                report['owned_fixture_database_dropped']=absent
        report['proxy_identity_unchanged']=sealed(status())==sealed(runtime_before)
        assert report['proxy_identity_unchanged']
        report['runtime_identity']=sealed(runtime_before)
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        dump(directory/'report.json',report)
        print(json.dumps({'status':report['status'],'report':str(directory/'report.json'),'sha256':sha(directory/'report.json')}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true')
    parser.add_argument('--child',type=Path);arguments=parser.parse_args()
    if arguments.child:child_main(arguments.child)
    elif arguments.execute:sys.exit(run())
    else:parser.error('explicit --execute required after registration')
