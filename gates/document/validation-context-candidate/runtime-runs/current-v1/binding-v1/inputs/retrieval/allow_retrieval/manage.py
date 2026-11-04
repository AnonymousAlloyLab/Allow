"""Explicit local maintenance commands, never exposed by the HTTP JSON bridge."""
import argparse
import collections
import json
from pathlib import Path
from .common import ROOT,RUNTIME,canonical,digest,private_write
from .database import Repository

def export_records():
    repo=Repository(purpose='analyze')
    rows=repo.evaluation_records()
    with repo.transaction() as c:
        origins=c.execute('SELECT o.record_id,array_agg(DISTINCT a.source_root ORDER BY a.source_root) AS sources FROM retrieval.record_origin o JOIN retrieval.artifact a ON a.id=o.artifact_id GROUP BY o.record_id').fetchall()
    coverage={x['record_id']:x['sources'] for x in origins}
    for row in rows:row['sources']=coverage.get(row['record_id'],[row['source']])
    data={'records':rows,'id':digest(rows),'schema':'allow-retrieval-v1'}
    path=RUNTIME/'manifests'/('records-'+data['id']+'.json')
    private_write(path,(canonical(data)+'\n').encode())
    return path,data

def register_encoder(adapter_path=None,training_ids=()):
    from .embedding import load_encoder
    encoder=load_encoder(adapter_path=adapter_path)
    manifest={'encoder_id':encoder.model_id,'model_lock':json.loads((encoder.model_dir/'model-lock.json').read_text()),
              'dimension':3072,'adapter_sha256':digest(Path(adapter_path).read_bytes()) if adapter_path else 'identity',
              'recipe':'hierarchy4x768-query-480-membermean','training_ids':list(training_ids)}
    Repository(purpose='train').register_model(encoder.model_id,manifest,training_ids)
    return encoder

def drain(encoder,limit=1000):
    repo=Repository(purpose='embed');counts=collections.Counter()
    while sum(counts.values())<limit:
        job=repo.claim_job(encoder.model_id)
        if not job:break
        if job['model_id']!=encoder.model_id:
            repo.fail_job(job,'encoder_model_mismatch');counts['model_mismatch']+=1;continue
        try:
            vector=encoder.encode_record(job['content'])
            repo.publish(job,vector)
            counts['published']+=1
        except ValueError as exc:
            repo.fail_job(job,str(exc));counts['failed']+=1
    return dict(counts)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=('initialize','export','embed','status'))
    parser.add_argument('--adapter');parser.add_argument('--training-manifest');args=parser.parse_args()
    if args.command=='initialize':Repository().initialize();result={'initialized':True}
    elif args.command=='export':
        path,data=export_records();result={'path':str(path),'records':len(data['records']),'id':data['id']}
    elif args.command=='embed':
        ids=[]
        if args.adapter:
            if not args.training_manifest:raise ValueError('training_manifest_required')
            ids=json.loads(Path(args.training_manifest).read_text())['record_ids']
        encoder=register_encoder(args.adapter,ids);result={'model_id':encoder.model_id,**drain(encoder)}
    else:result=Repository().status()
    print(canonical(result))

if __name__=='__main__':main()
