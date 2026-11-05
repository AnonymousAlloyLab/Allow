"""Read-only replacement guard regressions; no real services/accounts/SQL touched."""
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).absolute().parent

def source(name):
    module = types.ModuleType(name)
    module.__file__ = str(HERE / name)
    exec(compile((HERE / name).read_bytes(), str(HERE / name), 'exec'), module.__dict__)
    return module


guard = source('public_guard.py')


class PublicGuardTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(installation_slot='PUBLIC_REPLACEMENT', access_mode='ANONYMOUS',
                           transport='wsl', backend_port=18081, tunnel_port=18081)
        self.state = dict(LoadState='loaded', ActiveState='inactive', SubState='dead', MainPID='0',
                          UnitFileState='disabled', Job='0', ControlGroup='')
        self.stack = []
        def apply(target, **kwargs):
            mock = patch(target, **kwargs)
            self.stack.append(mock)
            return mock.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.stack)])
        self.account = apply('pwd.getpwnam', side_effect=lambda name: types.SimpleNamespace(pw_uid=1001 if name == 'allow-public' else 1002))
        apply('os.geteuid', return_value=1001)
        apply('pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='test-primary'))
        self.access = apply('os.access', return_value=False)
        p = patch.object(Path, 'lstat', autospec=True, side_effect=lambda path: types.SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o700, st_uid=1001 if path == guard.PUBLIC_ROOT else 1002))
        self.stack.append(p); self.info = p.start()
        p = patch.object(Path, 'resolve', autospec=True, side_effect=lambda path, **kw: path)
        self.stack.append(p); p.start()
        p = patch.object(guard, 'systemd_state', side_effect=lambda: self.state.copy())
        self.stack.append(p); self.metadata = p.start()
        p = patch.object(guard, 'empty_cgroup')
        self.stack.append(p); self.cgroup = p.start()

    def check(self):
        guard.check(self.config, guard.PUBLIC_ROOT)

    def test_positive_and_individual_access_checks(self):
        self.check()
        self.assertEqual([c.args[1] for c in self.access.call_args_list], [os.R_OK, os.W_OK, os.X_OK])
        for call in self.access.call_args_list:
            self.assertEqual(call.kwargs, {'effective_ids': True})

    def test_each_single_access_grant_denies(self):
        for right in (os.R_OK, os.W_OK, os.X_OK):
            with self.subTest(right=right):
                self.access.side_effect = lambda path, mode, **kw: mode == right
                with self.assertRaises(ValueError): self.check()
        self.metadata.assert_not_called()

    def test_every_unsafe_unit_state_denies(self):
        for key, bad in [('LoadState','not-found'),('ActiveState','active'),('SubState','running'),
                         ('MainPID','12'),('UnitFileState','enabled'),('Job','32')]:
            with self.subTest(key=key):
                good = self.state[key]; self.state[key] = bad
                with self.assertRaises(ValueError): self.check()
                self.state[key] = good
        self.cgroup.assert_not_called()

    def test_ambiguous_or_unavailable_metadata_denies(self):
        self.metadata.side_effect = ValueError('unavailable')
        with self.assertRaises(ValueError): self.check()
        self.cgroup.assert_not_called()

    def test_wrong_tuple_and_root_deny_before_observation(self):
        for key, value in [('installation_slot','UNKNOWN'), ('access_mode','PRIVATE'), ('transport','ssh'),
                           ('backend_port',8080), ('tunnel_port',8080)]:
            config = self.config | {key:value}
            with self.assertRaises(ValueError): guard.check(config, guard.PUBLIC_ROOT)
        with self.assertRaises(ValueError): guard.check(self.config, Path('/opt/allow'))
        self.account.assert_not_called()

    def test_wrong_owner_mode_or_link_denies(self):
        for mode, uid in [(stat.S_IFDIR|0o755,1001),(stat.S_IFLNK|0o700,1001),(stat.S_IFDIR|0o700,44)]:
            self.info.side_effect = None
            self.info.return_value = types.SimpleNamespace(st_mode=mode, st_uid=uid)
            with self.assertRaises(ValueError): self.check()
        self.metadata.assert_not_called()

    def test_primary_has_no_observations(self):
        self.account.side_effect = KeyError('allow-public absent')
        guard.check({}, Path('/anywhere'))
        self.metadata.assert_not_called()

    def test_shared_or_root_uid_denies(self):
        for uid in (0,1001):
            self.account.side_effect = lambda name: types.SimpleNamespace(pw_uid=uid)
            with self.assertRaises(ValueError): self.check()
        self.metadata.assert_not_called()


class GuardBoundaryTests(unittest.TestCase):
    def test_cgroup_empty_absent_nested_and_poisoned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mountinfo = root / 'mountinfo'
            mountinfo.write_text(f'1 0 0:1 / {root} rw - cgroup2 cgroup rw\n')
            (root / 'cgroup.controllers').write_text('cpu memory pids\n')
            with patch.object(guard, 'CGROUP_ROOT', root), patch.object(guard, 'MOUNTINFO', mountinfo):
                guard.empty_cgroup('/absent')
                parent = root / 'allow.service'
                parent.mkdir(); (parent / 'cgroup.procs').write_text('')
                guard.empty_cgroup('/allow.service')
                child = parent / 'nested'
                child.mkdir(); (child / 'cgroup.procs').write_text('123\n')
                with self.assertRaises(ValueError): guard.empty_cgroup('/allow.service')
                (child / 'cgroup.procs').write_text('')
                guard.empty_cgroup('/allow.service')
                (child / 'cgroup.procs').unlink()
                (child / 'cgroup.procs').symlink_to(parent / 'cgroup.procs')
                with self.assertRaises(ValueError): guard.empty_cgroup('/allow.service')
                for invalid in ('/', '../bad', '/a/../bad', 'relative'):
                    with self.assertRaises(ValueError): guard.empty_cgroup(invalid)

    def test_missing_unavailable_or_nonunified_mount_cannot_mean_absent_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'cgroup'
            mountinfo = Path(temporary) / 'mountinfo'
            mountinfo.write_text('')
            with patch.object(guard, 'CGROUP_ROOT', root), patch.object(guard, 'MOUNTINFO', mountinfo):
                for group in ('', '/absent'):
                    with self.assertRaises(OSError): guard.empty_cgroup(group)
                root.mkdir()
                for metadata in ('', f'1 0 0:1 / {root} rw - tmpfs tmpfs rw\n',
                                 f'1 0 0:1 / {root} rw - cgroup2 cgroup rw\n'*2):
                    mountinfo.write_text(metadata)
                    with self.assertRaises(ValueError): guard.empty_cgroup('/absent')
                mountinfo.write_text(f'1 0 0:1 / {root} rw - cgroup2 cgroup rw\n')
                with self.assertRaises(OSError): guard.empty_cgroup('/absent')
                (root / 'cgroup.controllers').write_text('cpu memory\n')
                guard.empty_cgroup('/absent')
                mountinfo.unlink()
                with self.assertRaises(OSError): guard.empty_cgroup('/absent')

    def test_denial_precedes_setup_and_service_ownership(self):
        # Reuse source-only fixture support, never imported application bytecode.
        tests = source('test_deployment.py')
        fixture = tests.Fixture()
        self.addCleanup(fixture.close)
        config = {'installation_slot': 'PUBLIC_REPLACEMENT'}
        for module, action in ((fixture.setup, lambda: fixture.setup.initialize(fixture.root, config)),
                               (fixture.service, lambda: fixture.service.serve(config, fixture.root))):
            with patch.object(module.trust, 'public_guard', side_effect=ValueError('denied')), \
                    patch.object(module.trust, 'exclusive') as ownership, \
                    patch.object(module.trust, 'run') as sql:
                with self.assertRaises(ValueError): action()
                ownership.assert_not_called(); sql.assert_not_called()
                self.assertFalse((fixture.root / '.runtime').exists())

    def test_verified_check_entry_rejects_primary_without_runtime(self):
        tests = source('test_deployment.py')
        fixture = tests.Fixture()
        self.addCleanup(fixture.close)
        for name in ('public_guard.py', 'check_public.py'):
            fixture.write('deploy/linux/' + name, (HERE / name).read_bytes())
        fixture.freeze()
        config = fixture.config()
        result = subprocess.run(['/usr/bin/python3','-I','-B',
            str(fixture.root / 'deploy/linux/check_public.py'),'--config',str(config)],
            capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires PUBLIC_REPLACEMENT', result.stderr)
        self.assertFalse((fixture.root / '.runtime').exists())

    def test_primary_cannot_bypass_reserved_root_or_account(self):
        trust = source('trust.py')
        with self.assertRaises(ValueError): trust.public_guard({}, Path('/opt/allow-public'))
        with patch('pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='uid-alias')), \
                patch('pwd.getpwnam', return_value=types.SimpleNamespace(pw_uid=os.geteuid())):
            with self.assertRaises(ValueError): trust.public_guard({}, Path('/tmp/otherwise-primary'))
            with self.assertRaises(ValueError): guard.check({}, Path('/tmp/otherwise-primary'))
        with patch('pwd.getpwnam', side_effect=KeyError('missing')):
            trust.public_guard({}, Path('/tmp/otherwise-primary'))
            guard.check({}, Path('/tmp/otherwise-primary'))
        with self.assertRaises(ValueError): guard.check({}, guard.PUBLIC_ROOT)

    def test_metadata_parser_and_output_bound(self):
        spawn = subprocess.Popen
        good = 'LoadState=loaded\nActiveState=inactive\nSubState=dead\nMainPID=0\nUnitFileState=disabled\nJob=0\nControlGroup=\n'
        for output, valid in ((good,True), (good+'Job=0\n',False),
                              (good.replace('LoadState=loaded\n',''),False), ('x'*17000,False)):
            def child(command, **kwargs):
                self.assertEqual(command[:3], ['/usr/bin/systemctl','show','allow.service'])
                self.assertNotIn('JAVA_TOOL_OPTIONS', kwargs['env'])
                return spawn(['/usr/bin/python3','-I','-B','-c', 'print('+repr(output)+',end="")'], **kwargs)
            with patch.object(guard.subprocess, 'Popen', side_effect=child):
                if valid:
                    self.assertEqual(guard.systemd_state()['Job'], '0')
                else:
                    with self.assertRaises(ValueError): guard.systemd_state()

    def test_config_closed_slot_and_primary_compatibility(self):
        tests = source('test_deployment.py')
        fixture = tests.Fixture()
        self.addCleanup(fixture.close)
        self.assertEqual(fixture.trust.load_config(fixture.config())['installation_slot'], 'PRIMARY')
        for changes in ({'installation_slot': 'unknown'}, {'installation_slot':'PUBLIC_REPLACEMENT'}):
            with self.assertRaises(ValueError): fixture.trust.load_config(fixture.config(**changes))
        config = fixture.trust.load_config(fixture.config(installation_slot='PUBLIC_REPLACEMENT',
            access_mode='ANONYMOUS', transport='wsl', backend_port=18081,tunnel_port=18081))
        self.assertEqual(config['installation_slot'], 'PUBLIC_REPLACEMENT')


if __name__ == '__main__':
    unittest.main()
