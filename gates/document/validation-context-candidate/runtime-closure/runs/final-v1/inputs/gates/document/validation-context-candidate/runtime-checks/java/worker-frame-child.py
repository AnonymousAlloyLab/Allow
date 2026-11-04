"""Read one actual worker frame and return its nonce and observed byte count."""
import json
import sys

raw = sys.stdin.buffer.read()
if not raw.endswith(b'\n') or raw.count(b'\n') != 1:
    raise SystemExit(1)
frame = json.loads(raw[:-1].decode('utf-8'))
response = {'protocol': 1, 'requestId': frame['requestId'], 'status': 'UNAVAILABLE',
            'data': {'bytes': len(raw) - 1}}
sys.stdout.write(json.dumps(response, separators=(',', ':')) + '\n')
