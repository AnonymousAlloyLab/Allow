"""Derive document subset evidence from actual full186 test records; no invented deltas."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report_path=ROOT/'gates/document/inherited-runtime-tests.json'
log_path=report_path.with_suffix('.log')
report=json.loads(report_path.read_text());log=log_path.read_text()
assert report['status']=='PASS' and report['tests']==186
assert not any(report[k]for k in['failures','errors','skipped']) and report['source_unchanged']
files={row['path']:row['sha256']for row in report['files']}
headers=list(re.finditer(r'(?m)^(test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\)',log))
assert len(headers)==186
blocks={}
for index,header in enumerate(headers):
 block=log[header.start():headers[index+1].start()if index+1<len(headers)else len(log)]
 assert '... ok' in block
 assert header.group(2)not in blocks
 blocks[header.group(2)]=block
source=ROOT/'retrieval/tests/test_documents.py'
assert sha(source)==files['retrieval/tests/test_documents.py']
names=[]
for cls in ast.parse(source.read_text()).body:
 if isinstance(cls,ast.ClassDef):
  for method in cls.body:
   if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))and method.name.startswith('test_'):
    names.append('test_documents.'+cls.name+'.'+method.name)
assert len(names)==22 and all(name in blocks for name in names)
selected={name:digest for name,digest in files.items()if name.startswith(('retrieval/allow_documents/','retrieval/allow_retrieval/sql'))or name in['retrieval/tests/test_documents.py','config/sqlean-parser-lock.json','db/document/interface.json','db/document/schema-catalog.sql']}
assert all(sha(ROOT/name)==digest for name,digest in selected.items())
common={'classification':'EXECUTED_FULL_SUITE_SUBSET_NOT_SEPARATE_TIMING_OR_COUNTER_RUN','timestamp_utc':datetime.now(timezone.utc).isoformat(),
 'failures':0,'errors':0,'skipped':0,'source_unchanged':True,
 'evidence':{'full_suite_report':str(report_path.relative_to(ROOT)),'full_suite_report_sha256':sha(report_path),'full_suite_log':str(log_path.relative_to(ROOT)),'full_suite_log_sha256':sha(log_path),'full_suite_input_root_sha256':report['input_root_sha256'],'full_suite_tests':186,'binding_verifier_sha256':sha(Path(__file__))},
 'subset_timing':'NOT_SEPARATELY_MEASURED','subset_proxy_counter_attribution':'NOT_MEASURED',
 'limitations':['Document subset derived from actual full186-test execution, not a newly timed isolated22-test run.','No old timing or counter delta is reused or attributed to this subset.','Some wire/identity tests reject before database access; actual SQL routing has separate SQL52/client evidence.','No PostgreSQL restart; documentSQL tests use isolated random scopes.']}
null='test_documents.DocumentSQLTests.test_reaped_worker_without_captured_start_ticks_requires_absent_pid'
assert null in names and null in blocks
paths=[ROOT/'db/document/runtime-evidence.json',ROOT/'gates/document/store-null-start-recovery-report.json']
for path in paths:
 if path.exists():
  target=OUT/'pre-refresh'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
document=dict(common,status='PASS',tests=22,source_sha256=selected,tested_symbols=names)
null_report=dict(common,status='PASS',tests=1,input_sha256=selected,tested_symbols=[null],
 checks=['Actual live PID with null captured start rejected.','Owned child waited/reaped and absent PID with null captured start accepted.','Nonce rotated; stale old nonce rejected; recovered generation finalized through actual proxy.'],
 boundary='Actual registered test body and full-suite log bind these checks. Trusted supervisor reaps owned process; no expiry or PID-reuse authority is inferred.')
for path,value in zip(paths,[document,null_report]):path.write_text(json.dumps(value,indent=2)+'\n')
(OUT/'document-subset-tests.log').write_text('\n'.join(blocks[name].rstrip()for name in names)+'\n')
(OUT/'null-start-subset-test.log').write_text(blocks[null])
print(json.dumps({'documents':22,'null_start':1,'status':'PASS','full_suite_tests':186,'no_subset_timing_or_counter_claim':True}))
