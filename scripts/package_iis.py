#!/usr/bin/python3
"""Create a private portable IIS/Linux artifact from explicit compiled inputs only."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'.runtime', '.git', '__pycache__', 'node_modules', 'retrieval-venv',
             'checkpoints', 'dataset', 'datasets', 'browser-state', '.env'}
FIXED = (
    'config/sqlean-parser-lock.json', 'retrieval/bootstrap_ml.py',
    'retrieval/requirements-ml.lock', 'retrieval/model-lock.json', 'retrieval/model-notice.json',
    'db/migrations/005_expected_catalog.json', 'db/migrations/005_explicit.json',
    'db/document/schema-catalog.sql', 'scripts/warm_worker_image.py',
    'scripts/bootstrap_corpus.py', 'scripts/bootstrap_documents.py',
    '.tools/sqlean/sqlean_pg_grammar', '.tools/sqlean/POSTGRESQL-COPYRIGHT',
    'spec/iis-deployment.json', 'docs/iis-deployment.md',
    'formal/Allow/IisDeployment.lean',
    'gates/deployment/iis-v1/council-disposition.json',
    'gates/deployment/iis-v1/formal-report.json',
)


def regular(path):
    """Require a regular file and reject all symlink path components."""
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('Missing, linked or nonregular package input: ' + str(path))
    return path


def safe_name(name):
    """Reject path escape and private/runtime payload names."""
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or any(part in FORBIDDEN for part in path.parts):
        raise ValueError('Forbidden package member: ' + name)
    if any(part.endswith(('.pyc', '.pem', '.key', '.dump', '.checkpoint', '.pt', '.pth')) for part in path.parts):
        raise ValueError('Forbidden private/binary member: ' + name)


def collect(root, target, frontend):
    """Enumerate narrow source families and compiled outputs, excluding ambient state."""
    members = {}

    def add(name, source):
        safe_name(name)
        if name in members:
            raise ValueError('Duplicate member: ' + name)
        members[name] = regular(source)

    for name in FIXED:
        add(name, root / name)
    add('README.md', root / 'deploy/README.md')
    module_names = ('retrieval/allow_documents/__init__.py', 'retrieval/allow_documents/cli.py', 'retrieval/allow_documents/context_lease.py', 'retrieval/allow_documents/identifiers.py', 'retrieval/allow_documents/identity.py', 'retrieval/allow_documents/migration.py', 'retrieval/allow_documents/store.py', 'retrieval/allow_documents/wire.py', 'retrieval/allow_retrieval/__init__.py', 'retrieval/allow_retrieval/cli.py', 'retrieval/allow_retrieval/common.py', 'retrieval/allow_retrieval/corpus.py', 'retrieval/allow_retrieval/database.py', 'retrieval/allow_retrieval/embedding.py', 'retrieval/allow_retrieval/evaluation.py', 'retrieval/allow_retrieval/importer.py', 'retrieval/allow_retrieval/journal.py', 'retrieval/allow_retrieval/manage.py', 'retrieval/allow_retrieval/migration.py', 'retrieval/allow_retrieval/promotion.py', 'retrieval/allow_retrieval/rag.py', 'retrieval/allow_retrieval/ranking.py', 'retrieval/allow_retrieval/sql_connections.py', 'retrieval/allow_retrieval/sql_context_control.py', 'retrieval/allow_retrieval/sql_context_identity.py', 'retrieval/allow_retrieval/sql_context_journal.py', 'retrieval/allow_retrieval/sql_context_lease.py', 'retrieval/allow_retrieval/sql_context_observer.py', 'retrieval/allow_retrieval/sql_context_protocol.py', 'retrieval/allow_retrieval/sql_guard.py', 'retrieval/allow_retrieval/sql_image.py', 'retrieval/allow_retrieval/sql_image_config.py', 'retrieval/allow_retrieval/sql_image_init.py', 'retrieval/allow_retrieval/sql_inventory.py', 'retrieval/allow_retrieval/sql_proxy.py', 'retrieval/allow_retrieval/training.py')
    for name in module_names:
        add(name, root / name)
    for name in ('deploy/configure.py', 'deploy/windows/Start-Tunnel.ps1',
                 'deploy/windows/Install-Site.ps1', 'deploy/linux/setup.py', 'deploy/linux/service.py'):
        add(name, root / name)
    for source in sorted((target / 'classes').rglob('*')):
        if source.is_file() and 'static' not in source.relative_to(target / 'classes').parts:
            add('backend/target/' + str(source.relative_to(target)), source)
    for source in sorted((target / 'dependency').glob('*.jar')):
        add('backend/target/dependency/' + source.name, source)
    add('backend/target/solver/alloy.jar', target / 'solver/alloy.jar')
    for source in sorted(frontend.rglob('*')):
        if source.is_file():
            if source.suffix not in ('.html', '.js', '.css', '.svg', '.png', '.ico', '.woff', '.woff2', '.txt'):
                raise ValueError('Unexpected frontend artifact: ' + str(source))
            add('backend/target/classes/static/' + str(source.relative_to(frontend)), source)
    required = ('backend/target/classes/dev/allow/backend/AllowApplication.class',
                'backend/target/classes/static/index.html', 'deploy/linux/setup.py', 'deploy/linux/service.py')
    if any(name not in members for name in required) or not list((target / 'dependency').glob('*.jar')):
        raise ValueError('Incomplete application build')
    parser_lock = json.loads((root / 'config/sqlean-parser-lock.json').read_text())
    if hash_file(members['.tools/sqlean/sqlean_pg_grammar']) != parser_lock['binary_sha256']:
        raise ValueError('Pinned parser mismatch')
    if hash_file(members['scripts/warm_worker_image.py']) != '85f217246b6abeab699249f74e97abab586822678e7b573bbf5690588072dca0':
        raise ValueError('Pinned worker helper mismatch')
    return members


def hash_file(path):
    """Stream SHA256 without buffering jars or parser executables."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build(root, target, frontend, output):
    """Write a new archive atomically with deterministic names and a bound manifest."""
    members = collect(root, target, frontend)
    manifest = {'schema': 1, 'id': 'allow-iis-linux-private-v1',
                'scope': 'Operator-private artifact; target acceptance remains OPEN',
                'files': {name: hash_file(source) for name, source in sorted(members.items())}}
    raw = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    output = Path(os.path.abspath(output))
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a new path')
    if any(p.is_symlink() for p in output.parents):
        raise ValueError('Linked output parent rejected')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, source in sorted(members.items()):
                archive.write(source, name)
            archive.writestr('MANIFEST.json', raw)
            archive.writestr('MANIFEST.sha256', hashlib.sha256(raw).hexdigest() + '  MANIFEST.json\n')
        with zipfile.ZipFile(output) as archive:
            for name, expected in manifest['files'].items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                    raise ValueError('Post-write package mismatch')
        checksum = output.with_suffix(output.suffix + '.sha256')
        with checksum.open('x') as stream:
            stream.write(hash_file(output) + '  ' + output.name + '\n')
        checksum.chmod(0o600)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {'package': str(output), 'sha256': hash_file(output), 'files': len(members), 'bytes': output.stat().st_size}


def main():
    """Require isolated backend/frontend build paths and a fresh output location."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-target', type=Path, required=True)
    parser.add_argument('--frontend-dist', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.backend_target, args.frontend_dist, args.output), indent=2))


if __name__ == '__main__':
    main()
