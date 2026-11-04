"""Create the single safety registration before any registered test execution."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from verify_safety import file_record, members, packed, sha, write_new


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
TARGET = HERE.parent/'build-r2/backend/target'
MAVEN = ROOT/'.tools/apache-maven-3.9.11'
JDK = Path('/usr/lib/jvm/java-17-openjdk-amd64')
CLASSES = ('WorkerLaunchProfileTest', 'FreshTier1SafetyTest', 'FreshTier1DeadlineTest',
           'FreshTier1SolverBaselineTest', 'DocumentWorkerLifecycleTest', 'DocumentValidationContextTest')


def main():
    """Pin source, compiled input, offline cache and tooling with exact predicates."""
    if (HERE/'manifest.json').exists():
        raise RuntimeError('REGISTRATION_ALREADY_FROZEN')
    repository = HERE/'maven-repository'
    shutil.copytree(Path('/home/augustus/.m2/repository'), repository, symlinks=True)
    files, links, trees = {}, {}, []

    def admit(path):
        """Register regular contents and literal aliases without hiding resolution."""
        path = Path(path)
        if path.is_symlink():
            links[str(path)] = {'path': str(path), 'link_text': os.readlink(path),
                                'resolved': str(path.resolve())}
        if path.is_file():
            resolved = path.resolve()
            files[str(resolved)] = file_record(resolved)

    def tree(path):
        """Pin a complete tree so extra executable inputs cannot appear silently."""
        path = Path(path)
        trees.append({'path': str(path), 'members': members(path)})
        for item in path.rglob('*'):
            admit(item)

    for path in (TARGET/'classes', TARGET/'test-classes', TARGET/'dependency', TARGET/'solver',
                 TARGET.parent/'src', repository, MAVEN, JDK, Path('/etc/java-17-openjdk'),
                 Path('/usr/lib/python3.12')):
        tree(path)
    for path in (TARGET.parent/'pom.xml', TARGET.parent.parent/'config/checkstyle.xml',
                 TARGET.parent.parent/'spec/egraph-rules.json', HERE/'settings.xml',
                 HERE/'verify_safety.py', HERE/'freeze_safety.py', HERE.parent/'safety-claims.json',
                 HERE.parent/'probe-r2-build.json', HERE.parent.parent/'contract.json',
                 HERE.parent.parent/'formal-activation.json', Path('/etc/ld.so.cache'),
                 Path('/etc/os-release'), Path('/proc/sys/kernel/random/boot_id')):
        admit(path)
    methods = []
    source_bindings = []
    for name in CLASSES:
        source = TARGET.parent/'src/test/java/dev/allow/backend'/f'{name}.java'
        current = ROOT/'backend/src/test/java/dev/allow/backend'/f'{name}.java'
        assert sha(source) == sha(current), 'CURRENT_TEST_SOURCE_MISMATCH'
        admit(current)
        names = re.findall(r'@Test\s+(?:public\s+)?void\s+(\w+)\s*\(', source.read_text())
        assert names, 'NO_TEST_METHODS'
        methods.extend('dev.allow.backend.' + name + '#' + method for method in names)
        source_bindings.append({'class': 'dev.allow.backend.' + name, 'copied_source': str(source),
                                'current_source': str(current), 'sha256': sha(source), 'methods': names})
    assert len(methods) == len(set(methods)) == 36, 'EXACT_METHOD_COUNT_CHANGED'
    binary_paths = ['/usr/bin/python3', '/usr/bin/java', '/bin/sh', '/bin/cat', '/bin/kill',
                    '/usr/bin/bwrap', '/usr/bin/prlimit', '/usr/bin/dirname', '/usr/bin/readlink',
                    '/usr/bin/uname', '/usr/bin/expr', '/usr/bin/grep', '/usr/bin/tr', '/usr/bin/ls',
                    '/usr/bin/which', '/usr/bin/ldd']
    binary_paths += [str(path) for path in JDK.rglob('*.so')]
    binary_paths += [str(path) for path in Path('/usr/lib/python3.12/lib-dynload').glob('*.so')]
    for name in binary_paths:
        admit(Path(name))
        result = subprocess.run(['/usr/bin/ldd', str(Path(name).resolve())], capture_output=True,
                                timeout=10, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        for dependency in re.findall(rb'(/[^\s]+)\s+\(0x', result.stdout):
            admit(Path(os.fsdecode(dependency)))
    claims = json.loads((HERE.parent/'safety-claims.json').read_bytes())['claims']
    assert len(claims) == len({claim['id'] for claim in claims}) == 12
    for claim in claims:
        claim['status'] = 'FROZEN_NOT_EXECUTED'
        claim['claim_class'] = 'FINITE_RUNTIME_TEST'
        claim['verifier'] = 'V-REGISTERED-SUREFIRE-SAFETY'
        claim['pass_condition'] = 'Every exact referenced method occurs once with no failure/error/skip; all 36 suite methods pass; offline Maven exits 0; all original frozen inputs unchanged.'
        claim['block_conditions'] = ['Missing/duplicate/unexpected test method', 'Any failure/error/skip',
                                     'Nonzero/timeout execution', 'Input/root/verifier mutation',
                                     'Unregistered configuration or missing dependency']
        claim['public_claim'] = 'These finite test instances passed under the registered inputs and TCB.'
        assert set(claim['tests']).issubset(methods)
    argv = [str(MAVEN/'bin/mvn'), '-B', '-o', '-s', str(HERE/'settings.xml'), '-gs', str(HERE/'settings.xml'),
            '-f', str(TARGET.parent/'pom.xml'), '-Dmaven.repo.local=' + str(repository),
            '-Dtest=' + ','.join(CLASSES), '-DfailIfNoTests=true', '-Dsurefire.failIfNoSpecifiedTests=true',
            '-DforkCount=1', '-DreuseForks=true', 'org.apache.maven.plugins:maven-surefire-plugin:3.5.6:test']
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
                   'HOME': str(HERE/'private-home'), 'JAVA_HOME': str(JDK), 'MAVEN_SKIP_RC': '1',
                   'MAVEN_BASEDIR': str(HERE), 'MAVEN_OPTS': '-Duser.home=' + str(HERE/'private-home')}
    dependencies = {'verified': [], 'trusted': [
        {'id': 'TCB-PYTHON-SHA-XML', 'description': 'Pinned CPython, standard library, SHA-256 and XML parser implement registration and evidence checks.'},
        {'id': 'TCB-MAVEN-JUNIT', 'description': 'Pinned Maven 3.9.11, Surefire 3.5.6, private offline dependency cache and JUnit/Mockito assertion/execution semantics.'},
        {'id': 'TCB-JDK', 'description': 'Pinned JDK 17.0.20.1 runtime, JVM flags, class loading and process implementation.'},
        {'id': 'TCB-OS', 'description': 'Recorded Linux kernel, /proc, process identities, clocks, namespaces, cgroups, loader and pinned user-space launch/native tools.'},
        {'id': 'TCB-HARDWARE', 'description': 'Workstation CPU, memory, filesystem and scheduling correctness; timings are not performance acceptance.'},
        {'id': 'TCB-TEST-INTERPRETATION', 'description': 'Frozen tests are finite operational assertions, not universal behavioral specifications or implementation-to-Lean correspondence.'}], 'undeclared': []}
    manifest = {'schema_version': '1.0', 'closure_id': 'allow-fresh-tier1-registered-safety-r1',
                'status': 'FROZEN_NOT_EXECUTED', 'files': sorted(files.values(), key=lambda row: row['path']),
                'links': sorted(links.values(), key=lambda row: row['path']), 'trees': trees,
                'absent_paths': [str(HERE/'.mvn'), str(HERE/'private-home/.m2'),
                                 str(HERE/'private-home/.mavenrc')],
                'claims': claims, 'test_methods': sorted(methods), 'test_source_bindings': source_bindings,
                'execution': {'argv': argv, 'environment': environment, 'cwd': str(TARGET.parent),
                              'report_directory': str(TARGET/'surefire-reports'), 'timeout_seconds': 180,
                              'network': 'OFFLINE_MAVEN_NO_DEPENDENCY_FETCH', 'compilation': 'FORBIDDEN_DIRECT_GOAL_ONLY'},
                'verifier': {'id': 'V-REGISTERED-SUREFIRE-SAFETY', 'path': str(HERE/'verify_safety.py'),
                             'sha256': sha(HERE/'verify_safety.py'), 'exit_codes': {'0': 'VERIFIED', '1': 'BLOCKED', '2': 'INFRASTRUCTURE_FAILURE'}},
                'environment_identity': {'kernel': platform.uname()._asdict(), 'python': sys.version,
                                         'java_release': (JDK/'release').read_text()},
                'dependencies': dependencies,
                'builds': {'required': 0, 'executed': 0, 'departure': 'Parent-authorized immutable compiled-artifact rerun; rebuilding is forbidden. No source-to-bytecode or clean-build claim.'},
                'determinism': {'required': 'Exact frozen method/status set and immutable input hashes',
                                'allowed_nondeterminism': ['JUnit time attributes', 'wall clock timestamps', 'PID', 'temp paths', 'generated UUIDs', 'test stdout elapsed nanoseconds'],
                                'repeated_build_reproducibility': 'OUT_OF_SCOPE'},
                'closure_boundary': {'verified_surface': ['Exact 12 finite test claims with 36 exact JUnit methods', 'Original input root and before/after integrity', 'Zero errors/failures/skips and zero Maven exit'],
                                     'trusted_surface': [item['id'] for item in dependencies['trusted']],
                                     'excluded_surface': ['Universal correctness', 'Lean/runtime or source/bytecode semantic correspondence', 'New clean builds', 'P1 cleanup matrix', 'Whole-response comparison', 'HTTP latency or target host acceptance', 'F1 selection', 'Actual JVM generated stdout at 1MiB boundary', 'Host SIGKILL/process-tree/cgroup guarantees'],
                                     'interpretation': 'VERIFIED applies only to the frozen finite runtime test surface under the explicit TCB; active profile remains DEFAULT.'}}
    import hashlib
    manifest['input_root_sha256'] = hashlib.sha256(packed(manifest)).hexdigest()
    write_new(HERE/'manifest.json', manifest)
    print(json.dumps({'status': manifest['status'], 'input_root_sha256': manifest['input_root_sha256'],
                      'claims': len(claims), 'test_methods': len(methods), 'files': len(files)}))


if __name__ == '__main__':
    main()
