"""Bind six prepared HTTP trials to one tested production surface and fixed recipe.

This checks artifact correspondence, not the truth of historical test assertions.
It never launches a process, runs a workload, changes a profile, or rewrites evidence.
"""
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
SOURCE = 'backend/src/main/java/dev/allow/backend/DocumentQueries.java'
CLASS = 'backend/target/classes/dev/allow/backend/DocumentQueries.class'
DEFAULT = b'private static final WorkerLaunchProfile ADVISORY_PROFILE = WorkerLaunchProfile.DEFAULT;'
TIER1 = b'private static final WorkerLaunchProfile ADVISORY_PROFILE = WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1;'
TARGETS = ('backend/target/classes/', 'backend/target/dependency/', 'backend/target/solver/')
SOURCES = ('retrieval/', 'scripts/', 'config/', 'db/', 'spec/', 'backend/src/')
CONTROL_FIELDS = {'copied_root', 'port', 'unit', 'run_id', 'created_utc', 'input_root_sha256'}
REQUIRED = {'finite_semantics', 'comparator_negative_cases', 'p1_regressions', 'java_safety'}
P1_STEPS = ('bootstrap', 'migrate', 'initialize-retrieval', 'bootstrap-documents', 'python-all',
            'sql-runtime', 'sql-clients-and-retrieval-recovery', 'document-recovery', 'http-smoke', 'http-restart')
ORDER = [[1, 'F0'], [1, 'F1'], [2, 'F1'], [2, 'F0'], [3, 'F0'], [3, 'F1']]
PROGRAMS = ('experiment_binding.py', 'test_experiment_binding.py', 'prepare_f1.py',
            'workload_correspondence.py', 'test_workload_correspondence.py',
            'compare_responses.py', 'test_compare_responses.py')
SCOPE_TOOLS = {'/usr/bin/taskset', '/etc/apparmor.d/chatgpt', '/etc/apparmor.d/unprivileged_userns'}


def require(condition, code):
    """Fail closed on a missing, ambiguous or mismatched binding."""
    if not condition:
        raise ValueError(code)


def packed(value):
    """Produce the same canonical finite JSON used by the frozen manifests."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(path):
    """Hash complete regular file bytes without logging private contents."""
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def unique(pairs):
    """Reject duplicate JSON fields before they can erase contradictory evidence."""
    result = {}
    for name, value in pairs:
        require(name not in result, 'DUPLICATE_JSON_FIELD')
        result[name] = value
    return result


def load(path):
    """Decode finite JSON from a regular nonsymlink evidence file."""
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'REGULAR_EVIDENCE_REQUIRED')
    value = json.loads(path.read_bytes(), object_pairs_hook=unique)
    packed(value)
    return value


def root_hash(value):
    """Recompute the canonical root excluding its self-referential digest."""
    return hashlib.sha256(packed({key: item for key, item in value.items()
                                 if key != 'input_root_sha256'})).hexdigest()


def rooted(path):
    """Require an exact internally bound historical or prepared input manifest."""
    value = load(path)
    require(value.get('input_root_sha256') == root_hash(value), 'MANIFEST_ROOT_MISMATCH')
    return value


def binding(path):
    """Preserve absolute artifact identity without silently resolving an alias."""
    path = Path(path).absolute()
    require(path.resolve() == path and path.is_file() and not path.is_symlink(), 'EXACT_ARTIFACT_PATH_REQUIRED')
    return {'path': str(path), 'sha256': digest(path)}


def inventory(rows, historical_labels=False):
    """Require unique safe relative input names and complete SHA-256 values."""
    result = {}
    for row in rows:
        name = row['path']
        require(isinstance(name, str) and not Path(name).is_absolute()
                and (historical_labels or '..' not in Path(name).parts)
                and str(Path(name)) == name, 'UNSAFE_INPUT_NAME')
        require(name not in result and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
                'DUPLICATE_OR_INVALID_INPUT')
        result[name] = row['sha256']
    require(bool(result), 'EMPTY_INPUT_INVENTORY')
    return result


def equal_subset(required, observed, label):
    """Check every required named digest; missing evidence never becomes an exclusion."""
    require(bool(required), 'EMPTY_REQUIRED_SURFACE:' + label)
    for name, value in required.items():
        require(name in observed, 'MISSING_TESTED_INPUT:' + label + ':' + name)
        require(observed[name] == value, 'TESTED_INPUT_MISMATCH:' + label + ':' + name)


def tool_inventory(rows):
    """Normalize historical resolved tool names while rejecting contradictory duplicate bindings."""
    result = {}
    for row in rows:
        name = row.get('resolved', row['path'])
        if 'sha256' not in row or not Path(name).is_absolute():
            continue
        require(name not in result or result[name] == row['sha256'], 'CONTRADICTORY_TOOL_BINDING')
        result[name] = row['sha256']
    return result


def targets(rows):
    """Select the complete production classes, resources, dependencies and solver."""
    return {name: sha for name, sha in inventory(rows).items() if name.startswith(TARGETS)}


def common_identity(manifest):
    """Ignore only declared physical/trial metadata; preserve every semantic input."""
    value = {key: item for key, item in manifest.items() if key not in CONTROL_FIELDS | {'f1_recipe'}}
    value['files'] = sorted(value['files'], key=lambda row: row['path'])
    return hashlib.sha256(packed(value)).hexdigest()


def check_recipe(baseline, candidate, receipt, recipe_sha):
    """Check the exact two-file patch, all other bytes, and recipe-to-baseline identity."""
    require(baseline['variant'] == 'F0' and candidate['variant'] == 'F1', 'PAIR_VARIANT_MISMATCH')
    first, second = inventory(baseline['files']), inventory(candidate['files'])
    require(set(first) == set(second), 'PAIR_INVENTORY_CHANGED')
    changed = {name for name in first if first[name] != second[name]}
    require(changed == {SOURCE, CLASS}, 'EXACT_TWO_FILE_DELTA_REQUIRED')
    delta = [{'path': name, 'before_sha256': first[name], 'after_sha256': second[name]}
             for name in (SOURCE, CLASS)]
    recipe = candidate.get('f1_recipe', {})
    require(recipe.get('baseline_input_root_sha256') == baseline['input_root_sha256']
            and recipe.get('baseline_root') == baseline['copied_root'], 'RECIPE_BASELINE_MISMATCH')
    require(recipe.get('verifier_sha256') == recipe_sha and recipe.get('delta') == delta, 'RECIPE_DELTA_MISMATCH')
    require(receipt.get('status') == 'PREPARED_NOT_EXECUTED' and receipt.get('variant') == 'F1'
            and receipt.get('input_root_sha256') == candidate['input_root_sha256']
            and receipt.get('copied_root') == candidate['copied_root'], 'RECIPE_RECEIPT_IDENTITY')
    require(receipt.get('exact_delta') == delta and receipt.get('build_identity') == candidate['build_identity']
            and type(receipt.get('matching_class_builds')) is int and receipt['matching_class_builds'] == 2,
            'RECIPE_RECEIPT_BUILD')
    require(receipt.get('production_profile') == 'DEFAULT_UNCHANGED'
            and receipt.get('performance_acceptance') == 'NOT_EXECUTED', 'RECIPE_NOT_GATE_ONLY')
    expected = [{'advisory_profile': profile, 'typed_advisory_constructor': True, 'default_mutation_factory': True}
                for profile in ('DEFAULT', 'DOCUMENT_ADVISORY_TIER1')]
    require(packed(receipt.get('callsites')) == packed(expected), 'RECIPE_CALLSITE_FENCE')
    excluded = CONTROL_FIELDS | {'files', 'variant', 'build_identity', 'f1_recipe'}
    require(packed({k: v for k, v in baseline.items() if k not in excluded})
            == packed({k: v for k, v in candidate.items() if k not in excluded}), 'PAIR_NONPATCH_METADATA_DRIFT')
    first_rows = {row['path']: row for row in baseline['files']}
    second_rows = {row['path']: row for row in candidate['files']}
    for name in first:
        if name not in changed:
            require(first_rows[name] == second_rows[name], 'PAIR_NONPATCH_FILE_METADATA_DRIFT')
        else:
            require(first_rows[name]['mode'] == second_rows[name]['mode'], 'PATCH_MODE_DRIFT')
    old = (Path(baseline['copied_root'])/SOURCE).read_bytes()
    new = (Path(candidate['copied_root'])/SOURCE).read_bytes()
    require(old.count(DEFAULT) == 1 and TIER1 not in old and new == old.replace(DEFAULT, TIER1, 1),
            'EXACT_SOURCE_CONSTANT_PATCH_REQUIRED')
    return delta


def check_source_ready(path, baseline):
    """Link the complete ready receipt to the prepared source and compiled inventories."""
    receipt = load(path)
    require(receipt.get('status') == 'SOURCE_READY', 'SOURCE_READY_REQUIRED')
    require(baseline['source_ready'] == binding(path), 'SOURCE_READY_RECEIPT_MISMATCH')
    files = inventory(baseline['files'])
    expected = {name: sha for name, sha in files.items() if
                (name.startswith(SOURCES) and not name.endswith(('.pyc', '.pyo')))
                or name in {'backend/pom.xml', 'gates/document/headless-preview-fixture.json'}}
    require(inventory(receipt['files']) == expected, 'SOURCE_READY_COMPLETE_INVENTORY_MISMATCH')
    compiled = {'backend/target/' + name: sha for name, sha in inventory(receipt['backend_target']['files']).items()}
    require(compiled == targets(baseline['files']), 'SOURCE_READY_COMPILED_INVENTORY_MISMATCH')
    probe = {'.gate/probe-classes/' + name: sha for name, sha in inventory(receipt['probe_classes']).items()}
    equal_subset(probe, files, 'source-ready-probe')
    programs = {'.gate/' + name: digest(HERE/name) for name in PROGRAMS}
    equal_subset(programs, files, 'prepared-gate-programs')
    return receipt


def report_inputs(prerequisites, name, artifacts):
    """Resolve a frozen prerequisite report, preserving its exact original bytes."""
    item = prerequisites[name]
    require(binding(item['path']) == {'path': item['path'], 'sha256': item['sha256']}, 'PREREQUISITE_REPORT_MUTATED:' + name)
    artifacts.append(binding(item['path']))
    return Path(item['path']), load(item['path'])


def link_semantics(path, report, baseline, artifacts, scope_tools=None):
    """Bind the differential result and its retained registration to the entire F0 build."""
    require(report.get('status') == 'PASS' and report.get('mode') == 'compare'
            and report.get('selection_evidence') is True and report.get('failures') == []
            and type(report.get('expected_cases')) is int and report['expected_cases'] == 190
            and type(report.get('executed_cases')) is int and report['executed_cases'] == 190, 'SEMANTIC_SUITE_INCOMPLETE')
    inputs_path = path.parent/'inputs.json'
    snapshot_path = path.parent/'frozen-inputs/manifest.json'
    inputs, snapshot = load(inputs_path), load(snapshot_path)
    artifacts.extend([binding(inputs_path), binding(snapshot_path)])
    registered = snapshot['registration']
    require(registered.get('input_root_sha256') == root_hash(registered)
            == report.get('runtime_registration') == inputs.get('runtime_registration'), 'SEMANTIC_REGISTRATION_LINK')
    require(inputs['backend_target_files'] == registered['backend_target_files'], 'SEMANTIC_BUILD_REGISTRATION')
    registered_files = inventory(registered['files'], historical_labels=True)
    require(inventory(snapshot['files'], historical_labels=True) == registered_files, 'SEMANTIC_SNAPSHOT_INVENTORY')
    for row in snapshot['files']:
        copied = path.parent/row['snapshot']
        require(copied.resolve().is_relative_to(path.parent.resolve()/'frozen-inputs'), 'SEMANTIC_SNAPSHOT_PATH')
        require(digest(copied) == row['sha256'], 'SEMANTIC_SNAPSHOT_MUTATED')
        artifacts.append(binding(copied))
    compiled = {'backend/target/' + name: sha for name, sha in inventory(inputs['backend_target_files']).items()
                if name.startswith(('classes/', 'dependency/', 'solver/'))}
    require(compiled == targets(baseline['files']), 'SEMANTIC_TESTED_BUILD_MISMATCH')
    require(report['build_identity'] == baseline['build_identity']['value'], 'SEMANTIC_BUILD_IDENTITY_MISMATCH')
    probe = {'.gate/probe-classes/' + name.removeprefix('test-classes/'): sha
             for name, sha in inventory(inputs['backend_target_files']).items() if name.startswith('test-classes/')}
    equal_subset(probe, inventory(baseline['files']), 'semantic-probe')
    runtime = tool_inventory(baseline['tooling']['files'])
    if scope_tools is not None:
        equal_subset(scope_tools, runtime, 'prepared-scope-tools')
        runtime = {name: sha for name, sha in runtime.items() if name not in scope_tools}
    equal_subset(runtime,
                 tool_inventory(registered['tooling']['files']), 'semantic-runtime-tooling')
    require(registered_files.get('compare_responses.py') == digest(HERE/'compare_responses.py'), 'COMPARATOR_TESTED_BYTES_MISMATCH')
    return registered


def link_negatives(path, report, semantic, artifacts):
    """Bind the negative-oracle tests to the exact historical semantic verifier bytes."""
    require(report.get('status') == 'PASS' and type(report.get('tests')) is int and report['tests'] == 31
            and all(type(report.get(name)) is int and report[name] == 0 for name in ('failures', 'errors', 'skips')),
            'NEGATIVE_SUITE_INCOMPLETE')
    require(report['registration_root'] == semantic['input_root_sha256'], 'NEGATIVE_REGISTRATION_LINK')
    equal_subset(inventory(report['files']), inventory(semantic['files'], historical_labels=True), 'negative-verifier')
    require(digest(report['log']) == report['log_sha256'], 'NEGATIVE_LOG_MUTATED')
    artifacts.append(binding(report['log']))


def p1_surface(files):
    """Select every runtime Python, Java, SQL, policy and installed tool input covered by P1."""
    return {name: sha for name, sha in files.items() if name.startswith(TARGETS)
            or name.startswith(('backend/src/main/', 'config/', 'db/', 'spec/', '.tools/'))
            or name == 'backend/pom.xml'
            or name.startswith(('retrieval/', 'scripts/')) and name.endswith('.py')}


def p1_manifest(path):
    """Bind P1 membership and links inside the registered root, before any execution."""
    manifest = load(path)
    keys = ('files', 'tooling', 'suite', 'runtime_binding_version', 'managed_runtime_files', 'managed_runtime_links')
    original_root = hashlib.sha256(packed({key: manifest[key] for key in keys})).hexdigest()
    require(manifest.get('input_root_sha256') == original_root and manifest.get('suite') == 'complete-regressions'
            and manifest.get('profile') == 'DEFAULT' and type(manifest.get('runtime_binding_version')) is int
            and manifest['runtime_binding_version'] == 1, 'P1_MANIFEST_ROOT_OR_SCOPE')
    return manifest


def link_p1_runtime(manifest, baseline):
    """Check the complete managed runtime membership, alias resolutions and executable bytes."""
    tooling = baseline['tooling']
    aliases = [row['resolved'] for row in tooling['aliases'] if row['alias'] == '.tools/retrieval-venv']
    require(len(aliases) == 1 and isinstance(aliases[0], str), 'MANAGED_PYTHON_TOOL_ALIAS_REQUIRED')
    alias = aliases[0]
    require(any(row['path'] == '.tools/retrieval-venv' and row.get('resolved') == alias
                for row in manifest['tooling']), 'P1_MANAGED_PYTHON_ALIAS_MISMATCH')
    interpreter = [row['resolved'] for row in tooling['links'] if row['path'] == alias + '/bin/python']
    require(len(interpreter) == 1, 'MANAGED_PYTHON_INTERPRETER_LINK_REQUIRED')
    python_tools = {name: sha for name, sha in tool_inventory(tooling['files']).items()
                    if name == interpreter[0] or name == alias + '/pyvenv.cfg'
                    or name.startswith(alias + '/') and '/site-packages/' in name}
    require(interpreter[0] in python_tools, 'MANAGED_PYTHON_INTERPRETER_BYTES_REQUIRED')
    equal_subset(python_tools, tool_inventory(manifest['tooling']), 'P1-Python-runtime')
    expected = [{'path': '.tools/retrieval-venv', 'target': alias, 'resolved': alias}]
    expected += [{'path': '.tools/retrieval-venv/' + str(Path(row['path']).relative_to(alias)),
                  'target': row['link_text'], 'resolved': row['resolved']}
                 for row in tooling['links'] if Path(row['path']).is_relative_to(alias)]
    links = manifest['managed_runtime_links']
    require(len({row['path'] for row in links}) == len(links)
            and packed(sorted(links, key=lambda row: row['path'])) == packed(sorted(expected, key=lambda row: row['path'])),
            'P1_MANAGED_PYTHON_LINK_MISMATCH')
    members = manifest['managed_runtime_files']
    require(len(set(members)) == len(members)
            and all(name.startswith('.tools/retrieval-venv/') for name in members), 'P1_RUNTIME_MEMBERSHIP_INVALID')
    trees = [row['members'] for row in tooling['trees'] if row['root'] == alias]
    require(len(trees) == 1, 'MANAGED_PYTHON_TREE_REQUIRED')
    observed = {name.removeprefix('.tools/retrieval-venv/') for name in members}
    observed.update(row['path'].removeprefix('.tools/retrieval-venv/') for row in links
                    if row['path'] != '.tools/retrieval-venv')
    require(set(trees[0]) == observed, 'P1_RUNTIME_MEMBERSHIP_MISMATCH')


def link_p1(path, report, baseline, artifacts):
    """Require P1's tested production surface, never just a matching source-ready label."""
    require(report.get('status') == 'PASS' and report.get('source_mutation') == []
            and report.get('shared_runtime_modified') is False
            and report.get('spring_cleanup', {}).get('owned_identity_absent') is True, 'P1_REGRESSIONS_INCOMPLETE')
    require([row.get('service') for row in report.get('service_cleanup', [])] == ['proxy', 'postgres']
            and all(row.get('owned_identity_absent') is True and row.get('emergency_escalation') is False
                    for row in report['service_cleanup']), 'P1_CLEANUP_INCOMPLETE')
    require([row.get('name') for row in report.get('steps', [])] == list(P1_STEPS)
            and all(row.get('status') == 'PASS' and type(row.get('exit_code')) is int
            and row['exit_code'] == 0 for row in report['steps']), 'P1_STEP_FAILED')
    for row in report['steps']:
        log = path.parent/(row['name'] + '-private.log')
        require(digest(log) == row['log_sha256'], 'P1_STEP_LOG_MUTATION')
        artifacts.append(binding(log))
    manifest_path = path.parent/'manifest.json'
    manifest = p1_manifest(manifest_path)
    artifacts.append(binding(manifest_path))
    require(manifest['input_root_sha256'] == report['input_root_sha256'], 'P1_REPORT_ROOT')
    require(report.get('manifest_sha256_before_execution') == digest(manifest_path)
            and report.get('manifest_unchanged_after_execution') is True
            and report.get('tooling_mutation') == []
            and report.get('managed_runtime_inventory_unchanged') is True
            and report.get('managed_runtime_links_unchanged') is True, 'P1_RUNTIME_INTEGRITY_LINK')
    observed = inventory(manifest['files'])
    relative_tools = {}
    for row in manifest['tooling']:
        if 'sha256' not in row or Path(row['path']).is_absolute():
            continue
        name, sha = next(iter(inventory([row]).items()))
        require(name not in relative_tools or relative_tools[name] == sha, 'P1_AMBIGUOUS_TOOL_BINDING')
        relative_tools[name] = sha
    for name, sha in relative_tools.items():
        require(name not in observed or observed[name] == sha, 'P1_AMBIGUOUS_TOOL_BINDING')
        observed[name] = sha
    equal_subset(p1_surface(inventory(baseline['files'])), observed, 'P1-runtime')
    link_p1_runtime(manifest, baseline)
    for row in report['copied_artifacts']:
        copied = path.parent/row['path']
        require(digest(copied) == row['sha256'], 'P1_SUBREPORT_MUTATION')
        artifacts.append(binding(copied))


def link_safety(path, report, baseline, artifacts):
    """Bind the registered safety report to its complete tested production bytes and sources."""
    expected = {'total': 12, 'passed': 12, 'blocked': 0, 'unresolved': 0}
    require(report.get('status') == 'VERIFIED' and packed(report.get('claims')) == packed(expected)
            and report.get('blocking_reasons') == [] and report.get('infrastructure_errors') == [], 'SAFETY_SUITE_INCOMPLETE')
    manifest_path = path.parent/'manifest.json'
    manifest = rooted(manifest_path)
    artifacts.append(binding(manifest_path))
    require(report['input_root_sha256'] == manifest['input_root_sha256']
            and report['verifier'] == manifest['verifier'], 'SAFETY_REPORT_ROOT')
    cwd = Path(manifest['execution']['cwd'])
    observed = {}
    for row in manifest['files']:
        original = Path(row['path'])
        if original.is_relative_to(cwd):
            name = 'backend/' + str(original.relative_to(cwd))
            require(name not in observed, 'SAFETY_DUPLICATE_INPUT')
            observed[name] = row['sha256']
    require({name: sha for name, sha in observed.items() if name.startswith(TARGETS)}
            == targets(baseline['files']), 'SAFETY_TESTED_BUILD_MISMATCH')
    sources = {name: sha for name, sha in inventory(baseline['files']).items()
               if name.startswith('backend/src/') or name == 'backend/pom.xml'}
    equal_subset(sources, observed, 'safety-source')
    java_home = baseline['java']['home']
    java_tools = {name: sha for name, sha in tool_inventory(baseline['tooling']['files']).items()
                  if name.startswith((java_home + '/', '/etc/java-17-openjdk/'))}
    equal_subset(java_tools, tool_inventory(manifest['files']), 'safety-JDK')
    require(packed(report['raw_result']['tests']) == packed(sorted(manifest['test_methods']))
            and len(manifest['test_methods']) == 36
            and len(set(manifest['test_methods'])) == 36
            and all(type(report['raw_result'][name]) is int and report['raw_result'][name] == 0
                    for name in ('failures', 'errors', 'skipped')), 'SAFETY_METHOD_INVENTORY')
    require(len(manifest['claims']) == 12 and len({claim['id'] for claim in manifest['claims']}) == 12,
            'SAFETY_CLAIM_INVENTORY')
    for claim in manifest['claims']:
        evidence_path = path.parent/(claim['id'] + '.json')
        evidence = load(evidence_path)
        require(evidence.get('status') == 'PASS' and evidence.get('claim_id') == claim['id']
                and evidence.get('input_root_sha256') == manifest['input_root_sha256']
                and evidence.get('verifier_sha256') == report['verifier']['sha256']
                and evidence['raw_result']['tests'] == claim['tests'], 'SAFETY_CLAIM_EVIDENCE_LINK')
        artifacts.append(binding(evidence_path))
    for name in ('before.json', 'after.json'):
        value = load(path.parent/name)
        require(value.get('input_root_sha256') == manifest['input_root_sha256'] and value.get('inputs_verified') is True
                and value.get('manifest_sha256') == digest(manifest_path), 'SAFETY_INPUT_INTEGRITY_LINK')
        artifacts.append(binding(path.parent/name))
    for row in report['raw_result']['xml_reports']:
        require(digest(row['path']) == row['sha256'], 'SAFETY_XML_MUTATED')
        artifacts.append(binding(row['path']))


def scope_projection(directory, baseline, artifacts):
    """Attribute exactly three containment-only inputs to a real-worker preflight, not190 semantics."""
    directory = Path(directory)
    manifest_path, report_path = directory/'manifest.json', directory/'report.json'
    manifest, report = rooted(manifest_path), load(report_path)
    require(manifest.get('kind') == 'CALLER_CONTEXT_SCOPE_PREFLIGHT'
            and report.get('status') == 'PASS' and report.get('benchmark_executed') is False
            and report.get('input_root_sha256') == manifest['input_root_sha256'], 'SCOPE_PREFLIGHT_IDENTITY')
    worker, cleanup = report['worker'], report['cleanup']
    require(worker.get('profile') == 'DEFAULT' and worker.get('outcome') == 'COMPLETE_RESPONSE'
            and worker.get('workerStatus') == 'VALIDATED' and worker.get('reaped') is True
            and type(worker.get('workerExitCode')) is int and worker['workerExitCode'] == 0
            and worker.get('buildIdentity') == baseline['build_identity']['value'], 'SCOPE_REAL_WORKER_REQUIRED')
    require(cleanup.get('status') == 'PASS' and cleanup.get('populated_zero_observed') is True
            and cleanup.get('owned_identities_absent') is True and cleanup.get('terminal_resources_complete') is True
            and cleanup.get('terminal_resource_limits_passed') is True, 'SCOPE_CLEANUP_REQUIRED')
    tools = tool_inventory([*manifest['scope_tools'], *manifest['policy_inputs']])
    require(set(tools) == SCOPE_TOOLS, 'EXACT_SCOPE_TOOL_PROJECTION_REQUIRED')
    artifacts.extend([binding(manifest_path), binding(report_path)])
    for row in manifest['files']:
        copied = Path(manifest['copied_root'])/row['path']
        require(digest(copied) == row['sha256'], 'SCOPE_RETAINED_INPUT_MUTATION')
        artifacts.append(binding(copied))
    verifier = next(row for row in manifest['files'] if row['path'] == '.gate/scope_preflight.py')
    require(report.get('verifier_sha256') == verifier['sha256'], 'SCOPE_VERIFIER_LINK')
    return tools


def link_prerequisites(path, baseline, artifacts, scope_preflight=None):
    """Resolve four reports to their unique tested inventories before admitting a baseline."""
    prerequisites = load(path)
    require(set(prerequisites) == REQUIRED, 'EXACT_PREREQUISITE_SET_REQUIRED')
    artifacts.append(binding(path))
    resolved = {name: report_inputs(prerequisites, name, artifacts) for name in REQUIRED}
    scoped = baseline.get('launch_lane') == 'owned_caller_scope_v1'
    require(scoped == (scope_preflight is not None), 'SCOPE_PREFLIGHT_BINDING_REQUIRED')
    scope_tools = scope_projection(scope_preflight, baseline, artifacts) if scoped else None
    semantic = link_semantics(*resolved['finite_semantics'], baseline, artifacts, scope_tools)
    link_negatives(*resolved['comparator_negative_cases'], semantic, artifacts)
    link_p1(*resolved['p1_regressions'], baseline, artifacts)
    link_safety(*resolved['java_safety'], baseline, artifacts)
    return {'semantic_root': semantic['input_root_sha256'], 'baseline_build': baseline['build_identity']['value'],
            'containment_only_inputs': scope_tools or {},
            'containment_projection': 'Exactly taskset and two AppArmor policy files use frozen real-worker scope preflight; not part of historical190 semantic coverage.' if scoped else None,
            'scope': 'Exact tested production/source inventory links; historical test semantics remain verifier-trusted.'}


def check_pairs(pairs, source_ready_path, artifacts):
    """Require all three complete pairs before execution and reject every cross-pair drift."""
    require(len(pairs) == 3 and [row['pair'] for row in pairs] == [1, 2, 3]
            and all(type(row['pair']) is int for row in pairs), 'EXACT_THREE_PAIRS_REQUIRED')
    profiles, trials, roots, units = {}, [], set(), set()
    baseline_reference = None
    recipe_sha = digest(HERE/'prepare_f1.py')
    for pair in pairs:
        first = rooted(pair['f0_manifest'])
        second = rooted(pair['f1_manifest'])
        check_recipe(first, second, load(pair['recipe_receipt']), recipe_sha)
        check_source_ready(source_ready_path, first)
        artifacts.extend(binding(pair[key]) for key in ('f0_manifest', 'f1_manifest', 'recipe_receipt'))
        for manifest, key in ((first, 'f0_manifest'), (second, 'f1_manifest')):
            require(manifest['copied_root'] not in roots and manifest['unit'] not in units, 'TRIAL_INSTALLATION_REUSED')
            roots.add(manifest['copied_root']); units.add(manifest['unit'])
            profile = manifest['variant']
            current = common_identity(manifest)
            require(profile not in profiles or profiles[profile] == current, 'CROSS_PAIR_CONTENT_DRIFT:' + profile)
            profiles[profile] = current
            trials.append({'pair': pair['pair'], 'variant': profile, 'manifest': binding(pair[key]),
                           'input_root_sha256': manifest['input_root_sha256'], 'common_identity': current})
        baseline_reference = first if baseline_reference is None else baseline_reference
    return baseline_reference, profiles, trials


def create_experiment(prerequisite_path, source_ready_path, pairs, scope_preflight=None):
    """Create a complete in-memory registration; the caller must persist it exclusively before execution."""
    artifacts = [binding(source_ready_path)] + [binding(HERE/name) for name in PROGRAMS]
    baseline, identities, trials = check_pairs(pairs, source_ready_path, artifacts)
    prerequisites = link_prerequisites(prerequisite_path, baseline, artifacts, scope_preflight)
    files = {row['path']: row for row in artifacts}
    value = {'schema_version': '1.0', 'status': 'FROZEN_EXPERIMENT_BINDING', 'order': ORDER,
             'source_ready': str(Path(source_ready_path).absolute()), 'prerequisites': str(Path(prerequisite_path).absolute()),
             'scope_preflight': str(Path(scope_preflight).absolute()) if scope_preflight is not None else None,
             'pairs': [{key: str(Path(item).absolute()) if key != 'pair' else item for key, item in row.items()} for row in pairs],
             'common_identities': identities, 'trials': trials, 'prerequisite_links': prerequisites,
             'files': sorted(files.values(), key=lambda row: row['path']),
             'excluded_controls': sorted(CONTROL_FIELDS),
             'boundary': 'Artifact correspondence only; installation.verify must still check actual copied inputs and tooling before/after runtime. No benchmark execution, acceptance or profile activation.'}
    value['input_root_sha256'] = root_hash(value)
    return value


def verify_experiment(value):
    """Recompute every binding against the original frozen root, never a replacement registration."""
    require(value.get('status') == 'FROZEN_EXPERIMENT_BINDING'
            and value.get('input_root_sha256') == root_hash(value), 'EXPERIMENT_ROOT_MISMATCH')
    require(len({row['path'] for row in value['files']}) == len(value['files']), 'DUPLICATE_EXPERIMENT_INPUT')
    for row in value['files']:
        require(binding(row['path']) == row, 'EXPERIMENT_INPUT_MUTATION')
    rebuilt = create_experiment(value['prerequisites'], value['source_ready'], value['pairs'], value['scope_preflight'])
    require(packed(rebuilt) == packed(value), 'EXPERIMENT_BINDING_CHANGED')
    return value['input_root_sha256']


def verify_trial(value, manifest_path, pair, variant):
    """Authorize only an exact member of the frozen six-trial set; ordering remains the runner's duty."""
    verify_experiment(value)
    matches = [row for row in value['trials'] if row['pair'] == pair and row['variant'] == variant]
    require(type(pair) is int and len(matches) == 1 and matches[0]['manifest'] == binding(manifest_path),
            'UNREGISTERED_TRIAL')
    return matches[0]
