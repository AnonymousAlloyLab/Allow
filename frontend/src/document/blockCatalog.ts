import type {Check,DraftModule,Expression,Id} from './types';
import type {Fit} from './gesture';
export type BlockGroup='formula'|'relation'|'quantifier'|'reference';
interface CatalogEntry {readonly symbol:string;readonly label:string;readonly code:string;readonly hint:string}
const CATALOG:Readonly<Record<Expression['tag'],CatalogEntry>>={
  signature_ref:{symbol:'S',label:'Signature',code:'Sig',hint:'All atoms of a declared signature.'},
  field_ref:{symbol:'↦',label:'Field',code:'field',hint:'A declared field relation.'},
  variable_ref:{symbol:'x',label:'Variable',code:'x',hint:'A quantified variable or predicate parameter in scope here.'},
  predicate_call:{symbol:'ƒ',label:'Call predicate',code:'p[…]',hint:'Use another predicate; it always reads the current definition.'},
  not:{symbol:'¬',label:'Not',code:'not',hint:'True when the inner formula is false.'},
  some_test:{symbol:'∃',label:'Some tuples',code:'some',hint:'The expression has at least one tuple.'},
  no_test:{symbol:'∄',label:'No tuples',code:'no',hint:'The expression is empty.'},
  one_test:{symbol:'1',label:'Exactly one tuple',code:'one',hint:'The expression has exactly one tuple.'},
  lone_test:{symbol:'≤1',label:'At most one tuple',code:'lone',hint:'The expression has zero or one tuple.'},
  transpose:{symbol:'∼',label:'Transpose',code:'~',hint:'Swap the two columns of a binary relation.'},
  and:{symbol:'∧',label:'And',code:'and',hint:'Both formulas hold.'},
  or:{symbol:'∨',label:'Or',code:'or',hint:'At least one formula holds.'},
  implies:{symbol:'⇒',label:'Implies',code:'implies',hint:'Whenever the left formula holds, the right one holds.'},
  iff:{symbol:'⇔',label:'If and only if',code:'iff',hint:'Both formulas are true together or false together.'},
  equal:{symbol:'=',label:'Equals',code:'=',hint:'Both expressions contain exactly the same tuples.'},
  subset:{symbol:'⊆',label:'Subset',code:'in',hint:'Every tuple on the left is also on the right.'},
  union:{symbol:'∪',label:'Union',code:'+',hint:'Tuples in either expression.'},
  intersection:{symbol:'∩',label:'Intersection',code:'&',hint:'Tuples in both expressions.'},
  difference:{symbol:'−',label:'Difference',code:'-',hint:'Tuples on the left that are not on the right.'},
  join:{symbol:'·',label:'Join',code:'.',hint:'Relational join: follow the left relation into the right one.'},
  product:{symbol:'×',label:'Product',code:'->',hint:'Every combination of a left tuple with a right tuple.'},
  all_quant:{symbol:'∀',label:'For every variable',code:'all x: S |',hint:'The body holds for every atom of the signature.'},
  some_quant:{symbol:'∃',label:'For some variable',code:'some x: S |',hint:'The body holds for at least one atom of the signature.'},
};
/** Supply a compact visual symbol while preserving a spoken text label. @param tag Closed constructor. @returns Operator glyph. */
export function operatorSymbol(tag:Expression['tag']):string {return CATALOG[tag].symbol;}
/** Give each closed operator a familiar visible palette label. @param tag Exact operator. @returns User-facing block name. */
export function paletteLabel(tag:Expression['tag']):string {return CATALOG[tag].label;}
/** Show the Alloy spelling a block prints as, so blocks map visibly onto explicit source. @param tag Exact operator. @returns Alloy token or template. */
export function alloyToken(tag:Expression['tag']):string {return CATALOG[tag].code;}
/** Explain a block in one plain sentence. @param tag Exact operator. @returns Short description. */
export function blockHint(tag:Expression['tag']):string {return CATALOG[tag].hint;}
/** Name each semantic palette group for headings and the canvas legend. @param group Semantic kind. @returns Visible title. */
export function groupTitle(group:BlockGroup|'hole'|'saved'):string {
  const titles={formula:'Logic',relation:'Relations',quantifier:'Quantifiers',reference:'References',hole:'Empty slot',saved:'Saved blocks'};
  return titles[group];
}
/** Describe a destination check as text plus symbol so meaning never depends on color alone. @param kind Shared guard outcome. @returns Short visible badge. */
export function fitBadge(kind:Fit['kind']):string {
  const badges={compatible:'✓ Fits',unresolved:'◌ Possible',incompatible:'✕ Won’t fit',unavailable:'– Unchecked'};
  return badges[kind];
}
/** Resolve a declaration or visible binder without inventing a name for an invalid reference. @param module Draft declarations. @param node Reference node. @param checked Current scopes. @returns Human-readable block title. */
export function nodeLabel(module:DraftModule,node:Expression,checked:Check):string {
  if(node.tag==='signature_ref') return `Signature · ${module.signatures.find(matchesId.bind(null,node.targetId))?.name??'unresolved reference'}`;
  if(node.tag==='field_ref') return `Field · ${module.fields.find(matchesId.bind(null,node.targetId))?.name??'unresolved reference'}`;
  if(node.tag==='variable_ref') return `Variable · ${checked.scopes.get(node.id)?.find(matchesId.bind(null,node.targetId))?.name??'out-of-scope reference'}`;
  if(node.tag==='predicate_call') return `Call predicate · ${module.predicates.find(matchesId.bind(null,node.predicateId))?.name??'unresolved reference'}`;
  if(node.tag==='all_quant'||node.tag==='some_quant') return `${paletteLabel(node.tag)} · ${node.binder.name}: ${module.signatures.find(matchesId.bind(null,node.binder.signatureId))?.name??'unresolved signature'}`;
  return paletteLabel(node.tag);
}
/** Compare a declaration identity without exposing unresolved raw identifiers. @param id Requested identity. @param item Candidate declaration. @returns Exact identity match. */
export function matchesId(id:Id,item:{readonly id:Id}):boolean {return item.id===id;}
/** Show the concrete Alloy spelling for a palette choice, including its referenced name. @param tag Constructor. @param label Inventory label of the form "Kind · name". @param variable Name used for new quantifier binders. @returns Alloy token or template. */
export function choiceCode(tag:Expression['tag'],label:string,variable:string):string {
  const name=label.split(' · ').slice(1).join(' · ');
  if(!name) return alloyToken(tag);
  if(tag==='predicate_call') return `${name}[…]`;
  if(tag==='all_quant'||tag==='some_quant') return `${tag==='all_quant'?'all':'some'} ${variable||'x'}: ${name} |`;
  return name;
}
