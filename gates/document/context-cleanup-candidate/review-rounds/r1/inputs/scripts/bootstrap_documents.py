#!/usr/bin/env python3
"""Bootstrap separate documents schema through the existing SQL parser proxy."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'retrieval'))
from allow_documents import identity
from allow_documents.migration import migrate, has_existing_store
from allow_documents.store import Store


def main():
    """Refuse identity replacement for any nonempty store, then initialize scope."""
    migrate()
    path = identity.DIRECTORY / 'identity.json'
    if not path.exists() and has_existing_store():
        raise RuntimeError('missing_identity_for_nonempty_document_store')
    identity.provision()
    result = Store().initialize('document-v1')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
