"""Canonical proxy-only PostgreSQL connections and clean libpq tool environments."""
import json
import os
from pathlib import Path
import re
from uuid import UUID
from .common import ROOT

RUNTIME_DIRECTORY = ROOT / '.runtime/corpus'
PROXY_DIRECTORY = RUNTIME_DIRECTORY / 'sql-proxy/socket'
PROXY_SOCKET = PROXY_DIRECTORY / '.s.PGSQL.54329'
BACKEND_SOCKET = RUNTIME_DIRECTORY / 'postgres/socket/.s.PGSQL.54329'
PORT = '54329'
ENVIRONMENT_ROUTES = ('ALLOW_RETRIEVAL_DSN','ALLOW_RETRIEVAL_ADMIN_DSN','PGHOST','PGHOSTADDR',
                      'PGPORT','PGSERVICE','PGSERVICEFILE','PGSYSCONFDIR','PGOPTIONS','PGCLIENTENCODING')
CLIENT_TAGS = {'allow-app','allow-bootstrap','allow-proxy-readiness','allow-migration','allow-tests',
               'allow-recovery','allow-recovery-control','allow-recovery-dump','allow-recovery-restore',
               'allow-pg-dump','allow-pg-restore'}
ALLOWED_KEYS = {'host','port','dbname','user','password','client_encoding','application_name',
                'connect_timeout','sslmode','gssencmode','options'}

class ConnectionPolicyError(ValueError):
    """A connection would escape the owned parser proxy or its safe startup mode."""


def private_client_role(client):
    """Recognize only canonical private UUID tags; no tag grants role authority."""
    if not isinstance(client, str):
        return None
    for prefix, role in (('allow-document-context:', 'context'),
                         ('allow-context-observer:', 'observer')):
        if client.startswith(prefix):
            suffix = client[len(prefix):]
            try:
                return role if str(UUID(suffix)) == suffix else None
            except (ValueError, AttributeError):
                return None
    return None


def validate_client_tag(client, *, admin=False, database='allow_retrieval'):
    """Restrict dynamic context/observer tags to the canonical application database."""
    if not isinstance(client, str):
        raise ConnectionPolicyError('invalid_client_tag')
    role = private_client_role(client)
    if role is not None:
        if admin or database != 'allow_retrieval':
            raise ConnectionPolicyError('private_client_role_forbidden')
        return role
    if client not in CLIENT_TAGS:
        raise ConnectionPolicyError('invalid_client_tag')
    return None


def reject_environment_routes():
    """Reject ambient route/options overrides instead of silently inheriting them."""
    if any(os.environ.get(key) for key in ENVIRONMENT_ROUTES):
        raise ConnectionPolicyError('ambient_database_route_forbidden')
    alternate = os.environ.get('ALLOW_CORPUS_RUNTIME')
    if alternate and Path(alternate) != RUNTIME_DIRECTORY:
        raise ConnectionPolicyError('alternate_database_runtime_forbidden')


def configuration():
    """Read only the canonical private credential file, without emitting its contents."""
    reject_environment_routes()
    path = RUNTIME_DIRECTORY / 'database.json'
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ConnectionPolicyError('database_configuration_not_private')
    return json.loads(path.read_text())


def validate_dsn(dsn, admin=False, allow_temporary=False, client='allow-app'):
    """Validate every explicit endpoint and force the parser's UTF-8 startup mode."""
    reject_environment_routes()
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    if not isinstance(dsn,str):
        raise ConnectionPolicyError('database_dsn_required')
    try:
        fields = conninfo_to_dict(dsn)
    except Exception as exc:
        raise ConnectionPolicyError('invalid_database_dsn') from exc
    if set(fields)-ALLOWED_KEYS or fields.get('host') != str(PROXY_DIRECTORY) or fields.get('port') != PORT:
        raise ConnectionPolicyError('owned_proxy_endpoint_required')
    if fields.get('user') != ('allow_admin' if admin else 'allow_app'):
        raise ConnectionPolicyError('unexpected_database_role')
    database = fields.get('dbname')
    temporary = isinstance(database,str) and re.fullmatch(r'allow_(?:recovery|sql_test)_[0-9a-f]{32}',database)
    if database not in ('allow_retrieval','postgres') and not (allow_temporary and temporary):
        raise ConnectionPolicyError('database_not_registered')
    if not admin and database == 'postgres':
        raise ConnectionPolicyError('application_database_required')
    if fields.get('sslmode','disable')!='disable' or fields.get('gssencmode','disable')!='disable':
        raise ConnectionPolicyError('alternate_database_transport_forbidden')
    if fields.get('client_encoding','UTF8').upper().replace('-','') != 'UTF8' or fields.get('options',''):
        raise ConnectionPolicyError('unsafe_database_startup_mode')
    validate_client_tag(client, admin=admin, database=database)
    fields.update(client_encoding='UTF8',options='',sslmode='disable',gssencmode='disable',
                  application_name=client,connect_timeout='5')
    return make_conninfo(**fields)


def configured_dsn(admin=False, client='allow-app'):
    """Return the canonical authenticated proxy DSN; no environment fallback exists."""
    value = configuration()['admin_dsn' if admin else 'app_dsn']
    return validate_dsn(value,admin=admin,client=client)


def database_dsn(dsn, database, admin=False, client='allow-recovery'):
    """Change only an explicitly registered recovery/test database, retaining the proxy."""
    from psycopg.conninfo import make_conninfo
    base = validate_dsn(dsn,admin=admin,client=client)
    return validate_dsn(make_conninfo(base,dbname=database),admin=admin,allow_temporary=True,client=client)


def connect(dsn=None, admin=False, allow_temporary=False, client='allow-app', **kwargs):
    """Open a connection only after endpoint validation and safe startup normalization."""
    import psycopg
    allowed = {'autocommit','row_factory'}
    if set(kwargs)-allowed:
        raise ConnectionPolicyError('connection_override_forbidden')
    normalized = validate_dsn(dsn or configured_dsn(admin,client),admin,allow_temporary,client)
    # Psycopg's automatic cache emits SQL DEALLOCATE after DDL/rollback.
    # Keep normal parameter Bind frames, but never create that opaque SQL path.
    return psycopg.connect(normalized,prepare_threshold=None,**kwargs)


def tool_environment(dsn, admin=False, client='allow-recovery-dump', allow_temporary=True):
    """Build a libpq environment with no inherited PostgreSQL route/service settings."""
    from psycopg.conninfo import conninfo_to_dict
    fields = conninfo_to_dict(validate_dsn(dsn,admin,allow_temporary,client))
    env = {key:value for key,value in os.environ.items() if not key.startswith('PG')}
    mapping = {'host':'PGHOST','port':'PGPORT','dbname':'PGDATABASE','user':'PGUSER','password':'PGPASSWORD',
               'client_encoding':'PGCLIENTENCODING','application_name':'PGAPPNAME','sslmode':'PGSSLMODE',
               'gssencmode':'PGGSSENCMODE','connect_timeout':'PGCONNECT_TIMEOUT'}
    env.update({mapping[key]:value for key,value in fields.items() if key in mapping})
    env['PGOPTIONS'] = ''
    return env
