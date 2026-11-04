#!/usr/bin/env python3
"""Real isolated documents pg_dump/pg_restore, owner metadata and full ACL recovery."""
from contextlib import ExitStack
from datetime import datetime, timezone
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'retrieval'))
from psycopg import sql
from psycopg.rows import dict_row
from allow_documents import identity, wire, migration
from allow_documents.store import Store
from allow_retrieval.sql_connections import (connect,configured_dsn,database_dsn,tool_environment,
                                              PROXY_DIRECTORY,PORT)
from verify_sql_runtime import read_status,runtime_identity

STATUS = ROOT/'.runtime/corpus/sql-proxy/status.json'
REPORT = ROOT/'gates/document/document-recovery-report.json'
BINARIES = ROOT/'.tools/retrieval/postgres/bin'


def inputs():
    """Hash only actual recovery/document/router source inputs, not generated reports."""
    paths = list((ROOT/'retrieval/allow_documents').glob('*.py'))
    paths += list((ROOT/'db/document').glob('*.sql'))
    paths += [Path(__file__),ROOT/'scripts/verify_sql_clients.py',ROOT/'scripts/verify_sql_runtime.py',
              ROOT/'retrieval/allow_retrieval/sql_connections.py',ROOT/'retrieval/allow_retrieval/sql_guard.py',
              ROOT/'retrieval/allow_retrieval/sql_proxy.py',ROOT/'retrieval/allow_retrieval/sql_image.py',
              ROOT/'retrieval/allow_retrieval/sql_image_init.py',ROOT/'retrieval/allow_retrieval/sql_image_config.py',
              ROOT/'config/sqlean-parser-lock.json',
              ROOT/'db/document/interface.json']
    return {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def dsns(name):
    """Permit only a generated registered temporary database through the canonical proxy."""
    if not re.fullmatch(r'allow_recovery_[0-9a-f]{32}',name):
        raise ValueError('temporary_database_required')
    return (database_dsn(configured_dsn(True),name,admin=True,client='allow-recovery-control'),
            database_dsn(configured_dsn(),name,client='allow-recovery'))


class TemporaryRoute:
    """Test-only production-helper seam chooses a registered temporary database."""
    def __init__(self,name):
        """Resolve exact validated role-specific DSNs without exposing credentials."""
        self.name=name
        self.admin,self.app=dsns(name)
        self.endpoints={}

    def connect(self,*args,**kwargs):
        """Keep every real driver call in the unchanged validated sql_connections helper."""
        if args:
            raise ValueError('unexpected_production_dsn')
        admin=kwargs.pop('admin',False)
        client='allow-migration' if admin else 'allow-recovery'
        kwargs.pop('client',None)
        connection=connect(self.admin if admin else self.app,admin=admin,
                           allow_temporary=True,client=client,**kwargs)
        assert connection.info.host==str(PROXY_DIRECTORY) and str(connection.info.port)==PORT
        assert connection.info.dbname==self.name
        self.endpoints[client]={'host':connection.info.host,'port':str(connection.info.port),
                                'database':self.name,'application_name':client}
        return connection

    def install(self,stack):
        """Patch only local test process aliases; production Store/SQL helper are unchanged."""
        stack.enter_context(patch('allow_documents.migration.connect',self.connect))
        stack.enter_context(patch('allow_documents.store.connect',self.connect))


def empty_module():
    """Construct valid empty syntax forest for the authored storage-boundary fixture."""
    return {'version':1,'signatures':[],'fields':[],'predicates':[],'facts':[],
            'assertions':[],'commands':[],'nodes':[]}


def artifact(label=None):
    """Build authored checked-content fixture; this test makes no parser refinement claim."""
    source='' if label is None else 'sig '+label+' {}\r\n'
    module=empty_module()
    if label is not None:
        module['signatures']=[{'tag':'signature','id':wire.fresh_id(),'name':label,'multiplicity':'set'}]
    return {'artifactId':wire.fresh_id(),'mode':'BLOCK_SUPPORTED','source':source,
            'sourceHash':hashlib.sha256(source.encode()).hexdigest(),'module':module,'occurrences':[],
            'trivia':[],'analysisDescriptors':[],'policyVersion':'authored-document-recovery-v1',
            'dependencyHash':hashlib.sha256(b'authored-storage-fixture-not-Alloy-runtime').hexdigest()}


def commit(store,document='CREATE',revision=None,label=None):
    """Exercise actual admission and atomic accepted revision plus exact receipt."""
    key=uuid.uuid4().hex
    value=artifact(label)
    body={'idempotencyKey':key,'title':'Authored recovery'} if document=='CREATE' else {
        'idempotencyKey':key,'expectedRevision':revision,'candidate':{'mode':'SOURCE','source':value['source']}}
    route='/api/v1/documents' if document=='CREATE' else '/api/v1/documents/'+document+'/commit'
    request={'documentId':document,'key':key,'method':'POST','route':route,'bodyBase64':wire.b64(wire.encode(body))}
    admission=store.admit(dict(request,ownerPid=os.getpid(),ownerStartTicks=identity.process_start(os.getpid()),
                               operation='CREATE' if document=='CREATE' else 'COMMIT',expectedRevision=revision))
    assert admission['status']=='ADMITTED'
    result_document=admission['documentId'];new_revision=0 if document=='CREATE' else revision+1
    outcome=wire.encode({'protocol':1,'requestId':str(uuid.uuid4()),'status':'COMMITTED','data':{
        'documentId':result_document,'revision':new_revision,'artifact':value,'idRemapping':{}}})
    frame=dict(request,nonce=admission['nonce'],policyVersion=value['policyVersion'],expectedRevision=revision,
               artifact=value,outcomeBase64=wire.b64(outcome),result='COMMITTED',targetRevision=None,direction=None)
    assert store.finalize(frame)['responseBase64']==wire.b64(outcome)
    return result_document,request,outcome


def normalized(value):
    """Hash snapshots without emitting source, outcomes, identities or database secrets."""
    if isinstance(value,(bytes,memoryview)):
        return {'bytes':base64.b64encode(bytes(value)).decode()}
    if isinstance(value,datetime):
        return value.isoformat()
    if isinstance(value,dict):
        return {key:normalized(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):
        return [normalized(item) for item in value]
    return value


def snapshot(admin):
    """Compare all document rows, schema owners, table/column ACLs and forced RLS."""
    with connect(admin,admin=True,allow_temporary=True,client='allow-recovery-control',row_factory=dict_row) as c:
        tables={}
        for table in migration.TABLES:
            rows=c.execute(sql.SQL('SELECT * FROM documents.{}').format(sql.Identifier(table))).fetchall()
            encoded=[json.dumps(normalized(row),sort_keys=True,separators=(',',':')) for row in rows]
            tables[table]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(sorted(encoded)).encode()).hexdigest()}
        catalog=c.execute("SELECT n.nspname,c.relname,c.relkind,r.rolname,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='documents' ORDER BY 1,2,3").fetchall()
        columns=c.execute("SELECT c.relname,a.attname,a.attacl::text FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='documents' AND a.attnum>0 AND a.attacl IS NOT NULL ORDER BY 1,2").fetchall()
        schemas=c.execute("SELECT n.nspname,r.rolname,n.nspacl::text FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname IN ('documents','public') ORDER BY 1").fetchall()
        roles=c.execute("SELECT rolname,rolcanlogin,rolsuper,rolbypassrls FROM pg_roles WHERE rolname IN ('allow_owner','allow_app') ORDER BY 1").fetchall()
    return {'tables':tables,'table_owner_rls_acl':normalized(catalog),'column_acl':normalized(columns),
            'schema_owner_acl':normalized(schemas),'preexisting_cluster_roles':normalized(roles)}


def metadata(directory):
    """Bind independent private metadata bytes, owner and modes across SQL restoration."""
    identity.load(directory)
    path=directory/'identity.json'
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'uid':path.stat().st_uid,
            'gid':path.stat().st_gid,'file_mode':path.stat().st_mode&0o777,
            'directory_mode':directory.stat().st_mode&0o777}


def pg_tool(arguments,environment,stdout):
    """Run full native archive tools with bounded private stderr and no DSNs in argv."""
    with tempfile.TemporaryFile() as errors:
        result=subprocess.run(arguments,env=environment,stdout=stdout,stderr=errors,timeout=90)
        if result.returncode:
            errors.seek(0)
            diagnostic=errors.read(65536)
            private=ROOT/'.runtime/corpus/sql-client-failures'/('document-'+uuid.uuid4().hex+'.stderr')
            private.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            descriptor=os.open(private,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as output:output.write(diagnostic)
            raise RuntimeError('native_archive_tool_failed_private_diagnostic')


def restored_checks(store,document,request,outcome):
    """Read retained exact history/receipt and demonstrate restored app immutability."""
    assert store.read({'documentId':document,'revision':0})['artifact']['source']==''
    current=store.read({'documentId':document,'revision':None})
    assert current['headRevision']==1 and current['artifact']['source']=='sig A {}\r\n'
    assert store.receipt(request)=={'status':'REPLAY','responseBase64':wire.b64(outcome)}
    import psycopg.errors
    for statement in ('UPDATE documents.revision SET revision=99','DELETE FROM documents.receipt',
                      "UPDATE documents.artifact SET source_hash='not-authorized'"):
        try:
            with store.transaction() as connection:connection.execute(statement)
        except psycopg.errors.InsufficientPrivilege:
            continue
        raise AssertionError('restored_immutable_grant_not_enforced')
    foreign=Store({'principalId':str(uuid.uuid4()),'workspaceId':str(uuid.uuid4()),'logicalLaunchId':str(uuid.uuid4())})
    try:
        foreign.read({'documentId':document,'revision':None})
    except ValueError:
        return
    raise AssertionError('restored_rls_not_enforced')


def fresh_process(name,directory,fixture):
    """Reopen durable identity and receipt in a new Python process after restore."""
    path=directory/'verification.json'
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as output:output.write(wire.encode(fixture))
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--verify',name,str(directory)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
    assert result.returncode==0 and result.stdout.strip()==b'{"status":"PASS"}','fresh_process_recovery_failed'


def verify_child(name,directory):
    """Execute isolated fresh-process checks without provisioning any new owner identity."""
    route=TemporaryRoute(name);scope=identity.load(directory)
    fixture=wire.decode((directory/'verification.json').read_bytes())
    with ExitStack() as stack:
        route.install(stack)
        restored_checks(Store(scope),fixture['documentId'],fixture['request'],wire.unb64(fixture['outcomeBase64'],1048576))
    print('{"status":"PASS"}')
    return 0


def execute(name,directory,report):
    """Migrate, author, fully back up, diverge, restore and verify only a temporary DB."""
    route=TemporaryRoute(name)
    owner=directory/'owner';scope=identity.provision(owner)
    report['owner_metadata_before']=metadata(owner)
    with ExitStack() as stack:
        route.install(stack);migration.migrate()
        store=Store(scope);assert store.initialize('authored-document-recovery-v1')['status']=='READY'
        document,create_request,create_outcome=commit(store)
        _,request,outcome=commit(store,document,0,'A')
        before=snapshot(route.admin)
        backup=directory/'full.dump'
        dump_environment=tool_environment(route.admin,admin=True,client='allow-recovery-dump')
        restore_environment=tool_environment(route.admin,admin=True,client='allow-recovery-restore')
        for environment in (dump_environment,restore_environment):
            assert environment['PGHOST']==str(PROXY_DIRECTORY) and environment['PGPORT']==PORT
        with backup.open('wb') as output:pg_tool([str(BINARIES/'pg_dump'),'-Fc'],dump_environment,output)
        backup.chmod(0o600)
        listing=subprocess.run([str(BINARIES/'pg_restore'),'--list',str(backup)],capture_output=True,check=True,timeout=15).stdout
        acl_entries=sum(b' ACL ' in line for line in listing.splitlines());assert acl_entries>0
        commit(store,document,1,'B');assert store.read({'documentId':document,'revision':None})['headRevision']==2
        pg_tool([str(BINARIES/'pg_restore'),'--clean','--if-exists','--single-transaction','-d',name,str(backup)],restore_environment,subprocess.DEVNULL)
        after=snapshot(route.admin);assert before==after,'restored_document_rows_or_permissions_differ'
        restored_checks(Store(identity.load(owner)),document,request,outcome)
        assert store.receipt(create_request)['responseBase64']==wire.b64(create_outcome)
        fresh_process(name,owner,{'documentId':document,'request':request,'outcomeBase64':wire.b64(outcome)})
        report['owner_metadata_after']=metadata(owner)
        assert report['owner_metadata_before']==report['owner_metadata_after']
        report.update(status='PASS',actual_pg_dump_restore=True,full_acl_entries=acl_entries,
                      backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),row_and_acl_snapshot_before=before,
                      row_and_acl_snapshot_after=after,restored_rows_owners_rls_and_acls_equal=True,
                      fresh_process_exact_receipt_recovery=True,private_metadata_unchanged=True,
                      restored_immutability_and_scope_denials=True,canonical_endpoints=route.endpoints)


def main():
    """Retain source/runtime-bound evidence and drop only this generated isolated database."""
    from verify_sql_clients import inventory
    source_before=inputs();before=read_status(STATUS);runtime_before=runtime_identity(before)
    assert runtime_before['status']=='PASS'
    name='allow_recovery_'+uuid.uuid4().hex
    directory=ROOT/'.runtime'/('document-recovery-'+uuid.uuid4().hex);directory.mkdir(mode=0o700)
    control_dsn=database_dsn(configured_dsn(True),'postgres',admin=True,client='allow-recovery-control')
    report={'status':'FAIL','actual_pg_dump_restore':False,'classification':'FINITE_DOCUMENT_STORE_RECOVERY_NOT_FORMAL_REFINEMENT',
            'timestamp_utc':datetime.now(timezone.utc).isoformat(),'input_sha256_before':source_before,
            'runtime_identity_before':runtime_before,'live_database_targeted':False,
            'fixture':'Authored checked-artifact store boundary fixture; no Alloy parser/runtime refinement claim.',
            'native_tool_sha256':{tool:hashlib.sha256((BINARIES/tool).read_bytes()).hexdigest() for tool in ('pg_dump','pg_restore')},
            'backup_arguments':['pg_dump','-Fc'],'restore_arguments':['pg_restore','--clean','--if-exists','--single-transaction'],
            'limitations':['Cluster roles must preexist; pg_dump single database does not export global role definitions.',
                           'No PostgreSQL restart; live database contents and corpus recovery script are untouched.',
                           'Private owner identity metadata is retained independently, not exported by SQL pg_dump.']}
    controls=connect(control_dsn,admin=True,autocommit=True,client='allow-recovery-control');created=False
    try:
        assert controls.info.dbname=='postgres' and controls.info.host==str(PROXY_DIRECTORY)
        controls.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)));created=True
        execute(name,directory,report)
    except Exception as failure:
        report.update(status='FAIL',failure_class=type(failure).__name__)
    finally:
        if created:controls.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        controls.close();shutil.rmtree(directory)
        time.sleep(.35);after=read_status(STATUS);source_after=inputs()
        tags=('allow-migration','allow-recovery-control','allow-recovery','allow-recovery-dump','allow-recovery-restore')
        delta={tag:{key:after.get('clients',{}).get(tag,{}).get(key,0)-before.get('clients',{}).get(tag,{}).get(key,0)
                    for key in sorted(set(before.get('clients',{}).get(tag,{}))|set(after.get('clients',{}).get(tag,{})))} for tag in tags}
        runtime_after=runtime_identity(after,before)
        report.update(input_sha256_after=source_after,source_unchanged=source_before==source_after,
                      runtime_identity_after=runtime_after,per_client_counter_deltas=delta,inventory=inventory())
        if source_before!=source_after or runtime_after['status']!='PASS' or report['inventory']['status']!='PASS' or not all(delta[tag].get('accepted',0)>0 for tag in tags):report['status']='FAIL'
        REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'report':str(REPORT.relative_to(ROOT))}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--verify':raise SystemExit(verify_child(sys.argv[2],Path(sys.argv[3])))
    if len(sys.argv)!=1:raise SystemExit('unsupported_arguments')
    raise SystemExit(main())
