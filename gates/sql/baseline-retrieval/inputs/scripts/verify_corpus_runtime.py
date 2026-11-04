#!/usr/bin/env python3
"""Execute the finite local corpus tests; failures or skipped required tests never pass."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def fingerprint():
    """Bind the test run to authored runtime inputs, locks and compiled Java resources."""
    paths = []
    for name in ['backend/src', 'frontend/src', 'db/migrations', 'retrieval', 'backend/target/classes']:
        paths.extend(p for p in (ROOT / name).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths.append(Path(__file__))
    files = [{'path':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(set(paths))]
    root = hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
    return files, root


def main():
    """Require real local database/model dependencies and record the complete executable test outcome."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'gates/retrieval/runtime-tests.json')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'retrieval'))
    files, before = fingerprint()
    suite = unittest.defaultTestLoader.discover(str(ROOT/'retrieval/tests'), pattern='test_*.py')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    _, after = fingerprint()
    passed = result.wasSuccessful() and not result.skipped and before == after
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix('.log')
    log_path.write_text(log.getvalue())
    report = {'status':'PASS' if passed else 'FAIL',
              'classification':'EXECUTED_IMPLEMENTATION_TESTS_NOT_FORMAL_REFINEMENT',
              'timestamp_utc':datetime.now(timezone.utc).isoformat(),
              'python':sys.version, 'tests':result.testsRun,
              'failures':len(result.failures), 'errors':len(result.errors),
              'skipped':len(result.skipped), 'source_unchanged':before == after,
              'input_root_sha256':before, 'files':files,
              'log_sha256':hashlib.sha256(log_path.read_bytes()).hexdigest(),
              'limitations':['Tests exercise finite fixtures, not universal Java/Python/SQL refinement',
                             'Synthetic test models/vectors are isolated under unique RLS tenant IDs',
                             'Corpus quality is measured separately on the frozen family split']}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(log.getvalue())
    print(json.dumps({k:report[k] for k in ['status','tests','failures','errors','skipped','source_unchanged','input_root_sha256']},indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
