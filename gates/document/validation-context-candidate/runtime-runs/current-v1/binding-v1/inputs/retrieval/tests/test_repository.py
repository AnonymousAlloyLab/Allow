"""Real PostgreSQL/pgvector, real worker, journal and LangGraph integration checks."""
import copy
import math
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from allow_retrieval.common import canonical,digest
from allow_retrieval.corpus import worker,normalize_full
from allow_retrieval.database import Repository,Forbidden,NotFound
from allow_retrieval.journal import Journal,Quarantined
from allow_retrieval.ranking import search,score,overlap
from allow_retrieval.importer import split_records,family_id,read_source

class RankingTests(unittest.TestCase):
    def test_exact_overlap_and_wrong_context(self):
        a={'vector':[1/math.sqrt(3072)]*3072,'context_key':'a','context_bytes':'a',
           'content':{'positives':[[1],[2],[3]],'negatives':[[4],[5],[6]]}}
        b=copy.deepcopy(a);b['content']['positives']=[[1],[2],[3],[7],[8]]
        s=score(a,b)
        self.assertAlmostEqual(s['sharedPositive'],.6)
        self.assertAlmostEqual(s['score'],.55+.225*.6+.225)
        b['context_bytes']='changed';s=score(a,b)
        self.assertFalse(s['contextCompatible']);self.assertEqual(s['sharedNegative'],0)
        b['content']['positives']=a['content']['negatives']
        self.assertEqual(overlap(a['content']['positives'],b['content']['positives'],True),0)
        with self.assertRaises(ValueError):score(a,b,(-1,1,1))

    def test_family_alias_duplicate_union(self):
        self.assertEqual(family_id('alloy4fun',Path('coursesNew/correct/a.als')),family_id('alloy4fun',Path('coursesOld/a.als')))
        rows=[]
        for i in range(15):
            rows.append({'id':str(i),'origin_family':'f'+str(i),'source_hash':'s'+str(i),'content':{'predicate':['p',i]}})
        rows[1]['source_hash']=rows[0]['source_hash']
        rows[2]['content']=rows[1]['content']
        assignments,manifest=split_records(rows);lookup={x[0]:x[1] for x in assignments}
        self.assertEqual(lookup['0'],lookup['1']);self.assertEqual(lookup['1'],lookup['2'])
        self.assertEqual(manifest['components'],13)
        self.assertTrue(all(v==0 for v in manifest['cross_split_intersections'].values()))

class SourceTests(unittest.TestCase):
    def test_no_follow_symlink_components(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'model.als').write_text('sig A {}')
            self.assertEqual(read_source(root,root/'model.als')[1],b'sig A {}')
            (root/'link.als').symlink_to(root/'model.als')
            (root/'linked').symlink_to(root,target_is_directory=True)
            with self.assertRaises(OSError):read_source(root,root/'link.als')
            with self.assertRaises(OSError):read_source(root,root/'linked/model.als')
            with self.assertRaises(ValueError):read_source(root,root/'../escape.als')

class JournalTests(unittest.TestCase):
    def test_chain_missing_corrupt_and_truncation(self):
        with tempfile.TemporaryDirectory() as t:
            j=Journal(t)
            with j.lock():
                with self.assertRaises(Quarantined):j.read()
                j.initialize();j.append('REVOKE_RECORD','record','tenant','project','test')
                self.assertEqual(len(j.read()),2)
                data=j.path.read_bytes();j.path.write_bytes(data[:-1])
                with self.assertRaises(Quarantined):j.read()
                j.path.write_bytes(data.replace(b'"target":"record"',b'"target":"forged"'))
                with self.assertRaises(Quarantined):j.read()

class SandboxTests(unittest.TestCase):
    def test_host_sentinel_denied_and_positive_worker(self):
        import subprocess
        from allow_retrieval.corpus import sandbox_command,JAVA_HOME,worker
        with tempfile.TemporaryDirectory() as t:
            sentinel=Path(t)/'Sentinel.java'
            sentinel.write_text('/** Sandbox sentinel fixture. */ class Sentinel { /** Prints a sentinel. @param args unused */ public static void main(String[] args) {System.out.println("HOST_SENTINEL_LEAK");}}')
            result=subprocess.run(sandbox_command()+[str(JAVA_HOME/'bin/java'),str(sentinel)],capture_output=True,timeout=10,env={})
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn(b'HOST_SENTINEL_LEAK',result.stdout)
        self.assertEqual(worker('sig A {r:set A} pred p {some r}',0)['status'],'FULL')

class PostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tenant='test-'+uuid.uuid4().hex
        cls.store=Repository(tenant=cls.tenant,purpose='store')
        try:cls.store.status()
        except (OSError,ImportError):raise unittest.SkipTest('local PostgreSQL runtime unavailable')
        cls.ids=[]
        for source in ('sig A {r:set A} pred p {some r}', 'sig A {r:set A} pred p {no r}'):
            response=worker(source,0);record,outcomes,meta=normalize_full(response)
            meta.update(N=3,target_slot=0,family='fixture:'+digest(source.encode()))
            rid=cls.store.add_record({'root':'authored-test','locator':digest(source.encode()),'source_hash':digest(source.encode()),'snapshot':'synthetic-no-source-snapshot'},record,outcomes,meta)
            cls.ids.append(rid)
        cls.store.assign_splits([(rid,'train','fixture'+str(i)) for i,rid in enumerate(cls.ids)])
        cls.model='test-model-'+uuid.uuid4().hex
        cls.train=Repository(tenant=cls.tenant,purpose='train')
        cls.train.register_model(cls.model,{'kind':'synthetic-test-vectors','adapter_sha256':'synthetic-test'},[cls.ids[0]])
        with cls.store.transaction() as c:
            cls.intent_count=c.execute('SELECT count(*) AS n FROM retrieval.embedding_intent').fetchone()['n']
        from allow_retrieval.promotion import freeze_evidence
        cls.train.promote_model(cls.model,freeze_evidence({'model_id':cls.model,'adapter_sha256':'synthetic-test','training_record_ids':[cls.ids[0]],'integrity_passed':True,'quality_gate':'PASS','family_components':12,'validation_components':2,'test_components':2,'frozen_manifest_id':'synthetic-test','validation_decision_sha256':'synthetic-test','source_coverage':['alloy4fun','alloy5','alloy6'],'weights':[.55,.225,.225],'learned_family_macro_mrr':1.,'baseline_family_macro_mrr':1.}))
        cls.embed=Repository(tenant=cls.tenant,purpose='embed')
        cls.vector=[1/math.sqrt(3072)]*3072
        cls.jobs=[]
        while (job:=cls.embed.claim_job()):
            cls.embed.publish(job,cls.vector);cls.jobs.append(job)

    @classmethod
    def tearDownClass(cls):
        # Keep journal tombstones durable; clean isolated test rows in FK order.
        with cls.store.transaction() as c:
            for table in ('embedding','outbox','training_lineage','membership','run','record_origin','embedding_intent','record','witness','artifact','model','diagnostic'):
                c.execute('DELETE FROM retrieval.'+table)

    def test_01_nonbypassrls_exact_and_langgraph(self):
        self.assertEqual(self.intent_count,2)
        retrieve=Repository(tenant=self.tenant)
        with retrieve.transaction() as c:
            flags=c.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
            self.assertFalse(flags['rolsuper']);self.assertFalse(flags['rolbypassrls'])
        hidden='unpromoted-'+uuid.uuid4().hex
        self.train.register_model(hidden,{'kind':'unpromoted'},[self.ids[1]])
        with self.assertRaises(ValueError):self.train.promote_model(hidden,{'integrity_passed':True,'quality_gate':'OPEN'})
        result=search(retrieve,self.ids[0],10,self.model)
        self.train.revoke(hidden,kind='model',reason='test_cleanup_unpromoted')
        self.assertEqual(result['candidateCount'],1)
        self.assertEqual(result['results'][0]['recordId'],self.ids[1])
        with retrieve._connect() as raw:
            self.assertEqual(raw.execute('SELECT count(*) AS n FROM retrieval.record').fetchone()['n'],0)
        with retrieve.transaction() as c:
            c.execute('SAVEPOINT purpose_test')
            c.execute("UPDATE retrieval.record SET allowed_purposes=array_remove(allowed_purposes,'retrieve') WHERE id=%s",(self.ids[0],))
            with self.assertRaises(NotFound):retrieve.searchable(c,self.ids[0],self.model)
            c.execute('ROLLBACK TO SAVEPOINT purpose_test')
        self.assertAlmostEqual(result['results'][0]['score'],.55)
        with self.assertRaises(NotFound):search(Repository(tenant='wrong-'+self.tenant),self.ids[0])
        with self.assertRaises(Forbidden):search(self.store,self.ids[0])
        from allow_retrieval.rag import build_graph
        output=build_graph(retrieve).invoke({'record_id':self.ids[0],'limit':2})
        self.assertEqual(len(output['documents']),1)
        self.assertTrue(output['documents'][0].metadata['evidenceOnly'])
        import json
        content=json.loads(output['documents'][0].page_content)
        self.assertEqual(set(content),{'context','predicate','positives','negatives'})
        self.assertEqual(len(content['positives']),3)
        self.assertNotIn('sig A {r:set A}',output['documents'][0].page_content)

    def test_02_atomic_failure_and_full_gate(self):
        with self.store.transaction() as c:before=c.execute('SELECT count(*) AS n FROM retrieval.record').fetchone()['n']
        with self.assertRaises(ValueError):
            self.store.add_record({}, {'context':[],'predicate':[],'positives':[],'negatives':[]},{},{'N':3,'target_slot':0})
        with self.store.transaction() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM retrieval.record').fetchone()['n'],before)
        from unittest.mock import patch
        response=worker('sig A {r:set A} pred p {some r and some A}',0)
        content,outcomes,meta=normalize_full(response)
        meta.update(N=3,target_slot=0,family='rollback-fixture')
        with patch.object(self.store,'_queue',side_effect=RuntimeError('injected_after_all_pool_writes')):
            with self.assertRaises(RuntimeError):
                self.store.add_record({'root':'authored-test','locator':'rollback','source_hash':digest(b'rollback'),'snapshot':'synthetic'},content,outcomes,meta,self.model)
        with self.store.transaction() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM retrieval.record').fetchone()['n'],before)
        job=self.jobs[0]
        self.embed.publish(job,self.vector) # identical retry
        with self.assertRaises(ValueError):self.embed.publish(job,[0]*3072)

    def test_025_lease_owner_and_expired_claim(self):
        with self.store.transaction() as c:
            c.execute("UPDATE retrieval.outbox SET status='PENDING' WHERE id=%s",(self.jobs[0]['id'],))
        old=self.embed.claim_job()
        self.assertIsNotNone(old)
        self.assertIsNone(self.embed.claim_job())
        with self.store.transaction() as c:
            c.execute("UPDATE retrieval.outbox SET lease_until=now()-interval '1 second' WHERE id=%s",(old['id'],))
        new=self.embed.claim_job()
        self.assertNotEqual(old['claim_token'],new['claim_token'])
        with self.assertRaises(Forbidden):self.embed.publish(old,self.vector)
        self.embed.publish(new,self.vector)
        self.jobs[0]=new

    def test_03_lineage_revoke_restore_and_retries(self):
        with self.store.transaction() as c:
            state=c.execute('SELECT * FROM retrieval.runtime_state').fetchone()
        self.store.revoke(self.ids[0],reason='test_training_rights_revoke')
        with self.assertRaises(NotFound):search(Repository(tenant=self.tenant),self.ids[1])
        with self.assertRaises(Forbidden):self.embed.publish(self.jobs[1],self.vector)
        # Restore pre-revoke database rows/head as a stale backup would. Independent
        # log is deliberately not restored; the next startup must replay tombstones.
        with self.store.journal.lock():
            with self.store._connect() as c:
                self.store._scope(c)
                c.execute('UPDATE retrieval.record SET revoked=false')
                c.execute('UPDATE retrieval.model SET active=true')
                c.execute("UPDATE retrieval.outbox SET status='PENDING'")
                c.execute('UPDATE retrieval.runtime_state SET journal_seq=%s,journal_head=%s,quarantined=true',(state['journal_seq'],state['journal_head']))
        status=self.store.status();self.assertEqual(status['revoked'],1)
        self.assertEqual(status['vectors'],0)
        with self.store.transaction() as c:
            self.assertFalse(c.execute('SELECT active FROM retrieval.model WHERE id=%s',(self.model,)).fetchone()['active'])
            self.assertEqual(c.execute("SELECT count(*) AS n FROM retrieval.outbox WHERE status!='CANCELLED' AND model_id=%s",(self.model,)).fetchone()['n'],0)

if __name__=='__main__':unittest.main()
