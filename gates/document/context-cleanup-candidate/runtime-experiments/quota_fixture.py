"""Construct the CC29 storage-shaped quota witness only in a frozen copied root.

These rows reproduce VC19 storage accounting; they are not Alloy admissions.
Database operations are deferred until explicit setup/injection calls. Every
connection uses the copied canonical SQLeanParser route. The supervisor must
also impose the 600-second setup deadline on blocked transport operations.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import uuid

from allow_documents import wire

COUNT = 4096
BUDGET = 268435456
ACCOUNTED_BYTES = 268434782
ARTIFACT_BYTES = 115323865
TEXT_BYTEA_BYTES = 230655922
POLICY = 'vc19-storage-shaped-v1'
SETUP_SECONDS = 600
TABLES = ('workspace', 'logical_launch', 'document', 'artifact', 'revision', 'receipt', 'admission')


def identifier(seed, label):
    """Derive the original fixed-length, canonical UUIDv4-shaped fixture IDs."""
    return 'server:' + str(uuid.UUID(bytes=uuid.uuid5(uuid.UUID(seed), label).bytes, version=4))


def empty_module():
    """Return the precise collection shape used by the prior VC19 witness."""
    return {'version': 1, 'signatures': [], 'fields': [], 'predicates': [], 'facts': [],
            'assertions': [], 'commands': [], 'nodes': []}


def fixture(config, index, padding):
    """Reproduce exact artifact, original request, outcome and per-revision charge."""
    module = empty_module()
    server = identifier(config['seed'], 'definition-' + str(index))
    draft = 'draft:' + str(uuid.UUID(bytes=uuid.uuid5(uuid.UUID(config['seed']), 'draft-' + str(index)).bytes, version=4))
    if index:
        module['signatures'] = [{'tag': 'signature', 'id': server, 'name': 'Profile', 'multiplicity': 'set'}]
    source = '' if index == 0 else '//' + padding + '\nsig Profile {}\n'
    artifact = {'artifactId': identifier(config['seed'], 'artifact-' + str(index)), 'mode': 'BLOCK_SUPPORTED',
                'source': source, 'sourceHash': hashlib.sha256(source.encode()).hexdigest(), 'module': module,
                'occurrences': [], 'trivia': [], 'analysisDescriptors': [], 'policyVersion': POLICY,
                'dependencyHash': hashlib.sha256(b'not-an-Alloy-runtime-validation').hexdigest()}
    key = uuid.uuid5(uuid.UUID(config['seed']), 'key-' + str(index)).hex
    body = original_request(config, index, source, module, draft, key)
    mapping = {} if index < 2 else {draft: server}
    outcome = {'protocol': 1, 'requestId': str(uuid.uuid5(uuid.UUID(config['seed']), 'response-' + str(index))),
               'status': 'COMMITTED', 'data': {'documentId': config['document'], 'revision': index,
               'artifact': artifact, 'idRemapping': mapping}}
    artifact_bytes, request_bytes, outcome_bytes = wire.encode(artifact), wire.encode(body), wire.encode(outcome)
    wire.artifact(artifact, POLICY)
    charge = 2 * len(request_bytes) + len(outcome_bytes) + len(artifact_bytes) + 8192
    return artifact, artifact_bytes, request_bytes, outcome_bytes, key, charge


def original_request(config, index, source, module, draft, key):
    """Preserve the VC19 CREATE/SOURCE/BLOCK_SUPPORTED request byte shapes."""
    if index == 0:
        return {'idempotencyKey': key, 'title': 'VC19 storage-shaped fixture'}
    if index == 1:
        return {'idempotencyKey': key, 'expectedRevision': index - 1,
                'candidate': {'mode': 'SOURCE', 'source': source}}
    candidate = json.loads(json.dumps(module))
    candidate['signatures'][0]['id'] = draft
    return {'idempotencyKey': key, 'expectedRevision': index - 1,
            'candidate': {'mode': 'BLOCK_SUPPORTED', 'module': candidate, 'presentationCopies': []}}


def check_deadline(deadline):
    """Reject setup work that has reached its fixed monotonic time budget."""
    if time.monotonic() >= deadline:
        raise TimeoutError('fixture_setup_budget')


def padding_for(config, deadline=None):
    """Calculate the prior fixed-width padding without changing quota or source bounds."""
    baseline = 0
    for index in range(COUNT):
        if deadline is not None:
            check_deadline(deadline)
        baseline += fixture(config, index, '')[-1]
    width = (BUDGET - baseline) // (2 * COUNT)
    if not 0 < width < 32740:
        raise ValueError('fixture_source_padding_bound')
    padding = base64.b64encode(hashlib.shake_256(config['seed'].encode()).digest(width)).decode()[:width]
    return padding, width


def copied_root():
    """Require this exact generator inside a private, manifest-bound isolated copy."""
    from allow_retrieval.common import ROOT
    root = ROOT.resolve()
    script = Path(__file__).resolve()
    if root.parent != Path('/tmp') or not root.name.startswith('allow-cc-') or script.parent != root / '.gate':
        raise ValueError('quota_fixture_isolated_root_required')
    metadata = root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700 or metadata.st_uid != os.getuid():
        raise ValueError('quota_fixture_private_root_required')
    manifest = json.loads((root / '.gate/manifest.json').read_text())
    expected = [row['sha256'] for row in manifest['files'] if row['path'] == '.gate/quota_fixture.py']
    if manifest['copied_root'] != str(root) or expected != [hashlib.sha256(script.read_bytes()).hexdigest()]:
        raise ValueError('quota_fixture_manifest_mismatch')
    return root


def require_empty_schema(deadline):
    """Check all seven document tables globally through the canonical admin proxy."""
    from allow_retrieval.sql_connections import connect
    with connect(admin=True, client='allow-tests') as connection:
        if connection.info.dbname != 'allow_retrieval':
            raise ValueError('quota_fixture_canonical_database_required')
        for table in TABLES:
            check_deadline(deadline)
            if connection.execute('SELECT count(*) FROM documents.' + table).fetchone()[0] != 0:
                raise ValueError('quota_fixture_requires_empty_document_schema')
    check_deadline(deadline)


def insert_revision(connection, store, config, index, value, owner):
    """Write one storage-shaped revision using the caller's scoped Store transaction."""
    artifact, raw, request, outcome, key, _ = value
    scope = (store.principal, store.workspace)
    namespace = 'CREATE' if index == 0 else config['document']
    route = '/api/v1/documents' if index == 0 else '/api/v1/documents/' + config['document'] + '/commit'
    connection.execute('INSERT INTO documents.artifact(principal_id,workspace_id,document_id,artifact_id,content,source_hash,policy_version) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                       (*scope, config['document'], artifact['artifactId'], raw, artifact['sourceHash'], POLICY))
    connection.execute('INSERT INTO documents.revision(principal_id,workspace_id,document_id,revision,artifact_id) VALUES(%s,%s,%s,%s,%s)',
                       (*scope, config['document'], index, artifact['artifactId']))
    connection.execute('INSERT INTO documents.receipt(principal_id,workspace_id,launch_id,namespace,request_key,method,route,request_bytes,request_hash,outcome,outcome_code,result_document_id,result_revision) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                       (*scope, store.launch, namespace, key, 'POST', route, request, hashlib.sha256(request).hexdigest(), outcome, 'COMMITTED', config['document'], index))
    connection.execute('INSERT INTO documents.admission(principal_id,workspace_id,launch_id,namespace,request_key,method,route,request_bytes,operation,document_id,expected_revision,owner_pid,owner_start,owner_nonce,state,reservation_bytes,reservation_documents,reservation_revisions) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0)',
                       (*scope, store.launch, namespace, key, 'POST', route, request, 'CREATE' if index == 0 else 'COMMIT', config['document'], None if index == 0 else index - 1, *owner, str(uuid.uuid4()), 'TERMINAL'))


def populate(store, config, padding, deadline):
    """Insert the exact full fixture in one scoped transaction, rolling back on failure."""
    from allow_documents import identity
    sums = {'artifact_bytes': 0, 'request_bytes_once': 0, 'outcome_bytes': 0, 'accounted_bytes': 0}
    hashes = []
    owner = (os.getpid(), identity.process_start(os.getpid()))
    if owner[1] is None:
        raise RuntimeError('fixture_writer_identity_missing')
    with store.transaction() as connection:
        connection.execute('INSERT INTO documents.document(principal_id,workspace_id,document_id,title,head_revision) VALUES(%s,%s,%s,%s,%s)',
                           (store.principal, store.workspace, config['document'], 'VC19 storage-shaped', COUNT - 1))
        for index in range(COUNT):
            check_deadline(deadline)
            value = fixture(config, index, padding)
            insert_revision(connection, store, config, index, value, owner)
            _, raw, request, outcome, _, charge = value
            hashes.append(hashlib.sha256(raw).hexdigest())
            for field, size in (('artifact_bytes', len(raw)), ('request_bytes_once', len(request)),
                                ('outcome_bytes', len(outcome)), ('accounted_bytes', charge)):
                sums[field] += size
        check_deadline(deadline)
        if sums['accounted_bytes'] != ACCOUNTED_BYTES or sums['artifact_bytes'] != ARTIFACT_BYTES:
            raise ValueError('fixture_exact_charge_mismatch')
        connection.execute('UPDATE documents.workspace SET document_count=1,revision_count=%s,receipt_count=%s,accounted_bytes=%s',
                           (COUNT, COUNT, sums['accounted_bytes']))
    check_deadline(deadline)
    return sums, hashes


def verify_counts(store, sums, deadline):
    """Measure actual relation counts and stored bytes; reject any accounting mismatch."""
    check_deadline(deadline)
    with store.transaction() as connection:
        actual = connection.execute('SELECT (SELECT count(*) FROM documents.document) AS documents, (SELECT count(*) FROM documents.revision) AS revisions, (SELECT count(*) FROM documents.artifact) AS artifacts, (SELECT count(*) FROM documents.receipt) AS receipts, (SELECT count(*) FROM documents.admission) AS admissions, (SELECT sum(octet_length(content)) FROM documents.artifact) AS artifact_bytes, (SELECT sum(octet_length(request_bytes)) FROM documents.receipt) AS receipt_request_bytes, (SELECT sum(octet_length(outcome)) FROM documents.receipt) AS outcome_bytes, (SELECT sum(octet_length(request_bytes)) FROM documents.admission) AS admission_request_bytes, (SELECT accounted_bytes FROM documents.workspace) AS accounted_bytes, (SELECT head_revision FROM documents.document) AS head_revision').fetchone()
    expected = {'documents': 1, 'revisions': COUNT, 'artifacts': COUNT, 'receipts': COUNT, 'admissions': COUNT,
                'artifact_bytes': sums['artifact_bytes'], 'receipt_request_bytes': sums['request_bytes_once'],
                'outcome_bytes': sums['outcome_bytes'], 'admission_request_bytes': sums['request_bytes_once'],
                'accounted_bytes': ACCOUNTED_BYTES, 'head_revision': COUNT - 1}
    if actual != expected:
        raise ValueError('fixture_database_counts_mismatch')
    check_deadline(deadline)
    return {key: int(value) for key, value in actual.items()}


def finish_config(config, padding, sums, hashes):
    """Bind exact expected context output and full-history row multiset privately."""
    inventory = {identifier(config['seed'], 'definition-' + str(index)): 'signature' for index in range(1, COUNT)}
    absent = identifier(config['seed'], 'definition-0')
    wanted = sorted([*inventory, absent])
    if len(set(wanted)) != COUNT or absent in inventory:
        raise ValueError('fixture_inventory_shape')
    base = fixture(config, 0, padding)
    config.update(revision=0, artifact=base[0], wanted=wanted, expected_inventory=inventory,
                  absent_id=absent, expected_base_sha256=hashlib.sha256(base[1]).hexdigest(),
                  artifact_bytes=sums['artifact_bytes'], head_observed=COUNT - 1,
                  row_multiset_sha256=hashlib.sha256('\n'.join(sorted(hashes)).encode()).hexdigest(),
                  fixture_row_hashes_by_revision=hashes, source_padding_bytes=len(padding))
    return config


def setup_fixture():
    """Return private expected context and public counts for a fresh canonical database."""
    from allow_documents import identity
    from allow_documents.store import Store
    started = time.monotonic()
    deadline = started + SETUP_SECONDS
    root = copied_root()
    scope = identity.load()
    require_empty_schema(deadline)
    config = {'seed': str(uuid.uuid5(uuid.UUID(scope['workspaceId']), 'CC29-storage-shaped-v1')),
              'document': wire.fresh_id(), 'scope': scope, 'copied_root': str(root)}
    padding, width = padding_for(config, deadline)
    store = Store()
    if store.initialize(POLICY) != {'status': 'READY', 'policyVersion': POLICY}:
        raise ValueError('fixture_policy_initialization')
    sums, hashes = populate(store, config, padding, deadline)
    actual = verify_counts(store, sums, deadline)
    config = finish_config(config, padding, sums, hashes)
    check_deadline(deadline)
    counts = {'fixture_kind': 'storage-shaped-not-Alloy-admissions', 'revisions': COUNT,
              'target_accounted_bytes': BUDGET, 'unused_target_bytes': BUDGET - ACCOUNTED_BYTES,
              'source_padding_bytes': width, 'expected_text_bytea_bytes': TEXT_BYTEA_BYTES,
              'raw_row_bytes_status': 'EXPECTED_ONLY_UNTIL_ACTUAL_LIBPQ_TELEMETRY',
              'requested_ids': COUNT, 'known_requested_ids': COUNT - 1, 'absent_requested_ids': 1,
              'actual_database_counts_and_bytes': actual, 'setup_elapsed_seconds': time.monotonic() - started,
              'setup_deadline_seconds': SETUP_SECONDS, **sums}
    return config, counts


def conflict_bytes(config):
    """Prepare a same-size intentional historical kind collision without asserting row order."""
    padding, _ = padding_for(config)
    target = fixture(config, COUNT - 1, padding)
    mutated = json.loads(target[1])
    focus = identifier(config['seed'], 'definition-1')
    mutated['module']['signatures'][0].update(id=focus, tag='predicate')
    raw = wire.encode(mutated)
    wire.artifact(mutated, POLICY)
    if len(raw) != len(target[1]):
        raise ValueError('fixture_conflict_charge_changed')
    return target[0]['artifactId'], target[1], raw, focus


def add_late_conflict(config):
    """Inject one declared corruption through scoped canonical admin SQL; require trace proof later."""
    from allow_documents import identity
    from allow_retrieval.sql_connections import connect
    if str(copied_root()) != config['copied_root'] or identity.load() != config['scope']:
        raise ValueError('fixture_conflict_scope_mismatch')
    artifact, before, after, focus = conflict_bytes(config)
    scope = config['scope']
    with connect(admin=True, client='allow-tests') as connection:
        connection.execute("SELECT set_config('allow.tenant',%s,true)", (scope['principalId'],))
        connection.execute("SELECT set_config('allow.project',%s,true)", (scope['workspaceId'],))
        connection.execute("SELECT set_config('allow.purpose',%s,true)", ('document',))
        changed = connection.execute('UPDATE documents.artifact SET content=%s WHERE principal_id=%s AND workspace_id=%s AND document_id=%s AND artifact_id=%s AND content=%s',
                                     (after, scope['principalId'], scope['workspaceId'], config['document'], artifact, before))
        if changed.rowcount != 1:
            raise ValueError('fixture_conflict_expected_row_missing')
    updated = dict(config)
    hashes = list(config['fixture_row_hashes_by_revision'])
    hashes[-1] = hashlib.sha256(after).hexdigest()
    updated.update(focus_id=focus, expected_matching_row_sha256=config['fixture_row_hashes_by_revision'][1],
                   expected_conflict_row_sha256=hashlib.sha256(after).hexdigest(),
                   replaced_row_sha256=hashlib.sha256(before).hexdigest(),
                   fixture_row_hashes_by_revision=hashes,
                   row_multiset_sha256=hashlib.sha256('\n'.join(sorted(hashes)).encode()).hexdigest(),
                   matching_fixture_revision=1, conflict_fixture_revision=COUNT - 1,
                   required_conflict_order='actual matching row index < actual conflicting row index',
                   observed_conflict_order=None, conflict_kind='signature-versus-predicate',
                   declared_writer='intentional same-byte-length artifact corruption; not an Alloy-valid admission')
    return updated
