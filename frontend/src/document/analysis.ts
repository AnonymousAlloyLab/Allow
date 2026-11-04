import type {Job} from '../api';
import type {Accepted,AnalysisDescriptor,Envelope} from './types';
import type {DocumentState} from './state';
import {BASE,request,serializeRequest} from './api';
export interface AcceptedAnalysisKey {
  readonly documentId:string;readonly acceptedRevision:number;readonly draftEpoch:number;readonly jobAnalysisKey:string;
  readonly artifactId:string;readonly sourceHash:string;readonly policyVersion:string|number;readonly dependencyHash:string;
  readonly commandKey:string;readonly options:Readonly<Record<string,unknown>>;
}
export interface AnalysisData {readonly jobId:string;readonly acceptedAnalysisKey:AcceptedAnalysisKey;readonly historical?:boolean;readonly job:Job}
export interface AnalysisSnapshot {readonly accepted:Accepted;readonly descriptor:AnalysisDescriptor;readonly draftId:string;readonly epoch:number;readonly contentGeneration:number}
export interface AnalysisEvent {readonly kind:'current'|'historical'|'unavailable'|'timeout'|'waiting';readonly data:AnalysisData|null;readonly notice:string}
export interface AnalysisSession {
  readonly token:string;readonly snapshot:AnalysisSnapshot;readonly controller:AbortController;
  readonly current:()=>AnalysisSnapshot|null;readonly emit:(event:AnalysisEvent)=>void;
  readonly transport?:AnalysisTransport;
}
/** Authenticated analysis exchange contract, injectable for finite delayed-response tests. @param path Exact endpoint. @param body Exact POST body or omitted GET. @param signal Bounded cancellation. @returns Analysis envelope. */
export type AnalysisTransport=(path:string,body:string|undefined,signal:AbortSignal)=>Promise<Envelope<AnalysisData>>;
/** Compare immutable JSON options independent of object key insertion order. @param left First bounded option value. @param right Second value. @returns Exact structural equality. */
export function sameOptions(left:unknown,right:unknown):boolean {
  if(left===right) return true;
  if(!left||!right||typeof left!=='object'||typeof right!=='object'||Array.isArray(left)!==Array.isArray(right)) return false;
  const a=Object.keys(left).sort(),b=Object.keys(right).sort();
  if(a.length!==b.length) return false;
  for(let i=0;i<a.length;i++) {
    if(a[i]!==b[i]||!sameOptions((left as Record<string,unknown>)[a[i]],(right as Record<string,unknown>)[b[i]])) return false;
  }
  return true;
}
/** Capture only a current exact accepted source and its authorized command descriptor. @param state Current draft. @param command Selected opaque command key. @returns Snapshot or unavailable current evidence. */
export function analysisSnapshot(state:DocumentState,command:string):AnalysisSnapshot|null {
  const accepted=state.accepted;
  if(!accepted||state.dirty||state.source!==accepted.artifact.source||accepted.headRevision!==accepted.revision) return null;
  for(const descriptor of accepted.artifact.analysisDescriptors) {
    if(descriptor.commandKey===command&&descriptor.artifactId===accepted.artifact.artifactId&&descriptor.sourceHash===accepted.artifact.sourceHash&&descriptor.policyVersion===accepted.artifact.policyVersion) {
      return {accepted,descriptor,draftId:state.draftId,epoch:state.epoch,contentGeneration:state.contentGeneration};
    }
  }
  return null;
}
/** Compare every accepted and presentation identity before displaying current evidence. @param origin Submitted snapshot. @param current Current selection. @returns Exact current identity. */
export function snapshotCurrent(origin:AnalysisSnapshot,current:AnalysisSnapshot|null):boolean {
  if(!current) return false;
  const a=origin.accepted,b=current.accepted;
  return origin.draftId===current.draftId&&origin.epoch===current.epoch&&origin.contentGeneration===current.contentGeneration
    &&a.documentId===b.documentId&&a.revision===b.revision&&a.artifact.artifactId===b.artifact.artifactId
    &&a.artifact.source===b.artifact.source&&a.artifact.sourceHash===b.artifact.sourceHash
    &&a.artifact.policyVersion===b.artifact.policyVersion&&a.artifact.dependencyHash===b.artifact.dependencyHash
    &&origin.descriptor.commandKey===current.descriptor.commandKey&&sameOptions(origin.descriptor.options,current.descriptor.options);
}
/** Verify all server key fields and underlying job identity against an accepted snapshot. @param data Returned job envelope. @param snapshot Exact expected artifact/descriptor. @param original Optional original job key. @returns Bound response identity. */
export function analysisIdentity(data:AnalysisData,snapshot:AnalysisSnapshot,original?:AcceptedAnalysisKey):boolean {
  if(!data?.job||!data.acceptedAnalysisKey) return false;
  const key=data.acceptedAnalysisKey,accepted=snapshot.accepted,artifact=accepted.artifact,job=data.job;
  return key.documentId===accepted.documentId&&key.acceptedRevision===accepted.revision&&key.draftEpoch===snapshot.epoch
    &&key.artifactId===artifact.artifactId&&key.sourceHash===artifact.sourceHash&&key.policyVersion===artifact.policyVersion
    &&key.dependencyHash===artifact.dependencyHash&&key.commandKey===snapshot.descriptor.commandKey
    &&sameOptions(key.options,snapshot.descriptor.options)&&typeof key.jobAnalysisKey==='string'&&key.jobAnalysisKey.length>0
    &&job.jobId===data.jobId&&job.sourceHash===key.sourceHash&&job.revision===key.acceptedRevision
    &&job.epoch===key.draftEpoch&&job.analysisKey===key.jobAnalysisKey
    &&(!original||sameOptions(key,original));
}
/** Permit Results only for nonhistorical, fully matched current evidence. @param data Response. @param origin Submitted snapshot. @param current Current snapshot. @returns Safe current result. */
export function currentAnalysis(data:AnalysisData,origin:AnalysisSnapshot,current:AnalysisSnapshot|null):boolean {
  return data.historical!==true&&snapshotCurrent(origin,current)&&analysisIdentity(data,origin);
}
/** Recognize bounded worker terminal outcomes. @param job Job. @returns No further polling needed. */
function terminal(job:Job):boolean {return job.status!=='QUEUED'&&job.status!=='RUNNING';}
/** Abort browser waiting at the fixed wall deadline; this does not claim server cancellation. @param controller Session controller. @returns Nothing. */
function deadline(controller:AbortController):void {controller.abort('deadline');}
/** Send a bounded authenticated exchange. @param session Current run. @param path Exact endpoint. @param body Optional POST bytes. @returns Envelope. */
async function exchange(session:AnalysisSession,path:string,body?:string):Promise<Envelope<AnalysisData>> {
  if(session.transport) return session.transport(path,body,session.controller.signal);
  return request(session.token,path,body,session.controller.signal);
}
/** Publish a response only after identity and live-selection checks. @param session Run. @param data Response. @param original Initial job key. @returns Whether polling may continue. */
function deliver(session:AnalysisSession,data:AnalysisData,original?:AcceptedAnalysisKey):boolean {
  if(session.controller.signal.aborted) return false;
  if(!analysisIdentity(data,session.snapshot,original)||data.historical===true||!snapshotCurrent(session.snapshot,session.current())) {
    session.emit({kind:'historical',data:null,notice:'This analysis belongs to an earlier model or command. Run the current model for a current result.'});
    return false;
  }
  session.emit({kind:'current',data,notice:terminal(data.job)?'Analysis finished within the selected bounds.':'Analyzing the saved model…'});
  return !terminal(data.job);
}
/** Poll at250ms with at most60 reads and an independent15s abort deadline. @param session Active run. @param initial Valid initial response. @returns Completion. */
async function poll(session:AnalysisSession,initial:AnalysisData):Promise<void> {
  for(let count=0;count<60;count++) {
    await pause(session.controller.signal);
    if(!snapshotCurrent(session.snapshot,session.current())) return;
    const path=`${BASE}/${encodeURIComponent(session.snapshot.accepted.documentId)}/analysis/${encodeURIComponent(initial.jobId)}`;
    const response=await exchange(session,path);
    if(response.status!=='OK'||typeof response.data?.historical!=='boolean') throw new Error('Analysis result is unavailable.');
    if(!deliver(session,response.data,initial.acceptedAnalysisKey)) return;
  }
  session.emit({kind:'timeout',data:null,notice:'Stopped waiting for analysis. You can run the saved model again.'});
}
/** Submit and track one bounded accepted analysis session. @param session Snapshot, authority and cancellation. @returns Completion with no unbounded background polling. */
export async function runAnalysis(session:AnalysisSession):Promise<void> {
  const timer=setTimeout(deadline.bind(null,session.controller),15000),snapshot=session.snapshot;
  try {
    const body=serializeRequest({acceptedRevision:snapshot.accepted.revision,commandKey:snapshot.descriptor.commandKey,draftEpoch:snapshot.epoch,exactSourceHash:snapshot.accepted.artifact.sourceHash});
    const response=await exchange(session,`${BASE}/${encodeURIComponent(snapshot.accepted.documentId)}/analyze`,body);
    if(response.status!=='SUBMITTED') throw new Error('Analysis could not be started.');
    if(deliver(session,response.data)) await poll(session,response.data);
  } catch(error) {
    if(session.controller.signal.reason==='deadline') session.emit({kind:'timeout',data:null,notice:'Stopped waiting after15 seconds. The saved model is unchanged.'});
    else if(!session.controller.signal.aborted) session.emit({kind:'unavailable',data:null,notice:error instanceof Error?error.message:'Analysis unavailable.'});
  } finally {clearTimeout(timer);}
}
/** Schedule one abortable polling interval. @param signal Session lifetime. @param resolve Successful timer. @param reject Cancellation. @returns Nothing. */
function schedule(signal:AbortSignal,resolve:()=>void,reject:(reason:unknown)=>void):void {
  /** Clear the session listener after the timer fires. @returns Nothing. */
  function done():void {signal.removeEventListener('abort',cancel);resolve();}
  /** Clear the timer immediately on cancellation. @returns Nothing. */
  function cancel():void {clearTimeout(timer);signal.removeEventListener('abort',cancel);reject(new DOMException('Analysis wait aborted','AbortError'));}
  const timer=setTimeout(done,250);
  if(signal.aborted) {cancel();return;}
  signal.addEventListener('abort',cancel,{once:true});
}
/** Wait without issuing requests after cancellation. @param signal Session lifetime. @returns Bounded delay. */
function pause(signal:AbortSignal):Promise<void> {return new Promise(schedule.bind(null,signal));}
