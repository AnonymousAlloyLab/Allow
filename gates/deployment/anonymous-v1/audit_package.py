"""Verify the anonymous candidate and extract only into a fresh owned directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'dist/allow-iis-wsl-anonymous-20261104-r3.zip'
DESTINATION = Path('/tmp/allow-anonymous-package-r3')


def audit():
    """Check every archive byte, mode and required public input before extraction."""
    with zipfile.ZipFile(ARCHIVE) as archive:
        raw = archive.read('MANIFEST.json')
        manifest = json.loads(raw)
        members = manifest['files']
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(members) | {'MANIFEST.json', 'MANIFEST.sha256'}
        assert archive.read('MANIFEST.sha256').decode().split()[0] == hashlib.sha256(raw).hexdigest()
        required = json.loads((EVIDENCE / 'package-input-audit-r3.json').read_text())['required_inputs']
        assert all(members.get(name) == digest for name, digest in required.items())
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
    return {'status': 'PASS', 'manifest_files': len(members), 'zip_members': len(members) + 2,
            'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'extracted_root': str(DESTINATION)}


def preflight():
    """Render the selected nonsecret target and verify without initialization or SQL."""
    generated = DESTINATION / 'generated-instance'
    subprocess.run(['/usr/bin/python3', '-I', '-B', str(DESTINATION / 'deploy/configure.py'),
                    '--origin', 'https://allow.alloy4.fun', '--access-mode', 'ANONYMOUS',
                    '--transport', 'wsl', '--backend-port', '18081', '--tunnel-port', '18081',
                    '--install-root', '/opt/allow', '--account', 'allow', '--output', str(generated)], check=True)
    config = DESTINATION / 'deploy/instance.json'
    config.write_bytes((generated / 'linux/instance.json').read_bytes())
    config.chmod(0o600)
    command = ['/usr/bin/python3', '-I', '-B', str(DESTINATION / 'deploy/linux/setup.py'), '--config', str(config)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (EVIDENCE / 'package-preflight-r3.log').write_text(completed.stdout + completed.stderr)
    assert completed.returncode == 0, 'preflight failed; see retained log'
    assert not (DESTINATION / '.runtime').exists()
    return {'status': 'PASS', 'sql_started': False, 'runtime_created': False,
            'native_windows_wsl_iis': 'OPEN', 'generated_configuration': str(generated)}


if __name__ == '__main__':
    os.umask(0o077)
    result = audit()
    result['preflight'] = preflight()
    with ARCHIVE.open('rb') as stream:
        result['archive_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (EVIDENCE / 'package-audit-r3.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
