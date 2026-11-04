import { expect, test } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { CorpusResults } from './CorpusPanel';
import { decodeSearch } from './corpus';
import type { CorpusSearch } from './corpus';

/** Create a result with deliberately incompatible contexts. @returns Safe test envelope. */
function fixture(): CorpusSearch {
  return {queryRecordId:'a'.repeat(64),modelId:'local-pinned-model',exact:true,candidateCount:8,
    weights:[.55,.225,.225],results:[{recordId:'b'.repeat(64),family:'family <script>',score:.4,
      canonicalSimilarity:.8,predicateCosine:.9,sharedPositive:0,sharedNegative:0,
      contextCompatible:false,positiveCount:3,negativeCount:3}]};
}
/** Render candidates with explicit non-proof labels and escaped metadata. @returns Nothing. */
function displaysCandidateBoundary(): void {
  const html = renderToStaticMarkup(<CorpusResults result={fixture()}/>);
  expect(html).toContain('Matching samples and high similarity do not prove equivalence');
  expect(html).toContain('overlap credit is zero');
  expect(html).toContain('3072 dimensions');
  expect(html).toContain('family &lt;script&gt;');
  expect(html).not.toContain('<script>');
  expect(html).toContain('3 examples / 3 counterexamples');
}
/** A cleared or stale response has no visible previous result. @returns Nothing. */
function clearsStaleDisplay(): void {
  expect(renderToStaticMarkup(<CorpusResults result={null}/>)).toBe('');
}
/** Exercise an unrelated response through the strict decoder. @returns Nothing. */
function wrongQuery(): void { decodeSearch(fixture(),'c'.repeat(64)); }
/** Reject unrelated evidence even when its rank data is otherwise well formed. @returns Nothing. */
function rejectsWrongIdentity(): void { expect(wrongQuery).toThrow('identity changed'); }
/** Exercise a nonfinite score rather than rendering it as a confidence value. @returns Nothing. */
function invalidScore(): void {
  const value = fixture();
  decodeSearch({...value,results:[{...value.results[0],score:Number.NaN}]},value.queryRecordId);
}
/** Reject nonfinite measurements at the presentation boundary. @returns Nothing. */
function rejectsNonfinite(): void { expect(invalidScore).toThrow('Invalid corpus measurement'); }
test('renders evidence-only retrieval and context limitations',displaysCandidateBoundary);
test('clears previous corpus results',clearsStaleDisplay);
test('rejects mismatched corpus query identity',rejectsWrongIdentity);
test('rejects nonfinite retrieval measurements',rejectsNonfinite);
