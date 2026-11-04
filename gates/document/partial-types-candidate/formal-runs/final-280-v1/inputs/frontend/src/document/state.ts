import type {Accepted,DraftModule,Id,PresentationCopy,Validation,Pending,Candidate,Module,CommitData,Envelope,MutationData,Diagnostic} from './types';
import {emptyModule,checkModule,freshId} from './model';
import {validUnicode} from './api';
import type {Clipboard} from './operations';
export interface DocumentState {
 readonly accepted:Accepted|null;readonly draftId:string;readonly epoch:number;readonly contentGeneration:number;
 readonly baseRevision:number;readonly module:DraftModule;readonly source:string;readonly mode:'BLOCK_SUPPORTED'|'SOURCE';
 readonly selected:Id|null;readonly dirty:boolean;readonly copies:readonly PresentationCopy[];readonly clipboard:Clipboard|null;
 readonly validation:Validation|null;readonly validationBody:string|null;readonly preview:string|null;readonly historicalPreview:string|null;readonly pending:Pending|null;
 readonly rejectionDiagnostics:readonly Diagnostic[];readonly notice:string;readonly historyCursor:number|null;
}
/** Initialize an isolated browser draft. @returns Empty state. */
export function initialState():DocumentState {return {accepted:null,draftId:crypto.randomUUID(),epoch:0,contentGeneration:0,baseRevision:0,module:emptyModule(),source:'',mode:'BLOCK_SUPPORTED',selected:null,dirty:false,copies:[],clipboard:null,validation:null,validationBody:null,preview:null,historicalPreview:null,pending:null,rejectionDiagnostics:[],notice:'Create or open a model.',historyCursor:null};}
/** Invalidate diagnostics/evidence without changing content. @param state Current state. @param selected Optional selection. @returns New presentation. */
export function selectNode(state:DocumentState,selected:Id|null):DocumentState {return {...state,selected,epoch:state.epoch+1,validation:null,validationBody:null,historicalPreview:state.preview??state.historicalPreview,preview:null,rejectionDiagnostics:[]};}
/** Apply immutable candidate content and invalidate old snapshots. @param state Prior. @param module New forest. @param selected Focus destination. @param copies Transfers. @returns Dirty draft. */
export function editModule(state:DocumentState,module:DraftModule,selected:Id|null=state.selected,copies:readonly PresentationCopy[]=state.copies):DocumentState {
  return {...selectNode(state,selected),module,copies,mode:'BLOCK_SUPPORTED',contentGeneration:state.contentGeneration+1,dirty:true,clipboard:null};
}
/** Retain invalid exact text separately from accepted source. @param state Prior. @param source New exact source. @returns Dirty source draft. */
export function editSource(state:DocumentState,source:string):DocumentState {return {...selectNode(state,state.selected),source,mode:'SOURCE',dirty:true,contentGeneration:state.contentGeneration+1,clipboard:null};}
/** Open an authorized immutable snapshot, explicitly replacing local draft. @param state Prior. @param accepted Server snapshot. @returns New draft bound to accepted base. */
export function openAccepted(state:DocumentState,accepted:Accepted):DocumentState {
  if(state.accepted?.documentId===accepted.documentId&&accepted.headRevision<state.accepted.headRevision) return {...state,notice:'Ignored an older server head response.'};
  const module=accepted.artifact.module??emptyModule();
  return {...initialState(),accepted,draftId:crypto.randomUUID(),epoch:state.epoch+1,contentGeneration:state.contentGeneration+1,baseRevision:accepted.headRevision,module,source:accepted.artifact.source,mode:accepted.artifact.module?'BLOCK_SUPPORTED':'SOURCE',notice:'Model opened.',historyCursor:accepted.revision};
}
/** Build only a complete independently checked candidate. @param state Current draft. @returns Wire candidate. @throws Error on holes/types/Unicode/bounds. */
export function candidate(state:DocumentState):Candidate {
  if(state.mode==='SOURCE') {
    if(!validUnicode(state.source)||new TextEncoder().encode(state.source).length>32768) throw new Error('Source must be strict Unicode and at most32768 UTF8 bytes.');
    return {mode:'SOURCE',source:state.source};
  }
  const checked=checkModule(state.module);
  if(!checked.complete) throw new Error(checked.diagnostics[0]?.message??'Fill every unresolved hole before validating or saving.');
  return {mode:'BLOCK_SUPPORTED',module:state.module as Module,presentationCopies:state.copies};
}
/** Bind a validation response to the current exact request snapshot. @param state Current. @param body Original request bytes. @param hash SHA256 of body. @param response Advisory result. @returns State with current diagnostics only. */
export function applyValidation(state:DocumentState,body:string,hash:string,response:Validation):DocumentState {
  if(state.validationBody!==body||response.requestHash!==hash||response.draftId!==state.draftId||response.draftEpoch!==state.epoch||response.baseRevision!==state.baseRevision) return state;
  return {...state,validation:response,preview:response.proposedSource,notice:'Draft checked. Your saved version is unchanged.'};
}
/** Apply durable success monotonically, preserving newer drafts and evidence invalidation. @param state Current. @param pending Origin. @param response Receipt. @returns Updated knowledge. */
export function applyCommit(state:DocumentState,pending:Pending,response:Envelope<MutationData>):DocumentState {
  if(response.status!=='COMMITTED') return {...state,rejectionDiagnostics:'diagnostics' in response.data?response.data.diagnostics:[],pending:uncertain(response.status)?pending:null,notice:`${response.status}: draft retained; accepted state unchanged or awaiting recovery.`};
  if(!('artifact' in response.data)) return {...state,notice:'Invalid success envelope; exact pending bytes retained for recovery.'};
  const data=response.data,known=state.accepted?.headRevision??-1;
  if(data.revision<known) return {...state,pending:null,notice:'Historical receipt recovered; refresh current head.'};
  const accepted:Accepted={documentId:data.documentId,revision:data.revision,headRevision:data.revision,artifact:data.artifact,provenance:data.provenance};
  if(state.draftId===pending.draftId&&state.epoch===pending.epoch) return {...openAccepted(state,accepted),historyCursor:pending.route.endsWith('/history-copy')?state.historyCursor:data.revision,pending:null,notice:'Saved this version.'};
  return {...state,accepted,pending:null,validation:null,preview:null,notice:'Server commit recorded; newer draft preserved. Rebase explicitly before saving.'};
}
/** Identify uncertain or active outcomes requiring identical retry bytes. @param status Server status. @returns Keep pending request. */
export function uncertain(status:string):boolean {return ['UNKNOWN_COMMIT_OUTCOME','IN_PROGRESS','UNAVAILABLE'].includes(status);}
/** Verify clipboard content identity independently of selection epoch. @param state Current. @returns Clipboard still eligible. */
export function clipboardCurrent(state:DocumentState):boolean {
  const copy=state.clipboard;
  return !!copy&&copy.documentId===state.accepted?.documentId&&copy.baseRevision===state.baseRevision&&copy.draftId===state.draftId&&copy.contentGeneration===state.contentGeneration;
}
