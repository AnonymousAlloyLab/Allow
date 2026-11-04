import type {DraftModule,Id,PartialFact,DestinationConstraint,Schema} from './types';
import type {RuleGraph,Equation} from './partialRules';
import {typeLabel} from './model';
/** Return exact columns only when one shape has no unresolved position. @param fact Partial result. @returns Exact ordered schema or null. */
function exactColumns(fact:PartialFact|undefined):Schema|null {
  if(!fact||fact.sort!=='relation'||fact.shapes.length!==1) return null;
  const columns:Id[]=[];for(const value of fact.shapes[0].columns) {if(value===null) return null;columns.push(value);}return columns;
}
/** Derive a label from a structured equation; text never enforces compatibility. @param module Environment. @param equation Rule. @param id Destination. @param facts Partial results. @returns Specific label. */
function description(module:DraftModule,equation:Equation,id:Id,facts:ReadonlyMap<Id,PartialFact>):string {
  if(equation.rule==='expect') {
    if(equation.expected==='relation') return equation.widths?.length===1?`relation width ${equation.widths[0]}`:'nonempty relation schema';
    return typeLabel(module,equation.expected);
  }
  if(equation.rule==='product') return 'relation: concatenated result width≤8';
  if(equation.rule==='join') return 'relation: left-last = right-first; result nonempty, width≤8';
  if(equation.rule==='transpose') return 'binary relation [A → B]';
  let other:Id|undefined;for(const value of equation.ids) if(value!==id) {other=value;break;}
  const columns=exactColumns(other?facts.get(other):undefined);
  return columns?typeLabel(module,{kind:'relation',columns}):'relation matching resolved sibling schema';
}
/** Project the exact constraints and labels attached to one current child. @param module Forest. @param graph Fixed rules. @param facts Partial results. @param id Destination identity. @returns Structured description. */
function destination(module:DraftModule,graph:RuleGraph,facts:ReadonlyMap<Id,PartialFact>,id:Id):DestinationConstraint {
  const equations:Equation[]=[],required:Equation[]=[];
  for(const equation of graph.equations) if(equation.ids.includes(id)) {equations.push(equation);if(equation.rule==='expect'&&equation.ids[0]===id) required.push(equation);}
  const primary=required[0],sort=primary?.expected!=='relation'&&primary?.expected?.kind==='formula'?'formula':'relation';
  let exact:Schema|null=null,widths:readonly number[]=sort==='relation'?[1,2,3,4,5,6,7,8]:[];
  for(const equation of required) {
    const expected=equation.expected;
    if(expected&&expected!=='relation'&&expected.kind==='relation') exact=expected.columns;
    if(equation.widths) widths=equation.widths;
  }
  const labels=new Set<string>();for(const equation of equations) labels.add(description(module,equation,id,facts));
  return {slot:graph.slots.get(id)!,sort,exact,widths,descriptions:labels.size?[...labels]:[sort]};
}
/** Project accessible labels from the same constraints used for enforcement. @param module Forest. @param graph Fixed inventory. @param facts Partial results. @returns Current child-indexed constraints. */
export function destinations(module:DraftModule,graph:RuleGraph,facts:ReadonlyMap<Id,PartialFact>):ReadonlyMap<Id,DestinationConstraint> {
  const result=new Map<Id,DestinationConstraint>();for(const id of graph.slots.keys()) result.set(id,destination(module,graph,facts,id));return result;
}
