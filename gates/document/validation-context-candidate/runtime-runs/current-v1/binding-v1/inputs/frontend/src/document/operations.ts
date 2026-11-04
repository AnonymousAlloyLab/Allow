import type {DraftModule,DraftNode,Expression,Id,Type,PresentationCopy,Check,UnaryTag,BinaryTag,SlotObligation,PartialLimits} from './types';
import {freshId,subtree,nodeIndex,checkModule,FORMULA,typeLabel,UNARY} from './model';
import {captureObligation,retainObligations,copyObligations} from './obligations';
export interface Clipboard {readonly documentId:string;readonly baseRevision:number;readonly draftId:string;readonly contentGeneration:number;readonly nodeId:Id;readonly cut:boolean}
export interface EditResult {readonly module:DraftModule;readonly copies:readonly PresentationCopy[];readonly selected:Id;readonly slotObligations:readonly SlotObligation[];readonly error:string|null}
/** Allocate an explicit draft hole. @param expected Known constraint. @returns Hole. */
export function hole(expected:Type|null=null):DraftNode {return {tag:'hole',id:freshId(),expected};}
/** Create a complete operator shape with unresolved child holes. @param tag Closed palette tag. @param target Reference/predicate/signature identity. @param module Environment. @param name Binder name. @returns New owned nodes. */
export function construct(tag:Expression['tag'],target:Id,module:DraftModule,name='variable'):readonly DraftNode[] {
  const id=freshId();
  if(tag==='signature_ref'||tag==='field_ref'||tag==='variable_ref') return [{tag,id,targetId:target}];
  if(tag==='predicate_call') {
    const slots:DraftNode[]=[];
    for(const pred of module.predicates) if(pred.id===target) for(const param of pred.parameters) slots.push(hole({kind:'relation',columns:param.columns}));
    const args:Id[]=[];for(const slot of slots) args.push(slot.id);
    return [{tag,id,predicateId:target,arguments:args},...slots];
  }
  if(tag==='all_quant'||tag==='some_quant') {const body=hole(FORMULA);return [{tag,id,binder:{id:freshId(),name,signatureId:target},bodyId:body.id},body];}
  if((UNARY as readonly string[]).includes(tag)) {const child=hole(tag==='not'?FORMULA:null);return [{tag:tag as UnaryTag,id,operandId:child.id},child];}
  const boolean=['and','or','implies','iff'].includes(tag),left=hole(boolean?FORMULA:null),right=hole(boolean?FORMULA:null);
  return [{tag:tag as BinaryTag,id,leftId:left.id,rightId:right.id},left,right];
}
/** Rewrite owned child edges only. @param node Existing node. @param oldId Replaced child. @param nextId New root. @returns Rewritten node. */
function swapChild(node:DraftNode,oldId:Id,nextId:Id):DraftNode {
  if('operandId' in node) return {...node,operandId:node.operandId===oldId?nextId:node.operandId};
  if('leftId' in node) return {...node,leftId:node.leftId===oldId?nextId:node.leftId,rightId:node.rightId===oldId?nextId:node.rightId};
  if('bodyId' in node) return {...node,bodyId:node.bodyId===oldId?nextId:node.bodyId};
  if('arguments' in node) {const args:Id[]=[];for(const id of node.arguments) args.push(id===oldId?nextId:id);return {...node,arguments:args};}
  return node;
}
/** Replace a subtree preserving outside identity and immutable order. @param module Current draft. @param target Destination. @param additions New owned nodes root-first. @returns Candidate. */
export function replaceSubtree(module:DraftModule,target:Id,additions:readonly DraftNode[]):DraftModule {
  const removed=subtree(module,target),next=additions[0].id,nodes:DraftNode[]=[];
  for(const node of module.nodes) if(!removed.has(node.id)) nodes.push(swapChild(node,target,next));
  nodes.push(...additions);
  const predicates=[];for(const pred of module.predicates) predicates.push({...pred,bodyId:pred.bodyId===target?next:pred.bodyId});
  const facts=[];for(const fact of module.facts) facts.push({...fact,bodyId:fact.bodyId===target?next:fact.bodyId});
  const assertions=[];for(const item of module.assertions) assertions.push({...item,bodyId:item.bodyId===target?next:item.bodyId});
  return {...module,nodes,predicates,facts,assertions};
}
/** Prepare replacement and retained explicit destination constraints as one immutable candidate. @param module Original forest. @param target Destination slot. @param nodes New owned subtree. @param obligations Original sidecar. @returns Candidate forest and matching sidecar. */
export function replacement(module:DraftModule,target:Id,nodes:readonly DraftNode[],obligations:readonly SlotObligation[]):{module:DraftModule;slotObligations:readonly SlotObligation[]} {
  const captured=captureObligation(module,target,obligations),candidate=replaceSubtree(module,target,nodes);
  return {module:candidate,slotObligations:retainObligations(candidate,captured)};
}
/** Reject new exact constraint violations only after both full analyses finish. @param before Prior forest. @param after Candidate forest. @param beforeObligations Prior sidecar. @param afterObligations Candidate sidecar. @param limits Optional deterministic analysis budgets. @returns Specific new error or compatible transition. */
export function newContradiction(before:DraftModule,after:DraftModule,beforeObligations:readonly SlotObligation[]=[],afterObligations:readonly SlotObligation[]=beforeObligations,limits?:PartialLimits):string|null {
  const prior=checkModule(before,beforeObligations,limits),next=checkModule(after,afterObligations,limits),failure=prior.resourceFailure??next.resourceFailure;
  if(failure) return `${failure.code}: Draft constraint analysis did not complete; edit rejected.`;
  for(const [key,item] of next.violations) if(!prior.violations.has(key)) return item.message;
  return null;
}
/** Map copied identity with external declaration preservation. @param id Original. @param remap Owned mapping. @returns Fresh or external identity. */
function mapped(id:Id,remap:ReadonlyMap<Id,Id>):Id {return remap.get(id)??id;}
/** Clone one owned node including locally bound references. @param node Node. @param remap Owned/binder map. @returns Remapped clone. */
function cloneNode(node:DraftNode,remap:ReadonlyMap<Id,Id>):DraftNode {
  const id=mapped(node.id,remap);
  if('targetId' in node) return {...node,id,targetId:mapped(node.targetId,remap)};
  if('binder' in node) return {...node,id,binder:{...node.binder,id:mapped(node.binder.id,remap),name:`${node.binder.name.slice(0,48)}_${id.slice(-8)}`},bodyId:mapped(node.bodyId,remap)};
  if('operandId' in node) return {...node,id,operandId:mapped(node.operandId,remap)};
  if('leftId' in node) return {...node,id,leftId:mapped(node.leftId,remap),rightId:mapped(node.rightId,remap)};
  if('arguments' in node) {const args:Id[]=[];for(const item of node.arguments) args.push(mapped(item,remap));return {...node,id,arguments:args};}
  return {...node,id};
}
/** Clone a subtree freshening every owned node and binder. @param module Draft. @param root Source root. @returns Nodes root-first and mapping. */
export function cloneSubtree(module:DraftModule,root:Id):{nodes:readonly DraftNode[];remap:ReadonlyMap<Id,Id>;expressionMap:ReadonlyMap<Id,Id>} {
  const owned=subtree(module,root),index=nodeIndex(module),remap=new Map<Id,Id>(),expressionMap=new Map<Id,Id>(),nodes:DraftNode[]=[];
  for(const id of owned) {remap.set(id,freshId());expressionMap.set(id,remap.get(id)!);const node=index.get(id);if(node&&'binder' in node) remap.set(node.binder.id,freshId());}
  for(const id of owned) {const node=index.get(id);if(node) nodes.push(cloneNode(node,remap));}
  return {nodes,remap,expressionMap};
}
/** Track accepted-base comment provenance for a copy or copy-of-copy. @param prior Existing transfers. @param remap Copy mapping. @returns Extended comment-only map. */
export function copyProvenance(prior:readonly PresentationCopy[],remap:ReadonlyMap<Id,Id>):readonly PresentationCopy[] {
  const result:PresentationCopy[]=[...prior];
  for(const [oldId,newId] of remap) {
    let source=oldId.startsWith('server:')?oldId:null;
    for(const copy of prior) if(copy.targetNodeId===oldId) source=copy.sourceNodeId;
    if(source) result.push({sourceNodeId:source,targetNodeId:newId});
  }
  return result;
}
/** Discard transfer entries whose destination no longer exists. @param copies Transfers. @param module Candidate. @returns Valid destination entries. */
export function retainCopies(copies:readonly PresentationCopy[],module:DraftModule):readonly PresentationCopy[] {
  const ids=new Set<Id>();for(const node of module.nodes) ids.add(node.id);
  const result:PresentationCopy[]=[];for(const copy of copies) if(ids.has(copy.targetNodeId)) result.push(copy);
  return result;
}
/** Apply a clipboard operation atomically to the forest and retained constraints. @param module Current forest. @param clipboard Source snapshot. @param target Destination. @param copies Comment provenance. @param obligations Original sidecar. @returns Complete candidate or unchanged rejection. */
export function paste(module:DraftModule,clipboard:Clipboard,target:Id,copies:readonly PresentationCopy[],obligations:readonly SlotObligation[]=[]):EditResult {
  const unchanged={module,copies,selected:target,slotObligations:obligations};
  if(subtree(module,clipboard.nodeId).has(target)) return {...unchanged,error:'Cannot paste into the source or its descendant.'};
  const index=nodeIndex(module);
  if(!index.has(target)||!index.has(clipboard.nodeId)) return {...unchanged,error:'Clipboard source/destination is unavailable.'};
  let working=module,nodes:readonly DraftNode[],transfers=copies,retained=captureObligation(module,target,obligations);
  if(clipboard.cut) {
    const selected:DraftNode[]=[];
    for(const id of subtree(module,clipboard.nodeId)) {const node=index.get(id);if(node) selected.push(node);}
    nodes=selected;working=replaceSubtree(module,clipboard.nodeId,[hole()]);
    retained=captureObligation(module,clipboard.nodeId,retained);
  } else {
    const clone=cloneSubtree(module,clipboard.nodeId);nodes=clone.nodes;transfers=copyProvenance(copies,clone.expressionMap);
    retained=copyObligations(module,clipboard.nodeId,retained,clone.remap);
  }
  const candidate=replaceSubtree(working,target,nodes),slotObligations=retainObligations(candidate,retained);
  const error=newContradiction(module,candidate,obligations,slotObligations);
  return error?{...unchanged,error}:{module:candidate,copies:retainCopies(transfers,candidate),selected:nodes[0].id,slotObligations,error:null};
}
/** Describe a destination using the same structured analysis used for enforcement. @param module Declaration names. @param checked Shared analysis. @returns Identity-indexed accessible conjunction descriptions. */
export function slotConstraints(module:DraftModule,checked:Check):ReadonlyMap<Id,string> {
  const result=new Map<Id,string>();
  for(const [id,constraint] of checked.destinations) {
    const descriptions=[...constraint.descriptions];
    if(constraint.exact) descriptions.unshift(typeLabel(module,{kind:'relation',columns:constraint.exact}));
    result.set(id,descriptions.length?descriptions.join('; '):constraint.sort);
  }
  return result;
}
/** Describe expected destination constraints before insertion. @param module Draft forest. @param id Slot identity. @param obligations Retained explicit expectations. @returns Accessible constraint text. */
export function slotConstraint(module:DraftModule,id:Id,obligations:readonly SlotObligation[]=[]):string {return slotConstraints(module,checkModule(module,obligations)).get(id)??'formula';}
