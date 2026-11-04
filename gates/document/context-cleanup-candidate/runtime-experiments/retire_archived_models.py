#!/usr/bin/env python3
"""Retire only four reviewed inert model copies after exact archive/restoration checks."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import uuid

import model_retention as retention
import experiment as support

HERE = retention.HERE
SELECTED = ('r11-regressions', 'r12-regressions', 'r13-regressions', 'r14-regressions')


def free_bytes():
    """Read available filesystem bytes without attributing concurrent activity to this action."""
    value = os.statvfs('/tmp')
    return value.f_bavail*value.f_frsize


def verified_plan():
    """Bind the reviewed immutable plan, restore proof and every archived file before retirement."""
    folder = HERE/'model-retention-r1'
    digest = json.loads((folder/'plan-sha256.json').read_text())['sha256']
    if support.digest(folder/'plan.json') != digest:
        raise RuntimeError('reviewed_plan_changed')
    plan = json.loads((folder/'plan.json').read_text())
    proof = json.loads((folder/'restoration-verification.json').read_text())
    if proof['status'] != 'RESTORED_VERIFIED' or proof['plan_sha256'] != digest:
        raise RuntimeError('restore_verification_missing')
    if support.digest(Path(plan['restore_driver']['path'])) != plan['restore_driver']['sha256']:
        raise RuntimeError('tested_restore_driver_changed')
    archive = Path(plan['archive']['path'])
    if archive.resolve() != archive or archive.parent.parent != retention.ARCHIVES:
        raise RuntimeError('archive_alias_rejected')
    actual = sorted(str(p.relative_to(archive)) for p in archive.rglob('*') if p.is_file())
    expected = sorted(row['path'] for row in plan['archive']['files'])
    if actual != expected:
        raise RuntimeError('archive_membership_changed')
    for row in plan['archive']['files']:
        path = archive/row['path']
        if path.is_symlink() or support.digest(path) != row['sha256']:
            raise RuntimeError('archive_bytes_changed')
    return folder, digest, plan, proof


def validate_target(current, original):
    """Require the exact originally reviewed files, metadata, roots and historical evidence."""
    for name in ('root', 'root_metadata', 'model_directory', 'directory_metadata', 'files', 'manifest', 'report'):
        if current[name] != original[name]:
            raise RuntimeError('reviewed_copy_input_or_metadata_changed')


def restore_command(folder, digest, run):
    """Provide literal argv so restoration needs no shell expansion or authority inference."""
    return ['/home/augustus/Allow/.tools/retrieval-venv/bin/python', str(HERE/'model_retention.py'),
            'restore', '--plan', str(folder/'plan.json'), '--plan-sha256', digest,
            '--run-id', run, '--receipt', str(folder/(run+'-restoration-receipt.json'))]


def retire_one(folder, digest, plan, target):
    """Atomically retire one verified tree and leave an explicit historical archived-input receipt."""
    model = Path(target['model_directory'])
    pending = model.with_name('models.retirement-pending-'+uuid.uuid4().hex)
    receipt_path = model.with_name('models.ARCHIVED-INPUT.json')
    if receipt_path.exists():
        raise RuntimeError('archival_receipt_already_exists')
    intent = {'run_id': target['run_id'], 'model_directory': str(model), 'pending_directory': str(pending),
              'plan_sha256': digest, 'status': 'RETIREMENT_INTENT_BEFORE_RENAME'}
    support.write_private(folder/(target['run_id']+'-retirement-intent.json'), intent)
    model.rename(pending)
    for row in target['files']:
        path = pending/row['path']
        if retention.metadata(path)['inode'] != row['inode']:
            raise RuntimeError('retired_file_identity_changed')
        path.unlink()
    pending.rmdir()
    receipt = {'status': 'ORIGINAL_MODEL_TREE_ARCHIVED', 'recorded_utc': datetime.now(timezone.utc).isoformat(),
               'run_id': target['run_id'], 'model_directory_at_recording': 'ABSENT',
               'not_a_substitute_for_original_regular_files': True, 'plan_path': str(folder/'plan.json'),
               'plan_sha256': digest, 'archive': plan['archive'], 'original_inventory': target,
               'restore_argv': restore_command(folder, digest, target['run_id']),
               'historical_manifest_and_report_unchanged': True,
               'restoration_note': 'A later restore must create distinct files and a separate restoration receipt; this immutable record describes archival time only.'}
    support.write_private(receipt_path, receipt)
    support.write_private(folder/(target['run_id']+'-archived-input-receipt.json'), receipt)
    return {'run_id': target['run_id'], 'model_directory_absent': not model.exists(),
            'receipt_path': str(receipt_path), 'receipt_sha256': support.digest(receipt_path),
            'removed_allocated_bytes': sum(row['allocated_bytes'] for row in target['files'])}


def remove_verification(folder, proof):
    """Remove only the newly created, hash-verified restore check authorized for cleanup."""
    model = Path(proof['destination'])
    if (not proof['verification_copy_only'] or model.name != 'models' or model.parent.parent != Path('/tmp')
            or not model.parent.name.startswith('allow-model-restore-check-') or model.resolve() != model):
        raise RuntimeError('verification_copy_path_invalid')
    metadata = retention.metadata(model.parent)
    if metadata['mode'] != 0o700 or list(model.parent.iterdir()) != [model]:
        raise RuntimeError('verification_parent_contains_unowned_files')
    if retention.references({'verification_copy': model.parent})['matching_owned_process_references']:
        raise RuntimeError('verification_copy_still_referenced')
    rows = []
    for row in proof['files']:
        path = model/row['path']
        current = retention.metadata(path)
        if (support.digest(path) != row['sha256'] or current['mode'] != row['mode']
                or current['mtime_ns'] != row['mtime_ns']):
            raise RuntimeError('verification_copy_changed')
        rows.append((path, current['allocated_bytes']))
    if {path.name for path, _ in rows} != {path.name for path in model.iterdir()}:
        raise RuntimeError('verification_membership_changed')
    for path, _ in rows:
        path.unlink()
    model.rmdir()
    model.parent.rmdir()
    value = {'status': 'AUTHORIZED_VERIFICATION_COPY_REMOVED', 'path': str(model.parent),
             'verification_receipt_sha256': support.digest(folder/'restoration-verification.json'),
             'removed_allocated_bytes': sum(size for _, size in rows), 'absence': not model.parent.exists()}
    support.write_private(folder/'verification-copy-cleanup.json', value)
    return value


def main():
    """Perform the parent's reviewed bounded archival; retain all original evidence and archive bytes."""
    os.umask(0o077)
    folder, digest, plan, proof = verified_plan()
    before = free_bytes()
    originals = {row['run_id']: row for row in plan['targets']}
    targets = [retention.target_inventory(run) for run in SELECTED]
    for target in targets:
        validate_target(target, originals[target['run_id']])
    absence = retention.references({row['run_id']: Path(row['root']) for row in targets})
    if absence['matching_owned_process_references']:
        raise RuntimeError('selected_copy_still_referenced')
    support.write_private(folder/'pre-retirement-check.json', {'status': 'PASS', 'targets': targets,
                          'absence': absence, 'plan_sha256': digest, 'free_bytes_before': before,
                          'operation_driver_sha256': support.digest(Path(__file__).resolve())})
    retired = [retire_one(folder, digest, plan, target) for target in targets]
    verification = remove_verification(folder, proof)
    for target in plan['targets']:
        for kind in ('manifest', 'report'):
            if support.digest(Path(target[kind]['path'])) != target[kind]['sha256']:
                raise RuntimeError('historical_evidence_changed')
    retained = originals['r15-regressions']
    if not Path(retained['model_directory']).is_dir():
        raise RuntimeError('r15_model_tree_missing')
    result = {'status': 'ARCHIVAL_COMPLETE', 'plan_sha256': digest, 'retired': retired,
              'verification_copy_cleanup': verification, 'r15_physically_retained': True,
              'private_archive_retained': True, 'canonical_model_touched': False, 'active_runtime_touched': False,
              'all_five_original_manifests_and_reports_unchanged': True,
              'removed_allocated_bytes': sum(row['removed_allocated_bytes'] for row in retired)+verification['removed_allocated_bytes'],
              'free_bytes_before': before, 'free_bytes_after': free_bytes(),
              'free_delta_caveat': 'Concurrent benchmark preparation may also consume disk; removed_allocated_bytes measures only this authorized action.',
              'restore_instructions': {run: restore_command(folder, digest, run) for run in SELECTED}}
    support.write_private(folder/'completion.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'removed_allocated_bytes', 'free_bytes_after',
                       'r15_physically_retained', 'all_five_original_manifests_and_reports_unchanged')}))


if __name__ == '__main__':
    main()
