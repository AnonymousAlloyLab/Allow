"""Closed, bounded private Java-to-Python document operation bridge."""
import os
import sys
import uuid
from . import identity, wire
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
    'policy': {'expectedPolicyVersion','policyVersion'}
}


def dispatch(frame):
    """Validate closed internal frame before loading durable server-owned scope."""
    wire.fields(frame, {'protocol','requestId','operation','args'})
    if type(frame['protocol']) is not int or frame['protocol'] != 1:
        raise ValueError('invalid_protocol')
    if str(uuid.UUID(frame['requestId'])) != frame['requestId']:
        raise ValueError('invalid_nonce')
    operation,args = frame['operation'],frame['args']
    if operation not in SHAPES:
        raise ValueError('unsupported_operation')
    wire.fields(args, SHAPES[operation])
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
                  'validationContext':lambda:store.validation_context(args),
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
        raw = wire.encode({'protocol':1,'requestId':result['requestId'],'status':'UNAVAILABLE','data':{'reason':'bridge_output_limit'}})
    sys.stdout.buffer.write(raw + b'\n')


if __name__ == '__main__':
    main()
