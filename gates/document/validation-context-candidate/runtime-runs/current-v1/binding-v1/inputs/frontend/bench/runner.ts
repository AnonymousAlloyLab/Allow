import fixtureText from '../../gates/document/headless-preview-fixture.json?raw';
import type {DraftModule,Id} from '../src/document/types';
import {changeModule} from '../src/document/controller';
import {children,nodeIndex} from '../src/document/model';
import {current,observe} from './bridge';
import type {Committed} from './bridge';
import {identityEvidence,browserEnvironment,refreshSamples,advisoryEvidence} from './evidence';
import {resourceCapture} from './resources';

interface Edit {readonly nodeId:Id;readonly targetId:Id}
interface Fixture {readonly module:DraftModule;readonly source:string;readonly edits:readonly Edit[]}
interface Identity {readonly mount:object;readonly token:string;readonly document:string;readonly base:number;readonly draft:string;readonly generation:number}
const EXPECTED='947ed5002b097cd25e780afddfca5a3db9721c42b839fad4925b488af996089c';
const A='server:00000000-0000-4000-8000-000000001000',B='server:00000000-0000-4000-8000-000000001001';
const TIMEOUT=10000;
/** Reject a false invariant. @param condition Invariant. @param reason Failure explanation. @returns Nothing. */
function requireState(condition:unknown,reason:string):asserts condition {if(!condition) throw new Error(reason);}
/** Hash fixture bytes. @param text Exact UTF-8 text. @returns Hex SHA-256. */
async function digest(text:string):Promise<string> {
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
  return Array.from(new Uint8Array(hash),hexByte).join('');
}
/** Format one hash byte. @param byte Byte value. @returns Hexadecimal pair. */
function hexByte(byte:number):string {return byte.toString(16).padStart(2,'0');}
/** Capture the authority and committed draft identity. @param value Committed React view. @returns Identity. */
function identity(value:Committed):Identity {
  const state=value.view.document;requireState(state.accepted,'Open an accepted document first.');
  return {mount:value.mount,token:value.controller.token,document:state.accepted.documentId,base:state.baseRevision,draft:state.draftId,generation:state.contentGeneration};
}
/** Check all identity fields and expected content generation. @param value Committed view. @param expected Identity. @returns Nothing. */
function match(value:Committed|null,expected:Identity):void {
  requireState(value&&document.visibilityState==='visible','Unmount or visibility loss.');
  const actual=identity(value);
  requireState(actual.mount===expected.mount&&actual.token===expected.token&&actual.document===expected.document&&actual.base===expected.base&&actual.draft===expected.draft&&actual.generation===expected.generation,'Identity or generation changed.');
}
/** Arm a fresh matching rendered-view commit with explicit cleanup. @param expected Expected identity. @param after Previous commit sequence. @returns Promise and cancellation. */
function arm(expected:Identity,after:number):{promise:Promise<void>;cancel:()=>void} {
  let timer=0,rejectPending:(error:unknown)=>void=ignoreRejectedCommit;
  /** Install the commit observer. @param resolve Completion. @param reject Failure. @returns Nothing. */
  function executor(resolve:()=>void,reject:(error:unknown)=>void):void {
    rejectPending=reject;
    /** Fail on an absent commit. @returns Nothing. */
    function timeout():void {observe(null);reject(new Error('Commit timeout.'));}
    timer=window.setTimeout(timeout,TIMEOUT);
    /** Match the next rendered-view commit. @param value Committed view. @returns Nothing. */
    function notified(value:Committed):void {try {requireState(value.sequence>after,'Stale commit.');match(value,expected);clearTimeout(timer);observe(null);resolve();} catch(error) {clearTimeout(timer);observe(null);reject(error);}}
    observe(notified);
  }
  /** Remove the pending observer if dispatch throws. @returns Nothing. */
  function cancel():void {clearTimeout(timer);observe(null);rejectPending(new Error('Dispatch failed.'));}
  return {promise:new Promise(executor),cancel};
}
/** Wait for two sequential frame callbacks following the matching React commit. @param expected Expected identity. @returns Second callback clock reading. */
function frames(expected:Identity):Promise<number> {
  /** Install frame callbacks. @param resolve Completion. @param reject Failure. @returns Nothing. */
  function executor(resolve:(time:number)=>void,reject:(error:unknown)=>void):void {
    /** Reject a frame timeout. @returns Nothing. */
    function timeout():void {reject(new Error('Frame timeout.'));}
    const timer=window.setTimeout(timeout,TIMEOUT);
    /** Check the second callback and capture its monotonic timestamp. @returns Nothing. */
    function second():void {try {match(current(),expected);const end=performance.now();clearTimeout(timer);resolve(end);} catch(error) {clearTimeout(timer);reject(error);}}
    /** Check the first callback and request the second from inside it. @returns Nothing. */
    function first():void {try {match(current(),expected);requestAnimationFrame(second);} catch(error) {clearTimeout(timer);reject(error);}}
    requestAnimationFrame(first);
  }
  return new Promise(executor);
}
/** Apply one frozen toggle without changing registry order. @param module Prior candidate. @param edit Frozen toggle. @returns New candidate. */
function toggle(module:DraftModule,edit:Edit):DraftModule {
  let changed=0;
  /** Toggle the matching owned reference. @param node Existing node. @returns Updated node. */
  function apply(node:DraftModule['nodes'][number]):DraftModule['nodes'][number] {if(node.id!==edit.nodeId) return node;requireState(node.tag==='signature_ref'&&node.targetId!==edit.targetId,'Unexpected pre-edit target.');changed++;return {...node,targetId:edit.targetId};}
  const nodes=module.nodes.map(apply);
  requireState(changed===1,'Missing or duplicate edited reference.');return {...module,nodes};
}
/** Obtain a node identity. @param node Owned node. @returns Identity. */
function nodeId(node:DraftModule['nodes'][number]):Id {return node.id;}
/** Match declaration A. @param sig Signature declaration. @returns Whether A. */
function isA(sig:DraftModule['signatures'][number]):boolean {return sig.id===A&&sig.name==='A';}
/** Match declaration B. @param sig Signature declaration. @returns Whether B. */
function isB(sig:DraftModule['signatures'][number]):boolean {return sig.id===B&&sig.name==='B';}
/** Validate deterministic input bounds and declaration identity. @param fixture Frozen fixture. @returns Nothing. */
function validateFixture(fixture:Fixture):void {
  const module=fixture.module,index=nodeIndex(module),ids=new Set(module.nodes.map(nodeId));
  requireState(ids.size===500&&module.nodes.length===500&&fixture.edits.length===1100,'Fixture count mismatch.');
  requireState(new TextEncoder().encode(fixture.source).length===2565,'Fixture source size mismatch.');
  requireState(module.signatures.some(isA)&&module.signatures.some(isB),'Fixture declaration mismatch.');
  /** Count owned tree depth. @param id Root identity. @returns Depth. */
  function depth(id:Id):number {const node=index.get(id);requireState(node,'Missing fixture node.');return 1+Math.max(0,...children(node).map(depth));}
  for(const pred of module.predicates) requireState(depth(pred.bodyId)<=32,'Fixture depth exceeded.');
}
/** Construct a rendered block identity. @param node Owned node. @returns Button ID. */
function blockId(node:DraftModule['nodes'][number]):string {return `block-${node.id}`;}
/** Read a rendered element ID. @param element DOM element. @returns Element identity string. */
function elementId(element:Element):string {return element.id;}
/** Check actual owned forest identities and target type text. @param module Expected module. @param edit Last edit. @returns Nothing. */
function verifyDom(module:DraftModule,edit:Edit):void {
  const forest=document.querySelector('[aria-label="Owned expression forest"]');requireState(forest,'Missing owned forest.');
  const buttons=Array.from(forest.querySelectorAll('button[id^="block-"]')),expected=new Set(module.nodes.map(blockId));
  /** Check a rendered button belongs to fixture. @param button Rendered button. @returns Membership. */
  function inExpected(button:Element):boolean {return expected.has(button.id);}
  /** Match the edited button. @param button Rendered button. @returns Identity match. */
  function isEdited(button:Element):boolean {return button.id===`block-${edit.nodeId}`;}
  requireState(buttons.length===500&&new Set(buttons.map(elementId)).size===500&&buttons.every(inExpected),'Rendered node set mismatch.');
  requireState(!forest.querySelector('[role="alert"]'),'Missing-node or depth alert.');
  const button=buttons.find(isEdited),name=edit.targetId===A?'A':edit.targetId===B?'B':'';
  requireState(name&&button?.textContent===`signature ref · ${name}`,'Edited target DOM mismatch.');
}
/** Prevent an orphaned timeout rejection if dispatch throws synchronously. @param error Rejection. @returns Nothing. */
function ignoreRejectedCommit(error:unknown):void {void error;}
/** Run one actual controller edit through commit and two frame opportunities. @param module Current candidate. @param edit Frozen event. @returns Updated candidate and elapsed milliseconds. */
async function step(module:DraftModule,edit:Edit):Promise<{module:DraftModule;elapsed:number;dispatch:number}> {
  const prior=current();requireState(prior,'Workbench not mounted.');requireState(prior.view.document.module===module,'Prior committed candidate changed.');
  /** Match the frozen target node. @param node Owned node. @returns Identity match. */
  function findEdited(node:DraftModule['nodes'][number]):boolean {return node.id===edit.nodeId;}
  const previous=module.nodes.find(findEdited);requireState(previous?.tag==='signature_ref','Missing prior target.');
  verifyDom(module,{nodeId:edit.nodeId,targetId:previous.targetId});const id=identity(prior),next=toggle(module,edit);
  const expected={...id,generation:id.generation+1},pending=arm(expected,prior.sequence);
  pending.promise.catch(ignoreRejectedCommit);const start=performance.now();
  try {changeModule(prior.controller,next);} catch(error) {pending.cancel();throw error;}
  await pending.promise;const end=await frames(expected);const elapsed=end-start;
  match(current(),expected);requireState(current()?.view.document.module===next,'Committed candidate mismatch.');verifyDom(next,edit);
  return {module:next,elapsed,dispatch:start};
}
/** Compare timing values numerically. @param a First value. @param b Second value. @returns Ordering. */
function numericOrder(a:number,b:number):number {return a-b;}
/** Validate one duration. @param value Duration. @returns Whether finite and nonnegative. */
function validSample(value:number):boolean {return Number.isFinite(value)&&value>=0;}
/** Format nearest-rank result using unrounded observations. @param samples Actual durations. @returns Summary. */
function statistics(samples:number[]):object {
  const sorted=[...samples].sort(numericOrder);requireState(sorted.length===1000&&sorted.every(validSample),'Invalid sample vector.');
  return {p50:sorted[499],p95:sorted[949],p99:sorted[989],classification:sorted[949]<50?'PASS':'FAIL'};
}
interface RunEvidence {
  status:string;samples:number[];warmupSamples:number[];reason?:string;statistics?:object;visibility:string[];cold:string;
  environment:object;resources:object[];limitation:string;refreshIntervalsMs?:number[];advisory?:object;fixture?:object;
  initialIdentity?:object;fixtureIdentity?:object;finalIdentity?:object;continuityChecks:number;startedUtc:string;errors:string[];finalDispatchMs?:number;resourceCoverage?:object;
}
/** Record pinned fixture facts outside all measured intervals. @param fixture Parsed fixture. @returns Reproducible fixture metadata. */
async function fixtureEvidence(fixture:Fixture):Promise<object> {
  const index=nodeIndex(fixture.module);
  /** Compute one owned subtree depth. @param id Owned identity. @returns Depth. */
  function depth(id:Id):number {const node=index.get(id);requireState(node,'Missing fixture node.');return 1+Math.max(0,...children(node).map(depth));}
  let maximum=0;for(const pred of fixture.module.predicates) maximum=Math.max(maximum,depth(pred.bodyId));
  return {fileSha256:EXPECTED,sourceSha256:await digest(fixture.source),sourceUtf8Bytes:new TextEncoder().encode(fixture.source).length,
    editSequenceSha256:await digest(JSON.stringify(fixture.edits)),nodeIdsSha256:await digest(JSON.stringify(fixture.module.nodes.map(nodeId))),
    expressionNodes:fixture.module.nodes.length,maximumDepth:maximum,warmupEvents:100,measuredEvents:1000};
}
/** Allocate a fresh incomplete run report. @returns Redacted evidence container. */
function newReport():RunEvidence {
  return {status:'INCOMPLETE',samples:[],warmupSamples:[],visibility:[],cold:'NOT_CONDUCTED',environment:browserEnvironment(),resources:[],
    limitation:'Pinned server-prefixed fixture declaration IDs may be foreign to the accepted document; preview is not authoritative acceptance.',
    continuityChecks:0,startedUtc:new Date().toISOString(),errors:[]};
}
/** Check initial state and inject the frozen draft through the real controller. @param fixture Frozen candidate. @param report Evidence container. @returns Initial mount identity. */
async function setup(fixture:Fixture,report:RunEvidence):Promise<Identity> {
  const initial=current();requireState(initial&&initial.view.document.accepted,'Open an accepted document first.');
  requireState(!initial.view.document.pending&&!initial.view.document.validationBody&&!initial.view.document.dirty,'Start with a clean accepted document and no pending operation.');
  const baseline=identity(initial);match(initial,baseline);report.initialIdentity=identityEvidence(initial);
  const pending=arm({...baseline,generation:baseline.generation+1},initial.sequence);pending.promise.catch(ignoreRejectedCommit);
  try {changeModule(initial.controller,fixture.module);} catch(error) {pending.cancel();throw error;}
  await pending.promise;const committed=current();requireState(committed,'Workbench unmounted during setup.');
  report.fixtureIdentity=identityEvidence(committed);return {...baseline,generation:baseline.generation+1};
}
/** Run the frozen sequence with persistent mount and document continuity. @param fixture Frozen fixture. @param baseline Setup identity. @param report Evidence. @param status Progress surface. @returns Nothing. */
async function runEdits(fixture:Fixture,baseline:Identity,report:RunEvidence,status:HTMLElement):Promise<void> {
  let module=fixture.module;
  for(let i=0;i<fixture.edits.length;i++) {
    match(current(),{...baseline,generation:baseline.generation+i});
    const result=await step(module,fixture.edits[i]);module=result.module;
    match(current(),{...baseline,generation:baseline.generation+i+1});report.continuityChecks++;
    if(i<100) report.warmupSamples.push(result.elapsed);else report.samples.push(result.elapsed);
    if(i===fixture.edits.length-1) report.finalDispatchMs=result.dispatch;
    requireState(report.visibility.length===0,'Visibility transition during benchmark.');status.textContent=`Benchmark ${i+1}/1100`;
  }
  const last=current();requireState(last,'Workbench unmounted at end.');report.finalIdentity=identityEvidence(last);
}
/** Execute the benchmark and retain evidence even when interrupted. @returns Completion. */
export async function runBenchmark():Promise<void> {
  const status=document.getElementById('benchmark-status');requireState(status,'Missing status.');const report=newReport();
  /** Record visibility transitions. @returns Nothing. */
  function visibility():void {report.visibility.push(`${performance.now()}:${document.visibilityState}`);}
  /** Record a runtime error without exposing private details. @returns Nothing. */
  function error():void {report.errors.push('window error');}
  /** Record an unhandled rejection without exposing private details. @returns Nothing. */
  function rejection():void {report.errors.push('unhandled rejection');}
  document.addEventListener('visibilitychange',visibility);window.addEventListener('error',error);window.addEventListener('unhandledrejection',rejection);
  try {
    requireState(await digest(fixtureText)===EXPECTED,'Fixture hash mismatch.');const fixture=JSON.parse(fixtureText) as Fixture;validateFixture(fixture);report.fixture=await fixtureEvidence(fixture);
    report.refreshIntervalsMs=await refreshSamples();const baseline=await setup(fixture,report);
    await runEdits(fixture,baseline,report,status);report.statistics=statistics(report.samples);
    const final=current();requireState(final&&report.finalDispatchMs!==undefined,'Missing final identity or dispatch boundary.');
    const advisory=await advisoryEvidence(report.finalDispatchMs,final);report.advisory=advisory;
    const coverage=resourceCapture.coverage();report.resourceCoverage=coverage;requireState(coverage.complete,'Resource coverage incomplete or unknown.');
    match(current(),{...baseline,generation:baseline.generation+1100});
    requireState(advisory.status==='SETTLED_OBSERVED','Advisory outcome not observed within deadline.');
    requireState(report.errors.length===0,'Browser runtime error observed.');requireState(report.visibility.length===0,'Visibility transition during evidence capture.');
    report.status='COMPLETE';
  } catch(error) {report.reason=error instanceof Error?error.message:String(error);}
  finally {observe(null);document.removeEventListener('visibilitychange',visibility);window.removeEventListener('error',error);window.removeEventListener('unhandledrejection',rejection);report.resources=resourceCapture.records();const coverage=resourceCapture.coverage();report.resourceCoverage=coverage;
    if(!coverage.complete) {report.status='INCOMPLETE';report.reason='Resource coverage incomplete or unknown.';}
    status.textContent=JSON.stringify(report,null,2);}
}
