"""Structured adversarial fixtures for correspondence only; no JVM, SQL or HTTP work."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import experiment_binding as subject


def write(path, value):
    """Create deterministic fixture JSON under the test-owned temporary directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(subject.packed(value))
    return path


def seal(value):
    """Give a synthetic fixture a real canonical content root."""
    value['input_root_sha256'] = subject.root_hash(value)
    return value


class Fixture:
    """Provide fully linked synthetic historical reports and six separate prepared roots."""

    def __init__(self, root):
        """Build small valid-shaped evidence without pretending to execute its test claims."""
        self.root = root
        self.source_ready = root/'source-ready.json'
        self.prerequisites = root/'prerequisites.json'
        self.pairs = []
        self.tools = [{'path': '/test-tools/jdk/release', 'sha256': '1'*64},
                      {'path': '/test-tools/venv/lib/python3.12/site-packages/module.py', 'sha256': '2'*64},
                      {'path': '/test-tools/python', 'sha256': '3'*64}]
        for number in range(1, 4):
            self.pair(number)
        baseline = subject.load(self.pairs[0]['f0_manifest'])
        self.historical(baseline)

    def contents(self, profile):
        """Define a finite complete fake installation and the only allowed profile delta."""
        result = {subject.SOURCE: subject.DEFAULT if profile == 'F0' else subject.TIER1,
                subject.CLASS: ('class-' + profile).encode(),
                'backend/target/classes/application.properties': b'properties',
                'backend/target/dependency/dependency.jar': b'dependency',
                'backend/target/solver/alloy.jar': b'alloy',
                'backend/src/main/java/Marker.java': b'main',
                'backend/src/test/java/FixtureTest.java': b'test',
                'backend/pom.xml': b'pom', 'retrieval/allow_documents/store.py': b'store',
                'scripts/bootstrap_documents.py': b'bootstrap', 'config/policy.json': b'policy',
                'db/schema.sql': b'schema', 'spec/policy.json': b'spec',
                'gates/document/headless-preview-fixture.json': b'fixture',
                '.gate/probe-classes/dev/allow/backend/FreshTier1ProbeMain.class': b'probe',
                '.gate/probe-classes/dev/allow/backend/FreshTier1ProbeMain$Options.class': b'options',
                '.tools/sqlean/guard': b'guard'}
        result.update({'.gate/' + name: (subject.HERE/name).read_bytes() for name in subject.PROGRAMS})
        return result

    def manifest(self, number, profile):
        """Write a separate root with actual Query source bytes and fixed content identities."""
        directory = self.root/f'pair-{number}-{profile}'
        rows = []
        for name, raw in self.contents(profile).items():
            path = directory/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            rows.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw), 'mode': 384})
        value = {'files': rows, 'variant': profile, 'copied_root': str(directory), 'unit': f'unit-{number}-{profile}',
                 'run_id': f'run-{number}-{profile}', 'port': 18000 + number, 'created_utc': str(number),
                 'java': {'home': '/test-tools/jdk'},
                 'tooling': {'files': self.tools, 'aliases': [{'alias': '.tools/retrieval-venv', 'resolved': '/test-tools/venv'}],
                             'links': [{'path': '/test-tools/venv/bin/python', 'resolved': '/test-tools/python',
                                        'link_text': '/test-tools/python'}],
                             'trees': [{'root': '/test-tools/venv',
                                        'members': ['bin/python', 'lib/python3.12/site-packages/module.py']}]},
                 'build_identity': {'value': 'build-' + profile}, 'source_ready': {}}
        if not self.source_ready.exists():
            files = subject.inventory(rows)
            sources = [row for row in rows if row['path'].startswith(subject.SOURCES)
                       or row['path'] in {'backend/pom.xml', 'gates/document/headless-preview-fixture.json'}]
            targets = [dict(row, path=row['path'].removeprefix('backend/target/')) for row in rows
                       if row['path'].startswith(subject.TARGETS)]
            probes = [dict(row, path=row['path'].removeprefix('.gate/probe-classes/')) for row in rows
                      if row['path'].startswith('.gate/probe-classes/')]
            write(self.source_ready, {'status': 'SOURCE_READY', 'files': sources,
                                     'backend_target': {'path': str(directory/'backend/target'), 'files': targets},
                                     'probe_classes': probes})
        value['source_ready'] = subject.binding(self.source_ready)
        return seal(value)

    def pair(self, number):
        """Bind a synthetic successful recipe to the exact baseline and candidate manifests."""
        first, second = self.manifest(number, 'F0'), self.manifest(number, 'F1')
        a, b = subject.inventory(first['files']), subject.inventory(second['files'])
        delta = [{'path': name, 'before_sha256': a[name], 'after_sha256': b[name]} for name in (subject.SOURCE, subject.CLASS)]
        second['f1_recipe'] = {'baseline_root': first['copied_root'], 'baseline_input_root_sha256': first['input_root_sha256'],
                               'verifier_sha256': subject.digest(subject.HERE/'prepare_f1.py'), 'delta': delta}
        seal(second)
        receipt = {'status': 'PREPARED_NOT_EXECUTED', 'variant': 'F1', 'copied_root': second['copied_root'],
                   'input_root_sha256': second['input_root_sha256'], 'build_identity': second['build_identity'],
                   'exact_delta': delta, 'matching_class_builds': 2, 'production_profile': 'DEFAULT_UNCHANGED',
                   'performance_acceptance': 'NOT_EXECUTED',
                   'callsites': [{'advisory_profile': item, 'typed_advisory_constructor': True, 'default_mutation_factory': True}
                                 for item in ('DEFAULT', 'DOCUMENT_ADVISORY_TIER1')]}
        directory = self.root/f'pair-{number}'
        self.pairs.append({'pair': number, 'f0_manifest': write(directory/'F0.json', first),
                           'f1_manifest': write(directory/'F1.json', second),
                           'recipe_receipt': write(directory/'recipe.json', receipt)})

    def historical(self, baseline):
        """Construct complete linked manifests and reports, whose truth is outside these tests."""
        rows = baseline['files']
        compiled = [dict(row, path=row['path'].removeprefix('backend/target/')) for row in rows if row['path'].startswith(subject.TARGETS)]
        compiled += [dict(row, path='test-classes/' + row['path'].removeprefix('.gate/probe-classes/'))
                     for row in rows if row['path'].startswith('.gate/probe-classes/')]
        semantic = self.root/'semantic'
        snapshot_file = semantic/'frozen-inputs/0.input'
        snapshot_file.parent.mkdir(parents=True)
        snapshot_file.write_bytes((subject.HERE/'compare_responses.py').read_bytes())
        verifier = {'path': 'compare_responses.py', 'sha256': subject.digest(snapshot_file)}
        registered = seal({'files': [verifier], 'backend_target_files': compiled, 'tooling': {'files': self.tools}})
        write(semantic/'frozen-inputs/manifest.json', {'registration': registered,
              'files': [dict(verifier, snapshot='frozen-inputs/0.input')]})
        write(semantic/'inputs.json', {'runtime_registration': registered['input_root_sha256'], 'backend_target_files': compiled})
        reports = {'finite_semantics': write(semantic/'report.json', {'status': 'PASS', 'mode': 'compare',
                   'selection_evidence': True, 'failures': [], 'expected_cases': 190, 'executed_cases': 190,
                   'runtime_registration': registered['input_root_sha256'], 'build_identity': 'build-F0'})}
        log = self.root/'negative.log'; log.write_bytes(b'not an execution record; synthetic parser fixture')
        reports['comparator_negative_cases'] = write(self.root/'negative.json', {'status': 'PASS', 'tests': 31,
                  'failures': 0, 'errors': 0, 'skips': 0, 'registration_root': registered['input_root_sha256'],
                  'files': [verifier], 'log': str(log), 'log_sha256': subject.digest(log)})
        p1 = self.root/'p1'
        tools = [row for row in rows if row['path'].startswith('.tools/')] + self.tools
        tools += [{'path': '.tools/retrieval-venv', 'resolved': '/test-tools/venv'}]
        old = {'files': rows, 'tooling': tools, 'suite': 'complete-regressions', 'profile': 'DEFAULT',
               'runtime_binding_version': 1,
               'managed_runtime_files': ['.tools/retrieval-venv/bin/python', '.tools/retrieval-venv/lib/python3.12/site-packages/module.py'],
               'managed_runtime_links': [{'path': '.tools/retrieval-venv', 'target': '/test-tools/venv', 'resolved': '/test-tools/venv'},
                                         {'path': '.tools/retrieval-venv/bin/python', 'target': '/test-tools/python', 'resolved': '/test-tools/python'}]}
        keys = ('files', 'tooling', 'suite', 'runtime_binding_version', 'managed_runtime_files', 'managed_runtime_links')
        old['input_root_sha256'] = hashlib.sha256(subject.packed({key: old[key] for key in keys})).hexdigest()
        write(p1/'manifest.json', old)
        steps = []
        for name in subject.P1_STEPS:
            log = p1/(name + '-private.log'); log.write_bytes(b'synthetic evidence fixture')
            steps.append({'name': name, 'status': 'PASS', 'exit_code': 0, 'log_sha256': subject.digest(log)})
        reports['p1_regressions'] = write(p1/'report.json', {'status': 'PASS', 'source_mutation': [],
                  'shared_runtime_modified': False, 'spring_cleanup': {'owned_identity_absent': True},
                  'service_cleanup': [{'service': name, 'owned_identity_absent': True, 'emergency_escalation': False}
                                      for name in ('proxy', 'postgres')],
                  'steps': steps, 'input_root_sha256': old['input_root_sha256'],
                  'copied_artifacts': [], 'tooling_mutation': [],
                  'manifest_sha256_before_execution': subject.digest(p1/'manifest.json'),
                  'manifest_unchanged_after_execution': True,
                  'managed_runtime_inventory_unchanged': True, 'managed_runtime_links_unchanged': True})
        reports['java_safety'] = self.safety(rows)
        self.reports = reports
        write(self.prerequisites, {name: subject.binding(path) for name, path in reports.items()})

    def safety(self, rows):
        """Create explicit per-claim and before/after correspondence witnesses."""
        path = self.root/'safety'
        cwd = self.root/'old-build/backend'
        files = [dict(row, path=str(cwd/row['path'].removeprefix('backend/')))
                 for row in rows if row['path'].startswith('backend/')] + self.tools
        methods = [f'x.Test#t{i:02d}' for i in range(36)]
        claims = [{'id': f'FTS{i:02d}', 'tests': methods[:1]} for i in range(1, 13)]
        verifier = {'sha256': 'f'*64}
        manifest = seal({'execution': {'cwd': str(cwd)}, 'files': files, 'verifier': verifier,
                         'test_methods': methods, 'claims': claims})
        manifest_path = write(path/'manifest.json', manifest)
        for name in ('before.json', 'after.json'):
            write(path/name, {'input_root_sha256': manifest['input_root_sha256'], 'inputs_verified': True,
                             'manifest_sha256': subject.digest(manifest_path)})
        for claim in claims:
            write(path/(claim['id'] + '.json'), {'status': 'PASS', 'claim_id': claim['id'],
                  'input_root_sha256': manifest['input_root_sha256'], 'verifier_sha256': verifier['sha256'],
                  'raw_result': {'tests': claim['tests']}})
        return write(path/'report.json', {'status': 'VERIFIED', 'claims': {'total': 12, 'passed': 12, 'blocked': 0, 'unresolved': 0},
                     'blocking_reasons': [], 'infrastructure_errors': [], 'input_root_sha256': manifest['input_root_sha256'],
                     'verifier': verifier, 'raw_result': {'tests': methods, 'failures': 0, 'errors': 0, 'skipped': 0, 'xml_reports': []}})

    def create(self):
        """Exercise the complete production binding constructor against synthetic evidence."""
        return subject.create_experiment(self.prerequisites, self.source_ready, self.pairs)


class BindingTests(unittest.TestCase):
    """Reject each missing or changed semantic input without executing production workloads."""

    def setUp(self):
        """Allocate one independent evidence tree for every adversarial test."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = Fixture(Path(self.temporary.name))

    def test_complete_six_trial_binding(self):
        """One root identifies six unique copied installations and all prerequisite links."""
        value = self.fixture.create()
        self.assertEqual(subject.verify_experiment(value), value['input_root_sha256'])
        self.assertEqual(len(value['trials']), 6)
        for pair in self.fixture.pairs:
            for variant in ('F0', 'F1'):
                self.assertEqual(subject.verify_trial(value, pair[variant.lower() + '_manifest'], pair['pair'], variant)['variant'], variant)

    def test_missing_or_mismatched_every_required_input(self):
        """Every selected digest independently blocks on omission or changed evidence."""
        required = subject.inventory(subject.load(self.fixture.pairs[0]['f0_manifest'])['files'])
        for name in required:
            for mutation in ('missing', 'changed'):
                with self.subTest(name=name, mutation=mutation):
                    observed = dict(required)
                    if mutation == 'missing': observed.pop(name)
                    else: observed[name] = '0'*64
                    with self.assertRaises(ValueError): subject.equal_subset(required, observed, 'test')

    def test_source_ready_is_not_report_authority(self):
        """A complete ready receipt cannot substitute for a missing prerequisite report."""
        for name, path in self.fixture.reports.items():
            with self.subTest(name=name):
                raw = path.read_bytes(); path.unlink()
                with self.assertRaises(ValueError): self.fixture.create()
                path.write_bytes(raw)

    def test_each_prerequisite_report_hash_is_required(self):
        """Even an otherwise valid PASS report is rejected when its bytes change."""
        for name, path in self.fixture.reports.items():
            with self.subTest(name=name):
                raw = path.read_bytes(); path.write_bytes(raw + b' ')
                with self.assertRaises(ValueError): self.fixture.create()
                path.write_bytes(raw)

    def test_semantic_compiled_input_mismatch(self):
        """A semantic PASS for another target cannot authorize the baseline bytes."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        first['files'][1]['sha256'] = '0'*64
        report_path = self.fixture.reports['finite_semantics']
        with self.assertRaisesRegex(ValueError, 'SEMANTIC_TESTED_BUILD'):
            subject.link_semantics(report_path, subject.load(report_path), first, [])

    def test_copied_gate_programs_match_registered_current_bytes(self):
        """Current selftests cannot authorize stale copied workload or binding verifiers."""
        for name in subject.PROGRAMS:
            with self.subTest(name=name):
                first = subject.load(self.fixture.pairs[0]['f0_manifest'])
                next(row for row in first['files'] if row['path'] == '.gate/' + name)['sha256'] = '0'*64
                with self.assertRaisesRegex(ValueError, 'prepared-gate-programs'):
                    subject.check_source_ready(self.fixture.source_ready, first)

    def test_p1_source_mismatch(self):
        """Unchanged Java classes do not excuse changed persistence source."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        next(row for row in first['files'] if row['path'].endswith('store.py'))['sha256'] = '0'*64
        path = self.fixture.reports['p1_regressions']
        with self.assertRaisesRegex(ValueError, 'P1-runtime'):
            subject.link_p1(path, subject.load(path), first, [])

    def test_repeated_p1_tool_labels_must_have_identical_digest(self):
        """The complete managed superset can repeat a prior tool label only with identical bytes."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        path = self.fixture.reports['p1_regressions']; manifest_path = path.parent/'manifest.json'
        original = subject.load(manifest_path); report = subject.load(path)
        for changed in (False, True):
            value = copy.deepcopy(original)
            row = copy.deepcopy(value['tooling'][0])
            if changed: row['sha256'] = '0'*64
            value['tooling'].append(row)
            keys = ('files', 'tooling', 'suite', 'runtime_binding_version', 'managed_runtime_files', 'managed_runtime_links')
            value['input_root_sha256'] = hashlib.sha256(subject.packed({key: value[key] for key in keys})).hexdigest()
            write(manifest_path, value)
            report.update(input_root_sha256=value['input_root_sha256'], manifest_sha256_before_execution=subject.digest(manifest_path))
            if changed:
                with self.assertRaisesRegex(ValueError, 'P1_AMBIGUOUS_TOOL_BINDING'):
                    subject.link_p1(path, report, first, [])
            else:
                subject.link_p1(path, report, first, [])

    def test_p1_incomplete_or_repeated_execution_steps(self):
        """One successful command or a repeated command cannot stand in for the full suite."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        path = self.fixture.reports['p1_regressions']; original = subject.load(path)
        for steps in (original['steps'][:1], original['steps'][:-1] + original['steps'][:1]):
            changed = dict(original, steps=steps)
            with self.assertRaisesRegex(ValueError, 'P1_STEP_FAILED'): subject.link_p1(path, changed, first, [])

    def test_p1_execution_log_mutation(self):
        """Retained command evidence remains bound after a successful headline is emitted."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        path = self.fixture.reports['p1_regressions']
        (path.parent/'python-all-private.log').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'P1_STEP_LOG_MUTATION'):
            subject.link_p1(path, subject.load(path), first, [])

    def test_safety_source_and_compiled_mismatch(self):
        """Both source and target provenance are required from the safety inventory."""
        path = self.fixture.reports['java_safety']
        for name in (subject.SOURCE, subject.CLASS):
            with self.subTest(name=name):
                first = subject.load(self.fixture.pairs[0]['f0_manifest'])
                next(row for row in first['files'] if row['path'] == name)['sha256'] = '0'*64
                with self.assertRaises(ValueError): subject.link_safety(path, subject.load(path), first, [])

    def test_cross_pair_drift_in_each_content_category(self):
        """Physical metadata may vary; code, tooling, JDK, cache and budgets may not."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        for key in ('files', 'tooling', 'java', 'build_identity', 'python_bytecode', 'unknown_future_budget'):
            with self.subTest(key=key):
                changed = copy.deepcopy(first); changed[key] = {'changed': True}
                if key == 'files': changed[key] = [dict(first['files'][0], sha256='0'*64)]
                self.assertNotEqual(subject.common_identity(first), subject.common_identity(changed))

    def test_cross_pair_drift_blocks_complete_registration(self):
        """A separately consistent second pair with another toolchain cannot join the experiment."""
        pair = self.fixture.pairs[1]
        first, second = subject.load(pair['f0_manifest']), subject.load(pair['f1_manifest'])
        for value in (first, second): value['tooling']['files'][0]['sha256'] = '0'*64
        seal(first)
        second['f1_recipe']['baseline_input_root_sha256'] = first['input_root_sha256']
        seal(second)
        receipt = subject.load(pair['recipe_receipt']); receipt['input_root_sha256'] = second['input_root_sha256']
        write(pair['f0_manifest'], first); write(pair['f1_manifest'], second); write(pair['recipe_receipt'], receipt)
        with self.assertRaisesRegex(ValueError, 'CROSS_PAIR_CONTENT_DRIFT'): self.fixture.create()

    def test_unbound_python_cache_blocks_runtime_link(self):
        """Source equality cannot stand in for a potentially loaded executable cache."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        first['tooling']['files'].append({'path': '/test-tools/venv/lib/python3.12/site-packages/__pycache__/module.pyc', 'sha256': '4'*64})
        path = self.fixture.reports['p1_regressions']
        with self.assertRaisesRegex(ValueError, 'MISSING_TESTED_INPUT:P1-Python-runtime'):
            subject.link_p1(path, subject.load(path), first, [])

    def test_p1_root_covers_managed_members_and_links(self):
        """New runtime metadata must be included in the original registered root."""
        path = self.fixture.root/'p1/manifest.json'
        original = subject.load(path)
        for key in ('managed_runtime_files', 'managed_runtime_links', 'runtime_binding_version'):
            value = copy.deepcopy(original)
            value[key] = [] if key != 'runtime_binding_version' else 2
            write(path, value)
            with self.assertRaisesRegex(ValueError, 'P1_MANIFEST_ROOT_OR_SCOPE'): subject.p1_manifest(path)

    def test_p1_manifest_pre_and_post_integrity(self):
        """A PASS headline cannot replace full-manifest and executable runtime integrity."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        path = self.fixture.reports['p1_regressions']
        original = subject.load(path)
        for key, changed in (('manifest_sha256_before_execution', '0'*64),
                             ('manifest_unchanged_after_execution', False), ('tooling_mutation', ['changed']),
                             ('managed_runtime_inventory_unchanged', False), ('managed_runtime_links_unchanged', False)):
            with self.subTest(key=key):
                value = dict(original); value[key] = changed
                with self.assertRaisesRegex(ValueError, 'P1_RUNTIME_INTEGRITY_LINK'):
                    subject.link_p1(path, value, first, [])

    def test_p1_symlink_target_and_resolution_are_bound(self):
        """Equal interpreter bytes do not excuse different runtime alias routing."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        original = subject.load(self.fixture.root/'p1/manifest.json')
        for key in ('target', 'resolved'):
            value = copy.deepcopy(original); value['managed_runtime_links'][1][key] = '/elsewhere'
            with self.assertRaisesRegex(ValueError, 'P1_MANAGED_PYTHON_LINK_MISMATCH'):
                subject.link_p1_runtime(value, first)

    def test_p1_runtime_membership_missing_surplus_duplicate(self):
        """Missing, extra or duplicate executable members cannot inherit tested status."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        original = subject.load(self.fixture.root/'p1/manifest.json')
        for mutation in ('missing', 'extra', 'duplicate'):
            value = copy.deepcopy(original)
            if mutation == 'missing': value['managed_runtime_files'].pop()
            if mutation == 'extra': value['managed_runtime_files'].append('.tools/retrieval-venv/lib/unseen.pyc')
            if mutation == 'duplicate': value['managed_runtime_files'].append(value['managed_runtime_files'][-1])
            with self.assertRaises(ValueError): subject.link_p1_runtime(value, first)

    def test_missing_jdk_inventory_blocks_safety_link(self):
        """A tested class inventory cannot authorize an untested JDK runtime file."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        first['tooling']['files'].append({'path': '/test-tools/jdk/lib/modules', 'sha256': '5'*64})
        path = self.fixture.reports['java_safety']
        with self.assertRaisesRegex(ValueError, 'MISSING_TESTED_INPUT:safety-JDK'):
            subject.link_safety(path, subject.load(path), first, [])

    def scope_fixture(self):
        """Create a synthetic real-worker-shaped containment record without running a worker."""
        directory = self.fixture.root/'scope'; copied = directory/'copied'
        program = copied/'.gate/scope_preflight.py'; program.parent.mkdir(parents=True)
        program.write_bytes(b'synthetic preflight verifier')
        rows = [{'path': name, 'sha256': '6'*64} for name in sorted(subject.SCOPE_TOOLS)]
        manifest = seal({'kind': 'CALLER_CONTEXT_SCOPE_PREFLIGHT', 'copied_root': str(copied),
                         'files': [{'path': '.gate/scope_preflight.py', 'sha256': subject.digest(program)}],
                         'scope_tools': rows[:1], 'policy_inputs': rows[1:]})
        write(directory/'manifest.json', manifest)
        report = {'status': 'PASS', 'benchmark_executed': False, 'input_root_sha256': manifest['input_root_sha256'],
                  'verifier_sha256': subject.digest(program),
                  'worker': {'profile': 'DEFAULT', 'outcome': 'COMPLETE_RESPONSE', 'workerStatus': 'VALIDATED',
                             'reaped': True, 'workerExitCode': 0, 'buildIdentity': 'build-F0'},
                  'cleanup': {'status': 'PASS', 'populated_zero_observed': True, 'owned_identities_absent': True,
                              'terminal_resources_complete': True, 'terminal_resource_limits_passed': True}}
        write(directory/'report.json', report)
        return directory, rows

    def test_scope_projection_is_exact_and_does_not_extend_semantic_claim(self):
        """Only frozen taskset/two policy inputs can be attributed to the separate scope preflight."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        directory, rows = self.scope_fixture(); artifacts = []
        tools = subject.scope_projection(directory, first, artifacts)
        self.assertEqual(set(tools), subject.SCOPE_TOOLS)
        first['tooling']['files'].extend(rows)
        path = self.fixture.reports['finite_semantics']
        with self.assertRaisesRegex(ValueError, 'semantic-runtime-tooling'):
            subject.link_semantics(path, subject.load(path), first, [])
        subject.link_semantics(path, subject.load(path), first, [], tools)
        first['tooling']['files'].append({'path': '/test-tools/jdk/lib/unseen.so', 'sha256': '7'*64})
        with self.assertRaisesRegex(ValueError, 'semantic-runtime-tooling'):
            subject.link_semantics(path, subject.load(path), first, [], tools)

    def test_scope_projection_rejects_missing_or_failed_evidence(self):
        """A missing worker, failed cleanup or altered preflight bytes cannot authorize tools."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        directory, rows = self.scope_fixture(); original = subject.load(directory/'report.json')
        for group, field, value in (('worker', 'reaped', False), ('worker', 'buildIdentity', 'other'),
                                    ('cleanup', 'terminal_resources_complete', False), ('cleanup', 'owned_identities_absent', False)):
            changed = copy.deepcopy(original); changed[group][field] = value
            write(directory/'report.json', changed)
            with self.assertRaises(ValueError): subject.scope_projection(directory, first, [])
        write(directory/'report.json', original)
        (directory/'copied/.gate/scope_preflight.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SCOPE_RETAINED_INPUT_MUTATION'):
            subject.scope_projection(directory, first, [])

    def test_historical_snapshot_mutation_blocks_semantics(self):
        """A PASS header cannot conceal altered registered verifier input bytes."""
        path = self.fixture.root/'semantic/frozen-inputs/0.input'
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'SEMANTIC_SNAPSHOT_MUTATED'): self.fixture.create()

    def test_only_declared_control_fields_are_ignored(self):
        """Explicit physical-root/port/unit/date variation cannot weaken semantic fields."""
        first = subject.load(self.fixture.pairs[0]['f0_manifest'])
        changed = copy.deepcopy(first)
        for key in subject.CONTROL_FIELDS: changed[key] = 'different'
        self.assertEqual(subject.common_identity(first), subject.common_identity(changed))

    def test_recipe_must_identify_exact_baseline(self):
        """A successful recipe from another baseline root is not transferable."""
        pair = self.fixture.pairs[0]
        first, second = subject.load(pair['f0_manifest']), subject.load(pair['f1_manifest'])
        second['f1_recipe']['baseline_input_root_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'RECIPE_BASELINE'):
            subject.check_recipe(first, second, subject.load(pair['recipe_receipt']), subject.digest(subject.HERE/'prepare_f1.py'))

    def test_extra_patch_and_missing_patch_rejected(self):
        """The recipe permits exactly Query source and bytecode, never a third or omitted file."""
        pair = self.fixture.pairs[0]
        for mutation in ('extra', 'missing'):
            first, second = subject.load(pair['f0_manifest']), subject.load(pair['f1_manifest'])
            row = next(row for row in second['files'] if row['path'] == (subject.CLASS if mutation == 'missing' else 'db/schema.sql'))
            row['sha256'] = subject.inventory(first['files'])[subject.CLASS] if mutation == 'missing' else '0'*64
            with self.assertRaisesRegex(ValueError, 'TWO_FILE'):
                subject.check_recipe(first, second, subject.load(pair['recipe_receipt']), subject.digest(subject.HERE/'prepare_f1.py'))

    def test_false_or_missing_recipe_fences(self):
        """Build count, callsites, nonactivation and receipt identity are independent predicates."""
        pair = self.fixture.pairs[0]
        first, second = subject.load(pair['f0_manifest']), subject.load(pair['f1_manifest'])
        for key, value in (('matching_class_builds', True), ('callsites', []), ('production_profile', 'TIER1_ACTIVE'),
                           ('performance_acceptance', 'PASS'), ('input_root_sha256', '0'*64)):
            with self.subTest(key=key):
                receipt = subject.load(pair['recipe_receipt']); receipt[key] = value
                with self.assertRaises(ValueError): subject.check_recipe(first, second, receipt, subject.digest(subject.HERE/'prepare_f1.py'))

    def test_all_three_pairs_required_before_freeze(self):
        """Partial or repeated pair schedules cannot register an experiment."""
        for pairs in (self.fixture.pairs[:2], [self.fixture.pairs[0]]*3):
            with self.assertRaises(ValueError): subject.check_pairs(pairs, self.fixture.source_ready, [])

    def test_frozen_artifact_mutation_is_detected(self):
        """Editing an old report after registration cannot silently replace its authority."""
        value = self.fixture.create()
        path = self.fixture.reports['p1_regressions']; path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'EXPERIMENT_INPUT_MUTATION'): subject.verify_experiment(value)

    def test_unregistered_trial_cannot_use_valid_binding(self):
        """A valid binding does not authorize another profile, pair number or manifest path."""
        value = self.fixture.create()
        with self.assertRaises(ValueError): subject.verify_trial(value, self.fixture.pairs[0]['f0_manifest'], 2, 'F0')

    def test_duplicate_and_unsafe_input_names(self):
        """Artifact labels cannot conceal duplicate definitions or escape copied roots."""
        row = {'path': 'x', 'sha256': '1'*64}
        for rows in ([row, row], [dict(row, path='../x')], [dict(row, path='/x')], []):
            with self.assertRaises(ValueError): subject.inventory(rows)


if __name__ == '__main__':
    unittest.main()
