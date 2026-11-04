#!/usr/bin/env python3
"""Execute the complete copied Python test discovery, with skips failing acceptance."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'retrieval/tests'), str(ROOT/'retrieval')]


def main():
    """Retain every discovered test outcome without printing credentials or test fixtures."""
    from offline_regressions import RecordedResult
    suite = unittest.defaultTestLoader.discover(str(ROOT/'retrieval/tests'))
    output = Path(sys.argv[1])
    with output.with_suffix('.log').open('x') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
    passed = result.wasSuccessful() and not result.skipped
    value = {'status': 'PASS' if passed else 'BLOCKED', 'tests': result.testsRun,
             'failures': len(result.failures), 'errors': len(result.errors),
             'skipped': len(result.skipped), 'test_outcomes': result.records,
             'selection': 'unittest discover retrieval/tests, all test*.py files, no exclusions',
             'scope': 'Fresh copied owned cluster; all SQL uses canonical copied SQLeanParser route.'}
    with output.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value[key] for key in ('status', 'tests', 'failures', 'errors', 'skipped')}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
