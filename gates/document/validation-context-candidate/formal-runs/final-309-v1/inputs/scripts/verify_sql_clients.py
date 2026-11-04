#!/usr/bin/env python3
"""Finite client entrypoint inventory and identity-bound real recovery coverage.

Run only against the released owned proxy. Reports never contain SQL or DSNs.
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'retrieval'))
from verify_sql_runtime import read_status, runtime_identity

STATUS = ROOT/'.runtime/corpus/sql-proxy/status.json'
INPUTS = ('spec/sql-stage.json', 'config/sqlean-parser-lock.json',
          'scripts/bootstrap_corpus.py', 'scripts/retrieval_recovery_test.py',
          'scripts/verify_sql_clients.py', 'scripts/verify_sql_runtime.py', 'db/migrations/005_expected_catalog.json',
          'scripts/bootstrap_documents.py', 'scripts/document_recovery_test.py', 'db/document/interface.json')


def fingerprint():
    paths = [ROOT/name for name in INPUTS]
    paths += list((ROOT/'retrieval/allow_retrieval').glob('*.py'))
    paths += list((ROOT/'retrieval/allow_documents').glob('*.py'))
    paths += list((ROOT/'db/document').rglob('*.sql'))
    paths += list((ROOT/'scripts').rglob('*.py'))
    files = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(set(paths))}
    return files


def inventory():
    """Enumerate finite Python production connection/execution sites via AST.

    This establishes a checked source inventory, not dynamic dispatch completeness.
    The wire daemon's open_unix_connection is transport, not a SQL client.
    """
    sites=[]; raw=[]
    paths=list((ROOT/'retrieval/allow_retrieval').glob('*.py'))+list((ROOT/'retrieval/allow_documents').glob('*.py'))+list((ROOT/'scripts').rglob('*.py'))
    scanned_files={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    for path in sorted(paths):
        tree=ast.parse(path.read_text(), filename=str(path))
        aliases={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                for item in node.names:aliases[item.asname or item.name]=item.name
            elif isinstance(node,ast.ImportFrom):
                for item in node.names:aliases[item.asname or item.name]=(node.module or '')+'.'+item.name
        def name(node):
            if isinstance(node,ast.Name):return aliases.get(node.id,node.id)
            if isinstance(node,ast.Attribute):return name(node.value)+'.'+node.attr
            return '<dynamic>'
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            call=name(node.func)
            if call in ('psycopg.connect','psycopg2.connect'):
                raw.append({'path':str(path.relative_to(ROOT)),'line':node.lineno,'call':call})
            if call.rsplit('.',1)[-1] in ('connect','execute','executemany','copy','pg_tool','sql','tool_environment'):
                sites.append({'path':str(path.relative_to(ROOT)),'line':node.lineno,'call':call})
    sole=len(raw)==1 and raw[0]['path']=='retrieval/allow_retrieval/sql_connections.py'
    helper=ast.parse((ROOT/'retrieval/allow_retrieval/sql_connections.py').read_text())
    function=next(node for node in helper.body if isinstance(node,ast.FunctionDef) and node.name=='connect')
    assigned=any(isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='normalized' for target in node.targets) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='validate_dsn' for node in function.body)
    returned=any(isinstance(node,ast.Return) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and isinstance(node.value.func.value,ast.Name) and node.value.func.value.id=='psycopg' and node.value.func.attr=='connect' and node.value.args and isinstance(node.value.args[0],ast.Name) and node.value.args[0].id=='normalized' for node in function.body)
    helper_validated=assigned and returned
    return {'status':'PASS' if sole and helper_validated else 'FAIL','raw_driver_connections':raw,
            'sole_raw_driver_in_validated_helper':sole,'helper_validates_driver_dsn_ast':helper_validated,'scanned_file_sha256':scanned_files,'connection_and_sql_sites':sites,
            'limits':'Finite Python AST inventory; calls and aliases enumerated, not universal dynamic-call analysis. Shell/tool entrypoints are separately registered and exercised.'}


class Evidence:
    def __init__(self):
        self.files=fingerprint();self.before=read_status(STATUS)
        self.identity_before=runtime_identity(self.before)
        from allow_retrieval.corpus import toolchain_id
        self.worker_identity=toolchain_id()
        if self.identity_before['status']!='PASS':raise RuntimeError('stale_proxy_identity')

    def finish(self, tags):
        # Status publishes every 250ms; use an identity-bound fresh snapshot.
        time.sleep(.35)
        after=read_status(STATUS);identity_after=runtime_identity(after,self.before)
        deltas={}
        for tag in tags:
            a=self.before.get('clients',{}).get(tag,{})
            b=after.get('clients',{}).get(tag,{})
            deltas[tag]={key:b.get(key,0)-a.get(key,0) for key in sorted(set(a)|set(b))}
        from allow_retrieval.corpus import toolchain_id
        worker_after=toolchain_id()
        unchanged=self.files==fingerprint() and self.worker_identity==worker_after
        covered=all(deltas[tag].get('accepted',0)>0 for tag in tags)
        return {'status':'PASS' if unchanged and covered and identity_after['status']=='PASS' else 'FAIL',
                'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                'classification':'FINITE_CLIENT_CHECKS_NOT_FORMAL_REFINEMENT',
                'input_sha256_before':self.files,'input_sha256_after':fingerprint(),
                'source_unchanged':unchanged,'worker_toolchain_sha256_before':self.worker_identity,'worker_toolchain_sha256_after':worker_after,'runtime_identity_before':self.identity_before,
                'runtime_identity_after':identity_after,'daemon_started_before':self.before.get('started'),
                'daemon_started_after':after.get('started'),'per_client_counter_deltas':deltas,
                'each_registered_tag_accepted':covered}


def main():
    from allow_retrieval.sql_connections import configuration,PROXY_DIRECTORY,PORT,connect
    import bootstrap_corpus
    import retrieval_recovery_test
    audit=inventory();evidence=Evidence()
    if audit['status']!='PASS':raise RuntimeError('client_inventory_failed')
    # Exercise the actual psql bootstrap entrypoint with a read-only statement.
    assert bootstrap_corpus.PROXY_SOCKET.parent==PROXY_DIRECTORY
    bootstrap_corpus.sql('SELECT 1',configuration())
    from allow_retrieval.database import Repository
    with Repository()._connect() as connection:
        assert Path(connection.info.host)==PROXY_DIRECTORY and str(connection.info.port)==PORT
        assert connection.execute('SELECT 1 AS n').fetchone()=={'n':1}
    def live_snapshot():
        with connect(admin=True,client='allow-recovery-control') as connection:
            counts=connection.execute('SELECT (SELECT count(*) FROM retrieval.artifact),(SELECT count(*) FROM retrieval.record),(SELECT count(*) FROM retrieval.run),(SELECT count(*) FROM retrieval.model),(SELECT count(*) FROM retrieval.embedding)').fetchone()
        journal=ROOT/'.runtime/corpus/journal/revocations.jsonl'
        return {'table_counts':dict(zip(('artifact','record','run','model','embedding'),counts)),
                'independent_journal_sha256':hashlib.sha256(journal.read_bytes()).hexdigest()}
    live_before=live_snapshot()
    recovery_failure=None
    try:
        recovery_result=retrieval_recovery_test.main()
    except Exception as exc:
        recovery_result=1
        recovery_failure=type(exc).__name__
    live_after=live_snapshot()
    assert live_before==live_after,'live_corpus_changed'
    tags=('allow-bootstrap','allow-app','allow-migration','allow-recovery-control',
          'allow-recovery','allow-recovery-dump','allow-recovery-restore')
    report=evidence.finish(tags)
    report.update(inventory=audit,canonical_endpoint={'host':str(PROXY_DIRECTORY),'port':PORT},
                  entrypoints={'allow-bootstrap':'scripts/bootstrap_corpus.py:sql (psql)',
                  'allow-app':'Repository._connect through validated sql_connections.connect',
                  'allow-migration':'migration.apply_migrations in isolated recovery database',
                  'allow-recovery-control':'recovery CREATE/DROP isolated database',
                  'allow-recovery':'Repository fixture transactions',
                  'allow-recovery-dump':'pg_dump -Fc full ACL backup',
                  'allow-recovery-restore':'pg_restore full ACL restoration'},
                  recovery_returncode=recovery_result,recovery_failure_class=recovery_failure,live_corpus_before=live_before,live_corpus_after=live_after,live_corpus_unchanged=live_before==live_after,
                  limits=['Runtime tests and ML/HTTP entrypoints have separate reports; tags alone do not prove universal coverage.'])
    if recovery_result:report['status']='FAIL'
    output=ROOT/'gates/sql/client-coverage.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'report':str(output.relative_to(ROOT))}))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
