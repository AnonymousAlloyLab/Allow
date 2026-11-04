import { EGraphPanel } from './EGraphPanel';
import type { EGraphView } from './egraph';
import type { Job, Status } from './api';
interface Atom { id: string; memberships: string[] }
interface Relation { name: string; arity: number; tuples: string[][] }
interface WitnessState { atoms: Atom[]; relations: Relation[] }
interface Witness { states: WitnessState[]; traceLength: number; loopState: number; truncated: boolean; fullInstanceHash: string }
interface Canonical { status: string; payload: string | null; sha256: string | null; features: number[] | null; egraph?: EGraphView | null }
interface ResultJob extends Job { commandKind?: string; message?: string; witness?: Witness | null; canonical?: Canonical | null }
interface ResultProps { job: Job | null; notice: string }
/** Describe an outcome without overstating bounded evidence. @param status Job status. @param kind Run or check. @returns User-facing result label. */
export function resultLabel(status: Status, kind?: string): string {
  if (status === 'SAT' && kind === 'check') return 'Counterexample found';
  if (status === 'SAT' && kind === 'run') return 'Instance found';
  if (status === 'UNSAT' && kind === 'check') return 'No counterexample within bounds';
  if (status === 'UNSAT' && kind === 'run') return 'No instance within bounds';
  if (status === 'SAT') return 'Satisfiable within bounds';
  if (status === 'UNSAT') return 'Unsatisfiable within bounds';
  const labels: Record<Exclude<Status,'SAT'|'UNSAT'>,string> = {
    QUEUED:'Queued',RUNNING:'Running',VALIDATED:'Source validated',INVALID:'Invalid source',
    UNSUPPORTED:'Unsupported',UNKNOWN:'Inconclusive',ERROR:'Analysis error',
    TIMEOUT:'Time limit reached',CANCELLED:'Cancelled',
  };
  return labels[status];
}
/** Format one atom. @param atom Instance atom. @returns Readable atom label. */
function atomLabel(atom: Atom): string {
  return atom.memberships.length ? `${atom.id} (${atom.memberships.join(', ')})` : atom.id;
}
/** Render an atom. @param atom Instance atom. @returns Atom list item. */
function atomItem(atom: Atom) { return <li key={atom.id}>{atomLabel(atom)}</li>; }
/** Format one relation tuple. @param tuple Ordered atom IDs. @returns Readable tuple. */
function tupleLabel(tuple: string[]): string { return tuple.join(' → '); }
/** Render a relation and a bounded tuple selection. @param relation Witness relation. @returns Relation summary. */
function relationItem(relation: Relation) {
  const shown = relation.tuples.slice(0,8).map(tupleLabel).join(', ');
  const suffix = relation.tuples.length > 8 ? `, +${relation.tuples.length - 8} more` : '';
  return <li key={relation.name}><strong>{relation.name}</strong> <span>({relation.arity})</span>
    <div>{shown || '∅'}{suffix}</div></li>;
}
/** Render one witness state. @param state State data. @param index State index. @returns Compact state view. */
function stateItem(state: WitnessState, index: number) {
  return <section className="witness-state" key={index}>
    <h4>State {index + 1}</h4>
    {state.atoms.length > 0 && <><span className="result-caption">ATOMS</span>
      <ul>{state.atoms.slice(0,12).map(atomItem)}</ul>
      {state.atoms.length > 12 && <small>+{state.atoms.length - 12} more atoms</small>}</>}
    {state.relations.length > 0 && <><span className="result-caption">RELATIONS</span>
      <ul>{state.relations.slice(0,12).map(relationItem)}</ul>
      {state.relations.length > 12 && <small>+{state.relations.length - 12} more relations</small>}</>}
  </section>;
}
/** Render bounded witness details. @param props Witness value. @returns Witness section. */
function WitnessPanel(props: {witness: Witness}) {
  const witness = props.witness;
  return <div className="witness"><h4>Witness</h4>
    <p>{witness.traceLength} state{witness.traceLength === 1 ? '' : 's'}
      {witness.loopState >= 0 ? ` · loop at state ${witness.loopState + 1}` : ''}</p>
    {witness.states.slice(0,3).map(stateItem)}
    {witness.states.length > 3 && <small>+{witness.states.length - 3} more displayed states</small>}
    {witness.truncated && <p>Witness display is truncated.</p>}
    <details><summary>Witness provenance</summary><p>Full instance hash: {witness.fullInstanceHash}</p></details>
  </div>;
}
/** Render optional anonymous structural output. @param props Canonical result. @returns Expandable structural details. */
function CanonicalPanel(props: {canonical: Canonical}) {
  const value = props.canonical;
  return <details className="canonical-details"><summary>Anonymous structural profile</summary>
    <p>Status: {value.status}</p>
    {value.sha256 && <p>SHA-256: {value.sha256}</p>}
    {value.features && <p>Feature dimensions: {value.features.length}</p>}
    {value.payload && <pre>{value.payload}</pre>}
    <p>Structural representation for retrieval; it is not an equivalence proof.</p>
  </details>;
}
/** Render the analysis result and optional evidence. @param props Job and live notice. @returns Result panel. */
export function Results(props: ResultProps) {
  const job = props.job as ResultJob | null;
  return <div className="results"><div className="results-heading"><h3>ANALYSIS</h3>
    <span>{job?.status ?? 'READY'}</span></div>
    {job && <p className="result-label">{resultLabel(job.status,job.commandKind)}</p>}
    <p aria-live="polite">{props.notice}</p>
    {job?.message && <p>{job.message}</p>}
    {job?.witness && <WitnessPanel witness={job.witness}/>}
    {job?.canonical && <CanonicalPanel canonical={job.canonical}/>}
    {job?.canonical?.egraph && <EGraphPanel key={`${job.jobId}:${job.sourceHash}:${job.revision}:${job.epoch}`} value={job.canonical.egraph}/>}
    <p className="disclaimer">Results are bounded by the selected Alloy command. A lack of counterexamples is not an unbounded proof.</p>
  </div>;
}
