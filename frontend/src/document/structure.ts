import type {DraftModule,Field,Id,Multiplicity,Schema,Signature} from './types';
import {freshId} from './model';
import {validName} from '../model';
import {groupDraftFields} from './fieldOrder';
import {deleteDeclaration} from './declarations';
export const MULTIPLICITIES:readonly Multiplicity[]=['set','one','lone','some'];
export interface FieldSpec {readonly owner:Id;readonly name:string;readonly multiplicity:Multiplicity;readonly range:Schema}
/** Pick the first unused name of the form stem1, stem2, … @param stem Name stem. @param taken Names already in use. @returns Fresh name. */
export function nextName(stem:string,taken:ReadonlySet<string>):string {
  let count=1;
  while(taken.has(`${stem}${count}`)) count++;
  return `${stem}${count}`;
}
/** Collect top-level names that a new signature must not reuse. @param module Draft. @returns Signature, predicate, fact and assertion names. */
export function topLevelNames(module:DraftModule):Set<string> {
  const names=new Set<string>();
  for(const item of [...module.signatures,...module.predicates,...module.facts,...module.assertions]) names.add(item.name);
  return names;
}
/** Collect the field names already declared on one signature. @param module Draft. @param owner Signature identity. @returns Field names. */
export function fieldNames(module:DraftModule,owner:Id):Set<string> {
  const names=new Set<string>();
  for(const field of module.fields) if(field.ownerSignatureId===owner) names.add(field.name);
  return names;
}
/** Explain why a proposed name cannot be used. @param name Trimmed proposal. @param taken Names already used in the same scope. @returns Problem text, or null when the name is usable. */
export function nameProblem(name:string,taken:ReadonlySet<string>):string|null {
  if(name.length>64) return 'Use a name of at most 64 characters.';
  if(name.startsWith('allow_')) return 'Names starting with allow_ are reserved.';
  if(!validName(name)) return `“${name}” can’t be used: start with a letter, use only letters, digits and _, and avoid Alloy keywords such as sig, set or one.`;
  if(taken.has(name)) return `“${name}” is already used.`;
  return null;
}
/** Append a named signature with no fields. @param module Draft. @param name Valid name. @returns New draft. */
export function withSignature(module:DraftModule,name:string):DraftModule {
  const signature:Signature={tag:'signature',id:freshId(),name,multiplicity:'set'};
  return {...module,signatures:[...module.signatures,signature]};
}
/** Add a field to a signature, kept with that signature's other fields. @param module Draft. @param spec Owner, name, multiplicity and range. @returns New draft. */
export function withField(module:DraftModule,spec:FieldSpec):DraftModule {
  const field:Field={tag:'field',id:freshId(),name:spec.name,ownerSignatureId:spec.owner,rangeColumns:spec.range,multiplicity:spec.multiplicity};
  return {...module,fields:groupDraftFields(module,[...module.fields,field])};
}
/** Remove a signature together with the fields declared on it; other references stay visible as problems. @param module Draft. @param signature Target. @returns New draft. */
export function withoutSignature(module:DraftModule,signature:Signature):DraftModule {
  let next=deleteDeclaration(module,signature);
  for(const field of module.fields) if(field.ownerSignatureId===signature.id) next=deleteDeclaration(next,field);
  return next;
}
/** List fields whose owner is not a current signature. @param module Draft. @returns Unowned fields. */
export function unownedFields(module:DraftModule):readonly Field[] {
  const owners=new Set<Id>(),result:Field[]=[];
  for(const signature of module.signatures) owners.add(signature.id);
  for(const field of module.fields) if(!owners.has(field.ownerSignatureId)) result.push(field);
  return result;
}

export interface SourceSignature {readonly names:readonly string[];readonly open:number;readonly close:number}
const HIDDEN=/\/\*[\s\S]*?(?:\*\/|$)|\/\/[^\n]*|--[^\n]*|"(?:[^"\\\n]|\\.)*"?/g;
const SIGNATURE=/\bsig\s+([A-Za-z]\w*(?:\s*,\s*[A-Za-z]\w*)*)\s*(?:(?:extends|in)\b[^{]*)?\{/g;
/** Blank one comment or string literal, keeping its length and line breaks. @param text Matched text. @returns Same-length blanks. */
function blank(text:string):string {return text.replace(/[^\n]/g,' ');}
/** Hide comments and string literals so structural scanning ignores them, preserving offsets. @param source Alloy text. @returns Masked text of equal length. */
export function maskSource(source:string):string {return source.replace(HIDDEN,blank);}
/** Find the brace that closes the one at an index. @param masked Masked source. @param open Index of an opening brace. @returns Matching index, or -1. */
function closing(masked:string,open:number):number {
  let depth=0;
  for(let index=open;index<masked.length;index++) {
    if(masked[index]==='{') depth++;
    else if(masked[index]==='}'&&--depth===0) return index;
  }
  return -1;
}
/** List signature declarations in Alloy text with the braces of their field bodies. @param source Alloy text. @returns Declarations in text order. */
export function sourceSignatures(source:string):readonly SourceSignature[] {
  const masked=maskSource(source),result:SourceSignature[]=[];
  for(const match of masked.matchAll(SIGNATURE)) {
    const open=(match.index??0)+match[0].length-1,close=closing(masked,open);
    if(close>open) result.push({names:match[1].split(/\s*,\s*/),open,close});
  }
  return result;
}
/** Index of the last non-blank character, or -1. @param text Masked text. @returns Position. */
function lastCode(text:string):number {
  for(let index=text.length-1;index>=0;index--) if(!/\s/.test(text[index])) return index;
  return -1;
}
/** Append a signature declaration after the last one, or at the end of the text. @param source Alloy text. @param name Valid name. @returns New text. */
export function appendSignature(source:string,name:string):string {
  const last=sourceSignatures(source).at(-1),masked=maskSource(source);
  if(last&&masked.slice(last.close+1).trimStart()[0]!=='{') return `${source.slice(0,last.close+1)}\nsig ${name} {}${source.slice(last.close+1)}`;
  return `${source}${source&&!source.endsWith('\n')?'\n':''}sig ${name} {}\n`;
}
/** Write a field declaration into a signature's field body, after any existing fields. @param source Alloy text. @param signature Target declaration from sourceSignatures. @param declaration Field text such as `owner: one Person`. @returns New text. */
export function insertField(source:string,signature:SourceSignature,declaration:string):string {
  const body=source.slice(signature.open+1,signature.close),last=lastCode(maskSource(source).slice(signature.open+1,signature.close));
  if(last<0&&!body.trim()) return `${source.slice(0,signature.open+1)}\n  ${declaration}\n${source.slice(signature.close)}`;
  if(last<0) return `${source.slice(0,signature.open+1)}\n  ${declaration}${source.slice(signature.open+1)}`;
  const at=signature.open+2+last,comma=source[at-1]===','?'':',';
  return `${source.slice(0,at)}${comma}\n  ${declaration}${source.slice(at)}`;
}
/** Spell a single-range field declaration as Alloy text. @param name Field name. @param multiplicity Multiplicity keyword. @param range Range signature name. @returns Declaration text. */
export function fieldText(name:string,multiplicity:Multiplicity,range:string):string {return `${name}: ${multiplicity} ${range}`;}
