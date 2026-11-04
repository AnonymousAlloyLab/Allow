"""Real proxy-only SQL document atomicity, replay, scope and recovery regressions."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid
from allow_documents import identity, wire
from allow_documents.store import Store, KnownRollback


def scope():
    """Create a private test scope without modifying production identity."""
    return {'principalId':str(uuid.uuid4()),'workspaceId':str(uuid.uuid4()),'logicalLaunchId':str(uuid.uuid4())}


def artifact(source='', policy='document-v1'):
    """Build a checked-frame fixture; parser authority belongs to Java integration."""
    return {'artifactId':wire.fresh_id(),'mode':'BLOCK_SUPPORTED','source':source,
            'sourceHash':hashlib.sha256(source.encode()).hexdigest(),'module':{'version':1,'signatures':[],
            'fields':[],'predicates':[],'facts':[],'assertions':[],'commands':[],'nodes':[]},
            'occurrences':[],'trivia':[],'analysisDescriptors':[],'policyVersion':policy,'dependencyHash':'none'}


class WireTests(unittest.TestCase):
    def test_strict_duplicate_surrogate_number_and_limit(self):
        """Malformed frames fail before database access or large allocation."""
        for raw in (b'{"x":1,"x":2}',b'"\\ud800"',b'1.5',b'NaN',b'9007199254740992',b'\xef\xbb\xbf{}'):
            with self.assertRaises((ValueError,UnicodeError)):
                wire.decode(raw)
        with self.assertRaises(ValueError):
            wire.unb64('A'*100,1)

    def test_private_identity_restart_modes_and_symlink(self):
        """Durable identity survives load and denies unsafe permissions/symlinks."""
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root)/'documents'
            first=identity.provision(directory)
            self.assertEqual(first,identity.load(directory))
            os.chmod(directory/'identity.json',0o644)
            with self.assertRaises(ValueError):identity.load(directory)
            os.chmod(directory/'identity.json',0o600)
            (directory/'identity.json').rename(directory/'saved')
            (directory/'identity.json').symlink_to(directory/'saved')
            with self.assertRaises(ValueError):identity.load(directory)


class DocumentSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Use isolated owner/workspace while retaining real proxy connections."""
        cls.store=Store(scope());cls.store.initialize('document-v1')

    def request(self, document='CREATE', operation='CREATE', expected=None, body=None):
        """Prepare exact original HTTP bytes plus trusted owner-incarnation frame."""
        key=uuid.uuid4().hex
        content=body or ({'idempotencyKey':key,'title':'Private test'} if operation=='CREATE' else {'idempotencyKey':key,'expectedRevision':expected,'candidate':{'mode':'SOURCE','source':''}})
        if operation=='HISTORY_COPY' and body is None:
            content={'idempotencyKey':key,'expectedRevision':expected,'targetRevision':0,'direction':'UNDO'}
        content['idempotencyKey']=key
        route='/api/v1/documents' if operation=='CREATE' else '/api/v1/documents/'+document+('/history-copy' if operation=='HISTORY_COPY' else '/commit')
        return {'documentId':document,'key':key,'method':'POST','route':route,'bodyBase64':wire.b64(wire.encode(content)),
                'ownerPid':os.getpid(),'ownerStartTicks':identity.process_start(os.getpid()),'operation':operation,'expectedRevision':expected}

    def finish(self, req, admission, value=None, result='COMMITTED', target=None, direction=None, id_remapping=None):
        """Submit trusted bounded final candidate with exact original request identity."""
        value=value if value is not None else artifact()
        data={'artifact':value,'idRemapping':id_remapping if id_remapping is not None else {}}
        if result=='REJECTED' and req['documentId']!='CREATE':
            data['acceptedRevision']=self.store.read({'documentId':req['documentId'],'revision':None})['headRevision']
        outcome=wire.encode({'protocol':1,'requestId':str(uuid.uuid4()),'status':result,'data':data})
        args={key:req[key] for key in ('documentId','key','method','route','bodyBase64')}
        args.update(nonce=admission['nonce'],policyVersion=value['policyVersion'],expectedRevision=req['expectedRevision'],artifact=value if result=='COMMITTED' else None,
                    outcomeBase64=wire.b64(outcome),result=result,targetRevision=target,direction=direction)
        return self.store.finalize(args),args,outcome

    def create(self):
        """Create accepted revision zero through admission and final transaction."""
        req=self.request();admission=self.store.admit(req)
        result,args,raw=self.finish(req,admission)
        self.assertEqual(result['status'],'COMMITTED')
        return result['documentId'],req,args,raw

    def test_encoded_route_preserved_and_encoding_change_collides(self):
        """Only literal colon or canonical percent3A route is admitted, never normalized."""
        document,_,_,_=self.create();req=self.request(document,'COMMIT',0)
        req['route']=req['route'].replace('server:','server%3A')
        a=self.store.admit(req);result,args,raw=self.finish(req,a)
        self.assertEqual(result['status'],'COMMITTED')
        self.assertEqual(self.store.receipt(req)['responseBase64'],wire.b64(raw))
        changed=dict(req,route=req['route'].replace('server%3A','server:'))
        self.assertEqual(self.store.receipt(changed)['status'],'IDEMPOTENCY_CONFLICT')
        for route in (req['route'].replace('%3A','%3a'),req['route']+'?q=1',req['route'].replace('%3A','%253A')):
            with self.assertRaises(ValueError):wire.request(dict(req,route=route))

    def test_create_revision_zero_and_exact_replay_at_stale_base(self):
        """Exact receipt replay neither revalidates nor appends a second revision."""
        document,req,args,raw=self.create()
        self.assertEqual(self.store.read({'documentId':document,'revision':0})['headRevision'],0)
        replay=self.store.finalize(args)
        self.assertEqual(replay,{'status':'REPLAY','responseBase64':wire.b64(raw)})
        changed=dict(req);changed['bodyBase64']=wire.b64(wire.unb64(req['bodyBase64'],262144)+b' ')
        self.assertEqual(self.store.receipt(changed)['status'],'IDEMPOTENCY_CONFLICT')

    def test_rejected_receipt_and_nonce_fence(self):
        """Stale owner cannot finalize; deterministic denial is itself replayable."""
        document,_,_,_=self.create();req=self.request(document,'COMMIT',0);admission=self.store.admit(req)
        result,args,raw=self.finish(req,admission,result='REJECTED')
        self.assertEqual(result['status'],'REJECTED')
        self.assertEqual(self.store.receipt(req)['responseBase64'],wire.b64(raw))
        self.assertEqual(self.store.read({'documentId':document,'revision':None})['headRevision'],0)
        req2=self.request(document,'COMMIT',0);a2=self.store.admit(req2);a2['nonce']=str(uuid.uuid4())
        self.assertEqual(self.finish(req2,a2)[0]['status'],'STALE_OWNER')

    def test_competing_revision_and_terminal_stale_receipt(self):
        """Concurrent bases produce one appended revision and immutable stale denial."""
        document,_,_,_=self.create()
        first=self.request(document,'COMMIT',0);second=self.request(document,'COMMIT',0)
        a=self.store.admit(first);b=self.store.admit(second)
        self.assertEqual(self.finish(first,a)[0]['status'],'COMMITTED')
        self.assertEqual(self.finish(second,b)[0]['status'],'STALE_REVISION')
        self.assertEqual(self.finish(second,b,result='REJECTED')[0]['status'],'REJECTED')
        self.assertEqual(self.store.read({'documentId':document,'revision':None})['headRevision'],1)

    def test_scope_and_immutable_sql_grants(self):
        """RLS hides foreign documents and app role cannot rewrite receipts/history."""
        document,_,_,_=self.create();foreign=Store(scope());foreign.initialize('document-v1')
        with self.assertRaises(ValueError):foreign.read({'documentId':document,'revision':None})
        for sql in ('UPDATE documents.revision SET revision=99','DELETE FROM documents.receipt','UPDATE documents.artifact SET content=%s'):
            with self.assertRaises(Exception):
                with self.store.transaction() as c:c.execute(sql,(b'x',) if '%s' in sql else ())

    def test_policy_fence_and_history_zero_fresh_artifact(self):
        """Policy changes invalidate checked frames; restore zero appends fresh identity."""
        own=Store(scope());own.initialize('document-v1');oldstore=self.store;self.store=own
        try:
            document,_,_,_=self.create();req=self.request(document,'HISTORY_COPY',0);a=own.admit(req)
            own.policy('document-v1','document-v2')
            self.assertEqual(self.finish(req,a,target=0,direction='UNDO')[0]['status'],'REVALIDATE')
            value=artifact(policy='document-v2')
            result,_,_=self.finish(req,a,value,target=0,direction='UNDO')
            self.assertEqual(result['revision'],1)
            historical=own.read({'documentId':document,'revision':0})
            fresh=own.read({'documentId':document,'revision':1})
            self.assertEqual(historical['artifact']['policyVersion'],'document-v1')
            self.assertNotEqual(historical['artifact']['artifactId'],fresh['artifact']['artifactId'])
        finally:self.store=oldstore

    def test_live_owner_and_verified_dead_takeover(self):
        """Process start ticks prevent PID-reuse takeover and new nonce fences old frame."""
        child=subprocess.Popen(['/bin/sleep','20'])
        req=self.request();req['ownerPid']=child.pid;req['ownerStartTicks']=identity.process_start(child.pid)
        try:
            first=self.store.admit(req);retry=dict(req,ownerPid=os.getpid(),ownerStartTicks=identity.process_start(os.getpid()))
            self.assertEqual(self.store.admit(retry)['status'],'IN_PROGRESS')
            child.terminate();child.wait()
            recovered=self.store.admit(retry)
            self.assertNotEqual(first['nonce'],recovered['nonce'])
            self.assertEqual(self.finish(retry,first)[0]['status'],'STALE_OWNER')
            self.assertEqual(self.finish(retry,recovered)[0]['status'],'COMMITTED')
        finally:
            if child.poll() is None:child.kill();child.wait()

    def test_simultaneous_exact_key_serializes_and_commits_once(self):
        """Parallel duplicate admissions/finalizers yield one revision and one receipt."""
        from concurrent.futures import ThreadPoolExecutor
        req=self.request()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(self.store.admit,[req,req]))
        self.assertEqual(sorted(x['status'] for x in results),['ADMITTED','IN_PROGRESS'])
        admitted=next(x for x in results if x['status']=='ADMITTED')
        value=artifact();args={key:req[key] for key in ('documentId','key','method','route','bodyBase64')}
        args.update(nonce=admitted['nonce'],policyVersion='document-v1',expectedRevision=None,artifact=value,
                    outcomeBase64=wire.b64(wire.encode({'protocol':1,'requestId':str(uuid.uuid4()),'status':'COMMITTED','data':{}})),result='COMMITTED',targetRevision=None,direction=None)
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(self.store.finalize,[args,args]))
        self.assertEqual(sorted(x['status'] for x in results),['COMMITTED','REPLAY'])
        self.assertEqual(self.store.read({'documentId':admitted['documentId'],'revision':None})['headRevision'],0)

    def test_applied_commit_lost_ack_and_denial_lost_ack_recover_receipt(self):
        """Injected acknowledgement loss after real commit recovers both outcomes."""
        from contextlib import contextmanager
        from unittest.mock import patch
        from allow_documents.store import UncertainCommit
        document,_,_,_=self.create()
        for kind in ('COMMITTED','REJECTED'):
            head=self.store.read({'documentId':document,'revision':None})['headRevision']
            req=self.request(document,'COMMIT',head);a=self.store.admit(req)
            original=self.store.transaction
            @contextmanager
            def lose_ack():
                with original() as connection:
                    yield connection
                raise OSError('forced_lost_commit_ack')
            # Only final SQL transaction loses its acknowledgement; initial receipt read succeeds.
            calls=[0]
            @contextmanager
            def controlled():
                calls[0]+=1
                manager=original() if calls[0]==1 else lose_ack()
                with manager as connection:yield connection
            # Build complete final frame before injecting loss (rejection helper otherwise reads head).
            value=artifact();args={key:req[key] for key in ('documentId','key','method','route','bodyBase64')}
            outcome=wire.encode({'protocol':1,'requestId':str(uuid.uuid4()),'status':kind,'data':{'acceptedRevision':head,'idRemapping':{}}})
            args.update(nonce=a['nonce'],policyVersion='document-v1',expectedRevision=head,artifact=value if kind=='COMMITTED' else None,outcomeBase64=wire.b64(outcome),result=kind,targetRevision=None,direction=None)
            with patch.object(self.store,'transaction',controlled):
                with self.assertRaises(UncertainCommit):self.store.finalize(args)
            self.assertEqual(self.store.receipt(req)['responseBase64'],wire.b64(outcome))
            self.assertEqual(self.store.read({'documentId':document,'revision':None})['headRevision'],head+int(kind=='COMMITTED'))

    def test_reaped_worker_without_captured_start_ticks_requires_absent_pid(self):
        """Null start capture accepts only verified reaped/absent PID, never live reuse."""
        req=self.request();a=self.store.admit(req)
        proof={key:req[key] for key in ('documentId','key','method','route','bodyBase64','ownerPid','ownerStartTicks')}
        proof.update(nonce=a['nonce'],workerPid=os.getpid(),workerStartTicks=None,noWorkerStarted=False)
        with self.assertRaises(ValueError):self.store.recover(proof)
        child=subprocess.Popen(['/bin/true']);child.wait()
        self.assertIsNone(identity.process_start(child.pid))
        proof['workerPid']=child.pid
        fresh=self.store.recover(proof)
        self.assertEqual(fresh['status'],'ADMITTED')
        self.assertNotEqual(a['nonce'],fresh['nonce'])
        self.assertEqual(self.finish(req,a)[0]['status'],'STALE_OWNER')
        self.assertEqual(self.finish(req,fresh)[0]['status'],'COMMITTED')

    def test_lost_admission_ack_recovers_same_supervisor_before_worker_start(self):
        """A committed admission with lost reply is recoverable without process restart."""
        from contextlib import contextmanager
        from unittest.mock import patch
        req=self.request();original=self.store.transaction
        @contextmanager
        def lost():
            with original() as connection:yield connection
            raise OSError('lost_admission_ack')
        with patch.object(self.store,'transaction',lost):
            with self.assertRaises(OSError):self.store.admit(req)
        proof={key:req[key] for key in ('documentId','key','method','route','bodyBase64','ownerPid','ownerStartTicks')}
        proof['noWorkerStarted']=True
        recovered=self.store.recover_unstarted(proof)
        self.assertEqual(recovered['status'],'ADMITTED')
        self.assertEqual(self.finish(req,recovered)[0]['status'],'COMMITTED')

    def test_unknown_sqlstates_never_claim_known_rollback(self):
        """Actual psycopg unknown-completion error classes retain uncertainty."""
        import psycopg.errors
        from unittest.mock import patch
        from allow_documents.store import UncertainCommit
        req=self.request();a=self.store.admit(req)
        for error in (psycopg.errors.TransactionResolutionUnknown('injected08007'),
                      psycopg.errors.StatementCompletionUnknown('injected40003'),
                      psycopg.errors.ConnectionFailure('injected08006')):
            with patch.object(self.store,'finish',side_effect=error):
                with self.assertRaises(UncertainCommit):self.finish(req,a)
        self.assertEqual(self.store.receipt(req)['status'],'ABSENT')
        self.assertEqual(self.finish(req,a)[0]['status'],'COMMITTED')

    def test_live_supervisor_recovery_requires_reap_proof(self):
        """Same live supervisor rotates nonce only after owned worker death proof."""
        req=self.request();first=self.store.admit(req)
        self.assertEqual(self.store.admit(req)['status'],'IN_PROGRESS')
        recover={key:req[key] for key in ('documentId','key','method','route','bodyBase64','ownerPid','ownerStartTicks')}
        recover.update(nonce=first['nonce'],workerPid=os.getpid(),workerStartTicks=identity.process_start(os.getpid()),noWorkerStarted=False)
        with self.assertRaises(ValueError):self.store.recover(recover)
        recover.update(workerPid=None,workerStartTicks=None,noWorkerStarted=True)
        fresh=self.store.recover(recover)
        self.assertNotEqual(first['nonce'],fresh['nonce'])
        self.assertEqual(self.finish(req,first)[0]['status'],'STALE_OWNER')
        self.assertEqual(self.finish(req,fresh)[0]['status'],'COMMITTED')

    def test_final_rejection_observed_head_is_locked(self):
        """Denial is not receipted with a stale acceptedRevision response."""
        document,_,_,_=self.create();req=self.request(document,'COMMIT',0);a=self.store.admit(req)
        _,args,_=self.finish(req,dict(a,nonce=str(uuid.uuid4())),result='REJECTED')
        raw=wire.decode(wire.unb64(args['outcomeBase64'],wire.MAX_RESPONSE))
        raw['data']['acceptedRevision']=99;args['nonce']=a['nonce'];args['outcomeBase64']=wire.b64(wire.encode(raw))
        self.assertEqual(self.store.finalize(args),{'status':'STALE_REVISION','acceptedRevision':0})
        self.assertEqual(self.store.receipt(req)['status'],'ABSENT')
        self.assertEqual(self.finish(req,a,result='REJECTED')[0]['status'],'REJECTED')

    def test_receipt_replay_ignores_broken_new_checked_frame(self):
        """Existing receipt is returned before new output/checked artifact validation."""
        _,_,args,raw=self.create();args['artifact']={'malformed':True};args['outcomeBase64']='!'
        self.assertEqual(self.store.finalize(args),{'status':'REPLAY','responseBase64':wire.b64(raw)})

    def test_locked_historical_fresh_id_collision_and_remapping_denial(self):
        """Generated IDs cannot alias unsubmitted historical IDs even of the same kind."""
        document,_,_,_=self.create();old=wire.fresh_id()
        initial=artifact();initial['module']['signatures']=[{'tag':'signature','id':old,'name':'A','multiplicity':'set'}]
        req=self.request(document,'COMMIT',0);self.finish(req,self.store.admit(req),initial)
        draft='draft:'+str(uuid.uuid4());raw=artifact()['module']
        raw['signatures']=[{'tag':'signature','id':draft,'name':'B','multiplicity':'set'}]
        body={'expectedRevision':1,'candidate':{'mode':'BLOCK_SUPPORTED','module':raw,'presentationCopies':[]}}
        req=self.request(document,'COMMIT',1,body);a=self.store.admit(req)
        colliding=artifact();colliding['module']=copy.deepcopy(raw);colliding['module']['signatures'][0]['id']=old
        with self.assertRaises(ValueError):self.finish(req,a,colliding,id_remapping={draft:old})
        self.assertEqual(self.store.receipt(req)['status'],'ABSENT')
        self.assertEqual(self.store.read({'documentId':document,'revision':None})['headRevision'],1)
        fresh=wire.fresh_id();value=artifact();value['module']=copy.deepcopy(raw);value['module']['signatures'][0]['id']=fresh
        for mapping in ({},{draft:fresh,'draft:'+str(uuid.uuid4()):wire.fresh_id()}):
            with self.assertRaises(ValueError):self.finish(req,a,value,id_remapping=mapping)
        self.assertEqual(self.finish(req,a,value,id_remapping={draft:fresh})[0]['status'],'COMMITTED')
        source=self.request(document,'COMMIT',2);s=self.store.admit(source)
        reused=artifact();reused['module']=copy.deepcopy(value['module'])
        with self.assertRaises(ValueError):self.finish(source,s,reused)
        self.assertEqual(self.store.receipt(source)['status'],'ABSENT')

    def test_owned_ids_bounded_kinds_and_cross_scope_fk(self):
        """Historical ownership returns stable categories; foreign composite FK denies."""
        document,_,_,_=self.create();req=self.request(document,'COMMIT',0);a=self.store.admit(req)
        value=artifact();sig,node=wire.fresh_id(),wire.fresh_id()
        value['module']['signatures']=[{'tag':'signature','id':sig,'name':'A','multiplicity':'set'}]
        value['module']['nodes']=[{'tag':'signature_ref','id':node,'targetId':sig}]
        self.finish(req,a,value)
        self.assertEqual(self.store.owned_ids({'documentId':document,'ids':[sig,node]}),{'ids':{sig:'signature',node:'expression'}})
        with self.assertRaises(ValueError):self.store.owned_ids({'documentId':document,'ids':[sig]*4097})
        foreign=Store(scope());foreign.initialize('document-v1')
        with self.assertRaises(Exception):
            with foreign.transaction() as c:
                c.execute('INSERT INTO documents.artifact(principal_id,workspace_id,document_id,artifact_id,content,source_hash,policy_version) VALUES(%s,%s,%s,%s,%s,%s,%s)',(foreign.principal,foreign.workspace,document,wire.fresh_id(),b'{}','x','document-v1'))

    def test_create_capacity_reserves_pending_documents_and_replay(self):
        """63 existing plus pending CREATE rejects another slot; replay ignores quotas."""
        own=Store(scope());own.initialize('document-v1');oldstore=self.store;self.store=own
        try:
            document,req,args,raw=self.create()
            with own.transaction() as c:c.execute('UPDATE documents.workspace SET document_count=63')
            admitted=own.admit(self.request())
            self.assertEqual(admitted['status'],'ADMITTED')
            self.assertEqual(own.admit(self.request())['status'],'CAPACITY_PRE_ADMISSION')
            self.assertEqual(own.receipt(req)['responseBase64'],wire.b64(raw))
        finally:self.store=oldstore

    def test_failure_after_append_and_receipt_rolls_back_every_row(self):
        """A database error after all writes cannot leave partial revision/receipt."""
        from unittest.mock import patch
        document,_,_,_=self.create();req=self.request(document,'COMMIT',0);a=self.store.admit(req)
        original=self.store.settle
        def fail_after_writes(c,*args):
            original(c,*args)
            c.execute('SELECT 1/0')
        with patch.object(self.store,'settle',fail_after_writes):
            with self.assertRaises(KnownRollback):self.finish(req,a)
        self.assertEqual(self.store.read({'documentId':document,'revision':None})['headRevision'],0)
        self.assertEqual(self.store.receipt(req)['status'],'ABSENT')
        self.assertEqual(self.finish(req,a)[0]['status'],'COMMITTED')

    def test_forced_fk_rollback_keeps_previous_head(self):
        """Database rejection atomically rolls back appended artifact and head update."""
        document,_,_,_=self.create();req=self.request(document,'COMMIT',0);a=self.store.admit(req)
        value=self.store.read({'documentId':document,'revision':0})['artifact']
        with self.assertRaises(KnownRollback):self.finish(req,a,value)
        self.assertEqual(self.store.read({'documentId':document,'revision':None})['headRevision'],0)
        self.assertEqual(self.store.receipt(req)['status'],'ABSENT')


if __name__=='__main__':unittest.main()
