"""Focused deployment boundary tests; no SQL, model download or live processes."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import setup
import service

PACKAGE_PATH = HERE.parents[1] / 'scripts/package_iis.py'
spec = importlib.util.spec_from_file_location('package_iis', PACKAGE_PATH)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class Configuration(unittest.TestCase):
    def config(self, directory, **overrides):
        value = {'public_origin': 'https://allow.example.com', 'tunnel_port': 18080,
                 'backend_port': 8080, 'advisory_profile': 'DOCUMENT_ADVISORY_TIER1'}
        value.update(overrides)
        path = Path(directory) / 'instance.json'
        path.write_text(json.dumps(value))
        return path

    def test_closed_config_and_command(self):
        with tempfile.TemporaryDirectory() as temp:
            config = setup.load_config(self.config(temp))
            args = service.command(config, Path('/opt/allow'))
            self.assertIn('--server.address=127.0.0.1', args)
            self.assertIn('--allow.deployment.tunnel-host=127.0.0.1:18080', args)
            self.assertIn('--allow.document.advisory-profile=DOCUMENT_ADVISORY_TIER1', args)
            self.assertNotIn('--allow.worker.pool.enabled=false', args)

    def test_config_rejects_hostile_and_unknown_values(self):
        with tempfile.TemporaryDirectory() as temp:
            for origin in ('http://allow.example.com', 'https://127.0.0.1', 'https://allow.example.com/',
                           'https://allow.example.com:443', 'https://allow.example.com:0444',
                           'https://localhost', 'https://user@allow.example.com', 'https://ALLOW.example.com', 'https://a..com'):
                with self.subTest(origin=origin), self.assertRaises(ValueError):
                    setup.load_config(self.config(temp, public_origin=origin))
            for override in ({'public_origin': None}, {'public_origin': 123}, {'advisory_profile': 'FAST'}, {'backend_port': True}, {'extra': 'secret'}):
                with self.subTest(override=override), self.assertRaises(ValueError):
                    setup.load_config(self.config(temp, **override))

    def test_clean_environment(self):
        with patch.dict(os.environ, {'JAVA_TOOL_OPTIONS': '-agentlib:bad', '_JAVA_OPTIONS': 'bad',
                                    'JDK_JAVA_OPTIONS': 'bad', 'PGHOST': 'bad', 'PYTHONHOME': 'bad'}, clear=True):
            env = setup.environment(Path('/opt/allow'))
            self.assertEqual(env, {'PATH': '/usr/bin:/bin', 'PYTHONPATH': '/opt/allow/retrieval'})

    def test_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            link = Path(temp) / 'linked'
            link.symlink_to('/tmp')
            with self.assertRaises(ValueError):
                setup.no_links(link / 'missing')

    def test_provision_does_not_call_model_bootstrap(self):
        with patch.object(setup.importlib.util, 'module_from_spec') as module, \
                patch.object(setup.importlib.util, 'spec_from_file_location'):
            setup.provision()
            module.return_value.provision_runtime.assert_called_once_with()
            module.return_value.bootstrap.assert_not_called()

    def test_failed_initialization_restores_environment_and_original_error(self):
        with tempfile.TemporaryDirectory() as temp:
            original = dict(os.environ)
            with patch.object(setup, 'ROOT', Path(temp)), \
                    patch.object(setup, 'load_config'), patch.object(setup, 'verify_package'), \
                    patch.object(setup, 'prerequisites'), \
                    patch.object(setup, 'provision', side_effect=ValueError('original initialization failure')), \
                    patch.object(setup, 'run', side_effect=RuntimeError('cleanup failure')), \
                    patch.object(sys, 'argv', ['setup.py', '--config', 'public.json', '--initialize']):
                with self.assertRaisesRegex(ValueError, 'original initialization failure') as caught:
                    setup.main()
                self.assertIn('SQL cleanup also failed: RuntimeError', caught.exception.__notes__)
            self.assertEqual(dict(os.environ), original)

    def test_private_token_file_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'launch.url'
            service.private_write(path, 'https://allow.example.com/#token=private\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.unlink()
            path.symlink_to(Path(temp) / 'victim')
            with self.assertRaises(OSError):
                service.private_write(path, 'secret')


class Packaging(unittest.TestCase):
    def test_sensitive_member_denials(self):
        for name in ('.runtime/database.json', '../escape', '/absolute', 'models/private.pt',
                     'retrieval/checkpoints/state', '.tools/retrieval-venv/bin/python', 'ssh.key'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                package.safe_name(name)
        package.safe_name('.tools/sqlean/sqlean_pg_grammar')

    def test_linked_input_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'file'
            target.write_text('public')
            link = Path(temp) / 'link'
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                package.regular(link)

    def test_actual_archive_manifest_and_private_output(self):
        import hashlib
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'app.py'
            source.write_text('print("public")\n')
            output = root / 'private.zip'
            with patch.object(package, 'collect', return_value={'app.py': source}):
                result = package.build(root, root, root, output)
                self.assertEqual(result['files'], 1)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                with zipfile.ZipFile(output) as archive:
                    manifest = json.loads(archive.read('MANIFEST.json'))
                    self.assertEqual(manifest['files']['app.py'], hashlib.sha256(source.read_bytes()).hexdigest())
                    self.assertEqual(archive.namelist(), ['app.py', 'MANIFEST.json', 'MANIFEST.sha256'])
                with self.assertRaises(ValueError):
                    package.build(root, root, root, output)


if __name__ == '__main__':
    unittest.main()
