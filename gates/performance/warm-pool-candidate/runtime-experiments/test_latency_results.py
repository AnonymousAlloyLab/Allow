"""Adversarial verifier tests; synthetic evidence is not runtime evidence."""
import base64
import copy
import json
import hashlib
import tempfile
from pathlib import Path
import uuid
import unittest
from unittest.mock import patch
import latency_results as c

class Tests(unittest.TestCase):
    def setUp(self):
        self.row = dict(startNs=100,endNs=200,durationNs=100,capacityAcquiredNs=110,callStartNs=120,callEndNs=150,serializedNs=160,publicationEndNs=170,capacityReleasedNs=190,previousEndToAdmissionGapNs=None,cycleStartNs=100,cycleDurationNs=100,conditionStartNs=None,conditionEndNs=None,conditionDurationNs=None,initializationStartNs=None,initializationEndNs=None,teardownStartNs=None,teardownEndNs=None)
        self.cpu = {'cpu': {}, 'timing': dict(measurementStartNs=90,measurementEndNs=210,teardownStartNs=220,teardownEndNs=240)}
        for name, t, n in [('beforeMeasured',80,10),('afterMeasured',215,20),('afterTeardown',250,30)]:
            self.cpu['cpu'][name] = {'observedNs':t,'raw':f'usage_usec {n}\nuser_usec {n}\nsystem_usec {n}\n'}
        self.pool='11111111-1111-4111-8111-111111111111'; self.worker='22222222-2222-4222-8222-222222222222'
        self.group=dict(poolNonce=self.pool,workerNonce=self.worker,slot=0,generation=1,group=f'pool-{self.pool}/slot-0-g1',device=1,inode=2,phase='RELEASED',attempted=True,directChildReaped=True,pidStartAbsent=True,exitCode=0,pid=12345,startTicks='123',terminalCounters={'cgroup.events':'populated 0\n','memory.peak':'10','memory.events':'oom 0\noom_kill 0\noom_group_kill 0\n','pids.peak':'1','pids.events':'max 0\n','cpu.stat':'usage_usec 1\n'})
    def reject(self,fn,*args):
        with self.assertRaises((ValueError,AssertionError,KeyError,TypeError)): fn(*args)
    def test_ranks_and_zero(self):
        a=c.statistics(list(range(1,101))); self.assertEqual((a['p50_ns'],a['p95_ns'],a['p99_ns']),(50,95,99))
        a=c.statistics(list(range(20))); self.assertEqual((a['p50_ns'],a['p95_ns'],a['p99_ns']),(9,18,19))
        self.assertEqual(c.statistics([0]*20)['p99_ns'],0)
        for x in ([],[True],[-1],[1.0]): self.reject(c.statistics,x)
    def test_timing_and_ready(self):
        c.row_timing(self.row,None,'POOL_SERIAL')
        for k,v in [('durationNs',99),('capacityAcquiredNs',99),('callStartNs',109),('serializedNs',149),('publicationEndNs',159),('capacityReleasedNs',169),('conditionStartNs',100)]:
            row=copy.deepcopy(self.row); row[k]=v
            with self.subTest(field=k): self.reject(c.row_timing,row,None,'POOL_SERIAL')
        row=copy.deepcopy(self.row); row.update(cycleStartNs=90,cycleDurationNs=110,conditionStartNs=90,conditionEndNs=90,conditionDurationNs=0)
        c.row_timing(row,None,'POOL_READY'); row['conditionDurationNs']=1; self.reject(c.row_timing,row,None,'POOL_READY')
        self.reject(c.row_timing,self.row,None,'FRESH')
    def test_cycle_duration_exact(self):
        row=copy.deepcopy(self.row); row['cycleDurationNs']+=1; self.reject(c.row_timing,row,None,'POOL_SERIAL')
    def test_gap_exact(self):
        row=copy.deepcopy(self.row); row['previousEndToAdmissionGapNs']=5; c.row_timing(row,{'endNs':95},'POOL_SERIAL')
        row['previousEndToAdmissionGapNs']=4; self.reject(c.row_timing,row,{'endNs':95},'POOL_SERIAL'); self.reject(c.row_timing,row,None,'POOL_SERIAL')
    def test_cpu_tail(self):
        c.cpu_metrics(self.cpu,[self.row],0)
        report=copy.deepcopy(self.cpu); report['cpu']['afterMeasured']['observedNs']=230; self.reject(c.cpu_metrics,report,[self.row],0)
        report=copy.deepcopy(self.cpu); report['cpu']['afterTeardown']['raw']='usage_usec 1\nuser_usec 1\nsystem_usec 1\n'; self.reject(c.cpu_metrics,report,[self.row],0)
    def test_terminals(self):
        with patch.object(c,'same_process',return_value=False):
            c.terminal_groups([self.group],{'rootDevice':1})
            for k,v in [('group','missing'),('directChildReaped',False),('pidStartAbsent',False),('phase','UNKNOWN')]:
                g=copy.deepcopy(self.group); g[k]=v
                with self.subTest(field=k): self.reject(c.terminal_groups,[g],{'rootDevice':1})
            for k,v in [('cgroup.events','populated 1\n'),('memory.events','oom 1\noom_kill 0\noom_group_kill 0\n'),('pids.events','max 1\n'),('cpu.stat','other 1\n')]:
                g=copy.deepcopy(self.group); g['terminalCounters'][k]=v
                with self.subTest(counter=k): self.reject(c.terminal_groups,[g],{'rootDevice':1})
            self.reject(c.terminal_groups,[self.group,self.group],{'rootDevice':1})
        with patch.object(c,'same_process',return_value=True): self.reject(c.terminal_groups,[self.group],{'rootDevice':1})
    def test_identity_reuse(self):
        row={'freshRecovery':{'workerPid':123,'workerStartTicks':'456'}}; self.reject(c.inventory,[row,copy.deepcopy(row)],'FRESH',{},[])
    def test_response(self):
        value={'protocol':1,'requestId':self.pool,'status':'VALIDATED','data':{}}; raw=json.dumps(value,separators=(',',':')).encode()
        row={'responseBase64':base64.b64encode(raw).decode(),'responseBytes':len(raw),'requestNonce':self.pool}; self.assertEqual(c.response(row),value)
        for k,v in [('responseBase64','!'),('responseBytes',len(raw)+1),('requestNonce',self.worker),('requestNonce','invalid')]:
            bad=copy.deepcopy(row); bad[k]=v
            with self.subTest(field=k): self.reject(c.response,bad)
        raw=b'{"protocol":1,"protocol":1}'; bad=dict(row,responseBase64=base64.b64encode(raw).decode(),responseBytes=len(raw)); self.reject(c.response,bad)
    def test_source_and_class_rejected(self):
        value={'requestId':self.pool,'status':'VALIDATED','data':{'mode':'BLOCK_SUPPORTED','module':{'nodes':[{}]*500},'source':'correct','sourceHash':'hash'}}
        fixture={}; expected={'nodes':500,'source':'correct','source_sha256':'hash'}
        with patch.object(c.compare_responses,'check_response'):
            c.check_response(value,fixture,expected)
            for field, wrong in [('source','altered'),('sourceHash','wrong'),('mode','TEXT_ONLY')]:
                bad=copy.deepcopy(value); bad['data'][field]=wrong
                with self.subTest(field=field): self.reject(c.check_response,bad,fixture,expected)
            bad=copy.deepcopy(value); bad['data']['module']['nodes'].pop(); self.reject(c.check_response,bad,fixture,expected)

    def test_full_positive_and_omitted_rows(self):
        # Structurally valid synthetic output; not a claim about JVM worker output.
        fixture=json.loads((Path(__file__).parent/'latency-fixture.json').read_text())
        expected=json.loads((Path(__file__).parent/'latency-expected.json').read_text())
        definitions=c.compare_responses.definitions(fixture['candidate']['module'])
        mapping={ident:'server:'+ident[6:] for _,_,ident in definitions}
        def convert(value):
            if isinstance(value,str): return mapping.get(value,value)
            if isinstance(value,list): return [convert(x) for x in value]
            if isinstance(value,dict): return {k:convert(v) for k,v in value.items()}
            return value
        data=dict(mode='BLOCK_SUPPORTED',source=expected['source'],sourceHash=expected['source_sha256'],module=convert(fixture['candidate']['module']),occurrences=[],trivia=[],analysisDescriptors=[],diagnostics=[],idRemapping=mapping)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); evidence=root/'evidence'; evidence.mkdir()
            (root/'.gate').mkdir(); (root/'.runtime/warm-pool').mkdir(parents=True)
            (root/'gates/document').mkdir(parents=True); (root/'backend/target/classes/dev/allow/document').mkdir(parents=True)
            def write(path,value):
                path.write_text(json.dumps(value)); path.chmod(0o600)
            (root/'gates/document/headless-preview-fixture.json').write_text('synthetic input')
            (root/'backend/target/classes/dev/allow/document/ModulePrinter.class').write_text('synthetic class')
            expected['headless_fixture_sha256']=c.digest(root/'gates/document/headless-preview-fixture.json')
            expected['printer_class_sha256']=c.digest(root/'backend/target/classes/dev/allow/document/ModulePrinter.class')
            write(root/'.gate/latency-fixture.json',fixture); write(root/'.gate/latency-expected.json',expected)
            write(root/'.runtime/warm-pool/config.json',{'cgroupRoot':'/synthetic','rootDevice':1})
            plan=dict(schema=1,profile='FRESH',mode='MEASURED',contractSha256=c.CONTRACT,warmups=20,measured=100,cgroupRoot='/synthetic',cpuStat='/synthetic/cpu.stat',fixture=str(root/'.gate/latency-fixture.json'),fixtureSha256=c.digest(root/'.gate/latency-fixture.json'),variantId='synthetic')
            rows=[]
            for i in range(120):
                nonce=str(uuid.UUID(int=(4 << 76) | (2 << 62) | (i+1)))
                value=dict(protocol=1,requestId=nonce,status='VALIDATED',data=data)
                raw=json.dumps(value,separators=(',',':')).encode(); row=copy.deepcopy(self.row)
                delta=i*200
                for key in ('startNs','endNs','capacityAcquiredNs','callStartNs','callEndNs','serializedNs','capacityReleasedNs','cycleStartNs'): row[key]+=delta
                row.update(index=i,phase='WARMUP' if i<20 else 'MEASURED',outcome='SUCCESS',failure=None,publicationEndNs=None,requestNonce=nonce,responseBase64=base64.b64encode(raw).decode(),responseBytes=len(raw),admission=None,consumed=None,freshRecovery={'noWorkerStarted':False,'workerPid':10000+i,'workerStartTicks':str(i+1)},previousEndToAdmissionGapNs=None if i==0 else 100)
                rows.append(row)
            report=dict(schema=1,status='COMPLETE',failure=None,notExecuted=[],variantId=plan['variantId'],profile='FRESH',mode='MEASURED',contractSha256=c.CONTRACT,fixtureSha256=plan['fixtureSha256'],buildSha256='build',contextBoundary=c.CONTEXT,expectedWarmups=20,expectedMeasured=100,rows=rows,generations=[],cleanup={'poolClosed':True,'ledgerClosed':True,'remainingReservations':0},cpu={},timing={'measurementStartNs':4090,'measurementEndNs':24110,'teardownStartNs':24130,'teardownEndNs':24140})
            for name,t,n in [('beforeMeasured',4080,10),('afterMeasured',24120,20),('afterTeardown',24150,30)]: report['cpu'][name]={'observedNs':t,'raw':f'usage_usec {n}\nuser_usec {n}\nsystem_usec {n}\n'}
            oracle=dict(protocol=1,requestId=str(uuid.uuid4()),status='VALIDATED',data=data)
            manifest={'build_identity':{'value':'build'}}
            write(evidence/'latency-java.json',report)
            with patch.object(c,'same_process',return_value=False):
                result=c.verify_variant(root,evidence,manifest,plan,fixture,oracle)
                self.assertEqual(result['attempts_checked'],120); self.assertEqual(result['metrics']['latency']['p95_ns'],100)
                for index in (0,20):
                    bad=copy.deepcopy(report); bad['rows'].pop(index); write(evidence/'latency-java.json',bad)
                    self.reject(c.verify_variant,root,evidence,manifest,plan,fixture,oracle)

    def test_pair_descriptive(self):
        def variant(profile,n): return {'profile':profile,'status':'PASS','metrics':{'latency':dict(p50_ns=n,p95_ns=n,p99_ns=n,max_ns=n)}}
        result=c.paired_metrics(variant('FRESH',100),variant('POOL_SERIAL',120)); self.assertEqual(result['p95_ns']['pool_minus_fresh'],20); self.assertEqual(result['p95_ns']['reduction_percent'],-20); self.assertNotIn('selection',result)
        self.reject(c.paired_metrics,variant('POOL_SERIAL',1),variant('FRESH',1))

if __name__=='__main__': unittest.main()
