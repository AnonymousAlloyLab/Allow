import {comparisonClassification} from './blockComparison';
import type {ComparisonData,ComparisonCategory,ComparisonCorrespondence} from './blockComparison';
const LABELS:Readonly<Record<string,string>>={both:'Both A and B',leftOnly:'A holds; B does not',rightOnly:'B holds; A does not',neither:'Neither A nor B'};
/** Render exact shared-assignment witnesses without color-only meanings or unbounded equivalence claims. @param props Bound result. @returns Evidence panels. */
export function BlockComparisonResults(props:{data:ComparisonData}) {
  const panels=[];for(const key of ['both','leftOnly','rightOnly','neither']) {const category=props.data.categories?.[key];if(category) panels.push(<Category key={key} name={LABELS[key]} category={category} mapping={props.data.correspondence}/>);}
  const classification=comparisonClassification(props.data),label=classification==='DISTINGUISHED'?'A bounded distinguishing example exists.':classification==='AGREEMENT'?'A and B agree under these facts, assignments and bounds.':classification==='NO_INSTANCES'?'No admissible bounded instances. Facts may be inconsistent or domains empty.':'Comparison inconclusive; no agreement established.';
  return <div className="comparison-results"><p role="status"><strong>{label}</strong></p><p>Uniform scope {props.data.scope}; bitwidth 4; maximum sequence 3. This is bounded evidence for selected formulas.</p>{props.data.correspondence&&<SharedMapping mapping={props.data.correspondence}/>}<div className="comparison-categories">{panels}</div><details><summary>Evidence identity</summary><p>Request SHA256: {props.data.requestHash}</p><p>Source SHA256: {props.data.sourceHash}</p><p>Module SHA256: {props.data.moduleHash}</p>{props.data.correspondence&&<pre>{JSON.stringify(props.data.correspondence,null,2)}</pre>}</details></div>;
}
/** Explain the verified common declarations and positional parameter pairing in ordinary model names. @param props Checked correspondence. @returns Shared background explanation. */
function SharedMapping(props:{mapping:ComparisonCorrespondence}) {
  const declarations=[],parameters=[];
  for(const item of props.mapping.declarations) declarations.push(<li key={`${item.kind}:${item.name}`}>{item.kind==='signatures'?'Signature':item.kind==='fields'?'Field':item.kind} {item.name} ↔ {item.name}</li>);
  for(const [index,item] of props.mapping.parameters.entries()) parameters.push(<li key={index}>{item.leftName} ↔ {item.rightName}: {item.columns.join(' → ')} (shared set-valued relation)</li>);
  return <div className="comparison-mapping"><h3>Shared background and parameter mapping</h3><p>{props.mapping.leftPredicate} ↔ {props.mapping.rightPredicate}: both predicates use the same checked declarations and facts.</p><ul>{declarations}</ul>{parameters.length?<ul>{parameters}</ul>:<p>These predicates have no parameters.</p>}</div>;
}
/** Display one checked truth category and bounded shared-instance witness. @param props Category evidence. @returns Accessible category. */
function Category(props:{name:string;category:ComparisonCategory;mapping?:ComparisonCorrespondence}) {
  const item=props.category,assignments=[],states=[];
  for(const variable of item.assignment??[]) assignments.push(<li key={variable.id}><strong>{assignmentLabel(variable,props.mapping)}</strong> ({variable.columns.join(' → ')}): {variable.tuples.map(tupleText).join(', ')||'∅'}{variable.truncated?' — display truncated':''}</li>);
  for(const [index,state] of (item.witness?.states??[]).entries()) {const relations=[];for(const relation of state.relations) relations.push(<li key={relation.name}><strong>{relation.name}</strong> ({relation.arity}): {relation.tuples.map(tupleText).join(', ')||'∅'}</li>);states.push(<div key={index}><h4>Instance {index+1}</h4><p>Atoms: {state.atoms.map(atomText).join(', ')||'∅'}</p><ul>{relations}</ul></div>);}
  return <article className="comparison-category"><h3>{props.name}</h3><p><strong>{item.status==='SAT'?'Instance found':item.status==='UNSAT'?'No instance within bounds':item.status}</strong></p>{item.status==='SAT'&&<><p>Checked truth: A {String(item.left)}, B {String(item.right)}.</p><h4>Shared free-variable assignment</h4>{assignments.length?<ul>{assignments}</ul>:<p>No free variables.</p>}{states}{item.witness?.truncated&&<p>Instance display is truncated; hashes cover full evidence.</p>}<details><summary>Category evidence identity</summary><small>Evidence SHA256: {item.evidenceHash}</small><small>Full instance SHA256: {item.witness?.fullInstanceHash}</small><pre>{JSON.stringify(item.assignment,null,2)}</pre></details></>}</article>;
}
/** Resolve original model parameter names before showing worker-generated variable labels. @param variable Shared assignment. @param mapping Checked original parameter pairs. @returns Meaningful name. */
function assignmentLabel(variable:{id:string;name:string},mapping?:ComparisonCorrespondence):string {
  for(const pair of mapping?.parameters??[]) if(pair.sharedId===variable.id) return `${pair.leftName} ↔ ${pair.rightName}`;
  return variable.name;
}
/** Format a bounded tuple with ordered columns. @param tuple Atom identities. @returns Text. */
function tupleText(tuple:readonly string[]):string {return tuple.join(' → ');}
/** Format one atom and its checked signature memberships. @param atom Instance atom. @returns Text. */
function atomText(atom:{id:string;memberships:readonly string[]}):string {return `${atom.id}${atom.memberships.length?` (${atom.memberships.join(', ')})`:''}`;}
