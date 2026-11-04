#!/usr/bin/env python3
"""Exercise only immutable application-byte transport and kernel seals inside a private scope."""
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import stat
import subprocess
import sys
import time

REQUIRED = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
ALLOY = '6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d'


def sha(path):
    """Read bounded build files without retaining complete JARs in Python memory."""
    value=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1048576):value.update(chunk)
    return value.hexdigest()


def save(path,value):
    """Keep one immutable private evidence object."""
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def members(target):
    """Match the existing logical BuildIdentity input groups and lexical path ordering."""
    result=[]
    for directory,jars_only in [('classes',False),('dependency',True)]:
        group=target/directory
        for path in sorted(group.rglob('*'),key=lambda item:str(item)):
            if path.is_symlink():raise RuntimeError('build_symlink_rejected')
            if path.is_file() and (not jars_only or path.suffix=='.jar'):result.append(path)
    result.append(target/'solver/alloy.jar')
    if len(result)>512 or sum(path.stat().st_size for path in result)>67108864:
        raise RuntimeError('image_inventory_budget_exceeded')
    return result


def capture(path):
    """Copy one exact ordinary file, seal it, and hash destination bytes after sealing."""
    source=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    descriptor=None
    try:
        metadata=os.fstat(source)
        if not stat.S_ISREG(metadata.st_mode):raise RuntimeError('nonregular_source')
        descriptor=os.memfd_create('allow-public-image-probe',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
        os.fchmod(descriptor,0o444)
        remaining=metadata.st_size
        while remaining:
            chunk=os.read(source,min(1048576,remaining))
            if not chunk:raise RuntimeError('early_source_eof')
            remaining-=len(chunk)
            view=memoryview(chunk)
            while view:
                count=os.write(descriptor,view)
                if count<=0:raise RuntimeError('image_short_write')
                view=view[count:]
        if os.read(source,1):raise RuntimeError('source_grew')
        fcntl.fcntl(descriptor,fcntl.F_ADD_SEALS,REQUIRED)
        if fcntl.fcntl(descriptor,fcntl.F_GET_SEALS)&REQUIRED!=REQUIRED:
            raise RuntimeError('missing_seals')
        digest=hashlib.sha256();offset=0
        while offset<metadata.st_size:
            chunk=os.pread(descriptor,min(1048576,metadata.st_size-offset),offset)
            if not chunk:raise RuntimeError('sealed_image_eof')
            digest.update(chunk);offset+=len(chunk)
        result=descriptor;descriptor=None
        return result,metadata.st_size,digest.hexdigest()
    finally:
        os.close(source)
        if descriptor is not None:os.close(descriptor)


def deny_mutations(descriptor,size):
    """Require actual kernel EPERM for write, growth and shrink attempts on each sealed object."""
    checks=[('write',lambda:os.pwrite(descriptor,b'!',0)),('grow',lambda:os.ftruncate(descriptor,size+1))]
    if size:checks.append(('shrink',lambda:os.ftruncate(descriptor,size-1)))
    result={}
    for name,operation in checks:
        try:operation()
        except OSError as error:result[name]=error.errno==errno.EPERM
        else:result[name]=False
    if not all(result.values()):raise RuntimeError('sealed_mutation_not_denied')
    return result


def destination(relative):
    """Keep exactly the current directory classpath and solver pathname."""
    if relative=='solver/alloy.jar':return '/app/solver.jar'
    return '/app/'+relative


def logical_identity(rows,descriptors,version):
    """Compute exact path-NUL/bytes-NUL plus runtime-version identity from sealed destination objects."""
    digest=hashlib.sha256()
    for row,descriptor in zip(rows,descriptors):
        digest.update(row['path'].encode());digest.update(b'\0');offset=0
        while offset<row['size']:
            chunk=os.pread(descriptor,min(1048576,row['size']-offset),offset)
            if not chunk:raise RuntimeError('logical_image_eof')
            digest.update(chunk);offset+=len(chunk)
        digest.update(b'\0')
    digest.update(version.encode())
    return digest.hexdigest()


def probe(output,unit,variant):
    """Compare actual sealed/mounted bytes with current BuildIdentity, without processing an Alloy model."""
    root=Path('/home/augustus/Allow');target=root/'backend/target'
    group=Path('/proc/self/cgroup').read_text().strip().split('::')[1]
    if not group.endswith('/'+unit):raise RuntimeError('private_scope_required')
    baseline_fds=len(list(Path('/proc/self/fd').iterdir()))
    descriptors=[];report={'status':'BLOCKED','scope':group,'pid':os.getpid(),'initial_fd_count':baseline_fds}
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE,(1024,1024))
        resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648))
        resource.setrlimit(resource.RLIMIT_CPU,(12,12))
        resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864))
        report['public_capture_fsize_limit']=67108864
        paths=members(target)
        before=[{'path':str(path.relative_to(target)),'size':path.stat().st_size,'sha256':sha(path)} for path in paths]
        save(output/'source-inventory.json',{'files':before,'source_inventory_sha256':hashlib.sha256(json.dumps(before,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
        java='/usr/lib/jvm/java-17-openjdk-amd64/bin/java'
        command=['/usr/bin/prlimit','--as=2147483648','--cpu=5','--',java,'-Xmx128m','-Xss512k','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:MaxMetaspaceSize=128m','-XX:CompressedClassSpaceSize=64m','-XX:ReservedCodeCacheSize=48m','--class-path',str(target/'classes'),str(Path(__file__).with_name('IdentityReadProbe.java')),str(target)]
        identity_run=subprocess.run(command,capture_output=True,text=True,timeout=10,env={'PATH':'/usr/bin:/bin'})
        (output/'identity-private.stderr').write_text(identity_run.stderr)
        if identity_run.returncode:raise RuntimeError('java_identity_probe_failed')
        identity=identity_run.stdout.splitlines()
        if len(identity)!=2 or len(identity[0])!=64:raise RuntimeError('java_identity_reply')
        mutation=[];rows=[]
        for path,expected in zip(paths,before):
            descriptor,size,digest=capture(path);descriptors.append(descriptor)
            if size!=expected['size'] or digest!=expected['sha256']:raise RuntimeError('captured_source_changed')
            mutation.append(deny_mutations(descriptor,size))
            rows.append(dict(expected,mount_path=destination(expected['path']),seals=fcntl.fcntl(descriptor,fcntl.F_GET_SEALS)))
        actual=logical_identity(rows,descriptors,identity[1])
        if actual!=identity[0] or rows[-1]['sha256']!=ALLOY:raise RuntimeError('logical_build_or_alloy_identity_mismatch')
        report.update(java_build_identity=identity[0],sealed_build_identity=actual,java_runtime_version=identity[1],image_files=len(rows),image_bytes=sum(row['size'] for row in rows),live_fd_count=len(list(Path('/proc/self/fd').iterdir())),seal_denial_checks=mutation)
        directories={str(parent) for row in rows for parent in Path(row['mount_path']).parents if str(parent)!='/'}
        argv=['/usr/bin/prlimit','--as=2147483648','--cpu=12','--fsize=67108864','--','/usr/bin/bwrap','--unshare-all','--new-session','--die-with-parent','--cap-drop','ALL','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/usr','--dir','/usr/bin','--ro-bind','/usr/bin/sha256sum','/usr/bin/sha256sum','--ro-bind','/usr/bin/prlimit','/usr/bin/prlimit']
        for directory in sorted(directories,key=lambda value:(value.count('/'),value)):argv+=['--dir',directory]
        for row,descriptor in zip(rows,descriptors):
            os.lseek(descriptor,0,os.SEEK_SET)
            argv+=['--perms','0444','--ro-bind-data',str(descriptor),row['mount_path']]
        argv+=['--tmpfs','/tmp','--proc','/proc','--dev','/dev','--chdir','/tmp','/usr/bin/prlimit','--as=2147483648','--cpu=12','--fsize=8388608','--','/usr/bin/sha256sum','--',*[row['mount_path'] for row in rows],'-']
        save(output/'mounted-probe-registration.json',{'argv':argv,'image_rows':rows,'private_input':False,'entrypoint':'fixed sha256sum only; no Alloy parser/JVM worker'})
        report['trusted_bwrap_setup_fsize_limit']=67108864
        report['final_public_executable_fsize_limit']=8388608
        report['mount_variant']=variant
        with subprocess.Popen(argv,pass_fds=descriptors,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={}) as child:
            try:
                report['final_executable_observation']=observe_final(child.pid,group)
                stdout,stderr=child.communicate(input=b'',timeout=10)
            except subprocess.TimeoutExpired:
                child.kill();child.wait(timeout=3);raise
        report['bwrap_exit_code']=child.returncode
        report['bwrap_process_reaped']=True
        (output/'mounted-private.stderr').write_bytes(stderr)
        if child.returncode or len(stdout)>65536:raise RuntimeError('mounted_hash_probe_failed')
        values={line.split(b'  ',1)[1].decode():line.split(b'  ',1)[0].decode() for line in stdout.splitlines()}
        if values.pop('-',None)!=hashlib.sha256(b'').hexdigest():raise RuntimeError('unexpected_public_stdin')
        if values!={row['mount_path']:row['sha256'] for row in rows}:raise RuntimeError('mounted_byte_mismatch')
        after=[{'path':str(path.relative_to(target)),'size':path.stat().st_size,'sha256':sha(path)} for path in members(target)]
        save(output/'source-inventory-after.json',{'files':after})
        if after!=before:raise RuntimeError('active_build_changed')
        report.update(status='PASS',mounted_files_equal=len(values),bwrap_exit_code=child.returncode,bwrap_process_reaped=True,source_bytes_unchanged=True,no_alloy_model_executed=True,no_private_request=True)
    except BaseException as error:
        report['failure_class']=type(error).__name__;report['failure_code']=str(error) if isinstance(error,RuntimeError) else 'private_diagnostics_retained'
    finally:
        if 'before' in locals():
            observed=[{'path':str(path.relative_to(target)),'size':path.stat().st_size,'sha256':sha(path)} for path in members(target)]
            report['source_bytes_and_membership_unchanged']=observed==before
            if not report['source_bytes_and_membership_unchanged']:report['status']='BLOCKED'
        old=descriptors[:]
        for descriptor in descriptors:os.close(descriptor)
        report['every_image_fd_closed']=all(closed(descriptor) for descriptor in old)
        report['final_fd_count']=len(list(Path('/proc/self/fd').iterdir()))
        if report['final_fd_count']!=baseline_fds or not report['every_image_fd_closed']:report['status']='BLOCKED'
        save(output/'probe-result.json',report)
    deadline=time.monotonic()+5
    while not (output/'allow-exit').exists() and time.monotonic()<deadline:time.sleep(.01)
    return 0 if report['status']=='PASS' else 1


def observe_final(parent,group):
    """Read the actual blocked public executable's kernel limits and dropped capabilities."""
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:
        queue=[parent];seen=set()
        while queue:
            pid=queue.pop()
            if pid in seen:continue
            seen.add(pid)
            path=Path('/proc',str(pid))
            try:
                queue.extend(int(value) for value in (path/'task'/str(pid)/'children').read_text().split())
                command=(path/'cmdline').read_bytes().split(b'\0')
                if not command or command[0]!=b'/usr/bin/sha256sum':continue
                before=(path/'stat').read_text();ticks=before[before.rfind(')')+2:].split()[19]
                if (path/'cgroup').read_text().strip().split('::')[1]!=group:raise RuntimeError('public_executable_wrong_group')
                limits=(path/'limits').read_text()
                caps={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in (path/'status').read_text().splitlines() if line.startswith(('CapEff:','CapPrm:','CapBnd:','NoNewPrivs:'))}
                after=(path/'stat').read_text()
                if after[after.rfind(')')+2:].split()[19]!=ticks:raise RuntimeError('public_executable_identity_changed')
                expected={'Max file size':(8388608,'bytes'),'Max address space':(2147483648,'bytes'),'Max cpu time':(12,'seconds')}
                for label,(value,unit) in expected.items():
                    if not re.search('^'+re.escape(label)+r'\s+'+str(value)+r'\s+'+str(value)+r'\s+'+unit+'$',limits,re.M):raise RuntimeError('final_executable_limits_mismatch')
                if any(caps.get(key)!='0000000000000000' for key in ('CapEff','CapPrm','CapBnd')):raise RuntimeError('final_executable_capabilities_not_dropped')
                return {'pid':pid,'start_ticks':ticks,'limits':limits,'capabilities':caps,'same_private_group':True,'input':'fixed empty public stdin only'}
            except (FileNotFoundError,ProcessLookupError):continue
        time.sleep(.005)
    raise RuntimeError('final_executable_not_observed')


def closed(descriptor):
    """Independently require EBADF on every formerly owned image descriptor."""
    try:os.fstat(descriptor)
    except OSError as error:return error.errno==errno.EBADF
    return False


if __name__=='__main__':raise SystemExit(probe(Path(sys.argv[1]),sys.argv[2],sys.argv[3]))
