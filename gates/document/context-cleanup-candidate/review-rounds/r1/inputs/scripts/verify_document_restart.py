#!/usr/bin/env python3
"""Check retained receipts after the task-owned server was killed and freshly launched.

The smoke test writes private prior state. This checker never prints the old or new bearer.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from smoke_documents import API, DocumentClient, digest, encoded, fingerprint

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Require changed authority, identical durable scope and exact historical response bytes."""
    state = json.loads((ROOT/'.runtime/documents/http-restart-fixture.json').read_text())
    client = DocumentClient()
    assert client.token != state['priorToken'], 'Restart must issue fresh bearer authority'
    assert client.raw(API, headers={'Authorization': 'Bearer '+state['priorToken']})[0] == 403
    identity_hash = digest((ROOT/'.runtime/documents/identity.json').read_bytes())
    assert identity_hash == state['identitySha256']
    head, _ = client.call(state['path'])
    assert head['revision'] == head['headRevision'] == state['headRevision']
    assert head['artifact'] == state['artifact']
    assert client.raw(API, encoded(state['createBody']))[2] == state['createResponse'].encode()
    assert client.raw(state['path']+'/commit', encoded(state['sourceBody']))[2] == state['sourceResponse'].encode()
    assert client.call(state['path'])[0]['revision'] == state['headRevision']
    files, root = fingerprint()
    report = {'status': 'PASS', 'classification': 'ACTUAL_POST_PROCESS_CRASH_HTTP_RECOVERY_NOT_FORMAL_REFINEMENT',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'checks': ['Fresh bearer differs and old bearer is denied', 'Durable private identity hash unchanged',
                         'Exact accepted head and artifact retained', 'Original create response bytes replay',
                         'Original historical commit response bytes replay', 'Replay advances no revision'],
              'source_sha256': files, 'input_root_sha256': root,
              'verifier_sha256': digest(Path(__file__).read_bytes()),
              'scope': 'Owned Spring JVM killed after completed smoke; PostgreSQL was not restarted; no in-flight transaction fault injection.',
              'authority_or_source_exported': False}
    (ROOT/'gates/document/restart-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'checks': len(report['checks'])}))


if __name__ == '__main__':
    main()
