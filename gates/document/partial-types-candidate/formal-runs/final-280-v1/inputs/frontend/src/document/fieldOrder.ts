import type {DraftModule,Field} from './types';
/** Check owner grouping without normalizing a submitted complete candidate. @param module Signature and field presentation order. @returns Whether fields follow signature order with no missing owner. */
export function fieldsGrouped(module:DraftModule):boolean {
  let previous=-1;
  for(const field of module.fields) {
    let owner=-1;
    for(let index=0;index<module.signatures.length;index++) {
      if(module.signatures[index].id===field.ownerSignatureId) owner=index;
    }
    if(owner<0||owner<previous) return false;
    previous=owner;
  }
  return true;
}
/** Explicitly group a draft field transition while retaining unresolved owners visibly. @param module Ordered signatures. @param fields Proposed draft field sequence. @returns Grouped known fields followed by unresolved draft fields, each preserving relative order. */
export function groupDraftFields(module:DraftModule,fields:readonly Field[]):readonly Field[] {
  const result:Field[]=[],owners=new Set<string>();
  for(const signature of module.signatures) {
    owners.add(signature.id);
    for(const field of fields) {
      if(field.ownerSignatureId===signature.id) result.push(field);
    }
  }
  for(const field of fields) {
    if(!owners.has(field.ownerSignatureId)) result.push(field);
  }
  return result;
}
/** Explain a visible field insertion or owner reassignment before any server acceptance. @param before Prior draft. @param after New draft. @returns Specific operation notice or null for unrelated edits. */
export function fieldTransitionNotice(before:DraftModule,after:DraftModule):string|null {
  let changed=after.fields.length>before.fields.length;
  for(const field of after.fields) {
    for(const old of before.fields) {
      if(field.id===old.id&&field.ownerSignatureId!==old.ownerSignatureId) changed=true;
    }
  }
  if(!changed) return null;
  return 'Draft field insertion/reassignment grouped by signature order; within-owner order retained. Accepted history unchanged.';
}
