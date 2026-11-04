import {expect,test,vi} from 'vitest';
import type {SetStateAction} from 'react';
import type {Accepted,Artifact} from './types';
import type {Controller,ViewState} from './controller';
import {validate} from './controller';
import {initialState,openAccepted,editSource} from './state';
import {digest} from './api';
import {AdvisoryValidator} from './advisory';
import {advisoryKey} from './useAdvisory';
/** Construct a controller with a dirty exact-source candidate and no persistence callback. @returns Controller fixture. */
function controllerFixture():Controller {
  const artifact:Artifact={artifactId:'artifact',mode:'TEXT_ONLY',source:'',sourceHash:'old',module:null,occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:'policy',dependencyHash:'dependency'};
  const accepted:Accepted={documentId:'document',revision:1,headRevision:1,artifact,provenance:null};
  const document=editSource(openAccepted(initialState(),accepted),'sig A {}\n');
  const current={current:{document,documents:[],target:0,history:null,direction:'UNDO' as const} as ViewState};
  /** Capture React-style state updates outside a browser. @param value Immutable view or reducer. @returns Nothing. */
  function set(value:SetStateAction<ViewState>):void {current.current=typeof value==='function'?value(current.current):value;}
  return {token:'private-test-authority',current,set};
}
/** Return an exact request-bound diagnostic envelope without a document commit. @param paths Captured endpoint paths. @param input Request target. @param init Request options. @returns Mock diagnostic response. */
async function diagnosticResponse(paths:string[],input:RequestInfo|URL,init?:RequestInit):Promise<Response> {
  paths.push(String(input));
  const body=String(init?.body),request=JSON.parse(body),source=request.candidate.source,sourceHash=await digest(source);
  const data={draftId:request.draftId,draftEpoch:request.draftEpoch,baseRevision:request.baseRevision,requestHash:await digest(body),supportMode:'BLOCK_SUPPORTED',diagnostics:[],proposedSource:source,proposedSourceHash:sourceHash,sourceHash};
  return new Response(JSON.stringify({protocol:1,requestId:'request',status:'VALIDATED',data}),{status:200});
}
/** Automatic advisory execution uses only validate, preserves accepted revision, and never retries unchanged input. @returns Completion. */
async function neverCommits():Promise<void> {
  vi.useFakeTimers();const controller=controllerFixture(),scheduler=new AdvisoryValidator(),paths:string[]=[];
  const accepted=controller.current.current.document.accepted,key=advisoryKey(controller.current.current.document);
  let work:Promise<void>|null=null;
  /** Invoke the same diagnostic-only controller path used by live projection. @param signal Bounded scheduler lifetime. @returns Completion. */
  function run(signal:AbortSignal):Promise<void> {work=validate(controller,signal);return work;}
  vi.stubGlobal('fetch',diagnosticResponse.bind(null,paths));
  try {
    scheduler.request({key,run});await vi.advanceTimersByTimeAsync(350);await work;
    expect(paths).toEqual(['/api/v1/documents/document/validate']);
    expect(controller.current.current.document.accepted).toBe(accepted);
    expect(controller.current.current.document.dirty).toBe(true);
    expect(controller.current.current.document.preview).toBe('sig A {}\n');
    scheduler.request({key,run});await vi.advanceTimersByTimeAsync(10000);expect(paths).toHaveLength(1);
  } finally {scheduler.dispose();vi.unstubAllGlobals();vi.useRealTimers();}
}
test('live source projection calls validate only, never commits, and deduplicates unchanged draft',neverCommits);
