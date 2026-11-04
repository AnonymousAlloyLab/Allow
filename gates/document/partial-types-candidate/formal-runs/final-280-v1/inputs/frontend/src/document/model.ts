import type {DraftModule,DraftNode,Expression,Id,Type,Schema,Parameter,Check,Diagnostic} from './types';
export const UNARY = ['not','some_test','no_test','one_test','lone_test','transpose'] as const;
export const BINARY = ['and','or','implies','iff','equal','subset','union','intersection','difference','join','product'] as const;
export const QUANT = ['all_quant','some_quant'] as const;
export const FORMULA:Type = {kind:'formula'};
/** Allocate an untrusted placeholder. @returns Fresh draft identity. */
export function freshId():Id { return `draft:${crypto.randomUUID()}`; }
/** Create an empty complete module. @returns Immutable module value. */
export function emptyModule():DraftModule { return {version:1,signatures:[],fields:[],predicates:[],facts:[],assertions:[],commands:[],nodes:[]}; }
/** Obtain ownership children only. @param node Expression or draft hole. @returns Ordered owned IDs. */
export function children(node:DraftNode):readonly Id[] {
  if ('operandId' in node) return [node.operandId];
  if ('leftId' in node) return [node.leftId,node.rightId];
  if ('bodyId' in node) return [node.bodyId];
  return 'arguments' in node ? node.arguments : [];
}
/** Compare exact nominal types. @param a First type. @param b Second type. @returns Exact equality. */
export function sameType(a:Type|null|undefined,b:Type|null|undefined):boolean {
  return !!a && !!b && a.kind===b.kind && (a.kind==='formula' || (b.kind==='relation' && sameSchema(a.columns,b.columns)));
}
/** Compare ordered schemas. @param a First columns. @param b Second columns. @returns Ordered equality. */
export function sameSchema(a:Schema,b:Schema):boolean {
  if (a.length!==b.length) return false;
  for(let i=0;i<a.length;i++) if(a[i]!==b[i]) return false;
  return true;
}
/** Build an index without silently overwriting identities. @param module Draft module. @returns Node index. */
export function nodeIndex(module:DraftModule):ReadonlyMap<Id,DraftNode> {
  const result=new Map<Id,DraftNode>();
  for(const node of module.nodes) result.set(node.id,node);
  return result;
}
/** Collect a subtree, with a finite guard. @param module Current module. @param id Root identity. @returns Owned IDs. */
export function subtree(module:DraftModule,id:Id):ReadonlySet<Id> {
  const index=nodeIndex(module), result=new Set<Id>(), queue=[id];
  while(queue.length) {
    const next=queue.pop()!;
    if(result.has(next)) continue;
    result.add(next);
    const node=index.get(next);
    if(node) queue.push(...children(node));
  }
  return result;
}
/** Display a nominal type. @param module Declaration environment. @param type Known type. @returns Human-readable schema. */
export function typeLabel(module:DraftModule,type:Type|null|undefined):string {
  if(!type) return 'unresolved relation constraint';
  if(type.kind==='formula') return 'formula';
  const names:string[]=[];
  for(const id of type.columns) {
    let name=id;
    for(const sig of module.signatures) if(sig.id===id) name=sig.name;
    names.push(name);
  }
  return names.join(' → ');
}
/** Validate a schema independently of parser types. @param module Declarations. @param schema Columns. @returns Valid exact schema. */
export function schemaValid(module:DraftModule,schema:Schema):boolean {
  if(schema.length<1 || schema.length>8) return false;
  const ids=new Set<Id>();
  for(const sig of module.signatures) ids.add(sig.id);
  for(const id of schema) if(!ids.has(id)) return false;
  return true;
}
/** Find a lexical variable. @param environment Visible binders. @param id Stable identity. @returns Matching parameter. */
export function findVariable(environment:readonly Parameter[],id:Id):Parameter|undefined {
  for(const item of environment) if(item.id===id) return item;
  return undefined;
}
/** Record a bounded diagnostic. @param diagnostics Mutable local collector. @param nodeId Failing identity. @param message Specific reason. @returns Nothing. */
export function issue(diagnostics:Diagnostic[],nodeId:Id,message:string):void {
  if(diagnostics.length<64) diagnostics.push({nodeId,message});
}
/** Check the full draft independently. @param module Draft forest. @returns Types, lexical environments and diagnostics. */
export function checkModule(module:DraftModule):Check { return new Checker(module).check(); }
import {Checker} from './checker';
