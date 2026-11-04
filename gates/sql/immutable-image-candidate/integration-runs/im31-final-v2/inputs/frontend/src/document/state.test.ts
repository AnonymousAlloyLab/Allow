import {expect,test,vi} from 'vitest';
import type {Accepted,Artifact,Envelope,CommitData,Validation,Pending} from './types';
import {initialState,openAccepted,selectNode,editSource,applyValidation,applyCommit,clipboardCurrent,candidate} from './state';
import {emptyModule} from './model';
import {prepareCommit,sendPending,digest,validUnicode} from './api';
/** Build an immutable server-shaped accepted fixture. @param revision Accepted revision. @returns Server snapshot. */
function accepted(revision=1):Accepted {
  const artifact:Artifact={artifactId:`artifact-${revision}`,mode:'BLOCK_SUPPORTED',source:'',sourceHash:'hash',module:emptyModule() as Artifact['module'],occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:1,dependencyHash:'dependency'};
  return {documentId:'document',revision,headRevision:revision,artifact,provenance:null};
}
/** Build a successful durable receipt. @param revision Result revision. @returns Envelope. */
function receipt(revision:number):Envelope<CommitData> {
  const current=accepted(revision);
  return {protocol:1,requestId:'request',status:'COMMITTED',data:{documentId:current.documentId,revision,artifact:current.artifact,sourceHash:current.artifact.sourceHash,policyVersion:1,idRemapping:{},provenance:null}};
}
/** Bind source diagnostics to current exact serialized request. @returns Nothing. */
function rejectsStaleValidation():void {
  const state=openAccepted(initialState(),accepted()),body='exact serialized request',waiting={...state,validationBody:body};
  const validation:Validation={draftId:state.draftId,draftEpoch:state.epoch,baseRevision:state.baseRevision,requestHash:'hash',supportMode:'BLOCK_SUPPORTED',diagnostics:[],proposedSource:'projection',proposedSourceHash:'sourcehash'};
  expect(applyValidation(waiting,body,'hash',validation).preview).toBe('projection');
  const selected=selectNode(waiting,'node');
  expect(applyValidation(selected,body,'hash',validation)).toBe(selected);
  expect(applyValidation(waiting,body,'different',validation)).toBe(waiting);
  expect(applyValidation(waiting,'different','hash',validation)).toBe(waiting);
  expect(applyValidation(waiting,body,'hash',{...validation,baseRevision:0})).toBe(waiting);
}
/** Keep clipboard eligible after selection, invalid after content edits. @returns Nothing. */
function selectionClipboard():void {
  const state=openAccepted(initialState(),accepted()),clipboard={documentId:'document',baseRevision:state.baseRevision,draftId:state.draftId,contentGeneration:state.contentGeneration,nodeId:'source',cut:false};
  const copied={...state,clipboard},selected=selectNode(copied,'destination');
  expect(selected.epoch).toBeGreaterThan(copied.epoch);
  expect(selected.contentGeneration).toBe(copied.contentGeneration);
  expect(clipboardCurrent(selected)).toBe(true);
  expect(clipboardCurrent(editSource(selected,'invalid'))).toBe(false);
}
/** Preserve newer invalid drafts after a delayed accepted receipt. @returns Nothing. */
function lateCommit():void {
  const state=openAccepted(initialState(),accepted()),pending=prepareCommit('document',candidate(state),1,state.draftId,state.epoch);
  const newer=editSource({...state,pending},'invalid draft'),result=applyCommit(newer,pending,receipt(2));
  expect(result.source).toBe('invalid draft');expect(result.dirty).toBe(true);
  expect(result.accepted?.headRevision).toBe(2);expect(result.preview).toBe(null);
  const stale=applyCommit(result,pending,receipt(1));
  expect(stale.accepted?.headRevision).toBe(2);
  expect(openAccepted(result,accepted(1)).accepted?.headRevision).toBe(2);
}
/** Keep pending bytes on uncertain outcomes and accepted artifact on deterministic denial. @returns Nothing. */
function uncertainCommit():void {
  const state=openAccepted(initialState(),accepted()),pending=prepareCommit('document',candidate(state),1,state.draftId,state.epoch);
  const result=applyCommit({...state,pending},pending,{...receipt(2),status:'UNKNOWN_COMMIT_OUTCOME'});
  expect(result.pending).toBe(pending);expect(result.accepted).toBe(state.accepted);
  const denied=applyCommit(result,pending,{...receipt(2),status:'TYPE_MISMATCH'});
  expect(denied.pending).toBe(null);expect(denied.accepted).toBe(state.accepted);
}
/** Preserve explicit history cursor independently of newly appended head. @returns Nothing. */
function historyCursor():void {
  const state={...openAccepted(initialState(),accepted(3)),historyCursor:1};
  const pending:Pending={route:'/api/v1/documents/document/history-copy',method:'POST',key:'retained',body:'exact',draftId:state.draftId,epoch:state.epoch};
  const result=applyCommit(state,pending,receipt(4));
  expect(result.historyCursor).toBe(1);expect(result.accepted?.headRevision).toBe(4);
}
/** Reject invalid UTF16 before TextEncoder replacement. @returns Completion. */
async function strictUnicode():Promise<void> {
  expect(validUnicode('😀e\u0301\r\n')).toBe(true);expect(validUnicode('\ud800')).toBe(false);expect(validUnicode('\udc00')).toBe(false);
  await expect(digest('\ud800')).rejects.toThrow('surrogate');
  expect(await digest('a\r\n')).not.toBe(await digest('a\n'));
}
/** Retry byte-identical body with fresh bearer authority. @returns Completion. */
async function exactRetry():Promise<void> {
  const state=openAccepted(initialState(),accepted()),pending=prepareCommit('document',candidate(state),1,state.draftId,state.epoch),bodies:unknown[]=[],authorities:unknown[]=[];
  /** Capture only test payload identity. @param input Endpoint. @param init Fetch options. @returns Mock transport. */
  async function transport(input:RequestInfo|URL,init?:RequestInit):Promise<Response> {
    bodies.push(init?.body);authorities.push((init?.headers as Record<string,string>).Authorization);
    return new Response(JSON.stringify(receipt(2)),{status:200});
  }
  vi.stubGlobal('fetch',transport);
  try {await sendPending('first',pending);await sendPending('rotated',pending);expect(bodies).toEqual([pending.body,pending.body]);expect(authorities).toEqual(['Bearer first','Bearer rotated']);}
  finally {vi.unstubAllGlobals();}
}
test('validation requires exact request and current draft epoch/base',rejectsStaleValidation);
test('destination selection preserves content-generation clipboard eligibility',selectionClipboard);
test('late accepted commit preserves newer draft and monotone head',lateCommit);
test('uncertain commit retains bytes and deterministic rejection preserves accepted',uncertainCommit);
test('history cursor stays independent of appended head',historyCursor);
test('strict Unicode preserves exact CRLF bytes',strictUnicode);
test('lost-response retry resends exact body with fresh bearer',exactRetry);
