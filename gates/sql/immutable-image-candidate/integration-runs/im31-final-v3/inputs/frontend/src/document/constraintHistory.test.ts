import {expect,test} from 'vitest';
import type {Accepted,Artifact,CommitData,DraftModule,Envelope,Module,Pending,SlotObligation} from './types';
import {initialState,openAccepted,editModule,applyCommit,candidate} from './state';
import {capturePendingObligations,revisionObligations} from './constraintHistory';
/** Build a complete module using either draft or accepted occurrence identities. @param prefix Identity namespace. @returns Valid nominal module. */
function historyModule(prefix:string):DraftModule {
  return {version:1,signatures:[{tag:'signature',id:`${prefix}A`,name:'A',multiplicity:'set'}],fields:[],predicates:[],assertions:[],commands:[],facts:[{tag:'fact',id:`${prefix}fact`,name:'savedFact',bodyId:`${prefix}main`}],nodes:[{tag:'some_test',id:`${prefix}main`,operandId:`${prefix}reference`},{tag:'signature_ref',id:`${prefix}reference`,targetId:`${prefix}A`}]};
}
/** Construct a complete immutable accepted revision for history tests. @param revision Exact server revision. @param prefix Server identity namespace. @returns Accepted snapshot. */
function accepted(revision:number,prefix='server:'):Accepted {
  const artifact:Artifact={artifactId:`artifact${revision}`,mode:'BLOCK_SUPPORTED',source:'sig A {} fact savedFact { some A }',sourceHash:`hash${revision}`,module:historyModule(prefix) as Module,occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:1,dependencyHash:'dependency'};
  return {documentId:'document',revision,headRevision:revision,artifact,provenance:null};
}
/** Build an existing-format commit receipt with authorized draft identity remapping. @param revision New accepted revision. @returns Successful envelope. */
function receipt(revision:number):Envelope<CommitData> {
  const snapshot=accepted(revision),idRemapping={'draft:A':'server:A','draft:fact':'server:fact','draft:main':'server:main','draft:reference':'server:reference'};
  return {protocol:1,requestId:'request',status:'COMMITTED',data:{documentId:'document',revision,artifact:snapshot.artifact,sourceHash:snapshot.artifact.sourceHash,policyVersion:1,idRemapping,provenance:null}};
}
/** Retain a private sidecar for a complete draft without adding anything to its wire candidate. @returns Draft, exact pending request, and immutable obligations. */
function prepared():{state:ReturnType<typeof initialState>;pending:Pending;obligations:readonly SlotObligation[]} {
  const obligations:readonly SlotObligation[]=[{slot:{ownerId:'draft:main',role:'operand'},expected:{kind:'relation',columns:['draft:A']}}];
  const base=openAccepted(initialState(),accepted(1)),state=editModule(base,historyModule('draft:'),'draft:reference',[],obligations);
  const pending:Pending={route:'/api/v1/documents/document/commit',method:'POST',body:JSON.stringify({candidate:candidate(state)}),key:'pendingKey',draftId:state.draftId,epoch:state.epoch};
  return {state:capturePendingObligations({...state,pending},pending,obligations),pending,obligations};
}
/** Remap only private sidecar identities on successful commit and retain immutable revision history. @returns Nothing. */
function commitRemapsObligations():void {
  const fixture=prepared(),result=applyCommit(fixture.state,fixture.pending,receipt(2));
  const expected=[{slot:{ownerId:'server:main',role:'operand'},expected:{kind:'relation',columns:['server:A']}}];
  expect(result.slotObligations).toEqual(expected);expect(result.pendingObligations).toBeNull();expect(result.obligationHistory).toHaveLength(1);
  expect(revisionObligations(result,'document',2)).toBe(result.slotObligations);expect(fixture.state.slotObligations).toBe(fixture.obligations);
  expect(fixture.state.obligationHistory).toEqual([]);expect(fixture.pending.body).not.toContain('slotObligations');expect(fixture.pending.body).not.toContain('pendingObligations');
}
/** Preserve the exact earlier pending constraint snapshot when a newer draft survives a delayed receipt. @returns Nothing. */
function lateCommitUsesCapturedSidecar():void {
  const fixture=prepared(),newerObligations:readonly SlotObligation[]=[];
  const newer=editModule(fixture.state,fixture.state.module,fixture.state.selected,[],newerObligations),result=applyCommit(newer,fixture.pending,receipt(2));
  expect(result.slotObligations).toBe(newerObligations);expect(result.module).toBe(newer.module);expect(result.accepted?.revision).toBe(2);
  expect(revisionObligations(result,'document',2)).toHaveLength(1);expect(fixture.state.pendingObligations?.obligations).toBe(fixture.obligations);
}
/** Reload cached constraints through undo and redo snapshots without inventing constraints for unknown versions. @returns Nothing. */
function historyRetainsKnownConstraints():void {
  const fixture=prepared(),saved=applyCommit(fixture.state,fixture.pending,receipt(2)),old=openAccepted(saved,accepted(3));
  expect(old.slotObligations).toEqual([]);expect(old.obligationHistory).toBe(saved.obligationHistory);
  const historical={...accepted(2),headRevision:3},restored=openAccepted(old,historical);
  expect(restored.slotObligations).toBe(saved.slotObligations);expect(restored.accepted?.revision).toBe(2);
  const pending:Pending={...fixture.pending,route:'/api/v1/documents/document/history-copy',key:'restoreKey',draftId:restored.draftId,epoch:restored.epoch};
  const waiting=capturePendingObligations({...restored,pending,historyCursor:2},pending,revisionObligations(restored,'document',2));
  const reapplied=applyCommit(waiting,pending,receipt(4));expect(reapplied.slotObligations).toEqual(saved.slotObligations);expect(reapplied.historyCursor).toBe(2);
  expect(revisionObligations(reapplied,'document',4)).toEqual(saved.slotObligations);
}
/** Retain pending sidecars only for retryable uncertain outcomes and discard them after deterministic denial. @returns Nothing. */
function pendingSidecarLifetime():void {
  const fixture=prepared(),uncertain=applyCommit(fixture.state,fixture.pending,{...receipt(2),status:'UNKNOWN_COMMIT_OUTCOME'});
  expect(uncertain.pendingObligations).toBe(fixture.state.pendingObligations);expect(uncertain.slotObligations).toBe(fixture.obligations);
  const rejected=applyCommit(uncertain,fixture.pending,{...receipt(2),status:'TYPE_MISMATCH'});
  expect(rejected.pendingObligations).toBeNull();expect(rejected.slotObligations).toBe(fixture.obligations);expect(rejected.obligationHistory).toEqual([]);
}
test('PT-028 accepted receipt remaps draft-only constraints without wire changes',commitRemapsObligations);
test('PT-028 delayed receipt uses captured sidecar and preserves newer local constraints',lateCommitUsesCapturedSidecar);
test('PT-028 undo and redo preserve known in-tab revision obligations',historyRetainsKnownConstraints);
test('retryable uncertainty retains pending obligations and deterministic denial releases only the pending capture',pendingSidecarLifetime);
