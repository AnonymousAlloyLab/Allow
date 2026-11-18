#!/usr/bin/python3
"""Exercise disabled intake and real route/CSP boundaries without any external providers."""
import argparse
import json
from pathlib import Path
import urllib.error
import urllib.request


def read(base, path, headers=None, body=None):
    """Read one explicit loopback endpoint, including fixed error responses."""
    request = urllib.request.Request(base + path, headers=headers or {}, data=body)
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as failure:
        response = failure
    with response:
        return response.status, response.headers, response.read(262145)


def acceptance(base):
    """Require disabled intake, isolated child CSP and unchanged workspace protection."""
    if not base.startswith('http://127.0.0.1:'):
        raise ValueError('Use an explicit disposable loopback server')
    status, headers, body = read(base, '/request-ai-access')
    assert status == 200 and b'AI access' in body and b'google.com' not in body
    assert 'google.com' not in headers['Content-Security-Policy']
    assert headers['Cache-Control'] == 'no-store'
    status, headers, body = read(base, '/request-ai-access/captcha.html')
    policy = headers['Content-Security-Policy']
    assert status == 200 and 'sandbox allow-scripts;' in policy
    assert 'allow-same-origin' not in policy and "frame-ancestors 'self'" in policy
    assert b'captcha.js' in body
    assert read(base, '/request-ai-access/captcha.js')[0] == 200
    assert json.loads(read(base, '/api/ai-access/config')[2]) == {'enabled': False}
    assert read(base, '/api/ai-access/challenge', {'Origin': base, 'Content-Type': 'application/json'}, b'{}')[0] == 503
    assert read(base, '/api/ai-access/challenge', {'Origin': 'null', 'Content-Type': 'application/json'}, b'{}')[0] == 403
    assert read(base, '/request-ai-access', {'Authorization': 'Bearer inert-rejected-fixture'})[0] == 400
    assert read(base, '/request-ai-access?alias=1')[0] == 400
    assert read(base, '/request-ai-access/captcha.html?alias=1')[0] == 400
    assert read(base, '/api/config')[0] == 403
    return {'status': 'PASS', 'mode': 'OFF', 'checks': 10,
            'scope': 'Real HTTP route/CSP/disabled intake acceptance; enabled provider flow covered by injected unit fixtures only',
            'external_google_calls': 0, 'external_email_messages': 0}


def main():
    """Require an explicit target and save only nonsecret boundary outcomes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = acceptance(args.base)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
