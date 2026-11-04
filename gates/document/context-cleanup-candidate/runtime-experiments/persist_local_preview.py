#!/usr/bin/env python3
"""Apply the authorized detached-launch correction without repeating database restoration."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import restore_local_preview as restoration
import regression_experiment as runtime
import experiment as support

ROOT, HERE = restoration.ROOT, restoration.HERE


def relocate_backup(output):
    """Move only the owned old target out of the authored tree, binding every file."""
    source = ROOT/'backend/target.before-local-preview-r1'
    rows = [{'path': str(p.relative_to(source)), 'sha256': support.digest(p)}
            for p in sorted(source.rglob('*')) if p.is_file()]
    if not rows:
        raise RuntimeError('owned_rollback_target_missing')
    container = Path(tempfile.mkdtemp(prefix='allow-preview-rollback-'))
    container.chmod(0o700)
    target = container/'target'
    shutil.move(str(source), str(target))
    if any(support.digest(target/row['path']) != row['sha256'] for row in rows):
        raise RuntimeError('rollback_target_move_changed_bytes')
    value = {'original_path': str(source), 'preserved_path': str(target), 'files': rows,
             'source_absent': not source.exists(), 'all_hashes_preserved': True}
    restoration.save(output/'rollback-relocation.json', value)
    return {'path': str(target), 'file_count': len(rows), 'receipt_sha256': support.digest(output/'rollback-relocation.json')}


def main():
    """Start the same tested DEFAULT argv in an independent session and retain ownership."""
    os.umask(0o077)
    output = HERE/'local-preview-restoration-r2'
    output.mkdir(mode=0o700)
    report = {'status': 'BLOCKED', 'classification': 'NARROW_LOCAL_DEV_LAUNCH_PERSISTENCE_FIX',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'profile': 'DEFAULT',
              'p1_full33': 'BLOCKED', 'F1_enabled': False, 'postgres_restarted': False}
    from allow_documents.identity import load
    from bootstrap_corpus import process_identity
    from verify_sql_runtime import runtime_identity
    try:
        previous = json.loads((HERE/'local-preview-restoration-r1/report.json').read_text())
        if process_identity(previous['new_spring_identity']['pid']) is not None:
            raise RuntimeError('unexpected_previous_spring_still_live')
        status = json.loads((ROOT/'.runtime/corpus/sql-proxy/status.json').read_text())
        if runtime_identity(status)['status'] != 'PASS' or status['context']['status'] != 'READY':
            raise RuntimeError('proxy_not_ready_for_narrow_launch')
        receipt = json.loads((ROOT/'gates/performance/fresh-tier1-candidate/runtime-experiments/source-ready-r1.json').read_text())['backend_target']
        if any(support.digest(ROOT/'backend/target'/r['path']) != r['sha256'] for r in receipt['files']):
            raise RuntimeError('installed_default_target_changed')
        before = restoration.snapshot(load())
        if before != json.loads((HERE/'local-preview-restoration-r1/database-after.json').read_text()):
            raise RuntimeError('database_changed_since_first_restoration')
        report['rollback_target'] = relocate_backup(output)
        original = subprocess.Popen
        def detached(*arguments, **keywords):
            """Retain the tested command and private logs while detaching from the tool session."""
            keywords.update(start_new_session=True, stdin=subprocess.DEVNULL)
            return original(*arguments, **keywords)
        with patch.object(runtime.subprocess, 'Popen', side_effect=detached):
            child, owner, token = runtime.launch_spring(ROOT, output, {'java': str(runtime.JAVA), 'port': 18080}, 'spring')
        runtime.wait_spring({'port': 18080}, child, token)
        report['http'] = restoration.verify_http(token)
        after = restoration.snapshot(load())
        if after != before:
            raise RuntimeError('durable_state_changed_during_launch_fix')
        restoration.save(output/'database-before.json', before)
        restoration.save(output/'database-after.json', after)
        current = process_identity(owner['pid'])
        if current is None or current['start_ticks'] != owner['start']:
            raise RuntimeError('spring_identity_not_stable')
        report.update(status='RUNNING_BEFORE_LAUNCHER_RETURN', spring_pid=owner['pid'],
                      spring_identity=current, durable_state_unchanged=True,
                      session_id=os.getsid(owner['pid']), private_launch_file=str(ROOT/'.runtime/launch.url'))
        ownership = {'spring_pid': owner['pid'], 'spring_identity': current,
                     'proxy_pid': status['pid'], 'profile': 'DEFAULT',
                     'restoration_evidence': str(output/'report.json')}
        temporary = ROOT/'.runtime/local-preview-owner.new'
        restoration.save(temporary, ownership)
        os.replace(temporary, ROOT/'.runtime/local-preview-owner.json')
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        report['failure_code'] = str(error) if isinstance(error, RuntimeError) else 'private_diagnostics_retained'
    finally:
        restoration.save(output/'report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'profile', 'p1_full33', 'F1_enabled')}))
    return 0 if report['status'] == 'RUNNING_BEFORE_LAUNCHER_RETURN' else 1


if __name__ == '__main__':
    raise SystemExit(main())
