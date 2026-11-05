"""Read-only comparison of frozen R6 application payload and isolated build inputs."""
from pathlib import Path
import hashlib
import json
import zipfile

BASE = Path('/home/augustus/Allow')
BACKEND = Path('/tmp/allow-security-drag-build/backend/target')
FRONTEND = Path('/tmp/allow-security-drag-build/frontend/dist')
ARCHIVE = BASE / 'dist/allow-iis-linux-private-20261104-r6.zip'


def main():
    """Compare every shipped application member without reading runtime state."""
    entries = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith('backend/target/'):
                continue
            relative = name.removeprefix('backend/target/')
            if relative.startswith('classes/static/'):
                source = FRONTEND / relative.removeprefix('classes/static/')
            else:
                source = BACKEND / relative
            shipped = hashlib.sha256(archive.read(name)).hexdigest()
            actual = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() and not source.is_symlink() else None
            entries.append({'member': name, 'source': str(source), 'archive_sha256': shipped,
                            'input_sha256': actual, 'match': actual == shipped})
    mismatches = [entry['member'] for entry in entries if not entry['match']]
    inventory = json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
    report = {'status': 'PASS' if entries and not mismatches else 'FAIL',
              'archive': str(ARCHIVE), 'archive_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
              'backend_input': str(BACKEND), 'frontend_input': str(FRONTEND),
              'compared_members': len(entries), 'mismatches': mismatches,
              'comparison_inventory_sha256': hashlib.sha256(inventory).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Exact application payload identity only; deployment changes require their own checks.',
              'entries': entries}
    destination = BASE / 'gates/deployment/public-iis-v1/reused-build-inputs.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'entries'}))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
