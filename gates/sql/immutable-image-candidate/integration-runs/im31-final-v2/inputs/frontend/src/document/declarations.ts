import type {DraftModule,Signature,Field,Predicate,Parameter,FormulaDeclaration,Command,Id,DraftNode} from './types';
import {freshId,FORMULA,subtree} from './model';
import {hole} from './operations';
import {groupDraftFields} from './fieldOrder';
export type Declaration=Signature|Field|Predicate|FormulaDeclaration|Command;
/** Replace one immutable array member. @param items Existing items. @param replacement New item. @returns New array. */
export function replaceItem<T extends {readonly id:Id}>(items:readonly T[],replacement:T):readonly T[] {
  const result:T[]=[];for(const item of items) result.push(item.id===replacement.id?replacement:item);
  return result;
}
/** Replace a declaration and keep all dependent drafts visible. @param module Prior. @param item New declaration. @returns New module. */
export function updateDeclaration(module:DraftModule,item:Declaration):DraftModule {
  switch(item.tag) {
    case 'signature':return {...module,signatures:replaceItem(module.signatures,item)};
    case 'field':return {...module,fields:groupDraftFields(module,replaceItem(module.fields,item))};
    case 'predicate':return {...module,predicates:replaceItem(module.predicates,item)};
    case 'fact':return {...module,facts:replaceItem(module.facts,item)};
    case 'assertion':return {...module,assertions:replaceItem(module.assertions,item)};
    default:return {...module,commands:replaceItem(module.commands,item)};
  }
}
/** Remove a declaration and only its owned expressions. @param module Prior. @param item Explicit target. @returns Draft retaining incoming dependency errors. */
export function deleteDeclaration(module:DraftModule,item:Declaration):DraftModule {
  const removed='bodyId' in item?subtree(module,item.bodyId):new Set<Id>(),nodes:DraftNode[]=[];
  const signatures:Signature[]=[],fields:Field[]=[],predicates:Predicate[]=[],facts:FormulaDeclaration[]=[],assertions:FormulaDeclaration[]=[],commands:Command[]=[];
  for(const node of module.nodes) if(!removed.has(node.id)) nodes.push(node);
  for(const decl of module.signatures) if(decl.id!==item.id) signatures.push(decl);
  for(const decl of module.fields) if(decl.id!==item.id) fields.push(decl);
  for(const decl of module.predicates) if(decl.id!==item.id) predicates.push(decl);
  for(const decl of module.facts) if(decl.id!==item.id) facts.push(decl);
  for(const decl of module.assertions) if(decl.id!==item.id) assertions.push(decl);
  for(const decl of module.commands) if(decl.id!==item.id) commands.push(decl);
  return {...module,signatures,fields,predicates,facts,assertions,commands,nodes};
}
/** Add a visible editable declaration with explicit unresolved fields. @param module Prior. @param tag Declaration kind. @returns New candidate. */
export function addDeclaration(module:DraftModule,tag:Declaration['tag']):DraftModule {
  const id=freshId(),name=`${tag}_${id.slice(-8).replaceAll('-','')}`,sig=module.signatures[0]?.id??'';
  if(tag==='signature') return {...module,signatures:[...module.signatures,{tag,id,name,multiplicity:'set'}]};
  if(tag==='field') return {...module,fields:groupDraftFields(module,[...module.fields,{tag,id,name,ownerSignatureId:sig,rangeColumns:[sig],multiplicity:'set'}])};
  if(tag==='run'||tag==='check') return {...module,commands:[...module.commands,{tag,id,targetId:'',uniformScope:3,bitwidth:4,maxseq:3}]};
  const body=hole(FORMULA),nodes=[...module.nodes,body];
  if(tag==='predicate') return {...module,nodes,predicates:[...module.predicates,{tag,id,name,parameters:[],bodyId:body.id}]};
  if(tag==='fact') return {...module,nodes,facts:[...module.facts,{tag,id,name,bodyId:body.id}]};
  return {...module,nodes,assertions:[...module.assertions,{tag,id,name,bodyId:body.id}]};
}
/** Add a set-valued parameter preserving stable references. @param predicate Parent. @param signature Default nominal sort. @returns New predicate. */
export function addParameter(predicate:Predicate,signature:Id):Predicate {
  const id=freshId(),parameter:Parameter={tag:'parameter',id,name:`param_${id.slice(-8)}`,columns:[signature]};
  return {...predicate,parameters:[...predicate.parameters,parameter]};
}
