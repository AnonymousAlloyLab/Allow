#!/usr/bin/env python3
"""Create and clean one uniquely owned delegated scope, with an infrastructure-only child."""
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import time
import uuid

HERE=Path(__file__).resolve().parent


def save(path,value):
    """Retain immutable private evidence."""
    with path.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def properties(unit,environment):
    """Read exact unit identity and delegation without changing manager state."""
    value=subprocess.run(['/usr/bin/systemctl','--user','show',unit,'--property=Id,Description,InvocationID,ControlGroup,ActiveState,SubState,Delegate,DelegateControllers'],env=environment,capture_output=True,text=True,timeout=5,check=True).stdout
    return dict(line.split('=',1) for line in value.splitlines() if '=' in line)


def main():
    """Bound the capability probe and preserve fail-closed cleanup evidence."""
    os.umask(0o077)
    output=HERE/'delegation-probe-r1';output.mkdir(mode=0o700)
    unit='allow-warm-delegate-'+uuid.uuid4().hex+'.scope'
    description='allow-warm-infrastructure:'+uuid.uuid4().hex
    environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','XDG_RUNTIME_DIR':'/run/user/'+str(os.getuid()),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(os.getuid())+'/bus','PYTHONDONTWRITEBYTECODE':'1'}
    child=HERE/'delegation_probe_child.py'
    argv=['/usr/bin/systemd-run','--user','--scope','--quiet','--unit='+unit,'--description='+description,'--property=Delegate=yes','--property=CPUQuota=100%','--property=MemoryMax=268435456','--property=MemorySwapMax=0','--property=TasksMax=32','/usr/bin/env','-i','PATH=/usr/bin:/bin','LANG=C.UTF-8','PYTHONDONTWRITEBYTECODE=1','/usr/bin/python3',str(child),str(output),unit]
    save(output/'registration.json',{'unit':unit,'description':description,'argv':argv,'child_sha256':hashlib.sha256(child.read_bytes()).hexdigest(),'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'One new private infrastructure scope; no Allow/JVM/model/shared services; bounded30s outer deadline.'})
    state=None;events=None;report={'status':'INFRASTRUCTURE_FAILURE','unit':unit}
    with (output/'private.log').open('xb') as log:
        process=subprocess.Popen(argv,env=environment,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+15
            while not (output/'probe-result.json').exists() and process.poll() is None and time.monotonic()<deadline:
                if state is None:
                    observed=properties(unit,environment)
                    if observed.get('Description')==description and observed.get('ControlGroup'):
                        state=observed
                        events=os.open('/sys/fs/cgroup'+state['ControlGroup']+'/cgroup.events',os.O_RDONLY)
                time.sleep(.02)
            if state is None or not (output/'probe-result.json').exists():
                raise RuntimeError('probe_did_not_complete')
            current=properties(unit,environment)
            if current.get('InvocationID')!=state.get('InvocationID') or current.get('Description')!=description:
                raise RuntimeError('scope_incarnation_changed')
            report['unit_properties']=current
            report['probe']=json.loads((output/'probe-result.json').read_text())
            (output/'allow-exit').touch(mode=0o600)
            explicit_zero=False
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                try:
                    os.lseek(events,0,os.SEEK_SET)
                    if b'populated 0' in os.read(events,4096):explicit_zero=True
                except OSError:pass
                if process.poll() is not None and explicit_zero:break
                time.sleep(.005)
            report['systemd_run_exit_code']=process.wait(timeout=2)
            report['scope_explicit_populated_zero']=explicit_zero
            report['probe_process_absent']=not Path('/proc',str(report['probe']['probe_identity']['pid'])).exists()
            report['status']='PASS' if (report['probe']['status']=='PASS' and report['systemd_run_exit_code']==0 and report['probe_process_absent']) else 'BLOCKED'
        except BaseException as error:
            report['failure_class']=type(error).__name__;report['failure_code']=str(error) if isinstance(error,RuntimeError) else 'private_log_retained'
        finally:
            if process.poll() is None:
                current=properties(unit,environment)
                if current.get('Description')==description and (state is None or current.get('InvocationID')==state.get('InvocationID')):
                    cleanup=subprocess.run(['/usr/bin/systemctl','--user','kill','--kill-whom=all','--signal=SIGKILL',unit],env=environment,capture_output=True,timeout=5)
                    report['emergency_owned_unit_kill_code']=cleanup.returncode
                process.wait(timeout=5)
            if events is not None:os.close(events)
            report['unit_after_exit']=properties(unit,environment)
            report['boundary']='Infrastructure capability only; not JVM image, sandbox, crash/restart or production acceptance.'
            save(output/'report.json',report)
    print(json.dumps({key:report[key] for key in ('status','unit','scope_explicit_populated_zero','probe_process_absent') if key in report}))


if __name__=='__main__':main()
