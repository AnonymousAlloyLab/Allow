#!/usr/bin/env python3
"""Exercise the running local HTTP boundary with synthetic models; never print authority."""
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

class Client:
    """Keep the launch capability private while checking real request/response behavior."""

    def __init__(self):
        parts = urllib.parse.urlsplit((ROOT / '.runtime/launch.url').read_text().strip())
        self.base = urllib.parse.urlunsplit(parts._replace(fragment='')).rstrip('/')
        self.token = urllib.parse.parse_qs(parts.fragment)['token'][0]
        self.epoch = 0

    def request(self, path, body=None, method=None, headers=None, authorized=True):
        """Return status/data without logging raw headers or model content."""
        values = {'Content-Type': 'application/json'}
        if authorized:
            values['Authorization'] = 'Bearer ' + self.token
        values.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data, values, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw.startswith(b'{') else raw.decode()
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()

    def submit(self, source, operation='ANALYZE'):
        """Submit a unique edit snapshot and assert exact echoed source identity."""
        self.epoch += 1
        status, result = self.request('/api/jobs', {'source': source, 'commandIndex': 0,
            'revision': 1, 'epoch': self.epoch, 'operation': operation})
        assert status == 200, (status, result)
        assert result['sourceHash'] == hashlib.sha256(source.encode()).hexdigest()
        assert result['epoch'] == self.epoch and result['revision'] == 1
        return result

    def terminal(self, result):
        """Poll a bounded synthetic job, retaining all response identity checks."""
        original = {key: result[key] for key in ['jobId', 'sourceHash', 'revision', 'epoch', 'analysisKey']}
        end = time.monotonic() + 15
        while result['status'] in ['QUEUED', 'RUNNING']:
            assert time.monotonic() < end, 'Job did not terminate'
            time.sleep(0.05)
            status, result = self.request('/api/jobs/' + original['jobId'])
            assert status == 200
            assert all(result[key] == value for key, value in original.items())
        return result

def main():
    """Record only checks and bounded outcomes; no source corpus or capability is exported."""
    client = Client()
    checks = []
    status, shell = client.request('/', authorized=False)
    assert status == 200 and '<div id="root">' in shell
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', shell)
    assert len(assets) >= 2, 'Missing built JavaScript/CSS assets'
    for asset in assets:
        assert client.request(asset, authorized=False)[0] == 200
    checks.append('Spring serves the built React shell and referenced JavaScript/CSS assets')
    assert client.request('/api/config', authorized=False)[0] == 403
    assert client.request('/api/config', headers={'Authorization': 'Bearer invalid'})[0] == 403
    assert client.request('/api/config', headers={'Origin': 'https://hostile.invalid'})[0] == 403
    assert client.request('/api/config', headers={'Host': 'hostile.invalid'})[0] == 403
    checks.append('Missing/wrong authority, hostile Origin and Host rejected')
    fixtures = [
        ('SAT', 'sig Person {} run { some Person } for 3'),
        ('UNSAT', 'sig Person {} run { some Person and no Person } for 3'),
        ('SAT', 'sig Person {} assert Empty { no Person } check Empty for 3'),
        ('UNSAT', 'sig Person {} assert Identity { Person = Person } check Identity for 3'),
        ('INVALID', 'sig Person {} run { Person and some Person } for 3')]
    outcomes = []
    for expected, source in fixtures:
        result = client.terminal(client.submit(source))
        assert result['status'] == expected, result
        outcomes.append({'status': result['status'], 'commandKind': result['commandKind']})
    checks.append('Real sandboxed SAT/UNSAT run/check and invalid type outcomes')
    first = client.terminal(client.submit('sig Person {} run { some Person } for 3'))
    renamed = client.terminal(client.submit('sig PrivateLabel {} run { some PrivateLabel } for 3'))
    assert first['canonical']['status'] == renamed['canonical']['status'] == 'AVAILABLE'
    assert first['canonical'] == renamed['canonical']
    assert 'PrivateLabel' not in renamed['canonical']['payload']
    assert renamed['witness'] is not None
    checks.append('Alpha-renaming preserves exact anonymous bytes/hash/features; witness remains separate')
    validated = client.terminal(client.submit('sig Person {} run { some Person } for 3', 'VALIDATE'))
    assert validated['status'] == 'VALIDATED' and validated['witness'] is None
    checks.append('Validation does not fabricate a SAT witness')
    for source in ['open util/ordering[Person]\nsig Person {} run {}', 'a' * 32769]:
        assert client.request('/api/jobs', {'source': source, 'commandIndex': 0,
            'revision': 1, 'epoch': 100, 'operation': 'ANALYZE'})[0] == 400
    checks.append('Explicit imports and oversized source rejected at HTTP boundary')
    job = client.submit('sig Node { edge: set Node } run { some Node } for 10')
    status, cancelled = client.request('/api/jobs/' + job['jobId'], method='DELETE')
    assert status == 200 and cancelled['status'] == 'CANCELLED', cancelled
    time.sleep(0.2)
    assert client.request('/api/jobs/' + job['jobId'])[1]['status'] == 'CANCELLED'
    checks.append('Cancellation remains terminal after worker completion opportunity')
    report = {'status': 'PASS', 'classification': 'TESTED_HTTP_INTEGRATION_NOT_FORMAL_REFINEMENT',
        'checks': checks, 'solver_outcomes': outcomes,
        'browser_qa': 'NOT_RUN: CUA inventory has no browsers; in-app browser unavailable',
        'dataset_sources_used': False, 'authority_recorded': False}
    (ROOT / 'gates/g1/http-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
