"""Transactional local repository. Only FULL, authorized, current vectors are visible."""
import contextlib
import json
import math
import os
import uuid
import struct
from pathlib import Path
from .common import RUNTIME, SCHEMA, canonical, digest
from .journal import Journal, Quarantined

PURPOSES = ('analyze','store','embed','train','retrieve')

class Forbidden(RuntimeError):
    pass

class NotFound(RuntimeError):
    pass

def connection_dsn(admin=False):
    from .sql_connections import configured_dsn
    return configured_dsn(admin)

class Repository:
    def __init__(self, dsn=None, tenant='local', project='allow', purpose='retrieve', journal=None, allow_temporary=False, client='allow-app'):
        if not all(isinstance(x,str) and x and len(x) <= 128 for x in (tenant,project,purpose)):
            raise ValueError('invalid_scope')
        if purpose not in PURPOSES:
            raise Forbidden('unsupported_purpose')
        from .sql_connections import validate_dsn
        self.dsn = validate_dsn(dsn or connection_dsn(),allow_temporary=allow_temporary,client=client)
        self.tenant, self.project, self.purpose = tenant, project, purpose
        self.allow_temporary,self.client = allow_temporary,client
        self.journal = journal or Journal()

    def _connect(self):
        from psycopg.rows import dict_row
        from .sql_connections import connect
        return connect(self.dsn,allow_temporary=self.allow_temporary,client=self.client,row_factory=dict_row)

    def _scope(self, conn, tenant=None, project=None):
        conn.execute("SELECT set_config('allow.tenant',%s,true)",(tenant or self.tenant,))
        conn.execute("SELECT set_config('allow.project',%s,true)",(project or self.project,))
        conn.execute("SELECT set_config('allow.purpose',%s,true)",(self.purpose,))

    def _apply(self, conn, event):
        if event['seq'] == 0:
            return
        self._scope(conn,event['tenant'],event['project'])
        target = event['target']
        if event['action'] == 'REVOKE_RECORD':
            conn.execute('UPDATE retrieval.record SET revoked=true WHERE id=%s',(target,))
            conn.execute('UPDATE retrieval.model SET active=false WHERE id IN (SELECT model_id FROM retrieval.training_lineage WHERE record_id=%s)',(target,))
            conn.execute("UPDATE retrieval.embedding_intent SET status='CANCELLED' WHERE record_id=%s",(target,))
            conn.execute("UPDATE retrieval.outbox SET status='CANCELLED' WHERE record_id=%s OR model_id IN (SELECT model_id FROM retrieval.training_lineage WHERE record_id=%s)",(target,target))
        else:
            conn.execute('UPDATE retrieval.model SET active=false WHERE id=%s',(target,))
            conn.execute("UPDATE retrieval.outbox SET status='CANCELLED' WHERE model_id=%s",(target,))
        # Physical deletion is defense in depth; active-model filtering is authoritative.
        conn.execute('DELETE FROM retrieval.embedding WHERE record_id IN (SELECT id FROM retrieval.record WHERE revoked) OR model_id IN (SELECT id FROM retrieval.model WHERE NOT active)')

    def _replay(self, conn, initialize=False):
        state = conn.execute('SELECT * FROM retrieval.runtime_state WHERE singleton FOR UPDATE').fetchone()
        if not self.journal.path.exists() and initialize:
            count = conn.execute('SELECT count(*) AS n FROM retrieval.record').fetchone()['n']
            if state['journal_id'] is not None or count:
                raise Quarantined('cannot_initialize_nonempty_database')
            self.journal.initialize()
        events = self.journal.read()
        if state['journal_id'] not in (None,events[0]['journal_id']):
            raise Quarantined('journal_identity_mismatch')
        if state['journal_id'] is None:
            if not initialize:
                raise Quarantined('journal_not_initialized')
            state['journal_seq'], state['journal_head'] = 0, events[0]['hash']
        seq = state['journal_seq']
        if seq >= len(events) or events[seq]['hash'] != state['journal_head']:
            raise Quarantined('journal_rollback_or_gap')
        for event in events[seq+1:]:
            self._apply(conn,event)
        last = events[-1]
        conn.execute('UPDATE retrieval.runtime_state SET journal_id=%s,journal_seq=%s,journal_head=%s,quarantined=false WHERE singleton',
                     (last['journal_id'],last['seq'],last['hash']))
        self._scope(conn)

    @contextlib.contextmanager
    def transaction(self, initialize=False):
        # The independent lock makes a durable journal revoke deny-first, including
        # a revoke that crashed before the matching DB transaction committed.
        with self.journal.lock():
            with self._connect() as conn:
                self._scope(conn)
                self._replay(conn,initialize)
                yield conn

    def initialize(self):
        with self.transaction(initialize=True):
            pass

    def status(self):
        with self.transaction() as c:
            row = c.execute("SELECT count(*) AS records,count(*) FILTER(WHERE status='FULL' AND NOT revoked) AS full,count(*) FILTER(WHERE revoked) AS revoked FROM retrieval.record").fetchone()
            row['vectors'] = c.execute('SELECT count(*) AS n FROM retrieval.embedding e JOIN retrieval.model m ON m.id=e.model_id JOIN retrieval.record r ON r.id=e.record_id WHERE m.active AND m.servable AND NOT r.revoked AND %s=ANY(r.allowed_purposes)',(self.purpose,)).fetchone()['n']
            row['journal_sequence'] = c.execute('SELECT journal_seq FROM retrieval.runtime_state').fetchone()['journal_seq']
            row['models'] = c.execute('SELECT id,trained,active,servable FROM retrieval.model ORDER BY created_at').fetchall()
            row['source_coverage'] = c.execute("SELECT a.source_root AS source,count(DISTINCT r.id) AS records,count(DISTINCT a.id) AS source_files FROM retrieval.record r JOIN retrieval.record_origin o ON o.record_id=r.id JOIN retrieval.artifact a ON a.id=o.artifact_id WHERE r.status='FULL' AND NOT r.revoked GROUP BY a.source_root ORDER BY a.source_root").fetchall()
            row['queryProfile'] = {'scope':3,'bitwidth':4,'N':3,'temporal':False,'dimension':3072}
            row['quality'] = c.execute("SELECT split,count(DISTINCT family) AS families,count(*) AS records FROM retrieval.record WHERE status='FULL' AND NOT revoked GROUP BY split ORDER BY split").fetchall()
            return row

    def diagnostic(self,dataset,source_hash,reason,details):
        with self.transaction() as c:
            c.execute('INSERT INTO retrieval.diagnostic(tenant,project,dataset,source_hash,reason,details) VALUES(%s,%s,%s,%s,%s,%s::jsonb)',
                      (self.tenant,self.project,dataset,source_hash,reason,canonical(details)))

    def add_record(self, artifact, record, outcomes, metadata, model_id=None):
        if self.purpose != 'store':
            raise Forbidden('store_purpose_required')
        if set(record) != {'context','predicate','positives','negatives'}:
            raise ValueError('invalid_components')
        if metadata.get('certificate_status') != 'CHECKED' or not metadata.get('certificate_id') or metadata.get('root_path') != [3,metadata['target_slot'],5]:
            raise ValueError('checked_target_certificate_required')
        n = metadata['N']
        if n not in (3,4,5):
            raise ValueError('invalid_N')
        for polarity,key in [('positive','positives'),('negative','negatives')]:
            members = record[key]
            if len(members) != n or len({canonical(x) for x in members}) != n:
                raise ValueError('not_full_distinct_pool')
            if outcomes[polarity]['existence'] != 'SAT' or outcomes[polarity]['termination'] != 'CAP_REACHED':
                raise ValueError('not_full_validated_pool')
        # Full effective anonymous context includes bounds/profile/toolchain.
        context_bytes = canonical({'context':record['context'],'bounds':metadata['bounds'],'schema':SCHEMA,'toolchain':metadata['toolchain']})
        context_key = digest(context_bytes.encode())
        identity = {'record':record,'context':json.loads(context_bytes),'N':n,'status':'FULL','schema':SCHEMA,'ruleset':metadata['ruleset_digest'],'proof':metadata['certificate_id'],'tenant':self.tenant,'project':self.project}
        rid = digest(identity)
        aid = digest({'tenant':self.tenant,'project':self.project,'root':artifact['root'],'locator':artifact['locator'],'source_hash':artifact['source_hash']})
        rights = metadata.get('rights_version','local-user-2026-11-03-v1')
        allowed = metadata.get('allowed_purposes',list(PURPOSES))
        if not set(allowed) <= set(PURPOSES) or not {'store','retrieve'} <= set(allowed):
            raise ValueError('invalid_purpose_grant')
        with self.transaction() as c:
            prior_artifact=c.execute('SELECT source_hash,source_root,locator,snapshot FROM retrieval.artifact WHERE id=%s',(aid,)).fetchone()
            expected_artifact={'source_hash':artifact['source_hash'],'source_root':artifact['root'],'locator':artifact['locator'],'snapshot':artifact['snapshot']}
            if prior_artifact and prior_artifact!=expected_artifact:raise ValueError('artifact_hash_collision')
            c.execute('INSERT INTO retrieval.artifact(id,tenant,project,source_hash,source_root,locator,family,snapshot,provenance) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(id) DO NOTHING',
                      (aid,self.tenant,self.project,artifact['source_hash'],artifact['root'],artifact['locator'],metadata['family'],artifact['snapshot'],canonical(metadata)))
            old = c.execute('SELECT * FROM retrieval.record WHERE id=%s',(rid,)).fetchone()
            if old:
                c.execute('INSERT INTO retrieval.record_origin(tenant,project,record_id,artifact_id,target_slot,evidence) VALUES(%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING',(self.tenant,self.project,rid,aid,metadata['target_slot'],canonical(metadata)))
                if old['content'] != record or old['context_bytes'] != context_bytes or old['n'] != n:
                    raise ValueError('content_hash_collision')
                return rid
            c.execute('INSERT INTO retrieval.record(id,tenant,project,artifact_id,content,context_key,context_bytes,n,status,target_slot,family,allowed_purposes,rights_version,content_version) VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s,\'FULL\',%s,%s,%s,%s,%s)',
                      (rid,self.tenant,self.project,aid,canonical(record),context_key,context_bytes,n,metadata['target_slot'],metadata['family'],allowed,rights,rid))
            c.execute('UPDATE retrieval.record SET evidence=%s::jsonb WHERE id=%s',(canonical(metadata),rid))
            c.execute('INSERT INTO retrieval.record_origin(tenant,project,record_id,artifact_id,target_slot,evidence) VALUES(%s,%s,%s,%s,%s,%s::jsonb)',(self.tenant,self.project,rid,aid,metadata['target_slot'],canonical(metadata)))
            for polarity,key in [('positive','positives'),('negative','negatives')]:
                runid = digest({'record':rid,'polarity':polarity,'outcome':outcomes[polarity]})
                query = digest({'context':context_bytes,'predicate':record['predicate'],'polarity':polarity})
                c.execute('INSERT INTO retrieval.run(id,tenant,project,record_id,polarity,existence,termination,query_identity,details) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
                          (runid,self.tenant,self.project,rid,polarity,'SAT','CAP_REACHED',query,canonical(outcomes[polarity])))
                for witness in record[key]:
                    wbytes = canonical(witness); wid = digest({'context':context_bytes,'witness':witness,'tenant':self.tenant,'project':self.project})
                    existing = c.execute('SELECT canonical_bytes FROM retrieval.witness WHERE id=%s',(wid,)).fetchone()
                    if existing and existing['canonical_bytes'] != wbytes:
                        raise ValueError('witness_hash_collision')
                    c.execute('INSERT INTO retrieval.witness(id,tenant,project,context_key,canonical_bytes,content) VALUES(%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING',
                              (wid,self.tenant,self.project,context_key,wbytes,wbytes))
                    c.execute('INSERT INTO retrieval.membership(tenant,project,record_id,run_id,witness_id,polarity,validated) VALUES(%s,%s,%s,%s,%s,%s,true)',
                              (self.tenant,self.project,rid,runid,wid,polarity))
            c.execute('INSERT INTO retrieval.embedding_intent(tenant,project,record_id,content_version) VALUES(%s,%s,%s,%s)',(self.tenant,self.project,rid,rid))
            if model_id:
                self._queue(c,rid,model_id,rid)
        return rid

    def _queue(self,c,rid,model_id,version):
        c.execute('INSERT INTO retrieval.outbox(tenant,project,record_id,model_id,content_version) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                  (self.tenant,self.project,rid,model_id,version))

    def register_model(self,model_id,manifest,training_ids=()):
        if self.purpose != 'train':
            raise Forbidden('train_purpose_required')
        trained=bool(training_ids) or manifest.get('adapter_sha256')!='identity'
        if trained and not training_ids:raise ValueError('training_lineage_required')
        with self.transaction() as c:
            existing = c.execute('SELECT manifest FROM retrieval.model WHERE id=%s',(model_id,)).fetchone()
            if existing and existing['manifest'] != manifest:
                raise ValueError('model_hash_collision')
            c.execute('INSERT INTO retrieval.model(id,tenant,project,manifest,trained) VALUES(%s,%s,%s,%s::jsonb,%s) ON CONFLICT DO NOTHING',
                      (model_id,self.tenant,self.project,canonical(manifest),trained))
            for rid in training_ids:
                record = c.execute("SELECT * FROM retrieval.record WHERE id=%s AND NOT revoked AND split='train' AND 'train'=ANY(allowed_purposes)",(rid,)).fetchone()
                if not record:
                    raise Forbidden('unauthorized_training_lineage')
                c.execute('INSERT INTO retrieval.training_lineage(tenant,project,model_id,record_id,rights_version) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                          (self.tenant,self.project,model_id,rid,record['rights_version']))
            c.execute("INSERT INTO retrieval.outbox(tenant,project,record_id,model_id,content_version) SELECT tenant,project,id,%s,content_version FROM retrieval.record WHERE status='FULL' AND NOT revoked AND 'embed'=ANY(allowed_purposes) ON CONFLICT DO NOTHING",(model_id,))
            c.execute("UPDATE retrieval.embedding_intent SET status='QUEUED' WHERE record_id IN (SELECT record_id FROM retrieval.outbox WHERE model_id=%s) AND status!='CANCELLED'",(model_id,))

    def promote_model(self,model_id,evidence):
        if self.purpose!='train':raise Forbidden('train_purpose_required')
        from .promotion import verify_evidence
        if not isinstance(evidence,dict) or evidence.get('integrity_passed') is not True:
            raise Forbidden('integrity_gate_open')
        verified=verify_evidence(evidence)
        if verified.get('model_id')!=model_id:raise ValueError('promotion_model_mismatch')
        weights=verified.get('weights')
        if not isinstance(weights,list) or len(weights)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in weights) or abs(sum(weights)-1)>1e-9:
            raise ValueError('invalid_promotion_weights')
        with self.transaction() as c:
            model=c.execute('SELECT * FROM retrieval.model WHERE id=%s AND active FOR UPDATE',(model_id,)).fetchone()
            if not model:raise NotFound('active_model_not_found')
            if not model['manifest'].get('adapter_sha256') or verified.get('adapter_sha256')!=model['manifest']['adapter_sha256']:
                raise ValueError('promotion_adapter_mismatch')
            lineage=c.execute('SELECT record_id,rights_version FROM retrieval.training_lineage WHERE model_id=%s ORDER BY record_id',(model_id,)).fetchall()
            if sorted(verified.get('training_record_ids',[]))!=[x['record_id'] for x in lineage]:
                raise ValueError('promotion_lineage_mismatch')
            if model['trained']:
                counts=[verified.get(x) for x in ('family_components','validation_components','test_components')]
                metrics=[verified.get(x) for x in ('learned_family_macro_mrr','baseline_family_macro_mrr')]
                counts_valid=all(isinstance(x,int) and not isinstance(x,bool) for x in counts)
                metrics_valid=all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and 0<=x<=1 for x in metrics)
                source_valid=set(verified.get('source_coverage',[]))>={'alloy4fun','alloy5','alloy6'}
                if not (verified.get('quality_gate')=='PASS' and counts_valid and counts[0]>=12 and counts[1]>=2 and counts[2]>=2 and source_valid and metrics_valid and verified.get('frozen_manifest_id') and verified.get('validation_decision_sha256') and metrics[0]>=metrics[1]-.01):
                    raise Forbidden('quality_gate_open')
            if model['promotion'] is not None and model['promotion']!=evidence:raise ValueError('immutable_promotion')
            c.execute('UPDATE retrieval.model SET servable=true,promotion=%s::jsonb WHERE id=%s',(canonical(evidence),model_id))

    def claim_job(self,model_id=None):
        if self.purpose != 'embed':
            raise Forbidden('embed_purpose_required')
        with self.transaction() as c:
            # A dead process leaves RUNNING; retry is safe because publication is idempotent.
            row = c.execute("SELECT o.*,r.content FROM retrieval.outbox o JOIN retrieval.record r ON r.id=o.record_id JOIN retrieval.model m ON m.id=o.model_id WHERE (o.status='PENDING' OR (o.status='RUNNING' AND o.lease_until<now())) AND NOT r.revoked AND m.active AND r.status='FULL' AND 'embed'=ANY(r.allowed_purposes) AND r.content_version=o.content_version AND (%s::text IS NULL OR o.model_id=%s) ORDER BY o.id FOR UPDATE OF o SKIP LOCKED LIMIT 1",(model_id,model_id)).fetchone()
            if row:
                token=uuid.uuid4().hex
                c.execute("UPDATE retrieval.outbox SET status='RUNNING',attempts=attempts+1,claim_token=%s,lease_until=now()+interval '120 seconds' WHERE id=%s",(token,row['id']))
                row['claim_token']=token
            return row

    def publish(self,job,vector):
        if self.purpose != 'embed':
            raise Forbidden('embed_purpose_required')
        values = [float(x) for x in vector]
        if len(values)!=3072 or not all(math.isfinite(x) for x in values) or abs(math.sqrt(sum(x*x for x in values))-1)>1e-5:
            raise ValueError('invalid_vector')
        literal = '['+','.join(format(x,'.9g') for x in values)+']'
        with self.transaction() as c:
            eligible = c.execute("SELECT o.id FROM retrieval.outbox o JOIN retrieval.record r ON r.id=o.record_id JOIN retrieval.model m ON m.id=o.model_id WHERE o.id=%s AND o.record_id=%s AND o.model_id=%s AND o.content_version=%s AND r.content_version=o.content_version AND r.status='FULL' AND NOT r.revoked AND m.active AND 'embed'=ANY(r.allowed_purposes) AND o.status IN ('RUNNING','DONE') AND o.claim_token=%s AND o.lease_until>=now() FOR UPDATE OF o,r,m",(job['id'],job['record_id'],job['model_id'],job['content_version'],job['claim_token'])).fetchone()
            if not eligible:
                raise Forbidden('stale_or_revoked_publication')
            old = c.execute('SELECT vector::text AS vector FROM retrieval.embedding WHERE record_id=%s AND model_id=%s',(job['record_id'],job['model_id'])).fetchone()
            if old:
                previous = [float(x) for x in old['vector'].strip('[]').split(',')]
                if struct.pack('<3072f',*previous)!=struct.pack('<3072f',*values):
                    raise ValueError('non_idempotent_embedding')
            else:
                c.execute('INSERT INTO retrieval.embedding(tenant,project,record_id,model_id,content_version,vector) VALUES(%s,%s,%s,%s,%s,%s::vector)',
                          (self.tenant,self.project,job['record_id'],job['model_id'],job['content_version'],literal))
            c.execute("UPDATE retrieval.outbox SET status='DONE',error=NULL WHERE id=%s",(job['id'],))

    def fail_job(self,job,reason):
        with self.transaction() as c:
            c.execute("UPDATE retrieval.outbox SET status='ERROR',error=%s WHERE id=%s AND claim_token=%s AND lease_until>=now()",(str(reason)[:128],job['id'],job['claim_token']))

    def revoke(self,target,kind='record',reason='user_revocation'):
        if kind not in ('record','model'):
            raise ValueError('invalid_revoke_kind')
        with self.journal.lock():
            with self._connect() as c:
                self._scope(c); self._replay(c)
                table = 'retrieval.record' if kind=='record' else 'retrieval.model'
                if not c.execute('SELECT id FROM '+table+' WHERE id=%s',(target,)).fetchone():
                    raise NotFound('target_not_found')
                self.journal.append('REVOKE_RECORD' if kind=='record' else 'REVOKE_MODEL',target,self.tenant,self.project,reason)
                self._replay(c)

    def records(self,limit=20,model_id=None,include_content=False):
        with self.transaction() as c:
            rows=c.execute("SELECT r.id,r.family,r.split,r.n,r.status,r.context_key,r.content_version FROM retrieval.record r WHERE r.status='FULL' AND NOT r.revoked AND %s=ANY(r.allowed_purposes) AND EXISTS(SELECT 1 FROM retrieval.embedding e JOIN retrieval.model m ON m.id=e.model_id WHERE e.record_id=r.id AND e.content_version=r.content_version AND m.active AND m.servable) ORDER BY r.id LIMIT %s",(self.purpose,limit)).fetchall()
            return rows

    def add_training_variant(self,record_id,variant,worker_identity):
        if self.purpose!='store':raise Forbidden('store_purpose_required')
        with self.transaction() as c:
            row=c.execute("SELECT content,evidence FROM retrieval.record WHERE id=%s AND NOT revoked AND 'analyze'=ANY(allowed_purposes)",(record_id,)).fetchone()
            if not row:raise NotFound('authorized_record_not_found')
            from .training import checked_variant_record
            # This accepts only an internal isolated-worker result. Endpoint and
            # context linkage is checked here; Java performs independent replay.
            _,certificate_id=checked_variant_record(row['content'],row['evidence'],variant)
            vid=digest({'record_id':record_id,'certificate_id':certificate_id,'worker_identity':worker_identity})
            c.execute('INSERT INTO retrieval.training_variant(id,tenant,project,record_id,original_certificate_id,worker_identity,evidence) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING',
                      (vid,self.tenant,self.project,record_id,row['evidence']['certificate_id'],worker_identity,canonical(variant)))
            return vid

    def evaluation_records(self):
        with self.transaction() as c:
            rows=c.execute("SELECT r.id AS record_id,r.family,r.split,r.status,r.content,r.context_key,r.context_bytes,r.evidence,a.source_root AS source FROM retrieval.record r JOIN retrieval.artifact a ON a.id=r.artifact_id WHERE r.status='FULL' AND NOT r.revoked AND %s=ANY(r.allowed_purposes) ORDER BY r.id LIMIT 1000",(self.purpose,)).fetchall()
            derived=c.execute('SELECT record_id,evidence FROM retrieval.training_variant ORDER BY id').fetchall()
            byid={r['record_id']:r for r in rows}
            for item in derived:
                if item['record_id'] in byid:
                    byid[item['record_id']]['evidence'].setdefault('training_variants',[]).append(item['evidence'])
            return rows

    def assign_splits(self,assignments):
        if self.purpose != 'store':
            raise Forbidden('store_purpose_required')
        with self.transaction() as c:
            if c.execute('SELECT 1 FROM retrieval.training_lineage LIMIT 1').fetchone():
                raise Forbidden('split_frozen_after_training')
            for rid,split,family in assignments:
                if split not in ('train','validation','test'):
                    raise ValueError('invalid_split')
                c.execute('UPDATE retrieval.record SET split=%s,family=%s WHERE id=%s',(split,family,rid))

    def searchable(self,c,record_id,model_id=None):
        params = [record_id,self.purpose]
        clause = ''
        if model_id:
            clause=' AND e.model_id=%s';params.append(model_id)
        row = c.execute("SELECT r.*,e.model_id,e.vector::text AS vector,m.promotion,m.trained FROM retrieval.record r JOIN retrieval.embedding e ON e.record_id=r.id JOIN retrieval.model m ON m.id=e.model_id WHERE r.id=%s AND %s=ANY(r.allowed_purposes) AND NOT r.revoked AND r.status='FULL' AND e.content_version=r.content_version AND m.active AND m.servable"+clause+' ORDER BY m.created_at DESC LIMIT 1',params).fetchone()
        if not row:
            raise NotFound('eligible_record_not_found')
        return row
