"""Frozen family-macro structural retrieval metrics; no semantic labels inferred."""
import math
import numpy as np
from .embedding import compose


def metrics(rankings):
    families = {}
    for row in rankings:
        ids = row['ranked_target_ids']
        # Multiple serializations of one target count once.
        ids = list(dict.fromkeys(ids))
        rank = ids.index(row['target_id'])+1 if row['target_id'] in ids else 0
        hit = 0 < rank <= 10
        value = [1/rank if hit else 0, float(hit), 1/math.log2(rank+1) if hit else 0]
        families.setdefault(row['family'],[]).append(value)
    if not families: raise ValueError('empty_evaluation')
    per_family = {k:np.mean(v,axis=0).tolist() for k,v in families.items()}
    macro = np.mean(list(per_family.values()),axis=0)
    return {'family_macro':dict(zip(('mrr10','recall10','ndcg10'),map(float,macro))), 'families':per_family,'queries':len(rankings)}


def rank(query_blocks, candidates, log_scales=None, exclude_ids=()):
    q = compose(query_blocks,log_scales)
    scores = [(float(q @ compose(c['blocks'],log_scales)),c['record_id']) for c in candidates if c['record_id'] not in exclude_ids]
    return [record_id for _,record_id in sorted(scores,key=lambda x:(-x[0],x[1]))]


def promotion(baseline, learned, manifest, integrity_pass):
    splits = {}
    for row in manifest:
        family,split = row['family'],row['split']
        if family in splits and splits[family] != split: raise ValueError('family_split_leakage')
        splits[family] = split
    sources = {source for row in manifest if row.get('status') == 'FULL' for source in row.get('sources',[row['source']])}
    enough = len(splits)>=12 and sum(s=='validation' for s in splits.values())>=2 and sum(s=='test' for s in splits.values())>=2 and sources >= {'alloy4fun','alloy5','alloy6'}
    passes = enough and integrity_pass and learned['family_macro']['mrr10'] >= baseline['family_macro']['mrr10']-.01
    return {'promoted':bool(passes),'quality_gate':'PASS' if passes else 'OPEN','family_count':len(splits),'source_coverage':sorted(sources)}


def evaluate_cached(queries, candidates, log_scales=None, weights=(1.,0.,0.), predicate_only=False):
    """Rank all same-split heldout targets; inputs are checked structural variant fixtures.

    Each query supplies query_id, target_id, family, split, blocks, content,
    context_key and context_bytes. Candidate record_id identifies one distinct
    target. Candidate target_id may group several checked serializations.
    """
    from .ranking import score
    prepared = []
    for c in candidates:
        row = dict(c)
        row['vector'] = compose(c['blocks'],log_scales).tolist()
        prepared.append(row)
    rankings = []
    counts, block_diagnostics = [], []
    for q in queries:
        if q['split'] not in ('validation','test'):
            raise ValueError('heldout_split_required')
        query = dict(q)
        query['vector'] = compose(q['blocks'],log_scales).tolist()
        eligible = [c for c in prepared if c['split']==q['split'] and c['record_id']!=q['query_id']
                    and c['content']!=q['content']]
        if predicate_only:
            from .embedding import normalize
            predicate = normalize(q['blocks'][1])
            scored = [(float(predicate @ normalize(c['blocks'][1])),c['record_id'],c.get('target_id',c['record_id'])) for c in eligible]
        else:
            scored = [(score(query,c,weights)['score'],c['record_id'],c.get('target_id',c['record_id'])) for c in eligible]
        scored.sort(key=lambda row:(-row[0],row[1]))
        rankings.append({'family':q['family'],'target_id':q['target_id'],'ranked_target_ids':[x[2] for x in scored]})
        counts.append(len(eligible))
        target = next((c for c in eligible if c.get('target_id',c['record_id'])==q['target_id']),None)
        if target is not None:
            from .embedding import normalize
            qb,tb=normalize(q['blocks']),normalize(target['blocks'])
            if log_scales is not None:
                qb,tb=normalize(qb*np.exp(log_scales)),normalize(tb*np.exp(log_scales))
            block_diagnostics.append({'query_id':q['query_id'],'target_id':q['target_id'],
                                      'cosines':np.sum(qb*tb,axis=1).astype(float).tolist()})
    report = metrics(rankings)
    report.update(candidate_counts=counts,distinct_targets=len({q['target_id'] for q in queries}),weights=list(weights),target_block_cosines=block_diagnostics)
    # Family bootstrap reflects the grouping unit, without pretending a tiny pilot is broad evidence.
    values = [v[0] for v in report['families'].values()]
    rng = np.random.default_rng(20261103)
    samples = np.mean(rng.choice(values,size=(2000,len(values)),replace=True),axis=1)
    report['mrr10_family_bootstrap_95'] = list(map(float,np.quantile(samples,[.025,.975])))
    return report


def select_weights(validation_queries, candidates, log_scales=None):
    """Select only on validation families using the frozen nine-point grid."""
    if not validation_queries or any(q['split']!='validation' for q in validation_queries):
        raise ValueError('validation_only_selection')
    grid = [(d,(1-d)*r,(1-d)*(1-r)) for d in (.45,.55,.65) for r in (.25,.5,.75)]
    reports = [(weights,evaluate_cached(validation_queries,candidates,log_scales,weights)) for weights in grid]
    reports.sort(key=lambda row:(-row[1]['family_macro']['mrr10'],row[0]))
    return reports[0][0], reports


def run_pilot(rows, output_dir, encoder=None, integrity_pass=False):
    """Execute local feature caching, train-only fit and a single frozen holdout run.

    Rows must come from the authorized repository with replayed worker evidence.
    No method here admits records or grants permission to publish a trained model.
    """
    import hashlib
    import json
    from pathlib import Path
    from .embedding import Encoder
    from .training import checked_variant_record, train
    from .common import canonical, private_write
    if not rows or any(r['status']!='FULL' for r in rows):
        raise ValueError('full_records_required')
    encoder = encoder or Encoder()
    root = Path(output_dir)
    root.mkdir(mode=0o700,parents=True,exist_ok=True);root.chmod(0o700)
    candidates,queries,pairs,skips,eligible_rows = [],[],[],[],[]
    for row in rows:
        base = {k:row[k] for k in ('family','split','source','content','context_key','context_bytes')}
        variants = row['evidence'].get('training_variants',[])
        if not variants:
            skips.append({'record_id':row['record_id'],'reason':'no_checked_variant'});continue
        variant,certificate = checked_variant_record(row['content'],row['evidence'],variants[0])
        try:
            original = encoder.encode_blocks(row['content'])
            alternate = encoder.encode_blocks(variant)
        except ValueError as exc:
            if str(exc) not in ('component_budget','component_token_budget','component_chunk_budget','special_or_prefix_budget'):
                raise
            skips.append({'record_id':row['record_id'],'reason':str(exc)});continue
        if np.array_equal(original,alternate):
            skips.append({'record_id':row['record_id'],'reason':'identical_encoded_variant'});continue
        eligible_rows.append(row)
        candidates.append({**base,'record_id':row['record_id'],'blocks':original})
        # Content hashes plus frozen manifest bind private cached matrices to their inputs.
        cache = root/'features'/ (row['record_id']+'.npz')
        cache.parent.mkdir(mode=0o700,exist_ok=True)
        np.savez_compressed(cache,original=original,variant=alternate);cache.chmod(0o600)
        if row['split']=='train':
            pairs.append({'record_id':row['record_id'],'family':row['family'],'split':'train','certificate_id':certificate,
                          'equivalence_id':hashlib.sha256(canonical(row['content']['predicate']['representative']).encode()).hexdigest(),
                          'left_blocks':original,'right_blocks':alternate})
        else:
            queries.append({**base,'content':variant,'query_id':'variant:'+certificate,'target_id':row['record_id'],'blocks':alternate})
    lineage = [{k:r[k] for k in ('record_id','family','split','source','status')} | {'sources':r.get('sources',[r['source']]),'content_hash':hashlib.sha256(canonical(r['content']).encode()).hexdigest()} for r in eligible_rows]
    promotion({'family_macro':{'mrr10':0}}, {'family_macro':{'mrr10':0}}, lineage,False)
    frozen = hashlib.sha256(canonical(lineage).encode()).hexdigest()
    private_write(root/'frozen-manifest.json',(canonical({'id':frozen,'rows':lineage,'rejections':skips})+'\n').encode())
    report = {'frozen_manifest_id':frozen,'baseline_model_id':encoder.model_id,'full_records':len(rows),'eligible_records':len(eligible_rows),'source_coverage':sorted({source for r in lineage for source in r['sources']}),'training_pairs':len(pairs),
              'validation_queries':sum(q['split']=='validation' for q in queries),'test_queries':sum(q['split']=='test' for q in queries),
              'family_components':len({r['family'] for r in eligible_rows}),'validation_components':len({r['family'] for r in eligible_rows if r['split']=='validation'}),'test_components':len({r['family'] for r in eligible_rows if r['split']=='test'}),'skipped':skips,'quality_gate':'OPEN','training_status':'NOT_RUN','integrity_passed':bool(integrity_pass)}
    if len(pairs)<2 or len({p['equivalence_id'] for p in pairs})<2:
        report['training_status']='BLOCKED_INSUFFICIENT_TRAIN_TARGETS'
    else:
        adapter,training = train(pairs,root/'trained')
        report['training_status']='TRAINED';report['training']=training
        report['learned_model_id']=Encoder(encoder.model_dir,adapter_path=root/'trained'/'adapter.npy').model_id
        report['model_id']=report['learned_model_id'];report['adapter_sha256']=training['adapter_sha256'];report['training_record_ids']=training['record_ids']
        validation = [q for q in queries if q['split']=='validation']
        test = [q for q in queries if q['split']=='test']
        if validation and test:
            weights,grid = select_weights(validation,candidates,adapter)
            decision={'frozen_manifest_id':frozen,'adapter_sha256':training['adapter_sha256'],'weights':list(weights),
                      'grid':[{'weights':list(w),'metrics':m} for w,m in grid]}
            decision_bytes=(canonical(decision)+'\n').encode()
            private_write(root/'validation-decision.json',decision_bytes)
            report['validation_decision_sha256']=hashlib.sha256(decision_bytes).hexdigest()
            report['selected_weights']=list(weights);report['weights']=list(weights)
            report['pretrained'] = evaluate_cached(test,candidates)
            report['learned'] = evaluate_cached(test,candidates,adapter)
            report['predicate_only'] = evaluate_cached(test,candidates,predicate_only=True)
            report['learned_family_macro_mrr']=report['learned']['family_macro']['mrr10']
            report['baseline_family_macro_mrr']=report['pretrained']['family_macro']['mrr10']
            report['combined_pretrained'] = evaluate_cached(test,candidates,None,weights)
            report['combined_learned'] = evaluate_cached(test,candidates,adapter,weights)
            report.update(promotion(report['pretrained'],report['learned'],lineage,integrity_pass))
    private_write(root/'evaluation.json',(canonical(report)+'\n').encode())
    return report


def verify_cached_projection(encoder, content, variant, base_blocks, variant_blocks):
    """Require exact deterministic replay of pinned encoder inputs, not retrospective hashes."""
    if not np.array_equal(encoder.encode_blocks(content),base_blocks):
        raise ValueError('original_feature_cache_replay_mismatch')
    if not np.array_equal(encoder.encode_blocks(variant),variant_blocks):
        raise ValueError('variant_feature_cache_replay_mismatch')


def verify_original_manifest(manifest, expected_id):
    """Bind the historical eligible rows to their originally recorded content digest."""
    import hashlib
    from .common import canonical
    if manifest.get('id')!=expected_id or hashlib.sha256(canonical(manifest['rows']).encode()).hexdigest()!=expected_id:
        raise ValueError('original_manifest_changed')


def rerun_repaired_holdout(rows, prior_dir, output_dir, repair_evidence, encoder=None, integrity_pass=False):
    """Re-measure a technically repaired test query with the frozen original fit.

    This is explicitly an observed holdout rerun, never a new blind test. It does
    not call train or select_weights and refuses changed original family/content
    assignments. Only previously excluded missing-variant test rows may be added.
    """
    import hashlib
    import json
    from pathlib import Path
    from .common import canonical, private_write, digest
    from .embedding import Encoder
    from .training import checked_variant_record
    prior,root=Path(prior_dir),Path(output_dir)
    if prior.resolve()==root.resolve(): raise ValueError('preserve_original_pilot')
    root.mkdir(mode=0o700,parents=True,exist_ok=True);root.chmod(0o700)
    old_bytes=(prior/'evaluation.json').read_bytes();old=json.loads(old_bytes)
    prior_envelope=json.loads((prior/'evaluation-artifact.json').read_text())
    if hashlib.sha256(old_bytes).hexdigest()!=prior_envelope['evaluation_sha256']:
        raise ValueError('original_evaluation_changed')
    historical=json.loads(Path(repair_evidence['original_export_path']).read_text())
    if historical['id']!=repair_evidence['original_export_id'] or digest(historical['records'])!=historical['id']:
        raise ValueError('historical_export_changed')
    historical_rows={r['record_id']:r for r in historical['records']}
    if len(historical_rows)!=len(rows): raise ValueError('historical_record_count_changed')
    for row in rows:
        before=historical_rows[row['record_id']]
        for key in ('content','context_key','context_bytes','family','split','source','sources','status'):
            if row[key]!=before[key]: raise ValueError('historical_record_projection_changed')
        if row['evidence']['certificate']!=before['evidence']['certificate']:
            raise ValueError('original_certificate_changed')
    decision_bytes=(prior/'validation-decision.json').read_bytes()
    if hashlib.sha256(decision_bytes).hexdigest()!=old['validation_decision_sha256']:
        raise ValueError('validation_decision_changed')
    decision=json.loads(decision_bytes);weights=tuple(decision['weights'])
    if list(weights)!=old['weights']: raise ValueError('weight_change_forbidden')
    adapter_path=prior/'trained'/'adapter.npy'
    if hashlib.sha256(adapter_path.read_bytes()).hexdigest()!=old['adapter_sha256']:
        raise ValueError('checkpoint_changed')
    adapter=np.load(adapter_path,allow_pickle=False)
    encoder=encoder or Encoder()
    if encoder.model_id!=old['baseline_model_id'] or Encoder(encoder.model_dir,adapter_path=adapter_path).model_id!=old['model_id']:
        raise ValueError('runtime_or_model_changed')
    original_manifest=json.loads((prior/'frozen-manifest.json').read_text())
    verify_original_manifest(original_manifest,old['frozen_manifest_id'])
    original={r['record_id']:r for r in original_manifest['rows']}
    supplied={r['record_id']:r for r in rows}
    if len(supplied)!=len(rows) or not set(original)<=set(supplied): raise ValueError('record_set_changed')
    allowed={r['record_id'] for r in old['skipped'] if r['reason']=='no_checked_variant'}
    additions=set(supplied)-set(original)
    if not additions or additions!=allowed or any(supplied[r]['split']!='test' for r in additions):
        raise ValueError('only_missing_test_variant_repair_allowed')
    lineage=[];candidates=[];queries=[];cache_hashes={};repairs=[]
    training_pairs={r['record_id']:r for r in old['training']['pairs']}
    heldout_certificate={r['target_id']:r['query_id'].removeprefix('variant:') for r in old['learned']['target_block_cosines']+decision['grid'][0]['metrics']['target_block_cosines']}
    for row in rows:
        entry={k:row[k] for k in ('record_id','family','split','source','status')}
        entry.update(sources=row.get('sources',[row['source']]),content_hash=hashlib.sha256(canonical(row['content']).encode()).hexdigest())
        if row['status']!='FULL': raise ValueError('full_record_required')
        rid=row['record_id']
        if rid in original:
            if entry!=original[rid]: raise ValueError('original_lineage_or_content_changed')
            cache=prior/'features'/(rid+'.npz')
            with np.load(cache,allow_pickle=False) as data:
                base_blocks,variant_blocks=data['original'],data['variant']
            if rid in training_pairs:
                for key,value in [('left_blocks',base_blocks),('right_blocks',variant_blocks)]:
                    if hashlib.sha256(np.asarray(value,dtype='<f4').tobytes()).hexdigest()!=training_pairs[rid]['cache_sha256'][key]:
                        raise ValueError('training_cache_changed')
            cache_hashes[str(cache)]=hashlib.sha256(cache.read_bytes()).hexdigest()
            variant_content,certificate=checked_variant_record(row['content'],row['evidence'],row['evidence']['training_variants'][0])
            expected_certificate=training_pairs[rid]['certificate_id'] if rid in training_pairs else heldout_certificate[rid]
            if certificate!=expected_certificate: raise ValueError('original_variant_changed')
            verify_cached_projection(encoder,row['content'],variant_content,base_blocks,variant_blocks)
        else:
            variant_content,certificate=checked_variant_record(row['content'],row['evidence'],row['evidence']['training_variants'][0])
            base_blocks=encoder.encode_blocks(row['content']);variant_blocks=encoder.encode_blocks(variant_content)
            if np.array_equal(base_blocks,variant_blocks): raise ValueError('identity_repaired_variant')
            cache=root/'features'/(rid+'.npz');cache.parent.mkdir(mode=0o700,exist_ok=True)
            np.savez_compressed(cache,original=base_blocks,variant=variant_blocks);cache.chmod(0o600)
            cache_hashes[str(cache)]=hashlib.sha256(cache.read_bytes()).hexdigest()
            repairs.append({'record_id':rid,'certificate_sha256':certificate})
        compose(base_blocks);compose(variant_blocks)
        base={k:row[k] for k in ('family','split','source','content','context_key','context_bytes')}
        candidates.append({**base,'record_id':rid,'blocks':base_blocks})
        if row['split']=='test':
            queries.append({**base,'content':variant_content,'query_id':'variant:'+certificate,'target_id':rid,'blocks':variant_blocks})
        lineage.append(entry)
    manifest={'rows':lineage,'prior_evaluation_sha256':hashlib.sha256(old_bytes).hexdigest(),
              'prior_manifest_id':old['frozen_manifest_id'],'validation_decision_sha256':old['validation_decision_sha256'],
              'adapter_sha256':old['adapter_sha256'],'feature_cache_sha256':cache_hashes,'repairs':repairs,'technical_repair':repair_evidence,
              'original_cache_verification':f'All {len(original)} original canonical and exact certificate-bound variant arrays independently re-encoded with the pinned original model and matched bit-for-bit. Hashes below are new repair-input bindings, not invented historical hashes.'}
    frozen=hashlib.sha256(canonical(manifest).encode()).hexdigest()
    private_write(root/'frozen-manifest.json',(canonical({'id':frozen,**manifest})+'\n').encode())
    private_write(root/'validation-decision.json',decision_bytes)
    report={'model_id':old['model_id'],'learned_model_id':old['model_id'],'baseline_model_id':old['baseline_model_id'],
            'adapter_sha256':old['adapter_sha256'],'training_record_ids':old['training_record_ids'],'training':old['training'],
            'training_status':'REUSED_FROZEN_CHECKPOINT_NO_RETRAIN','training_pairs':old['training_pairs'],
            'frozen_manifest_id':frozen,'prior_evaluation_sha256':manifest['prior_evaluation_sha256'],
            'prior_evaluation_path':str(prior/'evaluation.json'),'original_export_id':historical['id'],'cache_verification':manifest['original_cache_verification'],'validation_decision_sha256':old['validation_decision_sha256'],
            'weights':list(weights),'full_records':len(rows),'eligible_records':len(rows),'repaired_queries':len(repairs),
            'family_components':len({r['family'] for r in rows}),
            'validation_components':len({r['family'] for r in rows if r['split']=='validation'}),
            'test_components':len({r['family'] for r in rows if r['split']=='test'}),
            'validation_queries':old['validation_queries'],'test_queries':len(queries),'integrity_passed':bool(integrity_pass),
            'exploratory_history':'Original incomplete test subset was already observed. This technical-repair rerun is not a fresh blind holdout.',
            'pretrained':evaluate_cached(queries,candidates),'learned':evaluate_cached(queries,candidates,adapter),
            'predicate_only':evaluate_cached(queries,candidates,predicate_only=True),
            'combined_pretrained':evaluate_cached(queries,candidates,None,weights),
            'combined_learned':evaluate_cached(queries,candidates,adapter,weights)}
    report['baseline_family_macro_mrr']=report['pretrained']['family_macro']['mrr10']
    report['learned_family_macro_mrr']=report['learned']['family_macro']['mrr10']
    report.update(promotion(report['pretrained'],report['learned'],lineage,integrity_pass))
    data=(canonical(report)+'\n').encode();private_write(root/'evaluation.json',data)
    envelope={k:report[k] for k in ('model_id','adapter_sha256','training_record_ids','frozen_manifest_id','family_components','validation_components','test_components','source_coverage','weights','quality_gate','integrity_passed','baseline_family_macro_mrr','learned_family_macro_mrr','validation_decision_sha256')}
    envelope.update(evaluation_path=str(root/'evaluation.json'),evaluation_sha256=hashlib.sha256(data).hexdigest())
    private_write(root/'evaluation-artifact.json',(canonical(envelope)+'\n').encode())
    return report
