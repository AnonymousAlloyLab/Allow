import { expect, test } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { EGraphPanel } from './EGraphPanel';
import { Results } from './Results';
import type { EGraphIsland, EGraphView, EGraphTerm } from './egraph';
import type { Job } from './api';
const TERM: EGraphTerm = {op:'TRUE',sort:{kind:'BOOL',schema:[]},atom:'',children:[]};
/** Create a current checked island with bounded search. @returns Anonymous wire fixture. */
function island(): EGraphIsland {
  return {rootPath:[2,0],certificateStatus:'CHECKED',stopReason:'MATCH_LIMIT',input:TERM,extracted:TERM,inputCost:1,extractedCost:1,
    stats:{nodes:3,classes:2,unions:1},preview:{classes:[{id:0,nodes:[TERM]},{id:1,nodes:[TERM]}],edges:[{from:0,to:1,position:0},{from:0,to:1,position:0}],truncated:true},proofSummary:{steps:1,bytes:100},certificate:{profile:'allow-egraph-proof-v1',steps:[]}};
}
/** Create the aggregate wire fixture. @param value Optional island override. @returns Egraph response. */
function view(value: EGraphIsland = island()): EGraphView {
  return {profile:'allow-egraph-v1',rulesetDigest:'anonymous-registry-digest',status:'AVAILABLE',islands:[value,{...value,rootPath:[3]}],truncated:false};
}
/** Keep checked local evidence independent from incomplete saturation. @returns Nothing. */
function separatesEvidenceAndBudget(): void {
  const html = renderToStaticMarkup(<EGraphPanel value={view()}/>);
  expect(html).toContain('Equivalence certificate checked');
  expect(html).toContain('Match budget reached');
  expect(html).toContain('Search is incomplete');
  expect(html).toContain('Graph preview is truncated');
  expect(html).toContain('Root 3');
  expect(html).toContain('Download anonymous certificate');
  expect(html).toContain('aria-label="Anonymous e-class membership and directed child dependencies"');
  expect(html).toContain('Class 0');
  expect(html).toContain('Class 0 → class 1 · child 1');
  expect(html).toContain('Directed child dependencies · 1');
  expect(html).toContain('marker-end=');
}
/** Suppress untrusted extracted terms and checked claims when replay fails. @returns Nothing. */
function hidesFailedExtraction(): void {
  const value = {...island(),certificateStatus:'FAILED',extracted:{...TERM,atom:'MUST_NOT_RENDER'}};
  const html = renderToStaticMarkup(<EGraphPanel value={view(value)}/>);
  expect(html).toContain('Certificate check failed');
  expect(html).not.toContain('Equivalence certificate checked');
  expect(html).not.toContain('MUST_NOT_RENDER');
  expect(html).not.toContain('Anonymous extracted term');
}
/** Describe aggregate truncation and empty output without claiming completeness. @returns Nothing. */
function explainsMissingIslands(): void {
  const html = renderToStaticMarkup(<EGraphPanel value={{...view(),islands:[],truncated:true}}/>);
  expect(html).toContain('not every root is represented');
  expect(html).toContain('No extracted equivalence is claimed');
  expect(html).not.toContain('Equivalence certificate checked');
}
/** Render bounded solver evidence and checked optimization as separate claims. @returns Nothing. */
function preservesBoundedSolverLabels(): void {
  const job: Job = {jobId:'j',sourceHash:'h',revision:1,epoch:1,status:'UNSAT',commandKind:'check',canonical:{status:'AVAILABLE',payload:'[]',sha256:'s',features:[],egraph:view()}};
  const html = renderToStaticMarkup(<Results job={job} notice="Finished"/>);
  expect(html).toContain('No counterexample within bounds');
  expect(html).toContain('Equivalence certificate checked');
  expect(html).toContain('Original Alloy source');
  expect(html).toContain('it is not an equivalence proof');
  expect(renderToStaticMarkup(<Results job={null} notice="Edited"/>)).not.toContain('Equality optimization');
}
/** Reject presentation of incomplete checked records as checked evidence. @returns Nothing. */
function suppressesMissingCheckedTerms(): void {
  const html = renderToStaticMarkup(<EGraphPanel value={view({...island(),extracted:null})}/>);
  expect(html).not.toContain('Equivalence certificate checked');
  expect(html).toContain('Equivalence certificate unavailable');
}
test('separates checked evidence from search and preview budgets',separatesEvidenceAndBudget);
test('does not present failed extraction',hidesFailedExtraction);
test('honestly reports missing islands',explainsMissingIslands);
test('preserves independent solver and optimization claims',preservesBoundedSolverLabels);
test('requires extracted terms for checked presentation',suppressesMissingCheckedTerms);
