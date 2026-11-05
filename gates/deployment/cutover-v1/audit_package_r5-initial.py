"""Bind the separate-install candidate to its predecessor and test safe extraction."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'dist/allow-iis-wsl-anonymous-20261104-r5.zip'
DESTINATION = Path('/tmp/allow-anonymous-package-r5')
CHANGED = {
    'README.md', 'docs/wsl-anonymous-deployment.md', 'deploy/configure.py',
    'deploy/linux/setup.py', 'deploy/linux/service.py', 'deploy/linux/trust.py',
    'deploy/linux/wsl_keepalive.py', 'deploy/windows/Start-Wsl.ps1',
    'deploy/windows/Test-Wsl.ps1',
}
ADDED = {
    'spec/staged-public-cutover.json', 'formal/Allow/StagedPublicCutover.lean',
    'gates/deployment/cutover-v1/council-disposition.json',
    'gates/deployment/cutover-v1/formal-report.json', 'docs/staged-public-cutover.md',
    'deploy/linux/public_guard.py', 'deploy/linux/check_public.py',
}


def digest(path):
    """Hash a local regular artifact for the evidence record."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit():
    """Verify the exact intended delta and every ZIP byte/mode before extraction."""
    with zipfile.ZipFile(ARCHIVE) as archive, zipfile.ZipFile(
            ROOT / 'dist/allow-iis-wsl-anonymous-20261104-r4.zip') as previous:
        raw = archive.read('MANIFEST.json')
        members = json.loads(raw)['files']
        prior = json.loads(previous.read('MANIFEST.json'))['files']
        assert set(members) - set(prior) == ADDED
        assert not set(prior) - set(members)
        assert {name for name in prior if prior[name] != members[name]} == CHANGED
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(members) | {'MANIFEST.json', 'MANIFEST.sha256'}
        assert archive.read('MANIFEST.sha256').decode().split()[0] == hashlib.sha256(raw).hexdigest()
        for name in CHANGED | ADDED:
            source = ROOT / ('deploy/README.md' if name == 'README.md' else name)
            assert members[name] == digest(source), name
        DESTINATION.mkdir(mode=0o700, exist_ok=False)
        for item in archive.infolist():
            relative = Path(item.filename)
            assert not relative.is_absolute() and '..' not in relative.parts
            assert not {'.runtime', '__pycache__', 'node_modules', '.git'} & set(relative.parts)
            mode = 0o755 if item.filename == '.tools/sqlean/sqlean_pg_grammar' else 0o644
            assert item.external_attr >> 16 == 0o100000 | mode
            body = archive.read(item)
            if item.filename in members:
                assert hashlib.sha256(body).hexdigest() == members[item.filename]
            target = DESTINATION / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(body)
            target.chmod(mode)
    return {'status': 'PASS', 'manifest_files': len(members),
            'zip_members': len(members) + 2, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'changed_from_r4': sorted(CHANGED), 'added_from_r4': sorted(ADDED),
            'unchanged_manifest_files': len(prior) - len(CHANGED),
            'application_retrieval_database_parser_bytes_identical_to_r4': True,
            'application_artifact_count': sum(name.startswith('backend/target/') for name in members),
            'extracted_root': str(DESTINATION)}


def render(slot, name):
    """Render an isolated configuration; fixed public paths are never created."""
    output = DESTINATION / ('generated-' + name)
    command = ['/usr/bin/python3', '-I', '-B', str(DESTINATION / 'deploy/configure.py'),
               '--origin', 'https://allow.alloy4.fun', '--access-mode', 'ANONYMOUS',
               '--transport', 'wsl', '--backend-port', '18081', '--tunnel-port', '18081',
               '--installation-slot', slot, '--output', str(output)]
    if slot == 'PUBLIC_REPLACEMENT':
        command += ['--install-root', '/opt/allow-public', '--account', 'allow-public']
    else:
        command += ['--install-root', str(DESTINATION), '--account', 'allow']
    subprocess.run(command, check=True, timeout=15)
    config = DESTINATION / 'deploy' / (name + '-instance.json')
    config.write_bytes((output / 'linux/instance.json').read_bytes())
    config.chmod(0o600)
    return config


def preflight():
    """Check PRIMARY prerequisites and actual replacement denial before effects."""
    primary = render('PRIMARY', 'primary')
    result = subprocess.run(['/usr/bin/python3', '-I', '-B',
                             str(DESTINATION / 'deploy/linux/setup.py'), '--config', str(primary)],
                            capture_output=True, text=True, timeout=30)
    (EVIDENCE / 'package-primary-preflight-r5.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0
    public = render('PUBLIC_REPLACEMENT', 'public')
    denials = []
    for entry, extra in [('check_public.py', []), ('setup.py', ['--initialize']), ('service.py', [])]:
        command = ['/usr/bin/python3', '-I', '-B', str(DESTINATION / 'deploy/linux' / entry),
                   '--config', str(public), *extra]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        (EVIDENCE / ('package-public-' + entry + '-denial-r5.log')).write_text(result.stdout + result.stderr)
        assert result.returncode != 0
        assert 'Invalid public replacement tuple' in result.stderr
        assert not (DESTINATION / '.runtime').exists()
        assert not (DESTINATION / '.tools/retrieval').exists()
        assert not (DESTINATION / '.tools/retrieval-venv').exists()
        denials.append(entry)
    return {'primary_host_prerequisites': 'PASS', 'public_wrong_root_denied_before_runtime': denials,
            'sql_started': False, 'runtime_created': False,
            'native_public_account_systemd_wsl_iis': 'OPEN'}


if __name__ == '__main__':
    os.umask(0o077)
    result = audit()
    result['preflight'] = preflight()
    result['archive_sha256'] = digest(ARCHIVE)
    assert ARCHIVE.with_suffix('.zip.sha256').read_text().split()[0] == result['archive_sha256']
    (EVIDENCE / 'package-audit-r5.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
