#!/usr/bin/env python3
"""Install the tested strict-deadline repair and refresh only the owned local DEFAULT preview.

The PostgreSQL incarnation, all stored rows and private workspace identity remain
unchanged. Full33 and production performance acceptance remain explicitly open.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import experiment as support
import regression_experiment as runtime
import restore_local_preview as restoration

ROOT, HERE = restoration.ROOT, restoration.HERE
CHANGED = ('retrieval/allow_retrieval/sql_context_lease.py',
           'retrieval/tests/test_context_leases.py')


def archive_current(output, status):
    """Preserve private state and exact old startup-loaded source before retiring services."""
    paths = [ROOT/'.runtime/documents/identity.json', ROOT/'.runtime/launch.url',
             ROOT/'.runtime/local-preview-owner.json', ROOT/'.runtime/corpus/database.json']
    paths += [p for folder in (ROOT/'.runtime/corpus/journal', ROOT/'.runtime/corpus/sql-proxy')
              for p in folder.rglob('*') if p.is_file() and not p.is_symlink()]
    rows = []
    for source in paths:
        target = output/'old-state'/source.relative_to(ROOT)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o600)
        rows.append({'path': str(target.relative_to(output)), 'sha256': support.digest(target)})
    for relative, expected in status['loaded_inputs'].items():
        target = output/'old-loaded-source'/relative
        runtime.copy_file(ROOT/relative, target, expected)
        rows.append({'path': str(target.relative_to(output)), 'sha256': expected})
    for relative in CHANGED:
        target = output/'rollback-source'/relative
        runtime.copy_file(ROOT/relative, target)
        rows.append({'path': str(target.relative_to(output)), 'sha256': support.digest(target)})
    restoration.save(output/'archive-manifest.json', {'files': rows})


def tested_candidate():
    """Require complete fresh regressions and immutable source/DEFAULT target identities."""
    run = HERE/'runs/r15-regressions'
    result = json.loads((run/'report.json').read_text())
    if (result['status'] != 'PASS' or result['tooling_mutation']
            or not result['managed_runtime_inventory_unchanged']
            or not result['managed_runtime_links_unchanged']
            or not result['manifest_unchanged_after_execution']):
        raise RuntimeError('repaired_regressions_not_passed')
    if support.digest(run/'manifest.json') != result['manifest_sha256_before_execution']:
        raise RuntimeError('tested_regression_manifest_changed')
    manifest = json.loads((run/'manifest.json').read_text())
    source = Path(manifest['copied_root'])
    hashes = {row['path']: row['sha256'] for row in manifest['files']}
    if any(support.digest(source/name) != hashes[name] for name in CHANGED):
        raise RuntimeError('tested_repair_source_changed')
    target = json.loads((ROOT/'gates/performance/fresh-tier1-candidate/runtime-experiments/source-ready-r1.json').read_text())['backend_target']
    if any(support.digest(ROOT/'backend/target'/row['path']) != row['sha256'] for row in target['files']):
        raise RuntimeError('default_java_target_changed')
    return source, hashes


def install(source, hashes, output):
    """Atomically replace only the two tested source files, preserving their preimages."""
    installed = []
    for relative in CHANGED:
        destination = ROOT/relative
        temporary = destination.with_name(destination.name+'.deadline-new')
        runtime.copy_file(source/relative, temporary, hashes[relative])
        os.replace(temporary, destination)
        installed.append({'path': relative, 'sha256': support.digest(destination)})
    restoration.save(output/'installed-source.json', {'files': installed})


def launch(output):
    """Use the same tested DEFAULT arguments with detached lifetime and private file logs."""
    original = subprocess.Popen

    def detached(*arguments, **keywords):
        """Prevent the launcher session from owning the preview process lifetime."""
        keywords.update(start_new_session=True, stdin=subprocess.DEVNULL)
        return original(*arguments, **keywords)

    with patch.object(runtime.subprocess, 'Popen', side_effect=detached):
        return runtime.launch_spring(ROOT, output, {'java': str(runtime.JAVA), 'port': 18080}, 'spring')


def main():
    """Perform the authorized reversible local refresh, stopping on any unexpected state."""
    os.umask(0o077)
    output = HERE/'local-preview-restoration-r3'
    output.mkdir(mode=0o700)
    report = {'status': 'BLOCKED', 'classification': 'TESTED_LOCAL_DEV_DEADLINE_REPAIR',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'profile': 'DEFAULT',
              'p1_full33': 'BLOCKED', 'F1_enabled': False, 'postgres_restarted': False}
    from allow_documents.identity import load
    from bootstrap_corpus import process_identity, start_proxy, wait_context_ready
    from verify_sql_runtime import runtime_identity
    try:
        source, hashes = tested_candidate()
        scope = load()
        owner = json.loads((ROOT/'.runtime/local-preview-owner.json').read_text())
        proxy = json.loads((ROOT/'.runtime/corpus/sql-proxy/owner.json').read_text())
        status = json.loads((ROOT/'.runtime/corpus/sql-proxy/status.json').read_text())
        if owner['proxy_pid'] != proxy['pid'] or proxy['pid'] != status['pid']:
            raise RuntimeError('unexpected_proxy_owner')
        if runtime_identity(status)['status'] != 'PASS' or status['context']['status'] != 'READY':
            raise RuntimeError('old_preview_proxy_not_consistent_ready')
        old_spring = restoration.assert_owner(owner['spring_pid'], owner['spring_identity'])
        old_proxy = restoration.assert_owner(proxy['pid'], proxy['identity'])
        pg_pid = int((ROOT/'.runtime/corpus/postgres/data/postmaster.pid').read_text().splitlines()[0])
        pg_identity = process_identity(pg_pid)
        if pg_identity is None:
            raise RuntimeError('existing_postgres_absent')
        identities = {str(p.relative_to(ROOT)): support.digest(p) for p in
                      (ROOT/'.runtime/documents/identity.json', ROOT/'.runtime/corpus/journal/revocations.jsonl')}
        archive_current(output, status)
        before = restoration.snapshot(scope)
        restoration.save(output/'database-before.json', before)
        report['backup'] = restoration.backup_database(output)
        report['old_spring_exit'] = restoration.retire(old_spring)
        if restoration.snapshot(scope) != before:
            raise RuntimeError('concurrent_durable_change_during_quiesce')
        report['old_proxy_exit'] = restoration.retire(old_proxy)
        for name in ('context-state.json', 'context-initialized'):
            shutil.copy2(ROOT/'.runtime/corpus/sql-proxy'/name, output/('retired-'+name))
        install(source, hashes, output)
        start_proxy(json.loads((ROOT/'.runtime/corpus/database.json').read_text()))
        wait_context_ready()
        current = json.loads((ROOT/'.runtime/corpus/sql-proxy/status.json').read_text())
        if runtime_identity(current)['status'] != 'PASS':
            raise RuntimeError('repaired_proxy_source_identity_mismatch')
        child, spring, token = launch(output)
        runtime.wait_spring({'port': 18080}, child, token)
        report['http'] = restoration.verify_http(token)
        after = restoration.snapshot(scope)
        restoration.save(output/'database-after.json', after)
        if after != before or any(support.digest(ROOT/name) != digest for name, digest in identities.items()):
            raise RuntimeError('durable_or_private_identity_changed')
        if process_identity(pg_pid) != pg_identity:
            raise RuntimeError('postgres_incarnation_changed')
        spring_identity = process_identity(spring['pid'])
        if spring_identity is None or spring_identity['start_ticks'] != spring['start']:
            raise RuntimeError('new_spring_identity_unstable')
        report.update(status='RUNNING_BEFORE_LAUNCHER_RETURN', spring_pid=spring['pid'],
                      spring_identity=spring_identity, proxy_pid=current['pid'],
                      postgres_pid=pg_pid, postgres_identity=pg_identity, durable_state_unchanged=True,
                      private_identity_unchanged=True, session_id=os.getsid(spring['pid']),
                      private_launch_file=str(ROOT/'.runtime/launch.url'))
        temporary = ROOT/'.runtime/local-preview-owner.new'
        restoration.save(temporary, {'spring_pid': spring['pid'], 'spring_identity': spring_identity,
                         'proxy_pid': current['pid'], 'profile': 'DEFAULT',
                         'restoration_evidence': str(output/'report.json')})
        os.replace(temporary, ROOT/'.runtime/local-preview-owner.json')
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        report['failure_code'] = str(error) if isinstance(error, RuntimeError) else 'private_diagnostics_retained'
    finally:
        restoration.save(output/'report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'profile', 'p1_full33', 'F1_enabled', 'postgres_restarted')}))
    return 0 if report['status'] == 'RUNNING_BEFORE_LAUNCHER_RETURN' else 1


if __name__ == '__main__':
    raise SystemExit(main())
