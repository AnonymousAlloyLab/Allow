import type {DocumentState} from '../state';
import {candidate,editSource,selectNode} from '../state';
import {digest} from '../api';
import type {Job,Receipt,Snapshot,Undo} from './types';
/** Capture all current content and authority identity without using a stale preview. @param state Current draft. @returns Exact identity string. */
export function identity(state:DocumentState):string {return JSON.stringify([state.accepted,state.baseRevision,state.draftId,state.epoch,state.contentGeneration,state.mode,state.module,state.source,state.copies,state.slotObligations,state.selected,state.pending]);}
/** Capture the complete candidate and prior local state. @param state Current draft. @returns Snapshot. @throws Error Missing or incomplete model. */
export function capture(state:DocumentState):Snapshot {if(!state.accepted||state.pending) throw new Error('Open a model and finish any pending save first.');return {key:identity(state),document:state,candidate:candidate(state)};}
/** Validate receipt bytes and server proposal agreement before local atomic comparison. @param receipt Exact receipt. @param job Current reviewed job. @returns Whether receipt matches. */
export async function matching(receipt:Receipt,job:Job):Promise<boolean> {return !!job.proposal&&receipt.jobId===job.id&&receipt.binding===job.binding&&receipt.proposalHash===job.proposal.proposalHash&&receipt.source===job.proposal.source&&receipt.sourceHash===job.proposal.sourceHash&&await digest(receipt.source)===receipt.sourceHash;}
/** Publish one source edit only against the exact captured draft and live receipt. @param state Actual latest draft. @param snapshot Original binding. @param receipt Matched receipt. @param consumed Consumed receipt IDs. @param now Current wall time. @returns New draft and one-use undo or null. */
export function apply(state:DocumentState,snapshot:Snapshot,receipt:Receipt,consumed:Set<string>,now=Date.now()):{document:DocumentState;undo:Undo}|null {
  if(identity(state)!==snapshot.key||state.pending||now>=Date.parse(receipt.expiresAt)||consumed.has(receipt.receiptId)) return null;
  consumed.add(receipt.receiptId);
  const document={...editSource(state,receipt.source),notice:'AI edit applied to draft. Review it, then explicitly Save version.'};
  return {document,undo:{prior:state,appliedKey:identity(document),receiptId:receipt.receiptId}};
}
/** Restore complete prior content with a fresh generation while retaining accepted knowledge. @param state Current actual draft. @param undo Single AI transaction. @returns Restored draft or null after any intervening operation. */
export function undoEdit(state:DocumentState,undo:Undo):DocumentState|null {
  if(identity(state)!==undo.appliedKey||state.pending) return null;
  return {...selectNode(undo.prior,undo.prior.selected),accepted:state.accepted,epoch:state.epoch+1,contentGeneration:state.contentGeneration+1,validation:null,validationBody:null,preview:null,historicalPreview:null,clipboard:null,rejectionDiagnostics:[],notice:'Undid AI draft edit. Your saved version is unchanged.'};
}
