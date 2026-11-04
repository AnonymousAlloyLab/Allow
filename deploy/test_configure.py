"""Check generated routing, resource limits and configuration rejection boundaries."""
import argparse
import tempfile
import unittest
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
            with self.assertRaises(FileExistsError):
                configure.render(args)

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
