"""Static document schema; every DDL statement is independently proxy admitted."""
from allow_retrieval.sql_connections import connect

SCOPE = 'principal_id text NOT NULL, workspace_id text NOT NULL'
KEY = 'principal_id,workspace_id'
TABLES = {
    'workspace': f'''CREATE TABLE IF NOT EXISTS documents.workspace ({SCOPE},
      policy_version text NOT NULL, document_count bigint NOT NULL DEFAULT 0,
      revision_count bigint NOT NULL DEFAULT 0, receipt_count bigint NOT NULL DEFAULT 0,
      accounted_bytes bigint NOT NULL DEFAULT 0, reserved_bytes bigint NOT NULL DEFAULT 0,
      reserved_receipts bigint NOT NULL DEFAULT 0, reserved_revisions bigint NOT NULL DEFAULT 0,
      reserved_documents bigint NOT NULL DEFAULT 0, PRIMARY KEY({KEY}),
      CHECK(document_count>=0 AND revision_count>=0 AND receipt_count>=0 AND accounted_bytes>=0
      AND reserved_bytes>=0 AND reserved_receipts>=0 AND reserved_revisions>=0 AND reserved_documents>=0))''',
    'logical_launch': f'''CREATE TABLE IF NOT EXISTS documents.logical_launch ({SCOPE},
      launch_id text NOT NULL, PRIMARY KEY({KEY},launch_id),
      FOREIGN KEY({KEY}) REFERENCES documents.workspace({KEY}))''',
    'document': f'''CREATE TABLE IF NOT EXISTS documents.document ({SCOPE},
      document_id text NOT NULL, title text NOT NULL, head_revision bigint NOT NULL CHECK(head_revision>=0),
      PRIMARY KEY({KEY},document_id), FOREIGN KEY({KEY}) REFERENCES documents.workspace({KEY}))''',
    'artifact': f'''CREATE TABLE IF NOT EXISTS documents.artifact ({SCOPE},
      document_id text NOT NULL, artifact_id text NOT NULL, content bytea NOT NULL,
      source_hash text NOT NULL, policy_version text NOT NULL,
      PRIMARY KEY({KEY},document_id,artifact_id),
      FOREIGN KEY({KEY},document_id) REFERENCES documents.document({KEY},document_id))''',
    'revision': f'''CREATE TABLE IF NOT EXISTS documents.revision ({SCOPE},
      document_id text NOT NULL, revision bigint NOT NULL CHECK(revision>=0), artifact_id text NOT NULL,
      target_revision bigint, direction text CHECK(direction IN ('UNDO','REDO')),
      created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY({KEY},document_id,revision),
      FOREIGN KEY({KEY},document_id,artifact_id) REFERENCES documents.artifact({KEY},document_id,artifact_id),
      FOREIGN KEY({KEY},document_id,target_revision) REFERENCES documents.revision({KEY},document_id,revision),
      CHECK((target_revision IS NULL)=(direction IS NULL)))''',
    'receipt': f'''CREATE TABLE IF NOT EXISTS documents.receipt ({SCOPE},
      launch_id text NOT NULL, namespace text NOT NULL, request_key text NOT NULL,
      method text NOT NULL, route text NOT NULL, request_bytes bytea NOT NULL, request_hash text NOT NULL,
      outcome bytea NOT NULL, outcome_code text NOT NULL, result_document_id text, result_revision bigint,
      committed_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY({KEY},launch_id,namespace,request_key),
      FOREIGN KEY({KEY},launch_id) REFERENCES documents.logical_launch({KEY},launch_id),
      FOREIGN KEY({KEY},result_document_id,result_revision) REFERENCES documents.revision({KEY},document_id,revision))''',
    'admission': f'''CREATE TABLE IF NOT EXISTS documents.admission ({SCOPE},
      launch_id text NOT NULL, namespace text NOT NULL, request_key text NOT NULL,
      method text NOT NULL, route text NOT NULL, request_bytes bytea NOT NULL,
      operation text NOT NULL CHECK(operation IN ('CREATE','COMMIT','HISTORY_COPY')),
      document_id text NOT NULL, expected_revision bigint, owner_pid bigint NOT NULL,
      owner_start text NOT NULL, owner_nonce text NOT NULL, state text NOT NULL,
      reservation_bytes bigint NOT NULL, reservation_documents bigint NOT NULL,
      reservation_revisions bigint NOT NULL, PRIMARY KEY({KEY},launch_id,namespace,request_key),
      FOREIGN KEY({KEY},launch_id) REFERENCES documents.logical_launch({KEY},launch_id),
      CHECK(state IN ('VALIDATING','TERMINAL')))'''
}
POLICY = "principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document'"


def migrate():
    """Install owned schema through admin proxy with no dynamic SQL bodies."""
    with connect(admin=True, client='allow-migration') as connection:
        connection.execute('CREATE SCHEMA IF NOT EXISTS documents AUTHORIZATION allow_owner')
        connection.execute('SET ROLE allow_owner')
        for statement in TABLES.values():
            connection.execute(statement)
        head_fk = connection.execute("SELECT 1 FROM pg_constraint WHERE conname='document_head_revision_fk' AND connamespace='documents'::regnamespace").fetchone()
        if head_fk is None:
            connection.execute('ALTER TABLE documents.document ADD CONSTRAINT document_head_revision_fk FOREIGN KEY(principal_id,workspace_id,document_id,head_revision) REFERENCES documents.revision(principal_id,workspace_id,document_id,revision) DEFERRABLE INITIALLY DEFERRED')
        for table in TABLES:
            connection.execute('ALTER TABLE documents.' + table + ' ENABLE ROW LEVEL SECURITY')
            connection.execute('ALTER TABLE documents.' + table + ' FORCE ROW LEVEL SECURITY')
            found = connection.execute("SELECT 1 FROM pg_policies WHERE schemaname='documents' AND tablename=%s AND policyname='document_scope'", (table,)).fetchone()
            if found is None:
                connection.execute('CREATE POLICY document_scope ON documents.' + table + ' USING (' + POLICY + ') WITH CHECK (' + POLICY + ')')
        from .lifecycle import REGISTRY_DDL
        connection.execute(REGISTRY_DDL)
        connection.execute('REVOKE ALL ON documents.public_workspace_lifecycle FROM PUBLIC,allow_app')
        connection.execute('ALTER TABLE documents.public_workspace_lifecycle ENABLE ROW LEVEL SECURITY')
        connection.execute('ALTER TABLE documents.public_workspace_lifecycle FORCE ROW LEVEL SECURITY')
        connection.execute('DROP POLICY IF EXISTS public_registry_scope ON documents.public_workspace_lifecycle')
        connection.execute('CREATE POLICY public_registry_scope ON documents.public_workspace_lifecycle FOR SELECT USING (' + POLICY + ')')
        connection.execute('GRANT SELECT ON documents.public_workspace_lifecycle TO allow_app')
        connection.execute('RESET ROLE')
        connection.execute('REVOKE ALL ON SCHEMA documents FROM PUBLIC')
        connection.execute('GRANT USAGE ON SCHEMA documents TO allow_app')
        for table in TABLES:
            connection.execute('REVOKE ALL ON documents.' + table + ' FROM PUBLIC')
            connection.execute('GRANT SELECT,INSERT ON documents.' + table + ' TO allow_app')
        connection.execute('GRANT UPDATE ON documents.workspace,documents.admission TO allow_app')
        connection.execute('GRANT UPDATE(head_revision,title) ON documents.document TO allow_app')


def has_existing_store():
    """Fail closed before identity provisioning if any durable workspace exists."""
    with connect(admin=True, client='allow-migration') as connection:
        return connection.execute('SELECT EXISTS(SELECT 1 FROM documents.workspace)').fetchone()[0]
