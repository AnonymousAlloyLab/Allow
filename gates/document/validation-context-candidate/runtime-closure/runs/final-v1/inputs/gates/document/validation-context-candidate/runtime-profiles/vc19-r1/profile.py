#!/usr/bin/env python3
"""Registered storage-shaped VC19 profile; all SQL uses the canonical proxy.

The only production seams select an owned temporary database/test scope and
observe libpq result metadata. The production CLI/store bodies are unchanged.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
from unittest.mock import patch
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0,str(ROOT/'retrieval'))
from psycopg import sql
from psycopg.rows import dict_row
from allow_documents import cli, identity, migration, wire
from allow_documents.store import Store
from allow_retrieval.sql_connections import connect, configured_dsn, database_dsn, PROXY_DIRECTORY, PORT


def packed(value):
    """Encode deterministic metadata without serializing credentials."""
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def sha(path):
    """Hash a frozen input or raw result file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    """Persist an owned report with exact newlines and private permissions."""
    path.write_text(json.dumps(value,indent=2)+'\n')
    path.chmod(0o600)


def check_inputs():
    """Reject a source/configuration change against the pre-execution registry."""
    manifest=json.loads((HERE/'manifest.json').read_text())
    assert hashlib.sha256(packed(manifest['files'])).hexdigest()==manifest['input_root_sha256']
    assert all(sha(ROOT/row['path'])==row['sha256'] for row in manifest['files'])
    return manifest['input_root_sha256']


def vm(pid='self'):
    """Read kernel memory high-water values, exposing no process environment."""
    values={}
    try:
        for line in Path('/proc',str(pid),'status').read_text().splitlines():
            name,_,value=line.partition(':')
            if name in {'VmPeak','VmSize','VmHWM','VmRSS'}:
                values[name+'_bytes']=int(value.strip().split()[0])*1024
    except FileNotFoundError:
        pass
    return values


def route(name,admin=False,client='allow-tests',**kwargs):
    """Connect only to a generated temporary database via unchanged routing policy."""
    assert re.fullmatch(r'allow_sql_test_[0-9a-f]{32}',name)
    dsn=database_dsn(configured_dsn(admin,client),name,admin=admin,client=client)
    connection=connect(dsn,admin=admin,allow_temporary=True,client=client,**kwargs)
    assert connection.info.host==str(PROXY_DIRECTORY) and str(connection.info.port)==PORT
    assert connection.info.dbname==name
    return connection


class ObservedConnection:
    """Observe the already-buffered libpq result without changing returned cursors."""
    def __init__(self,connection,stats):
        """Retain the owned connection and bounded numeric instrumentation state."""
        self.connection=connection
        self.stats=stats

    def __enter__(self):
        """Enter the real driver's transaction lifecycle."""
        self.connection.__enter__()
        return self

    def __exit__(self,*args):
        """Delegate commit/rollback/close before marking connection completion."""
        try:
            return self.connection.__exit__(*args)
        finally:
            self.stats['connection_closed']=bool(self.connection.closed)

    def execute(self,statement,*args,**kwargs):
        """Record actual client-side buffering before production row iteration."""
        started=time.monotonic()
        cursor=self.connection.execute(statement,*args,**kwargs)
        if statement=='SELECT content FROM documents.artifact WHERE document_id=%s':
            observed=time.monotonic()
            result=cursor.pgresult
            payload=sum(len(result.get_value(index,0)) for index in range(result.ntuples))
            self.stats['history']={'rows_buffered_before_iteration':result.ntuples,
                'raw_value_bytes_buffered':payload,'column_format':result.fformat(0),
                'execute_wall_seconds':observed-started,'inspection_wall_seconds':time.monotonic()-observed,
                'memory_before_iteration':vm(),'cursor_type':type(cursor).__name__}
        return cursor


def child(control):
    """Run actual CLI dispatch/store under caps, using only an owned test route."""
    config=json.loads(Path(control).read_text())
    stats={'history':None,'request_failure_class':None,
           'rlimit_as':list(resource.getrlimit(resource.RLIMIT_AS)),
           'rlimit_cpu':list(resource.getrlimit(resource.RLIMIT_CPU)), 'entry_memory':vm()}
    def app_connect(*args,**kwargs):
        """Change only the registered temporary DB while preserving role and proxy."""
        assert not args and not kwargs.pop('admin',False)
        kwargs.pop('client',None)
        return ObservedConnection(route(config['database'],client='allow-app',**kwargs),stats)
    instance=Store(config['scope'])
    original=instance.validation_context
    def observed_context(args):
        """Record an exception class only, then preserve production classification."""
        try:
            return original(args)
        except BaseException as error:
            stats['request_failure_class']=type(error).__name__
            raise
    try:
        with patch('allow_documents.store.connect',app_connect):
            with patch.object(instance,'validation_context',observed_context):
                with patch.object(cli,'Store',return_value=instance):
                    cli.main()
    finally:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        stats.update(final_memory=vm(),self_maxrss_bytes=usage.ru_maxrss*1024,
                     self_cpu_seconds=usage.ru_utime+usage.ru_stime)
        save(Path(config['telemetry']),stats)


def identifier(seed,label):
    """Derive fixture UUIDs deterministically while keeping database ownership random."""
    return 'server:'+str(uuid.UUID(bytes=uuid.uuid5(uuid.UUID(seed),label).bytes,version=4))


def empty_module():
    """Supply the exact collection shape used by persisted block artifacts."""
    return {'version':1,'signatures':[],'fields':[],'predicates':[],'facts':[],
            'assertions':[],'commands':[],'nodes':[]}


def fixture(config,index,padding):
    """Build explicitly storage-shaped artifact, original request and full outcome."""
    module=empty_module()
    server=identifier(config['seed'],'definition-'+str(index))
    draft='draft:'+str(uuid.UUID(bytes=uuid.uuid5(uuid.UUID(config['seed']),'draft-'+str(index)).bytes,version=4))
    if index:
        module['signatures']=[{'tag':'signature','id':server,'name':'Profile','multiplicity':'set'}]
    source='' if index==0 else '//'+padding+'\nsig Profile {}\n'
    artifact={'artifactId':identifier(config['seed'],'artifact-'+str(index)),'mode':'BLOCK_SUPPORTED',
        'source':source,'sourceHash':hashlib.sha256(source.encode()).hexdigest(),'module':module,
        'occurrences':[],'trivia':[],'analysisDescriptors':[],'policyVersion':'vc19-storage-shaped-v1',
        'dependencyHash':hashlib.sha256(b'not-an-Alloy-runtime-validation').hexdigest()}
    key=uuid.uuid5(uuid.UUID(config['seed']),'key-'+str(index)).hex
    if index==0:
        body={'idempotencyKey':key,'title':'VC19 storage-shaped fixture'}
    elif index==1:
        body={'idempotencyKey':key,'expectedRevision':index-1,'candidate':{'mode':'SOURCE','source':source}}
    else:
        candidate=json.loads(json.dumps(module));candidate['signatures'][0]['id']=draft
        body={'idempotencyKey':key,'expectedRevision':index-1,'candidate':{'mode':'BLOCK_SUPPORTED',
               'module':candidate,'presentationCopies':[]}}
    mapping={} if index<2 else {draft:server}
    outcome={'protocol':1,'requestId':str(uuid.uuid5(uuid.UUID(config['seed']),'response-'+str(index))),
        'status':'COMMITTED','data':{'documentId':config['document'],'revision':index,
        'artifact':artifact,'idRemapping':mapping}}
    a,b,o=wire.encode(artifact),wire.encode(body),wire.encode(outcome)
    wire.artifact(artifact,artifact['policyVersion'])
    return artifact,a,b,o,key,2*len(b)+len(o)+len(a)+8192


def setup_case(database,count,budget):
    """Populate one isolated scope with exact stored bytes and production charge totals."""
    config={'database':database,'seed':str(uuid.uuid4()),'document':wire.fresh_id(),
        'scope':{'principalId':str(uuid.uuid4()),'workspaceId':str(uuid.uuid4()),'logicalLaunchId':str(uuid.uuid4())}}
    baseline=sum(fixture(config,index,'')[-1] for index in range(count))
    width=(budget-baseline)//(2*count)
    assert 0<width<32740
    padding=base64.b64encode(hashlib.shake_256(config['seed'].encode()).digest(width)).decode()[:width]
    store=Store(config['scope'])
    def app_route(*args,**kwargs):
        """Route this fixture's normal Store transaction helper only to its owned DB."""
        assert not args
        kwargs.pop('client',None)
        return route(database,**kwargs)
    sums={'artifact_bytes':0,'request_bytes_once':0,'outcome_bytes':0,'accounted_bytes':0}
    with patch('allow_documents.store.connect',app_route):
        assert store.initialize('vc19-storage-shaped-v1')['status']=='READY'
        with store.transaction() as c:
            c.execute('INSERT INTO documents.document(principal_id,workspace_id,document_id,title,head_revision) VALUES(%s,%s,%s,%s,%s)',
                      (store.principal,store.workspace,config['document'],'VC19 storage-shaped',count-1))
            for index in range(count):
                if time.monotonic()>SETUP_DEADLINE:
                    raise TimeoutError('fixture_setup_budget')
                value,a,b,o,key,charge=fixture(config,index,padding)
                namespace='CREATE' if index==0 else config['document']
                path='/api/v1/documents' if index==0 else '/api/v1/documents/'+config['document']+'/commit'
                c.execute('INSERT INTO documents.artifact(principal_id,workspace_id,document_id,artifact_id,content,source_hash,policy_version) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                    (store.principal,store.workspace,config['document'],value['artifactId'],a,value['sourceHash'],value['policyVersion']))
                c.execute('INSERT INTO documents.revision(principal_id,workspace_id,document_id,revision,artifact_id) VALUES(%s,%s,%s,%s,%s)',
                    (store.principal,store.workspace,config['document'],index,value['artifactId']))
                c.execute('INSERT INTO documents.receipt(principal_id,workspace_id,launch_id,namespace,request_key,method,route,request_bytes,request_hash,outcome,outcome_code,result_document_id,result_revision) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (store.principal,store.workspace,store.launch,namespace,key,'POST',path,b,hashlib.sha256(b).hexdigest(),o,'COMMITTED',config['document'],index))
                c.execute('INSERT INTO documents.admission(principal_id,workspace_id,launch_id,namespace,request_key,method,route,request_bytes,operation,document_id,expected_revision,owner_pid,owner_start,owner_nonce,state,reservation_bytes,reservation_documents,reservation_revisions) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0)',
                    (store.principal,store.workspace,store.launch,namespace,key,'POST',path,b,'CREATE' if index==0 else 'COMMIT',config['document'],None if index==0 else index-1,os.getpid(),identity.process_start(os.getpid()),str(uuid.uuid4()),'TERMINAL'))
                for field,size in [('artifact_bytes',len(a)),('request_bytes_once',len(b)),('outcome_bytes',len(o)),('accounted_bytes',charge)]:
                    sums[field]+=size
            c.execute('UPDATE documents.workspace SET document_count=1,revision_count=%s,receipt_count=%s,accounted_bytes=%s',
                      (count,count,sums['accounted_bytes']))
        with store.transaction() as c:
            actual=c.execute('SELECT (SELECT count(*) FROM documents.revision) AS revisions, (SELECT count(*) FROM documents.artifact) AS artifacts, (SELECT sum(octet_length(content)) FROM documents.artifact) AS artifact_bytes, (SELECT sum(octet_length(request_bytes)) FROM documents.receipt) AS receipt_request_bytes, (SELECT sum(octet_length(outcome)) FROM documents.receipt) AS outcome_bytes, (SELECT sum(octet_length(request_bytes)) FROM documents.admission) AS admission_request_bytes, (SELECT accounted_bytes FROM documents.workspace) AS accounted_bytes').fetchone()
    assert actual['revisions']==actual['artifacts']==count
    assert actual['artifact_bytes']==sums['artifact_bytes'] and actual['outcome_bytes']==sums['outcome_bytes']
    assert actual['receipt_request_bytes']==actual['admission_request_bytes']==sums['request_bytes_once']
    assert actual['accounted_bytes']==sums['accounted_bytes']<=budget<=268435456
    config['wanted']=sorted(identifier(config['seed'],'definition-'+str(i)) for i in range(1,count))
    config['expected_base_sha256']=hashlib.sha256(fixture(config,0,padding)[1]).hexdigest()
    config['artifact_bytes']=sums['artifact_bytes']
    return config,{'revisions':count,'target_accounted_bytes':budget,'unused_target_bytes':budget-sums['accounted_bytes'],
                   'source_padding_bytes':width,'actual_database_counts_and_bytes':{k:int(v) for k,v in actual.items()},**sums}


def kill_group(process):
    """Terminate only this profile's owned child session on timeout/overflow."""
    try:
        os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:
        pass


def measured(config,output,label,empty=False):
    """Capture bounded real CLI output and kernel per-child usage under fixed caps."""
    telemetry=output/(label+'-child.json')
    private=output/(label+'-control.json')
    settings=dict(config,telemetry=str(telemetry));save(private,settings)
    nonce=str(uuid.uuid4())
    args={'documentId':config['document'],'revision':0,'ids':[] if empty else config['wanted']}
    frame=wire.encode({'protocol':1,'requestId':nonce,'operation':'validationContext','args':args})
    command=['/usr/bin/prlimit','--as=2147483648','--cpu=20','--',
             str(ROOT/'.tools/retrieval-venv/bin/python'),str(Path(__file__)),'--child',str(private)]
    environment={'PYTHONPATH':str(ROOT/'retrieval'),'ALLOW_CORPUS_RUNTIME':str(ROOT/'.runtime/corpus'),
                 'LANGSMITH_TRACING':'false'}
    start=time.monotonic();process=subprocess.Popen(command,cwd=ROOT,env=environment,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    captured={'stdout':bytearray(),'stderr':bytearray()};overflow=[];writer_errors=[]
    def reader(name,stream,limit):
        """Bound retained bytes before accepting any child response."""
        while True:
            chunk=stream.read(8192)
            if not chunk:
                break
            if len(captured[name])+len(chunk)>limit:
                overflow.append(name);kill_group(process);break
            captured[name].extend(chunk)
        stream.close()
    def writer():
        """Keep blocked stdin writes inside the external operation deadline."""
        try:
            process.stdin.write(frame+b'\n');process.stdin.close()
        except (BrokenPipeError,OSError) as error:
            writer_errors.append(type(error).__name__)
    threads=[threading.Thread(target=reader,args=('stdout',process.stdout,1572865)),
             threading.Thread(target=reader,args=('stderr',process.stderr,32768)),threading.Thread(target=writer)]
    for thread in threads:
        thread.start()
    sampled={};timed_out=False
    while True:
        for key,value in vm(process.pid).items():
            sampled[key]=max(sampled.get(key,0),value)
        pid,status,usage=os.wait4(process.pid,os.WNOHANG)
        if pid:
            process.returncode=os.waitstatus_to_exitcode(status);break
        if time.monotonic()-start>=20:
            timed_out=True;kill_group(process)
        time.sleep(.01)
    elapsed=time.monotonic()-start
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()
    private.unlink()
    raw=bytes(captured['stdout']);errors=bytes(captured['stderr'])
    (output/(label+'-stdout.bin')).write_bytes(raw);(output/(label+'-stderr.bin')).write_bytes(errors)
    stats=json.loads(telemetry.read_text()) if telemetry.exists() else None
    save(output/(label+'-kernel.json'),{'wall_seconds':elapsed,'cpu_seconds':usage.ru_utime+usage.ru_stime,
        'kernel_peak_rss_bytes':usage.ru_maxrss*1024,'sampled_memory_high_water':sampled,
        'exit_code':process.returncode,'wall_deadline_triggered':timed_out,'stdout_bytes':len(raw),
        'stderr_bytes':len(errors),'input_bytes':len(frame),'overflow':overflow})
    response=wire.decode(raw,1572865) if raw else None
    good=response is not None and response.get('protocol')==1 and response.get('requestId')==nonce
    success=good and response.get('status')=='OK' and process.returncode==0 and not timed_out and not overflow
    if success:
        data=response['data'];assert set(data)=={'documentId','baseRevision','headObserved','artifact','ownedIdInventory'}
        assert data['documentId']==config['document'] and data['baseRevision']==0
        assert data['headObserved']==len(config['wanted'])
        assert hashlib.sha256(wire.encode(data['artifact'])).hexdigest()==config['expected_base_sha256']
        assert data['ownedIdInventory']==({} if empty else {item:'signature' for item in config['wanted']})
        assert stats and stats['connection_closed'] and stats['rlimit_as']==[2147483648]*2 and stats['rlimit_cpu']==[20]*2
        if empty:
            assert stats['history'] is None
        else:
            assert stats['history']['rows_buffered_before_iteration']==len(config['wanted'])+1
            assert stats['history']['column_format']==0
            assert stats['history']['raw_value_bytes_buffered']==2*config['artifact_bytes']+2*(len(config['wanted'])+1)
    availability=(not success and not overflow and (timed_out or process.returncode in (-signal.SIGKILL,-signal.SIGXCPU)
                  or (good and response.get('status')=='UNAVAILABLE' and stats and stats['request_failure_class']=='MemoryError')))
    assert success or availability,'unexpected_profile_outcome'
    result={'label':label,'classification':'SUCCESS' if success else 'RESOURCE_LIMIT_FAIL_CLOSED',
        'wall_seconds':elapsed,'cpu_seconds':usage.ru_utime+usage.ru_stime,'kernel_peak_rss_bytes':usage.ru_maxrss*1024,
        'sampled_memory_high_water':sampled,'exit_code':process.returncode,'wall_deadline_triggered':timed_out,
        'stdout_bytes':len(raw),'stderr_bytes':len(errors),'stdout_sha256':hashlib.sha256(raw).hexdigest(),
        'stderr_sha256':hashlib.sha256(errors).hexdigest(),'input_bytes':len(frame),'empty_ids':empty,
        'telemetry':stats,'writer_errors':writer_errors,'overflow':overflow}
    save(output/(label+'-result.json'),result)
    return result


def main():
    """Run the frozen finite profile and always drop only its generated database."""
    global SETUP_DEADLINE
    root_hash=check_inputs();protocol=json.loads((HERE/'protocol.json').read_text())
    SETUP_DEADLINE=time.monotonic()+protocol['setup_wall_seconds']
    name='allow_sql_test_'+uuid.uuid4().hex
    output=HERE/'runs'/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True,mode=0o700)
    report={'status':'RUNNING','input_root_sha256':root_hash,'protocol':protocol,'cases':[],
        'temporary_database':name,'live_database_targeted':False,'database_dropped':False}
    sys.path.insert(0,str(ROOT/'scripts'))
    from verify_sql_runtime import read_status,runtime_identity
    status_path=ROOT/'.runtime/corpus/sql-proxy/status.json'
    before=read_status(status_path);report['proxy_before']=runtime_identity(before)
    assert report['proxy_before']['status']=='PASS'
    controls_dsn=database_dsn(configured_dsn(True,'allow-recovery-control'),'postgres',admin=True,client='allow-recovery-control')
    controls=connect(controls_dsn,admin=True,autocommit=True,client='allow-recovery-control');created=False
    try:
        controls.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)));created=True
        def migration_route(*args,**kwargs):
            """Route existing migration only to this fresh owned fixture database."""
            assert not args
            kwargs.pop('client',None)
            return route(name,client='allow-migration',**kwargs)
        with patch('allow_documents.migration.connect',migration_route):
            migration.migrate()
        for case in protocol['cases']:
            check_inputs();started=time.monotonic()
            config,details=setup_case(name,case['revisions'],case['accounted_budget_bytes'])
            details['setup_seconds']=time.monotonic()-started;details['runs']=[]
            report['cases'].append(details);save(output/'progress.json',report)
            for iteration in range(protocol['samples_per_case']):
                details['runs'].append(measured(config,output,'n'+str(case['revisions'])+'-'+str(iteration)))
            if case['revisions']==4096:
                details['empty_control']=measured(config,output,'n4096-empty',empty=True)
            check_inputs();save(output/'progress.json',report)
        report['status']='PASS'
    except BaseException as error:
        report.update(status='BLOCKED',failure_class=type(error).__name__,failure_reason=str(error)[:160])
    finally:
        if created:
            controls.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
            row=controls.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(name,)).fetchone()
            report['database_dropped']=row[0]==0
        controls.close()
        after=read_status(status_path);report['proxy_after']=runtime_identity(after,before)
        report['input_root_after']=check_inputs()
        if not report['database_dropped'] or report['proxy_after']['status']!='PASS':
            report['status']='BLOCKED'
        save(output/'report.json',report)
    print(json.dumps({'status':report['status'],'report':str(output/'report.json'),'database_dropped':report['database_dropped']}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--child':
        child(sys.argv[2])
    elif len(sys.argv)==2 and sys.argv[1]=='--execute':
        raise SystemExit(main())
    else:
        raise SystemExit('Explicit --execute requires the pre-execution manifest.')
