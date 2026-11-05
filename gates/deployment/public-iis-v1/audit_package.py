"""Audit final R7 bytes and extract only to a fresh owned staging root."""
import hashlib
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
ARCHIVE = ROOT/'dist/allow-iis-linux-private-20261104-r7.zip'
BASELINE = ROOT/'dist/allow-iis-linux-private-20261104-r6.zip'
DESTINATION = Path('/tmp/allow-public-iis-r7')
NEW = {'spec/public-iis-staging.json', 'formal/Allow/PublicIisStaging.lean',
       'gates/deployment/public-iis-v1/council-disposition.json',
       'gates/deployment/public-iis-v1/formal-report.json', 'deploy/probe_public.py'}
CHANGED = {'README.md', 'docs/iis-deployment.md', 'deploy/windows/Install-Site.ps1'}


def audit():
    """Bind manifest, contents, source and R6 delta without reading runtime data."""
    with zipfile.ZipFile(BASELINE) as previous, zipfile.ZipFile(ARCHIVE) as archive:
        prior = json.loads(previous.read('MANIFEST.json'))['files']
        raw = archive.read('MANIFEST.json')
        members = json.loads(raw)['files']
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(members) | {'MANIFEST.json', 'MANIFEST.sha256'}
        assert archive.read('MANIFEST.sha256').decode().split()[0] == hashlib.sha256(raw).hexdigest()
        added, removed = set(members) - set(prior), set(prior) - set(members)
        changed = {name for name in members.keys() & prior.keys() if members[name] != prior[name]}
        assert added == NEW and changed == CHANGED and not removed
        DESTINATION.mkdir(mode=0o700, exist_ok=False)
        for item in archive.infolist():
            relative = Path(item.filename)
            assert not relative.is_absolute() and '..' not in relative.parts
            expected_mode = 0o755 if item.filename == '.tools/sqlean/sqlean_pg_grammar' else 0o644
            assert item.external_attr >> 16 == 0o100000 | expected_mode
            body = archive.read(item)
            if item.filename in members:
                assert hashlib.sha256(body).hexdigest() == members[item.filename]
            target = DESTINATION/relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(body)
            target.chmod(expected_mode)
    return {'status': 'PASS', 'manifest_files': len(members), 'zip_members': len(members)+2,
            'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'new': sorted(added),
            'changed': sorted(changed), 'removed': sorted(removed),
            'application_build': 'EXACT_R6_BYTES', 'extracted_root': str(DESTINATION)}


if __name__ == '__main__':
    os.umask(0o077)
    result = audit()
    with ARCHIVE.open('rb') as stream:
        result['archive_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (EVIDENCE/'package-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
