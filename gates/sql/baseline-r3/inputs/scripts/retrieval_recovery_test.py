#!/usr/bin/env python3
"""Restore a real PostgreSQL backup while retaining the independent revocation log."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'retrieval'))
from allow_retrieval.common import RUNTIME,digest,private_write
from allow_retrieval.corpus import worker,normalize_full
from allow_retrieval.database import Repository,connection_dsn
from allow_retrieval.journal import Journal,Quarantined
from allow_retrieval.sql_connections import connect,database_dsn,tool_environment
from allow_retrieval.migration import apply_migrations


def pg_tool(arguments,environment,stdout):
    """Retain bounded failure diagnostics privately, never emit SQL or dump data."""
    with tempfile.TemporaryFile() as errors:
        result=subprocess.run(arguments,env=environment,stdout=stdout,stderr=errors,timeout=90)
        if result.returncode:
            errors.seek(0);diagnostic=errors.read(65536)
            identity=uuid.uuid4().hex
            private_write(RUNTIME/'sql-client-failures'/(identity+'.stderr'),diagnostic)
            raise RuntimeError(Path(arguments[0]).name+'_failed_private_diagnostic_'+identity)

def main():
    import psycopg
    from psycopg import sql
    name='allow_recovery_'+uuid.uuid4().hex
    admin=connection_dsn(True);app=connection_dsn()
    dbadmin=database_dsn(admin,name,admin=True,client='allow-recovery-control')
    dbapp=database_dsn(app,name,client='allow-recovery')
    directory=RUNTIME/('recovery-test-'+uuid.uuid4().hex);directory.mkdir(mode=0o700,parents=True)
    journal=Journal(directory/'journal')
    controls=connect(admin,admin=True,autocommit=True,client='allow-recovery-control')
    try:
        controls.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        with connect(dbadmin,admin=True,allow_temporary=True,client='allow-migration') as c:apply_migrations(c)
        store=Repository(dbapp,tenant='authored-recovery-fixture',purpose='store',journal=journal,allow_temporary=True,client='allow-recovery');store.initialize()
        ids=[]
        for source in ('sig A {r:set A} pred p {some r}','sig A {r:set A} pred p {no r}'):
            record,outcomes,meta=normalize_full(worker(source,0))
            meta.update(N=3,target_slot=0,family='authored-recovery-fixture')
            ids.append(store.add_record({'root':'authored-test','locator':digest(source.encode()),'source_hash':digest(source.encode()),'snapshot':'synthetic'},record,outcomes,meta))
        store.assign_splits([(rid,'train','authored-fixture') for rid in ids])
        model='authored-recovery-model'
        trainer=Repository(dbapp,tenant=store.tenant,purpose='train',journal=journal,allow_temporary=True,client='allow-recovery')
        trainer.register_model(model,{'kind':'authored-synthetic-test-only','adapter_sha256':'synthetic'},[ids[0]])
        embed=Repository(dbapp,tenant=store.tenant,purpose='embed',journal=journal,allow_temporary=True,client='allow-recovery')
        while (job:=embed.claim_job(model)):embed.publish(job,[1/math.sqrt(3072)]*3072)
        with store.transaction() as c:assert c.execute('SELECT count(*) AS n FROM retrieval.embedding').fetchone()['n']==2
        dump_environment=tool_environment(dbadmin,admin=True,client='allow-recovery-dump')
        restore_environment=tool_environment(dbadmin,admin=True,client='allow-recovery-restore')
        backup=directory/'before-revocation.dump'
        binaries=ROOT/'.tools/retrieval/postgres/bin'
        with backup.open('wb') as output:
            pg_tool([str(binaries/'pg_dump'),'-Fc'],dump_environment,output)
        backup.chmod(0o600)
        store.revoke(ids[0],reason='authored-real-backup-recovery-test')
        journal_before=journal.path.read_bytes()
        pg_tool([str(binaries/'pg_restore'),'--clean','--if-exists','--no-owner','--single-transaction','-d',name,str(backup)],restore_environment,subprocess.DEVNULL)
        assert journal.path.read_bytes()==journal_before
        status=store.status()
        assert status['revoked']==1
        with store.transaction() as c:
            assert c.execute('SELECT count(*) AS n FROM retrieval.embedding').fetchone()['n']==0
            assert c.execute('SELECT active FROM retrieval.model WHERE id=%s',(model,)).fetchone()['active'] is False
            assert c.execute("SELECT count(*) AS n FROM retrieval.outbox WHERE status!='CANCELLED'").fetchone()['n']==0
        # Missing/corrupt independent journal must deny service, even though the
        # restored DB contains its old successful startup marker.
        saved=journal.path.read_bytes();journal.path.unlink()
        try:
            store.status();raise AssertionError('missing journal was accepted')
        except Quarantined:pass
        journal.path.write_bytes(saved[:-1])
        try:
            store.status();raise AssertionError('truncated journal was accepted')
        except Quarantined:pass
        journal.path.write_bytes(saved)
        store.status()
        result={'status':'PASS','actual_pg_dump_restore':True,'lineage_model_invalidated':True,'all_derived_vectors_removed':True,'restored_outbox_cancelled':True,'missing_and_corrupt_journal_denied':True}
        print(json.dumps(result,separators=(',',':')))
        return 0
    finally:
        controls.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        controls.close();shutil.rmtree(directory)

if __name__=='__main__':raise SystemExit(main())
