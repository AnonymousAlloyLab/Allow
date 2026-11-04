"""Finite negative checks for delegated ownership, exact receipts and fixture routes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import Mock, patch

import containment
import delegation
import probe_results
import scope_launch
import semantic_plan
from harness_common import HERE, read_private, write_private


class DelegationTests(unittest.TestCase):
    """Use inert files to test predicates; no cgroup or process mutation occurs."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.group = self.root/'scope'
        (self.group/'control').mkdir(parents=True)
        (self.group/'cgroup.procs').write_text('')
        (self.group/'cgroup.controllers').write_text('cpu memory pids')
        (self.group/'cgroup.subtree_control').write_text('cpu memory pids')
        self.topology = {'root': delegation.identity(self.group), 'control': delegation.identity(self.group/'control')}
        write_private(self.root/'.gate/delegation-ready.json', self.topology)
        self.config = {'schema': 1, 'cgroupRoot': str(self.group), 'rootDevice': self.group.stat().st_dev,
                       'rootInode': self.group.stat().st_ino}
        write_private(self.root/'.runtime/warm-pool/config.json', self.config)

    def tearDown(self):
        self.temp.cleanup()

    def verify(self, pid_group='/scope/control'):
        with patch.object(containment, 'CGROUP', self.root), patch.object(containment, 'pid_group', return_value=pid_group):
            return delegation.verify(self.root, self.group, {'pid': 123})

    def test_positive_exact_topology(self):
        self.assertEqual(self.verify()['root_processes'], [])

    def test_nonempty_root_rejected(self):
        (self.group/'cgroup.procs').write_text('123')
        with self.assertRaisesRegex(ValueError, 'root_has_processes'):
            self.verify()

    def test_owner_outside_control_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside_control'):
            self.verify('/scope/other')

    def test_missing_delegated_controller_rejected(self):
        (self.group/'cgroup.subtree_control').write_text('memory pids')
        with self.assertRaisesRegex(ValueError, 'controllers_missing'):
            self.verify()

    def test_changed_group_inode_rejected(self):
        topology = dict(self.topology, root=dict(self.topology['root'], inode=0))
        with patch.object(delegation, 'read_private', return_value=topology):
            with self.assertRaisesRegex(ValueError, 'identity_changed'):
                self.verify()

    def test_boolean_schema_is_not_integer_one(self):
        original = delegation.read_private
        with patch.object(delegation, 'read_private', side_effect=lambda p: dict(self.config, schema=True)
                          if p.name == 'config.json' else original(p)):
            with self.assertRaisesRegex(ValueError, 'config_mismatch'):
                self.verify()

    def test_scope_properties_explicit_delegation_and_same_budgets(self):
        properties = scope_launch.properties(240)
        self.assertIn('Delegate=yes', properties)
        self.assertIn('CPUQuota=400%', properties)
        self.assertIn('MemoryMax=6442450944', properties)
        self.assertIn('MemoryHigh=5368709120', properties)
        self.assertFalse(any(p.startswith(('CPUAffinity=', 'Restart=', 'RemainAfterExit=')) for p in properties))


class ReceiptTests(unittest.TestCase):
    """Never translate UNKNOWN, a stale PID, or a malformed success into release."""

    def setUp(self):
        self.ownership = patch.object(probe_results, 'ownership_receipt', return_value=None)
        self.ownership.start()
        self.addCleanup(self.ownership.stop)
        self.item = {'id': 'normal-cold', 'kind': 'COLD_ONE_USE', 'expected_cleanup': 'PASS',
                     'expected_capacity_retained': False}
        self.result = {'id': 'normal-cold', 'status': 'PASS', 'classification': 'COLD_ONE_USE',
                       'cleanup': {'status': 'PASS', 'capacityRetained': False, 'directChildReaped': True,
                                   'populatedZero': True}, 'identities': [{'pid': 999999999, 'start_ticks': '1'}], 'evidence': []}

    def check(self):
        return probe_results.case_result(Path('/tmp/no-evidence'), self.item, self.result)

    def test_complete_receipt(self):
        self.assertEqual(self.check()['status'], 'PASS')

    def test_missing_positive_empty(self):
        self.result['cleanup']['populatedZero'] = False
        with self.assertRaisesRegex(ValueError, 'positive_empty'):
            self.check()

    def test_integer_is_not_boolean_reap(self):
        self.result['cleanup']['directChildReaped'] = 1
        with self.assertRaisesRegex(ValueError, 'unreaped'):
            self.check()

    def test_still_owned_process_rejected(self):
        with patch.object(probe_results, 'same_process', return_value=True):
            with self.assertRaisesRegex(ValueError, 'still_alive'):
                self.check()

    def test_actual_worker_identity_required(self):
        self.result['identities'] = []
        with self.assertRaisesRegex(ValueError, 'actual_worker'):
            self.check()

    def test_unknown_cannot_release_slot(self):
        self.item.update(id='postattach-unknown', kind='UNKNOWN_CAPACITY_RETAINED', expected_cleanup='UNKNOWN', expected_capacity_retained=True)
        self.result.update(id=self.item['id'], classification=self.item['kind'])
        self.result['cleanup'].update(status='UNKNOWN', populatedZero=False)
        with self.assertRaisesRegex(ValueError, 'capacity_release'):
            self.check()
        self.result['cleanup']['capacityRetained'] = True
        self.assertEqual(self.check()['status'], 'PASS')

    def test_wrong_classification_rejected(self):
        self.result['classification'] = 'UNAVAILABLE'
        with self.assertRaisesRegex(ValueError, 'wrong_classification'):
            self.check()

    def test_parent_path_evidence_rejected(self):
        self.result['evidence'] = [{'path': '../other', 'sha256': '0'*64}]
        with self.assertRaisesRegex(ValueError, 'evidence_path'):
            self.check()

    def test_stop5_without_positive_empty_is_unknown(self):
        self.assertFalse(containment.removed_after_empty(False, True, 5, {'LoadState': 'not-found'}))
        self.assertFalse(containment.removed_after_empty(True, False, 5, {'LoadState': 'not-found'}))
        self.assertFalse(containment.removed_after_empty(True, True, 1, {'LoadState': 'not-found'}))
        self.assertTrue(containment.removed_after_empty(True, True, 5, {'LoadState': 'not-found'}))

    def test_missing_oom_counter_cannot_count_as_zero(self):
        with self.assertRaisesRegex(ValueError, 'counter_missing'):
            containment.exhausted({'metrics': {'memory.events': 'oom 0\noom_kill 0', 'pids.events': 'max 0'}})


class StartingShutdownReceiptTests(unittest.TestCase):
    """Reject false STARTING coverage and cleanup summaries detached from the actual generation."""

    def setUp(self):
        self.identity = {'pid': 999999999, 'start_ticks': '123'}
        self.result = {'identities': [self.identity]}
        self.value = {'shutdownBarrier': 'GATE_MONITOR_BARRIER_BEFORE_LEDGER_READY_PUBLICATION',
                      'phaseAtCloseEntry': 'STARTING', 'rawReadyEmission': 'NOT_ASSERTED',
                      'attachedBeforeClose': True, 'noPrivateHandoff': True,
                      'poolClosedObservedWhileStarting': True, 'standbyMonitorHeldAtObservation': True,
                      'closeThreadJoined': True, 'closeThreadFailed': False, 'remainingReservations': 0,
                      'startingChildPid': self.identity['pid'], 'startingChildStartTicks': '123',
                      'groups': [{'pid': self.identity['pid'], 'startTicks': '123', 'directChildReaped': True,
                                  'exitCode': 137, 'finalPhase': 'RELEASED'}]}

    def check(self):
        probe_results.starting_shutdown_receipt(self.value, self.result)

    def test_exact_starting_shutdown_observation(self):
        self.check()

    def test_ready_or_unheld_observation_cannot_claim_starting_coverage(self):
        for field, wrong in [('phaseAtCloseEntry', 'READY'), ('shutdownBarrier', 'UNCONTROLLED_SAMPLE'),
                             ('rawReadyEmission', 'ASSERTED_NO_READY')]:
            with self.subTest(field=field):
                changed = dict(self.value, **{field: wrong})
                with self.assertRaises(ValueError):
                    probe_results.starting_shutdown_receipt(changed, self.result)

    def test_each_required_witness_is_a_true_boolean(self):
        for field in ('attachedBeforeClose', 'noPrivateHandoff', 'poolClosedObservedWhileStarting',
                      'standbyMonitorHeldAtObservation', 'closeThreadJoined'):
            for wrong in (False, 1):
                with self.subTest(field=field, wrong=wrong):
                    with self.assertRaises(ValueError):
                        probe_results.starting_shutdown_receipt(dict(self.value, **{field: wrong}), self.result)

    def test_uncertain_or_unreaped_generation_cannot_pass(self):
        for field, wrong in [('finalPhase', 'UNKNOWN'), ('directChildReaped', False), ('exitCode', True)]:
            changed = copy.deepcopy(self.value)
            changed['groups'][0][field] = wrong
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    probe_results.starting_shutdown_receipt(changed, self.result)

    def test_changed_or_unbound_child_is_rejected(self):
        for field, wrong in [('startingChildPid', True), ('startingChildPid', 123), ('startingChildStartTicks', '124')]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    probe_results.starting_shutdown_receipt(dict(self.value, **{field: wrong}), self.result)
        self.result['identities'] = []
        with self.assertRaises(ValueError):
            self.check()

    def test_extra_generation_or_child_cannot_be_ignored(self):
        self.value['groups'].append(dict(self.value['groups'][0]))
        with self.assertRaises(ValueError):
            self.check()
        self.value['groups'].pop()
        self.result['identities'].append({'pid': 999999998, 'start_ticks': '456'})
        with self.assertRaises(ValueError):
            self.check()

    def test_close_failure_or_retained_capacity_is_blocking(self):
        for field, wrong in [('closeThreadFailed', True), ('closeThreadFailed', 0),
                             ('remainingReservations', 1), ('remainingReservations', False)]:
            with self.subTest(field=field, wrong=wrong):
                with self.assertRaises(ValueError):
                    probe_results.starting_shutdown_receipt(dict(self.value, **{field: wrong}), self.result)


class SemanticPlanTests(unittest.TestCase):
    """The old fixture bytes are reused with explicit operation-specific routes."""

    def test_exact190_source_bound_routes(self):
        self.assertEqual(semantic_plan.verify(HERE)['operations'], {'VALIDATE': 153, 'REVALIDATE': 37})

    def test_revalidation_cannot_use_warm_entrypoint(self):
        plan = copy.deepcopy(read_private(HERE/'semantic-fixtures.json'))
        next(row for row in plan['fixtures'] if row['operation'] == 'REVALIDATE')['W1_route'] = 'warm-advisory'
        with patch.object(semantic_plan, 'read_private', return_value=plan):
            with self.assertRaisesRegex(ValueError, 'fixture_route'):
                semantic_plan.verify(HERE)

    def test_mutated_fixture_digest_rejected(self):
        plan = copy.deepcopy(read_private(HERE/'semantic-fixtures.json'))
        plan['fixtures'][0]['sha256'] = '0'*64
        with patch.object(semantic_plan, 'read_private', return_value=plan):
            with self.assertRaisesRegex(ValueError, 'fixture_identity'):
                semantic_plan.verify(HERE)

    def test_empty_probe_plan_cannot_pass_vacuously(self):
        with self.assertRaisesRegex(ValueError, 'nonempty_cases'):
            probe_results.check_plan(HERE, {'cases': []})

    def test_concrete_probe_cases_bind_fixtures(self):
        self.assertEqual(len(probe_results.check_plan(HERE, read_private(HERE/'probe-cases.json'))), 11)


class GroupReceiptTests(unittest.TestCase):
    """Reparse raw terminal counter text instead of trusting a probe summary flag."""

    def setUp(self):
        self.nonce = '00000000-0000-4000-8000-000000000001'
        self.config = {'cgroupRoot': '/sys/fs/cgroup/private.scope', 'rootDevice': 30}
        self.group = {'slot': 0, 'generation': 1, 'group': 'pool-'+self.nonce+'/slot-0-g1', 'device': 30, 'inode': 123,
                      'terminalCounters': {'cgroup.events': 'populated 0\nfrozen 0', 'memory.peak': '1234',
                      'memory.events': 'oom 0\noom_kill 0\noom_group_kill 0', 'pids.peak': '12',
                      'pids.events': 'max 0', 'cpu.stat': 'usage_usec 12'}}

    def test_exact_terminal_receipt(self):
        probe_results.group_receipt(self.group, self.nonce, self.config)

    def test_populated_group_rejected(self):
        self.group['terminalCounters']['cgroup.events'] = 'populated 1\nfrozen 0'
        with self.assertRaisesRegex(ValueError, 'terminal_empty'):
            probe_results.group_receipt(self.group, self.nonce, self.config)

    def test_oom_cannot_be_hidden_by_summary(self):
        self.group['terminalCounters']['memory.events'] = 'oom 1\noom_kill 0\noom_group_kill 0'
        with self.assertRaisesRegex(ValueError, 'exhaustion'):
            probe_results.group_receipt(self.group, self.nonce, self.config)

    def test_counter_boolean_rejected(self):
        self.group['terminalCounters']['memory.peak'] = True
        with self.assertRaisesRegex(ValueError, 'counter_schema'):
            probe_results.group_receipt(self.group, self.nonce, self.config)

    def test_wrong_generation_group_rejected(self):
        self.group['generation'] = 2
        with self.assertRaisesRegex(ValueError, 'group_identity'):
            probe_results.group_receipt(self.group, self.nonce, self.config)


class ControllerHelperReapTests(unittest.TestCase):
    """A stalled outside systemctl child never leaks or becomes a successful cleanup."""

    def child(self):
        child = Mock(pid=123, returncode=-9)
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('owned-systemctl', 3), -9]
        return child

    def test_stalled_signal_is_forcibly_reaped_without_promoting_pass(self):
        child = self.child()
        with patch.object(containment.subprocess, 'Popen', return_value=child), \
                patch.object(containment, 'user_manager_environment', return_value={}), \
                patch.object(containment, 'observe_stop_command', return_value={'status': 'PASS', 'graceful_kill_exit_code': None}):
            report = containment.stop_observed({'unit': 'owned.scope'}, [], {})
        self.assertEqual(report['status'], 'UNKNOWN')
        self.assertIsNone(report['graceful_kill_exit_code'])
        self.assertIsNone(report['control_command_cleanup']['original_exit_code'])
        self.assertTrue(report['control_command_cleanup']['forced'])
        self.assertTrue(report['control_command_cleanup']['reaped'])
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)

    def test_observer_exception_still_stops_unit_and_reaps_helper(self):
        child = self.child()
        with patch.object(containment.subprocess, 'Popen', return_value=child), \
                patch.object(containment, 'user_manager_environment', return_value={}), \
                patch.object(containment.subprocess, 'run', return_value=Mock(returncode=0)) as stop, \
                patch.object(containment, 'observe_stop_command', side_effect=ValueError('counter fixture')):
            report = containment.stop_observed({'unit': 'owned.scope'}, [], {})
        self.assertEqual(report['status'], 'UNKNOWN')
        self.assertEqual(report['observation_failure_class'], 'ValueError')
        self.assertEqual(report['emergency_stop_exit_code'], 0)
        stop.assert_called_once()
        child.kill.assert_called_once()

    def test_unit_stop_timeout_preserves_failure_and_still_reaps_helper(self):
        child = self.child()
        def failure(_manifest, _owned, _descriptors, _child, progress):
            progress['stop_attempted'] = True
            raise subprocess.TimeoutExpired('systemctl stop', 22)
        with patch.object(containment.subprocess, 'Popen', return_value=child), \
                patch.object(containment, 'user_manager_environment', return_value={}), \
                patch.object(containment.subprocess, 'run') as stop, \
                patch.object(containment, 'observe_stop_command', side_effect=failure):
            report = containment.stop_observed({'unit': 'owned.scope'}, [], {})
        self.assertEqual(report['status'], 'UNKNOWN')
        self.assertEqual(report['observation_failure_class'], 'TimeoutExpired')
        stop.assert_not_called()
        child.kill.assert_called_once()

    def test_already_finished_helper_is_not_signalled(self):
        child = Mock(pid=123, returncode=0)
        child.poll.return_value = 0
        result = containment.reap_control_command(child)
        self.assertFalse(result['forced'])
        self.assertTrue(result['reaped'])
        child.terminate.assert_not_called()
        child.kill.assert_not_called()


if __name__ == '__main__':
    unittest.main()
