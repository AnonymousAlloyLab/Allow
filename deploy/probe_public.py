#!/usr/bin/env python3
"""Probe one HTTPS Allow origin without a real capability or application mutations."""
import argparse
import http.client
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urlsplit

BODY_LIMIT = 65536
CHECKS = (
    ('root_html', '/', {}, (200,), True),
    ('absent_bearer', '/api/config', {}, (403,), True),
    ('invalid_bearer', '/api/config', {'Authorization': 'Bearer allow-probe-invalid'}, (403,), True),
    ('hostile_origin', '/', {'Origin': 'https://allow-probe.invalid'}, (403,), True),
    ('hostile_host', '/', {'Host': 'allow-probe.invalid'}, (400, 403), False),
    ('forwarded', '/api/config', {'X-Forwarded-Host': 'localhost',
        'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '127.0.0.1'}, (403,), True),
    ('encoded_alias', '/%61pi/config', {}, (400, 403, 404), False),
    ('matrix_alias', '/api;ignored/config', {}, (400, 403, 404), False),
)
ERRORS = frozenset(('none', 'tls', 'timeout', 'network', 'protocol', 'redirect',
                    'body_limit', 'status', 'headers', 'html', 'worker'))


def canonical_origin(value):
    """Reject launch links, paths, IP literals and ambiguous/non-HTTPS authorities."""
    pattern = r'https://([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+)(?::([1-9][0-9]{0,4}))?'
    match = re.fullmatch(pattern, value, flags=re.ASCII)
    if not match or len(match[1]) > 253 or any(len(label) > 63 for label in match[1].split('.')):
        raise argparse.ArgumentTypeError('Use one lowercase HTTPS DNS origin without a path or launch token')
    if all(label.isdigit() for label in match[1].split('.')):
        raise argparse.ArgumentTypeError('An HTTPS DNS name is required')
    if match[2] and (int(match[2]) == 443 or int(match[2]) > 65535):
        raise argparse.ArgumentTypeError('Omit default port 443; explicit ports must be within 1..65535')
    if match[1] == 'allow-probe.invalid':
        raise argparse.ArgumentTypeError('The negative-probe hostname is reserved')
    return value


def mode_value(value):
    """Select only the two installed authentication response policies."""
    if value not in ('PRIVATE', 'ANONYMOUS'):
        raise argparse.ArgumentTypeError('Access mode must be PRIVATE or ANONYMOUS')
    return value


def timeout_value(value):
    """Keep each supervised request within a finite operator-selected time budget."""
    number = float(value)
    if not 1 <= number <= 30:
        raise argparse.ArgumentTypeError('Timeout must be between 1 and 30 seconds')
    return number


def row(index, status, error, started):
    """Expose only fixed check identifiers, numeric observations and error categories."""
    return {'check': CHECKS[index][0], 'status': status, 'passed': error == 'none',
            'elapsed_ms': round((time.monotonic() - started) * 1000, 2), 'error': error}


def security_headers(headers):
    """Require one unambiguous instance of each security header on backend responses."""
    expected = {'cache-control': 'no-store', 'referrer-policy': 'no-referrer',
                'x-content-type-options': 'nosniff'}
    for name, value in expected.items():
        if headers.get_all(name) != [value]:
            return False
    policies = headers.get_all('content-security-policy', [])
    expected_policy = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                       "connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
    return policies == [expected_policy]


def response_error(index, response, body, access_mode="PRIVATE"):
    """Evaluate fixed expectations without retaining any response bytes or headers."""
    if len(body) > BODY_LIMIT:
        return 'body_limit'
    if 300 <= response.status <= 399:
        return 'redirect'
    expected = (401,) if access_mode == "ANONYMOUS" and index in (1, 2, 5) else CHECKS[index][3]
    if response.status not in expected:
        return 'status'
    if CHECKS[index][4] and not security_headers(response.headers):
        return 'headers'
    if index == 0 and ('text/html' not in response.headers.get('Content-Type', '')
                       or '<title>Allow · Alloy workbench</title>'.encode() not in body):
        return 'html'
    return 'none'


def bounded_body(response):
    """Reject ambiguous or incomplete HTTP framing and cap declared/streamed bodies."""
    lengths = response.headers.get_all('Content-Length', [])
    transfers = response.headers.get_all('Transfer-Encoding', [])
    transfer_tokens = [value.lower() for value in transfers]
    if len(lengths) > 1 or (lengths and transfers) or (transfers and transfer_tokens != ['chunked']):
        return b'', 'protocol'
    if lengths and not re.fullmatch('[0-9]+', lengths[0], flags=re.ASCII):
        return b'', 'protocol'
    if lengths and int(lengths[0]) > BODY_LIMIT:
        return b'', 'body_limit'
    body = response.read(BODY_LIMIT + 1)
    if response.length is not None and response.length > 0 and len(body) <= BODY_LIMIT:
        return b'', 'protocol'
    return body, 'none'


def observe(origin, index, timeout, access_mode="PRIVATE"):
    """Make one direct TLS request; the parent process enforces the total deadline."""
    mode_value(access_mode)
    started, status, connection = time.monotonic(), None, None
    try:
        target = urlsplit(canonical_origin(origin))
        connection = http.client.HTTPSConnection(target.hostname, target.port or 443,
            timeout=timeout, context=ssl.create_default_context())
        headers = {'Host': target.netloc, 'Connection': 'close', **CHECKS[index][2]}
        connection.request('GET', CHECKS[index][1], headers=headers)
        response = connection.getresponse()
        status = response.status
        body, error = bounded_body(response)
        if error == 'none':
            error = response_error(index, response, body, access_mode)
    except ssl.SSLError:
        error = 'tls'
    except (TimeoutError, socket.timeout):
        error = 'timeout'
    except OSError:
        error = 'network'
    except (http.client.HTTPException, ValueError):
        error = 'protocol'
    finally:
        if connection is not None:
            connection.close()
    return row(index, status, error, started)


def checked_worker_result(raw, index):
    """Reject unexpected child output instead of copying arbitrary data to the report."""
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {'check', 'status', 'passed', 'elapsed_ms', 'error'}:
        raise ValueError('Invalid worker result')
    if value['check'] != CHECKS[index][0] or value['error'] not in ERRORS:
        raise ValueError('Invalid worker identity')
    if value['status'] is not None and (type(value['status']) is not int or not 100 <= value['status'] <= 599):
        raise ValueError('Invalid status')
    if type(value['passed']) is not bool or value['passed'] != (value['error'] == 'none'):
        raise ValueError('Invalid verdict')
    if type(value['elapsed_ms']) not in (int, float) or not 0 <= value['elapsed_ms'] <= 31000:
        raise ValueError('Invalid duration')
    return value


def supervised(origin, index, timeout, access_mode="PRIVATE"):
    """Bound DNS, TLS and slow streaming together by killing and reaping one worker."""
    mode_value(access_mode)
    started = time.monotonic()
    command = [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
               '--origin', origin, '--timeout', str(timeout), '--worker', str(index),
               '--access-mode', access_mode]
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
        if result.returncode != 0 or result.stderr or len(result.stdout) > 1024:
            return row(index, None, 'worker', started)
        value = checked_worker_result(result.stdout, index)
        value['elapsed_ms'] = round((time.monotonic() - started) * 1000, 2)
        return value
    except subprocess.TimeoutExpired:
        return row(index, None, 'timeout', started)
    except (OSError, ValueError, TypeError, KeyError):
        return row(index, None, 'worker', started)


def report(origin, timeout, access_mode="PRIVATE"):
    """Run exactly eight sequential checks and keep deployment acceptance separate."""
    mode_value(access_mode)
    results = [supervised(origin, index, timeout, access_mode) for index in range(len(CHECKS))]
    passed = all(item['passed'] for item in results)
    return {'schema': 1, 'access_mode': access_mode, 'scope': 'Unauthenticated HTTPS boundary probe only',
            'status': 'PASS' if passed else 'FAIL', 'checks': results,
            'public_deployment_acceptance': 'OPEN'}


def main():
    """Print redacted JSON and fail the process if any finite probe fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True, type=canonical_origin)
    parser.add_argument('--timeout', type=timeout_value, default=8.0)
    parser.add_argument('--access-mode', type=mode_value, choices=['PRIVATE', 'ANONYMOUS'], default='PRIVATE')
    parser.add_argument('--worker', type=int, choices=range(len(CHECKS)), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        print(json.dumps(observe(args.origin, args.worker, args.timeout, args.access_mode)))
        return 0
    result = report(args.origin, args.timeout, args.access_mode)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
