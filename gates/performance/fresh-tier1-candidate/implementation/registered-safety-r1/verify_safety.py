"""Execute only the registered compiled safety suite and check its finite evidence."""
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent


def packed(value):
    """Encode canonical JSON bytes for input and result identity."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def sha(path):
    """Hash every byte of a regular input without truncation."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1048576):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path):
    """Record content, size and permissions for an already resolved regular file."""
    path = Path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise AssertionError('NONREGULAR_INPUT')
    return {'path': str(path), 'sha256': sha(path), 'size': info.st_size,
            'mode': stat.S_IMODE(info.st_mode)}


def write_new(path, value):
    """Preserve generated evidence without replacing an earlier run record."""
    with Path(path).open('xb') as stream:
        stream.write(packed(value) + b'\n')
    Path(path).chmod(0o600)


def require(condition, code):
    """Treat any unresolved registered predicate as blocking."""
    if not condition:
        raise AssertionError(code)


def members(path):
    """List executable input membership without following directory symlinks."""
    return sorted(str(item.relative_to(path)) for item in Path(path).rglob('*')
                  if item.is_file() or item.is_symlink())


def verify_inputs(manifest, expected_manifest_sha):
    """Recheck the original root, every file, links and tree membership."""
    require(sha(HERE/'manifest.json') == expected_manifest_sha, 'REGISTRATION_MUTATION')
    root = dict(manifest)
    claimed = root.pop('input_root_sha256')
    require(hashlib.sha256(packed(root)).hexdigest() == claimed, 'ROOT_MISMATCH')
    for row in manifest['files']:
        require(file_record(row['path']) == row, 'INPUT_MUTATION:' + row['path'])
    for row in manifest['links']:
        path = Path(row['path'])
        require(path.is_symlink() and os.readlink(path) == row['link_text']
                and str(path.resolve()) == row['resolved'], 'LINK_MUTATION:' + str(path))
    for tree in manifest['trees']:
        require(members(Path(tree['path'])) == tree['members'], 'TREE_MUTATION:' + tree['path'])
    for path in manifest['absent_paths']:
        require(not Path(path).exists() and not Path(path).is_symlink(), 'UNDECLARED_CONFIGURATION')


def test_results(directory, expected):
    """Require exactly the frozen tests once each, with zero failures/errors/skips."""
    paths = sorted(directory.glob('TEST-*.xml'))
    expected_classes = {item.split('#')[0] for item in expected}
    require({path.name for path in paths} == {'TEST-' + name + '.xml' for name in expected_classes},
            'TEST_SUITE_SET_MISMATCH')
    observed, reports = [], []
    for path in paths:
        tree = ET.parse(path).getroot()
        require(tree.tag == 'testsuite' and tree.attrib['name'] in expected_classes, 'XML_SUITE_IDENTITY')
        cases = tree.findall('testcase')
        require(int(tree.attrib['tests']) == len(cases), 'XML_TEST_COUNT_MISMATCH')
        require(all(tree.attrib[key] == '0' for key in ('failures', 'errors', 'skipped')), 'XML_NONPASS_COUNT')
        for case in cases:
            name = case.attrib['classname'] + '#' + case.attrib['name']
            require(case.attrib['classname'] == tree.attrib['name'], 'XML_CASE_CLASS_MISMATCH')
            require(not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')),
                    'XML_NONPASS_TEST:' + name)
            observed.append(name)
        reports.append(file_record(path))
    require(len(observed) == len(set(observed)) and sorted(observed) == sorted(expected),
            'EXACT_TEST_METHOD_SET_MISMATCH')
    require(not list(directory.glob('*.dump*')), 'SUREFIRE_DUMP_PRESENT')
    return {'tests': sorted(observed), 'xml_reports': reports,
            'failures': 0, 'errors': 0, 'skipped': 0, 'exact_method_inventory': True}


def preserve_reports(directory):
    """Copy generated XML and companion logs into this registration's private evidence."""
    destination = HERE/'surefire-reports'
    require(directory.is_dir() and not directory.is_symlink(), 'SUREFIRE_REPORTS_MISSING')
    require(all(path.is_file() and not path.is_symlink() for path in directory.iterdir()),
            'NONREGULAR_SUREFIRE_OUTPUT')
    shutil.copytree(directory, destination)
    for path in destination.iterdir():
        require(sha(path) == sha(directory/path.name), 'SUREFIRE_REPORT_COPY_MISMATCH')
        path.chmod(0o600)
    return destination


def execute(manifest):
    """Run one frozen offline Surefire invocation without compilation or build phases."""
    specification = manifest['execution']
    report_dir = Path(specification['report_directory'])
    require(not report_dir.exists(), 'STALE_SUREFIRE_REPORTS')
    require(not (HERE/'execution.json').exists(), 'RUN_ALREADY_EXECUTED')
    started = time.time_ns()
    with (HERE/'maven.stdout.log').open('xb') as stdout, (HERE/'maven.stderr.log').open('xb') as stderr:
        process = subprocess.Popen(specification['argv'], cwd=specification['cwd'],
                                   env=specification['environment'], stdout=stdout, stderr=stderr,
                                   start_new_session=True)
        timed_out = False
        try:
            exit_code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            exit_code = process.wait(timeout=10)
    result = {'argv': specification['argv'], 'environment': specification['environment'],
              'cwd': specification['cwd'], 'pid': process.pid, 'exit_code': exit_code, 'timed_out': timed_out,
              'started_unix_ns': started, 'ended_unix_ns': time.time_ns(),
              'stdout': file_record(HERE/'maven.stdout.log'), 'stderr': file_record(HERE/'maven.stderr.log')}
    write_new(HERE/'execution.json', result)
    return result


def report(manifest, state, raw, execution, reasons):
    """Generate claim-bound evidence with finite test and trust boundaries explicit."""
    registry = manifest['verifier']
    count = 0
    for claim in manifest['claims']:
        passed = state == 'VERIFIED' and set(claim['tests']).issubset(raw.get('tests', []))
        evidence = {'closure_id': manifest['closure_id'], 'claim_id': claim['id'],
                    'input_root_sha256': manifest['input_root_sha256'],
                    'verifier_id': registry['id'], 'verifier_sha256': registry['sha256'],
                    'execution_environment': manifest['environment_identity'],
                    'raw_result': {'tests': claim['tests'], 'all_present_and_passed': passed,
                                   'suite': raw, 'execution_exit_code': execution.get('exit_code')},
                    'exit_code': 0 if passed else 1, 'status': 'PASS' if passed else 'BLOCK'}
        write_new(HERE/(claim['id'] + '.json'), evidence)
        count += int(passed)
    result = {'schema_version': '1.0', 'closure_id': manifest['closure_id'], 'status': state,
              'input_root_sha256': manifest['input_root_sha256'], 'verifier': registry,
              'claims': {'total': len(manifest['claims']), 'passed': count,
                         'blocked': len(manifest['claims']) - count, 'unresolved': 0},
              'test_methods': len(raw.get('tests', [])), 'raw_result': raw,
              'builds': manifest['builds'], 'determinism': manifest['determinism'],
              'correspondence': {'required': 0, 'classification': 'OUT_OF_SCOPE_SOURCE_TO_BYTECODE_OR_LEAN'},
              'witnesses': {'required': 0, 'classification': 'TEST_INSTANCES_ONLY'},
              'provenance': {'public_claims': 12, 'fully_bound': 12, 'orphan_claims': 0,
                             'bindings': [{'claim_id': claim['id'], 'evidence': claim['id'] + '.json',
                                           'verifier': registry['id'], 'input_root_sha256': manifest['input_root_sha256']}
                                          for claim in manifest['claims']]},
              'execution_record': file_record(HERE/'execution.json') if (HERE/'execution.json').exists() else None,
              'dependencies': manifest['dependencies'], 'closure_boundary': manifest['closure_boundary'],
              'blocking_reasons': reasons if state == 'BLOCKED' else [],
              'infrastructure_errors': reasons if state == 'INFRASTRUCTURE_FAILURE' else [],
              'selection_evidence': False, 'active_profile': 'DEFAULT'}
    write_new(HERE/'report.json', result)
    print(json.dumps({'status': state, 'claims': result['claims'], 'test_methods': result['test_methods'],
                      'input_root_sha256': manifest['input_root_sha256']}))


def main():
    """Evaluate every required finite predicate and preserve all failure evidence."""
    manifest = json.loads((HERE/'manifest.json').read_bytes())
    original_sha = sha(HERE/'manifest.json')
    state, raw, execution, reasons = 'VERIFIED', {}, {}, []
    try:
        verify_inputs(manifest, original_sha)
        require(sha(__file__) == manifest['verifier']['sha256'], 'VERIFIER_MISMATCH')
        write_new(HERE/'before.json', {'input_root_sha256': manifest['input_root_sha256'],
                                     'manifest_sha256': original_sha, 'inputs_verified': True})
        execution = execute(manifest)
        require(not execution['timed_out'], 'SUREFIRE_TIMEOUT_CLEANUP_UNCONFIRMED')
        preserved = preserve_reports(Path(manifest['execution']['report_directory']))
        raw = test_results(preserved, manifest['test_methods'])
        require(execution['exit_code'] == 0, 'SUREFIRE_NONZERO_EXIT')
    except AssertionError as failure:
        state, reasons = 'BLOCKED', [str(failure)]
    except Exception as failure:
        state, reasons = 'INFRASTRUCTURE_FAILURE', [type(failure).__name__ + ':' + str(failure)]
    try:
        verify_inputs(manifest, original_sha)
        write_new(HERE/'after.json', {'input_root_sha256': manifest['input_root_sha256'],
                                    'manifest_sha256': original_sha, 'inputs_verified': True})
    except Exception as failure:
        state, reasons = 'BLOCKED', reasons + ['FINAL_INPUT_INTEGRITY:' + str(failure)]
    report(manifest, state, raw, execution, reasons)
    return 0 if state == 'VERIFIED' else 1 if state == 'BLOCKED' else 2


if __name__ == '__main__':
    sys.exit(main())
