"""Reject the specific false-pass and registration cases found during review."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from make_fixtures import frame, encoded
from run_semantic import check_fixtures, oracle
from test_compare_responses import specimen
import base64


def boundary():
    """Return an explicit oversize denial whose complete input identity is frozen."""
    item = {'bytes':2097152,'sha256':'a'*64,'expectedProbeReject':True}
    value = {'profile':'DEFAULT','inputSha256':item['sha256'],'inputBytes':item['bytes'],
             'outcome':'INPUT_REJECTED','noWorkerStarted':True}
    return {'exit_code':0,'record':value,'timed_out':False},item


class RunnerTests(unittest.TestCase):
    """Keep infrastructure errors distinct from the finite input-boundary oracle."""

    def test_explicit_size_rejection(self):
        """Only an identity-bound prelaunch rejection satisfies the oversize case."""
        result,item = boundary()
        self.assertIsNone(oracle(result,item,{},'F0','build'))

    def test_generic_exit_two_is_not_size_rejection(self):
        """A missing class or unavailable input cannot impersonate a boundary pass."""
        _,item = boundary()
        with self.assertRaises(AssertionError):
            oracle({'exit_code':2,'record':None},item,{},'F0','build')

    def test_wrong_profile_identity_and_started_child(self):
        """Correct status does not excuse wrong profile, bytes, digest or worker launch."""
        for key,value in (('profile','DOCUMENT_ADVISORY_TIER1'),('inputBytes',True),('inputSha256','wrong'),
                          ('noWorkerStarted',False),('workerPid',123),('buildIdentity','unexpected')):
            with self.subTest(key=key):
                result,item = boundary()
                result['record'][key]=value
                with self.assertRaises(AssertionError): oracle(result,item,{},'F0','build')

    def test_timeout_cannot_pass(self):
        """Cleanup uncertainty stops comparison even if a response file was written."""
        result,item = boundary()
        result['timed_out']=True
        with self.assertRaises(AssertionError): oracle(result,item,{},'F0','build')

    def test_kernel_tick_string_and_absence(self):
        """The Java kernel reader emits decimal strings, which stay bound through absence."""
        request,response,_ = specimen()
        raw = encoded(response)+b'\n'
        item = {'bytes':100,'sha256':'a'*64,'expectedStatus':'VALIDATED'}
        value = {'profile':'DEFAULT','inputSha256':'a'*64,'inputBytes':100,'buildIdentity':'build',
                 'noWorkerStarted':False,'outcome':'COMPLETE_RESPONSE','workerPid':123,'workerStartTicks':'456',
                 'reaped':True,'workerExitCode':0,'requestIdentityMatches':True,
                 'responseBase64':base64.b64encode(raw).decode(),'responseBytes':len(raw),
                 'responseSha256':hashlib.sha256(raw).hexdigest()}
        for key in ('constructorNanos','launchNanos','exchangeNanos','reapNanos','totalNanos'): value[key]=1
        result = {'exit_code':0,'record':value,'timed_out':False}
        with patch('run_semantic.process_identity',return_value=None):
            self.assertEqual(oracle(result,item,request,'F0','build'),response)
        with patch('run_semantic.process_identity',return_value={'pid':123,'start_ticks':'456'}):
            with self.assertRaises(AssertionError): oracle(result,item,request,'F0','build')
        for bad in (456,True,'0','0456','x'):
            value['workerStartTicks']=bad
            with self.assertRaises(AssertionError): oracle(result,item,request,'F0','build')

    def test_empty_duplicate_or_unregistered_corpus(self):
        """No-case, duplicate and extra-file corpora cannot yield a finite pass."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'manifest.json').write_text('{}')
            with self.assertRaises(AssertionError): check_fixtures(root,{'fixtures':[]})
            raw = encoded(frame('one',{'mode':'SOURCE','source':'sig A {}'}))
            (root/'one.json').write_bytes(raw)
            row = {'name':'one','path':'one.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            check_fixtures(root,{'fixtures':[row]})
            with self.assertRaises(AssertionError): check_fixtures(root,{'fixtures':[row,row]})
            (root/'unregistered.json').write_text('{}')
            with self.assertRaises(AssertionError): check_fixtures(root,{'fixtures':[row]})

    def test_mutated_fixture_is_rejected(self):
        """An edited fixture fails even when its JSON and byte count remain valid."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'manifest.json').write_text('{}')
            (root/'one.json').write_bytes(b'{}')
            row = {'name':'one','path':'one.json','bytes':2,'sha256':hashlib.sha256(b'[]').hexdigest()}
            with self.assertRaises(AssertionError): check_fixtures(root,{'fixtures':[row]})


if __name__ == '__main__':
    unittest.main()
