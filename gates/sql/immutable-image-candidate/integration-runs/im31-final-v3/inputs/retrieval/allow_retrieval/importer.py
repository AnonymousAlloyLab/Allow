"""Deterministic bounded local corpus ingestion and family-component splits."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import stat
from .common import RUNTIME, ROOT, SCHEMA, canonical, digest, private_write
from .corpus import worker, normalize_full, MAX_SOURCE
from .database import Repository

SOURCES={
 'alloy4fun':Path('/home/augustus/ACGN/classified-data'),
 'alloy5':Path('/home/augustus/下载/alloy5/2025-07-08-11-09-55'),
 'alloy6':Path('/home/augustus/下载/allloy6/2025-07-10-15-42-08')}
ALIASES={x:base for base,items in {
 'trash':['trash_fol','trash_rl','trash_ltl'],'classroom':['classroom_fol','classroom_rl'],
 'productionLine':['productionLineNew','productionLine_v1','productionLine_v2'],
 'cv':['cv_v1','cv_v2'],'courses':['coursesOld','coursesNew'],'trainStation':['trainStationOld','trainStationNew']}.items() for x in items}

def family_id(dataset,relative):
    family=relative.parts[0] if len(relative.parts)>1 else '__root__'
    known=set(ALIASES)|set(ALIASES.values())|{'graphs','socialMedia','lts'}
    for component in relative.parts[:-1]:
        if component in known:
            return 'alloy4fun:'+ALIASES.get(component,component)
    if dataset=='alloy4fun':
        return 'alloy4fun:'+ALIASES.get(family,family)
    # The same hashed repository top directory is shared by Alloy5/6 archives.
    return 'repository:'+family

def candidates(root,family_budget=16,files_per_family=3):
    if root.is_symlink() or not root.is_dir():
        return []
    families=collections.defaultdict(list)
    for directory,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(x for x in dirs if not (Path(directory)/x).is_symlink())
        for name in sorted(files):
            p=Path(directory)/name
            if p.suffix!='.als' or p.is_symlink():
                continue
            rel=p.relative_to(root)
            stat=p.stat(follow_symlinks=False)
            if not 0<stat.st_size<=MAX_SOURCE:
                continue
            family=rel.parts[0] if len(rel.parts)>1 else '__root__'
            # Prefer bounded small models; stable path hash breaks equal-size ties.
            families[family].append((stat.st_size,hashlib.sha256(str(rel).encode()).hexdigest(),p))
    ranked={}
    for family,pool in families.items():
        scored=[]
        for size,key,path in sorted(pool,key=lambda x:x[1])[:64]:
            if size>32768:continue
            try:source,_=read_source(root,path)
            except (ValueError,OSError,UnicodeError):continue
            clean=re.sub(r'/\*.*?\*/|//[^\n]*|--[^\n]*',' ',source,flags=re.S)
            nullary=len(re.findall(r'\bpred\s+[\w/$]+\s*(?:\[\s*\])?\s*\{',clean))
            imports=bool(re.search(r'\bopen\b',clean))
            restricted=bool(re.search(r'\b(abstract|extends|var)\b|\b(one|lone|some)\s+sig\b|\bsig\s+[^{}]*\bin\b',clean))
            score=(1000*(not nullary)+100*imports+100*restricted+5*(size<200),abs(size-1500),key)
            scored.append((score,path))
        if scored:ranked[family]=sorted(scored)
    names=sorted(ranked,key=lambda x:(ranked[x][0][0][0],hashlib.sha256(x.encode()).hexdigest()))[:family_budget]
    selected=[]
    for index in range(files_per_family):
        for family in names:
            pool=ranked[family]
            if index<len(pool):
                selected.append(pool[index][1])
    return selected

def read_source(root,path):
    relative=path.relative_to(root)
    if not relative.parts or any(x in ('..','.') for x in relative.parts):
        raise ValueError('source_outside_root')
    if root.resolve(strict=True)!=root:
        raise ValueError('symlink_source_root')
    directory_flags=os.O_RDONLY|os.O_DIRECTORY|getattr(os,'O_NOFOLLOW',0)
    directory=os.open(root,directory_flags)
    try:
        for component in relative.parts[:-1]:
            child=os.open(component,directory_flags,dir_fd=directory)
            os.close(directory);directory=child
        fd=os.open(relative.parts[-1],os.O_RDONLY|os.O_NONBLOCK|getattr(os,'O_NOFOLLOW',0),dir_fd=directory)
        with os.fdopen(fd,'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError('source_not_regular')
            raw=f.read(MAX_SOURCE+1)
    finally:
        os.close(directory)
    if len(raw)>MAX_SOURCE:raise ValueError('source_bytes')
    return raw.decode('utf-8'),raw

class UnionFind:
    def __init__(self):self.parents={}
    def find(self,x):
        self.parents.setdefault(x,x)
        if self.parents[x]!=x:self.parents[x]=self.find(self.parents[x])
        return self.parents[x]
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parents[max(a,b)]=min(a,b)

def split_records(rows,seed='20261103'):
    uf=UnionFind();keys={}
    for row in rows:
        rid=row['id'];uf.find(rid)
        # Conservative union includes predicate-only duplicates as well as modules.
        evidence=[('family',row['origin_family']),('source',row['source_hash']),
                  ('anonymous_record',digest(row['content'])),('predicate',digest({'context':row['content'].get('context'),'predicate':row['content']['predicate']}))]
        for key in evidence:
            if key in keys:uf.union(rid,keys[key])
            else:keys[key]=rid
    groups=collections.defaultdict(set)
    for row in rows:groups[uf.find(row['id'])].add(row['id'])
    order=sorted(groups,key=lambda x:digest({'seed':seed,'members':sorted(groups[x])}))
    count=len(order)
    # Reserve at least two whole components per held-out partition when possible.
    held=max(2,round(count*.15)) if count>=6 else (1 if count>=3 else 0)
    assignment=[]
    for i,key in enumerate(order):
        split='test' if i<held else 'validation' if i<2*held else 'train'
        component='component:'+digest(sorted(groups[key]))
        assignment.extend((rid,split,component) for rid in groups[key])
    byid={r['id']:r for r in rows};intersections={}
    split_by_id={rid:sp for rid,sp,_ in assignment}
    for field in ('source_hash','origin_family'):
        sets={s:{row[field] for row in rows if split_by_id[row['id']]==s} for s in ('train','validation','test')}
        intersections[field]=sum(len(sets[a]&sets[b]) for a,b in [('train','validation'),('train','test'),('validation','test')])
    if any(intersections.values()):raise ValueError('split_leakage')
    return assignment,{'components':count,'splits':dict(collections.Counter(x[1] for x in assignment)),
                       'component_splits':dict(collections.Counter('test' if i<held else 'validation' if i<2*held else 'train' for i in range(count))),
                       'cross_split_intersections':intersections,'seed':seed}

def finalize_splits(repo):
    with repo.transaction() as c:
        rows=c.execute("SELECT r.id,r.content,r.context_bytes,a.source_hash,a.family AS origin_family FROM retrieval.record r JOIN retrieval.record_origin o ON o.record_id=r.id JOIN retrieval.artifact a ON a.id=o.artifact_id WHERE r.status='FULL' AND NOT r.revoked ORDER BY r.id").fetchall()
    assignments,manifest=split_records(rows)
    repo.assign_splits(assignments)
    manifest['records']=[{'id':rid,'split':split,'family':family} for rid,split,family in assignments]
    manifest['manifest_id']=digest(manifest)
    path=RUNTIME/'manifests'/('split-'+manifest['manifest_id']+'.json')
    private_write(path,(canonical(manifest)+'\n').encode())
    return manifest

def preserve_response(dataset,source_hash,response,stage):
    identity=digest(response)
    private_write(RUNTIME/'diagnostics'/('response-'+identity+'.json'),(canonical(response)+'\n').encode())
    return {'response_id':identity,'status':response['status'],'stage':stage}

def ingest(family_budget=16,files_per_family=3,targets_per_file=2,n=3):
    repo=Repository(purpose='store');repo.initialize()
    totals=collections.Counter();by_source={};seen=set()
    for dataset,root in SOURCES.items():
        stats=collections.Counter()
        for path in candidates(root,family_budget,files_per_family):
            stats['considered_files']+=1
            source_hash=None
            try:
                source,raw=read_source(root,path);source_hash=hashlib.sha256(raw).hexdigest()
                if source_hash in seen:
                    stats['duplicate_source']+=1
                seen.add(source_hash)
                snapshot=RUNTIME/'sources'/source_hash[:2]/(source_hash+'.als')
                private_write(snapshot,raw)
                discovery=worker(source,-1,n)
                if discovery['status']!='DISCOVERY':
                    raise ValueError(discovery.get('reason') or 'discovery_rejected')
                slots=discovery.get('targetSlots',[])
                if not slots:raise ValueError('no_supported_nullary_predicate')
                for slot in slots[:targets_per_file]:
                    stats['considered_predicates']+=1
                    response=worker(source,slot,n)
                    if response['status']!='FULL':
                        reason=response.get('reason') or response['status']
                        stats[response['status']]+=1
                        repo.diagnostic(dataset,source_hash,str(reason)[:128],{**preserve_response(dataset,source_hash,response,'ingestion'),'target_slot':slot})
                        continue
                    record,outcomes,meta=normalize_full(response)
                    metadata={**meta,'family':family_id(dataset,path.relative_to(root)),'N':n,'target_slot':slot,
                              'schema':SCHEMA,'rights_version':'local-user-2026-11-03-v1','dataset':dataset}
                    rid=repo.add_record({'root':dataset,'locator':str(path.relative_to(root)),'source_hash':source_hash,'snapshot':str(snapshot)},record,outcomes,metadata)
                    stats['FULL']+=1
            except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
                stats['rejected_files']+=1
                reason=str(exc)[:128] if not isinstance(exc,subprocess.TimeoutExpired) else 'worker_timeout'
                repo.diagnostic(dataset,source_hash,reason,{'stage':'ingestion'})
        by_source[dataset]=dict(stats);totals.update(stats)
    manifest=finalize_splits(repo)
    report={'schema':SCHEMA,'totals':dict(totals),'sources':by_source,'split':manifest,
            'quality_gate':'OPEN_PENDING_EVALUATION' if manifest['components']>=12 else 'OPEN_INSUFFICIENT_INDEPENDENT_FAMILIES'}
    report['id']=digest(report)
    private_write(RUNTIME/'manifests'/('ingestion-'+report['id']+'.json'),(canonical(report)+'\n').encode())
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--families',type=int,default=16);p.add_argument('--files',type=int,default=3)
    p.add_argument('--targets',type=int,default=2);p.add_argument('--N',type=int,choices=(3,4,5),default=3);a=p.parse_args()
    if not 1<=a.families<=100 or not 1<=a.files<=10 or not 1<=a.targets<=10:raise SystemExit('bounded selection required')
    report=ingest(a.families,a.files,a.targets,a.N)
    # Aggregate output contains no original source, paths, predicates or witnesses.
    print(canonical({k:report[k] for k in ('id','totals','sources','quality_gate')}))
if __name__=='__main__':main()

def replay_accepted():
    """Re-admit a private frozen accepted-locator manifest after worker changes.

    Prior records are durably revoked even if their replacement is now unsupported.
    No previous pool or certificate is reused for the newly compiled worker.
    """
    repo=Repository(purpose='store')
    with repo.transaction() as c:
        rows=c.execute("SELECT r.id,o.target_slot,a.source_root,a.locator FROM retrieval.record r JOIN retrieval.record_origin o ON o.record_id=r.id JOIN retrieval.artifact a ON a.id=o.artifact_id WHERE NOT r.revoked ORDER BY a.source_root,a.locator,o.target_slot").fetchall()
    private_write(RUNTIME/'manifests'/('replay-input-'+digest(rows)+'.json'),(canonical(rows)+'\n').encode())
    previous={r['id'] for r in rows};new=set();stats=collections.Counter();sources=collections.Counter()
    unique={(r['source_root'],r['locator']) for r in rows}
    work=[]
    for dataset,locator in sorted(unique):
        try:
            source,_=read_source(SOURCES[dataset],SOURCES[dataset]/locator)
            discovery=worker(source,-1,3)
            for slot in discovery.get('targetSlots',[])[:3]:work.append({'source_root':dataset,'locator':locator,'target_slot':slot})
        except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired):stats['DISCOVERY_REJECTED']+=1
    for row in work:
        dataset=row['source_root']
        if dataset not in SOURCES:continue
        root=SOURCES[dataset];path=root/row['locator']
        try:
            source,raw=read_source(root,path);source_hash=hashlib.sha256(raw).hexdigest()
            response=worker(source,row['target_slot'],3)
            if response['status']!='FULL':
                stats[response['status']]+=1
                repo.diagnostic(dataset,source_hash,response.get('reason') or response['status'],{**preserve_response(dataset,source_hash,response,'final_worker_replay'),'target_slot':row['target_slot']})
                continue
            record,outcomes,meta=normalize_full(response)
            metadata={**meta,'family':family_id(dataset,path.relative_to(root)),'N':3,'target_slot':row['target_slot'],
                      'schema':SCHEMA,'rights_version':'local-user-2026-11-03-v1','dataset':dataset}
            snapshot=RUNTIME/'sources'/source_hash[:2]/(source_hash+'.als');private_write(snapshot,raw)
            rid=repo.add_record({'root':dataset,'locator':row['locator'],'source_hash':source_hash,'snapshot':str(snapshot)},record,outcomes,metadata)
            new.add(rid);stats['FULL']+=1;sources[dataset]+=1
        except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
            stats['REJECTED']+=1
            repo.diagnostic(dataset,None,'REPLAY_FAILURE',{'stage':'final_worker_replay','exception_type':type(exc).__name__})
    for rid in previous-new:repo.revoke(rid,reason='superseded_final_worker_replay')
    manifest=finalize_splits(repo)
    report={'source_files':len(unique),'attempts':len(work),'outcomes':dict(stats),'distinct_new_records':len(new),'sources':dict(sources),'split':manifest}
    private_write(RUNTIME/'manifests'/('replay-'+digest(report)+'.json'),(canonical(report)+'\n').encode())
    return report
