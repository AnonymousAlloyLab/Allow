"""Finite integration smoke of a newly initialized isolated deployment archive."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Instance:
    """Own one fresh service and keep its private capability out of test evidence."""

    def __init__(self, root, evidence):
        self.root, self.evidence = root, evidence
        self.config = json.loads((root/'deploy/instance.json').read_text())
        self.process = None
        self.token = None
        self.logs = []

    def start(self, label):
        log = self.evidence/f'service-{label}.log'
        self.logs.append(log)
        with log.open('xb') as stream:
            self.process = subprocess.Popen(['/usr/bin/python3', '-I', '-B', 'deploy/linux/service.py',
                '--config', 'deploy/instance.json'], cwd=self.root, stdout=stream, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline and self.process.poll() is None:
            link = self.root/'.runtime/launch.url'
            if link.exists():
                self.token = urllib.parse.parse_qs(urllib.parse.urlsplit(link.read_text().strip()).fragment)['token'][0]
                try:
                    if self.request('/api/config')[0] == 200:
                        return
                except (OSError, urllib.error.URLError):
                    pass
            time.sleep(.1)
        raise AssertionError('Owned deployment service failed to become ready; inspect its private test log')

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
                raise AssertionError('Service shutdown deadline exceeded')
            assert not (self.root/'.runtime/corpus/postgres/data/postmaster.pid').exists()
            assert not (self.root/'.runtime/corpus/sql-proxy/owner.json').exists()
            assert not (self.root/'.runtime/launch.url').exists()

    def request(self, path, data=None, token=None, headers=None):
        config = self.config
        values = {'Host': f'127.0.0.1:{config["tunnel_port"]}', 'Origin': config['public_origin'],
                  'Authorization': 'Bearer ' + (self.token if token is None else str(token))}
        values.update(headers or {})
        if token is False:
            values.pop('Authorization')
        body = None if data is None else json.dumps(data).encode()
        if body is not None:
            values['Content-Type'] = 'application/json'
        request = urllib.request.Request(f'http://127.0.0.1:{config["backend_port"]}'+path, body, values)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read(1048577), dict(response.headers)
        except urllib.error.HTTPError as failure:
            return failure.code, failure.read(1048577), dict(failure.headers)

    def call(self, path, data=None, expected='OK'):
        status, raw, _ = self.request(path, data)
        assert status == 200, (path, status)
        envelope = json.loads(raw)
        assert envelope['status'] == expected, (path, envelope['status'])
        return envelope['data']


def exercise(instance):
    """Exercise actual parser-routed persistence, Tier1 advisory, DEFAULT commit and solver."""
    api = '/api/v1/documents'
    status, index, headers = instance.request('/')
    assert status == 200 and b'<html' in index
    assert headers['Cache-Control'] == 'no-store'
    assert 'frame-ancestors' in headers['Content-Security-Policy']
    assert instance.request('/api/config', token='wrong')[0] == 403
    assert instance.request('/api/config', headers={'Origin': 'https://hostile.example'})[0] == 403
    assert instance.request('/api/config', headers={'Host': 'hostile.example',
        'X-Forwarded-Host': '127.0.0.1:'+str(instance.config['tunnel_port'])})[0] == 403
    initial = instance.call(api, {'idempotencyKey': str(uuid.uuid4()), 'title': 'Deployment smoke'}, 'COMMITTED')
    path = api+'/'+urllib.parse.quote(initial['documentId'], safe='')
    assert '%3A' in path
    assert instance.request(path, token='wrong')[0] == 403
    assert instance.request(path, token=False)[0] == 403
    for alias in ('/%61pi/config', '/api;ignored/config', path.replace('%3A', '%253A'), path.replace('%3A', '%3a')):
        assert instance.request(alias)[0] == 400, alias
    candidate = {'mode': 'SOURCE', 'source': 'sig A {}\npred Present { some A }\nrun Present for 3\n'}
    preview = {'draftId': str(uuid.uuid4()), 'draftEpoch': 1, 'baseRevision': 0, 'candidate': candidate}
    instance.call(path+'/validate', preview, 'VALIDATED')
    mutation = {'idempotencyKey': str(uuid.uuid4()), 'expectedRevision': 0, 'candidate': candidate}
    accepted = instance.call(path+'/commit', mutation, 'COMMITTED')
    assert accepted['revision'] == 1
    assert instance.call(path)['artifact']['source'] == candidate['source']
    assert instance.call(path+'?revision=0')['artifact']['source'] == ''
    descriptor = accepted['artifact']['analysisDescriptors'][0]
    submitted = instance.call(path+'/analyze', {'acceptedRevision': 1, 'commandKey': descriptor['commandKey'],
        'draftEpoch': 1, 'exactSourceHash': accepted['artifact']['sourceHash']}, 'SUBMITTED')
    deadline = time.monotonic() + 20
    while True:
        result = instance.call(path+'/analysis/'+submitted['jobId'])
        if result['job']['status'] not in ('QUEUED', 'RUNNING'):
            assert result['job']['status'] == 'SAT'
            break
        assert time.monotonic() < deadline
        time.sleep(.1)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(exist_ok=False)
    instance = Instance(args.root, args.evidence)
    report = {'status': 'RUNNING', 'manifest_sha256': digest(args.root/'MANIFEST.json'),
              'script_sha256': digest(Path(__file__)), 'windows_iis_ssh_acceptance': 'OPEN',
              'scope': 'Actual relocated Linux service and HTTP with explicit proxy Host/Origin; no real IIS or SSH hop.'}
    try:
        instance.start('first')
        path = exercise(instance)
        link_before = (args.root/'.runtime/launch.url').read_bytes()
        with (args.evidence/'service-competing.log').open('xb') as stream:
            competing = subprocess.run(['/usr/bin/python3', '-I', '-B', 'deploy/linux/service.py',
                '--config', 'deploy/instance.json'], cwd=args.root, stdout=stream,
                stderr=subprocess.STDOUT, timeout=20)
        assert competing.returncode != 0
        assert instance.process.poll() is None
        assert (args.root/'.runtime/launch.url').read_bytes() == link_before
        assert instance.request('/api/config')[0] == 200
        assert instance.call(path)['revision'] == 1
        report['concurrent_supervisor_rejected_without_owner_disruption'] = True
        old_token = instance.token
        proxy = json.loads((args.root/'.runtime/corpus/sql-proxy/status.json').read_text())
        report['sql_app_accepted'] = proxy['clients']['allow-app']['accepted']
        assert report['sql_app_accepted'] > 0
        instance.stop()
        instance.start('restart')
        assert old_token != instance.token
        assert instance.request('/api/config', token=old_token)[0] == 403
        assert instance.call(path)['revision'] == 1
        instance.stop()
        report.update(status='PASS', advisory='VALIDATED', solver='SAT', durable_revision=1,
                      restart_persistence='PASS', old_token_rejected=True, owned_stack_shutdown='PASS')
    except BaseException as error:
        report.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if instance.process is not None and instance.process.poll() is None:
            instance.stop()
        report['logs'] = [{'path': str(p), 'sha256': digest(p)} for p in instance.logs]
        (args.evidence/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
