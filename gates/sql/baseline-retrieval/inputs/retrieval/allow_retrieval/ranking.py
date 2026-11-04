"""Exact filtered retrieval from trusted stored record IDs."""
import math
from .common import SCHEMA, canonical
from .database import Forbidden

def cosine(a,b):
    if len(a)!=len(b) or not a:
        raise ValueError('vector_dimension')
    norm = math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    if not norm or not math.isfinite(norm):
        raise ValueError('invalid_vector')
    return max(-1.0,min(1.0,sum(x*y for x,y in zip(a,b))/norm))

def overlap(a,b,compatible):
    if not compatible:
        return 0.0
    left,right={canonical(x) for x in a},{canonical(x) for x in b}
    return len(left&right)/max(len(left),len(right)) if left and right else 0.0

def score(query,candidate,weights=(.55,.225,.225)):
    if len(weights)!=3 or any(not math.isfinite(x) or x<0 for x in weights) or abs(sum(weights)-1)>1e-9:
        raise ValueError('invalid_weights')
    qv,rv=query['vector'],candidate['vector']
    compatible=query['context_key']==candidate['context_key'] and query['context_bytes']==candidate['context_bytes']
    similarity=(1+cosine(qv,rv))/2
    positive=overlap(query['content']['positives'],candidate['content']['positives'],compatible)
    negative=overlap(query['content']['negatives'],candidate['content']['negatives'],compatible)
    return {'score':weights[0]*similarity+weights[1]*positive+weights[2]*negative,
            'canonicalSimilarity':similarity,'predicateCosine':cosine(qv[768:1536],rv[768:1536]),
            'sharedPositive':positive,'sharedNegative':negative,'contextCompatible':compatible,
            'compatibility':'EXACT_CONTEXT' if compatible else 'INCOMPATIBLE_CONTEXT'}

def parse_vector(text):
    values=[float(x) for x in text.strip('[]').split(',')]
    if len(values)!=3072 or not all(math.isfinite(x) for x in values):
        raise ValueError('stored_vector_invalid')
    return values

def search(repo,record_id,limit=10,model_id=None,weights=None,split=None,max_candidates=1000):
    if repo.purpose != 'retrieve':
        raise Forbidden('retrieve_purpose_required')
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=20:
        raise ValueError('limit_out_of_range')
    with repo.transaction() as c:
        query=repo.searchable(c,record_id,model_id)
        query['vector']=parse_vector(query['vector'])
        if weights is None:weights=tuple((query['promotion'] or {}).get('weights',[.55,.225,.225]))
        parameters=[query['model_id'],repo.purpose]
        clause=''
        if split is not None:
            if split not in ('train','validation','test'):
                raise ValueError('invalid_split')
            clause=' AND r.split=%s';parameters.append(split)
        countrow=c.execute("SELECT count(*) AS n,coalesce(sum(octet_length(r.content::text)),0) AS content_bytes FROM retrieval.record r JOIN retrieval.embedding e ON e.record_id=r.id JOIN retrieval.model m ON m.id=e.model_id WHERE e.model_id=%s AND %s=ANY(r.allowed_purposes) AND r.status='FULL' AND NOT r.revoked AND m.active AND m.servable AND e.content_version=r.content_version"+clause,parameters).fetchone()
        count=countrow['n']
        if countrow['content_bytes']+count*12288>32*1024*1024:raise ValueError('exact_payload_bound_exceeded')
        if count>max_candidates:raise ValueError('exact_corpus_bound_exceeded')
        rows=c.execute("SELECT r.id,r.content,r.context_bytes,r.context_key,r.n,r.family,r.split,r.status,r.rights_version,e.vector::text AS vector FROM retrieval.record r JOIN retrieval.embedding e ON e.record_id=r.id JOIN retrieval.model m ON m.id=e.model_id WHERE e.model_id=%s AND %s=ANY(r.allowed_purposes) AND r.status='FULL' AND NOT r.revoked AND m.active AND m.servable AND e.content_version=r.content_version"+clause+' ORDER BY r.id LIMIT %s',parameters+[max_candidates+1]).fetchall()
        if len(rows)>max_candidates:
            raise ValueError('exact_corpus_bound_exceeded')
        results=[];content_by_id={}
        for row in rows:
            if row['id']==record_id or row['content']==query['content']:
                continue
            row['vector']=parse_vector(row['vector'])
            values=score(query,row,weights)
            content_by_id[row['id']]=(row['content'],row['rights_version'],row['context_key'])
            results.append({'recordId':row['id'],'modelId':query['model_id'],'family':row['family'],'split':row['split'],
                            'schema':SCHEMA,'status':'FULL','representativeStatus':'CHECKED','positiveCount':row['n'],'negativeCount':row['n'],
                            'evidenceOnly':True,**values})
        results.sort(key=lambda x:(-x['score'],x['recordId']))
        selected=results[:limit];content_budget=1500000
        for result in selected:
            content,rights,context=content_by_id[result['recordId']]
            size=len(canonical(content).encode())
            result['safeProvenance']={'recordId':result['recordId'],'modelId':query['model_id'],'contextId':context,'profile':'allow-slot-ast-v1','rightsVersion':rights,'schema':SCHEMA}
            if size<=content_budget:
                result['structuredContent']=content;result['contentUnavailable']=False;content_budget-=size
            else:
                result['contentUnavailable']=True;result['contentReason']='RESPONSE_CONTENT_BUDGET'
        return {'queryRecordId':record_id,'modelId':query['model_id'],'exact':True,'candidateCount':len(results),
                'weights':list(weights),'results':selected}
