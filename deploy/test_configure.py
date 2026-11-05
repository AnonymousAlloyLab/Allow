"""Check generated routing, resource limits and configuration rejection boundaries."""
import argparse
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import xml.etree.ElementTree as ET
import configure


class ConfigurationTest(unittest.TestCase):
    """Exercise deployment outputs without IIS installation or live networking."""

    def test_exact_origin_domain(self):
        """Only canonical HTTPS DNS authorities enter generated configuration."""
        for value in ['https://allow.example.com', 'https://allow.example.com:8443']:
            self.assertEqual(configure.origin(value), value)
        for value in ['http://allow.example.com', 'https://allow.example.com/',
                      'https://ALLOW.example.com', 'https://allow.example.com:443',
                      'https://127.0.0.1', 'https://a@allow.example.com',
                      'https://allow.example.com?x=y', 'https://allow.example.com:99999']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                configure.origin(value)

    def test_proxy_preserves_authority_headers(self):
        """Rules reject wrong authority before a fixed destination without token injection."""
        xml = configure.web_config('https://allow.example.com', 18081)
        root = ET.fromstring(xml)
        rules = root.findall('./system.webServer/rewrite/rules/rule')
        self.assertEqual(len(rules), 3)
        self.assertEqual([r.find('action').get('type') for r in rules], ['CustomResponse', 'CustomResponse', 'Rewrite'])
        self.assertEqual(rules[-1].find('action').get('url'), 'http://127.0.0.1:18081/{R:1}')
        self.assertEqual(root.findall('.//serverVariables'), [])
        self.assertNotIn('Authorization', xml)
        self.assertNotIn('HTTP_ORIGIN', xml)

    def test_new_instance_only_and_service_budget(self):
        """Existing instance output is retained, and the whole service receives the budget."""
        with tempfile.TemporaryDirectory() as temporary:
            args = argparse.Namespace(origin='https://allow.example.com', output=str(Path(temporary)/'new'),
                install_root='/opt/allow', account='allow', tunnel_port=18081, backend_port=8080,
                advisory_profile='DOCUMENT_ADVISORY_TIER1')
            configure.render(args)
            unit = (Path(args.output)/'linux/allow.service').read_text()
            self.assertIn('CPUQuota=400%', unit)
            self.assertIn('MemoryMax=6G', unit)
            self.assertIn('KillMode=control-group', unit)
            self.assertIn('ExecStart=/usr/bin/python3 -I -B ', unit)
            self.assertEqual((Path(args.output)/'linux/instance.json').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                configure.render(args)

    def test_wsl_profile_is_closed_and_bounded(self):
        """WSL uses matching loopback ports and emits proposals without applying them."""
        with tempfile.TemporaryDirectory() as temporary:
            args = argparse.Namespace(origin='https://allow.alloy4.fun', output=str(Path(temporary)/'new'),
                install_root='/opt/allow', account='allow', tunnel_port=18081, backend_port=18081,
                advisory_profile='DOCUMENT_ADVISORY_TIER1', transport='wsl', access_mode='ANONYMOUS')
            configure.render(args)
            unit = (Path(args.output)/'linux/allow.service').read_text()
            self.assertIn('MemoryHigh=3G', unit)
            self.assertIn('MemoryMax=4G', unit)
            self.assertIn('memory=5GB', (Path(args.output)/'wslconfig.proposal').read_text())
            args.backend_port = 8080
            args.output = str(Path(temporary)/'rejected')
            with self.assertRaises(ValueError):
                configure.render(args)
            self.assertFalse(Path(args.output).exists())

    def test_public_replacement_tuple_and_unit(self):
        """The new slot renders an independent unit without implicit legacy lifecycle edges."""
        with tempfile.TemporaryDirectory() as temporary:
            args = argparse.Namespace(origin='https://allow.alloy4.fun', output=str(Path(temporary)/'new'),
                install_root='/opt/allow-public', account='allow-public', tunnel_port=18081, backend_port=18081,
                advisory_profile='DOCUMENT_ADVISORY_TIER1', transport='wsl', access_mode='ANONYMOUS',
                installation_slot='PUBLIC_REPLACEMENT')
            configure.render(args)
            unit = (Path(args.output)/'linux/allow-public.service').read_text()
            self.assertFalse((Path(args.output)/'linux/allow.service').exists())
            self.assertIn('User=allow-public', unit)
            self.assertIn('WorkingDirectory=/opt/allow-public', unit)
            self.assertIn('MemoryMax=4G', unit)
            for forbidden in ('allow.service', 'Conflicts=', 'BindsTo=', 'Requires='):
                self.assertNotIn(forbidden, unit)
            config = json.loads((Path(args.output)/'linux/instance.json').read_text())
            self.assertEqual(config['installation_slot'], 'PUBLIC_REPLACEMENT')

    def test_mixed_replacement_tuple_rejects_before_output(self):
        """Every replacement selector boundary rejects before creating any directory."""
        with tempfile.TemporaryDirectory() as temporary:
            baseline = dict(origin='https://allow.alloy4.fun', install_root='/opt/allow-public',
                account='allow-public', tunnel_port=18081, backend_port=18081,
                advisory_profile='DOCUMENT_ADVISORY_TIER1', transport='wsl', access_mode='ANONYMOUS',
                installation_slot='PUBLIC_REPLACEMENT')
            cases = [('installation_slot', 'PUBLIC'), ('installation_slot', 'PRIMARY'), ('install_root', '/opt/allow'), ('account', 'allow'),
                     ('transport', 'ssh'), ('access_mode', 'PRIVATE'), ('backend_port', 8080), ('tunnel_port', 8080)]
            for index, (key, value) in enumerate(cases):
                args = argparse.Namespace(**(baseline | {key: value, 'output': str(Path(temporary)/str(index))}))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    configure.render(args)
                self.assertFalse(Path(args.output).exists())

    def test_keepalive_closed_readonly_unit_selection(self):
        """Keepalive maps only trusted selectors to the selected unit, never lifecycle changes."""
        path = Path(configure.__file__).parent/'linux/wsl_keepalive.py'
        spec = importlib.util.spec_from_file_location('test_keepalive', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.selected_unit('PRIMARY'), 'allow.service')
        self.assertEqual(module.selected_unit('PUBLIC_REPLACEMENT'), 'allow-public.service')
        with self.assertRaises(ValueError):
            module.selected_unit('allow.service; stop')
        for slot, unit in [('PRIMARY', 'allow.service'), ('PUBLIC_REPLACEMENT', 'allow-public.service')]:
            result = module.subprocess.CompletedProcess([], 1)
            with patch.object(module.sys, 'argv', ['keepalive', '--installation-slot', slot]), \
                    patch.object(module.subprocess, 'run', return_value=result) as run:
                with self.assertRaises(SystemExit):
                    module.main()
                self.assertEqual(run.call_args.args[0], ['/usr/bin/systemctl', 'is-active', '--quiet', unit])

    def test_unsafe_root_and_ports(self):
        """Generated unit arguments cannot introduce shell/unit syntax or long sockets."""
        for value in ['/opt/allow\nUser=root', '/opt/../allow', '/opt//allow', '/opt/a b', '/'+('a'*45)]:
            with self.assertRaises(ValueError):
                configure.install_root(value)
        for value in [0, 80, 65536]:
            with self.assertRaises(ValueError):
                configure.port(value)


if __name__ == '__main__':
    unittest.main()
