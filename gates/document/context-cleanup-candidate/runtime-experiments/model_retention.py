#!/usr/bin/env python3
"""Prepare reversible model archives for a fixed set of inert owned regression copies.

Preparation never removes original inputs. Restoration always creates distinct
regular files and refuses existing destinations; original reports stay immutable.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

import experiment as support

HERE = Path(__file__).resolve().parent
RUNS = ('r11-regressions', 'r12-regressions', 'r13-regressions', 'r14-regressions', 'r15-regressions')
MODEL = Path('.tools/retrieval/models')
ARCHIVES = Path('/home/augustus/.local/state/allow-owned-regression-archives')


def metadata(path):
    """Capture restorable metadata and the observed physical ownership of a regular input."""
    value = path.lstat()
    if value.st_uid != os.getuid() or path.is_symlink():
        raise RuntimeError('unowned_or_aliased_input')
    return {'mode': stat.S_IMODE(value.st_mode), 'mtime_ns': value.st_mtime_ns,
            'uid': value.st_uid, 'gid': value.st_gid, 'device': value.st_dev,
            'inode': value.st_ino, 'size': value.st_size, 'allocated_bytes': value.st_blocks*512}


def references(roots):
    """Record current owned-process references and explicit visibility limitations without secrets."""
    found, limited = [], []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            command = (process/'cmdline').read_bytes()
            unreadable = []
            sources = {'cmdline': command}
            for name in ('maps', 'cwd', 'fd'):
                try:
                    if name == 'maps':
                        sources[name] = (process/name).read_bytes()
                    elif name == 'cwd':
                        sources[name] = os.readlink(process/name).encode()
                    else:
                        sources[name] = b'\0'.join(os.readlink(p).encode() for p in (process/name).iterdir())
                except PermissionError:
                    unreadable.append(name)
                except FileNotFoundError:
                    pass
            for run, root in roots.items():
                kinds = [kind for kind, value in sources.items() if str(root).encode() in value]
                if kinds:
                    found.append({'run': run, 'pid': int(process.name), 'reference_kinds': kinds})
            if unreadable:
                limited.append({'pid': int(process.name), 'unreadable': unreadable,
                                'cmdline_sha256': hashlib.sha256(command).hexdigest()})
        except (FileNotFoundError, ProcessLookupError):
            continue
    return {'matching_owned_process_references': found, 'visibility_limits': limited,
            'boundary': 'Prior exact owned-process cleanup receipts are primary; this additional current scan is not a universal claim about inaccessible unrelated processes.'}


def target_inventory(run):
    """Validate one owned completed or never-started copy against its frozen file manifest."""
    directory = HERE/'runs'/run
    manifest_path, report_path = directory/'manifest.json', directory/'report.json'
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(report_path.read_text())
    root = Path(manifest['copied_root'])
    if root.parent != Path('/tmp') or not root.name.startswith('allow-cc-') or root.resolve() != root:
        raise RuntimeError('unexpected_copy_root')
    root_meta = metadata(root)
    if root_meta['mode'] != 0o700 or not root.is_dir():
        raise RuntimeError('unsafe_copy_root')
    if run == 'r13-regressions':
        if report['status'] != 'INFRASTRUCTURE_FAILURE' or (root/'.runtime').exists():
            raise RuntimeError('failed_prepare_has_runtime')
    elif (report['status'] != 'PASS' or not report['spring_cleanup']['owned_identity_absent']
          or any(not row['owned_identity_absent'] or row['emergency_escalation'] for row in report['service_cleanup'])):
        raise RuntimeError('owned_cleanup_not_proven')
    proxy = root/'.runtime/corpus/sql-proxy/owner.json'
    proxy_observation = None
    if proxy.exists():
        owner = json.loads(proxy.read_text())
        current = support.process_identity(owner['pid'])
        if current is not None and current['start'] == owner['identity']['start_ticks']:
            raise RuntimeError('recorded_proxy_incarnation_live')
        proxy_observation = {'owner_receipt_sha256': support.digest(proxy), 'pid': owner['pid'],
                             'start_ticks': owner['identity']['start_ticks'], 'owned_incarnation_absent': True}
    model = root/MODEL
    if model.resolve() != model or not model.is_dir():
        raise RuntimeError('aliased_or_missing_models')
    frozen = {row['path']: row['sha256'] for row in manifest['files']}
    files = []
    for path in sorted(model.rglob('*')):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError('nonregular_model_member')
        row = dict(path=str(path.relative_to(model)), **metadata(path), sha256=support.digest(path))
        if row['sha256'] != frozen[str(path.relative_to(root))]:
            raise RuntimeError('model_differs_from_frozen_input')
        files.append(row)
    expected = {name for name in frozen if name.startswith(str(MODEL)+'/')}
    if expected != {str(MODEL/row['path']) for row in files}:
        raise RuntimeError('model_inventory_membership_mismatch')
    return {'run_id': run, 'root': str(root), 'root_metadata': root_meta,
            'model_directory': str(model), 'directory_metadata': metadata(model), 'files': files,
            'manifest': {'path': str(manifest_path), 'sha256': support.digest(manifest_path)},
            'report': {'path': str(report_path), 'sha256': support.digest(report_path)},
            'recorded_proxy_absence': proxy_observation,
            'prior_owned_cleanup': report.get('service_cleanup', 'NO_RUNTIME_EVER_STARTED'),
            'prior_spring_cleanup': report.get('spring_cleanup', 'NO_RUNTIME_EVER_STARTED')}


def content_rows(target):
    """Separate shared content identity from each copy's independently restorable metadata."""
    return [{key: row[key] for key in ('path', 'size', 'sha256')} for row in target['files']]


def prepare():
    """Inventory first, then copy and verify one private archive without removing any original."""
    os.umask(0o077)
    output = HERE/'model-retention-r1'
    output.mkdir(mode=0o700)
    targets = [target_inventory(run) for run in RUNS]
    absence = references({row['run_id']: Path(row['root']) for row in targets})
    if absence['matching_owned_process_references']:
        raise RuntimeError('owned_copy_still_referenced')
    inventory = {'created_utc': datetime.now(timezone.utc).isoformat(), 'targets': targets, 'absence': absence}
    support.write_private(output/'ownership-inventory.json', inventory)
    shared = content_rows(targets[0])
    if any(content_rows(row) != shared for row in targets[1:]):
        raise RuntimeError('model_contents_not_identical')
    identity = hashlib.sha256(support.packed(shared)).hexdigest()
    ARCHIVES.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ARCHIVES.is_symlink() or ARCHIVES.stat().st_uid != os.getuid() or stat.S_IMODE(ARCHIVES.stat().st_mode) != 0o700:
        raise RuntimeError('archive_root_not_private_owned')
    archive = ARCHIVES/('sha256-'+identity)
    archive.mkdir(mode=0o700)
    model = archive/'models'
    model.mkdir(mode=0o700)
    for row in shared:
        source = Path(targets[0]['model_directory'])/row['path']
        destination = model/row['path']
        shutil.copyfile(source, destination)
        destination.chmod(0o400)
        if support.digest(destination) != row['sha256'] or destination.stat().st_ino == source.stat().st_ino:
            raise RuntimeError('archive_copy_identity_failure')
    model.chmod(0o500)
    archive_inventory = {'content_sha256': identity, 'files': shared, 'source_inventory_sha256': support.digest(output/'ownership-inventory.json')}
    support.write_private(archive/'content-manifest.json', archive_inventory)
    original_bytes = sum(sum(row['allocated_bytes'] for row in target['files']) for target in targets)
    value = {'id': 'ALLOW-OWNED-MODEL-RETENTION-R1', 'status': 'PREPARED_NO_ORIGINAL_DELETION',
             'inventory': {'path': str(output/'ownership-inventory.json'), 'sha256': support.digest(output/'ownership-inventory.json')},
             'archive': {'path': str(model), 'content_sha256': identity, 'files': shared,
                         'manifest_path': str(archive/'content-manifest.json'), 'manifest_sha256': support.digest(archive/'content-manifest.json')},
             'targets': targets, 'restore_driver': {'path': str(Path(__file__).resolve()), 'sha256': support.digest(Path(__file__).resolve())},
             'original_allocated_bytes': original_bytes, 'archive_logical_bytes': sum(row['size'] for row in shared),
             'expected_net_reclaim_after_all_five': original_bytes-sum(row['size'] for row in shared),
             'recommended_order': ['r11-regressions', 'r12-regressions', 'r13-regressions', 'r14-regressions', 'r15-regressions'],
             'r15_condition': 'Archive r15 only after the binding consumer accepts archived-input receipts or restores before any physical-input verification. No manifest/report may be rewritten.',
             'deletion_barrier': 'Parent must review this prepared plan before original model bytes are removed. No symlink or hardlink may masquerade as original physical inputs.',
             'future_receipt': 'Each retired directory will be replaced by sibling models.ARCHIVED-INPUT.json binding this plan, original inventory, archive and restoration command. Historical manifests remain exact and unchanged.',
             'canonical_model_touched': False, 'active_runtime_touched': False, 'original_bytes_removed': 0}
    support.write_private(output/'plan.json', value)
    support.write_private(output/'plan-sha256.json', {'sha256': support.digest(output/'plan.json')})
    print(json.dumps({'status': value['status'], 'plan': str(output/'plan.json'), 'archive': str(model),
                      'shared_model_files': len(shared), 'expected_net_reclaim_bytes': value['expected_net_reclaim_after_all_five']}))


def restore(arguments):
    """Recreate one exact metadata tree as distinct regular files; never overwrite an existing tree."""
    if support.digest(arguments.plan) != arguments.plan_sha256:
        raise RuntimeError('retention_plan_digest_mismatch')
    plan = json.loads(arguments.plan.read_text())
    if support.digest(Path(__file__).resolve()) != plan['restore_driver']['sha256']:
        raise RuntimeError('restore_driver_changed')
    target = next(row for row in plan['targets'] if row['run_id'] == arguments.run_id)
    source = Path(plan['archive']['path'])
    if source.is_symlink() or source.resolve() != source or source.parent.parent != ARCHIVES:
        raise RuntimeError('archive_alias_rejected')
    if support.digest(Path(plan['archive']['manifest_path'])) != plan['archive']['manifest_sha256']:
        raise RuntimeError('archive_manifest_changed')
    destination = Path(target['model_directory'])
    if arguments.verification_copy:
        destination = Path(tempfile.mkdtemp(prefix='allow-model-restore-check-'))/'models'
    else:
        if metadata(Path(target['root']))['inode'] != target['root_metadata']['inode']:
            raise RuntimeError('original_copy_root_replaced')
        if references({target['run_id']: Path(target['root'])})['matching_owned_process_references']:
            raise RuntimeError('owned_copy_still_referenced')
    if destination.exists() or destination.is_symlink() or destination.parent.resolve() != destination.parent:
        raise RuntimeError('restore_destination_exists_or_aliased')
    destination.mkdir(mode=0o700)
    restored = []
    for row in target['files']:
        archived, result = source/row['path'], destination/row['path']
        if archived.is_symlink() or support.digest(archived) != row['sha256']:
            raise RuntimeError('archived_model_corrupt')
        shutil.copyfile(archived, result)
        os.chmod(result, row['mode'])
        os.utime(result, ns=(row['mtime_ns'], row['mtime_ns']))
        observed = metadata(result)
        if (support.digest(result) != row['sha256'] or observed['mode'] != row['mode']
                or observed['mtime_ns'] != row['mtime_ns'] or result.stat().st_nlink != 1
                or result.stat().st_ino == archived.stat().st_ino):
            raise RuntimeError('restored_model_identity_mismatch')
        restored.append({'path': row['path'], 'sha256': row['sha256'], 'mode': observed['mode'],
                         'mtime_ns': observed['mtime_ns'], 'distinct_regular_file': True})
    directory = target['directory_metadata']
    os.chmod(destination, directory['mode'])
    os.utime(destination, ns=(directory['mtime_ns'], directory['mtime_ns']))
    receipt = {'status': 'RESTORED_VERIFIED', 'plan_sha256': arguments.plan_sha256,
               'run_id': arguments.run_id, 'destination': str(destination), 'files': restored,
               'directory_mode': stat.S_IMODE(destination.stat().st_mode),
               'directory_mtime_ns': destination.stat().st_mtime_ns,
               'verification_copy_only': arguments.verification_copy, 'original_reports_modified': False}
    support.write_private(arguments.receipt, receipt)
    print(json.dumps({'status': receipt['status'], 'destination': str(destination), 'files': len(restored),
                      'verification_copy_only': arguments.verification_copy}))


def main():
    """Expose preparation and explicit restoration; original-input deletion is deliberately separate."""
    parser = argparse.ArgumentParser()
    operations = parser.add_subparsers(dest='operation', required=True)
    operations.add_parser('prepare')
    command = operations.add_parser('restore')
    command.add_argument('--plan', required=True, type=Path)
    command.add_argument('--plan-sha256', required=True)
    command.add_argument('--run-id', required=True, choices=RUNS)
    command.add_argument('--receipt', required=True, type=Path)
    command.add_argument('--verification-copy', action='store_true')
    arguments = parser.parse_args()
    prepare() if arguments.operation == 'prepare' else restore(arguments)


if __name__ == '__main__':
    main()
