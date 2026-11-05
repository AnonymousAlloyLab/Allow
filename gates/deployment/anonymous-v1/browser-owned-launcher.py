"""Own disposable SQL+Java for root-requested browser UX checks; never public exposure."""
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT = Path('/tmp/allow-anonymous-sql-r1')
BUILD = Path('/tmp/allow-anonymous-build/backend')
EVIDENCE = Path('/home/augustus/Allow/gates/deployment/anonymous-v1')
PORT = 18095
sys.path.insert(0, str(ROOT / 'retrieval'))
from allow_documents.store import Store



PROXY_PORT = 18096
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
       'te', 'trailer', 'transfer-encoding', 'upgrade'}


class UXProxy(BaseHTTPRequestHandler):
    """Loopback UX adapter only: fixed Host and replacement of existing Origin."""
    protocol_version = 'HTTP/1.1'

    def log_message(self, _format, *_args):
        """Suppress paths, headers, bodies and capability request logs."""
        pass

    def forward(self):
        """Forward bounded browser requests without forwarding hop-by-hop headers."""
        if not self.path.startswith('/') or self.path.startswith('//'):
            self.send_error(400)
            return
        try:
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('unsupported_request_encoding')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 <= size <= 1048576:
                raise ValueError('request_limit')
            body = self.rfile.read(size) if size else None
            removed = HOP | {name.strip().lower() for name in self.headers.get('Connection', '').split(',')}
            headers = {name: value for name, value in self.headers.items()
                       if name.lower() not in removed | {'host', 'content-length'}}
            for name in list(headers):
                if name.lower() == 'origin':
                    headers[name] = 'https://allow.alloy4.fun'
            headers['Host'] = '127.0.0.1:18095'
            connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=30)
            connection.request(self.command, self.path, body=body, headers=headers)
            incoming = connection.getresponse()
            content = incoming.read(3145729)
            if len(content) > 3145728:
                raise ValueError('response_limit')
            response_removed = HOP | {name.strip().lower() for name in incoming.getheader('Connection', '').split(',')}
            self.send_response(incoming.status)
            for name, value in incoming.getheaders():
                if name.lower() not in response_removed | {'content-length'}:
                    self.send_header(name, value)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)
            connection.close()
        except Exception:
            self.close_connection = True
            try:
                self.send_response(502)
                self.send_header('Content-Length', '0')
                self.end_headers()
            except Exception:
                pass

    do_GET = forward
    do_POST = forward
    do_DELETE = forward
    do_HEAD = forward
    do_OPTIONS = forward


class QuietProxy(ThreadingHTTPServer):
    """Suppress threaded handler diagnostics and bind only the owned loopback port."""
    daemon_threads = True

    def handle_error(self, _request, _address):
        """Do not log any request context from failed browser connections."""
        pass

def private_digest():
    with Store().transaction() as connection:
        rows = connection.execute('SELECT * FROM documents.workspace').fetchall()
    return hashlib.sha256((ROOT / '.runtime/documents/identity.json').read_bytes()).hexdigest(), hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main():
    os.umask(0o077)
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', PORT))
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', PROXY_PORT))
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda _sig, _frame: stop.set())
    signal.signal(signal.SIGINT, lambda _sig, _frame: stop.set())
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT), 'LANG': 'C.UTF-8',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
    python = str(ROOT / '.tools/retrieval-venv/bin/python')
    sql = [python, '-B', '-s', str(ROOT / 'scripts/bootstrap_corpus.py')]
    process = None
    baseline = None
    proxy = None
    proxy_thread = None
    control = ROOT / '.runtime/browser-fixture'
    stop_file = control / 'stop'
    ready_file = control / 'ready.json'
    token = secrets.token_urlsafe(32)
    stamp = str(time.time_ns())
    server_log = EVIDENCE / ('browser-owned-' + stamp + '-server.log')
    sql_log = EVIDENCE / ('browser-owned-' + stamp + '-sql.log')
    try:
        with sql_log.open('x') as output:
            subprocess.run(sql + ['start'], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=90)
        baseline = private_digest()
        control.mkdir(mode=0o700, exist_ok=True)
        if stop_file.exists() or ready_file.exists():
            raise RuntimeError('remove_stale_browser_fixture_control_only_after_confirming_old_owner_stopped')
        with server_log.open('x') as output:
            process = subprocess.Popen(['/usr/bin/java', '-cp', 'target/classes:target/dependency/*',
                'dev.allow.backend.AllowApplication', '--allow.access-mode=ANONYMOUS',
                '--allow.corpus.root=' + str(ROOT), '--allow.deployment.origin=https://allow.alloy4.fun',
                '--allow.deployment.tunnel-host=127.0.0.1:18095', '--server.port=18095',
                '--server.address=127.0.0.1', '--allow.document.advisory-profile=DOCUMENT_ADVISORY_TIER1'],
                cwd=BUILD, env=dict(env, ALLOW_TOKEN=token), stdout=output, stderr=subprocess.STDOUT)
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('isolated_browser_backend_startup_failed')
                try:
                    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=2)
                    connection.request('GET', '/api/public/config', headers={'Host': '127.0.0.1:18095'})
                    response = connection.getresponse()
                    ready = response.status == 200
                    response.read(4096)
                    connection.close()
                    if ready:
                        break
                except OSError:
                    pass
                stop.wait(0.1)
            else:
                raise RuntimeError('isolated_browser_backend_startup_timeout')
            proxy = QuietProxy(('127.0.0.1', PROXY_PORT), UXProxy)
            proxy_thread = threading.Thread(target=proxy.serve_forever, name='owned-browser-ux-adapter', daemon=True)
            proxy_thread.start()
            metadata = {'pid': os.getpid(), 'backend_pid': process.pid, 'browser_url': 'http://127.0.0.1:18096',
                'stop_file': str(stop_file), 'evidence_scope': 'Loopback UX adapter only; fixed Host and existing Origin replacement do not prove TLS/IIS/real Origin routing'}
            with ready_file.open('x') as ready:
                json.dump(metadata, ready, indent=2)
            print('BROWSER_UX_READY http://127.0.0.1:18096 stop_file=' + str(stop_file), flush=True)
            print(metadata['evidence_scope'], flush=True)
            while not stop.wait(1) and not stop_file.exists():
                if process.poll() is not None:
                    raise RuntimeError('isolated_browser_backend_exited')
    finally:
        if proxy is not None:
            proxy.shutdown()
            proxy.server_close()
        if proxy_thread is not None:
            proxy_thread.join(timeout=3)
        ready_file.unlink(missing_ok=True)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        private_unchanged = baseline is None or private_digest() == baseline
        with sql_log.open('a') as output:
            result = subprocess.run(sql + ['stop'], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=45)
        if token in server_log.read_text():
            raise RuntimeError('token_found_in_isolated_server_log')
        print('BROWSER_OWNED_STACK_STOPPED private_control_unchanged=' + str(private_unchanged) + ' sql_exit=' + str(result.returncode), flush=True)
        if not private_unchanged or result.returncode:
            raise RuntimeError('isolated_browser_cleanup_uncertain')


if __name__ == '__main__':
    main()
