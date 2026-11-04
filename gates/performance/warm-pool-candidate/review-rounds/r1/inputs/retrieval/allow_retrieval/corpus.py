"""Bounded, namespace-isolated Java corpus worker driver."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from .common import ROOT, RUNTIME, canonical, digest

MAX_SOURCE=32768
MAX_RESPONSE=2097152
TOOLCHAIN_FILES=('backend/target/solver/alloy.jar','backend/target/classes/dev/allow/corpus/CorpusWorkerMain.class')

JAVA_HOME=Path('/usr/lib/jvm/java-17-openjdk-amd64')
ALLOY_SHA256='6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d'

def toolchain_id():
    target=ROOT/'backend/target'
    # Corpus behavior excludes frontend static assets and Spring HTTP/UI code.
    # The frozen pilot's prior full-build identity remains preserved privately.
    paths=sorted(p for p in (target/'classes').rglob('*') if p.is_file() and 'static' not in p.relative_to(target/'classes').parts and not str(p.relative_to(target/'classes')).startswith('dev/allow/backend/'))
    paths+=sorted((target/'dependency').glob('*.jar'))
    paths+=[target/'solver/alloy.jar']
    if not paths or not (target/'classes/dev/allow/corpus/CorpusWorkerMain.class').is_file():
        raise RuntimeError('worker_not_built')
    hasher=hashlib.sha256()
    for p in paths:
        hasher.update(str(p.relative_to(target)).encode());hasher.update(b'\0')
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):hasher.update(block)
        hasher.update(b'\0')
    props=subprocess.run([str(JAVA_HOME/'bin/java'),'-XshowSettings:properties','-version'],capture_output=True,timeout=5,check=True)
    version=next(line.split('=',1)[1].strip() for line in props.stderr.decode().splitlines() if line.strip().startswith('java.runtime.version ='))
    hasher.update(version.encode())
    return hasher.hexdigest()

def sandbox_command():
    target=ROOT/'backend/target'
    solver=target/'solver/alloy.jar'
    if hashlib.sha256(solver.read_bytes()).hexdigest()!=ALLOY_SHA256:
        raise RuntimeError('unapproved_solver')
    command=['/usr/bin/prlimit','--as=2147483648','--fsize='+str(MAX_RESPONSE),'--nofile=256','--cpu=35',
             '/usr/bin/bwrap','--unshare-all','--new-session','--die-with-parent','--cap-drop','ALL']
    mounts=[(JAVA_HOME,str(JAVA_HOME)),('/usr/lib/x86_64-linux-gnu','/lib/x86_64-linux-gnu'),
            ('/usr/lib/x86_64-linux-gnu','/usr/lib/x86_64-linux-gnu'),('/lib64','/lib64'),
            ('/etc/java-17-openjdk','/etc/java-17-openjdk'),(target/'classes','/app/classes'),
            (target/'dependency','/app/dependency'),(solver,'/app/solver.jar')]
    for source,destination in mounts:
        if not Path(source).exists():raise RuntimeError('sandbox_runtime_missing')
        command+=['--ro-bind',str(source),destination]
    return command+['--tmpfs','/tmp','--proc','/proc','--dev','/dev','--chdir','/tmp']

def worker(source,target_slot=-1,n=3):
    raw=source.encode('utf-8')
    if len(raw)>MAX_SOURCE or n not in (3,4,5):
        raise ValueError('source_or_N_budget')
    if not shutil.which('bwrap') or not shutil.which('prlimit'):
        raise RuntimeError('isolated_worker_unavailable')
    request_id=str(uuid.uuid4());toolchain=toolchain_id();source_hash=hashlib.sha256(raw).hexdigest()
    request={'protocol':1,'source':source,'sourceHash':source_hash,'targetSlot':target_slot,'N':n,
             'requestId':request_id,'toolchain':toolchain}
    command=sandbox_command()+[str(JAVA_HOME/'bin/java'),'-Xmx512m','-Xss512k','-XX:+UseSerialGC',
             '-XX:ActiveProcessorCount=2','-XX:MaxMetaspaceSize=128m','-XX:CompressedClassSpaceSize=64m',
             '-XX:ReservedCodeCacheSize=48m','-Djava.awt.headless=true','-Dfile.encoding=UTF-8','-Djava.io.tmpdir=/tmp',
             '-cp','/app/classes:/app/dependency/*:/app/solver.jar','dev.allow.corpus.CorpusWorkerMain']
    work=RUNTIME/'worker';work.mkdir(mode=0o700,parents=True,exist_ok=True);work.chmod(0o700)
    with tempfile.TemporaryFile(dir=work) as output:
        result=subprocess.run(command,input=(canonical(request)+'\n').encode(),stdout=output,stderr=subprocess.DEVNULL,
                              timeout=33,env={})
        if result.returncode:
            raise RuntimeError('worker_process_failed')
        output.seek(0);response=output.read(MAX_RESPONSE+1)
    if len(response)>MAX_RESPONSE or response.count(b'\n')!=1 or not response.endswith(b'\n'):
        raise ValueError('worker_response_framing')
    if toolchain_id()!=toolchain:
        raise ValueError('worker_build_changed_during_job')
    data=json.loads(response)
    if not isinstance(data,dict) or data.get('status') not in ('DISCOVERY','FULL','PARTIAL','REJECTED'):
        raise ValueError('worker_response_shape')
    if target_slot>=0 and data.get('record'):
        provenance=data['record']['provenance']
        for key,expected in [('requestId',request_id),('sourceHash',source_hash),('targetSlot',target_slot),('toolchain',toolchain)]:
            if provenance.get(key)!=expected:
                raise ValueError('worker_identity_mismatch')
    return data

def normalize_full(response):
    if response.get('status')!='FULL':
        raise ValueError('not_FULL')
    r=response['record'];p=r['predicate'];island=p['island']
    if island.get('certificateStatus')!='CHECKED' or not isinstance(island.get('certificate'),dict):
        raise ValueError('missing_checked_certificate')
    slot=r['provenance']['targetSlot']
    if island.get('rootPath')!=[3,slot,5]:
        raise ValueError('certificate_target_mismatch')
    # Only closed anonymous structural projections enter the encoder. Certificates,
    # ruleset hashes, provenance and human names stay in the private metadata.
    context=json.loads(r['context']) if isinstance(r['context'],str) else r['context']
    body=p['body']
    if isinstance(body,str):
        body=json.loads(body)
    context={'environment':context,'bounds':r['provenance']['bounds'],'options':{'temporal':False,'noOverflow':True,'expected':-1,'perSignatureScopes':[]},'schema':'allow-retrieval-v1','profile':'allow-slot-ast-v1'}
    record={'context':context,'predicate':{'body':body,'representative':island['extracted']},
            'positives':[json.loads(x) if isinstance(x,str) else x for x in r['positive']['members']],
            'negatives':[json.loads(x) if isinstance(x,str) else x for x in r['negative']['members']]}
    if any(not isinstance(record[k],(list,dict)) for k in ('context','predicate')):
        raise ValueError('invalid_structural_projection')
    outcomes={key:{k:v for k,v in r[key].items() if k!='members'} for key in ('positive','negative')}
    proof={'certificate_status':'CHECKED','certificate_id':digest(island['certificate']),
           'certificate':island['certificate'],'ruleset_digest':p['rulesetDigest'],'root_path':island['rootPath']}
    return record,outcomes,{**r['provenance'],**proof,'training_variants':r.get('trainingVariants',[])}

def augment(record_id,certificate):
    """Run the trusted bounded pinned-rule replay helper, without source input."""
    import re
    if not isinstance(record_id,str) or not re.fullmatch('[0-9a-f]{64}',record_id) or not isinstance(certificate,dict):
        raise ValueError('invalid_augment_request')
    request_id=str(uuid.uuid4());before=toolchain_id();limit=524288
    payload=(canonical({'protocol':1,'requestId':request_id,'recordId':record_id,'certificate':certificate})+'\n').encode()
    if len(payload)>limit:raise ValueError('augment_input_budget')
    command=sandbox_command()+[str(JAVA_HOME/'bin/java'),'-Xmx512m','-Xss512k','-XX:+UseSerialGC',
             '-XX:ActiveProcessorCount=2','-XX:MaxMetaspaceSize=128m','-XX:CompressedClassSpaceSize=64m',
             '-XX:ReservedCodeCacheSize=48m','-Djava.awt.headless=true','-Dfile.encoding=UTF-8','-Djava.io.tmpdir=/tmp',
             '-cp','/app/classes:/app/dependency/*:/app/solver.jar','dev.allow.corpus.CorpusAugmentMain']
    work=RUNTIME/'worker';work.mkdir(mode=0o700,parents=True,exist_ok=True)
    with tempfile.TemporaryFile(dir=work) as output:
        process=subprocess.run(command,input=payload,stdout=output,stderr=subprocess.DEVNULL,timeout=33,env={})
        if process.returncode:raise RuntimeError('augment_worker_failed')
        output.seek(0);raw=output.read(limit+1)
    if len(raw)>limit or raw.count(b'\n')!=1 or not raw.endswith(b'\n'):raise ValueError('augment_response_framing')
    if toolchain_id()!=before:raise ValueError('augment_build_changed')
    response=json.loads(raw)
    if response.get('protocol')!=1 or response.get('requestId')!=request_id or response.get('recordId')!=record_id:
        raise ValueError('augment_response_identity')
    if response.get('status')!='CHECKED' or not isinstance(response.get('variants'),list) or not response['variants']:
        raise ValueError('augment_unavailable')
    return response['variants'],before
