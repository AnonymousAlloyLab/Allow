-- First-install review catalog. Runtime migration independently admits each statement and checks existing policies/FK.
CREATE SCHEMA IF NOT EXISTS documents AUTHORIZATION allow_owner;
SET ROLE allow_owner;
CREATE TABLE IF NOT EXISTS documents.workspace (principal_id text NOT NULL, workspace_id text NOT NULL,
      policy_version text NOT NULL, document_count bigint NOT NULL DEFAULT 0,
      revision_count bigint NOT NULL DEFAULT 0, receipt_count bigint NOT NULL DEFAULT 0,
      accounted_bytes bigint NOT NULL DEFAULT 0, reserved_bytes bigint NOT NULL DEFAULT 0,
      reserved_receipts bigint NOT NULL DEFAULT 0, reserved_revisions bigint NOT NULL DEFAULT 0,
      reserved_documents bigint NOT NULL DEFAULT 0, PRIMARY KEY(principal_id,workspace_id),
      CHECK(document_count>=0 AND revision_count>=0 AND receipt_count>=0 AND accounted_bytes>=0
      AND reserved_bytes>=0 AND reserved_receipts>=0 AND reserved_revisions>=0 AND reserved_documents>=0));
CREATE TABLE IF NOT EXISTS documents.logical_launch (principal_id text NOT NULL, workspace_id text NOT NULL,
      launch_id text NOT NULL, PRIMARY KEY(principal_id,workspace_id,launch_id),
      FOREIGN KEY(principal_id,workspace_id) REFERENCES documents.workspace(principal_id,workspace_id));
CREATE TABLE IF NOT EXISTS documents.document (principal_id text NOT NULL, workspace_id text NOT NULL,
      document_id text NOT NULL, title text NOT NULL, head_revision bigint NOT NULL CHECK(head_revision>=0),
      PRIMARY KEY(principal_id,workspace_id,document_id), FOREIGN KEY(principal_id,workspace_id) REFERENCES documents.workspace(principal_id,workspace_id));
CREATE TABLE IF NOT EXISTS documents.artifact (principal_id text NOT NULL, workspace_id text NOT NULL,
      document_id text NOT NULL, artifact_id text NOT NULL, content bytea NOT NULL,
      source_hash text NOT NULL, policy_version text NOT NULL,
      PRIMARY KEY(principal_id,workspace_id,document_id,artifact_id),
      FOREIGN KEY(principal_id,workspace_id,document_id) REFERENCES documents.document(principal_id,workspace_id,document_id));
CREATE TABLE IF NOT EXISTS documents.revision (principal_id text NOT NULL, workspace_id text NOT NULL,
      document_id text NOT NULL, revision bigint NOT NULL CHECK(revision>=0), artifact_id text NOT NULL,
      target_revision bigint, direction text CHECK(direction IN ('UNDO','REDO')),
      created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(principal_id,workspace_id,document_id,revision),
      FOREIGN KEY(principal_id,workspace_id,document_id,artifact_id) REFERENCES documents.artifact(principal_id,workspace_id,document_id,artifact_id),
      FOREIGN KEY(principal_id,workspace_id,document_id,target_revision) REFERENCES documents.revision(principal_id,workspace_id,document_id,revision),
      CHECK((target_revision IS NULL)=(direction IS NULL)));
CREATE TABLE IF NOT EXISTS documents.receipt (principal_id text NOT NULL, workspace_id text NOT NULL,
      launch_id text NOT NULL, namespace text NOT NULL, request_key text NOT NULL,
      method text NOT NULL, route text NOT NULL, request_bytes bytea NOT NULL, request_hash text NOT NULL,
      outcome bytea NOT NULL, outcome_code text NOT NULL, result_document_id text, result_revision bigint,
      committed_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(principal_id,workspace_id,launch_id,namespace,request_key),
      FOREIGN KEY(principal_id,workspace_id,launch_id) REFERENCES documents.logical_launch(principal_id,workspace_id,launch_id),
      FOREIGN KEY(principal_id,workspace_id,result_document_id,result_revision) REFERENCES documents.revision(principal_id,workspace_id,document_id,revision));
CREATE TABLE IF NOT EXISTS documents.admission (principal_id text NOT NULL, workspace_id text NOT NULL,
      launch_id text NOT NULL, namespace text NOT NULL, request_key text NOT NULL,
      method text NOT NULL, route text NOT NULL, request_bytes bytea NOT NULL,
      operation text NOT NULL CHECK(operation IN ('CREATE','COMMIT','HISTORY_COPY')),
      document_id text NOT NULL, expected_revision bigint, owner_pid bigint NOT NULL,
      owner_start text NOT NULL, owner_nonce text NOT NULL, state text NOT NULL,
      reservation_bytes bigint NOT NULL, reservation_documents bigint NOT NULL,
      reservation_revisions bigint NOT NULL, PRIMARY KEY(principal_id,workspace_id,launch_id,namespace,request_key),
      FOREIGN KEY(principal_id,workspace_id,launch_id) REFERENCES documents.logical_launch(principal_id,workspace_id,launch_id),
      CHECK(state IN ('VALIDATING','TERMINAL')));
ALTER TABLE documents.document ADD CONSTRAINT document_head_revision_fk FOREIGN KEY(principal_id,workspace_id,document_id,head_revision) REFERENCES documents.revision(principal_id,workspace_id,document_id,revision) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE documents.workspace ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.workspace FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.workspace USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
ALTER TABLE documents.logical_launch ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.logical_launch FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.logical_launch USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
ALTER TABLE documents.document ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.document FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.document USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
ALTER TABLE documents.artifact ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.artifact FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.artifact USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
ALTER TABLE documents.revision ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.revision FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.revision USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
ALTER TABLE documents.receipt ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.receipt FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.receipt USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
ALTER TABLE documents.admission ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.admission FORCE ROW LEVEL SECURITY;
CREATE POLICY document_scope ON documents.admission USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document') WITH CHECK (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
RESET ROLE;
REVOKE ALL ON SCHEMA documents FROM PUBLIC;
GRANT USAGE ON SCHEMA documents TO allow_app;
REVOKE ALL ON documents.workspace FROM PUBLIC;
GRANT SELECT,INSERT ON documents.workspace TO allow_app;
REVOKE ALL ON documents.logical_launch FROM PUBLIC;
GRANT SELECT,INSERT ON documents.logical_launch TO allow_app;
REVOKE ALL ON documents.document FROM PUBLIC;
GRANT SELECT,INSERT ON documents.document TO allow_app;
REVOKE ALL ON documents.artifact FROM PUBLIC;
GRANT SELECT,INSERT ON documents.artifact TO allow_app;
REVOKE ALL ON documents.revision FROM PUBLIC;
GRANT SELECT,INSERT ON documents.revision TO allow_app;
REVOKE ALL ON documents.receipt FROM PUBLIC;
GRANT SELECT,INSERT ON documents.receipt TO allow_app;
REVOKE ALL ON documents.admission FROM PUBLIC;
GRANT SELECT,INSERT ON documents.admission TO allow_app;
GRANT UPDATE ON documents.workspace,documents.admission TO allow_app;
GRANT UPDATE(head_revision,title) ON documents.document TO allow_app;

-- Anonymous lifecycle provenance is admin-only; app-role DELETE remains forbidden.
SET ROLE allow_owner;
CREATE TABLE IF NOT EXISTS documents.public_workspace_lifecycle (
 principal_id text NOT NULL, workspace_id text NOT NULL, launch_id text NOT NULL,
 incarnation text NOT NULL, expires_at_ms bigint NOT NULL CHECK(expires_at_ms>0),
 policy_version text NOT NULL, state text NOT NULL CHECK(state IN ('PROVISIONING','READY','QUARANTINED')),
 PRIMARY KEY(principal_id,workspace_id), UNIQUE(launch_id));
REVOKE ALL ON documents.public_workspace_lifecycle FROM PUBLIC,allow_app;
ALTER TABLE documents.public_workspace_lifecycle ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents.public_workspace_lifecycle FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_registry_scope ON documents.public_workspace_lifecycle;
CREATE POLICY public_registry_scope ON documents.public_workspace_lifecycle FOR SELECT USING (principal_id=current_setting('allow.tenant',true) AND workspace_id=current_setting('allow.project',true) AND current_setting('allow.purpose',true)='document');
GRANT SELECT ON documents.public_workspace_lifecycle TO allow_app;
RESET ROLE;
