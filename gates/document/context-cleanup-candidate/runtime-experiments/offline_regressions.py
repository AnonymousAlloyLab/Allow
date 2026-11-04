#!/usr/bin/env python3
"""Run explicitly selected offline regressions against a frozen copied installation.

The real psycopg entry point is denied for the duration. Wire tests own synthetic
backends and parser tests use the copied pinned executable; neither opens PG.
This finite regression report does not close the 33-case runtime contract.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


def digest(path):
    """Hash one declared local input without following a caller-provided SQL route."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    """Write a new evidence artifact and refuse to overwrite earlier evidence."""
    with path.open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
    path.chmod(0o600)


def check_sources(root, receipt):
    """Require every frozen source-ready byte to remain identical."""
    mismatches = []
    for entry in receipt['files']:
        path = root / entry['path']
        if not path.is_file() or digest(path) != entry['sha256']:
            mismatches.append(entry['path'])
    return mismatches


def deny_database(*arguments, **keywords):
    """Fail before any accidental real PostgreSQL connection can be attempted."""
    raise AssertionError('offline_regression_forbids_real_postgresql_connection')


def check_extra_inputs(registration):
    """Bind gate-local test helpers and the declared managed tooling manifest."""
    return [entry['path'] for entry in registration['additional_inputs']
            if digest(Path(entry['path'])) != entry['sha256']]


class RecordedResult(unittest.TextTestResult):
    """Retain finite test identifiers and outcomes alongside the exact text log."""
    def __init__(self, *arguments, **keywords):
        super().__init__(*arguments, **keywords)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'id': test.id(), 'status': 'PASS'})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.records.append({'id': test.id(), 'status': 'FAIL'})

    def addError(self, test, error):
        super().addError(test, error)
        self.records.append({'id': test.id(), 'status': 'ERROR'})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({'id': test.id(), 'status': 'SKIP', 'reason': reason})


def main():
    """Execute only the frozen offline selection, record inventory, and bind inputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', required=True, type=Path)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    root, output = Path(registration['copied_root']), Path(registration['output'])
    receipt_path = Path(registration['source_ready'])
    receipt = json.loads(receipt_path.read_text())
    if root.parent != Path('/tmp') or not root.name.startswith('allow-cc-'):
        raise ValueError('isolated_copied_root_required')
    if digest(Path(__file__)) != registration['driver_sha256']:
        raise ValueError('driver_changed_after_registration')
    if digest(receipt_path) != registration['source_ready_sha256']:
        raise ValueError('source_ready_changed_after_registration')
    before = check_sources(root, receipt)
    if before or check_extra_inputs(registration):
        raise ValueError('copied_source_mutation:' + ','.join(before))
    output.mkdir(mode=0o700)
    sys.path[:0] = [str(root/'retrieval/tests'), str(root/'retrieval'), str(root/'scripts')]
    sys.path.insert(0, str(Path(__file__).parent))
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTHONPATH'] = str(root/'retrieval')
    started = datetime.now(timezone.utc).isoformat()
    with (output/'tests.log').open('x') as stream, patch('psycopg.connect', deny_database):
        suite = unittest.defaultTestLoader.loadTestsFromNames(registration['selection'])
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
    from verify_sql_clients import inventory
    scanned = inventory()
    write(output/'sql-client-inventory.json', scanned)
    after = check_sources(root, receipt)
    active = check_sources(Path(registration['active_root']), receipt)
    extra = check_extra_inputs(registration)
    passed = result.wasSuccessful() and not result.skipped and not after and not active and not extra
    passed = passed and scanned['status'] == 'PASS'
    report = {'status': 'PASS' if passed else 'BLOCKED', 'started_utc': started,
              'registration_sha256': digest(args.registration),
              'source_ready_sha256': digest(receipt_path), 'copied_root': str(root),
              'test_count': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped),
              'test_outcomes': result.records, 'source_mismatches_before': before,
              'source_mismatches_after': after, 'active_source_mismatches_after': active,
              'additional_input_mismatches_after': extra,
              'sql_client_inventory_status': scanned['status'],
              'artifacts': {name: digest(output/name) for name in ('tests.log', 'sql-client-inventory.json')},
              'boundary': registration['boundary']}
    write(output/'report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'test_count', 'failures', 'errors', 'skipped')}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
