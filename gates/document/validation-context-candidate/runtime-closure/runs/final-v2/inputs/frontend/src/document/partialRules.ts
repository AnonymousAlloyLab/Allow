import type {DraftModule,DraftNode,Id,Type,SlotAddress,SlotObligation,Check} from './types';
import {children} from './model';
export interface Equation {readonly key:string;readonly ownerId:Id;readonly role:string;readonly rule:'expect'|'equal'|'product'|'join'|'transpose';readonly ids:readonly Id[];readonly expected?:Type|'relation';readonly widths?:readonly number[];readonly relatedIds?:readonly Id[]}
export interface RuleGraph {readonly equations:readonly Equation[];readonly slots:ReadonlyMap<Id,SlotAddress>;readonly valid:boolean}
/** Obtain a stable owning edge address for an immediate child. @param parent Owning constructor. @param index Child position. @returns Slot. */
function childSlot(parent:DraftNode,index:number):SlotAddress {
  const role='arguments' in parent?'argument':'bodyId' in parent?'body':'operandId' in parent?'operand':index===0?'left':'right';
  return {ownerId:parent.id,role,...(role==='argument'?{index}:{})};
}
/** Validate finite ownership before any propagation, including malformed shared/cyclic forests. @param module Draft. @returns Whether traversal completed under existing bounds. */
function validForest(module:DraftModule):boolean {
  if(module.nodes.length>512) return false;
  const index=new Map<Id,DraftNode>(),seen=new Set<Id>();for(const node of module.nodes) index.set(node.id,node);
  if(index.size!==module.nodes.length) return false;
  const queue:{id:Id;depth:number}[]=[];for(const root of [...module.predicates,...module.facts,...module.assertions]) queue.push({id:root.bodyId,depth:0});
  while(queue.length) {
    const item=queue.pop()!,node=index.get(item.id);
    if(!node||seen.has(item.id)||item.depth>=32) return false;
    seen.add(item.id);
    for(const id of children(node)) queue.push({id,depth:item.depth+1});
  }
  return seen.size===module.nodes.length;
}
/** Canonically add one fixed equation; repeated equivalent constraints share an ID. @param rows Collector. @param equation Local rule. @returns Nothing. */
function add(rows:Map<string,Equation>,equation:Omit<Equation,'key'>):void {
  const expected=equation.expected==='relation'?'relation':equation.expected?[equation.expected.kind,...(equation.expected.kind==='relation'?equation.expected.columns:[])]:null;
  const key=JSON.stringify([equation.ownerId,equation.role,equation.rule,equation.ids,expected,equation.widths,equation.relatedIds]);
  rows.set(key,{...equation,key});
}
/** Register each child's independently required sort/schema. @param module Environment. @param node Parent. @param rows Equations. @returns Nothing. */
function operandRules(module:DraftModule,node:DraftNode,rows:Map<string,Equation>):void {
  const ids=children(node);
  for(let index=0;index<ids.length;index++) {
    const slot=childSlot(node,index);let expected:Type|'relation'='relation';
    if('binder' in node||node.tag==='not'||['and','or','implies','iff'].includes(node.tag)) expected={kind:'formula'};
    if(node.tag==='predicate_call') {
      let parameter;for(const pred of module.predicates) if(pred.id===node.predicateId) parameter=pred.parameters[index];
      if(!parameter) continue;
      expected={kind:'relation',columns:parameter.columns};
    }
    add(rows,{ownerId:node.id,role:slot.role+(slot.index===undefined?'':`:${slot.index}`),rule:'expect',ids:[ids[index]],expected,
      ...(node.tag==='transpose'?{widths:[2]}:{}),...(node.tag==='predicate_call'?{relatedIds:[node.predicateId]}:{})});
  }
}
/** Register finite relational equations independently of child completion. @param node Constructor. @param rows Equations. @returns Nothing. */
function relationRules(node:DraftNode,rows:Map<string,Equation>):void {
  if(node.tag==='transpose') add(rows,{ownerId:node.id,role:'operand',rule:'transpose',ids:[node.operandId,node.id]});
  if(!('leftId' in node)) return;
  const ids=[node.leftId,node.rightId];
  if(['equal','subset','union','intersection','difference'].includes(node.tag)) add(rows,{ownerId:node.id,role:'operands',rule:'equal',ids});
  if(['union','intersection','difference'].includes(node.tag)) add(rows,{ownerId:node.id,role:'result',rule:'equal',ids:[node.id,node.leftId]});
  if(node.tag==='product'||node.tag==='join') add(rows,{ownerId:node.id,role:'result',rule:node.tag,ids:[node.leftId,node.rightId,node.id]});
}
/** Build a fixed, canonical equation inventory before iteration. @param module Draft. @param obligations Retained explicit slot constraints. @returns Rule graph. */
export function ruleGraph(module:DraftModule,obligations:readonly SlotObligation[]):RuleGraph {
  const rows=new Map<string,Equation>(),slots=new Map<Id,SlotAddress>();
  for(const root of [...module.predicates,...module.facts,...module.assertions]) {
    slots.set(root.bodyId,{ownerId:root.id,role:'body'});
    add(rows,{ownerId:root.id,role:'body',rule:'expect',ids:[root.bodyId],expected:{kind:'formula'}});
  }
  for(const node of module.nodes) {
    let index=0;for(const id of children(node)) slots.set(id,childSlot(node,index++));
    operandRules(module,node,rows);relationRules(node,rows);
  }
  for(const node of module.nodes) if(node.tag==='hole'&&node.expected) {
    const slot=slots.get(node.id);if(slot) add(rows,{ownerId:slot.ownerId,role:`${slot.role}:${slot.index??''}:explicit`,rule:'expect',ids:[node.id],expected:node.expected});
  }
  for(const obligation of obligations) for(const [id,slot] of slots) if(slot.ownerId===obligation.slot.ownerId&&slot.role===obligation.slot.role&&slot.index===obligation.slot.index) {
    add(rows,{ownerId:slot.ownerId,role:`${slot.role}:${slot.index??''}:explicit`,rule:'expect',ids:[id],expected:obligation.expected});
  }
  return {equations:[...rows.values()].sort(compareEquations),slots,valid:validForest(module)};
}
/** Allocate the constructor's known result independently of operands. @param node Draft node. @param checked Exact checker projections. @returns Partial result. */
export function constructorSort(node:DraftNode,checked:Pick<Check,'types'>):'unknown'|'formula'|'relation' {
  if(node.tag==='hole') return 'unknown';
  const exact=checked.types.get(node.id);if(exact) return exact.kind;
  return ['signature_ref','field_ref','variable_ref','transpose','union','intersection','difference','join','product'].includes(node.tag)?'relation':'formula';
}
/** Order canonical equation IDs independently of source array order. @param a First rule. @param b Second rule. @returns Lexical comparison. */
function compareEquations(a:Equation,b:Equation):number {return a.key.localeCompare(b.key);}
