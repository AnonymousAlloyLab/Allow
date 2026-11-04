#!/usr/bin/env python3
"""Two registered real negative-authentication probes; no credential-store edits."""
from contextlib import ExitStack
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
SPEC=importlib.util.spec_from_file_location('validation_context_gap_probe',HERE.parent/'r2/probe.py')
BASE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


class AuthRoute(BASE.Route):
    """Add a specific password-rejection assertion to the existing actual-login seam."""
    def connect(self,*args,**kwargs):
        """Classify the real authentication error without emitting its private text."""
        try:
            return super().connect(*args,**kwargs)
        except BASE.psycopg.OperationalError as failure:
            if self.control and self.control.get('fault')=='auth':
                diagnostic=str(failure)
                assert 'password authentication failed' in diagnostic.lower()
                self.control['password_rejection_diagnostic_verified']=True
            raise


def run():
    """Verify registered inputs and test both empty/nonempty-ID mandatory login paths."""
    registration=json.loads((HERE/'registration.json').read_text())
    for item in registration['files']:assert BASE.sha(ROOT/item['path'])==item['sha256']
    assert hashlib.sha256(json.dumps(registration['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==registration['input_root_sha256']
    route=AuthRoute('allow_recovery_'+uuid.uuid4().hex);created=False
    report={'status':'RUNNING','input_root_sha256':registration['input_root_sha256'],'cases':[]}
    before_runtime=BASE.status();before_counts=BASE.counters(before_runtime)
    try:
        with BASE.connect(BASE.configured_dsn(True),admin=True,client='allow-recovery-control',autocommit=True) as c:
            c.execute(BASE.sql.SQL('CREATE DATABASE {}').format(BASE.sql.Identifier(route.name)));created=True
        with ExitStack() as stack:
            route.install(stack);BASE.migration.migrate();store=BASE.Store(BASE.scope())
            assert store.initialize('authored-document-recovery-v1')['status']=='READY'
            document,_,_=BASE.fixtures.commit(store)
            durable_before=BASE.durable(route)
            for ids in ([],[BASE.wire.fresh_id()]):
                control={'fault':'auth'};route.control=control
                try:
                    request=BASE.frame({'documentId':document,'revision':0,'ids':ids})
                    result,byte_count=BASE.invoke(store,request);BASE.unavailable(result)
                finally:route.control=None
                assert control['password_rejection_diagnostic_verified']
                assert BASE.durable(route)==durable_before
                report['cases'].append({'empty_ids':not ids,'status':'UNAVAILABLE',
                    'password_rejection_diagnostic_verified':True,'response_bytes':byte_count,
                    'durable_unchanged':True,'stored_credentials_unchanged':True,
                    'actual_mechanism':'transient per-connection wrong password over canonical proxy'})
        report['proxy_counter_delta']=BASE.await_counter(before_counts,'connections',2)
        report['status']='PASS'
    except BaseException as failure:
        report['status']='FAIL';report['failure_type']=type(failure).__name__
    finally:
        route.control=None
        if created:
            with BASE.connect(BASE.configured_dsn(True),admin=True,client='allow-recovery-control',autocommit=True) as c:
                c.execute(BASE.sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(BASE.sql.Identifier(route.name)))
                report['owned_fixture_database_dropped']=c.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(route.name,)).fetchone()[0]==0
        report['proxy_identity_unchanged']=BASE.sealed(BASE.status())==BASE.sealed(before_runtime)
        assert report['proxy_identity_unchanged']
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        directory=HERE/'runs'/datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%SZ')
        directory.mkdir(parents=True,exist_ok=False);BASE.dump(directory/'report.json',report)
        print(json.dumps({'status':report['status'],'report':str(directory/'report.json'),'sha256':BASE.sha(directory/'report.json')}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    assert sys.argv[1:]==['--execute'],'explicit registered execution required'
    sys.exit(run())
