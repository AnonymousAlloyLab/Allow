"""Closed, bounded private Java-to-Python document operation bridge."""
import os
import sys
import uuid
from . import identity, wire, lifecycle
from .store import Store, UncertainCommit, KnownRollback

REQUEST = {'documentId','key','method','route','bodyBase64'}
SHAPES = {
    'init': {'policyVersion'}, 'list': set(),
    'read': {'documentId','revision'}, 'receipt': REQUEST,
    'ownedIds': {'documentId','ids'},
    'validationContext': {'documentId','revision','ids'},
    'admit': REQUEST | {'ownerPid','ownerStartTicks','operation','expectedRevision'},
    'recoverUnstarted': REQUEST | {'ownerPid','ownerStartTicks','noWorkerStarted'},
    'recover': REQUEST | {'nonce','ownerPid','ownerStartTicks','workerPid','workerStartTicks','noWorkerStarted'},
    'finalize': REQUEST | {'nonce','policyVersion','expectedRevision','artifact','outcomeBase64','result','targetRevision','direction'},
    'policy': {'expectedPolicyVersion','policyVersion'},
    'publicInit': {'policyVersion','expiresAtEpochMillis','incarnation'},
    'publicList': set(), 'publicPurge': {'incarnation'}
}


def dispatch(frame):
    """Validate closed internal frame before loading durable server-owned scope."""
    protocol = frame.get('protocol') if isinstance(frame, dict) else None
    wire.fields(frame, {'protocol','requestId','operation','args'} | ({'scope'} if protocol == 2 else set()))
    if type(protocol) is not int or protocol not in (1, 2):
        raise ValueError('invalid_protocol')
    if str(uuid.UUID(frame['requestId'])) != frame['requestId']:
        raise ValueError('invalid_nonce')
    operation,args = frame['operation'],frame['args']
    if operation not in SHAPES:
        raise ValueError('unsupported_operation')
    wire.fields(args, SHAPES[operation])
    if operation == 'publicList':
        if protocol != 1:
            raise ValueError('lifecycle_protocol')
        return lifecycle.listing()
    if protocol == 2:
        scope = lifecycle.validate_scope(frame['scope'])
        if operation == 'publicInit':
            return lifecycle.initialize(scope, args, Store)
        if operation == 'publicPurge':
            return lifecycle.purge(scope, args)
        if operation in ('init', 'policy'):
            raise ValueError('scoped_policy_operation_forbidden')
        lifecycle.registered(scope)
        store = Store(scope, public=True)
    else:
        if operation in ('publicInit', 'publicPurge'):
            raise ValueError('lifecycle_protocol')
        store = Store()
    if operation in ('admit','recover','recoverUnstarted'):
        if args['ownerPid'] != os.getppid():
            raise ValueError('owner_must_be_supervisor')
        if operation == 'recoverUnstarted':
            return store.recover_unstarted(args)
        return store.admit(args) if operation == 'admit' else store.recover(args)
    operations = {'init':lambda:store.initialize(args['policyVersion']),
                  'list':store.listing, 'read':lambda:store.read(args),
                  'receipt':lambda:store.receipt(args), 'ownedIds':lambda:store.owned_ids(args),
                  'validationContext':lambda:store.validation_context(args,frame['requestId']),
                  'finalize':lambda:store.finalize(args),
                  'policy':lambda:store.policy(args['expectedPolicyVersion'],args['policyVersion'])}
    return operations[operation]()


def main():
    """Emit one bounded nonce-bound envelope without logging private source."""
    result = {'protocol':1,'requestId':None,'status':'ERROR','data':{'reason':'invalid_request'}}
    try:
        frame = wire.decode(sys.stdin.buffer.read(wire.MAX_INPUT + 1))
        if isinstance(frame,dict) and isinstance(frame.get('requestId'),str):
            result['requestId'] = frame['requestId'][:128]
        if isinstance(frame, dict) and type(frame.get('protocol')) is int and frame['protocol'] in (1, 2):
            result['protocol'] = frame['protocol']
        result.update(status='OK',data=dispatch(frame))
    except KnownRollback:
        result.update(status='KNOWN_ROLLBACK',data={'reason':'transaction_rejected'})
    except UncertainCommit:
        result.update(status='UNKNOWN_COMMIT_OUTCOME',data={'reason':'recover_original_receipt'})
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        pass
    except Exception:
        result.update(status='UNAVAILABLE',data={'reason':'document_runtime_unavailable'})
    raw = wire.encode(result)
    if len(raw) > 1572864:
        raw = wire.encode({'protocol':result['protocol'],'requestId':result['requestId'],'status':'UNAVAILABLE','data':{'reason':'bridge_output_limit'}})
    sys.stdout.buffer.write(raw + b'\n')


if __name__ == '__main__':
    main()
