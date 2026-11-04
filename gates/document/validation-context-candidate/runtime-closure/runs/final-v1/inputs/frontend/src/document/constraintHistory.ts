import type {DocumentState} from './state';
import type {CommitData,Pending,SlotObligation} from './types';
import {remapObligations,retainObligations} from './obligations';
export interface ObligationSnapshot {readonly documentId:string;readonly revision:number;readonly obligations:readonly SlotObligation[]}
export interface PendingObligations {readonly key:string;readonly obligations:readonly SlotObligation[]}
/** Retrieve only constraints actually retained for an accepted revision in this tab. @param state Current draft and history. @param documentId Accepted document identity. @param revision Exact retained revision. @returns Known explicit constraints or no invented obligations. */
export function revisionObligations(state:DocumentState,documentId:string,revision:number):readonly SlotObligation[] {
  for(const snapshot of state.obligationHistory) if(snapshot.documentId===documentId&&snapshot.revision===revision) return snapshot.obligations;
  return [];
}
/** Capture the exact draft-side obligations associated with a pending request. @param state Original transaction state. @param pending Exact pending request. @param obligations Snapshot matching the candidate or history target. @returns State containing private pending constraints only. */
export function capturePendingObligations(state:DocumentState,pending:Pending,obligations:readonly SlotObligation[]):DocumentState {
  return {...state,pendingObligations:{key:pending.key,obligations}};
}
/** Retain nonempty accepted constraints after authorized server identity remapping. @param state Current state, possibly with a newer draft. @param pending Completed exact request. @param data Successful server receipt. @returns State with matching immutable revision constraints cached in this tab. */
export function rememberObligations(state:DocumentState,pending:Pending,data:CommitData):DocumentState {
  const snapshot=state.pendingObligations;
  if(snapshot?.key!==pending.key) return state;
  const remap=new Map(Object.entries(data.idRemapping)),module=data.artifact.module;
  const obligations=module?retainObligations(module,remapObligations(snapshot.obligations,remap)):[],history:ObligationSnapshot[]=[];
  for(const item of state.obligationHistory) if(item.documentId!==data.documentId||item.revision!==data.revision) history.push(item);
  if(obligations.length) history.push({documentId:data.documentId,revision:data.revision,obligations});
  return {...state,obligationHistory:history,pendingObligations:null};
}
