"""Immutable, local evaluation artifacts consumed by model promotion."""
import json
from .common import RUNTIME,canonical,digest,private_write

def freeze_evidence(payload):
    value=json.loads(canonical(payload))
    identity=digest(value)
    private_write(RUNTIME/'evaluations'/('promotion-'+identity+'.json'),(canonical(value)+'\n').encode())
    return {**value,'artifact_sha256':identity}

def verify_evidence(evidence):
    claimed=evidence.get('artifact_sha256')
    if not isinstance(claimed,str) or len(claimed)!=64:
        raise ValueError('evaluation_artifact_required')
    path=RUNTIME/'evaluations'/('promotion-'+claimed+'.json')
    if path.is_symlink():raise ValueError('evaluation_artifact_symlink')
    raw=path.read_bytes()
    if len(raw)>1048576:raise ValueError('evaluation_artifact_budget')
    value=json.loads(raw)
    if digest(value)!=claimed or value!={k:v for k,v in evidence.items() if k!='artifact_sha256'}:
        raise ValueError('evaluation_artifact_mismatch')
    return value
