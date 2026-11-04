"""Run immutable document fixtures through the real sandbox, never the HTTP path.

Authoring runs execute F0 only to diagnose fixture/oracle mistakes. Registered
differential runs require an explicit immutable registration and cannot mutate
their fixtures after a mismatch. Neither mode supplies a performance selection.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

from compare_responses import check_response, compare, decode, require
from harness_common import digest, process_identity, record, root_hash, write_private
import installation

HERE = Path(__file__).resolve().parent
JAVA = Path('/usr/lib/jvm/java-17-openjdk-amd64/bin/java')


def inventory(target):
    """Bind exact classes, dependencies, solver and only the gate probe classes."""
    files = []
    for directory in ('classes','dependency','solver'):
        files.extend(record(path,target) for path in sorted((target/directory).rglob('*')) if path.is_file())
    files.extend(record(path,target) for path in sorted((target/'test-classes/dev/allow/backend').glob('FreshTier1ProbeMain*.class')))
    require(bool(files) and any('FreshTier1ProbeMain.class' in row['path'] for row in files), 'PROBE_BUILD_REQUIRED')
    return files


def immutable(target, expected):
    """Recheck every bound compiled input before and after an entire run."""
    require(inventory(target)==expected,'COMPILED_INPUT_MUTATED')


def invoke(target, probe_classes, profile, fixture, output):
    """Start the fixed Java probe without inherited JVM flags or a shell."""
    classpath = ':'.join((str(probe_classes),str(target/'classes'),str(target/'dependency/*')))
    command = [str(JAVA),'-Xms32m','-Xmx256m','-XX:+UseSerialGC','-cp',classpath,
               'dev.allow.backend.FreshTier1ProbeMain','--target',str(target),'--profile',profile,
               '--input',str(fixture),'--output',str(output)]
    environment = {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
    started = time.monotonic_ns()
    process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment)
    try: descriptor = os.pidfd_open(process.pid)
    except ProcessLookupError: descriptor = None
    timed_out = False
    try:
        try: stdout,stderr = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            timed_out = True
            require(descriptor is not None,'PROBE_TIMEOUT_WITHOUT_OWNERSHIP')
            try: signal.pidfd_send_signal(descriptor,signal.SIGKILL)
            except ProcessLookupError: pass
            stdout,stderr = process.communicate(timeout=5)
    finally:
        if descriptor is not None: os.close(descriptor)
    value = json.loads(output.read_bytes()) if output.exists() else None
    write_private(output.with_suffix('.transport.json'),{'stdoutBase64':base64.b64encode(stdout).decode(),
                  'stderrBase64':base64.b64encode(stderr).decode(),'probePid':process.pid,'timed_out':timed_out})
    return {'exit_code':process.returncode,'wall_ns':time.monotonic_ns()-started,'timed_out':timed_out,
            'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
            'stderr_sha256':hashlib.sha256(stderr).hexdigest(),'record':value}


def oracle(result, item, request, profile, build_identity):
    """Require frozen expected status, source/history identity and exact worker reap."""
    require(not result.get('timed_out'),'PROBE_TIMEOUT_CLEANUP_UNCONFIRMED')
    require(result['exit_code']==0 and isinstance(result['record'],dict),'PROBE_EXECUTION_FAILED')
    value = result['record']
    expected_profile = 'DEFAULT' if profile=='F0' else 'DOCUMENT_ADVISORY_TIER1'
    require(value.get('profile')==expected_profile,'PROBE_PROFILE_MISMATCH')
    require(value.get('inputSha256')==item['sha256'] and type(value.get('inputBytes')) is int
            and value['inputBytes']==item['bytes'],'PROBE_INPUT_MISMATCH')
    if item.get('expectedProbeReject'):
        require(value.get('outcome')=='INPUT_REJECTED' and value.get('noWorkerStarted') is True
                and 'workerPid' not in value and 'buildIdentity' not in value,'PROBE_BOUNDARY_NOT_REJECTED')
        return None
    require(value.get('outcome')=='COMPLETE_RESPONSE','COMPLETE_RESPONSE_REQUIRED')
    require(value.get('buildIdentity')==build_identity and value.get('noWorkerStarted') is False,'PROBE_BUILD_MISMATCH')
    require(type(value.get('workerPid')) is int and value['workerPid']>0
            and isinstance(value.get('workerStartTicks'),str)
            and re.fullmatch('[1-9][0-9]*',value['workerStartTicks']) is not None,'OWNED_IDENTITY_REQUIRED')
    current = process_identity(value['workerPid'])
    require(current is None or current['start_ticks']!=value['workerStartTicks'],'WORKER_STILL_ALIVE')
    require(value.get('reaped') is True and type(value.get('workerExitCode')) is int
            and value['workerExitCode']==0 and value.get('requestIdentityMatches') is True,'OWNED_REAP_REQUIRED')
    for key in ('constructorNanos','launchNanos','exchangeNanos','reapNanos','totalNanos'):
        require(type(value.get(key)) is int and value[key]>=0,'INVALID_PROBE_TIMING')
    raw = base64.b64decode(value['responseBase64'],validate=True)
    require(len(raw)==value['responseBytes'] and hashlib.sha256(raw).hexdigest()==value['responseSha256'], 'RAW_RESPONSE_INTEGRITY')
    response = decode(raw)
    check_response(response,request)
    require(response['status']==item['expectedStatus'],'EXPECTED_STATUS_MISMATCH')
    if item.get('expectedMode'):
        require(response['data']['mode']==item['expectedMode'],'EXPECTED_MODE_MISMATCH')
    if response['status']=='VALIDATED':
        candidate = request.get('candidate')
        if candidate is not None and candidate.get('mode')=='SOURCE':
            require(response['data']['source']==candidate['source'],'SOURCE_BYTES_CHANGED')
        if item.get('historicalExact'):
            for key in ('mode','source','sourceHash','module','occurrences','trivia'):
                require(response['data'][key]==request['baseArtifact'][key], 'HISTORY_CONTENT_CHANGED')
    return response


def check_registration(path, target_rows, fixture_manifest):
    """Require every concrete fixture and comparator byte in the frozen run package."""
    registration = json.loads(path.read_bytes())
    require(registration.get('status')=='FROZEN_RUNTIME_REGISTRATION','REGISTRATION_STATUS')
    require(registration.get('input_root_sha256')==root_hash(registration),'REGISTRATION_ROOT')
    require(registration.get('backend_target_files')==target_rows,'REGISTERED_BUILD_MISMATCH')
    require(registration.get('fixture_manifest_sha256')==digest(fixture_manifest),'REGISTERED_FIXTURE_MISMATCH')
    require(len({row['path'] for row in registration['files']})==len(registration['files']),'DUPLICATE_REGISTRATION_INPUT')
    for row in registration['files']:
        path = HERE/row['path']
        require(path.is_file() and digest(path)==row['sha256'],'REGISTERED_VERIFIER_MUTATED')
    require(digest(Path(registration['python']['path']))==registration['python']['sha256'],'PYTHON_TOOL_MUTATED')
    for name in ('compare_responses.py','test_compare_responses.py','run_semantic.py','test_run_semantic.py',
                 'harness_common.py','installation.py','make_fixtures.py'):
        require(any(row['path']==name for row in registration['files']),'REQUIRED_VERIFIER_UNREGISTERED')
    manifest = json.loads(fixture_manifest.read_bytes())
    require(len(manifest['fixtures'])==registration['fixture_count']>0,'REGISTERED_CASE_COUNT')
    require([row['name'] for row in manifest['fixtures']]==registration['fixture_names'],'REGISTERED_CASE_NAMES')
    installation.verify_tools(registration['tooling'])
    return registration


def check_fixtures(directory, manifest):
    """Require the registered nonempty unique corpus, exact bytes and safe file names."""
    rows = manifest['fixtures']
    require(bool(rows) and len({row['name'] for row in rows})==len(rows),'EMPTY_OR_DUPLICATE_CORPUS')
    require(len({row['path'] for row in rows})==len(rows),'DUPLICATE_FIXTURE_PATH')
    for row in rows:
        require(isinstance(row['name'],str) and re.fullmatch('[A-Za-z0-9_-]+',row['name']) is not None,'UNSAFE_FIXTURE_NAME')
        path = Path(row['path'])
        require(len(path.parts)==1 and path.suffix=='.json' and path.name not in {'manifest.json'},'UNSAFE_FIXTURE_PATH')
        require(path.name==row['name']+'.json' and type(row['bytes']) is int and row['bytes']>0,'FIXTURE_IDENTITY')
        fixture = directory/path
        require(not fixture.is_symlink() and fixture.is_file(),'REGULAR_FIXTURE_REQUIRED')
        require(digest(fixture)==row['sha256'] and fixture.stat().st_size==row['bytes'],'FIXTURE_MUTATED')
    require({path.name for path in directory.iterdir()}=={'manifest.json',*(row['path'] for row in rows)},'UNREGISTERED_FIXTURE_FILE')


def copy_probe(target, output):
    """Admit exactly two frozen probe classes instead of the broad test classpath."""
    destination = output/'probe-classes'
    for name in ('FreshTier1ProbeMain.class','FreshTier1ProbeMain$Options.class'):
        relative = Path('dev/allow/backend')/name
        original = target/'test-classes'/relative
        copied = destination/relative
        copied.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        shutil.copy2(original,copied)
        require(digest(original)==digest(copied),'PROBE_COPY_MISMATCH')
    return destination


def snapshot_registration(registration, output):
    """Preserve every registered source/fixture byte for later replay of the evidence."""
    destination = output/'frozen-inputs'
    destination.mkdir(mode=0o700)
    rows = []
    for index,row in enumerate(registration['files']):
        original = HERE/row['path']
        copied = destination/f'{index:04d}.input'
        shutil.copy2(original,copied)
        copied.chmod(0o600)
        require(digest(copied)==row['sha256'],'REGISTRATION_SNAPSHOT_MUTATION')
        rows.append({**row,'snapshot':str(copied.relative_to(output))})
    write_private(destination/'manifest.json',{'registration':registration,'files':rows})


def execute(args):
    """Preserve every case result and fail the suite on any independently checked mismatch."""
    target,fixtures = args.target.resolve(),args.fixtures.resolve()
    rows = inventory(target)
    manifest_path = fixtures/'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    registration = check_registration(args.registration,rows,manifest_path) if args.registration else None
    root = registration['input_root_sha256'] if registration else None
    registration_sha = digest(args.registration) if args.registration else None
    check_fixtures(fixtures,manifest)
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    binding = {'mode':args.mode,'backend_target':str(target),'backend_target_files':rows,
               'fixture_manifest_sha256':digest(manifest_path),'java':record(JAVA),'runtime_registration':root,
               'verifiers':[record(HERE/name,HERE) for name in ('compare_responses.py','run_semantic.py')]}
    write_private(args.output/'inputs.json',binding)
    if registration: snapshot_registration(registration,args.output)
    probe_classes = copy_probe(target,args.output)
    java = installation.java_metadata()
    build_identity = installation.build_identity(target.parent.parent,java['runtime_version'])['value']
    results = []
    for item in manifest['fixtures']:
        fixture = fixtures/item['path']
        require(digest(fixture)==item['sha256'] and fixture.stat().st_size==item['bytes'],'FIXTURE_MUTATED')
        request = json.loads(fixture.read_bytes())
        row = {'name':item['name'],'status':'PASS','fixture_sha256':item['sha256'],'profiles':{}}
        responses = []
        cleanup_unknown = False
        for profile in (('F0',) if args.mode=='authoring' else ('F0','F1')):
            try:
                outcome = invoke(target,probe_classes,profile,fixture,args.output/f"{item['name']}-{profile}-private.json")
                row['profiles'][profile] = {key:value for key,value in outcome.items() if key!='record'}
                cleanup_unknown = outcome.get('timed_out',False)
                responses.append(oracle(outcome,item,request,profile,build_identity))
            except (AssertionError,ValueError,KeyError,subprocess.TimeoutExpired) as failure:
                row.update(status='FAIL',reason=str(failure)[:100] if isinstance(failure,AssertionError) else type(failure).__name__)
                break
        if args.mode=='compare' and row['status']=='PASS' and responses[0] is not None:
            try: row['comparison'] = compare(responses[0],responses[1],request)
            except (AssertionError,ValueError,KeyError) as failure: row.update(status='FAIL',reason=str(failure)[:100])
        results.append(row)
        write_private(args.output/f"{item['name']}-case.json",row)
        if cleanup_unknown or row['status']!='PASS' and args.mode=='compare': break
    integrity_error = None
    try:
        immutable(target,rows)
        check_fixtures(fixtures,manifest)
        require(digest(manifest_path)==binding['fixture_manifest_sha256'],'FIXTURE_MANIFEST_MUTATED')
        if registration:
            require(digest(args.registration)==registration_sha,'REGISTRATION_CHANGED_DURING_RUN')
            require(check_registration(args.registration,rows,manifest_path)['input_root_sha256']==root,
                    'REGISTRATION_ROOT_CHANGED_DURING_RUN')
    except (AssertionError,ValueError,OSError) as failure:
        integrity_error = type(failure).__name__+':'+str(failure)[:100]
    failures = [{'name':row['name'],'reason':row.get('reason')} for row in results if row['status']!='PASS']
    if integrity_error: failures.append({'name':'final-input-integrity','reason':integrity_error})
    report = {'status':'PASS' if not failures else 'BLOCKED','mode':args.mode,'runtime_registration':root,
              'cases':results,'failures':failures,'selection_evidence':args.mode=='compare' and not failures,
              'limitations':'Finite output/reap check only. No HTTP timing or whole-stack/target-host acceptance.'}
    report.update(expected_cases=len(manifest['fixtures']),executed_cases=len(results),build_identity=build_identity)
    write_private(args.output/'report.json',report)
    print(json.dumps({'status':report['status'],'cases':len(results),'failures':failures,'output':str(args.output)}))
    return 0 if report['status']=='PASS' else 1


def main():
    """Require explicit authoring or preregistered comparison mode and new output path."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('authoring','compare'),required=True)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--registration',type=Path)
    args = parser.parse_args()
    try:
        require(args.mode!='compare' or args.registration is not None,'COMPARISON_REGISTRATION_REQUIRED')
        descriptor = os.pidfd_open(os.getpid())
        os.close(descriptor)
        return execute(args)
    except Exception as failure:
        args.output.mkdir(mode=0o700,parents=True,exist_ok=True)
        report = {'status':'BLOCKED' if isinstance(failure,(AssertionError,ValueError)) else 'INFRASTRUCTURE_FAILURE',
                  'mode':args.mode,'selection_evidence':False,'failure_category':type(failure).__name__}
        path = args.output/'runner-failure.json'
        if not path.exists(): write_private(path,report)
        print(json.dumps(report))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
