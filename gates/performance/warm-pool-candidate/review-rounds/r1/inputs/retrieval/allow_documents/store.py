"""Scoped append-only PostgreSQL document store behind the mandatory SQL proxy."""
from contextlib import contextmanager
import hashlib
import uuid
from psycopg.rows import dict_row
import psycopg
from allow_retrieval.sql_connections import connect
from . import identity, wire, identifiers, context_lease

RESERVATION = 4194304
MAX_BYTES = 268435456


class UncertainCommit(RuntimeError):
    """A final SQL transaction may have committed; recover exact-key receipt."""


class KnownRollback(RuntimeError):
    """PostgreSQL explicitly rejected a transaction before commit."""


class Store:
    """One trusted owner/workspace/launch, always derived from private metadata."""

    def __init__(self, scope=None):
        """Load durable authority; explicit scope is an internal test seam only."""
        self.scope = scope if scope is not None else identity.load()
        self.principal = self.scope['principalId']
        self.workspace = self.scope['workspaceId']
        self.launch = self.scope['logicalLaunchId']

    @contextmanager
    def transaction(self):
        """Set fixed transaction-local scope keys on canonical proxy connection."""
        with connect(client='allow-app', row_factory=dict_row) as connection:
            connection.execute("SELECT set_config('allow.tenant',%s,true)", (self.principal,))
            connection.execute("SELECT set_config('allow.project',%s,true)", (self.workspace,))
            connection.execute("SELECT set_config('allow.purpose',%s,true)", ('document',))
            yield connection

    def initialize(self, policy):
        """Register private workspace and resumed logical scope without resetting policy."""
        self.policy_value(policy)
        with self.transaction() as c:
            c.execute('INSERT INTO documents.workspace(principal_id,workspace_id,policy_version) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING', (self.principal,self.workspace,policy))
            current = self.lock(c, 'CREATE')
            if current['policy_version'] != policy:
                return {'status':'POLICY_MISMATCH','policyVersion':current['policy_version']}
            c.execute('INSERT INTO documents.logical_launch(principal_id,workspace_id,launch_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING', (self.principal,self.workspace,self.launch))
        return {'status':'READY','policyVersion':policy}

    @staticmethod
    def policy_value(value):
        """Validate version identity without exposing parser/client authority."""
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            raise ValueError('invalid_policy')

    def lock(self, c, document):
        """Acquire workspace before document to serialize quota, policy and CAS."""
        workspace = c.execute('SELECT * FROM documents.workspace FOR UPDATE').fetchone()
        if workspace is None:
            raise ValueError('workspace_not_initialized')
        if document != 'CREATE' and c.execute('SELECT 1 FROM documents.document WHERE document_id=%s FOR UPDATE', (document,)).fetchone() is None:
            raise ValueError('document_not_found')
        return workspace

    def _receipt(self, c, req):
        """Read one authorized scoped receipt; exact bytes outrank digests."""
        doc,key,method,route,body = req
        row = c.execute('SELECT * FROM documents.receipt WHERE launch_id=%s AND namespace=%s AND request_key=%s', (self.launch,doc,key)).fetchone()
        if row is None:
            return None
        if row['method'] != method or row['route'] != route or bytes(row['request_bytes']) != body:
            return {'status':'IDEMPOTENCY_CONFLICT'}
        return {'status':'REPLAY','responseBase64':wire.b64(bytes(row['outcome']))}

    def receipt(self, args):
        """Authorize existence then recover outcome before validation or quota."""
        req = wire.request(args)
        with self.transaction() as c:
            if req[0] != 'CREATE' and c.execute('SELECT 1 FROM documents.document WHERE document_id=%s', (req[0],)).fetchone() is None:
                return {'status':'NOT_FOUND'}
            return self._receipt(c,req) or {'status':'ABSENT'}

    def admit(self, args):
        """Reserve bounded quota or take over only a provably dead process owner."""
        req = wire.request(args)
        pid,start = args['ownerPid'],args['ownerStartTicks']
        if not isinstance(start,str) or not identity.alive(pid,start):
            raise ValueError('owner_not_alive')
        with self.transaction() as c:
            workspace = self.lock(c,req[0])
            replay = self._receipt(c,req)
            if replay is not None:
                return replay
            old = c.execute('SELECT * FROM documents.admission WHERE launch_id=%s AND namespace=%s AND request_key=%s FOR UPDATE', (self.launch,req[0],req[1])).fetchone()
            if old is not None:
                return self.takeover(c,old,args,req,workspace)
            return self.reserve(c,args,req,workspace)

    def takeover(self, c, old, args, req, workspace):
        """Keep existing reservation, fence old frames and reject live ownership."""
        if old['method'] != req[2] or old['route'] != req[3] or bytes(old['request_bytes']) != req[4] or old['operation'] != args['operation']:
            return {'status':'IDEMPOTENCY_CONFLICT'}
        if old['state'] == 'TERMINAL':
            raise ValueError('terminal_without_receipt')
        if identity.alive(old['owner_pid'],old['owner_start']):
            return {'status':'IN_PROGRESS'}
        nonce = str(uuid.uuid4())
        c.execute('UPDATE documents.admission SET owner_pid=%s,owner_start=%s,owner_nonce=%s WHERE launch_id=%s AND namespace=%s AND request_key=%s', (args['ownerPid'],args['ownerStartTicks'],nonce,self.launch,req[0],req[1]))
        return {'status':'ADMITTED','nonce':nonce,'documentId':old['document_id'],'policyVersion':workspace['policy_version']}

    def recover(self, args):
        """Rotate a live supervisor's nonce only with reaped/no-start work proof."""
        req = wire.request(args)
        with self.transaction() as c:
            workspace = self.lock(c,req[0])
            replay = self._receipt(c,req)
            if replay is not None:
                return replay
            row = c.execute('SELECT * FROM documents.admission WHERE launch_id=%s AND namespace=%s AND request_key=%s FOR UPDATE',(self.launch,req[0],req[1])).fetchone()
            if row is None or row['state'] != 'VALIDATING' or row['owner_nonce'] != args['nonce']:
                return {'status':'STALE_OWNER'}
            if row['owner_pid'] != args['ownerPid'] or row['owner_start'] != args['ownerStartTicks'] or not identity.alive(args['ownerPid'],args['ownerStartTicks']):
                raise ValueError('recovery_not_owner')
            if row['method'] != req[2] or row['route'] != req[3] or bytes(row['request_bytes']) != req[4]:
                return {'status':'IDEMPOTENCY_CONFLICT'}
            worker = args['workerPid']
            if worker is None:
                if args['workerStartTicks'] is not None or args['noWorkerStarted'] is not True:
                    raise ValueError('missing_reap_proof')
            elif args['noWorkerStarted'] is not False:
                raise ValueError('missing_reap_proof')
            elif args['workerStartTicks'] is None:
                if identity.process_start(worker) is not None:
                    raise ValueError('worker_still_alive')
            elif not isinstance(args['workerStartTicks'],str) or identity.alive(worker,args['workerStartTicks']):
                raise ValueError('worker_still_alive')
            nonce = str(uuid.uuid4())
            c.execute('UPDATE documents.admission SET owner_nonce=%s WHERE launch_id=%s AND namespace=%s AND request_key=%s',(nonce,self.launch,req[0],req[1]))
            return {'status':'ADMITTED','nonce':nonce,'documentId':row['document_id'],'policyVersion':workspace['policy_version']}

    def reserve(self, c, args, req, workspace):
        """Reserve document slot for pending CREATE and revision0 atomically."""
        operation = args['operation']
        if operation not in ('CREATE','COMMIT','HISTORY_COPY') or (operation == 'CREATE') != (req[0] == 'CREATE'):
            raise ValueError('invalid_operation')
        suffix = {'CREATE':'','COMMIT':'/commit','HISTORY_COPY':'/history-copy'}[operation]
        base_route = '/api/v1/documents' if operation == 'CREATE' else '/api/v1/documents/' + req[0]
        allowed_routes = {base_route + suffix}
        if operation != 'CREATE':
            allowed_routes.add('/api/v1/documents/' + req[0].replace(':','%3A') + suffix)
        if req[3] not in allowed_routes:
            raise ValueError('operation_route_mismatch')
        expected = args['expectedRevision']
        if operation != 'CREATE' and (type(expected) is not int or not 0 <= expected < 9007199254740991):
            raise ValueError('invalid_revision')
        body = wire.decode(req[4],wire.MAX_REQUEST)
        if not isinstance(body,dict) or body.get('idempotencyKey') != req[1]:
            raise ValueError('key_body_mismatch')
        required = {'idempotencyKey','title'} if operation == 'CREATE' else {'idempotencyKey','expectedRevision','targetRevision','direction'} if operation == 'HISTORY_COPY' else {'idempotencyKey','expectedRevision','candidate'}
        wire.fields(body,required)
        if operation != 'CREATE' and body['expectedRevision'] != expected:
            raise ValueError('base_body_mismatch')
        create = int(operation == 'CREATE')
        full = workspace['document_count'] + workspace['reserved_documents'] + create > 64
        full |= workspace['revision_count'] + workspace['reserved_revisions'] + 1 > 4096
        full |= workspace['receipt_count'] + workspace['reserved_receipts'] + 1 > 16384
        full |= workspace['accounted_bytes'] + workspace['reserved_bytes'] + RESERVATION > MAX_BYTES
        if full:
            return {'status':'CAPACITY_PRE_ADMISSION'}
        nonce,document = str(uuid.uuid4()), wire.fresh_id() if create else req[0]
        values = (self.principal,self.workspace,self.launch,req[0],req[1],req[2],req[3],req[4],operation,document,expected,args['ownerPid'],args['ownerStartTicks'],nonce,RESERVATION,create)
        c.execute("INSERT INTO documents.admission(principal_id,workspace_id,launch_id,namespace,request_key,method,route,request_bytes,operation,document_id,expected_revision,owner_pid,owner_start,owner_nonce,state,reservation_bytes,reservation_documents,reservation_revisions) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'VALIDATING',%s,%s,1)", values)
        c.execute('UPDATE documents.workspace SET reserved_bytes=reserved_bytes+%s,reserved_receipts=reserved_receipts+1,reserved_revisions=reserved_revisions+1,reserved_documents=reserved_documents+%s', (RESERVATION,create))
        return {'status':'ADMITTED','nonce':nonce,'documentId':document,'policyVersion':workspace['policy_version']}

    def finalize(self, args):
        """Commit an immutable outcome or expose uncertainty without assuming rollback."""
        req = wire.request(args)
        existing = self.receipt(args)
        if existing['status'] != 'ABSENT':
            return existing
        outcome = wire.unb64(args['outcomeBase64'],wire.MAX_RESPONSE)
        wire.decode(outcome,wire.MAX_RESPONSE)
        if args['result'] not in ('COMMITTED','REJECTED'):
            raise ValueError('invalid_result')
        artifact = args['artifact']
        encoded = wire.artifact(artifact,args['policyVersion']) if artifact is not None else None
        try:
            with self.transaction() as c:
                result = self.finish(c,args,req,outcome,encoded)
            return result
        except (ValueError, TypeError):
            raise
        except psycopg.Error as error:
            if self.known_rollback(error.sqlstate):
                raise KnownRollback('KNOWN_ROLLBACK') from error
            raise UncertainCommit('UNKNOWN_COMMIT_OUTCOME') from error
        except Exception as error:
            raise UncertainCommit('UNKNOWN_COMMIT_OUTCOME') from error

    @staticmethod
    def known_rollback(sqlstate):
        """Whitelist explicit transaction rejection; unknown completion is never rollback."""
        if not isinstance(sqlstate,str) or len(sqlstate) != 5:
            return False
        return sqlstate[:2] in ('22','23','25','42') or sqlstate in ('40001','40P01')

    def recover_unstarted(self, args):
        """Recover lost admission reply only from same supervisor's no-start proof."""
        req = wire.request(args)
        if args['noWorkerStarted'] is not True or not identity.alive(args['ownerPid'],args['ownerStartTicks']):
            raise ValueError('invalid_unstarted_proof')
        with self.transaction() as c:
            workspace = self.lock(c,req[0])
            replay = self._receipt(c,req)
            if replay is not None:
                return replay
            row = c.execute('SELECT * FROM documents.admission WHERE launch_id=%s AND namespace=%s AND request_key=%s FOR UPDATE',(self.launch,req[0],req[1])).fetchone()
            if row is None:
                return {'status':'ABSENT'}
            if row['method'] != req[2] or row['route'] != req[3] or bytes(row['request_bytes']) != req[4]:
                return {'status':'IDEMPOTENCY_CONFLICT'}
            if row['state'] != 'VALIDATING' or row['owner_pid'] != args['ownerPid'] or row['owner_start'] != args['ownerStartTicks']:
                return {'status':'STALE_OWNER'}
            nonce = str(uuid.uuid4())
            c.execute('UPDATE documents.admission SET owner_nonce=%s WHERE launch_id=%s AND namespace=%s AND request_key=%s',(nonce,self.launch,req[0],req[1]))
            return {'status':'ADMITTED','nonce':nonce,'documentId':row['document_id'],'policyVersion':workspace['policy_version']}

    def finish(self, c, args, req, outcome, encoded):
        """Repeat receipt first, then policy and owner fences under ordered locks."""
        workspace = self.lock(c,req[0])
        replay = self._receipt(c,req)
        if replay is not None:
            return replay
        row = c.execute('SELECT * FROM documents.admission WHERE launch_id=%s AND namespace=%s AND request_key=%s FOR UPDATE', (self.launch,req[0],req[1])).fetchone()
        if row is None or row['state'] != 'VALIDATING' or row['owner_nonce'] != args['nonce']:
            return {'status':'STALE_OWNER'}
        if row['method'] != req[2] or row['route'] != req[3] or bytes(row['request_bytes']) != req[4]:
            return {'status':'IDEMPOTENCY_CONFLICT'}
        if workspace['policy_version'] != args['policyVersion']:
            return {'status':'REVALIDATE','policyVersion':workspace['policy_version']}
        if row['expected_revision'] != args['expectedRevision']:
            raise ValueError('base_substitution')
        return self.persist(c,args,req,outcome,encoded,row)

    def persist(self, c, args, req, outcome, encoded, row):
        """Atomically append accepted artifact or deterministic rejected receipt."""
        success = args['result'] == 'COMMITTED'
        create = row['operation'] == 'CREATE'
        head = -1 if create else c.execute('SELECT head_revision FROM documents.document WHERE document_id=%s', (row['document_id'],)).fetchone()['head_revision']
        if not success and not create:
            reported = wire.decode(outcome,wire.MAX_RESPONSE).get('data',{}).get('acceptedRevision')
            if type(reported) is not int or reported != head:
                return {'status':'STALE_REVISION','acceptedRevision':head}
        if success and not create and head != args['expectedRevision']:
            return {'status':'STALE_REVISION','acceptedRevision':head}
        if success and head >= 9007199254740991:
            return {'status':'REVISION_EXHAUSTED'}
        if success and encoded is None:
            raise ValueError('missing_artifact')
        revision = head + 1 if success else None
        if success:
            identifiers.check(c,row,wire.decode(req[4],wire.MAX_REQUEST),args['artifact'],wire.decode(outcome,wire.MAX_RESPONSE))
            self.append(c,args,row,revision,encoded)
        charge = len(req[4])*2 + len(outcome) + (len(encoded[0]) if success else 0) + 8192
        if charge > RESERVATION:
            raise ValueError('reservation_exceeded')
        vals = (self.principal,self.workspace,self.launch,req[0],req[1],req[2],req[3],req[4],hashlib.sha256(req[4]).hexdigest(),outcome,args['result'],row['document_id'] if success else None,revision)
        c.execute('INSERT INTO documents.receipt(principal_id,workspace_id,launch_id,namespace,request_key,method,route,request_bytes,request_hash,outcome,outcome_code,result_document_id,result_revision) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',vals)
        self.settle(c,req,row,success,create,charge)
        return {'status':'COMMITTED' if success else 'REJECTED','responseBase64':wire.b64(outcome),'documentId':row['document_id'],'revision':revision}

    def append(self, c, args, row, revision, encoded):
        """Write fresh immutable artifact/revision and same-document provenance."""
        artifact = args['artifact']
        document = row['document_id']
        target,direction = args['targetRevision'],args['direction']
        if row['operation'] == 'HISTORY_COPY':
            authored = wire.decode(bytes(row['request_bytes']),wire.MAX_REQUEST)
            if authored['targetRevision'] != target or authored['direction'] != direction:
                raise ValueError('history_body_mismatch')
            if type(target) is not int or target < 0 or direction not in ('UNDO','REDO'):
                raise ValueError('invalid_history_target')
            old = self._read(c,document,target)
            for field in ('source','module','occurrences','trivia'):
                if old['artifact'][field] != artifact[field]:
                    raise ValueError('history_content_substitution')
        elif target is not None or direction is not None:
            raise ValueError('unexpected_history')
        if row['operation'] == 'CREATE':
            if artifact['source'] != '' or artifact['analysisDescriptors'] or artifact['occurrences'] or artifact['trivia'] or artifact['mode'] != 'BLOCK_SUPPORTED':
                raise ValueError('create_not_empty')
            if artifact['module'] is None or any(value for key,value in artifact['module'].items() if key != 'version'):
                raise ValueError('create_not_empty')
            body = wire.decode(bytes(row['request_bytes']),wire.MAX_REQUEST)
            title = body.get('title')
            if not isinstance(title,str) or not 1 <= len(title) <= 128:
                raise ValueError('invalid_title')
            c.execute('INSERT INTO documents.document(principal_id,workspace_id,document_id,title,head_revision) VALUES(%s,%s,%s,%s,0)',(self.principal,self.workspace,document,title))
        c.execute('INSERT INTO documents.artifact(principal_id,workspace_id,document_id,artifact_id,content,source_hash,policy_version) VALUES(%s,%s,%s,%s,%s,%s,%s)',(self.principal,self.workspace,document,artifact['artifactId'],encoded[0],encoded[1],args['policyVersion']))
        c.execute('INSERT INTO documents.revision(principal_id,workspace_id,document_id,revision,artifact_id,target_revision,direction) VALUES(%s,%s,%s,%s,%s,%s,%s)',(self.principal,self.workspace,document,revision,artifact['artifactId'],target,direction))
        c.execute('UPDATE documents.document SET head_revision=%s WHERE document_id=%s',(revision,document))

    def settle(self, c, req, row, success, create, charge):
        """Settle every reservation once while retaining immutable history/receipt."""
        c.execute("UPDATE documents.admission SET state='TERMINAL',reservation_bytes=0,reservation_documents=0,reservation_revisions=0 WHERE launch_id=%s AND namespace=%s AND request_key=%s",(self.launch,req[0],req[1]))
        values = (int(success and create),int(success),charge,row['reservation_bytes'],row['reservation_documents'],row['reservation_revisions'])
        c.execute('UPDATE documents.workspace SET document_count=document_count+%s,revision_count=revision_count+%s,receipt_count=receipt_count+1,accounted_bytes=accounted_bytes+%s,reserved_bytes=reserved_bytes-%s,reserved_documents=reserved_documents-%s,reserved_revisions=reserved_revisions-%s,reserved_receipts=reserved_receipts-1',values)

    def _read(self, c, document, revision):
        """Return artifact with external immutable revision/provenance envelope."""
        head = c.execute('SELECT head_revision FROM documents.document WHERE document_id=%s',(document,)).fetchone()
        if head is None:
            raise ValueError('document_not_found')
        selected = head['head_revision'] if revision is None else revision
        row = c.execute('SELECT r.revision,r.target_revision,r.direction,a.content FROM documents.revision r JOIN documents.artifact a USING(principal_id,workspace_id,document_id,artifact_id) WHERE r.document_id=%s AND r.revision=%s',(document,selected)).fetchone()
        if row is None:
            raise ValueError('revision_not_found')
        return {'documentId':document,'headRevision':head['head_revision'],'requestedRevision':selected,'artifact':wire.decode(bytes(row['content']),wire.MAX_RESPONSE),'provenance':{'targetRevision':row['target_revision'],'direction':row['direction']}}

    def read(self, args):
        """Read an authorized exact historical revision or current head."""
        wire.identifier(args['documentId'])
        revision = args['revision']
        if revision is not None and (type(revision) is not int or revision < 0):
            raise ValueError('invalid_revision')
        with self.transaction() as c:
            return self._read(c,args['documentId'],revision)

    @contextmanager
    def _validation_snapshot(self, nonce):
        """Yield a private read-only snapshot before any scoped data is queried.

        Transaction mode precedes all SELECTs, including scope configuration.
        The proxy certifies owned backend cleanup before a result escapes.
        """
        with context_lease.connection(nonce, dict_row) as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            connection.execute('SET LOCAL statement_timeout = 1500')
            connection.execute('SET LOCAL lock_timeout = 250')
            connection.execute('SET LOCAL idle_in_transaction_session_timeout = 1000')
            connection.execute("SELECT set_config('allow.tenant',%s,true)", (self.principal,))
            connection.execute("SELECT set_config('allow.project',%s,true)", (self.workspace,))
            connection.execute("SELECT set_config('allow.purpose',%s,true)", ('document',))
            yield connection

    @staticmethod
    def _context_arguments(args):
        """Return bounded document, explicit revision and requested identity set.

        Reject malformed or noncanonical private arguments before database I/O.
        The browser cannot supply scope, a head selector or an ownership map.
        """
        wire.fields(args, {'documentId','revision','ids'})
        document = wire.identifier(args['documentId'])
        revision, ids = args['revision'], args['ids']
        if type(revision) is not int or not 0 <= revision <= 9007199254740991:
            raise ValueError('invalid_revision')
        if not isinstance(ids,list) or len(ids) > 4096 or len(wire.encode(args)) > wire.MAX_REQUEST:
            raise ValueError('ids_limit')
        for identifier in ids:
            wire.identifier(identifier)
        if ids != sorted(set(ids)):
            raise ValueError('noncanonical_id_set')
        return document, revision, set(ids)

    def _history_inventory(self, connection, document, wanted):
        """Resolve requested definition kinds from the entire supplied snapshot.

        Empty requests avoid a scan; otherwise every artifact is decoded and
        checked so a later kind collision or malformed artifact cannot be hidden.
        """
        result = {}
        if wanted:
            rows = connection.execute('SELECT content FROM documents.artifact WHERE document_id=%s',(document,))
            for row in rows:
                artifact = wire.decode(bytes(row['content']),wire.MAX_RESPONSE)
                wire.fields(artifact, wire.ARTIFACT_FIELDS)
                self.collect_ids(artifact['module'],wanted,result)
        return result

    def validation_context(self, args, request_id=None):
        """Read one exact base and its requested history inventory atomically.

        Missing scoped data is a request failure. Corrupt stored content or read
        transport failures are unavailable, never an uncertain mutation outcome.
        Return only after the proxy confirms successful owned backend cleanup.
        The CLI supplies its private nonce; direct internal callers mint one.
        """
        document, revision, wanted = self._context_arguments(args)
        nonce = context_lease.canonical_nonce(request_id if request_id is not None else str(uuid.uuid4()))
        try:
            with self._validation_snapshot(nonce) as connection:
                snapshot = self._read(connection,document,revision)
                wire.fields(snapshot['artifact'], wire.ARTIFACT_FIELDS)
                result = {'documentId':document,'baseRevision':revision,
                          'headObserved':snapshot['headRevision'],'artifact':snapshot['artifact'],
                          'ownedIdInventory':self._history_inventory(connection,document,wanted)}
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as failure:
            if isinstance(failure,ValueError) and str(failure) in {'document_not_found','revision_not_found'}:
                raise
            raise RuntimeError('validation_context_unavailable') from failure
        except (KnownRollback, UncertainCommit) as failure:
            raise RuntimeError('validation_context_unavailable') from failure
        return result

    def listing(self):
        """List only bounded metadata for the local authorized workspace."""
        with self.transaction() as c:
            return {'documents':c.execute('SELECT document_id AS "documentId",title,head_revision AS "headRevision" FROM documents.document ORDER BY document_id LIMIT 64').fetchall()}

    def owned_ids(self, args):
        """Resolve only requested IDs from immutable scoped document history."""
        document, ids = args['documentId'],args['ids']
        wire.identifier(document)
        if not isinstance(ids,list) or len(ids) > 4096 or len(wire.encode(args)) > 262144:
            raise ValueError('ids_limit')
        for identifier in ids:
            wire.identifier(identifier)
        wanted,result = set(ids),{}
        with self.transaction() as c:
            if c.execute('SELECT 1 FROM documents.document WHERE document_id=%s',(document,)).fetchone() is None:
                raise ValueError('document_not_found')
            rows = c.execute('SELECT content FROM documents.artifact WHERE document_id=%s',(document,))
            for row in rows:
                module = wire.decode(bytes(row['content']),wire.MAX_RESPONSE)['module']
                self.collect_ids(module,wanted,result)
        return {'ids':result}

    @staticmethod
    def collect_ids(module, wanted, result):
        """Extract declared ID kinds, rejecting cross-history kind instability."""
        pending = [module]
        while pending:
            value = pending.pop()
            if isinstance(value,dict):
                ident = value.get('id')
                if ident in wanted:
                    tag = value.get('tag')
                    kind = tag if tag in ('signature','field','predicate','fact','assertion') else 'command' if tag in ('run','check') else 'binder' if tag == 'parameter' or tag is None and 'signatureId' in value else 'expression'
                    if ident in result and result[ident] != kind:
                        raise ValueError('historical_id_kind_collision')
                    result[ident] = kind
                pending.extend(value.values())
            elif isinstance(value,list):
                pending.extend(value)

    def policy(self, expected, replacement):
        """Install policy under same workspace fence used by finalization."""
        self.policy_value(replacement)
        with self.transaction() as c:
            workspace = self.lock(c,'CREATE')
            if workspace['policy_version'] != expected:
                return {'status':'POLICY_MISMATCH','policyVersion':workspace['policy_version']}
            c.execute('UPDATE documents.workspace SET policy_version=%s',(replacement,))
        return {'status':'READY','policyVersion':replacement}
