"""Security regressions using tiny owned fixtures: no SQL, models or active backend."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import zipfile

REPO = Path(__file__).absolute().parents[2]


def source_module(path, name):
    """Load test subjects directly from source without consuming test bytecode."""
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


package = source_module(REPO / 'scripts/package_iis.py', 'package_iis_tests')
trust_source = REPO / 'deploy/linux/trust.py'


class Fixture:
    """Create a small checksum-complete installation with a fake never-run parser."""
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='allow-')
        self.root = Path(self.temporary.name)
        names = ('deploy/linux/setup.py', 'deploy/linux/service.py', 'deploy/linux/trust.py',
                 'scripts/warm_worker_image.py')
        for name in names:
            self.write(name, (REPO / name).read_bytes())
        self.write('.tools/sqlean/sqlean_pg_grammar', b'never executed fixture parser')
        parser = self.root / '.tools/sqlean/sqlean_pg_grammar'
        self.write('config/sqlean-parser-lock.json', json.dumps({'binary_sha256': self.hash(parser)}).encode())
        self.write('retrieval/allow_retrieval/__init__.py', b'')
        self.write('retrieval/allow_retrieval/common.py', b'FIXTURE = True\n')
        self.freeze()
        self.trust = source_module(self.root / 'deploy/linux/trust.py', 'fixture_trust')
        self.setup = source_module(self.root / 'deploy/linux/setup.py', 'fixture_setup')
        self.service = source_module(self.root / 'deploy/linux/service.py', 'fixture_service')

    def write(self, name, content, mode=0o644):
        """Write protected fixture files without relying on inherited umask."""
        path = self.root / name
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        for parent in path.parents:
            if parent == self.root:
                break
            parent.chmod(0o700)
        path.write_bytes(content)
        path.chmod(mode)
        return path

    def hash(self, path):
        """Hash one small fixture input."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def freeze(self):
        """Freeze current source bytes, excluding generated manifest companions."""
        files = {str(p.relative_to(self.root)): self.hash(p) for p in self.root.rglob('*')
                 if p.is_file() and p.name not in ('MANIFEST.json', 'MANIFEST.sha256')}
        raw = json.dumps({'schema': 1, 'files': files}).encode()
        self.write('MANIFEST.json', raw)
        self.write('MANIFEST.sha256', hashlib.sha256(raw).hexdigest().encode())

    def config(self, **overrides):
        """Create the sole declared private instance configuration."""
        value = {'public_origin': 'https://allow.example.com', 'tunnel_port': 18080,
                 'backend_port': 8080, 'advisory_profile': 'DOCUMENT_ADVISORY_TIER1'}
        value.update(overrides)
        return self.write('deploy/instance.json', json.dumps(value).encode(), 0o600)

    def invoke(self, entry='service.py', flags=('-I', '-B')):
        """Run only entry verification/help, never service lifecycle or prerequisites."""
        return subprocess.run(['/usr/bin/python3', *flags, str(self.root / 'deploy/linux' / entry), '--help'],
                              capture_output=True, text=True, cwd=self.root, timeout=10)

    def close(self):
        """Remove only this test fixture."""
        self.temporary.cleanup()


class DeploymentTests(unittest.TestCase):
    """Exercise actual entrypoints and lifecycle gates with side effects mocked."""
    def test_ai_configuration_requires_private_and_closed_settings(self):
        """Default OFF needs no runtime; anonymous AI and incomplete remote fail."""
        self.assertEqual(self.f.trust.load_config(self.f.config()).get('ai_mode', 'OFF'), 'OFF')
        path = self.f.config(ai_mode='FIXTURE', ai_ledger='/tmp/ai-private-ledger')
        self.assertEqual(self.f.trust.load_config(path)['ai_mode'], 'FIXTURE')
        path = self.f.config(access_mode='ANONYMOUS', ai_mode='FIXTURE', ai_ledger='/tmp/ai-ledger')
        with self.assertRaises(ValueError):
            self.f.trust.load_config(path)
        path = self.f.config(ai_mode='REMOTE_ASSISTED', ai_ledger='/tmp/ai-ledger')
        with self.assertRaises(ValueError):
            self.f.trust.load_config(path)

    def setUp(self):
        """Allocate an independent manifest-complete fixture."""
        self.f = Fixture()
        self.addCleanup(self.f.close)

    def test_positive_package_and_isolated_entry(self):
        """Both isolated trusted entrypoints accept unchanged protected inputs."""
        self.f.trust.verify_package(self.f.root)
        for name in ('setup.py', 'service.py'):
            result = self.f.invoke(name)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_unisolated_guard_precedes_shadow_module(self):
        """The entry guard imports no local standard-library shadow before rejecting."""
        sentinel = self.f.root / 'executed'
        self.f.write('deploy/linux/json.py', f'open({str(sentinel)!r}, "w").write("bad")\n'.encode())
        for flags in ((), ('-B',), ('-I',)):
            result = self.f.invoke(flags=flags)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Invoke with /usr/bin/python3 -I -B', result.stderr)
        self.assertFalse(sentinel.exists())

    def test_isolated_shadow_rejected_without_execution(self):
        """A local shadow module never runs and is rejected by closed inventory."""
        sentinel = self.f.root / 'executed'
        for name in ('deploy/linux/json.py', 'scripts/types.py', 'retrieval/json.py'):
            path = self.f.write(name, f'open({str(sentinel)!r}, "w").write("bad")\n'.encode())
            result = self.f.invoke()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unlisted application/bootstrap input', result.stderr)
            self.assertFalse(sentinel.exists())
            path.unlink()

    def test_timestamp_and_unchecked_bytecode_never_execute(self):
        """Poison valid import caches without modifying the manifested source bytes."""
        sentinel = self.f.root / 'executed'
        attacker = self.f.root / 'attacker.txt'
        attacker.write_text(f'open({str(sentinel)!r}, "w").write("bad")\n')
        for target in ('deploy/linux/trust.py', 'retrieval/allow_retrieval/common.py'):
            source = self.f.root / target
            original = source.read_bytes()
            cache = Path(importlib.util.cache_from_source(str(source)))
            cache.parent.mkdir(mode=0o700, exist_ok=True)
            for mode in (py_compile.PycInvalidationMode.TIMESTAMP, py_compile.PycInvalidationMode.UNCHECKED_HASH):
                py_compile.compile(str(attacker), cfile=str(cache), invalidation_mode=mode, doraise=True)
                if mode == py_compile.PycInvalidationMode.TIMESTAMP:
                    content = cache.read_bytes()
                    header = struct.pack('<II', int(source.stat().st_mtime), source.stat().st_size)
                    cache.write_bytes(content[:8] + header + content[16:])
                result = self.f.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('bytecode/cache is forbidden', result.stderr)
                self.assertFalse(sentinel.exists())
                self.assertEqual(source.read_bytes(), original)
            cache.unlink()
            cache.parent.rmdir()

    def test_unlisted_native_and_configuration_rejected(self):
        """Inventory closes deployment and retrieval roots, not only module packages."""
        for name in ('deploy/plugin.so', 'retrieval/extra.json', 'deploy/linux/x.pyo'):
            path = self.f.write(name, b'extra')
            with self.assertRaises(ValueError):
                self.f.trust.verify_package(self.f.root)
            path.unlink()

    def test_permissions_owner_and_symlinks(self):
        """Writable roots/files, foreign owners and linked inputs fail before helpers."""
        self.f.root.chmod(0o775)
        with self.assertRaisesRegex(ValueError, 'Writable'):
            self.f.trust.verify_package(self.f.root)
        self.f.root.chmod(0o700)
        target = self.f.root / 'retrieval/allow_retrieval/common.py'
        target.chmod(0o666)
        with self.assertRaisesRegex(ValueError, 'Writable'):
            self.f.trust.verify_package(self.f.root)
        target.chmod(0o644)
        with patch.object(self.f.trust.os, 'geteuid', return_value=os.geteuid() + 10000):
            with self.assertRaises(ValueError):
                self.f.trust.checked_path(self.f.root, install=True)
        target.unlink()
        target.symlink_to('/etc/hosts')
        with self.assertRaises(ValueError):
            self.f.trust.verify_package(self.f.root)

    def test_private_configuration_and_closed_values(self):
        """Canonical settings require service-owned private ordinary files."""
        path = self.f.config()
        config = self.f.trust.load_config(path)
        self.assertIn('--server.address=127.0.0.1', self.f.service.command(config))
        for override in ({'public_origin': 'https://localhost'}, {'public_origin': None},
                         {'advisory_profile': 'FAST'}, {'backend_port': True}, {'extra': 'secret'},
                         {'access_mode': 'PUBLIC'}, {'transport': 'mirrored'}, {'transport': 'wsl'}):
            with self.assertRaises(ValueError):
                self.f.trust.load_config(self.f.config(**override))
        public = self.f.trust.load_config(self.f.config(access_mode='ANONYMOUS', transport='wsl', backend_port=18081, tunnel_port=18081))
        self.assertIn('--allow.access-mode=ANONYMOUS', self.f.service.command(public))
        self.assertIn('--allow.access-mode=PRIVATE', self.f.service.command(config))
        path = self.f.config()
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'Private'):
            self.f.trust.load_config(path)

    def test_public_transport_is_bounded_without_changing_private_defaults(self):
        """Closed public transport bounds supplement global and per-workspace admission."""
        private = self.f.trust.load_config(self.f.config())
        public = dict(private, access_mode='ANONYMOUS')
        self.assertEqual(self.f.service.public_transport_bounds(private), [])
        command = self.f.service.command(public)
        for option in ('--server.tomcat.threads.max=16', '--server.tomcat.max-connections=64',
                       '--server.tomcat.accept-count=16', '--server.tomcat.connection-timeout=5s',
                       '--server.tomcat.keep-alive-timeout=5s', '--server.max-http-request-header-size=16KB'):
            self.assertIn(option, command)

    def test_public_supervisor_never_publishes_private_launch_authority(self):
        """Public mode supplies only an unused private constructor token, never a launch file."""
        runtime = self.f.trust.private_runtime(self.f.root)
        for mode in ('PRIVATE', 'ANONYMOUS'):
            config = self.f.trust.load_config(self.f.config(access_mode=mode))
            backend = Mock()
            backend.wait.return_value = 0
            backend.poll.return_value = 0
            with patch.object(self.f.service.signal, 'signal'), \
                    patch.object(self.f.service.trust, 'run') as sql, \
                    patch.object(self.f.service.trust, 'private_write', wraps=self.f.trust.private_write) as write, \
                    patch.object(self.f.service.subprocess, 'Popen', return_value=backend) as popen:
                self.assertEqual(self.f.service.supervise(config, self.f.root, runtime), 0)
                self.assertEqual(write.call_count, 1 if mode == 'PRIVATE' else 0)
                self.assertEqual(len(popen.call_args.kwargs['env']['ALLOW_TOKEN']), 43)
                self.assertEqual([call.args[1] for call in sql.call_args_list], ['start', 'stop'])
            self.assertFalse((runtime / 'launch.url').exists())

    def test_ai_supervisor_disables_core_dumps_before_launch(self):
        """The credential-bearing backend inherits a zero core-dump limit."""
        config = self.f.trust.load_config(self.f.config(ai_mode='FIXTURE', ai_ledger='/tmp/fixture-ledger'))
        runtime = self.f.trust.private_runtime(self.f.root)
        backend = Mock()
        backend.wait.return_value = 0
        backend.poll.return_value = 0
        events = []
        with patch.object(self.f.service.signal, 'signal'), \
                patch.object(self.f.service.resource, 'setrlimit', side_effect=lambda *args: events.append(('limit', args))), \
                patch.object(self.f.service.trust, 'run'), \
                patch.object(self.f.service.subprocess, 'Popen', side_effect=lambda *a, **kw: events.append(('spawn',)) or backend):
            self.assertEqual(self.f.service.supervise(config, self.f.root, runtime), 0)
        self.assertEqual(events[0], ('limit', (self.f.service.resource.RLIMIT_CORE, (0, 0))))
        self.assertEqual(events[1], ('spawn',))

    def test_ai_supervisor_refuses_launch_if_core_limit_fails(self):
        """Failure to disable dumps cannot launch the backend or SQL helpers."""
        config = self.f.trust.load_config(self.f.config(ai_mode='FIXTURE', ai_ledger='/tmp/fixture-ledger'))
        with patch.object(self.f.service.resource, 'setrlimit', side_effect=OSError('denied')), \
                patch.object(self.f.service.trust, 'run') as sql, \
                patch.object(self.f.service.subprocess, 'Popen') as popen:
            with self.assertRaises(OSError):
                self.f.service.supervise(config, self.f.root, self.f.root)
        sql.assert_not_called()
        popen.assert_not_called()

    def test_clean_subprocess_environment_and_bytecode_flags(self):
        """Application helpers cannot inherit JVM/Python overrides or emit bytecode."""
        with patch.dict(os.environ, {'JAVA_TOOL_OPTIONS': 'bad', 'PYTHONHOME': 'bad', 'PGHOST': 'bad'}, clear=True):
            env = self.f.trust.environment(self.f.root)
            self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')
            self.assertEqual(env['PYTHONNOUSERSITE'], '1')
            self.assertNotIn('JAVA_TOOL_OPTIONS', env)
            with patch.object(self.f.trust.subprocess, 'run') as call:
                self.f.trust.run('scripts/bootstrap_corpus.py', 'status', root=self.f.root)
                self.assertEqual(call.call_args.args[0][1:3], ['-B', '-s'])

    def test_prerequisite_processes_cannot_inherit_java_agents(self):
        """Even preflight Java/bubblewrap commands receive the fixed clean env."""
        completed = subprocess.CompletedProcess([], 0, stdout='', stderr='openjdk version "17.0.1"')
        with patch.dict(os.environ, {'JAVA_TOOL_OPTIONS': '-javaagent:sentinel.jar',
                                    'JDK_JAVA_OPTIONS': '-javaagent:sentinel.jar', '_JAVA_OPTIONS': 'bad'}, clear=True), \
                patch.object(self.f.trust.subprocess, 'run', return_value=completed) as run, \
                patch.object(self.f.trust.shutil, 'which', return_value='/usr/bin/tool'), \
                patch.object(Path, 'read_text', return_value='ID=ubuntu\nVERSION_ID="24.04"\n'):
            self.f.trust.prerequisites(self.f.root)
            self.assertEqual(run.call_count, 2)
            for call in run.call_args_list:
                self.assertFalse({'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS'} & call.kwargs['env'].keys())

    def test_fresh_old_tools_never_execute(self):
        """Old generated tools cause refusal before provision, SQL or cleanup effects."""
        for name in ('.tools/retrieval-venv', '.tools/retrieval', '.tools/retrieval-downloads'):
            path = self.f.root / name
            path.mkdir(mode=0o700)
            with patch.object(self.f.setup, 'provision') as provision, patch.object(self.f.setup.trust, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'existing generated tools'):
                    self.f.setup.initialize(self.f.root)
                provision.assert_not_called()
                run.assert_not_called()
            path.rmdir()

    def test_competing_supervisor_and_initializer_have_zero_effects(self):
        """An actual held flock denies whole lifecycle entry, including cleanup."""
        with self.f.trust.exclusive(self.f.root):
            for subject, action in ((self.f.service, lambda: self.f.service.serve({}, self.f.root)),
                                    (self.f.setup, lambda: self.f.setup.initialize(self.f.root))):
                with patch.object(subject.trust, 'run') as run, patch.object(subject.trust, 'private_write') as write, \
                        patch.object(self.f.service.subprocess, 'Popen') as popen:
                    with self.assertRaises(BlockingIOError):
                        action()
                    run.assert_not_called()
                    write.assert_not_called()
                    popen.assert_not_called()
        self.assertTrue((self.f.root / '.runtime/deployment.lock').is_file())

    def test_lock_and_token_hardlinks_and_modes(self):
        """Private authority/lock files reject symlinks, hardlinks and broad modes."""
        runtime = self.f.trust.private_runtime(self.f.root)
        token = runtime / 'launch.url'
        self.f.trust.private_write(token, 'private')
        self.assertEqual(token.stat().st_mode & 0o777, 0o600)
        os.link(token, runtime / 'alias')
        with self.assertRaises(ValueError):
            self.f.trust.private_write(token, 'replacement')
        self.assertEqual(token.read_text(), 'private')
        (runtime / 'alias').unlink()
        token.unlink()
        token.symlink_to(runtime / 'victim')
        with self.assertRaises(ValueError):
            self.f.trust.private_write(token, 'replacement')
        token.unlink()
        lock = self.f.write('.runtime/deployment.lock', b'', 0o644)
        with self.assertRaises(ValueError):
            with self.f.trust.exclusive(self.f.root):
                self.fail('Unsafe lock was acquired')

    def test_generated_dependency_links_are_constrained(self):
        """Only normal managed interpreter and internal lib links are trusted."""
        directory = self.f.root / '.tools/retrieval-venv'
        (directory / 'bin').mkdir(parents=True, mode=0o700)
        directory.chmod(0o700)
        link = directory / 'bin/python'
        link.symlink_to('/usr/bin/python3')
        self.f.trust.generated_link(link, directory, 'venv')
        link.unlink()
        link.symlink_to('/usr/bin/true')
        with self.assertRaises(ValueError):
            self.f.trust.generated_link(link, directory, 'venv')

    def test_source_provisioning_never_requests_model_bootstrap(self):
        """Initialization calls only the verified dependency provisioner."""
        with patch.object(self.f.setup.trust, 'load_source') as source:
            self.f.setup.provision(self.f.root)
            source.return_value.provision_runtime.assert_called_once_with()
            source.return_value.bootstrap.assert_not_called()

    def test_failed_initialization_preserves_error_and_environment(self):
        """A cleanup failure cannot mask initialization failure or retain polluted env."""
        original = dict(os.environ)
        with patch.object(self.f.setup, 'provision', side_effect=ValueError('original failure')), \
                patch.object(self.f.setup.trust, 'run', side_effect=RuntimeError('cleanup failed')):
            with self.assertRaisesRegex(ValueError, 'original failure') as caught:
                self.f.setup.initialize(self.f.root)
            self.assertIn('SQL cleanup also failed: RuntimeError', caught.exception.__notes__)
        self.assertEqual(dict(os.environ), original)

    def test_preserved_store_is_not_reinitialized(self):
        """A valid private retained-store marker preserves existing credentials/state."""
        runtime = self.f.trust.private_runtime(self.f.root)
        self.f.trust.private_write(runtime / 'deployment-initialized.json',
                                 json.dumps({'schema': 1, 'empty_private_store_initialized': True}))
        with patch.object(self.f.setup, 'provision') as provision, patch.object(self.f.setup.trust, 'run') as run:
            self.f.setup.initialize(self.f.root)
            provision.assert_not_called()
            run.assert_not_called()


class PackagingTests(unittest.TestCase):
    """Check actual archive contents, normalized modes and private output files."""
    def test_sensitive_member_denials(self):
        """Never admit runtime, credentials, cached code or learned checkpoints."""
        for name in ('.runtime/database.json', '../escape', '/absolute', 'models/private.pt',
                     '.tools/retrieval-venv/bin/python', 'ssh.key', '__pycache__/x.pyc'):
            with self.assertRaises(ValueError):
                package.safe_name(name)

    def test_archive_manifest_and_normalized_modes(self):
        """Actual zip metadata ignores permissive source modes and freezes file hashes."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'app.py'
            source.write_text('public')
            source.chmod(0o777)
            output = root / 'private.zip'
            members = {'app.py': source, '.tools/sqlean/sqlean_pg_grammar': source}
            with patch.object(package, 'collect', return_value=members):
                package.build(root, root, root, output)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                with zipfile.ZipFile(output) as archive:
                    manifest = json.loads(archive.read('MANIFEST.json'))
                    self.assertEqual(manifest['access_modes'], ['PRIVATE', 'ANONYMOUS'])
                    self.assertEqual(manifest['native_target_acceptance'], 'OPEN')
                    self.assertIn('Private-transfer', manifest['scope'])
                    self.assertEqual(manifest['files']['app.py'], hashlib.sha256(source.read_bytes()).hexdigest())
                    for info in archive.infolist():
                        expected = 0o755 if info.filename.endswith('sqlean_pg_grammar') else 0o644
                        self.assertEqual((info.external_attr >> 16) & 0o777, expected)


if __name__ == '__main__':
    unittest.main()
