#!/usr/bin/env python3
"""Freeze and run the explicitly authorized, non-promoting component diagnostic."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time

import controller
import installation
import latency_results as results
import scope_launch
import semantic_runner
from harness_common import HERE, ROOT, digest, read_private, record, root_hash, write_private

DIAGNOSTIC = HERE.parent/'latency-diagnostic'
CONTRACT = '626a50b7afa537c906b38219c8646ca1043d59dbf38187820ad8b56a9f1253f2'
TIMED = [('pair1-fresh', 'FRESH', 20, 100), ('pair1-pool', 'POOL_SERIAL', 20, 100),
         ('pair2-pool', 'POOL_SERIAL', 20, 100), ('pair2-fresh', 'FRESH', 20, 100),
         ('pair3-fresh', 'FRESH', 20, 100), ('pair3-pool', 'POOL_SERIAL', 20, 100),
         ('ready-conditioned', 'POOL_READY', 20, 100), ('empty-pool', 'POOL_EMPTY', 0, 20)]
PREFLIGHT = [('fixture-fresh', 'FRESH', 0, 1), ('fixture-pool', 'POOL_SERIAL', 0, 1)]


def require(condition, reason):
    """Reject unknown or changed diagnostic protocol without displaying private payloads."""
    if not condition:
        raise ValueError('latency_'+reason)


def schedule(mode):
    """Fix exact finite ordering and attempt populations independently of measured values."""
    require(mode in {'PREFLIGHT', 'MEASURED'}, 'mode')
    return PREFLIGHT if mode == 'PREFLIGHT' else TIMED


def approval_anchors():
    """Bind the exact six-seat supplement approval and corrected two-build Lean policy."""
    names = ['contract.json', 'council-disposition.json', 'policy-proof-report-r2.json',
             'WarmLatencyDiagnostic.lean', 'proof-inventory-commands-r2.lean', 'producer-plan-schema.json',
             'lean-clean-r2-1.json', 'lean-clean-r2-2.json', 'lean-axioms-r2-1.txt', 'lean-axioms-r2-2.txt']
    require(digest(DIAGNOSTIC/'contract.json') == CONTRACT, 'approved_contract_changed')
    council = json.loads((DIAGNOSTIC/'council-disposition.json').read_text())
    proof = json.loads((DIAGNOSTIC/'policy-proof-report-r2.json').read_text())
    require(council['status'] == 'APPROVED_FINITE_NON_PROMOTING_DIAGNOSTIC'
            and council['contract_sha256'] == CONTRACT, 'approval_disposition')
    seats = council['reviews']
    require(len(seats) == 6 and {r['seat'] for r in seats} == {'Terra1','Terra2','Sol1','Sol2','Astra1','Astra2'}, 'six_seats')
    require(all(r['decision'] == 'APPROVE_DIAGNOSTIC' and r['contract_sha256'] == CONTRACT
                and r['blocking_findings'] == [] for r in seats), 'six_approvals')
    require(digest(ROOT/council['policy_proof']['path']) == council['policy_proof']['sha256'], 'proof_pointer')
    require(proof['contract_sha256'] == CONTRACT and proof['clean_builds'] == 2
            and proof['all_builds_passed'] is True and proof['olean_deterministic'] is True
            and proof['axiom_inventories_identical'] is True and len(proof['theorems']) == 14, 'proof_r2')
    require(digest(DIAGNOSTIC/'WarmLatencyDiagnostic.lean') == proof['source_sha256'], 'proof_source')
    return [record(DIAGNOSTIC/name) for name in names]


def suite_path(path, new=False):
    """Keep diagnostic registrations separate from the original promotion experiment."""
    path = path.absolute()
    require(path.parent.resolve() == (DIAGNOSTIC/'runs').resolve(), 'suite_directory')
    if new:
        require(not path.exists(), 'new_suite_required')
    else:
        require(path.is_dir() and path.resolve() == path, 'registered_suite_required')
    return path


def plan_template(item, mode):
    """Register all Java arguments except kernel paths resolved by the trusted owner rule."""
    name, profile, warmups, measured = item
    return {'schema': 1, 'variantId': name, 'profile': profile, 'mode': mode,
            'warmups': warmups, 'measured': measured, 'contractSha256': CONTRACT,
            'fixtureSha256': digest(HERE/'latency-fixture.json')}



def diagnostic_claims(root, plan):
    """Namespace the authorized component obligations without changing original promotion claims."""
    claims = copy.deepcopy(read_private(root/'.gate/runtime-claims.json'))
    claims.update(namespace='ALLOW-WARM-LATENCY-DIAGNOSTIC-R1',
                  classification='FINITE_COMPONENT_DIAGNOSTIC_NOT_HTTP_ACCEPTANCE')
    for claim in claims['claims']:
        if claim['id'] == 'WP-H03':
            claim.update(kind='CHECKED', predicate='Exact registered warmup+measured attempt accounting, complete outputs, '
                         'timing and owned receipts pass latency_results.verify_variant',
                         plan=copy.deepcopy(plan), verifier='latency_results.verify_variant')
    claims['excluded'] = ['HTTP acceptance', 'production promotion or selection', 'SQL CLEAN validation',
                          'target4vCPU8GiB acceptance', 'full contract fault coverage', 'commercial release']
    return claims


def freeze_variant(run, manifest, suite, programs, plan):
    """Reuse the finite controller's cleanup registration, explicitly excluding HTTP acceptance."""
    root = Path(manifest['copied_root'])
    value = {'schema': 1, 'classification': 'DIAGNOSTIC', 'operation': 'latency', 'plan': plan,
             'installation_manifest': record(run/'manifest.json'), 'installation_root': manifest['input_root_sha256'],
             'claims': diagnostic_claims(root, plan), 'case_ids': [],
             'verifier': record(Path(__file__)), 'programs': programs, 'suite': record(suite/'registration.json'),
             'benchmark_authorized': False, 'component_diagnostic_authorized': True,
             'target_host_acceptance': 'OPEN'}
    value['input_root_sha256'] = root_hash(value)
    write_private(run/'preflight-registration.json', value)


def compatibility(path, manifest):
    """Bind a previously completed exact-input F/P compatibility result and its full fresh oracle."""
    suite, frozen = registered(path)
    require(frozen['mode'] == 'PREFLIGHT', 'compatibility_kind')
    value = read_private(suite/'report.json')
    require(value['status'] == 'PASS' and value['input_root_sha256'] == frozen['input_root_sha256'], 'compatibility_failed')
    first = read_private(Path(frozen['variants']['fixture-fresh']['manifest']['path']))
    semantic_runner.same_inputs(first, manifest)
    checked = check_completed(suite, frozen)
    require(value['variants'] == {name: row['report'] for name, row in checked.items()}, 'compatibility_reports_changed')
    fixture = read_private(HERE/'latency-fixture.json')
    fresh = results.extract_oracle(checked['fixture-fresh']['root']/'.gate/evidence')
    pool = results.response(read_private(checked['fixture-pool']['root']/'.gate/evidence/latency-java.json')['rows'][0])
    comparison = results.compare_preflight(fresh, pool, fixture)
    require(comparison == value['comparison'] and read_private(suite/'oracle.json') == fresh, 'compatibility_oracle_changed')
    return [record(suite/name) for name in ('registration.json', 'report.json', 'oracle.json')]


def freeze(args):
    """Freeze all independent scopes, counts and exact inputs before the first requested operation."""
    suite = suite_path(args.suite, new=True)
    supplied = json.loads(args.runs.read_text())
    items = schedule(args.mode)
    require(set(supplied) == {row[0] for row in items}, 'exact_variant_set')
    runs = {name: controller.run_path(Path(supplied[name])) for name, *_ in items}
    manifests = {name: read_private(run/'manifest.json') for name, run in runs.items()}
    require(len(set(runs.values())) == len(runs) and len({m['copied_root'] for m in manifests.values()}) == len(runs), 'distinct_scopes_required')
    programs = [record(path) for path in sorted(HERE.glob('*.py'))]
    common = next(iter(manifests.values()))
    for name, manifest in manifests.items():
        root = installation.verify(manifest)
        semantic_runner.same_inputs(common, manifest)
        require(not (runs[name]/'preflight-registration.json').exists(), 'unused_variant_required')
        require((root/'.gate/probe-classes/dev/allow/backend/WarmLatencyMain.class').is_file(), 'latency_main_missing')
        for row in programs:
            require(digest(root/'.gate'/Path(row['path']).name) == row['sha256'], 'copied_program_changed')
    prior = semantic_runner.ownership_prerequisite(controller.run_path(args.ownership), common)
    require(args.mode != 'MEASURED' or args.compatibility is not None, 'compatibility_required_before_timing')
    require(len(read_private(Path(prior[1]['path']))['case_ids']) == 11, 'eleven_case_ownership_required')
    compat = compatibility(args.compatibility, common) if args.mode == 'MEASURED' else []
    require(args.mode == 'MEASURED' or args.compatibility is None, 'unexpected_compatibility')
    value = {'schema': 1, 'classification': 'INSTRUMENTED_COMPONENT_DIAGNOSTIC_NOT_HTTP', 'mode': args.mode,
             'approval_anchors': approval_anchors(), 'ownership_prerequisite': prior, 'compatibility': compat,
             'programs': programs, 'order': [row[0] for row in items], 'deadline_seconds': 180,
             'variants': {name: {'manifest': record(runs[name]/'manifest.json'), 'root': manifests[name]['input_root_sha256'],
                                'plan': plan_template(item, args.mode)} for item in items for name in [item[0]]},
             'path_resolution': 'fixture=copied/.gate/latency-fixture.json;cgroupRoot=validated config root;cpuStat=cgroupRoot/cpu.stat',
             'fixtures': [record(HERE/name) for name in ('latency-fixture.json', 'latency-expected.json')],
             'total_requests': sum(row[2]+row[3] for row in items), 'promotion_authorized': False,
             'production_selection': 'DISABLED', 'sql_boundary': 'TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL'}
    value['input_root_sha256'] = root_hash(value)
    suite.mkdir(mode=0o700, parents=True)
    write_private(suite/'registration.json', value)
    for item in items:
        name = item[0]
        freeze_variant(runs[name], manifests[name], suite, programs, value['variants'][name]['plan'])
    return {'status': 'FROZEN_NOT_EXECUTED', 'suite': str(suite), 'input_root_sha256': value['input_root_sha256']}


def registered(path):
    """Reject mutated verifier, supplement, fixture, prerequisite and per-scope registration bytes."""
    suite = suite_path(path)
    value = read_private(suite/'registration.json')
    require(root_hash(value) == value['input_root_sha256'] and value['promotion_authorized'] is False, 'registration_root')
    require(value['order'] == [item[0] for item in schedule(value['mode'])], 'registered_order')
    require(set(value['variants']) == set(value['order']) and value['total_requests'] == sum(r[2]+r[3] for r in schedule(value['mode'])), 'registered_population')
    for item in schedule(value['mode']):
        require(value['variants'][item[0]]['plan'] == plan_template(item, value['mode']), 'registered_plan')
    rows = [*value['approval_anchors'], *value['ownership_prerequisite'], *value['compatibility'],
            *value['programs'], *value['fixtures'], *[v['manifest'] for v in value['variants'].values()]]
    for row in rows:
        require(record(Path(row['path'])) == row, 'registered_artifact_changed')
    for name in value['order']:
        item = value['variants'][name]
        run = Path(item['manifest']['path']).parent
        manifest = read_private(run/'manifest.json')
        frozen = controller.registration(run, manifest)
        require(manifest['input_root_sha256'] == item['root'] and frozen['suite'] == record(suite/'registration.json')
                and frozen['plan'] == item['plan'], 'variant_registration_changed')
    return suite, value


def concrete_inputs(root, manifest, template):
    """Check the runtime path substitutions and exact owner completion before inspecting outputs."""
    evidence = root/'.gate/evidence'
    done = read_private(evidence/'latency-complete.json')
    require(done['status'] == 'COMPLETE' and type(done['exit_code']) is int and done['exit_code'] == 0
            and done['probe_reaped'] is True, 'owner_incomplete')
    require(done['plan'] == record(evidence/'latency-plan.json') and done['java_report'] == record(evidence/'latency-java.json'), 'owner_receipt_changed')
    config = read_private(root/'.runtime/warm-pool/config.json')
    invocation = read_private(root/'.gate/unit-invocation.json')
    require(config['cgroupRoot'] == '/sys/fs/cgroup'+invocation['control_group'], 'actual_group_path')
    expected = dict(template, fixture=str(root/'.gate/latency-fixture.json'), cgroupRoot=config['cgroupRoot'],
                    cpuStat=config['cgroupRoot']+'/cpu.stat')
    plan = read_private(evidence/'latency-plan.json')
    require(plan == expected and digest(plan['fixture']) == plan['fixtureSha256'], 'concrete_plan_changed')
    fixture = read_private(plan['fixture'])
    return plan, fixture


def oracle_for(frozen):
    """Use only the full FRESH response bound by the completed fixture preflight."""
    if frozen['mode'] == 'MEASURED':
        return read_private(Path(frozen['compatibility'][2]['path']))
    return None


def verify_result(root, manifest, template, oracle):
    """Call the independently authored full-output/lifecycle/timing verifier after all samples."""
    plan, fixture = concrete_inputs(root, manifest, template)
    return results.verify_variant(root, root/'.gate/evidence', manifest, plan, fixture, oracle=oracle)


def wait_complete(root, manifest, known, snapshots, child):
    """Sample only containment during the series; never inspect partial latency statistics."""
    deadline = time.monotonic()+190
    while not (root/'.gate/evidence/latency-complete.json').exists():
        controller.collect(manifest, known, snapshots)
        if child.poll() is not None or time.monotonic() >= deadline:
            raise ValueError('latency_owner_exit_or_deadline')
        time.sleep(.25)
    controller.collect(manifest, known, snapshots)


def execute(args):
    """Run exactly one next registered variant once and preserve every failed attempt."""
    suite, frozen = registered(args.suite)
    require(args.variant in frozen['order'], 'unknown_variant')
    index = frozen['order'].index(args.variant)
    previous = check_completed(suite, frozen, frozen['order'][:index])
    require(not (suite/'report.json').exists(), 'suite_already_terminal')
    selected = frozen['variants'][args.variant]
    run = Path(selected['manifest']['path']).parent
    manifest = read_private(run/'manifest.json')
    root = installation.verify(manifest)
    registered_variant = controller.registration(run, manifest)
    write_private(run/'execution-started.json', {'suite': record(suite/'registration.json'), 'variant': args.variant,
                  'prior_reports': [row['report'] for row in previous.values()]})
    write_private(root/'.gate/evidence/latency-launch.json', {'plan': selected['plan'],
                  'installation_root': manifest['input_root_sha256'], 'suite_root': frozen['input_root_sha256']})
    report = {'status': 'BLOCKED', 'classification': 'DIAGNOSTIC', 'snapshots': [], 'variant': args.variant,
              'input_root_sha256': registered_variant['input_root_sha256'], 'installation_root': manifest['input_root_sha256'],
              'benchmark_executed': False, 'component_timing_executed': frozen['mode'] == 'MEASURED',
              'target_host_acceptance': 'OPEN', 'registered_claims': registered_variant['claims']}
    state, child, known = None, None, {}
    try:
        state, child = scope_launch.launch(manifest, sys.executable, ['-B', root/'.gate/latency_owner.py'], 240)
        wait_complete(root, manifest, known, report['snapshots'], child)
        report['result'] = verify_result(root, manifest, selected['plan'], oracle_for(frozen))
        report['checks_passed'] = report['result']['status'] == 'PASS'
    except Exception as error:
        report['failure_class'] = type(error).__name__
        report['blocking_reason'] = str(error) if isinstance(error, (ValueError, AssertionError)) else 'latency_operation_failed'
    finally:
        controller.finish(run, root, manifest, state, child, known, report)
    if report['status'] != 'PASS':
        failed_suite(suite, frozen, args.variant)
    return {'status': report['status'], 'variant': args.variant, 'report': str(run/'report.json')}


def check_completed(suite, frozen, names=None):
    """Replay full prior evidence and chained report pointers before admitting the next scope."""
    checked = {}
    for name in frozen['order'] if names is None else names:
        item = frozen['variants'][name]
        run = Path(item['manifest']['path']).parent
        manifest = read_private(run/'manifest.json')
        root = installation.verify(manifest, fresh=False)
        report = read_private(run/'report.json')
        registration = controller.registration(run, manifest)
        require(report['status'] == 'PASS' and report['input_root_sha256'] == registration['input_root_sha256']
                and report['installation_root'] == manifest['input_root_sha256'] and report['cleanup']['status'] == 'PASS'
                and report['launcher_reaped'] is True and report['post_input_identity'] == 'PASS', 'variant_final_gate')
        require(report['result'] == verify_result(root, manifest, item['plan'], oracle_for(frozen)), 'variant_evidence_changed')
        start = read_private(run/'execution-started.json')
        require(start['suite'] == record(suite/'registration.json') and start['variant'] == name
                and start['prior_reports'] == [row['report'] for row in checked.values()], 'prior_report_chain_changed')
        checked[name] = {'root': root, 'manifest': manifest, 'result': report['result'], 'report': record(run/'report.json')}
    return checked


def failed_suite(suite, frozen, failed):
    """Retain original failure and make all remaining scheduled variants explicitly unexecuted."""
    index = frozen['order'].index(failed)
    rows = {}
    for position, name in enumerate(frozen['order']):
        run = Path(frozen['variants'][name]['manifest']['path']).parent
        rows[name] = {'status': 'NOT_EXECUTED'} if position > index else {
            'status': read_private(run/'report.json')['status'], 'report': record(run/'report.json')}
    write_private(suite/'report.json', {'status': 'BLOCKED', 'input_root_sha256': frozen['input_root_sha256'],
                  'failed_variant': failed, 'variants': rows, 'performance_interpretation': 'INVALID',
                  'promotion_authorized': False, 'production_selection': 'DISABLED'})


def compare_checked(suite, frozen, pointer):
    """Recheck terminal inputs and produce either a fixture oracle or the finite diagnostic summary."""
    checked = check_completed(suite, frozen)
    value = {'status': 'PASS', 'input_root_sha256': frozen['input_root_sha256'], 'registration': pointer,
             'mode': frozen['mode'], 'variants': {name: row['report'] for name, row in checked.items()},
             'production_selection': 'DISABLED', 'promotion_authorized': False, 'http_acceptance': 'OPEN'}
    if frozen['mode'] == 'PREFLIGHT':
        fresh = results.extract_oracle(checked['fixture-fresh']['root']/'.gate/evidence')
        pool = results.response(read_private(checked['fixture-pool']['root']/'.gate/evidence/latency-java.json')['rows'][0])
        value['comparison'] = results.compare_preflight(fresh, pool, read_private(HERE/'latency-fixture.json'))
        require(value['comparison']['status'] == 'PASS', 'fixture_pair_failed')
        write_private(suite/'oracle.json', fresh)
        value['oracle'] = record(suite/'oracle.json')
    else:
        value['results'] = {name: row['result'] for name, row in checked.items()}
        value['pairs'] = {str(i): results.paired_metrics(checked[f'pair{i}-fresh']['result'],
                         checked[f'pair{i}-pool']['result']) for i in (1, 2, 3)}
        value['scope_resources'] = {name: read_private(Path(row['report']['path']))['cleanup']['terminal_resources']
                                    for name, row in checked.items()}
        require(sum(row['result']['attempts_checked'] for row in checked.values()) == 860, 'complete_860_accounting')
    try:
        require(registered(suite)[1] == frozen and check_completed(suite, frozen) == checked, 'terminal_evidence_changed')
        common = next(iter(checked.values()))['manifest']
        prior = Path(frozen['ownership_prerequisite'][0]['path']).parent
        require(semantic_runner.ownership_prerequisite(prior, common) == frozen['ownership_prerequisite'], 'terminal_prerequisite_changed')
        if frozen['mode'] == 'MEASURED':
            require(compatibility(Path(frozen['compatibility'][0]['path']).parent, common) == frozen['compatibility'], 'terminal_compatibility_changed')
        value['terminal_input_recheck'] = 'PASS'
    except Exception as error:
        value.update(status='BLOCKED', terminal_input_recheck='BLOCKED', failure_class=type(error).__name__)
    write_private(suite/'report.json', value)
    return {'status': value['status'], 'report': str(suite/'report.json')}



def compare(args):
    """Retain a terminal BLOCKED receipt even when replayed inputs or evidence disappear."""
    suite = suite_path(args.suite)
    pointer = record(suite/'registration.json')
    initial = read_private(suite/'registration.json')
    try:
        _, frozen = registered(suite)
        return compare_checked(suite, frozen, pointer)
    except Exception as error:
        value = {'status': 'BLOCKED', 'input_root_sha256': initial.get('input_root_sha256'),
                 'registration': pointer, 'performance_interpretation': 'INVALID',
                 'failure_class': type(error).__name__, 'promotion_authorized': False,
                 'production_selection': 'DISABLED', 'terminal_input_recheck': 'BLOCKED'}
        write_private(suite/'report.json', value)
        return {'status': 'BLOCKED', 'report': str(suite/'report.json')}


def main():
    """Separate registration, one ordered execution, and terminal comparison commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freezing = sub.add_parser('freeze')
    freezing.add_argument('--mode', choices=('PREFLIGHT', 'MEASURED'), required=True)
    for name in ('suite', 'runs', 'ownership'):
        freezing.add_argument('--'+name, type=Path, required=True)
    freezing.add_argument('--compatibility', type=Path)
    execution = sub.add_parser('execute')
    execution.add_argument('--suite', type=Path, required=True)
    execution.add_argument('--variant', required=True)
    comparison = sub.add_parser('compare')
    comparison.add_argument('--suite', type=Path, required=True)
    args = parser.parse_args()
    result = {'freeze': freeze, 'execute': execute, 'compare': compare}[args.command](args)
    print(json.dumps(result))
    return 0 if result['status'] in {'PASS', 'FROZEN_NOT_EXECUTED'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
