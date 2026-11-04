import type {DraftModule,DraftNode,Id,SlotAddress,SlotObligation,Type} from './types';
import {sameType,subtree} from './model';
/** Enumerate stable owning edges without deriving constraints from expression types. @param module Owned forest. @returns Child identities paired with their owning slots. */
export function moduleSlots(module:DraftModule):ReadonlyMap<Id,SlotAddress> {
  const slots=new Map<Id,SlotAddress>();
  for(const root of [...module.predicates,...module.facts,...module.assertions]) slots.set(root.bodyId,{ownerId:root.id,role:'body'});
  for(const node of module.nodes) {
    if('operandId' in node) slots.set(node.operandId,{ownerId:node.id,role:'operand'});
    if('leftId' in node) {slots.set(node.leftId,{ownerId:node.id,role:'left'});slots.set(node.rightId,{ownerId:node.id,role:'right'});}
    if('bodyId' in node) slots.set(node.bodyId,{ownerId:node.id,role:'body'});
    if('arguments' in node) for(let index=0;index<node.arguments.length;index++) slots.set(node.arguments[index],{ownerId:node.id,role:'argument',index});
  }
  return slots;
}
/** Identify one occurrence-owned destination independently of its current child identity. @param slot Owning edge. @returns Exact canonical address. */
function slotKey(slot:SlotAddress):string {return JSON.stringify([slot.ownerId,slot.role,slot.index??null]);}
/** Add an independent constraint once without changing a previous sidecar. @param obligations Existing obligations. @param obligation New conjunction member. @returns Immutable deduplicated sidecar. */
function appendObligation(obligations:readonly SlotObligation[],obligation:SlotObligation):readonly SlotObligation[] {
  for(const item of obligations) if(slotKey(item.slot)===slotKey(obligation.slot)&&sameType(item.expected,obligation.expected)) return obligations;
  return [...obligations,obligation];
}
/** Preserve an explicit hole constraint before the hole disappears. @param module Original forest. @param target Destination identity. @param obligations Original sidecar. @returns Sidecar including the independent explicit expectation. */
export function captureObligation(module:DraftModule,target:Id,obligations:readonly SlotObligation[]):readonly SlotObligation[] {
  const slot=moduleSlots(module).get(target);
  if(!slot) return obligations;
  for(const node of module.nodes) if(node.id===target&&node.tag==='hole'&&node.expected) return appendObligation(obligations,{slot,expected:node.expected});
  return obligations;
}
/** Keep obligations only while their owning slot still exists. @param module Result forest. @param obligations Candidate sidecar. @returns Retained immutable conjunctions. */
export function retainObligations(module:DraftModule,obligations:readonly SlotObligation[]):readonly SlotObligation[] {
  const slots=new Set<string>(),retained:SlotObligation[]=[];
  for(const slot of moduleSlots(module).values()) slots.add(slotKey(slot));
  for(const obligation of obligations) if(slots.has(slotKey(obligation.slot))) retained.push(obligation);
  return retained.length===obligations.length?obligations:retained;
}
/** Remap nominal declaration identities only where an authorized identity map supplies replacements. @param type Explicit expectation. @param remap Owned and declaration mapping. @returns Remapped expectation. */
function remapType(type:Type,remap:ReadonlyMap<Id,Id>):Type {
  if(type.kind==='formula') return type;
  const columns:Id[]=[];for(const id of type.columns) columns.push(remap.get(id)??id);
  return {kind:'relation',columns};
}
/** Remap occurrence ownership and nominal identities without mutating prior transaction state. @param obligations Source conjunctions. @param remap Authorized identity mapping. @returns Remapped immutable sidecar. */
export function remapObligations(obligations:readonly SlotObligation[],remap:ReadonlyMap<Id,Id>):readonly SlotObligation[] {
  const result:SlotObligation[]=[];
  for(const item of obligations) result.push({slot:{...item.slot,ownerId:remap.get(item.slot.ownerId)??item.slot.ownerId},expected:remapType(item.expected,remap)});
  return result;
}
/** Copy obligations owned inside a copied subtree while leaving its outer source slot in place. @param module Original forest. @param root Copied root. @param obligations Source sidecar. @param remap Clone identity map. @returns Extended copy sidecar. */
export function copyObligations(module:DraftModule,root:Id,obligations:readonly SlotObligation[],remap:ReadonlyMap<Id,Id>):readonly SlotObligation[] {
  const owned=subtree(module,root),internal:SlotObligation[]=[];
  for(const item of obligations) if(owned.has(item.slot.ownerId)) internal.push(item);
  return [...obligations,...remapObligations(internal,remap)];
}
