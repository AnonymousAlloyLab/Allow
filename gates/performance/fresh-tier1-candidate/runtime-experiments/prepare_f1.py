#!/usr/bin/env python3
"""Prepare a new owned F1 copy; never modify the active installation or launch a service."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import installation
from harness_common import (HERE, digest, read_private, record, regular, relative_name,
                            validate_root, write_private)

SOURCE = 'backend/src/main/java/dev/allow/backend/DocumentQueries.java'
CLASS = 'backend/target/classes/dev/allow/backend/DocumentQueries.class'
BASELINE = 'private static final WorkerLaunchProfile ADVISORY_PROFILE = WorkerLaunchProfile.DEFAULT;'
TIER1 = 'private static final WorkerLaunchProfile ADVISORY_PROFILE = WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1;'


def require(condition, category):
    """Fail closed with a content-free category before consuming comparative evidence."""
    if not condition:
        raise ValueError(category)


def declared_tree(root, manifest):
    """Reject unregistered files, devices and aliases including unexpected gate inputs."""
    names = {row['path'] for row in manifest['files']}
    aliases = {row['alias']: row['resolved'] for row in manifest['tooling']['aliases']}
    require(set(aliases) == {'.tools/retrieval-venv'}, 'unexpected_tool_alias')
    observed = set()
    for path in root.rglob('*'):
        name = str(path.relative_to(root))
        if path.is_symlink():
            require(name in aliases and str(path.resolve(strict=True)) == aliases[name], 'copy_alias_denied')
        elif path.is_dir():
            continue
        elif path.is_file():
            regular(path)
            if name != '.gate/manifest.json':
                observed.add(name)
        else:
            raise ValueError('copy_special_file_denied')
    require(observed == names, 'copy_manifest_surplus_or_missing')


def patch_source(source):
    """Change only the reviewed enum constant, preserving every other source byte."""
    require(source.count(BASELINE.encode()) == 1 and TIER1.encode() not in source, 'default_profile_source_required')
    require(source.count(b'new DocumentWorker(ADVISORY_PROFILE)') == 1, 'single_advisory_callsite_required')
    patched = source.replace(BASELINE.encode(), TIER1.encode(), 1)
    require(patched.replace(TIER1.encode(), BASELINE.encode(), 1) == source, 'source_delta_mismatch')
    return patched


def new_copy(baseline, output, manifest):
    """Materialize declared bytes into fresh private inodes and the single pinned tool alias."""
    require(output.parent == Path('/tmp') and re.fullmatch(r'allow-ft1-[a-zA-Z0-9_-]{1,20}', output.name),
            'short_f1_root_required')
    output.mkdir(mode=0o700, exist_ok=False)
    validate_root(output)
    installation.copy_rows(baseline, output, manifest['files'])
    (output/'.gate/tmp').mkdir(mode=0o700, parents=True, exist_ok=True)
    for row in manifest['tooling']['aliases']:
        alias = output/relative_name(row['alias'])
        alias.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        alias.symlink_to(row['resolved'], target_is_directory=True)
    return output


def private_log(path, data):
    """Retain compiler diagnostics privately without allowing overwrite or link following."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)


def compile_query(root, manifest, evidence, label):
    """Recompile only the query class with fixed Java17 options and an empty source path."""
    target = root/'backend/target'
    javac = Path(manifest['java']['home'])/'bin/javac'
    require(str(javac.resolve(strict=True)) in {row['path'] for row in manifest['tooling']['files']},
            'unregistered_java_compiler')
    classpath = [target/'classes', target/'solver/alloy.jar', *sorted((target/'dependency').glob('*.jar'))]
    with tempfile.TemporaryDirectory(prefix='allow-ft1-javac-') as temporary:
        build = Path(temporary)
        (build/'classes').mkdir()
        (build/'empty').mkdir()
        argv = [str(javac), '--release', '17', '-g', '-parameters', '-proc:none', '-implicit:none',
                '-encoding', 'UTF-8', '-sourcepath', str(build/'empty'), '-classpath',
                os.pathsep.join(map(str, classpath)), '-d', str(build/'classes'), str(root/SOURCE)]
        result = subprocess.run(argv, capture_output=True, timeout=60,
                                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'})
        private_log(evidence/(label+'.stdout'), result.stdout)
        private_log(evidence/(label+'.stderr'), result.stderr)
        require(result.returncode == 0, 'query_compilation_failed')
        outputs = [str(path.relative_to(build/'classes')) for path in (build/'classes').rglob('*') if path.is_file()]
        require(outputs == ['dev/allow/backend/DocumentQueries.class'], 'query_compiler_surplus_output')
        return (build/'classes/dev/allow/backend/DocumentQueries.class').read_bytes()


def bytecode(root, manifest, name, verbose=False):
    """Inspect the actual copied callsites using the same pinned JDK, never source guesses alone."""
    javap = Path(manifest['java']['home'])/'bin/javap'
    require(str(javap.resolve(strict=True)) in {row['path'] for row in manifest['tooling']['files']},
            'unregistered_java_disassembler')
    command = [str(javap), '-v' if verbose else '-c', '-p', '-classpath', str(root/'backend/target/classes'), name]
    run = subprocess.run(command, capture_output=True, text=True, timeout=30,
                         env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'})
    require(run.returncode == 0, 'query_disassembly_failed')
    return run.stdout


def check_callsites(root, manifest, profile):
    """Check the bounded compiler selection and unchanged default mutation factory descriptor."""
    query = bytecode(root, manifest, 'dev.allow.backend.DocumentQueries')
    expected = 'WorkerLaunchProfile.' + profile + ':'
    require(query.count(expected) == 1, 'advisory_bytecode_profile_mismatch')
    require('DocumentWorker."<init>":(Ldev/allow/backend/WorkerLaunchProfile;)V' in query,
            'advisory_typed_constructor_missing')
    mutation = bytecode(root, manifest, 'dev.allow.backend.DocumentMutations', verbose=True)
    require('REF_newInvokeSpecial dev/allow/backend/DocumentWorker."<init>":()V' in mutation,
            'mutation_default_factory_missing')
    require('WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1' not in mutation, 'mutation_profile_escape')
    return {'advisory_profile': profile, 'typed_advisory_constructor': True, 'default_mutation_factory': True}


def verify_delta(baseline, output, manifest):
    """Require the complete copied source/class change set to equal the two approved files."""
    changed = []
    for row in manifest['files']:
        old, new = baseline/row['path'], output/row['path']
        regular(new)
        require(old.stat().st_ino != new.stat().st_ino or old.stat().st_dev != new.stat().st_dev,
                'copied_file_inode_alias')
        if record(new, output) != row:
            changed.append(row['path'])
    require(set(changed) == {SOURCE, CLASS}, 'unexpected_f1_delta')
    return [{'path': name, 'before_sha256': digest(baseline/name), 'after_sha256': digest(output/name)}
            for name in sorted(changed)]


def prepare(arguments):
    """Check F0, build deterministic F1 and freeze a separately owned complete manifest."""
    baseline = validate_root(arguments.baseline)
    manifest = read_private(baseline/'.gate/manifest.json')
    require(manifest['variant'] == 'F0', 'f0_baseline_required')
    require(installation.verify(manifest, fresh=True) == baseline, 'f0_root_binding_mismatch')
    declared_tree(baseline, manifest)
    evidence = arguments.evidence.absolute()
    require(evidence.is_relative_to(HERE/'runs') and evidence.resolve() == evidence, 'gate_evidence_path_required')
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    before = check_callsites(baseline, manifest, 'DEFAULT')
    recompiled = compile_query(baseline, manifest, evidence, 'baseline')
    require(recompiled == (baseline/CLASS).read_bytes(), 'baseline_compiler_identity_mismatch')
    output = new_copy(baseline, arguments.output, manifest)
    (output/SOURCE).write_bytes(patch_source((baseline/SOURCE).read_bytes()))
    first = compile_query(output, manifest, evidence, 'tier1-build-1')
    second = compile_query(output, manifest, evidence, 'tier1-build-2')
    require(first == second, 'nondeterministic_tier1_class')
    (output/CLASS).write_bytes(first)
    delta = verify_delta(baseline, output, manifest)
    after = check_callsites(output, manifest, 'DOCUMENT_ADVISORY_TIER1')
    return finalize(manifest, baseline, output, evidence, before, after, delta)


def finalize(manifest, baseline, output, evidence, before, after, delta):
    """Recheck source/tooling stability and write new manifests without claiming measured acceptance."""
    installation.verify(manifest, fresh=True)
    declared_tree(baseline, manifest)
    updated = installation.finalize(manifest, output, 'F1', manifest['run_id']+'-f1')
    updated['f1_recipe'] = {'verifier_sha256': digest(Path(__file__)), 'baseline_root': str(baseline),
                            'baseline_input_root_sha256': manifest['input_root_sha256'], 'delta': delta}
    from harness_common import root_hash
    updated['input_root_sha256'] = root_hash(updated)
    declared_tree(output, updated)
    installation.verify(updated, fresh=True)
    write_private(output/'.gate/manifest.json', updated)
    write_private(evidence/'manifest.json', updated)
    receipt = {'status': 'PREPARED_NOT_EXECUTED', 'variant': 'F1', 'copied_root': str(output),
               'input_root_sha256': updated['input_root_sha256'], 'build_identity': updated['build_identity'],
               'exact_delta': delta, 'callsites': [before, after], 'matching_class_builds': 2,
               'production_profile': 'DEFAULT_UNCHANGED', 'performance_acceptance': 'NOT_EXECUTED'}
    write_private(evidence/'recipe-receipt.json', receipt)
    return receipt


def main():
    """Parse only copied-root/evidence paths; the JVM choice is fixed by this recipe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    arguments = parser.parse_args()
    try:
        receipt = prepare(arguments)
        print(json.dumps({key: receipt[key] for key in ('status', 'copied_root', 'input_root_sha256')}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(json.dumps({'status': 'BLOCKED', 'reason': 'f1_preparation_failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
