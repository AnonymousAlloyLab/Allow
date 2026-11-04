"""Check the exact inherited190 fixture bytes and explicit fresh/warm route split."""
import json
from pathlib import Path

from harness_common import digest, read_private


def verify(gate):
    """Reject partial, surplus, rerouted or changed fixture inventories."""
    plan = read_private(gate/'semantic-fixtures.json')
    rows = plan['fixtures']
    if len(rows) != 190 or len({row['path'] for row in rows}) != 190 or len({row['name'] for row in rows}) != 190:
        raise ValueError('semantic_exact190_unique_required')
    counts = {'VALIDATE': 0, 'REVALIDATE': 0}
    for row in rows:
        path = Path(row['path'])
        if path.parent != Path('fixtures/semantic') or path.name != row['name']+'.json':
            raise ValueError('semantic_fixture_path')
        actual = gate/path
        if actual.is_symlink() or digest(actual) != row['sha256'] or actual.stat().st_size != row['bytes']:
            raise ValueError('semantic_fixture_identity')
        request = json.loads(actual.read_bytes())
        operation = request['operation']
        expected = 'warm-advisory' if operation == 'VALIDATE' else 'fresh-revalidate'
        if operation not in counts or row['operation'] != operation or row['W0_route'] != 'fresh-default' or row['W1_route'] != expected:
            raise ValueError('semantic_fixture_route')
        counts[operation] += 1
    if counts != {'VALIDATE': 153, 'REVALIDATE': 37}:
        raise ValueError('semantic_operation_counts')
    excluded = [row for row in rows if row.get('comparison') == 'NOT_COMPARABLE']
    if len(excluded) != 1 or excluded[0]['name'] != 'context-invalid-policyVersion':
        raise ValueError('semantic_exact_preregistered_domain_gap')
    if excluded[0]['expectedStatus'] != 'UNAVAILABLE' or excluded[0]['expectedW1Outcome'] != 'BINDING_INPUT_REJECTED':
        raise ValueError('semantic_original_expectation_changed')
    actual = {str(path.relative_to(gate)) for path in (gate/'fixtures/semantic').rglob('*') if path.is_file()}
    if actual != {row['path'] for row in rows}:
        raise ValueError('semantic_fixture_surplus_or_missing')
    return {'status': 'CHECKED', 'count': 190, 'operations': counts, 'manifest_sha256': digest(gate/'semantic-fixtures.json')}
