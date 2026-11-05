import type {Expression,Id} from './types';
import type {DocumentState} from './state';
export type Gesture = {readonly nonce:string;readonly snapshot:string;readonly kind:'palette';readonly tag:Expression['tag'];readonly target:Id;readonly name:string}|{readonly nonce:string;readonly snapshot:string;readonly kind:'node';readonly source:Id};
export type Fit = {readonly kind:'compatible'|'incompatible'|'unresolved';readonly message:string};
/** Bind gesture ownership to content rather than selection. @param state Current document. @returns Stable identity. */
export function contentSnapshot(state:DocumentState):string {return JSON.stringify([state.accepted?.documentId,state.baseRevision,state.draftId,state.contentGeneration]);}
/** Describe an unfinished gesture without overwriting a completed drop. @param active Current gesture or null after drop. @param fit Last destination preview. @returns Cancellation notice or null. */
export function dragEndNotice(active:Gesture|null,fit:Fit|null):string|null {
  if(!active) return null;
  return fit?.kind==='incompatible'?`${fit.message} Draft unchanged.`:'Drag canceled or outside a typed slot; draft unchanged.';
}
