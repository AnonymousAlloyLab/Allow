#!/usr/bin/env python3
"""Run registered storage-shaped quota/deadline cases on a separate fresh copied cluster."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from probe_runtime import control, environment, ready, run_cli, save, snapshot


def binding(root, name, config):
    """Bind one result to the exact copied source, driver and generated fixture hashes."""
    manifest = json.loads((root/'.gate/manifest.json').read_text())
    encoded = json.dumps(config, sort_keys=True, separators=(',', ':')).encode()
    return {'claim_id': 'CC29', 'subcase': name, 'run_id': manifest['run_id'],
            'input_root_sha256': manifest['input_root_sha256'], 'verifier_id': 'CC29-QUOTA-PROBE',
            'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'fixture_sha256': hashlib.sha256(encoded).hexdigest(), 'status': 'BLOCK'}


def expected(config, ids):
    """Construct the complete expected private context; preserve all original artifact bytes/fields."""
    return {'documentId': config['document'], 'baseRevision': 0, 'headObserved': 4095,
            'artifact': config['artifact'], 'ownedIdInventory': config['expected_inventory'] if ids else {}}


def valid_case(root, config, name, directory, empty=False, reference=False):
    """Require full output, actual backend absence, successful cleanup and exact durable invariance."""
    before = snapshot()
    record = binding(root, name, config)
    ids = [] if empty else config['wanted']
    observed = run_cli(root, config, ids, 'normal' if reference else 'quota', directory)
    nonce, output = observed.pop('nonce'), observed.pop('outcome')
    record.update(observed=observed, durable_unchanged=snapshot() == before,
                  exact_envelope=output == {'protocol': 1, 'requestId': nonce, 'status': 'OK', 'data': expected(config, ids)})
    clean = any(event['phase'] == 'CLEAN' and not event['failed'] and event['successPermitted'] for event in observed['events'])
    passed = record['exact_envelope'] and observed['exit_code'] == 0 and observed['stderr_empty']
    passed = passed and observed['backend_absent'] and observed['absence_was_exact_bound_identity'] and clean
    passed = passed and record['durable_unchanged'] and observed['elapsed_ms'] < 3000
    if not reference:
        stats = json.loads((directory/'quota-telemetry.json').read_text())
        record['telemetry'] = {key: value for key, value in stats.items() if key != 'row_sha256'}
        passed = passed and stats['rlimit_as'] == [2147483648, 2147483648] and stats['rlimit_cpu'] == [20, 20]
        memory = stats['final_memory']
        passed = passed and 0 < memory['VmHWM_bytes'] <= memory['VmPeak_bytes'] <= 2147483648
        if empty:
            passed = passed and stats['history_select_count'] == stats['rows_iterated'] == 0
        else:
            passed = passed and stats['history_select_count'] == 1 and stats['rows_iterated'] == stats['raw_rows_buffered'] == 4096
            passed = passed and stats['decoded_content_bytes'] == config['artifact_bytes']
            passed = passed and stats['raw_column_format'] == 0 and stats['raw_column_bytes'] == 2*config['artifact_bytes']+8192
            passed = passed and stats['row_multiset_sha256'] == config['row_multiset_sha256']
    record['status'] = 'PASS' if passed else 'BLOCK'
    save(directory/'case.json', record)
    return record


def conflict_case(root, config, directory):
    """Require actual earlier/later conflict iteration and no success, not assumed heap ordering."""
    from quota_fixture import add_late_conflict
    changed = add_late_conflict(config)
    before = snapshot()
    record = binding(root, 'late-conflict', changed)
    observed = run_cli(root, changed, changed['wanted'], 'quota', directory)
    output = observed.pop('outcome')
    observed.pop('nonce')
    stats = json.loads((directory/'quota-telemetry.json').read_text())
    positions = stats['focus_row_indexes']
    state = control(root)
    record.update(observed=observed, durable_unchanged=snapshot() == before,
                  context_status_after=state, focus_positions=positions,
                  rows_iterated=stats['rows_iterated'], no_success=not output or output.get('status') != 'OK')
    passed = record['no_success'] and len(positions) >= 2 and positions[0] < positions[-1]
    if passed:
        passed = stats['row_sha256'][positions[0]] == changed['expected_matching_row_sha256']
        passed = passed and stats['row_sha256'][positions[-1]] == changed['expected_conflict_row_sha256']
    passed = passed and (observed['backend_absent'] or state.get('contextOccupied') is True) and record['durable_unchanged']
    record['status'] = 'PASS' if passed else 'BLOCK'
    save(directory/'case.json', record)
    return record


def main():
    """Provision one exact maximum workload, then stop after the first failed registered predicate."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument('--output', type=Path)
    outputs.add_argument('--setup-output', type=Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    from allow_retrieval.common import ROOT as installed_root
    from allow_documents import identity, migration
    from quota_fixture import setup_fixture
    if installed_root != root or root == Path('/home/augustus/Allow'):
        raise RuntimeError('copied_runtime_required')
    if arguments.setup_output:
        config, counts = setup_fixture()
        save(arguments.setup_output, {'config': config, 'counts': counts})
        return
    cases = []
    report = {'schema_version': '1.0', 'status': 'INFRASTRUCTURE_FAILURE', 'cases': cases}
    try:
        ready(root)
        report['environment'] = environment(root)
        migration.migrate()
        identity.provision()
        from experiment import private_command
        setup = arguments.output.parent/'fixture-setup-private.json'
        command = [str(root/'.tools/retrieval-venv/bin/python'), str(Path(__file__)),
                   '--root', str(root), '--setup-output', str(setup)]
        private_command(command, root, arguments.output.parent/'fixture-setup-private.log', 600)
        prepared = json.loads(setup.read_text())
        config, counts = prepared['config'], prepared['counts']
        report['fixture'] = counts
        save(arguments.output.parent/'fixture-private.json', config)
        save(arguments.output.parent/'fixture-counts.json', counts)
        for name in ('empty-0', 'empty-1', 'empty-2', 'full-0', 'full-1', 'full-2', 'reference-full'):
            ready(root)
            case = valid_case(root, config, name, arguments.output.parent/name,
                              empty=name.startswith('empty'), reference=name == 'reference-full')
            cases.append(case)
            if case['status'] != 'PASS':
                break
        if len(cases) == 7 and all(case['status'] == 'PASS' for case in cases):
            cases.append(conflict_case(root, config, arguments.output.parent/'late-conflict'))
        report['finite_subcases_passed'] = len(cases) == 8 and all(case['status'] == 'PASS' for case in cases)
        report['status'] = 'BLOCKED'
        report['blocking_reasons'] = ['Full33-case runtime gate and two implementation builds are outside this finite quota probe.']
    except BaseException as error:
        report['failure_class'] = type(error).__name__
        raise
    finally:
        report['boundary'] = 'Storage-shaped local deadline feasibility; no4096Alloyadmissions, latencypercentiles, whole-stack budget or production-target acceptance claim.'
        save(arguments.output, report)


if __name__ == '__main__':
    main()
