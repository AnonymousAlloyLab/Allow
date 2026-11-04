"""Actual CPU contrastive fitting of 3072 shared diagonal parameters."""
import hashlib
import importlib.metadata
import csv
import io
import json
from pathlib import Path
import numpy as np
from .embedding import compose


def train(pairs, output_dir):
    """Fit only supplied train-family checked pairs with the fixed 20-epoch recipe."""
    import torch
    runtime = json.loads((Path(__file__).resolve().parents[1]/'training-runtime-lock.json').read_text())
    distribution = importlib.metadata.distribution('torch')
    payload = [r for r in csv.reader(io.StringIO(distribution.read_text('RECORD'))) if r[1] and not r[0].endswith(('/INSTALLER','/REQUESTED','/direct_url.json')) and not r[0].startswith('../')]
    record_hash = hashlib.sha256(json.dumps(sorted(payload),separators=(',',':')).encode()).hexdigest()
    if distribution.version != runtime['torch_version'] or record_hash != runtime['distribution_payload_record_sha256']:
        raise ValueError('unapproved_training_runtime')
    if not pairs or any(p['split'] != 'train' for p in pairs):
        raise ValueError('training_split_only')
    ids = [p['record_id'] for p in pairs]
    if len(set(ids)) != len(ids):
        raise ValueError('one_pair_per_source_record')
    for p in pairs:
        if not p.get('certificate_id') or np.array_equal(p['left_blocks'], p['right_blocks']):
            raise ValueError('distinct_checked_pair_required')
        compose(p['left_blocks']); compose(p['right_blocks'])
    torch.manual_seed(20261103)
    torch.set_num_threads(4)
    rng = np.random.default_rng(20261103)
    scales = torch.zeros((4,768), requires_grad=True)
    optimizer = torch.optim.Adam([scales], lr=.001, weight_decay=.0001)
    history, skipped, epoch_orders = [], 0, []
    def encode(batch, side):
        x = torch.tensor(np.stack([p[side] for p in batch]), dtype=torch.float32)
        x = torch.nn.functional.normalize(x, dim=-1)
        x = torch.nn.functional.normalize(x * scales.exp(), dim=-1)
        return x.reshape(len(batch),3072)/2
    for epoch in range(20):
        losses = []
        order = rng.permutation(len(pairs))
        epoch_orders.append([pairs[i]["record_id"] for i in order])
        for start in range(0, len(order),16):
            batch = [pairs[i] for i in order[start:start+16]]
            keys = [p.get('equivalence_id',p['record_id']) for p in batch]
            content_keys = [{hashlib.sha256(np.asarray(p[side],dtype='<f4').tobytes()).hexdigest() for side in ('left_blocks','right_blocks')} for p in batch]
            if len(set(keys)) < 2 or not any(keys[i] != keys[j] and not content_keys[i].intersection(content_keys[j]) for i in range(len(batch)) for j in range(i)):
                skipped += 1; continue
            a,b = encode(batch,'left_blocks'),encode(batch,'right_blocks')
            logits = a @ b.T / .07
            mask = torch.tensor([[i != j and (keys[i] == keys[j] or bool(content_keys[i].intersection(content_keys[j]))) for j in range(len(batch))] for i in range(len(batch))])
            logits = logits.masked_fill(mask,float('-inf'))
            labels = torch.arange(len(batch))
            loss = (torch.nn.functional.cross_entropy(logits,labels)+torch.nn.functional.cross_entropy(logits.T,labels))/2
            loss = loss + .001 * ((scales.exp()-1)**2).mean()
            if not torch.isfinite(loss): raise ValueError('nonfinite_training_loss')
            optimizer.zero_grad(); loss.backward(); optimizer.step()
            if not torch.isfinite(scales).all(): raise ValueError('nonfinite_adapter')
            losses.append(float(loss.detach()))
        history.append({'epoch':epoch+1,'loss':float(np.mean(losses)) if losses else None,'batches':len(losses)})
    if not any(h['batches'] for h in history): raise ValueError('no_trainable_batches')
    out = Path(output_dir);out.mkdir(mode=0o700,parents=True,exist_ok=True);out.chmod(0o700)
    np.save(out/'adapter.npy',scales.detach().numpy(),allow_pickle=False)
    (out/'adapter.npy').chmod(0o600)
    manifest = {'seed':20261103,'epochs':20,'checkpoint':'final','parameters':3072,'optimizer':'Adam','learning_rate':.001,'weight_decay':.0001,'temperature':.07,'identity_l2':.001,'batch_size':16,'history':history,'skipped_batches':skipped,'record_ids':ids,'epoch_orders':epoch_orders,'pairs':[{'record_id':p['record_id'],'family':p['family'],'certificate_id':p['certificate_id'],'equivalence_id':p.get('equivalence_id',p['record_id']),'cache_sha256':{side:hashlib.sha256(np.asarray(p[side],dtype='<f4').tobytes()).hexdigest() for side in ('left_blocks','right_blocks')}} for p in pairs],'families':sorted(set(p['family'] for p in pairs)),'torch':torch.__version__,'adapter_sha256':hashlib.sha256((out/'adapter.npy').read_bytes()).hexdigest()}
    (out/'training.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'training.json').chmod(0o600)
    return scales.detach().numpy(),manifest


def checked_variant_record(record, evidence, variant):
    """Build a query projection from an internally replayed worker augmentation.

    This checks endpoint/context linkage, not certificate soundness. Only trusted
    worker evidence may reach this helper; it is never an HTTP admission route.
    """
    import copy
    original = evidence['certificate']
    certificate = variant.get('certificate')
    if variant.get('certificateStatus') != 'CHECKED' or not isinstance(certificate,dict):
        raise ValueError('unchecked_variant')
    if certificate.get('context') != original['context'] or certificate.get('rulesetDigest') != original['rulesetDigest']:
        raise ValueError('variant_context_or_ruleset_mismatch')
    if original['extracted'] != record['predicate']['representative']:
        raise ValueError('original_endpoint_mismatch')
    source = original['input']
    truth = {'op':'TRUE','sort':source['sort'],'atom':'','children':[]}
    expected = {'op':'AND','sort':source['sort'],'atom':'','children':[source,truth]}
    if variant.get('input') != expected or certificate.get('input') != expected or certificate.get('extracted') != variant.get('extracted'):
        raise ValueError('augmentation_endpoint_mismatch')
    result = copy.deepcopy(record)
    result['predicate']['representative'] = copy.deepcopy(expected)
    if result == record:
        raise ValueError('identity_variant')
    return result, hashlib.sha256(json.dumps(certificate,sort_keys=True,separators=(',',':')).encode()).hexdigest()
