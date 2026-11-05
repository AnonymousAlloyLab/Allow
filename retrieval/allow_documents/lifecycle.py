"""Closed anonymous lifecycle registry; every SQL statement uses the pinned proxy."""
import uuid
from psycopg.rows import dict_row
from allow_retrieval.sql_connections import connect
from allow_retrieval.sql_context_protocol import PUBLIC_TIMEOUT_SQL
from . import context_lease, identity, wire

REGISTRY_DDL = '''CREATE TABLE IF NOT EXISTS documents.public_workspace_lifecycle (
 principal_id text NOT NULL, workspace_id text NOT NULL, launch_id text NOT NULL,
 incarnation text NOT NULL, expires_at_ms bigint NOT NULL CHECK(expires_at_ms>0),
 policy_version text NOT NULL, state text NOT NULL CHECK(state IN ('PROVISIONING','READY','QUARANTINED')),
 PRIMARY KEY(principal_id,workspace_id), UNIQUE(launch_id))'''
SCOPE_WHERE = 'principal_id=%s AND workspace_id=%s'


def canonical_uuid(value):
    """Reject noncanonical or nontextual server-generated identities."""
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('invalid_scope_uuid')
    return value


def validate_scope(scope):
    """Accept only the immutable server-owned v2 scope, never filesystem authority."""
    wire.fields(scope, {'version', 'principalId', 'workspaceId', 'logicalLaunchId'})
    if type(scope['version']) is not int or scope['version'] != 1:
        raise ValueError('invalid_scope_version')
    for key in ('principalId', 'workspaceId', 'logicalLaunchId'):
        canonical_uuid(scope[key])
    return dict(scope)


def parameters(scope):
    """Return only the two SQL ownership-key parameters."""
    return scope['principalId'], scope['workspaceId']



def bounded_waits(connection):
    """Use existing parser-approved deadlines for lifecycle locks and statements."""
    for statement in PUBLIC_TIMEOUT_SQL:
        connection.execute(statement)


def registry_row(connection, scope):
    """Lock the exact registered scope; admin queries always have explicit WHERE."""
    return connection.execute('SELECT * FROM documents.public_workspace_lifecycle WHERE ' +
                              SCOPE_WHERE + ' FOR UPDATE', parameters(scope)).fetchone()


def same_registration(row, scope, incarnation=None):
    """Never repurpose a private or differently registered launch/incarnation."""
    if row is None or row['launch_id'] != scope['logicalLaunchId']:
        raise ValueError('anonymous_scope_not_registered')
    if incarnation is not None and row['incarnation'] != incarnation:
        raise ValueError('anonymous_incarnation_mismatch')
    return row


def registered(scope):
    """Require a READY persisted public registration before any scoped app operation."""
    validate_scope(scope)
    with connect(admin=True, client='allow-migration', row_factory=dict_row) as connection:
        row = same_registration(registry_row(connection, scope), scope)
        if row['state'] != 'READY':
            raise ValueError('anonymous_scope_not_ready')
        return row


def register(scope, args):
    """Commit provenance before initialization, refusing private collisions atomically."""
    validate_scope(scope)
    canonical_uuid(args['incarnation'])
    expiry = args['expiresAtEpochMillis']
    if type(expiry) is not int or not 0 < expiry <= 9007199254740991:
        raise ValueError('invalid_expiry')
    with connect(admin=True, client='allow-migration', row_factory=dict_row) as connection:
        bounded_waits(connection)
        connection.execute('LOCK TABLE documents.public_workspace_lifecycle IN ACCESS EXCLUSIVE MODE')
        connection.execute('LOCK TABLE documents.workspace IN SHARE ROW EXCLUSIVE MODE')
        row = registry_row(connection, scope)
        existing = connection.execute('SELECT 1 FROM documents.workspace WHERE ' + SCOPE_WHERE,
                                      parameters(scope)).fetchone()
        if row is not None:
            same_registration(row, scope, args['incarnation'])
            if row['expires_at_ms'] != expiry or row['policy_version'] != args['policyVersion'] or row['state'] == 'QUARANTINED':
                raise ValueError('anonymous_registration_conflict')
            return
        if existing is not None:
            raise ValueError('existing_workspace_cannot_become_public')
        count = connection.execute('SELECT count(*) AS occupied FROM documents.public_workspace_lifecycle').fetchone()['occupied']
        if count >= 4:
            raise ValueError('anonymous_capacity')
        values = (*parameters(scope), scope['logicalLaunchId'], args['incarnation'], expiry, args['policyVersion'])
        connection.execute('INSERT INTO documents.public_workspace_lifecycle(principal_id,workspace_id,launch_id,incarnation,expires_at_ms,policy_version,state) VALUES(%s,%s,%s,%s,%s,%s,\'PROVISIONING\')', values)


def initialize(scope, args, store_factory):
    """Keep registration on every failed/uncertain workspace initialization outcome."""
    store_factory.policy_value(args['policyVersion'])
    register(scope, args)
    result = store_factory(scope, public=True).initialize(args['policyVersion'])
    if result.get('status') != 'READY':
        raise ValueError('anonymous_initialization_not_ready')
    with connect(admin=True, client='allow-migration', row_factory=dict_row) as connection:
        row = same_registration(registry_row(connection, scope), scope, args['incarnation'])
        if row['state'] == 'QUARANTINED':
            raise ValueError('anonymous_scope_quarantined')
        connection.execute('UPDATE documents.public_workspace_lifecycle SET state=\'READY\' WHERE ' + SCOPE_WHERE,
                           parameters(scope))
    return result


def listing():
    """Return the complete bounded registry, never truncate uncertain occupied slots."""
    with connect(admin=True, client='allow-migration', row_factory=dict_row) as connection:
        rows = connection.execute('SELECT * FROM documents.public_workspace_lifecycle ORDER BY principal_id,workspace_id LIMIT 5').fetchall()
    if len(rows) > 4:
        raise ValueError('anonymous_registry_over_capacity')
    entries = []
    for row in rows:
        scope = {'version': 1, 'principalId': row['principal_id'], 'workspaceId': row['workspace_id'],
                 'logicalLaunchId': row['launch_id']}
        entries.append({'scope': validate_scope(scope), 'incarnation': canonical_uuid(row['incarnation']),
                        'expiresAtEpochMillis': row['expires_at_ms'], 'state': row['state']})
    return {'status': 'READY', 'workspaces': entries}


def require_clean_context():
    """Use fresh authenticated control status, never a stale status-file snapshot."""
    result = context_lease.exchange({'protocol': 1, 'operation': 'status'})
    wire.fields(result, {'protocol', 'status', 'contextOccupied', 'observerOccupied'})
    if type(result['protocol']) is not int or result['protocol'] != 1 or result['status'] != 'READY':
        raise ValueError('anonymous_cleanup_context_not_ready')
    if type(result['contextOccupied']) is not bool or result['contextOccupied']:
        raise ValueError('anonymous_cleanup_context_occupied')
    if type(result['observerOccupied']) is not bool:
        raise ValueError('anonymous_cleanup_context_unknown')


def quarantine(scope, incarnation):
    """Retain a matching registration and its occupied slot after uncertain cleanup."""
    with connect(admin=True, client='allow-migration', row_factory=dict_row) as connection:
        row = registry_row(connection, scope)
        if row is not None:
            same_registration(row, scope, incarnation)
            connection.execute('UPDATE documents.public_workspace_lifecycle SET state=\'QUARANTINED\' WHERE ' +
                               SCOPE_WHERE, parameters(scope))


def purge(scope, args):
    """Delete only registered drained public data; uncertainty retains quarantine."""
    validate_scope(scope)
    incarnation = canonical_uuid(args['incarnation'])
    try:
        require_clean_context()
        return purge_transaction(scope, incarnation)
    except Exception as original:
        try:
            quarantine(scope, incarnation)
        except Exception as cleanup:
            original.add_note('Quarantine persistence uncertain: ' + type(cleanup).__name__)
        raise


def purge_transaction(scope, incarnation):
    """Remove all exact-scope dependents atomically without app-role DELETE authority."""
    with connect(admin=True, client='allow-migration', row_factory=dict_row) as connection:
        bounded_waits(connection)
        connection.execute('LOCK TABLE documents.public_workspace_lifecycle IN ACCESS EXCLUSIVE MODE')
        connection.execute('LOCK TABLE documents.workspace IN SHARE ROW EXCLUSIVE MODE')
        row = registry_row(connection, scope)
        if row is None:
            existing = connection.execute('SELECT 1 FROM documents.workspace WHERE ' + SCOPE_WHERE,
                                          parameters(scope)).fetchone()
            if existing is not None:
                raise ValueError('unregistered_workspace_cannot_be_purged')
            return {'status': 'ABSENT'}
        same_registration(row, scope, incarnation)
        owners = connection.execute('SELECT owner_pid,owner_start FROM documents.admission WHERE ' +
                                    SCOPE_WHERE + " AND state='VALIDATING'", parameters(scope)).fetchall()
        if any(identity.alive(owner['owner_pid'], owner['owner_start']) for owner in owners):
            raise ValueError('anonymous_request_owner_still_alive')
        require_clean_context()
        for table in ('admission', 'receipt', 'revision', 'artifact', 'document', 'logical_launch', 'workspace'):
            connection.execute('DELETE FROM documents.' + table + ' WHERE ' + SCOPE_WHERE, parameters(scope))
        connection.execute('DELETE FROM documents.public_workspace_lifecycle WHERE ' + SCOPE_WHERE, parameters(scope))
    return {'status': 'PURGED'}
