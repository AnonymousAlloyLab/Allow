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
from allow_retrieval.common import RUNTIME,digest
from allow_retrieval.corpus import worker,normalize_full
from allow_retrieval.database import Repository,connection_dsn
from allow_retrieval.journal import Journal,Quarantined

def main():
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict,make_conninfo
    name='allow_recovery_'+uuid.uuid4().hex
    admin=connection_dsn(True);app=connection_dsn()
    dbadmin=make_conninfo(admin,dbname=name);dbapp=make_conninfo(app,dbname=name)
    directory=RUNTIME/('recovery-test-'+uuid.uuid4().hex);directory.mkdir(mode=0o700,parents=True)
    journal=Journal(directory/'journal')
    controls=psycopg.connect(admin,autocommit=True)
    try:
        controls.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        with psycopg.connect(dbadmin) as c:c.execute((ROOT/'db/migrations/004_retrieval.sql').read_text())
        store=Repository(dbapp,tenant='authored-recovery-fixture',purpose='store',journal=journal);store.initialize()
        ids=[]
        for source in ('sig A {r:set A} pred p {some r}','sig A {r:set A} pred p {no r}'):
            record,outcomes,meta=normalize_full(worker(source,0))
            meta.update(N=3,target_slot=0,family='authored-recovery-fixture')
            ids.append(store.add_record({'root':'authored-test','locator':digest(source.encode()),'source_hash':digest(source.encode()),'snapshot':'synthetic'},record,outcomes,meta))
        store.assign_splits([(rid,'train','authored-fixture') for rid in ids])
        model='authored-recovery-model'
        trainer=Repository(dbapp,tenant=store.tenant,purpose='train',journal=journal)
        trainer.register_model(model,{'kind':'authored-synthetic-test-only','adapter_sha256':'synthetic'},[ids[0]])
        embed=Repository(dbapp,tenant=store.tenant,purpose='embed',journal=journal)
        while (job:=embed.claim_job(model)):embed.publish(job,[1/math.sqrt(3072)]*3072)
        with store.transaction() as c:assert c.execute('SELECT count(*) AS n FROM retrieval.embedding').fetchone()['n']==2
        params=conninfo_to_dict(dbadmin)
        env={**os.environ,**{('PGDATABASE' if k=='dbname' else 'PG'+k.upper()):v for k,v in params.items() if k in ('host','port','user','password','dbname')}}
        backup=directory/'before-revocation.dump'
        binaries=ROOT/'.tools/retrieval/postgres/bin'
        with backup.open('wb') as output:
            subprocess.run([str(binaries/'pg_dump'),'-Fc'],env=env,stdout=output,stderr=subprocess.DEVNULL,check=True,timeout=30)
        backup.chmod(0o600)
        store.revoke(ids[0],reason='authored-real-backup-recovery-test')
        journal_before=journal.path.read_bytes()
        subprocess.run([str(binaries/'pg_restore'),'--clean','--if-exists','--no-owner','--single-transaction','-d',name,str(backup)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=30)
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
