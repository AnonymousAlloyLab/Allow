import type {DraftModule,DraftNode,Id,SlotObligation} from './types';
import type {DocumentState} from './state';
import {checkModule,subtree,nodeIndex} from './model';
import {cloneSubtree,replacement,newContradiction,retainCopies,type EditResult} from './operations';
import {remapObligations} from './obligations';
export interface SavedBlock {readonly id:string;readonly name:string;readonly documentId:string;readonly environment:string;readonly root:Id;readonly nodes:readonly DraftNode[];readonly obligations:readonly SlotObligation[];readonly external:readonly {id:Id;columns:readonly Id[]}[]}
/** Capture conservative identity-based declaration headers, intentionally excluding predicate bodies. @param module Current declarations. @returns Environment identity. */
export function blockEnvironment(module:DraftModule):string {
  const predicates=[];for(const item of module.predicates) predicates.push({id:item.id,name:item.name,parameters:item.parameters});
  return JSON.stringify([module.signatures,module.fields,predicates]);
}
/** Measure the entire shelf rather than trusting caller counters. @param entries Proposed shelf. @returns Rejection or null. */
export function libraryLimit(entries:readonly SavedBlock[]):string|null {
  let nodes=0;for(const item of entries) {nodes+=item.nodes.length;if(item.nodes.length>128) return 'A reusable block may contain at most 128 nodes.';}
  if(entries.length>24||nodes>1536) return 'Library limit: 24 blocks and 1536 total nodes.';
  return new TextEncoder().encode(JSON.stringify(entries)).length>524288?'Library exceeds 512 KiB.':null;
}
/** Snapshot owned content and external variable identities without retaining mutable live node lookups. @param state Current draft. @param name Display name. @returns Immutable entry. */
export function captureBlock(state:DocumentState,name:string):SavedBlock {
  if(state.mode!=='BLOCK_SUPPORTED'||!state.accepted||!state.selected) throw new Error('Select a block in a block-supported draft.');
  if(!name.trim()||name.length>64) throw new Error('Use a block name of 1–64 characters.');
  const checked=checkModule(state.module,state.slotObligations),owned=subtree(state.module,state.selected),index=nodeIndex(state.module);
  if(checked.resourceFailure||index.get(state.selected)?.tag==='hole'||!index.has(state.selected)) throw new Error('Cannot capture this unresolved root or invalid graph.');
  const nodes:DraftNode[]=[],internal=new Set<Id>(),external:{id:Id;columns:readonly Id[]}[]=[],obligations:SlotObligation[]=[];
  for(const id of owned) {const node=index.get(id);if(node) {nodes.push(node);if('binder' in node) internal.add(node.binder.id);}}
  for(const node of nodes) if(node.tag==='variable_ref'&&!internal.has(node.targetId)) {
    const variable=checked.scopes.get(node.id)?.find(matchesIdentity.bind(null,node.targetId));
    if(!variable) throw new Error('Captured block has an out-of-scope variable.');
    external.push({id:variable.id,columns:variable.columns});
  }
  for(const item of state.slotObligations) if(owned.has(item.slot.ownerId)) obligations.push(item);
  return JSON.parse(JSON.stringify({id:crypto.randomUUID(),name:name.trim(),documentId:state.accepted.documentId,environment:blockEnvironment(state.module),root:state.selected,nodes,obligations,external}));
}
/** Match an external variable by identity only. @param id Requested identity. @param item Candidate. @returns Exact match. */
function matchesIdentity(id:Id,item:{readonly id:Id}):boolean {return item.id===id;}
/** Prepare a fresh copied snapshot using the same destination constraint guard as ordinary edits. @param state Current draft. @param entry Immutable shelf item. @param target Current destination. @returns Atomic candidate or unchanged rejection. */
export function prepareSavedBlock(state:DocumentState,entry:SavedBlock,target:Id):EditResult {
  const unchanged={module:state.module,copies:state.copies,selected:target,slotObligations:state.slotObligations};
  if(state.mode!=='BLOCK_SUPPORTED'||entry.documentId!==state.accepted?.documentId) return {...unchanged,error:'Reusable block belongs to another document or source mode.'};
  if(entry.environment!==blockEnvironment(state.module)) return {...unchanged,error:'Declaration environment changed; capture this block again.'};
  const checked=checkModule(state.module,state.slotObligations),scope=checked.scopes.get(target)??[];
  if(checked.resourceFailure||!nodeIndex(state.module).has(target)) return {...unchanged,error:'Destination analysis unavailable.'};
  for(const variable of entry.external) if(!scope.some(matchesExternal.bind(null,variable))) return {...unchanged,error:'Saved variable is unavailable in this destination scope.'};
  const source={...state.module,nodes:entry.nodes},clone=cloneSubtree(source,entry.root);
  const prepared=replacement(state.module,target,clone.nodes,state.slotObligations);
  const obligations=[...prepared.slotObligations,...remapObligations(entry.obligations,clone.remap)];
  const error=newContradiction(state.module,prepared.module,state.slotObligations,obligations);
  return error?{...unchanged,error}:{...prepared,slotObligations:obligations,copies:retainCopies(state.copies,prepared.module),selected:clone.nodes[0].id,error:null};
}
/** Check external scope schema without name matching. @param expected Saved variable. @param actual Visible variable. @returns Identity/schema match. */
function matchesExternal(expected:{id:Id;columns:readonly Id[]},actual:{id:Id;columns:readonly Id[]}):boolean {return expected.id===actual.id&&JSON.stringify(expected.columns)===JSON.stringify(actual.columns);}
/** Assign stable semantic styling while retaining visible operator labels. @param tag Node/operator tag. @returns Semantic color group. */
export function blockKind(tag:string):string {
  if(tag==='hole') return 'hole';
  if(tag.endsWith('_ref')||tag==='predicate_call') return 'reference';
  if(tag.endsWith('_quant')) return 'quantifier';
  return ['transpose','union','intersection','difference','join','product'].includes(tag)?'relation':'formula';
}
