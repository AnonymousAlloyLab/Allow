"""Explicit idempotent schema migration: every actual statement crosses the proxy.

The original 004 SQL remains historical evidence and is never executed here.
No anonymous procedural bodies or dynamically executed SQL are used.
"""
import re

EXPECTED_CATALOG_SHA256 = '186e6838be0f8b2eb7f6caccd105eb5e6831ba5d792174deb8d96fd778e8ae36'

BASE_TABLES = (
    """CREATE TABLE IF NOT EXISTS retrieval.runtime_state (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), journal_id text, journal_seq bigint NOT NULL DEFAULT 0,
 journal_head text NOT NULL DEFAULT 'GENESIS', quarantined boolean NOT NULL DEFAULT true);""",
    """CREATE TABLE IF NOT EXISTS retrieval.artifact (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, source_hash text NOT NULL,
 source_root text NOT NULL, locator text NOT NULL, family text NOT NULL, snapshot text NOT NULL,
 provenance jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());""",
    """CREATE TABLE IF NOT EXISTS retrieval.record (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, artifact_id text NOT NULL REFERENCES retrieval.artifact,
 content jsonb NOT NULL, context_key text NOT NULL, context_bytes text NOT NULL, n integer NOT NULL CHECK(n BETWEEN 3 AND 5),
 status text NOT NULL CHECK(status IN ('FULL','PARTIAL','REJECTED')), target_slot integer NOT NULL,
 family text NOT NULL, split text NOT NULL CHECK(split IN ('unassigned','train','validation','test')) DEFAULT 'unassigned',
 allowed_purposes text[] NOT NULL, rights_version text NOT NULL, revoked boolean NOT NULL DEFAULT false,
 content_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());""",
    """CREATE TABLE IF NOT EXISTS retrieval.run (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 polarity text NOT NULL CHECK(polarity IN ('positive','negative')), existence text NOT NULL,
 termination text NOT NULL, query_identity text NOT NULL, details jsonb NOT NULL,
 UNIQUE(record_id,polarity));""",
    """CREATE TABLE IF NOT EXISTS retrieval.witness (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, context_key text NOT NULL,
 canonical_bytes text NOT NULL, content jsonb NOT NULL);""",
    """CREATE TABLE IF NOT EXISTS retrieval.membership (
 tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 run_id text NOT NULL REFERENCES retrieval.run, witness_id text NOT NULL REFERENCES retrieval.witness,
 polarity text NOT NULL CHECK(polarity IN ('positive','negative')), validated boolean NOT NULL CHECK(validated),
 PRIMARY KEY(record_id,polarity,witness_id));""",
    """CREATE TABLE IF NOT EXISTS retrieval.model (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, manifest jsonb NOT NULL,
 active boolean NOT NULL DEFAULT true, trained boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now());""",
    """CREATE TABLE IF NOT EXISTS retrieval.training_lineage (
 tenant text NOT NULL, project text NOT NULL, model_id text NOT NULL REFERENCES retrieval.model,
 record_id text NOT NULL REFERENCES retrieval.record, rights_version text NOT NULL,
 PRIMARY KEY(model_id,record_id));""",
    """CREATE TABLE IF NOT EXISTS retrieval.outbox (
 id bigserial PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 model_id text NOT NULL REFERENCES retrieval.model, content_version text NOT NULL,
 status text NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','RUNNING','DONE','CANCELLED','ERROR')),
 attempts integer NOT NULL DEFAULT 0, error text, UNIQUE(record_id,model_id,content_version));""",
    """CREATE TABLE IF NOT EXISTS retrieval.embedding (
 tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 model_id text NOT NULL REFERENCES retrieval.model, content_version text NOT NULL, vector vector(3072) NOT NULL,
 PRIMARY KEY(record_id,model_id));""",
    """CREATE TABLE IF NOT EXISTS retrieval.diagnostic (
 id bigserial PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, dataset text NOT NULL,
 source_hash text, reason text NOT NULL, details jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());""",
    """CREATE TABLE IF NOT EXISTS retrieval.record_origin (
 tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 artifact_id text NOT NULL REFERENCES retrieval.artifact, target_slot integer NOT NULL, evidence jsonb NOT NULL,
 PRIMARY KEY(record_id,artifact_id,target_slot));""",
    """CREATE TABLE IF NOT EXISTS retrieval.embedding_intent (
 tenant text NOT NULL, project text NOT NULL, record_id text PRIMARY KEY REFERENCES retrieval.record,
 content_version text NOT NULL, status text NOT NULL DEFAULT 'PENDING' CHECK(status IN('PENDING','QUEUED','CANCELLED')));""",
)
VARIANT_TABLE = """CREATE TABLE IF NOT EXISTS retrieval.training_variant (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL,
 record_id text NOT NULL, original_certificate_id text NOT NULL, worker_identity text NOT NULL,
 evidence jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(record_id,tenant,project) REFERENCES retrieval.record(id,tenant,project));"""
SCOPED_TABLES = ('artifact','record','run','witness','membership','model','training_lineage','outbox','embedding','diagnostic','record_origin','embedding_intent','training_variant')
UNIQUE_TABLES = ('artifact','record','run','witness','model')
LINKS = (('record','artifact_id','artifact'),('run','record_id','record'),
 ('membership','record_id','record'),('membership','run_id','run'),('membership','witness_id','witness'),
 ('record_origin','record_id','record'),('record_origin','artifact_id','artifact'),
 ('training_lineage','record_id','record'),('training_lineage','model_id','model'),
 ('outbox','record_id','record'),('outbox','model_id','model'),
 ('embedding','record_id','record'),('embedding','model_id','model'),('embedding_intent','record_id','record'))


def _identifier(name):
    if not re.fullmatch('[a-z_][a-z0-9_]*',name):raise ValueError('unregistered_migration_identifier')
    return name


def _constraint(conn,table,name,definition,counts):
    """Check each constraint independently, including a partially installed pair."""
    table,name=_identifier(table),_identifier(name)
    row=conn.execute("SELECT pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace='retrieval'::regnamespace AND conrelid=%s::regclass AND conname=%s",('retrieval.'+table,name)).fetchone()
    if row:
        observed=row['definition'] if isinstance(row,dict) else row[0]
        normal=lambda value:re.sub(r'\s+','',value).replace('"','').upper()
        if normal(observed)!=normal(definition):raise ValueError('existing_constraint_definition_mismatch')
        return
    conn.execute(f'ALTER TABLE retrieval.{table} ADD CONSTRAINT {name} {definition}')
    counts['constraints_added']+=1


def apply_migrations(conn):
    """Apply all schema changes atomically without replaying the opaque baseline."""
    counts={'constraints_added':0,'policies_verified':0,'tables':len(BASE_TABLES)+1}
    with conn.transaction():
        row=conn.execute('SELECT current_user AS name').fetchone()
        if (row['name'] if isinstance(row,dict) else row[0])!='allow_admin':
            raise ValueError('migration_admin_required')
        conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
        conn.execute('CREATE SCHEMA IF NOT EXISTS retrieval AUTHORIZATION allow_owner')
        conn.execute('SET LOCAL ROLE allow_owner')
        for statement in BASE_TABLES:conn.execute(statement)
        conn.execute('RESET ROLE')
        conn.execute("INSERT INTO retrieval.runtime_state(singleton) VALUES(true) ON CONFLICT DO NOTHING")
        for statement in (
            "ALTER TABLE retrieval.record ADD COLUMN IF NOT EXISTS evidence jsonb NOT NULL DEFAULT '{}'::jsonb",
            'ALTER TABLE retrieval.model ADD COLUMN IF NOT EXISTS servable boolean NOT NULL DEFAULT false',
            'ALTER TABLE retrieval.model ADD COLUMN IF NOT EXISTS promotion jsonb',
            'ALTER TABLE retrieval.outbox ADD COLUMN IF NOT EXISTS claim_token text',
            'ALTER TABLE retrieval.outbox ADD COLUMN IF NOT EXISTS lease_until timestamptz',
            'CREATE INDEX IF NOT EXISTS retrieval_record_scope ON retrieval.record(tenant,project,status,revoked)',
            'CREATE INDEX IF NOT EXISTS retrieval_lineage_record ON retrieval.training_lineage(record_id)'):
            conn.execute(statement)
        for table in UNIQUE_TABLES:
            _constraint(conn,table,table+'_scope_identity','UNIQUE(id,tenant,project)',counts)
        for table,column,parent in LINKS:
            _constraint(conn,table,table+'_'+column+'_scope_fk',f'FOREIGN KEY({column},tenant,project) REFERENCES retrieval.{parent}(id,tenant,project)',counts)
        _constraint(conn,'run','run_query_member_identity','UNIQUE(id,record_id,polarity)',counts)
        _constraint(conn,'membership','membership_own_query','FOREIGN KEY(run_id,record_id,polarity) REFERENCES retrieval.run(id,record_id,polarity)',counts)
        conn.execute('SET LOCAL ROLE allow_owner')
        conn.execute(VARIANT_TABLE)
        conn.execute('RESET ROLE')
        for table in SCOPED_TABLES:
            conn.execute(f'ALTER TABLE retrieval.{table} ENABLE ROW LEVEL SECURITY')
            conn.execute(f'ALTER TABLE retrieval.{table} FORCE ROW LEVEL SECURITY')
            # Reinstall each known policy transactionally, repairing its roles,
            # command and predicates even if an old schema was partially applied.
            conn.execute('SELECT policyname FROM pg_policies WHERE schemaname=%s AND tablename=%s AND policyname=%s',('retrieval',table,'scope')).fetchall()
            conn.execute(f'DROP POLICY IF EXISTS scope ON retrieval.{table}')
            conn.execute(f"CREATE POLICY scope ON retrieval.{table} USING(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true)) WITH CHECK(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true))")
            counts['policies_verified']+=1
        conn.execute('GRANT USAGE ON SCHEMA retrieval TO allow_app')
        for table in ('runtime_state',)+SCOPED_TABLES:
            if table=='training_variant':continue
            conn.execute(f'GRANT SELECT,INSERT,UPDATE,DELETE ON retrieval.{table} TO allow_app')
        conn.execute('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA retrieval TO allow_app')
        conn.execute('REVOKE UPDATE,DELETE ON retrieval.training_variant FROM allow_app')
        conn.execute('GRANT SELECT,INSERT ON retrieval.training_variant TO allow_app')
        conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        validate_catalog(conn)
    return counts



def capture_catalog(conn):
    """Capture every owned table column, constraint and index without reading data."""
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cursor:
        tables=cursor.execute("SELECT c.relname AS table_name FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='retrieval' AND c.relkind IN ('r','p') ORDER BY c.relname").fetchall()
        columns=cursor.execute("SELECT c.relname AS table_name,a.attname AS name,a.attnum AS position,format_type(a.atttypid,a.atttypmod) AS type,a.attnotnull AS not_null,a.attidentity AS identity_kind,a.attgenerated AS generated_kind,pg_get_expr(d.adbin,d.adrelid) AS default_expression FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE n.nspname='retrieval' AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum").fetchall()
        constraints=cursor.execute("SELECT c.relname AS table_name,k.conname AS name,k.contype AS type,k.convalidated AS validated,k.condeferrable AS deferrable,k.condeferred AS initially_deferred,pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='retrieval' ORDER BY c.relname,k.conname").fetchall()
        indexes=cursor.execute("SELECT c.relname AS table_name,ic.relname AS name,i.indisvalid AS valid,i.indisready AS ready,pg_get_indexdef(i.indexrelid) AS definition FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid JOIN pg_class ic ON ic.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='retrieval' ORDER BY c.relname,ic.relname").fetchall()
    return {'tables':tables,'columns':columns,'constraints':constraints,'indexes':indexes}


def validate_catalog(conn):
    """Deny schema drift, including missing inline checks/FKs and altered columns."""
    import json
    from pathlib import Path
    import hashlib
    raw=(Path(__file__).resolve().parents[2]/'db/migrations/005_expected_catalog.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_CATALOG_SHA256:raise ValueError('catalog_manifest_identity_mismatch')
    expected=json.loads(raw)
    if capture_catalog(conn)!=expected['catalog']:
        raise ValueError('existing_schema_catalog_mismatch')

def main():
    """Migrate only the canonical proxied local database and report aggregate counts."""
    import json
    from .sql_connections import connect
    from psycopg.rows import dict_row
    try:
        with connect(admin=True,client='allow-migration',row_factory=dict_row) as connection:
            counts=apply_migrations(connection)
        print(json.dumps({'status':'PASS',**counts},separators=(',',':')))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','reason':type(exc).__name__},separators=(',',':')))
        return 1

if __name__=='__main__':raise SystemExit(main())
