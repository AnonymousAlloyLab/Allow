"""Finite TLS-fixture and failure-boundary tests; no real deployment is contacted."""
import argparse
import http.server
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import probe_public as probe

POLICY = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
          "connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
HEADERS = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
           'X-Content-Type-Options': 'nosniff', 'Content-Security-Policy': POLICY,
           'Content-Type': 'text/html'}
HTML = '<title>Allow · Alloy workbench</title>'.encode()


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    """Reply using a fixed test policy, suppressing request/response logging."""

    def log_message(self, *_args):
        """Keep test and adversarial response text out of logs."""

    def do_GET(self):
        """Send the fixture's selected response without modifying application state."""
        status, body, headers, delay = self.server.reply(self)
        time.sleep(delay)
        try:
            self.send_response(status)
            for name, value in headers:
                self.send_header(name, value)
            length = len(body) if self.server.length_override is None else self.server.length_override
            if length != -1:
                self.send_header('Content-Length', str(length))
            self.end_headers()
            self.wfile.write(body)
        except (OSError, ssl.SSLError):
            pass


def positive_reply(request):
    """Model only the unauthenticated Allow boundary for eight fixed GET requests."""
    if request.path == '/':
        rejected = (request.headers.get('Host') == 'allow-probe.invalid'
                    or request.headers.get('Origin') == 'https://allow-probe.invalid')
        return (403 if rejected else 200), HTML, list(HEADERS.items()), 0
    status = 400 if request.path in ('/%61pi/config', '/api;ignored/config') else 403
    return status, b'{"status":"FORBIDDEN"}', list(HEADERS.items()), 0


def anonymous_reply(request):
    """Change only the anonymous authentication denial, preserving routing checks."""
    status, body, headers, delay = positive_reply(request)
    return (401 if request.path == '/api/config' else status), body, headers, delay


class PublicProbeTest(unittest.TestCase):
    """Exercise actual local TLS separately from the supervised process boundary."""

    @classmethod
    def setUpClass(cls):
        """Create one disposable self-signed fixture certificate and TLS listener."""
        cls.temporary = tempfile.TemporaryDirectory(prefix='allow-probe-test-')
        root = Path(cls.temporary.name)
        cls.cert, key = root/'cert.pem', root/'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', str(key), '-out', str(cls.cert), '-days', '1',
            '-subj', '/CN=allow.test', '-addext',
            'subjectAltName=DNS:allow.test,DNS:localhost.localdomain'],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.cert, key)
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), FixtureHandler)
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = 'https://allow.test:' + str(cls.server.server_port)
        cls.original_resolve = staticmethod(socket.getaddrinfo)
        cls.original_context = staticmethod(ssl.create_default_context)

    @classmethod
    def tearDownClass(cls):
        """Reap the owned listener and delete its temporary certificate/key."""
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temporary.cleanup()

    def setUp(self):
        """Restore the positive fixture before each independent check."""
        self.server.reply = positive_reply
        self.server.length_override = None

    def resolve(self, host, port, *args, **kwargs):
        """Resolve only the fixed local fixture name while preserving TLS hostname checks."""
        return self.original_resolve('127.0.0.1' if host == 'allow.test' else host,
                                     port, *args, **kwargs)

    def trusted_context(self):
        """Trust the test certificate only inside the fixture's patched observer."""
        return self.original_context(cafile=str(self.cert))

    def observe(self, index=0, trusted=True, timeout=1, access_mode="PRIVATE"):
        """Run real HTTPS to the fixture with explicit test-only DNS and CA patches."""
        with patch.object(probe.socket, 'getaddrinfo', self.resolve):
            if not trusted:
                return probe.observe(self.origin, index, timeout, access_mode)
            with patch.object(probe.ssl, 'create_default_context', self.trusted_context):
                return probe.observe(self.origin, index, timeout, access_mode)

    def fixed_reply(self, status=200, body=HTML, headers=None, delay=0):
        """Replace the fixture response with a deliberately hostile case."""
        selected = list(HEADERS.items()) if headers is None else headers
        self.server.reply = lambda _request: (status, body, selected, delay)

    def test_eight_fixed_checks_pass_tls_fixture(self):
        """Every prescribed request passes over certificate-verified fixture TLS."""
        self.assertEqual(len(probe.CHECKS), 8)
        for index in range(8):
            with self.subTest(check=probe.CHECKS[index][0]):
                result = self.observe(index)
                self.assertTrue(result['passed'], result)

    def test_anonymous_tls_policy_changes_only_authentication_denials(self):
        """All eight anonymous checks retain hostile-route and alias rejection rules."""
        self.server.reply = anonymous_reply
        for index in range(8):
            with self.subTest(index=index):
                self.assertTrue(self.observe(index, access_mode='ANONYMOUS')['passed'])
        for index in (1, 2, 5):
            self.assertEqual(self.observe(index)['error'], 'status')
        self.server.reply = positive_reply
        for index in (1, 2, 5):
            self.assertEqual(self.observe(index, access_mode='ANONYMOUS')['error'], 'status')
        self.fixed_reply(status=401)
        self.assertEqual(self.observe(3, access_mode='ANONYMOUS')['error'], 'status')

    def test_mode_domain_and_worker_propagation(self):
        """Closed mode input reaches the isolated worker without changing private defaults."""
        with self.assertRaises(argparse.ArgumentTypeError):
            probe.report('https://allow.test', 1, 'PUBLIC')
        result = json.dumps(probe.row(1, 401, 'none', time.monotonic())).encode()
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, result, b'')) as run:
            self.assertTrue(probe.supervised('https://allow.test', 1, 1, 'ANONYMOUS')['passed'])
            args = run.call_args.args[0]
            self.assertEqual(args[args.index('--access-mode') + 1], 'ANONYMOUS')
        cli = subprocess.run(['/usr/bin/python3', '-I', '-B', probe.__file__, '--origin', 'https://allow.test',
                              '--access-mode', 'PUBLIC'], capture_output=True, text=True, timeout=3)
        self.assertNotEqual(cli.returncode, 0)

    def test_untrusted_tls_fails(self):
        """A certificate outside the normal trust store cannot be bypassed."""
        self.assertEqual(self.observe(trusted=False)['error'], 'tls')

    def test_no_redirect_following_or_body_disclosure(self):
        """Redirects fail and no hostile Location or body enters the report."""
        self.fixed_reply(status=302, body=b'private-secret-marker',
                         headers=[('Location', 'https://secret.invalid/?token=secret')])
        result = self.observe()
        self.assertEqual(result['error'], 'redirect')
        self.assertNotIn('secret', json.dumps(result))

    def test_body_cap(self):
        """A streamed response larger than the cap fails without retaining its content."""
        self.fixed_reply(body=b'x' * (probe.BODY_LIMIT + 1))
        self.assertEqual(self.observe()['error'], 'body_limit')

    def test_truncated_and_ambiguous_http_framing(self):
        """Correct title/headers cannot hide premature EOF or duplicate framing."""
        self.fixed_reply()
        self.server.length_override = len(HTML) + 5
        self.assertEqual(self.observe()['error'], 'protocol')
        self.server.length_override = None
        self.fixed_reply(headers=list(HEADERS.items()) + [('Content-Length', str(len(HTML)))])
        self.assertEqual(self.observe()['error'], 'protocol')
        self.fixed_reply(headers=list(HEADERS.items()) + [('Transfer-Encoding', 'chunked')])
        self.assertEqual(self.observe()['error'], 'protocol')

    def test_valid_chunked_case_variant(self):
        """HTTP transfer-coding tokens are case-insensitive and retain normal checks."""
        encoded = format(len(HTML), 'x').encode() + b'\r\n' + HTML + b'\r\n0\r\n\r\n'
        self.server.length_override = -1
        self.fixed_reply(body=encoded, headers=list(HEADERS.items()) + [('Transfer-Encoding', 'Chunked')])
        self.assertTrue(self.observe()['passed'])

    def test_socket_deadline(self):
        """A fixture that stalls before headers exceeds the network deadline."""
        self.fixed_reply(delay=.2)
        self.assertEqual(self.observe(timeout=.03)['error'], 'timeout')

    def test_public_root_must_be_allow_html(self):
        """A generic successful proxy page cannot pass as the application."""
        self.fixed_reply(body=b'<title>Unrelated application</title>')
        self.assertEqual(self.observe()['error'], 'html')

    def test_weak_or_duplicate_security_headers_fail(self):
        """Missing, duplicate and weakened policy headers all fail."""
        for headers in ([], list(HEADERS.items()) + [('Cache-Control', 'public')],
                        list((HEADERS | {'Content-Security-Policy': POLICY + '; default-src *'}).items())):
            self.fixed_reply(headers=headers)
            self.assertEqual(self.observe()['error'], 'headers')

    def test_denial_must_not_be_success_or_outage(self):
        """Both unauthorized API success and gateway failure fail the probe."""
        for status in (200, 301, 404, 500, 502, 503):
            self.fixed_reply(status=status)
            self.assertFalse(self.observe(index=1)['passed'])

    def test_origin_and_timeout_boundaries(self):
        """Inputs cannot carry capabilities or turn the probe into arbitrary browsing."""
        for value in ('http://allow.test', 'https://allow.test/#token=secret',
                      'https://user:secret@allow.test', 'https://allow.test?token=secret',
                      'https://allow.test/', 'https://127.0.0.1', 'https://allow.test:443',
                      'https://allow-probe.invalid', 'https://allow.test:65536'):
            with self.assertRaises(argparse.ArgumentTypeError):
                probe.canonical_origin(value)
        for value in ('0', '31', 'nan', 'inf'):
            with self.assertRaises(argparse.ArgumentTypeError):
                probe.timeout_value(value)

    def test_child_result_is_closed_and_redacted(self):
        """A compromised or malformed child report cannot smuggle arbitrary data."""
        valid = probe.row(0, 200, 'none', time.monotonic())
        for value in (valid | {'body': 'secret'}, valid | {'error': 'secret'},
                      valid | {'passed': 'yes'}, valid | {'elapsed_ms': float('nan')}):
            with self.assertRaises(ValueError):
                probe.checked_worker_result(json.dumps(value), 0)

    def test_parent_deadline_includes_dns_and_reaps_worker(self):
        """The parent uses subprocess timeout even if child networking never returns."""
        with patch.object(probe.subprocess, 'run', side_effect=subprocess.TimeoutExpired('worker', 1)) as run:
            result = probe.supervised('https://allow.test', 0, 1)
        self.assertEqual(result['error'], 'timeout')
        self.assertEqual(run.call_args.kwargs['timeout'], 1)
        self.assertEqual(run.call_args.args[0][1:3], ['-I', '-B'])

    def test_actual_stalled_child_is_killed_and_reaped(self):
        """An actually stalled subprocess cannot survive the total request budget."""
        with tempfile.TemporaryDirectory(prefix='allow-probe-worker-') as temporary:
            script, marker = Path(temporary)/'worker.py', Path(temporary)/'pid'
            script.write_text('import os,time\nfrom pathlib import Path\n'
                              + 'Path(' + repr(str(marker)) + ').write_text(str(os.getpid()))\ntime.sleep(10)\n')
            started = time.monotonic()
            with patch.object(probe, '__file__', str(script)):
                result = probe.supervised('https://allow.test', 0, 1)
            self.assertEqual(result['error'], 'timeout')
            self.assertLess(time.monotonic() - started, 3)
            with self.assertRaises(ProcessLookupError):
                os.kill(int(marker.read_text()), 0)

    def test_report_does_not_promote_probe_to_acceptance(self):
        """Even all passing checks retain deployment acceptance OPEN."""
        with patch.object(probe, 'supervised', side_effect=lambda _o, i, _t, _m: probe.row(i, 200, 'none', time.monotonic())):
            result = probe.report('https://allow.test', 1)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['public_deployment_acceptance'], 'OPEN')
        self.assertEqual([r['check'] for r in result['checks']], [c[0] for c in probe.CHECKS])

    def test_real_child_isolation_and_failure_exit(self):
        """A real isolated worker rejects failed DNS without emitting exception details."""
        result = probe.supervised('https://allow-probe-target.invalid', 0, 2)
        self.assertFalse(result['passed'])
        self.assertIn(result['error'], ('network', 'timeout'))
        self.assertNotIn('allow-probe-target', json.dumps(result))

    def test_complete_cli_with_fixture_ca_and_ambient_proxy_ignored(self):
        """Run all real worker subprocesses with trusted local TLS and an unusable proxy."""
        origin = 'https://localhost.localdomain:' + str(self.server.server_port)
        environment = dict(os.environ, SSL_CERT_FILE=str(self.cert),
                           HTTPS_PROXY='http://127.0.0.1:1', HTTP_PROXY='http://127.0.0.1:1',
                           ALL_PROXY='http://127.0.0.1:1', NO_PROXY='')
        result = subprocess.run(['/usr/bin/python3', '-I', '-B', probe.__file__,
            '--origin', origin, '--timeout', '2'], env=environment,
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(len(report['checks']), 8)
        self.assertEqual(report['public_deployment_acceptance'], 'OPEN')

    def test_complete_anonymous_cli_uses_mode_in_actual_workers(self):
        """Real isolated subprocesses use401only for the three anonymous denial checks."""
        self.server.reply = anonymous_reply
        origin = 'https://localhost.localdomain:' + str(self.server.server_port)
        environment = dict(os.environ, SSL_CERT_FILE=str(self.cert))
        result = subprocess.run(['/usr/bin/python3', '-I', '-B', probe.__file__, '--origin', origin,
            '--timeout', '2', '--access-mode', 'ANONYMOUS'], env=environment,
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['access_mode'], 'ANONYMOUS')
        self.assertEqual([report['checks'][i]['status'] for i in (1, 2, 5)], [401, 401, 401])
        self.assertEqual(report['public_deployment_acceptance'], 'OPEN')


if __name__ == '__main__':
    unittest.main()
