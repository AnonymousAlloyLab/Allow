import type {MutableRefObject,Dispatch,SetStateAction} from 'react';
import type {DocumentState} from './state';
import type {DocumentSummary,Id,DraftModule,Expression,Pending,Envelope,CommitData,Accepted} from './types';
import {listDocuments,readDocument,BASE,prepareCommit,prepareHistory,sendPending,validateDraft,digest,serializeRequest} from './api';
import {selectNode,editModule,editSource,openAccepted,candidate,applyValidation,applyCommit,clipboardCurrent} from './state';
import {checkModule,nodeIndex} from './model';
import {fieldTransitionNotice} from './fieldOrder';
import {capturePendingObligations,revisionObligations} from './constraintHistory';
import {contentSnapshot,type Gesture,type Fit} from './gesture';
import {construct,hole,replacement,newContradiction,paste,retainCopies,type Clipboard,type EditResult} from './operations';
export interface ViewState {readonly document:DocumentState;readonly documents:readonly DocumentSummary[];readonly target:number;readonly history:Accepted|null;readonly direction:'UNDO'|'REDO'}
export interface Controller {readonly token:string;readonly current:MutableRefObject<ViewState>;readonly set:Dispatch<SetStateAction<ViewState>>}
/** Publish a synchronous snapshot so asynchronous completions inspect latest state. @param c Controller. @param next New view. @returns Nothing. */
export function publish(c:Controller,next:ViewState):void {c.current.current=next;c.set(next);}
/** Publish only document state. @param c Controller. @param document New document draft. @returns Nothing. */
export function publishDocument(c:Controller,document:DocumentState):void {publish(c,{...c.current.current,document});}
/** Announce an operation without changing content. @param c Controller. @param notice Message. @returns Nothing. */
export function announce(c:Controller,notice:string):void {publishDocument(c,{...c.current.current.document,notice});}
/** Refresh authenticated local document inventory. @param c Controller. @returns Completion. */
export async function refresh(c:Controller):Promise<void> {
  try {const result=await listDocuments(c.token);if(result.data.documents) publish(c,{...c.current.current,documents:result.data.documents});else announce(c,result.status);}
  catch(error) {announce(c,errorMessage(error));}
}
/** Format a transport failure without asserting rollback. @param error Unknown failure. @returns Message. */
export function errorMessage(error:unknown):string {return error instanceof Error?error.message:'Request unavailable; accepted commit outcome may require recovery.';}
/** Open a selected server head after explicit navigation. @param c Controller. @param id Document ID. @returns Completion. */
export async function openDocument(c:Controller,id:string):Promise<void> {
  const snapshot=selectNode(c.current.current.document,null);publishDocument(c,snapshot);
  try {const result=await readDocument(c.token,id);if(c.current.current.document.epoch!==snapshot.epoch) return;if(result.data.artifact) publishDocument(c,openAccepted(c.current.current.document,result.data));else announce(c,result.status);}
  catch(error) {announce(c,errorMessage(error));}
}
/** Create a fresh authorized document with retryable exact bytes. @param c Controller. @param title Display name. @returns Completion. */
export async function create(c:Controller,title:string):Promise<void> {
  const state=c.current.current.document;
  if(state.pending) {announce(c,'Recover the pending request before creating another document.');return;}
  const key=crypto.randomUUID(),pending:Pending={route:BASE,method:'POST',body:JSON.stringify({idempotencyKey:key,title}),key,draftId:state.draftId,epoch:state.epoch};
  publishDocument(c,{...state,pending,notice:'Creating document; exact request retained.'});
  await transmit(c,pending);
}
/** Recover or submit one identical pending request. @param c Controller. @param pending Frozen bytes. @returns Completion. */
export async function transmit(c:Controller,pending:Pending):Promise<void> {
  try {
    const result=await sendPending(c.token,pending),current=c.current.current.document;
    if(current.pending&&current.pending.key!==pending.key) return;
    if(pending.route!==BASE&&current.accepted&&!pending.route.includes(`/${encodeURIComponent(current.accepted.documentId)}/`)) return;
    if(pending.route===BASE&&'documentId' in result.data&&result.data.documentId) {
      publishDocument(c,{...c.current.current.document,pending:null});await refresh(c);await openDocument(c,result.data.documentId);return;
    }
    publishDocument(c,applyCommit(c.current.current.document,pending,result));
    if(result.status==='COMMITTED') await refresh(c);
  } catch(error) {announce(c,`${errorMessage(error)} Exact pending bytes retained; use Retry.`);}
}
/** Submit the independently checked full candidate. @param c Controller. @returns Completion. */
export async function save(c:Controller):Promise<void> {
  const state=c.current.current.document;
  if(!state.accepted) return;
  if(state.pending) {announce(c,'Retry/recover the existing request first.');return;}
  try {
    const pending=prepareCommit(state.accepted.documentId,candidate(state),state.baseRevision,state.draftId,state.epoch);
    const captured=capturePendingObligations(state,pending,state.mode==='BLOCK_SUPPORTED'?state.slotObligations:[]);
    publishDocument(c,{...captured,pending,notice:'Saving candidate; acceptance awaits server commit receipt.'});await transmit(c,pending);
  } catch(error) {announce(c,errorMessage(error));}
}
/** Validate a frozen whole-request snapshot, rejecting stale responses. @param c Controller. @param signal Optional advisory lifetime cancellation. @returns Completion. */
export async function validate(c:Controller,signal?:AbortSignal):Promise<void> {
  const state=c.current.current.document;
  if(!state.accepted) return;
  try {
    const body=serializeRequest({draftId:state.draftId,draftEpoch:state.epoch,baseRevision:state.baseRevision,candidate:candidate(state)});
    publishDocument(c,{...state,validationBody:body,notice:'Validating advisory draft…'});
    const hash=await digest(body),result=await validateDraft(c.token,state.accepted.documentId,body,signal);
    if(signal?.aborted) return;
    if(!result.data||typeof result.data.requestHash!=='string') {if(c.current.current.document.epoch===state.epoch) announce(c,result.status);return;}
    if(result.data.proposedSource!==null&&await digest(result.data.proposedSource)!==result.data.proposedSourceHash) throw new Error('Server projection hash mismatch.');
    if(state.mode==='SOURCE'&&result.data.sourceHash!==await digest(state.source)) throw new Error('Source validation identity mismatch.');
    if(!signal?.aborted) publishDocument(c,applyValidation(c.current.current.document,body,hash,result.data));
  } catch(error) {if(!signal?.aborted&&c.current.current.document.epoch===state.epoch) announce(c,errorMessage(error));}
}
/** Change selected node and invalidate presentation only. @param c Controller. @param id Selection. @returns Nothing. */
export function select(c:Controller,id:Id):void {publishDocument(c,selectNode(c.current.current.document,id));}
/** Apply an explicit declaration change, retaining dependent errors. @param c Controller. @param module New forest. @returns Nothing. */
export function changeModule(c:Controller,module:DraftModule):void {
  const state=c.current.current.document,next=editModule(state,module,state.selected,retainCopies(state.copies,module));
  publishDocument(c,{...next,notice:fieldTransitionNotice(state.module,module)??'Declaration draft changed; dependencies rechecked before acceptance.'});
}
/** Edit exact raw source independently of accepted state. @param c Controller. @param source Draft. @returns Nothing. */
export function changeSource(c:Controller,source:string):void {publishDocument(c,editSource(c.current.current.document,source));}
/** Publish one validated content transaction or only the rejection notice against its original snapshot. @param c Controller. @param state Pre-operation state. @param result Prepared candidate. @param notice Successful operation notice. @returns Nothing. */
function applyEdit(c:Controller,state:DocumentState,result:EditResult,notice:string):void {
  if(result.error) {publishDocument(c,{...state,notice:result.error});return;}
  const next={...editModule(state,result.module,result.selected,result.copies,result.slotObligations),notice};
  publishDocument(c,next);focusLater(c,next,result.selected);
}
/** Prepare one palette replacement against the current state. @param state Current content. @param tag Closed operator. @param target Referent. @param name Binder. @param destination Owned slot. @returns Candidate or rejection. */
function prepareInsert(state:DocumentState,tag:Expression['tag'],target:Id,name:string,destination:Id):EditResult {
  if(!nodeIndex(state.module).has(destination)) return {module:state.module,copies:state.copies,selected:destination,slotObligations:state.slotObligations,error:'Destination is unavailable.'};
  const nodes=construct(tag,target,state.module,name),prepared=replacement(state.module,destination,nodes,state.slotObligations);
  const error=newContradiction(state.module,prepared.module,state.slotObligations,prepared.slotObligations);
  return {...prepared,copies:retainCopies(state.copies,prepared.module),selected:nodes[0].id,error};
}
/** Insert a closed typed palette node. @param c Controller. @param tag Operator. @param target Referent. @param name Binder label. @param destination Slot. @returns Nothing. */
export function insert(c:Controller,tag:Expression['tag'],target:Id,name:string,destination:Id):void {
  const state=c.current.current.document;applyEdit(c,state,prepareInsert(state,tag,target,name,destination),'Inserted draft block; server acceptance pending.');
}
/** Prepare a clipboard identity without publishing selection or changing existing clipboard state. @param state Pre-gesture snapshot. @param nodeId Source subtree. @param cut Move instead of clone. @returns Local clipboard descriptor or unavailable accepted context. */
function clipboardFor(state:DocumentState,nodeId:Id,cut:boolean):Clipboard|null {
  if(!state.accepted) return null;
  return {documentId:state.accepted.documentId,baseRevision:state.baseRevision,draftId:state.draftId,contentGeneration:state.contentGeneration,nodeId,cut};
}
/** Capture clipboard content identity, preserving native selection semantics. @param c Controller. @param cut Move instead of clone. @returns Nothing. */
export function copy(c:Controller,cut:boolean):void {
  const state=c.current.current.document,clipboard=state.selected?clipboardFor(state,state.selected,cut):null;
  if(clipboard) publishDocument(c,{...state,clipboard,notice:`${cut?'Cut':'Copied'} subtree. Select a destination then Paste.`});
}
/** Apply current clipboard to current destination as one draft transaction. @param c Controller. @returns Nothing. */
export function pasteClipboard(c:Controller):void {
  const state=c.current.current.document;
  if(!clipboardCurrent(state)||!state.clipboard||!state.selected) {announce(c,'Clipboard stale or missing. Copy/Cut current content again.');return;}
  const result=paste(state.module,state.clipboard,state.selected,state.copies,state.slotObligations);
  applyEdit(c,state,result,'Draft paste completed; scope and nominal schemas rechecked.');
}
/** Prepare, validate, and publish a drag using the untouched pre-gesture snapshot. @param c Controller. @param source Source ID. @param target Destination ID. @param clone Copy modifier. @returns Nothing. */
export function dropNode(c:Controller,source:Id,target:Id,clone:boolean):void {
  const state=c.current.current.document,clipboard=clipboardFor(state,source,!clone);
  if(!clipboard||!nodeIndex(state.module).has(source)) {publishDocument(c,{...state,notice:'Foreign or stale dragged source.'});return;}
  const result=paste(state.module,clipboard,target,state.copies,state.slotObligations);
  applyEdit(c,state,result,'Draft drop completed; scope and nominal schemas rechecked.');
}
/** Prepare an owned gesture without publishing. @param state Current document. @param gesture Frozen gesture. @param target Destination. @param clone Copy modifier. @returns Candidate or rejection. */
function prepareGesture(state:DocumentState,gesture:Gesture,target:Id,clone:boolean):EditResult {
  const rejected={module:state.module,copies:state.copies,selected:target,slotObligations:state.slotObligations,error:'Stale or foreign drag; draft unchanged.'};
  if(!state.accepted||gesture.snapshot!==contentSnapshot(state)||!nodeIndex(state.module).has(target)) return rejected;
  if(gesture.kind==='palette') return prepareInsert(state,gesture.tag,gesture.target,gesture.name,target);
  const clipboard=clipboardFor(state,gesture.source,!clone);
  return clipboard?paste(state.module,clipboard,target,state.copies,state.slotObligations):rejected;
}
/** Preview one destination with the same candidate rules used for final drop. @param c Controller. @param gesture Active owned descriptor. @param target Destination. @param clone Copy modifier. @returns Honest compatibility state. */
export function previewGesture(c:Controller,gesture:Gesture,target:Id,clone:boolean):Fit {
  const result=prepareGesture(c.current.current.document,gesture,target,clone);
  if(result.error) return {kind:'incompatible',message:result.error};
  const checked=checkModule(result.module,result.slotObligations),type=checked.types.get(result.selected);
  if(!type||!checked.complete) return {kind:'unresolved',message:'Potentially compatible; constraints remain unresolved.'};
  return {kind:'compatible',message:'Compatible with the checked slot constraints.'};
}
/** Recheck and publish one current owned drag transaction. @param c Controller. @param gesture Active owned descriptor. @param target Destination. @param clone Copy modifier. @returns Nothing. */
export function commitGesture(c:Controller,gesture:Gesture,target:Id,clone:boolean):void {
  const state=c.current.current.document;applyEdit(c,state,prepareGesture(state,gesture,target,clone),'Draft drop completed; scope and nominal schemas rechecked.');
}
/** Delete selected expression while retaining the owning destination's independent constraints. @param c Controller. @returns Nothing. */
export function removeSelected(c:Controller):void {
  const state=c.current.current.document;if(!state.selected) return;
  const next=hole(),prepared=replacement(state.module,state.selected,[next],state.slotObligations);
  const error=newContradiction(state.module,prepared.module,state.slotObligations,prepared.slotObligations);
  applyEdit(c,state,{...prepared,copies:retainCopies(state.copies,prepared.module),selected:next.id,error},'Deleted draft subtree; comments become visible orphans on block commit.');
}
/** Focus only the still-current successful content transition. @param c Controller. @param state Successful snapshot. @param id Surviving block. @returns Nothing. */
function focusBlock(c:Controller,state:DocumentState,id:Id):void {if(c.current.current.document===state) document.getElementById(`block-${id}`)?.focus();}
/** Schedule focus once after a successful immutable publication. @param c Controller. @param state Published successful snapshot. @param id Block. @returns Nothing. */
function focusLater(c:Controller,state:DocumentState,id:Id):void {window.setTimeout(focusBlock.bind(null,c,state,id),0);}
/** Preview an exact retained historical target. @param c Controller. @param target Revision. @param direction Navigation direction. @returns Completion. */
export async function previewHistory(c:Controller,target:number,direction:'UNDO'|'REDO'):Promise<void> {
  const state=c.current.current.document;if(!state.accepted||!Number.isSafeInteger(target)||target<0) return;
  publishDocument(c,selectNode(state,state.selected));
  try {const result=await readDocument(c.token,state.accepted.documentId,target);if(result.data.artifact) publish(c,{...c.current.current,target,direction,history:result.data});else announce(c,result.status);}
  catch(error) {announce(c,errorMessage(error));}
}
/** Commit explicit historical target only after preview/action. @param c Controller. @returns Completion. */
export async function restore(c:Controller):Promise<void> {
  const view=c.current.current,state=view.document,target=view.history;
  if(!target||!state.accepted||state.pending) return;
  if(target.documentId!==state.accepted.documentId) {announce(c,'Historical target belongs to a different document.');return;}
  const pending=prepareHistory(state.accepted.documentId,state.accepted.headRevision,target.revision,view.direction,state.draftId,state.epoch);
  const obligations=revisionObligations(state,target.documentId,target.revision),captured=capturePendingObligations(state,pending,obligations);
  const notice=obligations.length?'Appending historical content with retained in-tab constraints.':'Appending historical content; explicit constraint provenance is unavailable for this version in this tab.';
  publishDocument(c,{...captured,pending,historyCursor:target.revision,notice});await transmit(c,pending);
}

/** Cancel pending clipboard interaction without changing accepted content. @param c Controller. @returns Nothing. */
export function cancelInteraction(c:Controller):void {
  const state=c.current.current.document;
  publishDocument(c,{...state,clipboard:null,notice:'Pending clipboard interaction cancelled.'});
}
