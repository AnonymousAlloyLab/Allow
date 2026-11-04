"""Bounded JSON stdin/stdout bridge; does not load the ML runtime for queries."""
import json
import re
import sys
import uuid
from .database import Repository, Forbidden, NotFound
from .journal import Quarantined
from .ranking import search

MAX_INPUT=8192

def dispatch(request):
    if not isinstance(request,dict) or type(request.get('protocol')) is not int or request.get('protocol')!=1:
        raise ValueError('invalid_protocol')
    nonce=request.get('requestId')
    if not isinstance(nonce,str) or str(uuid.UUID(nonce))!=nonce:
        raise ValueError('invalid_request_id')
    if set(request)-{'protocol','requestId','operation','recordId','limit','modelId'}:
        raise ValueError('unexpected_fields')
    repo=Repository()
    op=request.get('operation')
    if op=='status':
        return repo.status()
    limit=request.get('limit',10)
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=20:
        raise ValueError('invalid_limit')
    if op=='list':
        return {'records':repo.records(limit)}
    if op=='search':
        rid=request.get('recordId')
        if not isinstance(rid,str) or not re.fullmatch('[0-9a-f]{64}',rid):
            raise ValueError('invalid_record_id')
        model=request.get('modelId')
        if model is not None and (not isinstance(model,str) or not 1<=len(model)<=256):
            raise ValueError('invalid_model_id')
        return search(repo,rid,limit,model)
    raise ValueError('unsupported_operation')

def main():
    response={'protocol':1,'requestId':None,'status':'ERROR','data':{'reason':'invalid_request'}}
    try:
        raw=sys.stdin.buffer.read(MAX_INPUT+1)
        if len(raw)>MAX_INPUT or raw.count(b'\n')>1:
            raise ValueError('input_framing')
        request=json.loads(raw)
        if isinstance(request,dict) and isinstance(request.get('requestId'),str):
            response['requestId']=request['requestId'][:128]
        response['data']=dispatch(request);response['status']='OK'
    except Forbidden:
        response.update(status='FORBIDDEN',data={'reason':'purpose_or_lineage_denied'})
    except NotFound:
        response.update(status='NOT_FOUND',data={'reason':'eligible_record_not_found'})
    except Quarantined:
        response.update(status='UNAVAILABLE',data={'reason':'journal_quarantine'})
    except (OSError,ImportError):
        response.update(status='UNAVAILABLE',data={'reason':'local_runtime_unavailable'})
    except ValueError:
        pass
    except Exception:
        response.update(status='UNAVAILABLE',data={'reason':'local_repository_unavailable'})
    sys.stdout.write(json.dumps(response,separators=(',',':'),allow_nan=False)+'\n')

if __name__=='__main__':
    main()
