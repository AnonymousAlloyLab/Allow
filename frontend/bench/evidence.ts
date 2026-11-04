import {current} from './bridge';
import type {Committed} from './bridge';
import {resourceCapture} from './resources';

/** Return nonsecret identity from the committed view without exposing authority. @param value Committed view. @returns Document and generation evidence. */
export function identityEvidence(value:Committed):object {
  const state=value.view.document,accepted=state.accepted;
  return {documentId:accepted?.documentId??null,acceptedRevision:accepted?.revision??null,headRevision:accepted?.headRevision??null,
    baseRevision:state.baseRevision,draftId:state.draftId,draftEpoch:state.epoch,contentGeneration:state.contentGeneration,commitSequence:value.sequence};
}
/** Capture browser-reported machine and display information, excluding authority. @returns Browser environment metadata. */
export function browserEnvironment():object {
  const memory=(navigator as Navigator&{deviceMemory?:number}).deviceMemory;
  return {browser:navigator.userAgent,hardwareConcurrency:navigator.hardwareConcurrency,deviceMemoryGiB:memory??'unavailable',
    viewport:[innerWidth,innerHeight],devicePixelRatio,screen:[screen.width,screen.height],screenColorDepth:screen.colorDepth,
    visibility:document.visibilityState,clock:'performance.now',workerStartup:'excluded',physicalDisplayRefresh:'unknown'};
}
/** Sample browser animation-frame intervals outside the timed benchmark. @returns Consecutive callback intervals in milliseconds. */
export function refreshSamples():Promise<number[]> {
  /** Install bounded callbacks. @param resolve Completion. @param reject Failure. @returns Nothing. */
  function executor(resolve:(samples:number[])=>void,reject:(error:unknown)=>void):void {
    const times:number[]=[];
    /** Fail if callbacks are suppressed. @returns Nothing. */
    function timeout():void {reject(new Error('Refresh sampling timed out.'));}
    const timer=window.setTimeout(timeout,10000);
    /** Record one browser frame timestamp and request its successor. @param time Frame timestamp. @returns Nothing. */
    function next(time:number):void {
      times.push(time);
      if(times.length<13) {requestAnimationFrame(next);return;}
      clearTimeout(timer);const intervals:number[]=[];
      for(let i=1;i<times.length;i++) intervals.push(times[i]-times[i-1]);
      resolve(intervals);
    }
    requestAnimationFrame(next);
  }
  return new Promise(executor);
}
/** Match the retained validation request to the final committed identity. @param view Committed view. @param expected Final identity. @returns Whether exact current request identity matches. */
function matchingRequest(view:Committed,expected:Committed):boolean {
  const state=view.view.document,target=expected.view.document;
  if(view.mount!==expected.mount||view.controller.token!==expected.controller.token||state.accepted?.documentId!==target.accepted?.documentId||
     state.draftId!==target.draftId||state.baseRevision!==target.baseRevision||state.epoch!==target.epoch||state.contentGeneration!==target.contentGeneration||!state.validationBody) return false;
  try {
    const body:unknown=JSON.parse(state.validationBody);
    if(!body||typeof body!=='object') return false;
    const request=body as {draftId?:unknown;draftEpoch?:unknown;baseRevision?:unknown};
    return request.draftId===target.draftId&&request.draftEpoch===target.epoch&&request.baseRevision===target.baseRevision;
  } catch {return false;}
}
/** Wait for the ordinary final advisory request and its committed outcome. @param dispatch Final edit dispatch clock. @param expected Final committed identity. @returns Explicit outcome or timeout. */
export async function advisoryEvidence(dispatch:number,expected:Committed):Promise<{status:string;[key:string]:unknown}> {
  const deadline=performance.now()+10000;
  while(performance.now()<deadline) {
    const last=resourceCapture.validations(dispatch).at(-1),view=current();
    if(last&&view&&matchingRequest(view,expected)&&view.view.document.notice!=='Validating advisory draft…') {
      const state=view.view.document;
      return {status:last.responseStatus==='UNKNOWN_OR_ERROR'?'UNKNOWN_OR_ERROR':'SETTLED_OBSERVED',resource:last,notice:state.notice,
        validationPresent:!!state.validation,diagnostics:state.validation?.diagnostics??[],rejectionDiagnostics:state.rejectionDiagnostics,identity:identityEvidence(view)};
    }
    await delay();
  }
  const view=current();
  return {status:'NOT_SETTLED_WITHIN_10_SECONDS',notice:view?.view.document.notice??'workbench unmounted',
    identity:view?identityEvidence(view):null};
}
/** Wait briefly between advisory observations. @returns Completion. */
function delay():Promise<void> {
  /** Install a bounded timer. @param resolve Completion. @returns Nothing. */
  function executor(resolve:()=>void):void {window.setTimeout(resolve,100);}
  return new Promise(executor);
}
