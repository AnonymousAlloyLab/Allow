#!/usr/bin/env python3
"""Register finite W0/W1 semantics, retaining the declared whole190 equivalence block."""
import argparse
import json
from pathlib import Path
import sys
import time

import controller
import installation
import probe_results
import scope_launch
import semantic_plan
import semantic_results as results
from harness_common import HERE, digest, read_private, record, root_hash, write_private

COMMON = ('files', 'tooling', 'java', 'python_bytecode', 'source_ready', 'approval_anchors',
          'contract_sha256', 'experiment_sha256', 'launch_lane', 'build_identity')


def same_inputs(left, right):
    """Require identical executable, tool, policy, source and gate bytes across finite routes."""
    for key in COMMON:
        results.require(results.identical(left[key], right[key]), 'semantic_common_input_changed_'+key)


def ownership_prerequisite(path, manifest):
    """Mechanically connect the complete registered ownership run to these exact copied inputs."""
    prior = read_private(path/'manifest.json')
    same_inputs(prior, manifest)
    root = installation.verify(prior, fresh=False)
    frozen = controller.registration(path, prior)
    report = read_private(path/'report.json')
    results.require(frozen['operation'] == 'probe' and report['status'] == 'PASS'
                    and report['input_root_sha256'] == frozen['input_root_sha256']
                    and report['installation_root'] == prior['input_root_sha256']
                    and report['cleanup']['status'] == 'PASS' and report['launcher_reaped'] is True
                    and report['post_input_identity'] == 'PASS', 'semantic_ownership_prerequisite')
    checked = probe_results.verify(root, prior)
    results.require(checked == report['result'], 'semantic_ownership_receipts_changed')
    return [record(path/name) for name in ('manifest.json', 'preflight-registration.json', 'report.json')]


def freeze_variant(run, manifest, suite, programs, variant):
    """Freeze the route argument and shared verifier list before a private scope can launch."""
    root = Path(manifest['copied_root'])
    plan = read_private(root/'.gate/semantic-fixtures.json')
    value = {'schema': 1, 'classification': 'DIAGNOSTIC', 'operation': 'semantic', 'variant': variant,
             'installation_manifest': record(run/'manifest.json'), 'installation_root': manifest['input_root_sha256'],
             'claims': read_private(root/'.gate/runtime-claims.json'), 'case_ids': [r['name'] for r in plan['fixtures']],
             'verifier': record(Path(__file__)), 'programs': programs, 'suite': record(suite/'registration.json'),
             'benchmark_authorized': False, 'target_host_acceptance': 'OPEN'}
    value['input_root_sha256'] = root_hash(value)
    write_private(run/'preflight-registration.json', value)


def freeze(args):
    """Bind two unused copies, the exact prior ownership gate, and all finite comparison predicates."""
    suite = args.suite.absolute()
    results.require(suite.parent.resolve() == HERE/'runs' and not suite.exists(), 'semantic_new_suite_required')
    runs = {variant: controller.run_path(getattr(args, variant.lower())) for variant in ('W0', 'W1')}
    manifests = {variant: read_private(run/'manifest.json') for variant, run in runs.items()}
    for variant, manifest in manifests.items():
        root = installation.verify(manifest)
        semantic_plan.verify(root/'.gate')
        results.require((root/'.gate/probe-classes/dev/allow/backend/WarmSemanticProbeMain.class').is_file(), 'semantic_probe_missing')
        results.require(not (runs[variant]/'preflight-registration.json').exists(), 'semantic_already_registered')
    same_inputs(manifests['W0'], manifests['W1'])
    prereq = ownership_prerequisite(controller.run_path(args.ownership), manifests['W0'])
    programs = [record(path) for path in sorted(HERE.glob('*.py'))]
    for manifest in manifests.values():
        for row in programs:
            results.require(digest(Path(manifest['copied_root'])/'.gate'/Path(row['path']).name) == row['sha256'], 'semantic_stale_copied_program')
    value = suite_value(manifests, runs, programs, prereq)
    suite.mkdir(mode=0o700)
    write_private(suite/'registration.json', value)
    for variant in ('W0', 'W1'):
        freeze_variant(runs[variant], manifests[variant], suite, programs, variant)
    return {'status': 'FROZEN_NOT_EXECUTED', 'input_root_sha256': value['input_root_sha256'], 'suite': str(suite)}


def suite_value(manifests, runs, programs, prereq):
    """Make explicit the finite tested surface and boundaries before observing outputs."""
    value = {'schema': 1, 'classification': 'FINITE_SEMANTIC_DIAGNOSTIC', 'programs': programs,
             'ownership_prerequisite': prereq, 'order': ['W0', 'W1'], 'deadline_seconds_per_variant': 610,
             'variants': {v: {'manifest': record(runs[v]/'manifest.json'), 'root': manifests[v]['input_root_sha256']}
                          for v in ('W0', 'W1')}, 'fixtures': record(HERE/'semantic-fixtures.json'),
             'expected_cases': 190, 'expected_comparable': 189, 'expected_not_comparable': ['context-invalid-policyVersion'],
             'context_boundary': results.CONTEXT, 'selected_runtime_route': 'OPEN', 'sql_route': 'OPEN',
             'response_capture': {'W1_VALIDATE': 'RESERIALIZED_COMPLETE_POOL_RESPONSE', 'other': 'ACTUAL_STDOUT_FRAME'},
             'pass_predicate': '190 exact expected case outcomes;187 full response pairs+2 matching input rejection pairs;all cleanup/input/resource checks',
             'whole190_equivalence': 'BLOCKED even if finite checks pass: one preregistered domain gap',
             'tcb': ['Linux cgroup2/procfs/systemd/AppArmor', 'pinned JDK/Python/helper and gate Java observer',
                     'production lifecycle terminal receipts; independently parsed, not an OS refinement proof'],
             'benchmark_authorized': False, 'promotion_authorized': False}
    value['input_root_sha256'] = root_hash(value)
    return value


def registered(suite):
    """Recheck every immutable registration artifact and derive run paths from exact pointers."""
    suite = controller.run_path(suite)
    value = read_private(suite/'registration.json')
    results.require(root_hash(value) == value['input_root_sha256'] and value['benchmark_authorized'] is False
                    and value['promotion_authorized'] is False, 'semantic_registration_root')
    rows = [*value['programs'], *value['ownership_prerequisite'], value['fixtures']]
    rows += [row['manifest'] for row in value['variants'].values()]
    for row in rows:
        results.require(record(Path(row['path'])) == row, 'semantic_registered_artifact_changed')
    for variant, row in value['variants'].items():
        run = Path(row['manifest']['path']).parent
        manifest = read_private(run/'manifest.json')
        frozen = controller.registration(run, manifest)
        results.require(manifest['input_root_sha256'] == row['root'] and frozen['variant'] == variant
                        and frozen['suite'] == record(suite/'registration.json'), 'semantic_variant_registration')
    return suite, value


def wait_complete(root, manifest, variant, known, snapshots, child, seconds):
    """Observe aggregate containment until the fixed deadline without inspecting partial percentiles."""
    deadline = time.monotonic() + seconds
    while not (root/'.gate/evidence/semantic-complete.json').exists():
        controller.collect(manifest, known, snapshots)
        if child.poll() is not None or time.monotonic() >= deadline:
            raise ValueError('semantic_owner_exit_or_deadline')
        time.sleep(.25)
    controller.collect(manifest, known, snapshots)
    return results.verify_variant(root, manifest, variant)


def execute(args):
    """Execute one registered variant once, preserving every incomplete attempt and cleanup result."""
    suite, frozen = registered(args.suite)
    run = Path(frozen['variants'][args.variant]['manifest']['path']).parent
    prior = None
    if args.variant == 'W1':
        prior = Path(frozen['variants']['W0']['manifest']['path']).parent/'report.json'
        results.require(read_private(prior)['status'] == 'PASS', 'semantic_prior_variant_failed')
    manifest = read_private(run/'manifest.json')
    root = installation.verify(manifest)
    variant_registration = controller.registration(run, manifest)
    write_private(run/'execution-started.json', {'suite': record(suite/'registration.json'), 'variant': args.variant,
                  'prior_variant': record(prior) if prior else None})
    write_private(root/'.gate/evidence/semantic-launch.json', {'variant': args.variant,
                  'installation_root': manifest['input_root_sha256'], 'suite_root': frozen['input_root_sha256']})
    report = {'status': 'BLOCKED', 'classification': 'DIAGNOSTIC', 'snapshots': [], 'variant': args.variant,
              'input_root_sha256': variant_registration['input_root_sha256'], 'installation_root': manifest['input_root_sha256'],
              'benchmark_executed': False, 'target_host_acceptance': 'OPEN', 'registered_claims': variant_registration['claims']}
    state, child, known = None, None, {}
    try:
        state, child = scope_launch.launch(manifest, sys.executable, ['-B', root/'.gate/semantic_owner.py'], 660)
        report['result'] = wait_complete(root, manifest, args.variant, known, report['snapshots'], child, frozen['deadline_seconds_per_variant'])
        report['checks_passed'] = report['result']['status'] == 'PASS'
    except Exception as error:
        report['failure_class'], report['blocking_reason'] = type(error).__name__, str(error) if isinstance(error, (ValueError, AssertionError)) else 'semantic_operation_failed'
    finally:
        controller.finish(run, root, manifest, state, child, known, report)
    return {'status': report['status'], 'variant': args.variant, 'report': str(run/'report.json')}


def aggregate(rows, fixtures):
    """An explicit domain gap can pass its finite predicate but never the whole190 equality gate."""
    results.require(len(rows) == len(fixtures) == 190 and [r['id'] for r in rows] == [f['name'] for f in fixtures],
                    'semantic_summary_exact_case_set')
    gaps = [r['id'] for r in rows if r['status'] == 'NOT_COMPARABLE']
    good = all(r['status'] in {'PASS', 'NOT_COMPARABLE'} for r in rows)
    good = good and gaps == ['context-invalid-policyVersion'] and sum(r['status'] == 'PASS' for r in rows) == 189
    for row, item in zip(rows, fixtures):
        if item['comparison'] == 'NOT_COMPARABLE':
            good = good and row['status'] == 'NOT_COMPARABLE'
        elif item.get('expectedProbeReject'):
            good = good and row.get('comparison') == 'EXPLICIT_INPUT_LIMIT_REJECTION'
        else:
            good = good and row.get('full_response_equal') is True
    return {'status': 'BLOCKED', 'finite_expected_checks': 'PASS' if good else 'BLOCKED',
            'classification': 'TESTED_FINITE_SURFACE_ONLY', 'whole190_pairwise_equivalence': 'BLOCKED',
            'expected': 190, 'comparable_passed': sum(r['status'] == 'PASS' for r in rows),
            'full_response_pairs_passed': sum(r['status'] == 'PASS' and r.get('full_response_equal') is True for r in rows),
            'matching_input_rejections': sum(r['status'] == 'PASS' and r.get('comparison') == 'EXPLICIT_INPUT_LIMIT_REJECTION' for r in rows),
            'not_comparable': gaps, 'blocking_reasons': ['PREREGISTERED_BLANK_POLICY_DOMAIN_GAP'] if good else ['FINITE_CASE_FAILURE'],
            'context_boundary': results.CONTEXT, 'selected_runtime_route': 'OPEN', 'sql_route': 'OPEN',
            'performance_evidence': False, 'promotion_authorized': False, 'cases': rows}


def compare_variant_inputs(suite, frozen):
    """Recheck used roots and complete variant evidence before comparing any result."""
    checked = {}
    for variant in ('W0', 'W1'):
        run = Path(frozen['variants'][variant]['manifest']['path']).parent
        manifest = read_private(run/'manifest.json')
        root = installation.verify(manifest, fresh=False)
        report = read_private(run/'report.json')
        registration = controller.registration(run, manifest)
        results.require(report['status'] == 'PASS' and report['input_root_sha256'] == registration['input_root_sha256']
                        and report['installation_root'] == manifest['input_root_sha256'] and report['cleanup']['status'] == 'PASS'
                        and report['launcher_reaped'] is True and report['post_input_identity'] == 'PASS', 'semantic_variant_final_gate')
        value = results.verify_variant(root, manifest, variant)
        results.require(value == report['result'], 'semantic_variant_evidence_changed')
        checked[variant] = (root, manifest, value, record(run/'report.json'))
    same_inputs(checked['W0'][1], checked['W1'][1])
    start = read_private(Path(frozen['variants']['W1']['manifest']['path']).parent/'execution-started.json')
    results.require(start['prior_variant'] == checked['W0'][3], 'semantic_prior_report_changed')
    return checked


def compare_all(args):
    """Evaluate all pairs once and retain any mismatch without truncating the finite report."""
    suite, frozen = registered(args.suite)
    registration_pointer = record(suite/'registration.json')
    checked = compare_variant_inputs(suite, frozen)
    plan = read_private(HERE/'semantic-fixtures.json')
    rows = []
    for index, item in enumerate(plan['fixtures']):
        values = []
        try:
            frame = results.input_frame(checked['W0'][0], item)
            for variant in ('W0', 'W1'):
                root, manifest, verified, _ = checked[variant]
                raw = results.private_result(root, verified['cases'][index]['record'])
                values.append(results.response(raw, item, frame, variant, manifest['build_identity']['value']))
            outcome = results.compare_case(item, frame, *values)
        except Exception as error:
            outcome = {'id': item['name'], 'status': 'BLOCKED', 'failure_class': type(error).__name__,
                       'reason': str(error) if isinstance(error, (AssertionError, ValueError)) else 'comparison_failed'}
        rows.append(outcome)
    report = aggregate(rows, plan['fixtures'])
    try:
        _, terminal = registered(suite)
        results.require(terminal == frozen, 'semantic_registration_changed_during_comparison')
        results.require(compare_variant_inputs(suite, frozen) == checked, 'semantic_evidence_changed_during_comparison')
        prior = Path(frozen['ownership_prerequisite'][0]['path']).parent
        results.require(ownership_prerequisite(prior, checked['W0'][1]) == frozen['ownership_prerequisite'],
                        'semantic_prerequisite_changed_during_comparison')
        report['terminal_input_and_evidence_recheck'] = 'PASS'
    except Exception as error:
        report.update(finite_expected_checks='BLOCKED', terminal_input_and_evidence_recheck='BLOCKED',
                      blocking_reasons=['TERMINAL_INPUT_OR_EVIDENCE_CHANGED'], failure_class=type(error).__name__)
    report.update(input_root_sha256=frozen['input_root_sha256'], variants={v: checked[v][3] for v in checked},
                  registration=registration_pointer)
    write_private(suite/'report.json', report)
    return {k: report[k] for k in ('status', 'finite_expected_checks', 'comparable_passed', 'not_comparable', 'input_root_sha256')}


def main():
    """Expose separate immutable freeze, ordered variant execution and finite comparison steps."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze_parser = sub.add_parser('freeze')
    for name in ('suite', 'w0', 'w1', 'ownership'):
        freeze_parser.add_argument('--'+name, type=Path, required=True)
    execute_parser = sub.add_parser('execute')
    execute_parser.add_argument('--suite', type=Path, required=True)
    execute_parser.add_argument('--variant', choices=('W0', 'W1'), required=True)
    comparison = sub.add_parser('compare')
    comparison.add_argument('--suite', type=Path, required=True)
    args = parser.parse_args()
    result = {'freeze': freeze, 'execute': execute, 'compare': compare_all}[args.command](args)
    print(json.dumps(result))
    return 0 if result.get('status') in {'PASS', 'FROZEN_NOT_EXECUTED'} or result.get('finite_expected_checks') == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
