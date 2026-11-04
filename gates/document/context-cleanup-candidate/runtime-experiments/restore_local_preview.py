#!/usr/bin/env python3
"""Restore the authorized local DEFAULT preview, preserving the existing database.

All SQL uses the canonical SQLeanParser helper. The old database is never
restored or restarted. Existing bytes and ownership evidence are archived before
the exact owned Spring/proxy incarnations are retired. This is local development
restoration, not P1 acceptance or production performance certification.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

import experiment as support
import regression_experiment as runtime
from probe_runtime import normalized

ROOT = support.ROOT
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'retrieval'), str(ROOT/'scripts')]


def save(path, value):
    """Create immutable private evidence without exporting stored source or authority."""
    support.write_private(path, value)


def assert_owner(pid, expected):
    """Require the recorded start ticks and exact command before acquiring signal authority."""
    from bootstrap_corpus import process_identity
    if process_identity(pid) != expected:
        raise RuntimeError('old_service_identity_changed')
    return support.process_identity(pid)


def retire(identity, seconds=30):
    """Send TERM through a checked pidfd and wait for independent incarnation absence."""
    support.signal_owned(identity, signal.SIGTERM)
    deadline = time.monotonic()+seconds
    while support.process_identity(identity['pid']) == identity and time.monotonic() < deadline:
        time.sleep(.05)
    if support.process_identity(identity['pid']) == identity:
        raise RuntimeError('owned_service_did_not_exit_no_escalation')
    return {'pid': identity['pid'], 'start': identity['start'], 'owned_identity_absent': True}


def snapshot(scope):
    """Hash all document/retrieval rows and separately normalize only this workspace policy."""
    from psycopg import sql
    from psycopg.rows import dict_row
    from allow_retrieval.sql_connections import connect
    result = {}
    with connect(admin=True, client='allow-tests', row_factory=dict_row) as connection:
        tables = connection.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('documents','retrieval') ORDER BY schemaname,tablename").fetchall()
        for table in tables:
            rows = connection.execute(sql.SQL('SELECT * FROM {}.{}').format(
                sql.Identifier(table['schemaname']), sql.Identifier(table['tablename']))).fetchall()
            name = table['schemaname']+'.'+table['tablename']
            values = [normalized(dict(row)) for row in rows]
            exact = sorted(json.dumps(row, sort_keys=True, separators=(',', ':'), default=str) for row in values)
            result[name] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(exact).encode()).hexdigest()}
            if name == 'documents.workspace':
                for row in values:
                    if row['principal_id'] == scope['principalId'] and row['workspace_id'] == scope['workspaceId']:
                        result['scope_policy'] = row['policy_version']
                        row['policy_version'] = '<only-authorized-policy-cas>'
                stable = sorted(json.dumps(row, sort_keys=True, separators=(',', ':'), default=str) for row in values)
                result['workspace_except_scope_policy'] = hashlib.sha256('\n'.join(stable).encode()).hexdigest()
    return result


def backup_database(directory):
    """Take a complete private logical backup through the existing canonical proxy."""
    from allow_retrieval.sql_connections import configured_dsn, tool_environment
    environment = tool_environment(configured_dsn(admin=True), admin=True, client='allow-recovery-dump')
    destination = directory/'allow_retrieval-before.dump'
    binary = ROOT/'.tools/retrieval/postgres/bin'
    with (directory/'backup-private.log').open('xb') as log:
        completed = subprocess.run([str(binary/'pg_dump'), '-Fc', '-f', str(destination)],
                                  env=environment, stdout=log, stderr=log, timeout=180)
    if completed.returncode:
        raise RuntimeError('private_backup_failed')
    destination.chmod(0o600)
    listing = subprocess.run([str(binary/'pg_restore'), '--list', str(destination)],
                             capture_output=True, timeout=30, check=True).stdout
    if b'TABLE DATA documents document' not in listing or b'TABLE DATA documents receipt' not in listing:
        raise RuntimeError('backup_missing_document_tables')
    return {'sha256': support.digest(destination), 'bytes': destination.stat().st_size,
            'archive_list_sha256': hashlib.sha256(listing).hexdigest(),
            'contains_document_and_receipt_data': True, 'sql_route': 'canonical_SQLeanParser',
            'scope': 'Full database including ACLs; existing cluster roles and private metadata are separately retained.'}


def archive_files(directory, observation):
    """Preserve exact old state, private authority and available startup-loaded proxy source."""
    paths = [ROOT/'.runtime/documents/identity.json', ROOT/'.runtime/launch.url',
             ROOT/'.runtime/corpus/database.json']
    paths += [p for folder in (ROOT/'.runtime/corpus/journal', ROOT/'.runtime/corpus/sql-proxy')
              for p in folder.rglob('*') if p.is_file() and not p.is_symlink()]
    hashes = []
    for source in paths:
        target = directory/'old-state'/source.relative_to(ROOT)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o600)
        hashes.append({'path': str(target.relative_to(directory)), 'sha256': support.digest(target)})
    status = json.loads((ROOT/'.runtime/corpus/sql-proxy/status.json').read_text())
    baseline = HERE.parent/'formal-runs/final-v2/inputs'
    for name, digest in status['loaded_inputs'].items():
        source = baseline/name
        if support.digest(source) != digest:
            raise RuntimeError('old_loaded_source_archive_unavailable')
        target = directory/'old-loaded-proxy-source'/name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes.append({'path': str(target.relative_to(directory)), 'sha256': digest})
    save(directory/'old-state-manifest.json', {'files': hashes, 'observed_services': observation['services']})


def http(token, path, body=None):
    """Read bounded local responses with authority kept out of logs and exceptions."""
    headers = {'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'}
    raw = json.dumps(body, separators=(',', ':'), ensure_ascii=False).encode() if body is not None else None
    request = urllib.request.Request('http://127.0.0.1:18080'+path, raw, headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.loads(response.read(1572865))
    if response.status != 200:
        raise RuntimeError('local_http_status')
    return value


def verify_http(token):
    """Validate one existing exact source without committing or creating any document."""
    listed = http(token, '/api/v1/documents')
    if listed.get('status') != 'OK' or not listed['data']['documents']:
        raise RuntimeError('existing_documents_unavailable')
    item = listed['data']['documents'][0]
    path = '/api/v1/documents/'+urllib.parse.quote(item['documentId'], safe='')
    before = http(token, path)
    if before.get('status') != 'OK':
        raise RuntimeError('existing_document_read_unavailable')
    data = before['data']
    source = data['artifact']['source']
    body = {'draftId': str(uuid.uuid4()), 'draftEpoch': 1, 'baseRevision': data['revision'],
            'candidate': {'mode': 'SOURCE', 'source': source}}
    reply = http(token, path+'/validate', body)
    if reply.get('status') != 'VALIDATED':
        raise RuntimeError('existing_source_validation_not_validated')
    after = http(token, path)
    if before['data'] != after['data']:
        raise RuntimeError('advisory_validation_changed_document')
    digest = hashlib.sha256(source.encode()).hexdigest()
    if reply['data']['proposedSourceHash'] != digest:
        raise RuntimeError('existing_source_validation_changed_source')
    return {'document_count': len(listed['data']['documents']), 'exact_source_sha256': digest,
            'document_identity_sha256': hashlib.sha256(item['documentId'].encode()).hexdigest(),
            'revision': data['revision'], 'status': 'VALIDATED', 'head_and_artifact_unchanged': True}


def main():
    """Perform the root-authorized local restoration, leaving immutable failure evidence."""
    os.umask(0o077)
    directory = HERE/'local-preview-restoration-r1'
    directory.mkdir(mode=0o700)
    observation = json.loads((HERE/'local-preview-readonly-r1.json').read_text())
    fences = json.loads((HERE/'local-preview-fences-r1.json').read_text())
    from allow_documents.identity import load
    from bootstrap_corpus import start_proxy, wait_context_ready
    scope = load()
    expected_identity = support.digest(ROOT/'.runtime/documents/identity.json')
    expected_journal = support.digest(ROOT/'.runtime/corpus/journal/revocations.jsonl')
    target_ready = json.loads((ROOT/'gates/performance/fresh-tier1-candidate/runtime-experiments/source-ready-r1.json').read_text())['backend_target']
    report = {'status': 'BLOCKED', 'classification': 'LOCAL_DEV_RESTORATION_NOT_PRODUCTION_ACCEPTANCE',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'profile': 'DEFAULT',
              'p1_full33': 'BLOCKED', 'F1_enabled': False, 'postgres_restarted': False}
    old_spring = observation['services']['spring']
    old_proxy = observation['services']['proxy']
    try:
        for label in ('spring', 'proxy', 'postgres'):
            service = observation['services'][label]
            assert_owner(service['pid'], service['identity'])
        if any((ROOT/'.runtime/corpus/sql-proxy'/name).exists() for name in ('context-state.json', 'context-initialized')):
            raise RuntimeError('unexpected_context_ownership_state')
        archive_files(directory, observation)
        before_stop = snapshot(scope)
        save(directory/'database-before-stop.json', before_stop)
        report['backup'] = backup_database(directory)
        report['old_spring_exit'] = retire(assert_owner(old_spring['pid'], old_spring['identity']))
        before = snapshot(scope)
        save(directory/'database-before.json', before)
        if before != before_stop:
            raise RuntimeError('concurrent_database_change_during_backup_quiesce')
        report['old_proxy_exit'] = retire(assert_owner(old_proxy['pid'], old_proxy['identity']))
        staging = ROOT/'backend/target.local-preview-staging-r1'
        staging.mkdir()
        for row in target_ready['files']:
            runtime.copy_file(Path(target_ready['path'])/row['path'], staging/row['path'], row['sha256'])
        previous = ROOT/'backend/target.before-local-preview-r1'
        (ROOT/'backend/target').rename(previous)
        staging.rename(ROOT/'backend/target')
        report['previous_target_preserved'] = str(previous)
        report['installed_target_files'] = len(target_ready['files'])
        config = json.loads((ROOT/'.runtime/corpus/database.json').read_text())
        start_proxy(config)
        wait_context_ready()
        proxy_status = json.loads((ROOT/'.runtime/corpus/sql-proxy/status.json').read_text())
        if proxy_status.get('parser', {}).get('policy') != 'sql-routing-v8-context-leases':
            raise RuntimeError('new_proxy_policy_unavailable')
        spring, owner, token = runtime.launch_spring(ROOT, directory, {'java': str(runtime.JAVA), 'port': 18080}, 'spring')
        report['new_spring_identity'] = owner
        runtime.wait_spring({'port': 18080}, spring, token)
        report['http'] = verify_http(token)
        after = snapshot(scope)
        save(directory/'database-after.json', after)
        expected_policy = 'document-v1:'+fences['tested_r1_target']['fullBuildIdentity']
        if after['scope_policy'] != expected_policy:
            raise RuntimeError('unexpected_installed_workspace_policy')
        allowed = {'scope_policy', 'documents.workspace'}
        if {k:v for k,v in before.items() if k not in allowed} != {k:v for k,v in after.items() if k not in allowed}:
            raise RuntimeError('durable_state_changed_beyond_policy')
        if support.digest(ROOT/'.runtime/documents/identity.json') != expected_identity:
            raise RuntimeError('workspace_identity_changed')
        if support.digest(ROOT/'.runtime/corpus/journal/revocations.jsonl') != expected_journal:
            raise RuntimeError('retrieval_journal_changed')
        report.update(status='RESTORED', durable_state_unchanged_except_scope_policy=True,
                      workspace_identity_unchanged=True, retrieval_journal_unchanged=True,
                      installed_policy=expected_policy, new_proxy_pid=proxy_status['pid'],
                      private_launch_file=str(ROOT/'.runtime/launch.url'))
        save(ROOT/'.runtime/local-preview-owner.json', {'spring': owner, 'proxy_pid': proxy_status['pid'],
             'restoration_evidence': str(directory/'report.json'), 'profile': 'DEFAULT'})
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        report['failure_code'] = str(error) if isinstance(error, RuntimeError) else 'private_diagnostics_retained'
        report['boundary'] = 'Stop on unexpected condition. Do not delete journals, forget UNKNOWN, restore DB, or silently claim restoration.'
    finally:
        save(directory/'report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'profile', 'p1_full33', 'F1_enabled', 'postgres_restarted')}))
    return 0 if report['status'] == 'RESTORED' else 1


if __name__ == '__main__':
    sys.exit(main())
