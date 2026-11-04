#!/usr/bin/env python3
"""Freeze exact copied installations and build identities, with no live runtime reads."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import uuid

from harness_common import (HERE, ROOT, command, digest, packed, read_private, record, regular,
                            relative_name, root_hash, validate_root, write_private)

COPY_TREES = ('retrieval', 'scripts', 'config', 'db', 'spec', 'backend/src')
COPY_FILES = ('backend/pom.xml', 'gates/document/headless-preview-fixture.json')
TARGET_TREES = ('classes', 'dependency', 'solver')
TOOL_TREES = ('.tools/retrieval/postgres',)
TOOL_FILES = ('.tools/sqlean/sqlean_pg_grammar',
              '.tools/retrieval-downloads/postgresql-16.15.tar.bz2',
              '.tools/retrieval-downloads/pgvector-0.8.7.tar.gz')


def approval_anchors():
    """Bind the exact approved contract and finite abstract model without overstating it."""
    names = ('contract.json', 'experiment.json', 'council-disposition.json', 'formal-runs/final-v1/report.json',
             'review-input-pins.json')
    council = json.loads((HERE.parent/names[2]).read_text())
    formal = json.loads((HERE.parent/names[3]).read_text())
    decisions = [row['decision'] for row in council['reviews']]
    if council['status'] != 'APPROVED_IMPLEMENTATION_CONTRACT_ONLY' or decisions != ['APPROVE_IMPLEMENTATION_CONTRACT']*6:
        raise ValueError('exact_six_seat_approval_required')
    if formal['status'] != 'VERIFIED' or formal['input_root_hash'] != council['package_root_sha256']:
        raise ValueError('formal_approval_root_mismatch')
    if formal['claims'] != {'total': 36, 'passed': 36, 'blocked': 0, 'unresolved': 0} or formal['determinism'] != 'PASS':
        raise ValueError('formal_finite_claim_receipt_required')
    pins = json.loads((HERE.parent/names[4]).read_text())
    expected = {row['path']: row['sha256'] for row in pins['files']}
    if pins['input_root_sha256'] != formal['input_root_hash']:
        raise ValueError('approval_input_pin_root')
    for name in names[:2]:
        if expected.get(str((HERE.parent/name).relative_to(ROOT))) != digest(HERE.parent/name):
            raise ValueError('contract_or_experiment_differs_from_reviewed_bytes')
    return [record(HERE.parent/name, HERE.parent) for name in names]


def inventory(root, trees, names=(), include_bytecode=False):
    """Enumerate source files while excluding caches, never silently following aliases."""
    result = []
    for tree in trees:
        for path in sorted((root/tree).rglob('*')):
            if not include_bytecode and ('__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo')):
                continue
            if path.is_symlink():
                raise ValueError('source_inventory_symlink')
            if path.is_file():
                regular(path)
                result.append(record(path, root))
    for name in names:
        regular(root/name)
        result.append(record(root/name, root))
    return sorted(result, key=lambda row: row['path'])


def require_inventory(root, rows, expected):
    """Require complete exact identities instead of accepting a partial ready receipt."""
    actual = {row['path']: row['sha256'] for row in expected}
    supplied = {}
    for row in rows:
        name = str(relative_name(row['path']))
        if name in supplied or not re.fullmatch('[0-9a-f]{64}', row['sha256']):
            raise ValueError('ready_inventory_duplicate_or_digest')
        regular(root/name)
        if digest(root/name) != row['sha256']:
            raise ValueError('source_ready_input_mismatch')
        supplied[name] = row['sha256']
    if not actual.items() <= supplied.items():
        raise ValueError('source_ready_inventory_incomplete')
    return supplied


def source_ready(path):
    """Bind all copied source and concrete compiled bytes before preparation."""
    value = json.loads(path.read_text())
    if value.get('status') != 'SOURCE_READY':
        raise ValueError('source_ready_status_required')
    sources = inventory(ROOT, COPY_TREES, COPY_FILES)
    require_inventory(ROOT, value['files'], sources)
    target = Path(value['backend_target']['path'])
    if not target.is_absolute() or target.resolve() != target or '.runtime' in target.parts:
        raise ValueError('exact_backend_target_required')
    compiled = inventory(target, TARGET_TREES)
    supplied = require_inventory(target, value['backend_target']['files'], compiled)
    if set(supplied) != {row['path'] for row in compiled}:
        raise ValueError('compiled_inventory_surplus')
    if not (target/'classes/dev/allow/backend/AllowApplication.class').is_file():
        raise ValueError('spring_compiled_target_required')
    return value, sources, target, compiled


def copy_probe_classes(receipt, target, destination):
    """Copy only explicitly frozen gate-probe classes, never an ambient test classpath."""
    rows = receipt.get('probe_classes', [])
    if not rows:
        return []
    required = {str(relative_name(row['path'])) for row in rows}
    prefixes = tuple('dev/allow/backend/'+name for name in ('WarmPoolProbeMain', 'WarmProbeFiles',
                     'WarmProbeWitness', 'WarmProbeSession', 'WarmProbeFailures', 'FreshTier1ProbeMain', 'WarmSemanticProbeMain',
                     'WarmSemanticCase', 'WarmSemanticOwned', 'WarmSemanticProtocol',
                     'WarmProbeSequence', 'WarmSequenceRecords', 'WarmSequenceIdle',
                     'WarmLatencyMain', 'WarmLatencySeries', 'WarmLatencyFresh', 'WarmLatencyPool',
                     'WarmLatencyRecords', 'WarmLatencyResources'))
    if len(required) != len(rows) or not all(any(name == prefix+'.class' or
            name.startswith(prefix+'$') and name.endswith('.class') for prefix in prefixes) for name in required):
        raise ValueError('explicit_probe_class_inventory_required')
    expected = [record(target/'test-classes'/name, target/'test-classes') for name in sorted(required)]
    require_inventory(target/'test-classes', rows, expected)
    return copy_rows(target/'test-classes', destination, expected, '.gate/probe-classes')


def copy_rows(source, destination, rows, prefix=''):
    """Copy bytes into new inodes and preserve only their declared modes."""
    result = []
    for row in rows:
        original = source/relative_name(row['path'])
        regular(original)
        target = destination/prefix/row['path']
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(original, target, follow_symlinks=False)
        regular(target)
        if digest(target) != row['sha256'] or original.stat().st_ino == target.stat().st_ino:
            raise ValueError('fresh_copy_identity_failure')
        result.append(record(target, destination))
    return result


def external_tree(path):
    """Pin managed tooling/JDK files and every symlink resolution without copying data."""
    files, links = [], []
    for entry in sorted(path.rglob('*')):
        if entry.is_symlink():
            links.append({'path': str(entry), 'resolved': str(entry.resolve()),
                          'exists': entry.exists(), 'link_text': os.readlink(entry)})
        if entry.is_file():
            files.append(record(entry.resolve()))
    return files, links


def copy_tool_installation(destination):
    """Materialize executable installation aliases into independent regular files only."""
    paths = [path for tree in TOOL_TREES for path in sorted((ROOT/tree).rglob('*')) if path.is_file()]
    paths += [ROOT/name for name in TOOL_FILES]
    rows = []
    for source in paths:
        target = destination/source.relative_to(ROOT)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(source.resolve(strict=True), target)
        regular(target)
        if digest(source) != digest(target):
            raise ValueError('tool_installation_copy_mismatch')
        rows.append(record(target, destination))
    return rows


def freeze_bytecode(root):
    """Generate ordinary timestamp caches with the pinned managed compiler before any runtime."""
    script = ('import compileall,importlib.util,json,sys; from pathlib import Path; '
              'root=Path(sys.argv[1]); '
              'assert compileall.compile_dir(str(root/"retrieval"),ddir="/allow-frozen/retrieval",quiet=2,force=True,workers=1); '
              'print(json.dumps({"cache_tag":sys.implementation.cache_tag,"files":'
              '[{"source":str(p.relative_to(root)),"path":str(Path(importlib.util.cache_from_source(str(p))).relative_to(root))}'
              ' for p in sorted((root/"retrieval").rglob("*.py"))]}))')
    compiler = root/'.tools/retrieval-venv/bin/python'
    output = command([compiler, '-I', '-B', '-c', script, root], timeout=90,
                     env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    value = json.loads(output)
    rows = []
    for row in value['files']:
        source = root/row['source']
        cache = root/row['path']
        rows.append(dict(row, source_sha256=digest(source), sha256=digest(cache),
                         source_mtime_seconds=int(source.stat().st_mtime), source_bytes=source.stat().st_size))
    return {'compiler': record(compiler.resolve()), 'cache_tag': value['cache_tag'], 'invalidation': 'timestamp',
            'logical_compile_root': '/allow-frozen/retrieval',
            'files': rows, 'scope': 'Generated before launch; no module/server execution; exact bytes copied unchanged to F1'}


def verify_bytecode(root, bytecode):
    """Check registered cache/source correspondence and timestamp headers without executing caches."""
    require_tag = bytecode['cache_tag']
    if require_tag != 'cpython-312' or bytecode['invalidation'] != 'timestamp':
        raise ValueError('unregistered_python_cache_format')
    for row in bytecode['files']:
        source, cache = root/row['source'], root/row['path']
        header = cache.read_bytes()[:16]
        expected = source.parent/'__pycache__'/(source.stem+'.'+require_tag+'.pyc')
        if cache != expected or digest(source) != row['source_sha256'] or digest(cache) != row['sha256']:
            raise ValueError('python_cache_source_binding')
        if int.from_bytes(header[4:8], 'little') != 0 or int.from_bytes(header[8:12], 'little') != row['source_mtime_seconds']:
            raise ValueError('python_cache_timestamp_header')
        if int(source.stat().st_mtime) != row['source_mtime_seconds'] or source.stat().st_size != row['source_bytes']:
            raise ValueError('python_cache_source_metadata')
        if int.from_bytes(header[12:16], 'little') != row['source_bytes']:
            raise ValueError('python_cache_size_header')


def java_metadata():
    """Identify the fixed system JDK without accepting JVM options from environment."""
    java = Path('/usr/bin/java').resolve(strict=True)
    import subprocess
    run = subprocess.run([str(java), '-XshowSettings:properties', '-version'], capture_output=True,
                         text=True, timeout=15, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    values = {key.strip(): value.strip() for line in run.stderr.splitlines() if ' = ' in line
              for key, value in [line.split(' = ', 1)]}
    if run.returncode or not values.get('java.runtime.version', '').startswith('17.'):
        raise ValueError('reviewed_jdk17_required')
    return {'executable': str(java), 'home': values['java.home'],
            'runtime_version': values['java.runtime.version'], 'vendor': values['java.vendor']}


def external_tooling(java):
    """Pin managed dependencies, JDK/CDS/configuration and runtime dynamic libraries."""
    venv = (ROOT/'.tools/retrieval-venv').resolve(strict=True)
    stdlib = Path(command([venv/'bin/python', '-I', '-B', '-c',
                          'import sysconfig; print(sysconfig.get_path("stdlib"))'],
                          env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}).strip())
    paths, links, trees, absent = [], [], [], []
    system_stdlib = Path(command(['/usr/bin/python3', '-I', '-B', '-c',
                                  'import sysconfig; print(sysconfig.get_path("stdlib"))']).strip())
    search = json.loads(command(['/usr/bin/python3', '-I', '-B', '-c', 'import json,sys; print(json.dumps(sys.path))']))
    directories = {venv, stdlib, system_stdlib, Path(java['home']), Path('/etc/java-17-openjdk')}
    for name in search:
        path = Path(name)
        if path.is_dir():
            directories.add(path)
        elif path.is_file():
            paths.append(record(path))
        else:
            absent.append(str(path))
    for directory in sorted(directories):
        files, aliases = external_tree(directory)
        paths.extend(files)
        links.extend(aliases)
        trees.append({'root': str(directory), 'members': tool_members(directory)})
    binaries = ['/usr/bin/python3', sys.executable, '/usr/bin/systemd-run', '/usr/bin/systemctl', '/usr/bin/bwrap', '/usr/bin/prlimit', '/usr/bin/taskset',
                '/usr/bin/env', str(venv/'bin/python'), str(java['executable']),
                str(ROOT/'.tools/retrieval/postgres/bin/postgres'), str(ROOT/TOOL_FILES[0])]
    binaries.extend(str(path) for path in Path(java['home']).rglob('*.so') if path.is_file())
    binaries.extend(str(path) for path in (ROOT/'.tools/retrieval/postgres/lib').rglob('*.so') if path.is_file())
    binaries.extend(str(path) for directory in (stdlib, system_stdlib) for path in directory.rglob('*.so') if path.is_file())
    for name in binaries:
        supplied = Path(name)
        if supplied.is_symlink():
            links.append({'path': str(supplied), 'resolved': str(supplied.resolve()),
                          'exists': supplied.exists(), 'link_text': os.readlink(supplied)})
        path = supplied.resolve(strict=True)
        paths.append(record(path))
        output = command(['/usr/bin/ldd', str(path)])
        for line in output.splitlines():
            match = re.search(r'(/[^\s]+)\s+\(0x', line)
            if match:
                paths.append(record(Path(match.group(1)).resolve(strict=True)))
    unique = {row['path']: row for row in paths}
    for name in ('/etc/apparmor.d/chatgpt', '/etc/apparmor.d/unprivileged_userns'):
        unique[name] = record(Path(name))
    return {'files': sorted(unique.values(), key=lambda row: row['path']), 'links': links, 'trees': trees,
            'absent_paths': absent, 'system_python_import_paths': search,
            'aliases': [{'alias': '.tools/retrieval-venv', 'resolved': str(venv)}]}


def tool_members(root):
    """Bind the complete executable dependency tree, including bytecode and dangling aliases."""
    return sorted(str(path.relative_to(root)) for path in root.rglob('*') if path.is_file() or path.is_symlink())


def build_identity(root, runtime_version):
    """Transcribe current POSIX BuildIdentity order; this is a checked byte identity only."""
    import hashlib
    target = root/'backend/target'
    paths = sorted(path for path in (target/'classes').rglob('*') if path.is_file())
    paths += sorted(path for path in (target/'dependency').rglob('*.jar') if path.is_file())
    paths.append(target/'solver/alloy.jar')
    value = hashlib.sha256()
    for path in paths:
        value.update(str(path.relative_to(target)).encode() + b'\0')
        with path.open('rb') as stream:
            while chunk := stream.read(8192):
                value.update(chunk)
        value.update(b'\0')
    value.update(runtime_version.encode())
    return {'value': value.hexdigest(), 'java_runtime_version': runtime_version,
            'ordered_paths': [str(path.relative_to(target)) for path in paths],
            'interpretation': 'Independent POSIX byte transcription, not semantic refinement'}


def finalize(manifest, root, variant, run_id):
    """Refresh a separately checked F0/F1 copy; callers must enforce its allowed delta."""
    root = validate_root(root)
    result = copy.deepcopy(manifest)
    suffix = '.scope'
    result.update(copied_root=str(root), variant=variant, run_id=run_id,
                  unit='allow-wp-' + uuid.uuid4().hex + suffix)
    result['files'] = [record(root/row['path'], root) for row in manifest['files']]
    result['build_identity'] = build_identity(root, result['java']['runtime_version'])
    result['input_root_sha256'] = root_hash(result)
    return result


def verify_tools(tooling):
    """Reject mutated pinned external tooling bytes and changed alias resolutions."""
    for row in tooling['files']:
        actual = record(Path(row['path']))
        if actual != row:
            raise ValueError('pinned_external_tool_mutated')
    for row in tooling['links']:
        path = Path(row['path'])
        if not path.is_symlink() or str(path.resolve()) != row['resolved']:
            raise ValueError('external_tool_link_mutated')
        if path.exists() != row['exists'] or os.readlink(path) != row['link_text']:
            raise ValueError('external_tool_link_mutated')
    for tree in tooling['trees']:
        if tool_members(Path(tree['root'])) != tree['members']:
            raise ValueError('external_tool_inventory_surplus_or_missing')
    for name in tooling.get('absent_paths', []):
        if Path(name).exists() or Path(name).is_symlink():
            raise ValueError('previously_absent_tool_input_appeared')


def verify_copied_members(root, manifest, fresh):
    """Reject surplus executable inputs and disagreement between run and owner manifests."""
    expected = {row['path'] for row in manifest['files']}
    aliases = {row['alias'] for row in manifest['tooling']['aliases']}
    observed = set()
    for path in root.rglob('*'):
        name = str(path.relative_to(root))
        if name == '.gate/manifest.json':
            if packed(read_private(path)) != packed(manifest):
                raise ValueError('owner_manifest_disagrees_with_run_manifest')
        elif not fresh and (name.startswith(('.runtime/', '.gate/evidence/')) or name in runtime_evidence_names(manifest)):
            if path.is_symlink() or (path.is_file() and path.stat().st_nlink != 1):
                raise ValueError('mutable_runtime_alias')
            continue
        elif path.is_symlink():
            if name not in aliases:
                raise ValueError('copied_alias_surplus')
        elif path.is_file():
            observed.add(name)
        elif not path.is_dir():
            raise ValueError('copied_special_file')
    if observed != expected:
        raise ValueError('copied_inventory_surplus_or_missing')


def runtime_evidence_names(manifest):
    """Permit only named runtime receipts/logs, never executable caches or arbitrary gate files."""
    names = ['unit-invocation.json']
    if manifest.get('launch_lane') == 'owned_delegated_scope_v1':
        names += ['scope-intent.json', 'scoped-owner.json', 'scope-release.json', 'scope-private.log',
                  'scope-placement.json', 'scope-launch-failure.json', 'scope-failed-cleanup.json',
                  'scope-configure.json', 'delegation-ready.json']
    return {'.gate/'+name for name in names}


def verify(manifest, fresh=True):
    """Reject mutations and live-state aliases before accepting a prepared installation."""
    root = validate_root(manifest['copied_root'])
    if root_hash(manifest) != manifest['input_root_sha256']:
        raise ValueError('manifest_root_mismatch')
    for row in manifest['approval_anchors']:
        if digest(HERE.parent/row['path']) != row['sha256']:
            raise ValueError('approved_gate_anchor_mutation')
    names = set()
    for row in manifest['files']:
        name = str(relative_name(row['path']))
        if name in names:
            raise ValueError('manifest_duplicate_path')
        names.add(name)
        regular(root/name)
        if record(root/name, root) != row:
            raise ValueError('copied_input_mutation')
    for row in manifest['tooling']['aliases']:
        alias = root/relative_name(row['alias'])
        if not alias.is_symlink() or str(alias.resolve()) != row['resolved']:
            raise ValueError('managed_tool_alias_mismatch')
    verify_tools(manifest['tooling'])
    immutable = (*COPY_TREES, 'backend/target', '.tools/retrieval/postgres', '.tools/sqlean',
                 '.tools/retrieval-downloads')
    observed = {row['path'] for row in inventory(root, immutable, COPY_FILES, include_bytecode=True)}
    expected = {name for name in names if not name.startswith('.gate/')}
    if observed != expected:
        raise ValueError('copied_inventory_surplus_or_missing')
    if fresh and (root/'.runtime').exists():
        raise ValueError('fresh_runtime_required')
    verify_copied_members(root, manifest, fresh)
    if 'python_bytecode' in manifest:
        verify_bytecode(root, manifest['python_bytecode'])
    if build_identity(root, manifest['java']['runtime_version']) != manifest['build_identity']:
        raise ValueError('compiled_build_identity_mismatch')
    return root


def prepare(arguments, transform=None):
    """Copy a frozen DEFAULT installation; authoring creates no daemon or SQL connection."""
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,40}', arguments.run_id):
        raise ValueError('run_id_invalid')
    receipt, sources, target, compiled = source_ready(arguments.source_ready)
    receipt_sha256 = digest(arguments.source_ready)
    run = HERE/'runs'/arguments.run_id
    run.mkdir(mode=0o700, parents=True, exist_ok=False)
    expected_bytes = sum(row['size'] for row in [*sources, *compiled])
    expected_bytes += sum(path.stat().st_size for tree in TOOL_TREES for path in (ROOT/tree).rglob('*') if path.is_file())
    expected_bytes += sum((ROOT/name).stat().st_size for name in TOOL_FILES)
    free = shutil.disk_usage('/tmp').free
    reserve = {'free_bytes': free, 'planned_copy_bytes': expected_bytes, 'additional_cache_evidence_allowance': 134217728,
               'minimum_remaining_headroom': 2147483648, 'status': 'PASS' if free >= expected_bytes+2281701376 else 'BLOCKED'}
    write_private(run/'disk-reservation.json', reserve)
    if reserve['status'] != 'PASS':
        raise ValueError('prepared_copy_disk_headroom_required')
    root = Path(tempfile.mkdtemp(prefix='allow-wp-'))
    root.chmod(0o700)
    write_private(run/'preparation-started.json', {'copied_root': str(root), 'source_ready_sha256': receipt_sha256})
    files = copy_rows(ROOT, root, sources)
    files += copy_rows(target, root, compiled, 'backend/target')
    files += copy_probe_classes(receipt, target, root)
    files += copy_tool_installation(root)
    gate_rows = inventory(HERE, ('fixtures',), tuple(p.name for p in sorted(HERE.glob('*.py'))))
    gate_rows += inventory(HERE, (), ('runtime-claims.json', 'probe-cases.json', 'semantic-fixtures.json',
                                    'http-setup-expectation.json', 'latency-fixture.json', 'latency-expected.json'))
    files += copy_rows(HERE, root, gate_rows, '.gate')
    java = java_metadata()
    tooling = external_tooling(java)
    (root/'.gate/tmp').mkdir(mode=0o700)
    for row in tooling['aliases']:
        (root/row['alias']).symlink_to(row['resolved'], target_is_directory=True)
    bytecode = freeze_bytecode(root)
    files += [record(root/row['path'], root) for row in bytecode['files']]
    transformation = transform(root, java, files) if transform is not None else None
    if transformation is not None:
        files = [record(root/row['path'], root) for row in files]
    source_ready(arguments.source_ready)
    if digest(arguments.source_ready) != receipt_sha256:
        raise ValueError('source_ready_receipt_mutated_during_copy')
    return finish_prepare(arguments, run, root, files, tooling, java, bytecode, transformation)


def finish_prepare(arguments, run, root, files, tooling, java, bytecode, transformation=None):
    """Persist the exact prepared root and copied policy bindings before any launch."""
    import socket
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    inputs = {'schema_version': '1.0', 'port': port, 'files': sorted(files, key=lambda row: row['path']),
              'tooling': tooling, 'java': java, 'python_bytecode': bytecode,
              'launch_lane': 'owned_delegated_scope_v1',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'source_ready': {'path': str(arguments.source_ready.resolve()), 'sha256': digest(arguments.source_ready)},
              'approval_anchors': approval_anchors(),
              'contract_sha256': digest(HERE.parent/'contract.json'),
              'experiment_sha256': digest(HERE.parent/'experiment.json'),
              'workload_execution': 'HELD_CONCRETE_RUNTIME_REGISTRATION_AND_RELEASE_REQUIRED',
              'target_acceptance': 'OPEN', 'classification': 'PREPARED_NOT_EXECUTED'}
    if transformation is not None:
        inputs.update(diagnostic=True, transformation=transformation,
                      classification='DIAGNOSTIC_ONLY_NOT_SELECTION_EVIDENCE')
    manifest = finalize(inputs, root, 'W0', arguments.run_id)
    verify(manifest)
    write_private(root/'.gate/manifest.json', manifest)
    write_private(run/'manifest.json', manifest)
    return {'run_directory': str(run), 'copied_root': str(root),
            'input_root_sha256': manifest['input_root_sha256'], 'build_identity': manifest['build_identity']['value']}
