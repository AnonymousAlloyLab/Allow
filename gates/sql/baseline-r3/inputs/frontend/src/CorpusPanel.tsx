import { useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { corpusRecords, corpusSearch, corpusStatus } from './corpus';
import type { CorpusHit, CorpusRecord, CorpusSearch, CorpusStatus } from './corpus';

/** Create independent corpus state with a monotone request generation. @returns Private component state. */
function useCorpus() {
  const [status,setStatus] = useState<CorpusStatus | null>(null);
  const [records,setRecords] = useState<readonly CorpusRecord[]>([]);
  const [selected,setSelected] = useState('');
  const [result,setResult] = useState<CorpusSearch | null>(null);
  const [notice,setNotice] = useState('Browse locally stored predicates and their example pools.');
  const [busy,setBusy] = useState(false);
  const generation = useRef(0);
  return {status,setStatus,records,setRecords,selected,setSelected,result,setResult,notice,setNotice,busy,setBusy,generation};
}
type State = ReturnType<typeof useCorpus>;
/** Clear old results when starting a distinct request. @param state Component state. @returns New request generation. */
function begin(state: State): number {
  state.generation.current += 1;
  state.setResult(null); state.setBusy(true);
  return state.generation.current;
}
/** Refresh eligible records while suppressing stale responses. @param state Component state. @param token Authority. @returns Completion. */
async function refresh(state: State, token: string): Promise<void> {
  const generation = begin(state);
  state.setNotice('Reading the local corpus…');
  try {
    const [status,records] = await Promise.all([corpusStatus(token),corpusRecords(token)]);
    if (generation !== state.generation.current) return;
    state.setStatus(status); state.setRecords(records); state.setSelected(records[0]?.id ?? '');
    state.setNotice(records.length ? 'Choose a stored predicate to retrieve related candidates.' : 'No eligible embedded records yet.');
  } catch (error) {
    if (generation === state.generation.current) state.setNotice(error instanceof Error ? error.message : 'Corpus unavailable.');
  } finally { if (generation === state.generation.current) state.setBusy(false); }
}
/** Select a new record and invalidate any previous retrieval. @param state Component state. @param event Selection event. @returns Nothing. */
function select(state: State, event: ChangeEvent<HTMLSelectElement>): void {
  state.generation.current += 1; state.setSelected(event.target.value); state.setResult(null); state.setBusy(false);
}
/** Retrieve candidates for the exact selected record. @param state Component state. @param token Authority. @returns Completion. */
async function search(state: State, token: string): Promise<void> {
  const generation = begin(state);
  state.setNotice('Ranking candidates from the local corpus…');
  try {
    const result = await corpusSearch(token,state.selected);
    if (generation !== state.generation.current) return;
    state.setResult(result); state.setNotice('Candidate ranking ready. Similarity does not establish equivalence.');
  } catch (error) {
    if (generation === state.generation.current) state.setNotice(error instanceof Error ? error.message : 'Retrieval failed.');
  } finally { if (generation === state.generation.current) state.setBusy(false); }
}
/** Render a readable record option without revealing its original source. @param row Stored metadata. @returns Option. */
function option(row: CorpusRecord) {
  return <option key={row.id} value={row.id}>{row.id.slice(0,12)} · {row.family} · {row.n}+ / {row.n}−</option>;
}
/** Render one candidate with separate score components and compatibility. @param row Ranked candidate. @returns Evidence card. */
function candidate(row: CorpusHit) {
  return <li key={row.recordId} className="corpus-hit"><div><strong>{row.recordId.slice(0,12)}</strong><span className="corpus-score">{row.score.toFixed(3)}</span></div>
    <p>{row.family} · {row.positiveCount} examples / {row.negativeCount} counterexamples</p>
    <dl><div><dt>Hierarchy similarity</dt><dd>{row.canonicalSimilarity.toFixed(3)}</dd></div>
      <div><dt>Shared examples</dt><dd>{row.sharedPositive.toFixed(3)}</dd></div><div><dt>Shared counterexamples</dt><dd>{row.sharedNegative.toFixed(3)}</dd></div></dl>
    <small>{row.contextCompatible ? 'Matching environment and bounds' : 'Different environment or bounds · overlap credit is zero'}</small></li>;
}
/** Render retrieved evidence separately from solver results and editable source. @param props Checked response. @returns Results or no content. */
export function CorpusResults(props: {result: CorpusSearch | null}) {
  const result = props.result;
  if (!result) return null;
  return <div className="corpus-results"><p>{result.exact ? 'Exact ranking' : 'Approximate candidates'} · {result.candidateCount} eligible candidates · weights {result.weights.join(' / ')}</p>
    <p className="hint">Retrieval candidates only. Matching samples and high similarity do not prove equivalence.</p>
    <ol>{result.results.map(candidate)}</ol><details><summary>Embedding profile and query identity</summary><p>3072 dimensions · context / predicate / examples / counterexamples</p>
      <code>{result.modelId}</code><p>Query: <code>{result.queryRecordId}</code></p></details></div>;
}
/** Render authenticated local corpus browsing and evidence-only retrieval. @param props Launch authority. @returns Accessible corpus panel. */
export function CorpusPanel(props: {token: string}) {
  const state = useCorpus();
  return <section className="panel corpus" aria-labelledby="corpus-title"><div className="panel-title"><div><span className="panel-index">04</span><h2 id="corpus-title">Predicate corpus</h2></div>
    <span>LOCAL RETRIEVAL</span></div><p>Explore anonymous predicates with checked e-graph representatives and both witness polarities.</p>
    <div className="corpus-controls"><button className="secondary" disabled={state.busy} onClick={refresh.bind(null,state,props.token)}>Load corpus</button>
      <label htmlFor="corpus-record">Query predicate</label><select id="corpus-record" value={state.selected} onChange={select.bind(null,state)} disabled={!state.records.length}>
        {!state.records.length && <option value="">Load eligible records</option>}{state.records.map(option)}</select>
      <button className="primary" disabled={state.busy || !state.selected} onClick={search.bind(null,state,props.token)}>Find related predicates</button></div>
    {state.status && <p className="corpus-counts">{state.status.full} full pools · {state.status.vectors} embeddings · {state.status.revoked} revoked records</p>}
    <p role="status" aria-live="polite">{state.notice}</p><CorpusResults result={state.result}/></section>;
}
