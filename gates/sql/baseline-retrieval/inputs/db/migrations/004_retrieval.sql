CREATE EXTENSION IF NOT EXISTS vector;
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='allow_owner') THEN CREATE ROLE allow_owner NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='allow_app') THEN CREATE ROLE allow_app LOGIN NOSUPERUSER NOBYPASSRLS; END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS retrieval AUTHORIZATION allow_owner;
SET ROLE allow_owner;
CREATE TABLE IF NOT EXISTS retrieval.runtime_state (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), journal_id text, journal_seq bigint NOT NULL DEFAULT 0,
 journal_head text NOT NULL DEFAULT 'GENESIS', quarantined boolean NOT NULL DEFAULT true);
INSERT INTO retrieval.runtime_state(singleton) VALUES(true) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS retrieval.artifact (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, source_hash text NOT NULL,
 source_root text NOT NULL, locator text NOT NULL, family text NOT NULL, snapshot text NOT NULL,
 provenance jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS retrieval.record (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, artifact_id text NOT NULL REFERENCES retrieval.artifact,
 content jsonb NOT NULL, context_key text NOT NULL, context_bytes text NOT NULL, n integer NOT NULL CHECK(n BETWEEN 3 AND 5),
 status text NOT NULL CHECK(status IN ('FULL','PARTIAL','REJECTED')), target_slot integer NOT NULL,
 family text NOT NULL, split text NOT NULL CHECK(split IN ('unassigned','train','validation','test')) DEFAULT 'unassigned',
 allowed_purposes text[] NOT NULL, rights_version text NOT NULL, revoked boolean NOT NULL DEFAULT false,
 content_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS retrieval.run (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 polarity text NOT NULL CHECK(polarity IN ('positive','negative')), existence text NOT NULL,
 termination text NOT NULL, query_identity text NOT NULL, details jsonb NOT NULL,
 UNIQUE(record_id,polarity));
CREATE TABLE IF NOT EXISTS retrieval.witness (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, context_key text NOT NULL,
 canonical_bytes text NOT NULL, content jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS retrieval.membership (
 tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 run_id text NOT NULL REFERENCES retrieval.run, witness_id text NOT NULL REFERENCES retrieval.witness,
 polarity text NOT NULL CHECK(polarity IN ('positive','negative')), validated boolean NOT NULL CHECK(validated),
 PRIMARY KEY(record_id,polarity,witness_id));
CREATE TABLE IF NOT EXISTS retrieval.model (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, manifest jsonb NOT NULL,
 active boolean NOT NULL DEFAULT true, trained boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS retrieval.training_lineage (
 tenant text NOT NULL, project text NOT NULL, model_id text NOT NULL REFERENCES retrieval.model,
 record_id text NOT NULL REFERENCES retrieval.record, rights_version text NOT NULL,
 PRIMARY KEY(model_id,record_id));
CREATE TABLE IF NOT EXISTS retrieval.outbox (
 id bigserial PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 model_id text NOT NULL REFERENCES retrieval.model, content_version text NOT NULL,
 status text NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','RUNNING','DONE','CANCELLED','ERROR')),
 attempts integer NOT NULL DEFAULT 0, error text, UNIQUE(record_id,model_id,content_version));
CREATE TABLE IF NOT EXISTS retrieval.embedding (
 tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 model_id text NOT NULL REFERENCES retrieval.model, content_version text NOT NULL, vector vector(3072) NOT NULL,
 PRIMARY KEY(record_id,model_id));
CREATE TABLE IF NOT EXISTS retrieval.diagnostic (
 id bigserial PRIMARY KEY, tenant text NOT NULL, project text NOT NULL, dataset text NOT NULL,
 source_hash text, reason text NOT NULL, details jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS retrieval_record_scope ON retrieval.record(tenant,project,status,revoked);
CREATE INDEX IF NOT EXISTS retrieval_lineage_record ON retrieval.training_lineage(record_id);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['artifact','record','run','witness','membership','model','training_lineage','outbox','embedding','diagnostic'] LOOP
 EXECUTE format('ALTER TABLE retrieval.%I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE retrieval.%I FORCE ROW LEVEL SECURITY',t);
 IF NOT EXISTS(SELECT FROM pg_policies WHERE schemaname='retrieval' AND tablename=t AND policyname='scope') THEN
 EXECUTE format('CREATE POLICY scope ON retrieval.%I USING (tenant=current_setting(''allow.tenant'',true) AND project=current_setting(''allow.project'',true)) WITH CHECK (tenant=current_setting(''allow.tenant'',true) AND project=current_setting(''allow.project'',true))',t);
 END IF;
 END LOOP;
END $$;
RESET ROLE;
GRANT USAGE ON SCHEMA retrieval TO allow_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA retrieval TO allow_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA retrieval TO allow_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SET ROLE allow_owner;
ALTER TABLE retrieval.record ADD COLUMN IF NOT EXISTS evidence jsonb NOT NULL DEFAULT '{}'::jsonb;
CREATE TABLE IF NOT EXISTS retrieval.record_origin (
 tenant text NOT NULL, project text NOT NULL, record_id text NOT NULL REFERENCES retrieval.record,
 artifact_id text NOT NULL REFERENCES retrieval.artifact, target_slot integer NOT NULL, evidence jsonb NOT NULL,
 PRIMARY KEY(record_id,artifact_id,target_slot));
ALTER TABLE retrieval.record_origin ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval.record_origin FORCE ROW LEVEL SECURITY;
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_policies WHERE schemaname='retrieval' AND tablename='record_origin' AND policyname='scope') THEN
CREATE POLICY scope ON retrieval.record_origin USING(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true)) WITH CHECK(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true));
END IF; END $$;
RESET ROLE;
GRANT SELECT,INSERT,UPDATE,DELETE ON retrieval.record_origin TO allow_app;
SET ROLE allow_owner;
ALTER TABLE retrieval.model ADD COLUMN IF NOT EXISTS servable boolean NOT NULL DEFAULT false;
ALTER TABLE retrieval.model ADD COLUMN IF NOT EXISTS promotion jsonb;
CREATE TABLE IF NOT EXISTS retrieval.embedding_intent (
 tenant text NOT NULL, project text NOT NULL, record_id text PRIMARY KEY REFERENCES retrieval.record,
 content_version text NOT NULL, status text NOT NULL DEFAULT 'PENDING' CHECK(status IN('PENDING','QUEUED','CANCELLED')));
ALTER TABLE retrieval.embedding_intent ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval.embedding_intent FORCE ROW LEVEL SECURITY;
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_policies WHERE schemaname='retrieval' AND tablename='embedding_intent' AND policyname='scope') THEN
CREATE POLICY scope ON retrieval.embedding_intent USING(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true)) WITH CHECK(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true));
END IF; END $$;
RESET ROLE;
GRANT SELECT,INSERT,UPDATE,DELETE ON retrieval.embedding_intent TO allow_app;
SET ROLE allow_owner;
ALTER TABLE retrieval.outbox ADD COLUMN IF NOT EXISTS claim_token text;
ALTER TABLE retrieval.outbox ADD COLUMN IF NOT EXISTS lease_until timestamptz;
RESET ROLE;
-- Scope columns participate in referential integrity as well as RLS. A row in one
-- tenant/project cannot bind another scope's immutable evidence or model.
SET ROLE allow_owner;
DO $$ DECLARE t text; rel text; parent text; col text; cname text; BEGIN
 FOREACH t IN ARRAY ARRAY['artifact','record','run','witness','model'] LOOP
  cname=t||'_scope_identity';
  IF NOT EXISTS(SELECT FROM pg_constraint WHERE conname=cname AND connamespace='retrieval'::regnamespace) THEN
   EXECUTE format('ALTER TABLE retrieval.%I ADD CONSTRAINT %I UNIQUE(id,tenant,project)',t,cname);
  END IF;
 END LOOP;
 FOR rel,col,parent IN SELECT * FROM (VALUES
 ('record','artifact_id','artifact'),('run','record_id','record'),('membership','record_id','record'),
 ('membership','run_id','run'),('membership','witness_id','witness'),('record_origin','record_id','record'),
 ('record_origin','artifact_id','artifact'),('training_lineage','record_id','record'),
 ('training_lineage','model_id','model'),('outbox','record_id','record'),('outbox','model_id','model'),
 ('embedding','record_id','record'),('embedding','model_id','model'),('embedding_intent','record_id','record')) AS links(rel,col,parent)
 LOOP
  cname=rel||'_'||col||'_scope_fk';
  IF NOT EXISTS(SELECT FROM pg_constraint WHERE conname=cname AND connamespace='retrieval'::regnamespace) THEN
   EXECUTE format('ALTER TABLE retrieval.%I ADD CONSTRAINT %I FOREIGN KEY(%I,tenant,project) REFERENCES retrieval.%I(id,tenant,project)',rel,cname,col,parent);
  END IF;
 END LOOP;
 IF NOT EXISTS(SELECT FROM pg_constraint WHERE conname='run_query_member_identity' AND connamespace='retrieval'::regnamespace) THEN
  ALTER TABLE retrieval.run ADD CONSTRAINT run_query_member_identity UNIQUE(id,record_id,polarity);
  ALTER TABLE retrieval.membership ADD CONSTRAINT membership_own_query FOREIGN KEY(run_id,record_id,polarity) REFERENCES retrieval.run(id,record_id,polarity);
 END IF;
END $$;
RESET ROLE;
SET ROLE allow_owner;
CREATE TABLE IF NOT EXISTS retrieval.training_variant (
 id text PRIMARY KEY, tenant text NOT NULL, project text NOT NULL,
 record_id text NOT NULL, original_certificate_id text NOT NULL, worker_identity text NOT NULL,
 evidence jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(record_id,tenant,project) REFERENCES retrieval.record(id,tenant,project));
ALTER TABLE retrieval.training_variant ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval.training_variant FORCE ROW LEVEL SECURITY;
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_policies WHERE schemaname='retrieval' AND tablename='training_variant' AND policyname='scope') THEN
CREATE POLICY scope ON retrieval.training_variant USING(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true)) WITH CHECK(tenant=current_setting('allow.tenant',true) AND project=current_setting('allow.project',true));
END IF; END $$;
RESET ROLE;
GRANT SELECT,INSERT ON retrieval.training_variant TO allow_app;
