"""Finite validation-context regressions using isolated scopes and proxy-only SQL.

The stored-artifact fixtures exercise persistence projection, not Alloy semantics.
No fixture reads the production scope or prints credentials/source from that scope.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import copy
import io
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import MagicMock, patch
import uuid

import psycopg
from allow_documents import cli, store as store_module, wire, context_lease
from allow_documents.store import Store, KnownRollback, UncertainCommit
import test_documents as fixtures


class ValidationContextWireTests(unittest.TestCase):
    """Exercise private shape, bounded framing and failure classification."""

    def setUp(self):
        """Construct a test-only authority value without opening a connection."""
        self.store = Store(fixtures.scope())
        self.document = wire.fresh_id()

    def args(self, **changes):
        """Build the new closed argument shape with an explicit revision."""
        value = {'documentId':self.document,'revision':0,'ids':[]}
        value.update(changes)
        return value

    def frame(self, args=None):
        """Create a nonce-bound private request using only synthetic fixture data."""
        return {'protocol':1,'requestId':str(uuid.uuid4()),'operation':'validationContext',
                'args':self.args() if args is None else args}

    def invoke(self, raw):
        """Execute the actual CLI codec against byte streams and return its frame."""
        output = io.BytesIO()
        with patch.object(cli.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(raw))):
            with patch.object(cli.sys,'stdout',SimpleNamespace(buffer=output)):
                cli.main()
        encoded = output.getvalue()
        self.assertTrue(encoded.endswith(b'\n'))
        self.assertEqual(encoded.count(b'\n'),1)
        self.assertLessEqual(len(encoded),1572865)
        return wire.decode(encoded,1572865), encoded

    def test_context_arguments_reject_before_connection(self):
        """VC01/13: invalid identity/revision/set/shape never reaches SQL."""
        first, second = sorted([wire.fresh_id(),wire.fresh_id()])
        bad = [self.args(revision=x) for x in (None,True,-1,9007199254740992,'0',0.5)]
        bad += [self.args(ids=x) for x in (None,{},[first,first],[second,first],[2],['draft:'+str(uuid.uuid4())])]
        bad += [self.args(documentId='CREATE'),self.args(extra=True),self.args(ids=[first]*4097),
                self.args(ids=['x'*262144]),{'documentId':self.document,'ids':[]}]
        with patch.object(store_module,'connect') as connect:
            for args in bad:
                with self.subTest(args_kind=tuple(args)):
                    with self.assertRaises((ValueError,TypeError,KeyError)):
                        self.store.validation_context(args)
            connect.assert_not_called()

    def test_context_accepts_safe_integer_and_id_count_boundaries(self):
        """VC13: the private safe-integer and4096-identity boundaries are inclusive."""
        ids = sorted(wire.fresh_id() for _ in range(4096))
        document, revision, wanted = self.store._context_arguments(self.args(ids=ids,revision=9007199254740991))
        self.assertEqual((document,revision),(self.document,9007199254740991))
        self.assertEqual(wanted,set(ids))

    def test_closed_cli_shape_and_strict_json(self):
        """VC01: malformed framing and extra private fields fail before Store."""
        frame = self.frame()
        raws = [b'{"protocol":1,"protocol":1}',b'\xff',b'NaN',b'9007199254740992',
                wire.encode(dict(frame,protocol=True)),wire.encode(dict(frame,extra=True)),
                wire.encode(dict(frame,requestId='not-a-uuid')),
                wire.encode(dict(frame,requestId='11111111-1111-4111-8111-AAAAAAAAAAAA')),
                wire.encode(frame)+b'\n'+wire.encode(frame),
                wire.encode(dict(frame,operation='validationContext2')),
                wire.encode(dict(frame,args=self.args(principalId='forged')))]
        with patch.object(cli,'Store') as store:
            for raw in raws:
                result, _ = self.invoke(raw)
                self.assertEqual(result['status'],'ERROR')
            store.assert_not_called()

    def test_cli_dispatch_has_one_context_call(self):
        """VC03: empty-ID requests dispatch the mandatory context operation once."""
        frame = self.frame()
        fake = MagicMock()
        fake.validation_context.return_value = {'marker':'context'}
        with patch.object(cli,'Store',return_value=fake):
            result = cli.dispatch(frame)
        self.assertEqual(result,{'marker':'context'})
        fake.validation_context.assert_called_once_with(frame['args'],frame['requestId'])
        fake.read.assert_not_called()
        fake.owned_ids.assert_not_called()

    def test_full_cli_output_boundary_and_nonce(self):
        """VC12: size the whole transport envelope, including combined data fields."""
        frame = self.frame()
        data = {'artifact':{'source':''},'ownedIdInventory':{'fixture':'expression'}}
        prefix = wire.encode({'protocol':1,'requestId':frame['requestId'],'status':'OK','data':data})
        for extra, status in ((0,'OK'),(1,'UNAVAILABLE')):
            value = copy.deepcopy(data)
            value['artifact']['source'] = 'x'*(1572864-len(prefix)+extra)
            with patch.object(cli,'dispatch',return_value=value):
                result, encoded = self.invoke(wire.encode(frame))
            self.assertEqual(result['requestId'],frame['requestId'])
            self.assertEqual(result['status'],status)
            if extra == 0:
                self.assertEqual(len(encoded),1572865)
            else:
                self.assertNotIn('artifact',result['data'])

    def test_read_failure_never_invents_mutation_uncertainty(self):
        """VC14: corrupt/dead read paths cannot produce mutation outcome claims."""
        failures = [ValueError('input_limit'),KeyError('module'),psycopg.OperationalError('fixture'),
                    UncertainCommit('fixture'),KnownRollback('fixture')]
        @contextmanager
        def connection(nonce):
            """Provide a read seam without opening a database connection."""
            yield object()
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(self.store,'_validation_snapshot',connection):
                    with patch.object(self.store,'_read',side_effect=failure):
                        with patch.object(cli,'Store',return_value=self.store):
                            result, _ = self.invoke(wire.encode(self.frame()))
                self.assertEqual(result['status'],'UNAVAILABLE')
                self.assertNotIn('artifact',result['data'])

    def test_transaction_exit_failure_discards_complete_context(self):
        """VC14/15: a result formed before failed transaction exit is not published."""
        @contextmanager
        def fail_exit(nonce):
            """Fail after producing data to test the outer transaction boundary."""
            yield object()
            raise psycopg.OperationalError('fixture exit failure')
        snapshot = {'headRevision':0,'artifact':fixtures.artifact()}
        with patch.object(self.store,'_validation_snapshot',fail_exit):
            with patch.object(self.store,'_read',return_value=snapshot):
                with patch.object(cli,'Store',return_value=self.store):
                    result, _ = self.invoke(wire.encode(self.frame()))
        self.assertEqual(result['status'],'UNAVAILABLE')
        self.assertNotIn('artifact',result['data'])

    def test_legacy_mutation_uncertainty_remains(self):
        """VC21: the new path does not relabel existing mutator uncertainty."""
        frame = self.frame()
        frame['operation'] = 'finalize'
        for failure, status in ((UncertainCommit('fixture'),'UNKNOWN_COMMIT_OUTCOME'),
                                (KnownRollback('fixture'),'KNOWN_ROLLBACK')):
            with patch.object(cli,'dispatch',side_effect=failure):
                result, _ = self.invoke(wire.encode(frame))
            self.assertEqual(result['status'],status)


class ValidationContextSQLTests(unittest.TestCase):
    """Run real database reads and races in fresh private fixture workspaces."""
    request = fixtures.DocumentSQLTests.request
    finish = fixtures.DocumentSQLTests.finish
    create = fixtures.DocumentSQLTests.create
    invoke = ValidationContextWireTests.invoke

    def setUp(self):
        """Create one isolated workspace through the same mandatory SQL proxy."""
        self.store = Store(fixtures.scope())
        self.store.initialize('document-v1')
        self.document, _, _, _ = self.create()

    def args(self, revision=0, ids=(), document=None):
        """Return canonical arguments without exposing test scope on the wire."""
        return {'documentId':document or self.document,'revision':revision,'ids':sorted(set(ids))}

    def append(self, identifiers=(), source='sig Fixture {}\r\n'):
        """Append a trusted store fixture through normal admission/finalization."""
        writer = Store(self.store.scope)
        head = writer.read({'documentId':self.document,'revision':None})['headRevision']
        req = self.request(self.document,'COMMIT',head)
        admission = self.store.admit(req)
        value = fixtures.artifact(source)
        value['module']['signatures'] = [{'tag':'signature','id':item,'name':'Fixture'+str(index),
                                         'multiplicity':'set'} for index,item in enumerate(identifiers)]
        self.assertEqual(self.finish(req,admission,value)[0]['status'],'COMMITTED')
        return value

    def insert_fixture(self, value, raw=None):
        """Insert a bounded deliberate history fixture only in this isolated scope."""
        encoded = wire.encode(value) if raw is None else raw
        with self.store.transaction() as c:
            c.execute('INSERT INTO documents.artifact(principal_id,workspace_id,document_id,artifact_id,content,source_hash,policy_version) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                      (self.store.principal,self.store.workspace,self.document,value['artifactId'],
                       encoded,value['sourceHash'],value['policyVersion']))

    def state(self):
        """Read durable counts/counters for nonmutation assertions through the proxy."""
        with self.store.transaction() as c:
            workspace = c.execute('SELECT * FROM documents.workspace').fetchone()
            counts = c.execute('SELECT (SELECT count(*) FROM documents.artifact) AS artifacts, (SELECT count(*) FROM documents.revision) AS revisions, (SELECT count(*) FROM documents.receipt) AS receipts, (SELECT count(*) FROM documents.admission) AS admissions').fetchone()
            head = c.execute('SELECT head_revision FROM documents.document WHERE document_id=%s',(self.document,)).fetchone()
        return workspace,counts,head

    def test_actual_snapshot_mode_read_only_and_legacy_mode(self):
        """Context setup executes the fixed read-only prelude; writes fail at the gate.

        The v8 channel no longer permits diagnostic SQL inside the context.
        Actual transaction mode follows PostgreSQL's admitted SET semantics;
        these recorded calls and the legacy query do not prove that refinement.
        """
        original = context_lease.connection
        observed = []
        @contextmanager
        def capture(nonce, row_factory):
            """Record fixed statements while forwarding to the actual leased connection."""
            with original(nonce, row_factory) as connection:
                class RecordingConnection:
                    """Keep the real cursor and its execution semantics unchanged."""
                    def execute(self, sql, *args):
                        """Retain SQL templates only; never copy parameters or results."""
                        observed.append(sql)
                        return connection.execute(sql, *args)
                yield RecordingConnection()
        with patch.object(context_lease,'connection',capture):
            self.store.validation_context(self.args())
        self.assertEqual(observed[:4],[
            'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY',
            'SET LOCAL statement_timeout = 1500','SET LOCAL lock_timeout = 250',
            'SET LOCAL idle_in_transaction_session_timeout = 1000'])
        with self.assertRaises((psycopg.Error,RuntimeError)):
            with self.store._validation_snapshot(str(uuid.uuid4())) as c:
                c.execute('UPDATE documents.workspace SET accounted_bytes=accounted_bytes+1')
        with self.store.transaction() as c:
            mode = c.execute("SELECT current_setting('transaction_isolation') AS isolation, current_setting('transaction_read_only') AS readonly").fetchone()
            self.assertEqual(mode,{'isolation':'read committed','readonly':'off'})

    def test_actual_cli_context_and_database_error_envelopes(self):
        """VC14/22: real SQL success/failure uses the closed nonce-bound CLI codec."""
        frame = {'protocol':1,'requestId':str(uuid.uuid4()),'operation':'validationContext',
                 'args':self.args()}
        with patch.object(cli,'Store',return_value=self.store):
            result, _ = self.invoke(wire.encode(frame))
        self.assertEqual((result['status'],result['requestId']),('OK',frame['requestId']))
        self.assertEqual(result['data']['documentId'],self.document)
        def fail_query(connection, document, wanted):
            """Trigger the strict SQL gate after an authorized base was read."""
            connection.execute('SELECT 1/0')
        with patch.object(self.store,'_history_inventory',fail_query):
            with patch.object(cli,'Store',return_value=self.store):
                result, _ = self.invoke(wire.encode(frame))
        self.assertEqual(result['status'],'UNAVAILABLE')
        self.assertNotIn('artifact',result['data'])
        self.assertEqual(self.store.read({'documentId':self.document,'revision':None})['headRevision'],0)

    def test_proxy_connection_failure_has_no_fallback(self):
        """VC14/22: a failed canonical connection cannot route around the proxy."""
        with patch.object(context_lease.sql_connections,'connect',side_effect=psycopg.OperationalError('fixture')) as connect:
            with self.assertRaises((psycopg.OperationalError,RuntimeError)):
                self.store.validation_context(self.args())
        self.assertEqual(connect.call_count,1)

    def test_context_matches_legacy_at_quiescence_and_exact_source(self):
        """VC04/08: current and historical base content agree with existing reads."""
        identifier = wire.fresh_id()
        stored = self.append([identifier])
        for revision in (0,1):
            args = self.args(revision,[identifier,wire.fresh_id()])
            expected = self.store.read({'documentId':self.document,'revision':revision})
            inventory = self.store.owned_ids({'documentId':self.document,'ids':args['ids']})['ids']
            result = self.store.validation_context(args)
            self.assertEqual(set(result),{'documentId','baseRevision','headObserved','artifact','ownedIdInventory'})
            self.assertEqual(result,{'documentId':self.document,'baseRevision':revision,'headObserved':1,
                                     'artifact':expected['artifact'],'ownedIdInventory':inventory})
        self.assertEqual(self.store.validation_context(self.args(1))['artifact']['source'],stored['source'])

    def test_empty_ids_authorize_base_and_skip_scan(self):
        """VC03/05: no requested IDs skips only history, never the mandatory base read."""
        with patch.object(self.store,'collect_ids',side_effect=AssertionError('unexpected scan')):
            result = self.store.validation_context(self.args())
            self.assertEqual(result['ownedIdInventory'],{})
            with self.assertRaises(ValueError):
                self.store.validation_context(self.args(document=wire.fresh_id()))
            with self.assertRaises(ValueError):
                self.store.validation_context(self.args(revision=1))

    def test_missing_and_foreign_context_never_reaches_inventory(self):
        """VC05: absent bases/documents and both RLS dimensions deny before inventory."""
        foreign_scopes = [dict(self.store.scope,principalId=str(uuid.uuid4())),
                          dict(self.store.scope,workspaceId=str(uuid.uuid4()))]
        for scope in foreign_scopes:
            foreign = Store(scope)
            with patch.object(foreign,'_history_inventory',side_effect=AssertionError('inventory disclosed')):
                with self.assertRaises(ValueError):
                    foreign.validation_context(self.args(ids=[wire.fresh_id()]))
        with patch.object(self.store,'_history_inventory',side_effect=AssertionError('inventory disclosed')):
            with self.assertRaises(ValueError):
                self.store.validation_context(self.args(revision=1,ids=[wire.fresh_id()]))

    def test_logical_launch_does_not_partition_document_history(self):
        """VC05: another private launch in the same owner/workspace sees the same base."""
        other = Store(dict(self.store.scope,logicalLaunchId=str(uuid.uuid4())))
        other.initialize('document-v1')
        self.assertEqual(other.validation_context(self.args()),self.store.validation_context(self.args()))

    def test_requested_kind_inventory_and_text_only(self):
        """VC09: all8categories,duplicates and references retain exact legacy projection."""
        kinds = ['signature','field','predicate','fact','assertion','command','binder','expression']
        names = {kind:wire.fresh_id() for kind in kinds}
        value = fixtures.artifact()
        definitions = [{'id':names[kind],'tag':kind} for kind in kinds[:5]]
        definitions += [{'id':names['command'],'tag':'run'},{'id':names['binder'],'signatureId':names['signature']},
                        {'id':names['command'],'tag':'check'},{'id':names['binder'],'tag':'parameter'},
                        {'id':names['expression'],'tag':'signature_ref','targetId':names['signature']}]
        reference_only = wire.fresh_id()
        value['module']['nodes'] = definitions+[{'tag':'unknown','targetId':reference_only}]
        self.insert_fixture(value)
        value['artifactId'] = wire.fresh_id()
        self.insert_fixture(value)
        text = fixtures.artifact()
        text.update(mode='TEXT_ONLY',module=None)
        self.insert_fixture(text)
        wanted = list(names.values())+[reference_only,wire.fresh_id()]
        result = self.store.validation_context(self.args(ids=wanted))['ownedIdInventory']
        self.assertEqual(result,{identifier:kind for kind,identifier in names.items()})
        subset = self.store.validation_context(self.args(ids=[names['binder']]))['ownedIdInventory']
        self.assertEqual(subset,{names['binder']:'binder'})

    def test_complete_history_collision_and_malformed_artifact_fail(self):
        """VC10: a later conflict or malformed row cannot be hidden by an early match."""
        identifier = wire.fresh_id()
        first = fixtures.artifact()
        first['module']['signatures'] = [{'id':identifier,'tag':'signature'}]
        self.insert_fixture(first)
        conflict = fixtures.artifact()
        conflict['module']['fields'] = [{'id':identifier,'tag':'field'}]
        self.insert_fixture(conflict)
        with self.assertRaises(RuntimeError):
            self.store.validation_context(self.args(ids=[identifier]))
        self.assertEqual(self.store.validation_context(self.args(ids=[wire.fresh_id()]))['ownedIdInventory'],{})
        self.insert_fixture(fixtures.artifact(),raw=b'{')
        with self.assertRaises(RuntimeError):
            self.store.validation_context(self.args(ids=[wire.fresh_id()]))

    def test_reads_do_not_mutate_and_full_quota_remains_readable(self):
        """VC18/19: repeated context reads preserve all counters/history at full quota."""
        with self.store.transaction() as c:
            c.execute('UPDATE documents.workspace SET document_count=64,revision_count=4096,receipt_count=16384,accounted_bytes=268435456')
        before = self.state()
        first = self.store.validation_context(self.args())
        self.assertEqual(first,self.store.validation_context(self.args()))
        with self.assertRaises(ValueError):
            self.store.validation_context(self.args(revision=1))
        self.assertEqual(self.state(),before)

    def paused_read(self, position, revision=0):
        """Race a legitimate append against a fixed snapshot at one chosen boundary."""
        captured, release = threading.Event(), threading.Event()
        identifier = wire.fresh_id()
        original_read = self.store._read
        original_snapshot = self.store._validation_snapshot
        def pause():
            """Hold an already established snapshot while another connection commits."""
            captured.set()
            if not release.wait(10):
                raise RuntimeError('fixture barrier timeout')
        def read(connection, document, base):
            """Pause between immutable base read and ownership scan."""
            result = original_read(connection,document,base)
            pause()
            return result
        @contextmanager
        def snapshot(nonce):
            """Pause after scoped snapshot setup and before the document read."""
            with original_snapshot(nonce) as connection:
                pause()
                yield connection
        target, replacement = ('_read',read) if position == 'after_base' else ('_validation_snapshot',snapshot)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch.object(self.store,target,replacement):
                pending = pool.submit(self.store.validation_context,self.args(revision,[identifier]))
                try:
                    self.assertTrue(captured.wait(10),'snapshot barrier not reached')
                    self.append([identifier])
                finally:
                    release.set()
                try:
                    observed = pending.result(timeout=10)
                except ValueError:
                    if revision != 1:
                        raise
                    observed = None
        return observed,self.store.validation_context(self.args(revision,[identifier])),identifier

    def test_commit_after_snapshot_is_excluded_from_head_and_inventory(self):
        """VC06: snapshot setup freezes both head and history before a concurrent append."""
        old, new, identifier = self.paused_read('before_base')
        self.assertEqual((old['headObserved'],old['ownedIdInventory']),(0,{}))
        self.assertEqual((new['headObserved'],new['ownedIdInventory']),(1,{identifier:'signature'}))
        self.assertEqual(old['artifact'],new['artifact'])

    def test_commit_between_base_and_inventory_cannot_mix_snapshots(self):
        """VC07: a commit between the two logical reads cannot introduce future IDs."""
        old, new, identifier = self.paused_read('after_base')
        self.assertEqual((old['headObserved'],old['ownedIdInventory']),(0,{}))
        self.assertEqual(new['ownedIdInventory'],{identifier:'signature'})
        self.assertEqual(old['artifact'],new['artifact'])

    def test_future_base_committed_after_snapshot_requires_new_request(self):
        """VC07: a missing revision cannot become visible inside the older snapshot."""
        old, new, identifier = self.paused_read('before_base',revision=1)
        self.assertIsNone(old)
        self.assertEqual(new['baseRevision'],1)
        self.assertEqual(new['ownedIdInventory'],{identifier:'signature'})

    def test_connection_closes_before_context_is_returned(self):
        """VC15: the actual successful connection is closed at publication."""
        original = context_lease.sql_connections.connect
        opened = []
        def capture(*args, **kwargs):
            """Record the canonical connection handle without logging parameters."""
            connection = original(*args,**kwargs)
            opened.append(connection)
            return connection
        with patch.object(context_lease.sql_connections,'connect',side_effect=capture):
            result = self.store.validation_context(self.args())
        self.assertEqual(result['baseRevision'],0)
        self.assertEqual(len(opened),1)
        self.assertTrue(opened[0].closed)


if __name__ == '__main__':
    unittest.main()
