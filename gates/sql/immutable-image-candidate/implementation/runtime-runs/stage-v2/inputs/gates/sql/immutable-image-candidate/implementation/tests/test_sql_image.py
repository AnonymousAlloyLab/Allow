"""Finite frozen IM01-IM56 plan checks. DB/benchmark obligations remain pending.

Tiny synthetic images exercise Linux fd/seal/lifetime surfaces; real parser probes
use the actual pinned SQLeanParser image. Neither fixture is a database client.
"""
from collections import Counter, OrderedDict
from dataclasses import FrozenInstanceError, replace
import errno
import fcntl
import hashlib
import io
import json
import mmap
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from allow_retrieval import sql_image as image_module
from allow_retrieval import sql_image_init as init_module
from allow_retrieval.sql_guard import ParserGate, SQLGuardError
from allow_retrieval.sql_image import SealedImage, ParserFailure, Reservation
from allow_retrieval.sql_image_config import ConfigSnapshot, ImageError, workspace_root

ROOT = workspace_root()
HERE = Path(__file__).resolve().parents[1]


def fd_count():
    return len(list(Path('/proc/self/fd').iterdir()))


def wait_for(predicate, seconds=2):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.002)
    raise AssertionError('bounded fixture wait expired')


def rollup(pid):
    result = {}
    for line in Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].isdigit() and parts[2] == 'kB':
            result[parts[0].rstrip(':')] = int(parts[1])*1024
    return result


class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads((ROOT/'config/sqlean-parser-lock.json').read_text())
        cls.gate = ParserGate()
        cls.config = cls.gate._config
        with cls.gate._image.reserve(cls.config) as owner:
            cls.raw_report = cls.gate._image.run(owner, b'SELECT 1', cls.config)

    @classmethod
    def tearDownClass(cls):
        cls.gate.close()

    def tiny(self, data=b'image'):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name)/'source'
        source.write_bytes(data)
        return source, len(data), hashlib.sha256(data).hexdigest()

    def small_image(self):
        source, size, digest = self.tiny()
        fd = init_module.build_image(source, size, digest)
        config = replace(self.config, expected_size=size)
        with patch.object(image_module, 'initialize_image', return_value=fd):
            image = SealedImage(source, config)
        def cleanup():
            with image.lock:
                image.close_locked()
            image.finish_close()
        self.addCleanup(cleanup)
        return image, config

    def fake_gate(self, image, config):
        gate = ParserGate.__new__(ParserGate)
        gate._config = config
        gate._image = image
        gate._cache = OrderedDict()
        gate._cache_bytes = 0
        gate._reasons = Counter()
        return gate

    def test_IM01_initialize_pinned(self):
        with self.gate._image.lock:
            self.gate._image.check_locked(self.config)
            metadata = os.fstat(self.gate._image._descriptor)
        self.assertEqual(metadata.st_size, self.config.expected_size)
        digest = hashlib.sha256()
        with self.gate._image.reserve(self.config) as owner:
            offset = 0
            while chunk := os.pread(owner.descriptor, 1048576, offset):
                digest.update(chunk)
                offset += len(chunk)
        self.assertEqual(digest.hexdigest(), self.config.binary_sha256)

    def test_IM02_initialize_mismatch(self):
        source, size, _ = self.tiny()
        before = fd_count()
        with self.assertRaises(ValueError):
            init_module.build_image(source, size, '0'*64)
        self.assertEqual(fd_count(), before)

    def test_IM03_copy_race(self):
        source, size, digest = self.tiny()
        original = os.read
        def changed(descriptor, count):
            if count > 1:
                source.write_bytes(b'X'*size)
            return original(descriptor, count)
        before = fd_count()
        with patch.object(init_module.os, 'read', side_effect=changed), self.assertRaises(ValueError):
            init_module.build_image(source, size, digest)
        self.assertEqual(fd_count(), before)

    def seal_denial(self, action):
        image, _ = self.small_image()
        with self.assertRaises(OSError) as failure:
            action(image._descriptor)
        self.assertEqual(failure.exception.errno, errno.EPERM)

    def test_IM04_seal_write(self):
        self.seal_denial(lambda fd:os.pwrite(fd,b'X',0))

    def test_IM05_seal_grow(self):
        self.seal_denial(lambda fd:os.ftruncate(fd,6))

    def test_IM06_seal_shrink(self):
        self.seal_denial(lambda fd:os.ftruncate(fd,4))

    def test_IM07_seal_mmap(self):
        self.seal_denial(lambda fd:mmap.mmap(fd,0,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE))

    def test_IM08_missing_seal(self):
        for missing in (fcntl.F_SEAL_WRITE,fcntl.F_SEAL_GROW,fcntl.F_SEAL_SHRINK,fcntl.F_SEAL_SEAL):
            image, config = self.small_image()
            fd = os.memfd_create('missing-seal',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING|init_module.MFD_EXEC)
            os.write(fd,b'image')
            fcntl.fcntl(fd,fcntl.F_ADD_SEALS,init_module.REQUIRED_SEALS & ~missing)
            os.close(image._descriptor)
            image._descriptor = fd
            metadata = os.fstat(fd)
            image._object = (metadata.st_dev,metadata.st_ino)
            with image.lock, self.assertRaises(ImageError):
                image.check_locked(config)

    def test_IM09_wrong_size(self):
        image, config = self.small_image()
        wrong = replace(config, expected_size=6)
        image.config = wrong
        with image.lock, self.assertRaises(ImageError):
            image.check_locked(wrong)

    def test_IM10_closed_fd(self):
        image, config = self.small_image()
        os.close(image._descriptor)
        with image.lock, self.assertRaises(ImageError):
            image.check_locked(config)
        # The externally corrupted descriptor was already closed; do not close it again.
        image._descriptor = None

    def test_IM11_reused_fd(self):
        image, config = self.small_image()
        number = image._descriptor
        replacement = os.memfd_create('replacement',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING|init_module.MFD_EXEC)
        os.write(replacement,b'image')
        fcntl.fcntl(replacement,fcntl.F_ADD_SEALS,init_module.REQUIRED_SEALS)
        os.dup2(replacement,number)
        os.close(replacement)
        with image.lock, self.assertRaises(ImageError):
            image.check_locked(config)

    def test_IM12_lifetime_race(self):
        image, config = self.small_image()
        checked = threading.Event()
        release = threading.Event()
        closed = threading.Event()
        def admission():
            with image.lock:
                image.check_locked(config)
                checked.set()
                release.wait(2)
        thread = threading.Thread(target=admission)
        thread.start()
        self.assertTrue(checked.wait(1))
        def close():
            with image.lock:image.close_locked()
            image.finish_close()
            closed.set()
        closer = threading.Thread(target=close)
        closer.start()
        self.assertFalse(closed.wait(.02))
        release.set()
        thread.join(2);closer.join(2)
        self.assertTrue(closed.is_set())
        with image.lock,self.assertRaises(ImageError):image.check_locked(config)

    def test_IM13_duplicate_failure(self):
        image, config = self.small_image()
        before = fd_count()
        with patch.object(image_module.os,'dup',side_effect=OSError(errno.EMFILE,'fixture')):
            with image.lock,self.assertRaises(ImageError):image.check_locked(config)
        self.assertEqual(fd_count(),before)
        self.assertEqual(image._state,'failed')

    def actual_process(self, record=False):
        with self.gate._image.reserve(self.config) as owner:
            process = subprocess.Popen([image_module.PRLIMIT,'--as=1073741824','--cpu=6','--core=0',
                '--fsize=16777216','--',f'/proc/self/fd/{owner.descriptor}','--max-transitions','1000000'],
                pass_fds=(owner.descriptor,),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,env=image_module.ENVIRONMENT)
            owner.process = process
            expected = os.fstat(owner.descriptor)
            def matches():
                if process.poll() is not None:return False
                try:actual=os.stat(f'/proc/{process.pid}/exe')
                except FileNotFoundError:return False
                return (actual.st_dev,actual.st_ino)==(expected.st_dev,expected.st_ino)
            wait_for(matches)
            if record:
                report = {'scope':'isolated staged parser, not active proxy','memfd_backing_bytes':self.config.expected_size,
                    'proxy_fixture_rollup_bytes':rollup(os.getpid()),'parser_rollup_bytes':rollup(process.pid),
                    'parser_limits':Path(f'/proc/{process.pid}/limits').read_text(),
                    'accounting':'Unmapped memfd backing pages are not all charged as parent RSS; backing bytes are additional system shmem. Child AS limit does not bound parent/system memory.'}
                (HERE/'resource-probe.json').write_text(json.dumps(report,indent=2)+'\n')
            output,_=process.communicate(b'SELECT 1',timeout=5)
            self.assertEqual(process.returncode,0)
            self.assertEqual(json.loads(output)['sql'],'SELECT 1')

    def test_IM14_child_inheritance(self):
        self.actual_process()

    def test_IM15_actual_executable(self):
        self.actual_process()

    def test_IM16_procfs_missing(self):
        image, config = self.small_image()
        with image.reserve(config) as owner:
            with patch.object(image_module.subprocess,'Popen',side_effect=FileNotFoundError('fixture'))as launch:
                with self.assertRaises(ImageError):image.run(owner,b'SELECT 1',config)
            self.assertEqual(launch.call_count,1)
            self.assertIn('/proc/self/fd/',str(launch.call_args.args[0]))

    def test_IM17_noexec_policy(self):
        source,size,digest=self.tiny()
        before=fd_count()
        with patch.object(init_module.os,'memfd_create',side_effect=PermissionError('fixture'))as create:
            with self.assertRaises(OSError):init_module.build_image(source,size,digest)
        self.assertEqual(create.call_count,1)
        self.assertEqual(fd_count(),before)

    def test_IM18_parser_success(self):
        self.assertIsNone(self.gate.validate(b'SELECT 18001'))
        for field,value in [('profile','bad'),('postgresqlCommit','bad'),('sourcePreservation','bad'),('sql','SELECT 2'),('evidence','bad')]:
            report=json.loads(self.raw_report);report[field]=value
            with self.subTest(field=field),self.assertRaises(SQLGuardError):
                self.gate._classify(b'SELECT 1','SELECT 1',json.dumps(report).encode()+b'\n',self.config)

    def test_IM19_parser_rejection(self):
        before=len(self.gate._cache)
        with self.assertRaises(SQLGuardError):self.gate.validate(b'SELECT FROM FROM')
        self.assertEqual(len(self.gate._cache),before)

    def test_IM20_parser_timeout(self):
        image,config=self.small_image()
        class Stalled:
            returncode=None
            def communicate(self,*args,**kwargs):raise subprocess.TimeoutExpired('fixture',.01)
            def poll(self):return self.returncode
            def kill(self):self.returncode=-9
            def wait(self,timeout):return self.returncode
        process=Stalled()
        ticks=iter([0,10])
        with image.reserve(config)as owner:
            with patch.object(image_module.subprocess,'Popen',return_value=process),patch.object(image_module.time,'monotonic',side_effect=lambda:next(ticks)):
                with self.assertRaises(ParserFailure):image.run(owner,b'SELECT 1',config)
        self.assertEqual(process.returncode,-9)
        self.assertEqual(image._slots_free,2)

    def test_IM21_parser_output(self):
        for raw in (b'{}',b'{}\n\n',b'not json\n',b'{"sql":1,"sql":2}\n'):
            with self.subTest(raw=raw),self.assertRaises((SQLGuardError,ValueError)):
                self.gate._classify(b'SELECT 1','SELECT 1',raw,self.config)
        image,config=self.small_image()
        class Oversized:
            returncode=0
            def communicate(self,*args,**kwargs):return None,None
            def poll(self):return 0
        output=io.BytesIO();output.seek(image_module.MAX_OUTPUT+1)
        with image.reserve(config)as owner,patch.object(image_module.subprocess,'Popen',return_value=Oversized()),patch.object(image_module.tempfile,'TemporaryFile',return_value=output):
            with self.assertRaises(ParserFailure):image.run(owner,b'SELECT 1',config)

    def test_IM22_exact_cache(self):
        with patch.object(self.gate,'_classify',wraps=self.gate._classify)as classify:
            self.gate.validate(b'SELECT 22001');self.gate.validate(b'SELECT 22001')
        self.assertEqual(classify.call_count,1)
        self.assertIn((self.config.digest,self.config.generation,b'SELECT 22001'),self.gate._cache)

    def test_IM23_changed_sql(self):
        with patch.object(self.gate,'_classify',wraps=self.gate._classify)as classify:
            self.gate.validate(b'SELECT 23001');self.gate.validate(b'SELECT 23001 ')
        self.assertEqual(classify.call_count,2)

    def test_IM24_changed_generation(self):
        image,config=self.small_image();gate=self.fake_gate(image,config)
        changed=replace(config,generation=config.generation+1,digest='new')
        image.config=changed
        with self.assertRaises(SQLGuardError):gate.validate(b'SELECT 1')
        self.assertEqual(len(gate._cache),0)

    def test_IM25_cache_provenance(self):
        decision=self.gate.validate(b'PREPARE cache_fixture AS SELECT 1')
        self.assertEqual(self.gate.validate(b'PREPARE cache_fixture AS SELECT 1'),decision)
        self.assertFalse(hasattr(self.gate,'statements'))
        self.assertFalse(hasattr(self.gate,'portals'))
        with self.assertRaises(FrozenInstanceError):decision.name=b'other'

    def test_IM26_cache_bounds(self):
        image,config=self.small_image();gate=self.fake_gate(image,config)
        with image.lock:
            for i in range(300):gate._cache_insert_locked((config.digest,config.generation,str(i).encode()),None)
            self.assertEqual(len(gate._cache),256)
            for i in range(6):gate._cache_insert_locked((config.digest,config.generation,bytes([i])*1048576),None)
        self.assertLessEqual(gate._cache_bytes,4194304)
        self.assertLessEqual(len(gate._cache),256)

    def test_IM27_disk_replacement_running(self):
        with tempfile.TemporaryDirectory()as directory:
            source=Path(directory)/'parser';shutil.copyfile(self.gate.binary,source)
            with ParserGate(source=source)as gate:
                gate.validate(b'SELECT 27001')
                source.unlink()
                source.write_bytes(b'changed')
                self.assertIsNone(gate.validate(b'SELECT 27001'))
                self.assertIsNone(gate.validate(b'SELECT 27002'))
                self.assertEqual(gate.info['disk_policy'],'restart-check-only')

    def test_IM28_disk_replacement_restart(self):
        source,_,_=self.tiny()
        with self.assertRaises(ImageError):ParserGate(source=source)

    def test_IM29_stopped_gate(self):
        image,config=self.small_image();gate=self.fake_gate(image,config)
        gate._cache_insert_locked((config.digest,config.generation,b'SELECT 1'),None)
        gate.close()
        self.assertEqual(len(gate._cache),0)
        self.assertEqual(gate.info['lifecycle'],'stopped')
        self.assertTrue(gate.info['shutdown_complete'])
        with self.assertRaises(SQLGuardError):gate.validate(b'SELECT 1')

    def test_IM30_resource_accounting(self):
        self.actual_process(record=True)
        report=json.loads((HERE/'resource-probe.json').read_text())
        self.assertEqual(report['memfd_backing_bytes'],136492600)
        self.assertIn('1073741824',report['parser_limits'])
        self.assertIn('Rss',report['parser_rollup_bytes'])
        self.assertIn('Pss_Shmem',report['proxy_fixture_rollup_bytes'])

    def test_IM31_all_existing(self):
        report=json.loads((HERE.parent/'formal-runs/final-287-v2/report.json').read_text())
        self.assertEqual(report['status'],'VERIFIED')
        self.assertEqual(report['claims']['passed'],287)
        self.skipTest('Full existing SQL integration/database suites await authorized promotion; this is unresolved, not PASS')

    def test_IM32_full_cli_benchmark(self):
        self.skipTest('Stable baseline and promoted candidate full CLI benchmark not yet available; unresolved, not PASS')

    def test_IM33_trusted_size_missing(self):
        for size in (0,-1,True,None,136492601):
            data=dict(self.lock);data['binary_size']=size
            with self.subTest(size=size),self.assertRaises(ImageError):ConfigSnapshot.from_mapping(data)
        # Missing lock size uses the independent reviewed compiled pin, not source stat.
        self.assertEqual(ConfigSnapshot.from_mapping(self.lock).expected_size,136492600)

    def test_IM34_source_nonregular(self):
        with tempfile.TemporaryDirectory()as directory:
            fifo=Path(directory)/'fifo';os.mkfifo(fifo)
            link=Path(directory)/'link';link.symlink_to(self.gate.binary)
            before=fd_count()
            for source in(fifo,Path(directory),link,Path('/dev/null')):
                with self.subTest(source=source),self.assertRaises((ValueError,OSError)):
                    init_module.build_image(source,5,'0'*64)
            self.assertEqual(fd_count(),before)

    def test_IM35_source_oversize(self):
        source,size,digest=self.tiny()
        with patch.object(init_module,'copy_exact')as copier,self.assertRaises(ValueError):
            init_module.build_image(source,size-1,digest)
        copier.assert_not_called()

    def test_IM36_source_growing(self):
        source,size,digest=self.tiny();original=os.read;calls=[]
        def read(descriptor,count):
            calls.append(count)
            if count==1:
                with source.open('ab')as writer:writer.write(b'excess')
            return original(descriptor,count)
        before=fd_count()
        with patch.object(init_module.os,'read',side_effect=read),self.assertRaises(ValueError):
            init_module.build_image(source,size,digest)
        self.assertEqual(calls,[size,1]);self.assertEqual(fd_count(),before)

    def test_IM37_source_truncated(self):
        source,size,digest=self.tiny();original=os.read
        def read(descriptor,count):
            source.write_bytes(b'')
            return original(descriptor,count)
        before=fd_count()
        with patch.object(init_module.os,'read',side_effect=read),self.assertRaises(ValueError):
            init_module.build_image(source,size,digest)
        self.assertEqual(fd_count(),before)

    def test_IM38_initializer_deadline(self):
        original=subprocess.Popen;children=[]
        def stalled(*args,**kwargs):
            process=original(['/bin/sleep','30'],pass_fds=kwargs['pass_fds'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            children.append(process)
            return process
        before=fd_count();start=time.monotonic()
        with patch.object(image_module.subprocess,'Popen',side_effect=stalled),self.assertRaises(ImageError):
            image_module.initialize_image(self.gate.binary,self.config)
        self.assertLess(time.monotonic()-start,7)
        self.assertEqual(fd_count(),before)
        self.assertTrue(all(child.poll()is not None for child in children))

    def test_IM39_initializer_transfer(self):
        import array
        image,config=self.small_image()
        for count in(0,2):
            parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
            try:
                controls=[]
                if count:controls=[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[image._descriptor]*count))]
                child.sendmsg([b'{}'],controls)
                before=fd_count()
                with self.assertRaises(ImageError):image_module.receive_image(parent,config)
                self.assertEqual(fd_count(),before)
            finally:parent.close();child.close()

    def test_IM40_source_short_write(self):
        source,size,digest=self.tiny();original=os.write
        with patch.object(init_module.os,'write',side_effect=lambda fd,data:original(fd,data[:1])):
            fd=init_module.build_image(source,size,digest)
            os.close(fd)
        before=fd_count()
        with patch.object(init_module.os,'write',return_value=0),self.assertRaises(ValueError):
            init_module.build_image(source,size,digest)
        self.assertEqual(fd_count(),before)

    def slot_fixture(self):
        image,config=self.small_image();release=threading.Event();threads=[];errors=[]
        def holder():
            try:
                with image.reserve(config):release.wait(3)
            except Exception as error:errors.append(error)
        for _ in range(2):
            thread=threading.Thread(target=holder);thread.start();threads.append(thread)
        wait_for(lambda:len(image._owners)==2)
        self.addCleanup(lambda:release.set())
        return image,config,release,threads,errors

    def test_IM41_slot_wait_no_fd(self):
        image,config,release,threads,errors=self.slot_fixture();before=fd_count();cancel=threading.Event();wait_errors=[]
        def waiter():
            try:
                with image.reserve(config,cancel):pass
            except Exception as error:wait_errors.append(error)
        waiting=threading.Thread(target=waiter);waiting.start()
        wait_for(lambda:image._waiters==1)
        self.assertEqual(fd_count(),before)
        self.assertEqual(len(image._owners),2)
        cancel.set();waiting.join(2)
        release.set()
        for thread in threads:thread.join(2)
        self.assertEqual(len(wait_errors),1);self.assertEqual(errors,[])
        self.assertEqual(image._slots_free,2)

    def test_IM42_hit_fd_cleanup(self):
        self.gate.validate(b'SELECT 42001');before=fd_count()
        for _ in range(200):self.gate.validate(b'SELECT 42001')
        self.assertEqual(fd_count(),before)

    def test_IM43_cancel_fd_cleanup(self):
        image,config=self.small_image();cancel=threading.Event();before=fd_count()
        cancel.set()
        with self.assertRaises(ParserFailure):
            with image.reserve(config,cancel):pass
        cancel.clear()
        with self.assertRaises(ParserFailure):
            with image.reserve(config,cancel)as owner:
                cancel.set();image.run(owner,b'SELECT 1',config,cancel)
        self.assertEqual(fd_count(),before);self.assertEqual(image._slots_free,2)

    def test_IM44_launch_failure_cleanup(self):
        image,config=self.small_image();before=fd_count()
        with patch.object(image_module.subprocess,'Popen',side_effect=OSError('fixture')):
            with self.assertRaises(ImageError):
                with image.reserve(config)as owner:image.run(owner,b'SELECT 1',config)
        self.assertEqual(fd_count(),before);self.assertEqual(image._slots_free,2)

    def test_IM45_shutdown_reservations(self):
        image,config,release,threads,errors=self.slot_fixture();wait_errors=[]
        def waiter():
            try:
                with image.reserve(config):pass
            except Exception as error:wait_errors.append(error)
        waiting=threading.Thread(target=waiter);waiting.start();wait_for(lambda:image._waiters==1)
        with image.lock:image.close_locked()
        waiting.join(2);self.assertEqual(len(wait_errors),1)
        release.set()
        for thread in threads:thread.join(2)
        image.finish_close();self.assertEqual(image._owners,set());self.assertEqual(image._waiters,0)
        self.assertEqual(image._slots_free,2)

    def test_IM46_numeric_fd_reuse(self):
        image,config=self.small_image()
        with image.reserve(config)as owner:
            expected=os.fstat(owner.descriptor)
            for _ in range(50):
                churn=os.open('/dev/null',os.O_RDONLY);self.assertNotEqual(churn,owner.descriptor);os.close(churn)
            actual=os.fstat(owner.descriptor)
        self.assertEqual((actual.st_dev,actual.st_ino),(expected.st_dev,expected.st_ino))

    def config_changed(self,field,value):
        data=json.loads(json.dumps(self.lock));data[field]=value
        with self.assertRaises(ImageError):ConfigSnapshot.from_mapping(data)

    def test_IM47_profile_independent(self):self.config_changed('profile','changed')
    def test_IM48_commit_independent(self):self.config_changed('postgresql_commit','changed')
    def test_IM49_policy_independent(self):self.config_changed('policy','changed')

    def test_IM50_mapping_independent(self):
        for alteration in('entry','order'):
            data=json.loads(json.dumps(self.lock))
            if alteration=='entry':data['production_lhs'][0]='changed'
            else:data['production_lhs'][0],data['production_lhs'][-1]=data['production_lhs'][-1],data['production_lhs'][0]
            with self.subTest(alteration=alteration),self.assertRaises(ImageError):ConfigSnapshot.from_mapping(data)

    def test_IM51_mapping_alias(self):
        data=json.loads(json.dumps(self.lock));snapshot=ConfigSnapshot.from_mapping(data)
        original=snapshot.production_lhs[0];data['production_lhs'][0]='changed'
        self.assertEqual(snapshot.production_lhs[0],original)
        self.assertIsInstance(snapshot.production_lhs,tuple)
        with self.assertRaises(FrozenInstanceError):snapshot.profile='changed'

    def test_IM52_config_disk_change(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'lock';path.write_text(json.dumps(self.lock))
            with ParserGate(lock_path=path)as gate:
                before=gate.info['snapshot_sha256'];raw_digest=hashlib.sha256(path.read_bytes()).hexdigest();gate.validate(b'SELECT 52001')
                changed=dict(self.lock);changed['profile']='changed';path.write_text(json.dumps(changed))
                gate.validate(b'SELECT 52001');gate.validate(b'SELECT 52002')
                self.assertEqual(gate.info['snapshot_sha256'],before)
                self.assertEqual(gate.info['configuration_sha256'],raw_digest)
                with self.assertRaises(ImageError):ParserGate(lock_path=path)

    def test_IM53_digest_size_independent(self):
        self.config_changed('binary_sha256','0'*64)
        self.config_changed('binary_size',136492599)
        a=ConfigSnapshot.from_mapping(self.lock);b=ConfigSnapshot.from_mapping(self.lock)
        self.assertNotEqual(a.generation,b.generation);self.assertNotEqual(a.digest,b.digest)

    def test_IM54_status_snapshot_lifecycle(self):
        image,config=self.small_image();gate=self.fake_gate(image,config)
        status=gate.info;self.assertEqual(status['snapshot_sha256'],config.digest)
        self.assertEqual(status['mapping_sha256'],config.mapping_sha256)
        status['failure_counts']['changed']=100
        self.assertNotIn('changed',gate.info['failure_counts'])
        self.assertEqual(status['config_policy'],'frozen-until-new-generation')
        gate.close();self.assertEqual(gate.info['lifecycle'],'stopped')

    def test_IM55_stale_completion_shutdown(self):
        image,config=self.small_image();gate=self.fake_gate(image,config)
        def stop(*args,**kwargs):
            with image.lock:image.close_locked()
            return self.raw_report
        with patch.object(image,'run',side_effect=stop),self.assertRaises(SQLGuardError):gate.validate(b'SELECT 1')
        self.assertEqual(len(gate._cache),0);self.assertEqual(image._slots_free,2)

    def test_IM56_noexec_no_fallback(self):
        source,size,digest=self.tiny();before=fd_count()
        with patch.object(init_module.os,'memfd_create',side_effect=OSError(errno.EINVAL,'fixture'))as call:
            with self.assertRaises(OSError):init_module.build_image(source,size,digest)
        self.assertEqual(call.call_count,1)
        self.assertTrue(call.call_args.args[1] & init_module.MFD_EXEC)
        self.assertEqual(fd_count(),before)

    def test_close_failure_is_infrastructure_and_sticky(self):
        image,config=self.small_image();gate=self.fake_gate(image,config);original=os.close;leaked=[]
        def fail(descriptor):
            if descriptor!=image._descriptor:
                leaked.append(descriptor)
                raise OSError(errno.EIO,'fixture')
            return original(descriptor)
        with patch.object(image_module.os,'close',side_effect=fail):
            with self.assertRaises(SQLGuardError)as error:gate.validate(b'SELECT 1')
        self.assertEqual(error.exception.category,'infrastructureFailure')
        self.assertEqual(image._state,'failed')
        with self.assertRaises(SQLGuardError):gate.validate(b'SELECT 1')
        self.assertFalse(gate.info['shutdown_complete'])
        for descriptor in leaked:original(descriptor)
        # Clear only this injected uncertainty so fixture cleanup can complete.
        image._cleanup_failed=False

    def test_identity_error_cleanup_failure_sticks(self):
        image,config=self.small_image();original_close=os.close;leaked=[]
        image._object=(-1,-1)
        def fail(descriptor):
            if descriptor!=image._descriptor:
                leaked.append(descriptor)
                raise OSError(errno.EIO,'fixture')
            return original_close(descriptor)
        with patch.object(image_module.os,'close',side_effect=fail):
            with image.lock,self.assertRaises(ImageError):image.check_locked(config)
        self.assertEqual(image._state,'failed')
        self.assertTrue(image._cleanup_failed)
        for descriptor in leaked:original_close(descriptor)
        image._cleanup_failed=False

    def test_cancel_during_live_child_reaps_owner(self):
        image,config=self.small_image();cancel=threading.Event();original=subprocess.Popen;children=[];before=fd_count()
        def stalled(*args,**kwargs):
            process=original(['/bin/sleep','30'],**kwargs)
            children.append(process)
            return process
        with image.reserve(config,cancel)as owner:
            def cancelling():
                wait_for(lambda:owner.process is not None)
                cancel.set()
            thread=threading.Thread(target=cancelling);thread.start()
            with patch.object(image_module.subprocess,'Popen',side_effect=stalled):
                with self.assertRaises(ParserFailure):image.run(owner,b'SELECT 1',config,cancel)
            thread.join(2)
        self.assertEqual(fd_count(),before)
        self.assertTrue(all(child.poll()is not None for child in children))
        self.assertEqual(image._slots_free,2)
