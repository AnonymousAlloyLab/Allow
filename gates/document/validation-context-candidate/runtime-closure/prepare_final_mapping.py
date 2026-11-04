"""Freeze a revised, conservative assertion mapping; never execute supplemental tests."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((HERE/'case-mapping-r1.json').read_text());by={x['id']:x for x in r['obligations']}
py='gates/document/validation-context-candidate/runtime-checks/python/r2/runs/run-20261103T223426Z/report.json'
auth='gates/document/validation-context-candidate/runtime-checks/python/auth-diagnostic-r1/runs/run-20261103T223614Z/report.json'
for ident,path in [('supp:python-r2',py),('supp:auth',auth),('supp:java-head','gates/document/validation-context-candidate/runtime-checks/java/head-result.json'),('supp:java-bounds','gates/document/validation-context-candidate/runtime-checks/java/result.json'),('supp:java-sequence','gates/document/validation-context-candidate/runtime-checks/java/actual-sequence-result.json'),('supp:java-build-denial','gates/document/validation-context-candidate/runtime-checks/java/sequence-result.json'),('supp:java-ownership','gates/document/validation-context-candidate/runtime-checks/java/ownership-result.json'),('report:benchmark','gates/document/server-benchmark-runs/validation-context-v1/server-performance.json')]:
 r['records'][ident]={'kind':'registered_report','path':path,'sha256':sha(ROOT/path),'assertions_reviewed':['Supplemental finite cases verified by this closure verifier, not merely report title/test name.']}
resolved={
 'VC02':['Actual post-auth libpq trace BEGIN/mode/tenant/project/purpose/head/base/history/COMMIT, endpoint/closedconnection/proxy lowerbound bound.'],
 'VC03':['Emptywanted guard is a checked source AST fact: history SQL occurs only under if wanted; actual empty-ID/baseauthorization tests and maxquota emptycontrol are separately executed.'],
 'VC06':['P02 real first-tenant-SELECT barrier before projectSELECT: oldhead1/newhead2 and immutablebase0.'],
 'VC11':['Positive base1/head0 Java unavailable boundary explicitly executed after preregistration.'],
 'VC12':['Actual private frame structural sizes2097151 launch/reap,2097152/3 rejected without launch. Stronger public/artifact caps can make valid boundary unreachable; fixture is adversarial.'],
 'VC15':['Compositional: actual SQL COMMIT/closedconnection trace plus real DocumentGateway context bridge exit before two actual sandbox workers. Not one monolithic HTTP/SQL process trace.'],
 'VC16':['Two real context bridges and distinct successful actual workers; complete launcher command equality; copied-build mutation denied. No active build mutation.'],
 'VC17':['Direct actual isolated worker missing/foreign/wrong-kind INVALID and matchingkind VALIDATED, composed with actual Store RLS and public type/source fixtures.'],
 'VC18':['Actual cancel and20s timeout before/after all durable rows/ACL/counters equal after explicit owned-backend cleanup. Does not establish automatic SQL termination at CLI death.'],
 'VC22':['Actual newcontext full stage trace, canonical proxy/allow-recovery fixture tag, sealed identity and lower-bound counter delta. No exclusive asynchronous attribution.'],
 'VC24':['Both frozen complete1100runs; actualpercentiles/failures/source/fixture/verifier comparison. Measurement complete while strict300ms target remains FAIL.']}
extra={'VC02':['supp:python-r2'],'VC03':['supp:python-r2'],'VC06':['supp:python-r2'],'VC11':['supp:java-head'],'VC12':['supp:java-bounds'],'VC15':['supp:python-r2','supp:java-sequence'],'VC16':['supp:java-sequence','supp:java-build-denial'],'VC17':['supp:java-ownership'],'VC18':['supp:python-r2'],'VC22':['supp:python-r2'],'VC24':['report:benchmark']}
for key,notes in resolved.items():
 by[key]['remaining_required_cases']=[];by[key]['audit_status']='SUPPORTED_FINITE_EVIDENCE';by[key]['covered_cases']+=notes;by[key]['evidence_refs']+=extra[key]
for key in ['VC01','VC13','VC14']:by[key]['evidence_refs']+=['supp:python-r2','supp:auth']
by['VC01']['remaining_required_cases']=[{'gap_id':'VC01-PRIVATE-WIRE-BOUNDS','case':'Literal private full-frame MAX_INPUT and decoded96/97-depth boundary fixtures not located in executed new-operation evidence. Closed-shape/args-byte negatives cover different guards.'}]
by['VC13']['remaining_required_cases']=[{'gap_id':'VC13-JSON-NESTING','case':'Explicit decoded JSON nesting-limit negative fixture not located. Canonical valid args maximum188512bytes and adversarial262144/262145 encodedargs guards ARE covered; no valid256KiBshape is fabricated.'}]
by['VC14']['remaining_required_cases']=[{'gap_id':'VC14-PARSER-STOP','case':'Literal parser/helper shutdown during current context not performed. Real invalidSQL parser denial, injected transport closes and inherited private FailedGate tests do not equal actual helper shutdown.'}]
r['revision']='r2';r['scope']='Conservative assertion-level finite runtime audit, not formal implementation refinement. Three precise missing cases remain blocking.'
r['material_limitations']=[
 'Actual timeout killed/reaped the owned CLI at20.003274s but backend remained active and required explicit pg_cancel_backend cleanup. Nonmutation is an end-state observation after cleanup, not automatic backend lifetime enforcement.',
 'RealSQL COMMIT/closedconnection and actualcontextbridge-before-worker are compositional component observations, not a monolithic authenticated HTTP causal trace.',
 'VC19 fixtures are storage-shaped, not4096 independently Alloy-accepted edits; libpq client cursor buffers whole history result before iteration. Payload quota is not an RSS bound.',
 'Kernel maxRSS273301504bytes=260.64MiB differs from larger sampledRSS274898944bytes=262.16MiB; report both, never label260.64MiB the largest observed RSS.',
 'Browser cold-series/manualaccessibility and universal semantic/runtime refinement remain outside these finite checks.'
]
(HERE/'case-mapping-r2.json').write_text(json.dumps(r,indent=2)+'\n')
print('Mapped',len(by),'supported',sum(not x['remaining_required_cases']for x in by.values()),'unresolved',sum(bool(x['remaining_required_cases'])for x in by.values()))
