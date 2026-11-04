"""Download only public pinned model assets; never accepts corpus input."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

REVISION='f52bf8ec8c7124536f0efb74aca902b2995e5bcd'
EXPECTED='157f97ef1957d34f52efa26f8031371bf9043acc45460cec7ebe94631ac0e96b'
FILES=('model.onnx','tokenizer.json','config.json','special_tokens_map.json','tokenizer_config.json','vocab.txt')

def bootstrap(destination):
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    hashes={}
    expected_lock=json.loads((Path(__file__).parent/'model-lock.json').read_text())
    for name in FILES:
        target=root/name
        if not target.exists():
            temporary=root/(name+'.part')
            with urllib.request.urlopen(f'https://huggingface.co/intfloat/e5-base-v2/resolve/{REVISION}/onnx/{name}') as response, temporary.open('wb') as output:
                while chunk:=response.read(1024*1024): output.write(chunk)
            temporary.replace(target)
        hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
        if hashes[name]!=expected_lock['files'][name]: raise ValueError('unapproved_model_file_hash:'+name)
    # All official files locked after first provision; subsequent encoder construction checks every byte.
    lock={'model_id':'intfloat/e5-base-v2','revision':REVISION,'license':'MIT','files':hashes}
    old=root/'model-lock.json'
    if old.exists() and json.loads(old.read_text())!=lock: raise ValueError('model_lock_changed')
    old.write_text(json.dumps(lock,indent=2)+'\n')
    import onnx
    model=onnx.load(str(root/'model.onnx'),load_external_data=False)
    onnx.checker.check_model(model)
    if model.ir_version > 10 or any(x.domain not in ('', 'ai.onnx') or x.version > 21 or x.version < 7 for x in model.opset_import):
        raise ValueError('unsupported_opset_or_custom_domain')
    if any(x.domain not in ('','ai.onnx') for x in model.graph.node): raise ValueError('custom_operator_domain')
    inspection={'custom_operator_libraries':False,'ir_version':model.ir_version,'opsets':{x.domain:x.version for x in model.opset_import},'operators':sorted({x.domain+':'+x.op_type for x in model.graph.node})}
    if any(x.data_location==onnx.TensorProto.EXTERNAL for x in model.graph.initializer): raise ValueError('external_model_data_disallowed')
    (root/'onnx-inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
    return lock

def provision_runtime():
    """Provision only the workspace-owned isolated CPython3.12 runtime from hashes."""
    import subprocess
    import sys
    import time
    workspace=Path(__file__).resolve().parent.parent
    venv=workspace/'.tools'/'retrieval-venv'
    system='/usr/bin/python3'
    version=json.loads(subprocess.check_output([system,'-c','import json,sys;print(json.dumps(list(sys.version_info[:2])))']))
    if version != [3,12]: raise RuntimeError('CPython3.12_required_at_/usr/bin/python3')
    if venv.is_symlink(): raise RuntimeError('runtime_symlink_rejected')
    recreate=not (venv/'pyvenv.cfg').exists()
    if not recreate:
        actual=json.loads(subprocess.check_output([str(venv/'bin/python'),'-c','import json,sys;print(json.dumps(list(sys.version_info[:2])))']))
        recreate=actual != version or 'include-system-site-packages = false' not in (venv/'pyvenv.cfg').read_text()
    if recreate:
        if venv.exists(): venv.rename(venv.with_name('retrieval-venv.previous-'+str(time.time_ns())))
        subprocess.run([system,'-m','venv','--without-pip',str(venv)],check=True)
    python=str(venv/'bin/python')
    # Ubuntu may omit ensurepip. Seed only the exact hash-locked public pip wheel.
    if subprocess.run([python,'-m','pip','--version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        lock=(Path(__file__).parent/'requirements-ml.lock').read_text().splitlines()
        line=next(x for x in lock if x.startswith('pip=='))
        pip_version=line.split()[0].split('==')[1]
        expected=line.split('--hash=sha256:')[1]
        metadata=json.load(urllib.request.urlopen('https://pypi.org/pypi/pip/'+pip_version+'/json'))
        asset=next(x for x in metadata['urls'] if x['filename'].endswith('.whl') and x['digests']['sha256']==expected)
        wheel=venv/asset['filename']
        wheel.write_bytes(urllib.request.urlopen(asset['url']).read())
        if hashlib.sha256(wheel.read_bytes()).hexdigest()!=expected: raise ValueError('pip_seed_hash')
        env={**os.environ,'PYTHONPATH':str(wheel)}
        subprocess.run([python,'-m','pip','install','--no-deps','--no-index',str(wheel)],env=env,check=True)
    subprocess.run([python,'-m','pip','install','--require-hashes','-r',str(Path(__file__).parent/'requirements-ml.lock')],check=True)
    subprocess.run([python,'-m','pip','check'],check=True)
    return python


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('model_dir',nargs='?',default='.tools/retrieval/models')
    parser.add_argument('--provision-runtime',action='store_true')
    args=parser.parse_args()
    if args.provision_runtime:
        python=provision_runtime()
        os.execv(python,[python,str(Path(__file__).resolve()),args.model_dir])
    print(json.dumps(bootstrap(args.model_dir),indent=2))
