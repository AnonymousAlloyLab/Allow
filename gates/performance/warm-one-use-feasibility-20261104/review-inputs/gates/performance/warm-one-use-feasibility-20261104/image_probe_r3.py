#!/usr/bin/env python3
"""Supervise one public sealed-image infrastructure probe in a uniquely owned bounded scope."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from delegation_probe import properties, save, HERE


def main():
    """Preserve one variant's exact inputs/outcome and positively empty its private scope."""
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=('data-final-limit',),required=True);parser.add_argument('--run-id',choices=('image-probe-r3',),required=True);args=parser.parse_args()
    os.umask(0o077);output=HERE/args.run_id;output.mkdir(mode=0o700)
    unit='allow-warm-image-'+uuid.uuid4().hex+'.scope';description='allow-warm-image:'+uuid.uuid4().hex
    environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','XDG_RUNTIME_DIR':'/run/user/'+str(os.getuid()),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(os.getuid())+'/bus','PYTHONDONTWRITEBYTECODE':'1'}
    child=HERE/'image_probe_child_r3.py'
    argv=['/usr/bin/systemd-run','--user','--scope','--quiet','--unit='+unit,'--description='+description,'--property=Delegate=yes','--property=CPUQuota=100%','--property=MemoryMax=1073741824','--property=MemorySwapMax=0','--property=TasksMax=64','/usr/bin/env','-i','PATH=/usr/bin:/bin','LANG=C.UTF-8','PYTHONDONTWRITEBYTECODE=1','/usr/bin/python3',str(child),str(output),unit,args.variant]
    inputs=[Path(__file__),child,HERE/'delegation_probe.py',HERE/'IdentityReadProbe.java',Path('/usr/bin/bwrap'),Path('/usr/bin/prlimit'),Path('/usr/bin/sha256sum')]
    save(output/'registration.json',{'unit':unit,'description':description,'argv':argv,'inputs':[{'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in inputs],'scope':'Public image/identity/hash probe only; no Alloy model/private input or worker execution. Capture+bwrapsetupFS64MiB then finalexecutableFS8MiB, AS2GiB CPU12s throughout, private scope1GiB/1CPU/64tasks.'})
    state=None;events=None;report={'status':'INFRASTRUCTURE_FAILURE','unit':unit,'variant':args.variant}
    with (output/'private.log').open('xb') as log:
        process=subprocess.Popen(argv,env=environment,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+20
            while not (output/'probe-result.json').exists() and process.poll() is None and time.monotonic()<deadline:
                if state is None:
                    observed=properties(unit,environment)
                    if observed.get('Description')==description and observed.get('ControlGroup'):
                        state=observed;events=os.open('/sys/fs/cgroup'+state['ControlGroup']+'/cgroup.events',os.O_RDONLY)
                time.sleep(.02)
            if state is None or not (output/'probe-result.json').exists():raise RuntimeError('probe_did_not_complete')
            report['probe']=json.loads((output/'probe-result.json').read_text());report['unit_properties']=state
            (output/'allow-exit').touch(mode=0o600)
            explicit_zero=False;deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                try:
                    os.lseek(events,0,os.SEEK_SET)
                    if b'populated 0' in os.read(events,4096):explicit_zero=True
                except OSError:pass
                if process.poll() is not None and explicit_zero:break
                time.sleep(.005)
            report['systemd_run_exit_code']=process.wait(timeout=2);report['scope_explicit_populated_zero']=explicit_zero
            report['probe_process_absent']=not Path('/proc',str(report['probe']['pid'])).exists()
            report['status']=report['probe']['status'] if explicit_zero and report['probe_process_absent'] else 'INFRASTRUCTURE_FAILURE'
        except BaseException as error:
            report['failure_class']=type(error).__name__;report['failure_code']=str(error) if isinstance(error,RuntimeError) else 'private_log_retained'
        finally:
            current=properties(unit,environment)
            if current.get('Description')==description and (state is None or current.get('InvocationID')==state.get('InvocationID')):
                stopped=subprocess.run(['/usr/bin/systemctl','--user','stop',unit],env=environment,capture_output=True,timeout=5);report['owned_scope_stop_code']=stopped.returncode
            if process.poll() is None:process.wait(timeout=5)
            if events is not None:os.close(events)
            report['scope_path_absent']=state is not None and not Path('/sys/fs/cgroup'+state['ControlGroup']).exists()
            if not report['scope_path_absent']:report['status']='INFRASTRUCTURE_FAILURE'
            report['boundary']='Kernel byte/seal transport only; warm classloader, READY, private request, crashes and performance remain untested.'
            save(output/'report.json',report)
    print(json.dumps({key:report[key] for key in ('status','variant','scope_explicit_populated_zero','probe_process_absent','scope_path_absent') if key in report}))


if __name__=='__main__':main()
