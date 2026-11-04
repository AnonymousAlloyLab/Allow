#!/usr/bin/env python3
"""Bound staged test evidence to exact source/test inputs; pending plan checks block."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'tests'))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.rows=[]
    def addSuccess(self,test):
        super().addSuccess(test)
        self.rows.append({'test':test.id(),'status':'PASS'})
    def addSkip(self,test,reason):
        super().addSkip(test,reason)
        self.rows.append({'test':test.id(),'status':'UNRESOLVED','reason':reason})
    def addFailure(self,test,error):
        super().addFailure(test,error)
        self.rows.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(error,test)})
    def addError(self,test,error):
        super().addError(test,error)
        self.rows.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(error,test)})


def main():
    if len(sys.argv)!=2 or not sys.argv[1].replace('-','').replace('_','').isalnum():raise ValueError('run id')
    out=HERE/'runtime-runs'/sys.argv[1]
    out.mkdir(parents=True,exist_ok=False)
    inputs=sorted([*HERE.glob('allow_retrieval/*.py'),*HERE.glob('tests/*.py'),Path(__file__),
        HERE.parent/'runtime-test-plan.json',HERE.parent/'contract.json',HERE.parent/'contract.md',
        HERE.parent/'formal-runs/final-287-v2/report.json'])
    entries=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}for p in inputs]
    manifest={'files':entries}
    root_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    save(out/'manifest.json',manifest)
    for source in inputs:
        target=out/'inputs'/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    with(out/'tests.log').open('w')as stream:
        suite=unittest.defaultTestLoader.discover(str(HERE/'tests'))
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordedResult).run(suite)
    changed=[row['path']for row in entries if sha(ROOT/row['path'])!=row['sha256']or sha(out/'inputs'/row['path'])!=row['sha256']]
    plan=json.loads((HERE.parent/'runtime-test-plan.json').read_text())
    matrix=[]
    for obligation in plan['tests']:
        matches=[row for row in result.rows if'.test_'+obligation['id']+'_'in row['test']]
        matrix.append({'id':obligation['id'],'name':obligation['name'],'status':matches[0]['status']if len(matches)==1 else'UNRESOLVED','tests':matches})
    pending=[row['id']for row in matrix if row['status']!='PASS']
    status='BLOCKED'if changed or pending or not result.wasSuccessful()else'PASS'
    report={'scope':'staged runtime tests only; no production/database or benchmark promotion',
        'status':status,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'input_root_sha256':root_hash,
        'tests_run':result.testsRun,'passed':sum(row['status']=='PASS'for row in result.rows),'failures':len(result.failures),'errors':len(result.errors),
        'unresolved':len(result.skipped),'changed_inputs':changed,'matrix':matrix,'pending_plan_checks':pending,
        'legacy_wire':{'expected':39,'passed':sum('test_sql_proxy.'in row['test']and row['status']=='PASS'for row in result.rows)},
        'legacy_guard':{'expected':7,'passed':sum('test_sql_guard_regressions.'in row['test']and row['status']=='PASS'for row in result.rows)},
        'legacy_real_postgresql':{'expected':13,'status':'PENDING_AUTHORIZED_PROMOTION'},
        'shared_host_limit':'Parser tests shared host with active baseline; timings are capability evidence only, not comparative performance.',
        'results':result.rows}
    save(out/'report.json',report)
    if(HERE/'resource-probe.json').exists():shutil.copyfile(HERE/'resource-probe.json',out/'resource-probe.json')
    print(json.dumps({key:report[key]for key in['status','input_root_sha256','tests_run','passed','failures','errors','unresolved','pending_plan_checks','changed_inputs']},indent=2))
    return 1 if changed or not result.wasSuccessful()else 0


if __name__=='__main__':raise SystemExit(main())
