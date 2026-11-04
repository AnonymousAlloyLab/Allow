"""Full finite response comparison with explicit noncomparability and capture boundaries."""
import base64
import hashlib
import json
import re
from pathlib import Path
import uuid

from compare_responses import check_response, compare, decode, finite, identical, unique
import probe_results
import semantic_plan
from harness_common import digest, read_private, same_process

CONTEXT = 'TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL'
ROUTES = {'W0': 'FRESH_DEFAULT_BUBBLEWRAP', 'W1': 'ACTUAL_WARM_WORKER_POOL_ASSUMED_CLEAN'}
REVALIDATE = 'DIRECT_HELPER_LEDGER_NOT_OWNEDWORKERRUN'


def require(value, reason):
    """Missing, unknown and type-coerced success never discharge a finite obligation."""
    if not value:
        raise ValueError(reason)


def private_result(root, pointer):
    """Resolve only one hashed private evidence basename without following aliases."""
    relative = Path(pointer['path'])
    require(len(relative.parts) == 1 and relative.suffix == '.json', 'semantic_private_result_path')
    path = root/'.gate/evidence'/relative
    require(not path.is_symlink() and digest(path) == pointer['sha256'], 'semantic_private_result_identity')
    return read_private(path)


def input_frame(root, item):
    """Decode exact registered request bytes, with their distinct bound and no response framing."""
    raw = (root/'.gate'/item['path']).read_bytes()
    require(type(item['bytes']) is int and len(raw) == item['bytes'] <= 2097153
            and hashlib.sha256(raw).hexdigest() == item['sha256'], 'semantic_fixture_bytes')
    def nonfinite(_):
        raise ValueError('semantic_nonfinite_input')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    finite(value)
    require(isinstance(value, dict), 'semantic_input_object')
    return value


def response(record, item, frame, variant, build):
    """Check exact input, explicit guard classes and complete typed response content."""
    require(record['profile'] == 'DEFAULT' and record['variant'] == variant, 'semantic_default_profile_variant')
    require(record['inputSha256'] == item['sha256'] and type(record['inputBytes']) is int
            and record['inputBytes'] == item['bytes'], 'semantic_record_input_binding')
    require(record['buildIdentity'] == build, 'semantic_record_build_binding')
    require(type(record['schemaVersion']) is int and record['schemaVersion'] == 1
            and record['contextBoundary'] == CONTEXT, 'semantic_record_schema_context')
    route = REVALIDATE if variant == 'W1' and item['operation'] == 'REVALIDATE' else ROUTES[variant]
    require(record['route'] == route, 'semantic_record_route')
    if variant == 'W1' and item['comparison'] == 'NOT_COMPARABLE':
        require(record['outcome'] == 'BINDING_INPUT_REJECTED' and record['noPrivateHandoff'] is True
                and record['noWorkerStarted'] is True, 'semantic_binding_rejection_required')
        require('responseBase64' not in record, 'semantic_binding_rejection_has_response')
        require(item['name'] == 'context-invalid-policyVersion' and record['outputEquivalence'] == 'NOT_COMPARABLE'
                and record['rejectionCode'] == 'BLANK_POLICY_UNREACHABLE_INSTALLED_CONTEXT', 'semantic_binding_domain_gap')
        return None
    if item.get('expectedProbeReject'):
        require(record['outcome'] == 'INPUT_REJECTED' and record['noPrivateHandoff'] is True,
                'semantic_explicit_input_limit_rejection')
        if variant == 'W0':
            require(record['noWorkerStarted'] is True, 'semantic_fresh_boundary_spawned_worker')
        require('responseBase64' not in record, 'semantic_input_rejection_has_response')
        require(record['rejectionCode'] == 'PRIVATE_INPUT_LIMIT', 'semantic_input_rejection_code')
        if variant == 'W1':
            require(record['boundaryObservation'] == 'ACTUAL_POOL_ENCODER_EXCEPTION_BEFORE_EXCHANGE',
                    'semantic_actual_encoder_boundary_required')
        return None
    return complete_response(record, item, frame, variant)


def complete_response(record, item, frame, variant):
    """Preserve complete decoded output; do not call reserialization raw wire evidence."""
    capture = 'RESERIALIZED_COMPLETE_POOL_RESPONSE' if variant == 'W1' and item['operation'] == 'VALIDATE' else 'ACTUAL_STDOUT_FRAME'
    require(record['outcome'] == 'COMPLETE_RESPONSE' and record['responseCapture'] == capture,
            'semantic_complete_capture_required')
    require(record['requestIdentityMatches'] is True and record['reaped'] is True,
            'semantic_nonce_and_reap_required')
    require(record['noWorkerStarted'] is False and record['noPrivateHandoff'] is False,
            'semantic_actual_handoff_required')
    if variant == 'W1' and item['operation'] == 'VALIDATE':
        require(record['productionFrameStrictJsonEqual'] is True and record['published'] is True
                and type(record['productionFrameBytes']) is int and 0 < record['productionFrameBytes'] < 2097152
                and isinstance(record['productionFrameSha256'], str)
                and re.fullmatch('[0-9a-f]{64}', record['productionFrameSha256']) is not None,
                'semantic_production_encoder_observation')
    require(type(record['workerExitCode']) is int and record['workerExitCode'] == 0, 'semantic_worker_exit')
    raw = base64.b64decode(record['responseBase64'], validate=True)
    require(type(record['responseBytes']) is int and len(raw) == record['responseBytes']
            and hashlib.sha256(raw).hexdigest() == record['responseSha256'], 'semantic_response_bytes_hash')
    value = decode(raw)
    check_response(value, frame)
    require(record['workerStatus'] == value['status'], 'semantic_worker_status_binding')
    require(value['status'] == item['expectedStatus'], 'semantic_expected_status')
    if 'expectedMode' in item:
        if item['expectedMode'] is None:
            require('mode' not in value['data'], 'semantic_unexpected_mode')
        else:
            require(value['data'].get('mode') == item['expectedMode'], 'semantic_expected_mode')
    if value['status'] == 'VALIDATED':
        content_oracle(value, frame, item)
    return value


def content_oracle(value, frame, item):
    """Keep authored SOURCE and historical payloads byte/type exact where declared."""
    candidate = frame.get('candidate')
    if candidate is not None and candidate.get('mode') == 'SOURCE':
        require(value['data']['source'] == candidate['source'], 'semantic_authored_source_changed')
    if item.get('historicalExact'):
        for key in ('mode', 'source', 'sourceHash', 'module', 'occurrences', 'trivia'):
            require(identical(value['data'][key], frame['baseArtifact'][key]), 'semantic_history_changed')


def ownership(root, row, item, variant):
    """Distinguish actual worker-group receipts from the baseline's process-only ownership."""
    value = private_result(root, row['ownership'])
    cleanup = row['cleanup']
    require(cleanup['status'] == 'PASS' and cleanup['directChildReaped'] is True
            and cleanup['capacityRetained'] is False, 'semantic_case_cleanup')
    identities = row['identities']
    require(isinstance(identities, list), 'semantic_identity_list')
    for identity in identities:
        require(set(identity) == {'pid', 'start_ticks'} and type(identity['pid']) is int and identity['pid'] > 0,
                'semantic_process_identity_schema')
        require(isinstance(identity['start_ticks'], str) and identity['start_ticks'].isdigit()
                and not same_process(identity), 'semantic_owned_process_remaining')
    require(len({(v['pid'], v['start_ticks']) for v in identities}) == len(identities), 'semantic_duplicate_identity')
    groups = value['groups']
    require(isinstance(groups, list), 'semantic_group_receipts')
    if variant == 'W0':
        require(value['perWorkerCgroup'] is False and groups == [], 'semantic_baseline_ownership_scope')
        require(cleanup['populatedZero'] is False and cleanup['outerScopeCleanupRequired'] is True,
                'semantic_baseline_has_no_worker_group')
        return value
    require(value['perWorkerCgroup'] is True and type(value['remainingReservations']) is int
            and value['remainingReservations'] == 0, 'semantic_warm_ledger_not_released')
    if value['noGroupAllocated'] is True:
        require(groups == [] and item['comparison'] == 'NOT_COMPARABLE', 'semantic_unexpected_no_group')
        require(identities == [] and cleanup['populatedZero'] is False and cleanup['noGroupAllocated'] is True,
                'semantic_no_group_claims')
        return value
    require(groups and cleanup['populatedZero'] is True, 'semantic_warm_positive_empty')
    require(cleanup['noGroupAllocated'] is False, 'semantic_allocated_group_claim')
    nonce = value['poolNonce']
    require(str(uuid.UUID(nonce)) == nonce, 'semantic_pool_nonce')
    config = read_private(root/'.runtime/warm-pool/config.json')
    require(len({group['group'] for group in groups}) == len(groups), 'semantic_duplicate_group')
    bound = [group_identity(group, nonce, config, identities) for group in groups]
    require({v for v in bound if v is not None} == {(v['pid'], v['start_ticks']) for v in identities},
            'semantic_unbound_identity')
    return value


def group_identity(group, nonce, config, identities):
    """Link released generation counters to the original direct child, including exact reap."""
    probe_results.group_receipt(group, nonce, config)
    require(group['finalPhase'] == 'RELEASED', 'semantic_generation_not_released')
    if 'pid' not in group:
        require('startTicks' not in group and 'exitCode' not in group and 'directChildReaped' not in group,
                'semantic_never_spawned_identity_fields')
        return None
    identity = {'pid': group['pid'], 'start_ticks': group['startTicks']}
    require(type(group['pid']) is int and identity in identities and group['directChildReaped'] is True
            and type(group['exitCode']) is int, 'semantic_group_child_receipt')
    return (group['pid'], group['startTicks'])


def check_row(root, manifest, item, row, variant):
    """Validate one immutable fixture outcome before comparing it with its partner."""
    route = REVALIDATE if variant == 'W1' and item['operation'] == 'REVALIDATE' else ROUTES[variant]
    require(row['id'] == item['name'] and row['status'] == 'PASS' and row['route'] == route, 'semantic_row_identity_route')
    require(row['contextBoundary'] == CONTEXT, 'semantic_row_context')
    frame = input_frame(root, item)
    record = private_result(root, row['record'])
    response(record, item, frame, variant, manifest['build_identity']['value'])
    owned = ownership(root, row, item, variant)
    if record['outcome'] == 'COMPLETE_RESPONSE':
        selected = {'pid': record['workerPid'], 'start_ticks': record['workerStartTicks']}
        require(type(selected['pid']) is int and selected in row['identities'], 'semantic_actual_worker_required')
        if variant == 'W1':
            matches = [g for g in owned['groups'] if g.get('pid') == selected['pid']
                       and g.get('startTicks') == selected['start_ticks']]
            require(len(matches) == 1 and matches[0]['exitCode'] == record['workerExitCode'], 'semantic_selected_worker_receipt')
    if record['noWorkerStarted'] is True:
        require(row['identities'] == [], 'semantic_rejection_spawn_claim')
    return {'id': row['id'], 'status': 'PASS', 'route': route, 'outcome': record['outcome'],
            'record': row['record'], 'ownership': row['ownership'], 'comparison': item['comparison'],
            'responseCapture': record.get('responseCapture'), 'cleanup': row['cleanup']}


def verify_variant(root, manifest, variant):
    """Require exactly all190 case results plus the registered build and manifest bytes."""
    done = read_private(root/'.gate/evidence/semantic-complete.json')
    require(done['status'] == 'COMPLETE' and type(done['exit_code']) is int and done['exit_code'] == 0 and done['probe_reaped'] is True,
            'semantic_probe_transport_failed')
    path = root/'.gate/evidence/semantic-java.json'
    require(digest(path) == done['java_report_sha256'], 'semantic_java_report_changed')
    report = read_private(path)
    require(type(report['schema']) is int and report['schema'] == 1 and report['status'] == 'PASS'
            and report['variant'] == variant, 'semantic_java_report_status_variant')
    require(report['contextBoundary'] == CONTEXT and report['selectedRuntimeRoute'] == 'NOT_TESTED_PRODUCTION_DISABLED'
            and report['classification'] == 'FINITE_CASE_CHECKS_NOT_PAIRWISE_EQUIVALENCE', 'semantic_report_trust_labels')
    require(report['buildIdentity'] == manifest['build_identity']['value']
            and report['caseManifestSha256'] == digest(root/'.gate/semantic-fixtures.json'), 'semantic_report_input_binding')
    semantic_plan.verify(root/'.gate')
    plan = read_private(root/'.gate/semantic-fixtures.json')
    require(len(report['cases']) == len(plan['fixtures']) == 190, 'semantic_exact190_results')
    checked = [check_row(root, manifest, item, row, variant) for item, row in zip(plan['fixtures'], report['cases'])]
    return {'status': 'PASS', 'classification': 'FINITE_CASE_CHECKS_NOT_PAIRWISE_EQUIVALENCE',
            'variant': variant, 'cases': checked, 'java_report_sha256': digest(path),
            'context_boundary': CONTEXT, 'selected_runtime_route': 'OPEN', 'performance_evidence': False}


def compare_case(item, frame, left, right):
    """Keep the frozen domain gap explicit; never normalize it into equality."""
    if item['comparison'] == 'NOT_COMPARABLE':
        require(left is not None and right is None and left['status'] == 'UNAVAILABLE', 'semantic_domain_gap_changed')
        return {'id': item['name'], 'status': 'NOT_COMPARABLE', 'reason': item['comparison_reason']}
    if item.get('expectedProbeReject'):
        require(left is None and right is None, 'semantic_boundary_outcome_mismatch')
        return {'id': item['name'], 'status': 'PASS', 'comparison': 'EXPLICIT_INPUT_LIMIT_REJECTION'}
    result = compare(left, right, frame)
    return dict(result, id=item['name'])
