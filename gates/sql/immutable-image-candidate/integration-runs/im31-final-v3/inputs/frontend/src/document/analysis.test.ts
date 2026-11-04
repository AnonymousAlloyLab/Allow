import {expect,test,vi} from 'vitest';
import type {Accepted,AnalysisDescriptor,Envelope} from './types';
import {emptyModule} from './model';
import {initialState,openAccepted,editSource,selectNode} from './state';
import type {AnalysisData,AnalysisSnapshot,AnalysisEvent,AcceptedAnalysisKey} from './analysis';
import {analysisSnapshot,analysisIdentity,currentAnalysis,runAnalysis,sameOptions} from './analysis';
/** Create exact artifact/descriptor/job metadata for finite identity checks. @returns Snapshot and matching job. */
function fixture():{snapshot:AnalysisSnapshot;data:AnalysisData} {
  const descriptor:AnalysisDescriptor={commandKey:'command',index:0,kind:'run',label:'run model',artifactId:'artifact',sourceHash:'hash',policyVersion:'policy',options:{scope:3,solver:'SAT4J'}};
  const artifact={artifactId:'artifact',mode:'BLOCK_SUPPORTED' as const,source:'',sourceHash:'hash',module:emptyModule() as Accepted['artifact']['module'],occurrences:[],trivia:[],analysisDescriptors:[descriptor],policyVersion:'policy',dependencyHash:'dependency'};
  const accepted:Accepted={documentId:'document/id',revision:2,headRevision:2,artifact,provenance:null};
  const state=openAccepted(initialState(),accepted),snapshot=analysisSnapshot(state,'command')!;
  const key:AcceptedAnalysisKey={documentId:accepted.documentId,acceptedRevision:2,draftEpoch:state.epoch,jobAnalysisKey:'analysis',artifactId:'artifact',sourceHash:'hash',policyVersion:'policy',dependencyHash:'dependency',commandKey:'command',options:descriptor.options};
  return {snapshot,data:{jobId:'job/id',acceptedAnalysisKey:key,historical:false,job:{jobId:'job/id',status:'QUEUED',sourceHash:'hash',revision:2,epoch:state.epoch,analysisKey:'analysis'}}};
}
/** Reject every substituted accepted key field and each underlying job identity field. @returns Nothing. */
function rejectsIdentitySubstitution():void {
  const {snapshot,data}=fixture();
  expect(analysisIdentity(data,snapshot)).toBe(true);
  for(const field of ['documentId','acceptedRevision','draftEpoch','jobAnalysisKey','artifactId','sourceHash','policyVersion','dependencyHash','commandKey','options'] as const) {
    const prior=data.acceptedAnalysisKey[field],changed=typeof prior==='number'?prior+1:typeof prior==='string'?`${prior}-other`:{scope:4};
    expect(analysisIdentity({...data,acceptedAnalysisKey:{...data.acceptedAnalysisKey,[field]:changed}},snapshot)).toBe(false);
  }
  for(const field of ['sourceHash','revision','epoch','analysisKey','jobId'] as const) {
    const prior=data.job[field],changed=typeof prior==='number'?prior+1:`${prior}-other`;
    expect(analysisIdentity({...data,job:{...data.job,[field]:changed}},snapshot)).toBe(false);
  }
  expect(analysisIdentity({...data,jobId:'other'},snapshot)).toBe(false);
  expect(sameOptions({a:1,b:[2,3]},{b:[2,3],a:1})).toBe(true);
  expect(sameOptions({a:[1,2]},{a:[2,1]})).toBe(false);
}
/** Historical responses and dirty/selection/command changes cannot enter Results as current. @returns Nothing. */
function suppressesHistorical():void {
  const {snapshot,data}=fixture(),state=openAccepted(initialState(),snapshot.accepted);
  expect(currentAnalysis({...data,historical:true},snapshot,snapshot)).toBe(false);
  expect(currentAnalysis(data,snapshot,{...snapshot,epoch:snapshot.epoch+1})).toBe(false);
  expect(currentAnalysis(data,snapshot,{...snapshot,descriptor:{...snapshot.descriptor,commandKey:'other'}})).toBe(false);
  expect(analysisSnapshot(editSource(state,'invalid'),'command')).toBe(null);
  expect(analysisSnapshot({...state,source:'different'},'command')).toBe(null);
  expect(currentAnalysis(data,snapshot,null)).toBe(false);
}
/** Poll the document-scoped endpoint and stop immediately at a matching bounded terminal job. @returns Completion. */
async function pollsDocumentJob():Promise<void> {
  vi.useFakeTimers();const {snapshot,data}=fixture(),paths:string[]=[],events:AnalysisEvent[]=[];
  /** Return one submitted queue and one matching completed job. @param path Endpoint. @param body Optional POST. @param signal Cancellation. @returns Response. */
  async function transport(path:string,body:string|undefined,signal:AbortSignal):Promise<Envelope<AnalysisData>> {
    void signal;paths.push(path);
    return {protocol:1,requestId:'request',status:body?'SUBMITTED':'OK',data:body?data:{...data,job:{...data.job,status:'SAT'}}};
  }
  /** Read an unchanged view. @returns Snapshot. */
  function current():AnalysisSnapshot {return snapshot;}
  /** Collect checked display events. @param event Checked analysis notification. @returns Nothing. */
  function emit(event:AnalysisEvent):void {events.push(event);}
  try {
    const run=runAnalysis({token:'private',snapshot,controller:new AbortController(),current,emit,transport});
    await vi.advanceTimersByTimeAsync(250);await run;
    expect(paths).toEqual(['/api/v1/documents/document%2Fid/analyze','/api/v1/documents/document%2Fid/analysis/job%2Fid']);
    expect(events.at(-1)?.data?.job.status).toBe('SAT');expect(vi.getTimerCount()).toBe(0);
  } finally {vi.useRealTimers();}
}
/** Suppress a delayed submission after a selection change without scheduling a poll. @returns Completion. */
async function delayedSubmission():Promise<void> {
  vi.useFakeTimers();const {snapshot,data}=fixture(),events:AnalysisEvent[]=[],paths:string[]=[];
  let view:AnalysisSnapshot|null=snapshot,release:((value:Envelope<AnalysisData>)=>void)|null=null;
  /** Hold the POST response until the draft changes. @param path Endpoint. @param body Optional POST. @param signal Lifetime. @returns Delayed response. */
  function transport(path:string,body:string|undefined,signal:AbortSignal):Promise<Envelope<AnalysisData>> {
    void body;void signal;paths.push(path);
    /** Capture the delayed transport continuation. @param resolve Response consumer. @returns Nothing. */
    function capture(resolve:(value:Envelope<AnalysisData>)=>void):void {release=resolve;}
    return new Promise(capture);
  }
  /** Read current draft presentation. @returns Snapshot or invalidated view. */
  function current():AnalysisSnapshot|null {return view;}
  /** Collect current/historical classifications. @param event Classification. @returns Nothing. */
  function emit(event:AnalysisEvent):void {events.push(event);}
  try {
    const run=runAnalysis({token:'private',snapshot,controller:new AbortController(),current,emit,transport});
    view={...snapshot,epoch:snapshot.epoch+1};
    const resolve=release as unknown as (value:Envelope<AnalysisData>)=>void;
    resolve({protocol:1,requestId:'response',status:'SUBMITTED',data});await run;
    expect(events).toHaveLength(1);expect(events[0].kind).toBe('historical');expect(events[0].data).toBe(null);expect(paths).toHaveLength(1);
  } finally {vi.useRealTimers();}
}
/** Stop polling when the server marks a result historical or substitutes the original job key. @param mismatch Substitute job key. @returns Completion. */
async function stalePoll(mismatch:boolean):Promise<void> {
  vi.useFakeTimers();const {snapshot,data}=fixture(),events:AnalysisEvent[]=[];let calls=0;
  /** Return an unusable delayed poll result. @param path Endpoint. @param body Optional POST. @param signal Lifetime. @returns Envelope. */
  async function transport(path:string,body:string|undefined,signal:AbortSignal):Promise<Envelope<AnalysisData>> {
    void path;void signal;calls++;
    const changed={...data,historical:!mismatch,acceptedAnalysisKey:{...data.acceptedAnalysisKey,jobAnalysisKey:mismatch?'other':'analysis'},job:{...data.job,status:'SAT' as const,analysisKey:mismatch?'other':'analysis'}};
    return {protocol:1,requestId:'request',status:body?'SUBMITTED':'OK',data:body?data:changed};
  }
  /** Read unchanged local view. @returns Snapshot. */
  function current():AnalysisSnapshot {return snapshot;}
  /** Capture event classifications. @param event Event. @returns Nothing. */
  function emit(event:AnalysisEvent):void {events.push(event);}
  try {const run=runAnalysis({token:'private',snapshot,controller:new AbortController(),current,emit,transport});await vi.advanceTimersByTimeAsync(250);await run;expect(calls).toBe(2);expect(events.at(-1)?.kind).toBe('historical');expect(events.at(-1)?.data).toBe(null);}
  finally {vi.useRealTimers();}
}
/** Stop all queued reads immediately when a component lifetime is aborted. @returns Completion. */
async function stopsOnUnmount():Promise<void> {
  vi.useFakeTimers();const {snapshot,data}=fixture(),controller=new AbortController();let calls=0;
  /** Return a queued initial job. @param path Endpoint. @param body Optional POST. @param signal Lifetime. @returns Envelope. */
  async function transport(path:string,body:string|undefined,signal:AbortSignal):Promise<Envelope<AnalysisData>> {void path;void body;void signal;calls++;return {protocol:1,requestId:'request',status:'SUBMITTED',data};}
  /** Read initial current state. @returns Snapshot. */
  function current():AnalysisSnapshot {return snapshot;}
  /** Discard events for this lifecycle-only test. @param event Checked analysis notification. @returns Nothing. */
  function emit(event:AnalysisEvent):void {void event;}
  try {const run=runAnalysis({token:'private',snapshot,controller,current,emit,transport});await vi.advanceTimersByTimeAsync(0);controller.abort('unmount');await run;await vi.advanceTimersByTimeAsync(15000);expect(calls).toBe(1);expect(vi.getTimerCount()).toBe(0);}
  finally {vi.useRealTimers();}
}
test('all accepted key/job identity fields are mandatory for current Results',rejectsIdentitySubstitution);
test('historical, dirty and selection/descriptor changes cannot display current evidence',suppressesHistorical);
test('bounded polling uses encoded document job endpoint and stops at SAT',pollsDocumentJob);
test('delayed submit after selection change is historical and never polls',delayedSubmission);
test('historical poll cannot restore a current badge',stalePoll.bind(null,false));
test('changed job analysis key cannot substitute a same-looking result',stalePoll.bind(null,true));
test('unmount cancellation removes timers and prevents further reads',stopsOnUnmount);
/** Bound repeated queued results to15seconds and leave no active client timer. @returns Completion. */
async function deadlineStopsQueuedWork():Promise<void> {
  vi.useFakeTimers();const {snapshot,data}=fixture(),events:AnalysisEvent[]=[];let calls=0;
  /** Keep the worker queued to test only client polling bounds. @param path Endpoint. @param body Optional POST. @param signal Lifetime. @returns Envelope. */
  async function transport(path:string,body:string|undefined,signal:AbortSignal):Promise<Envelope<AnalysisData>> {void path;void signal;calls++;return {protocol:1,requestId:'request',status:body?'SUBMITTED':'OK',data};}
  /** Read unchanged current artifact. @returns Snapshot. */
  function current():AnalysisSnapshot {return snapshot;}
  /** Record client timeout without claiming server cancellation. @param event Checked lifecycle notification. @returns Nothing. */
  function emit(event:AnalysisEvent):void {events.push(event);}
  try {
    const run=runAnalysis({token:'private',snapshot,controller:new AbortController(),current,emit,transport});
    await vi.advanceTimersByTimeAsync(15000);await run;
    expect(calls).toBeLessThanOrEqual(61);expect(events.at(-1)?.kind).toBe('timeout');expect(events.at(-1)?.data).toBe(null);
    expect(vi.getTimerCount()).toBe(0);
  } finally {vi.useRealTimers();}
}
test('queued worker results cannot cause unbounded client polling',deadlineStopsQueuedWork);
