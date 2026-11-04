import { expect, test, vi } from 'vitest';
import { cancelSnapshot, sameIdentity } from './api';
import type { CancellationOutcome, Job, JobIdentity } from './api';

const SNAPSHOT: JobIdentity = {jobId:'job-a',sourceHash:'source-a',revision:1,epoch:2};
let current: JobIdentity = {...SNAPSHOT};
let resolveRequest: (value: Response) => void;
let rejectRequest: (reason: Error) => void;

/** Capture a controllable network request for out-of-order response tests. @param resolve Deferred HTTP response resolver. @param reject Deferred network error resolver. @returns Nothing. */
function captureRequest(resolve: (value: Response) => void, reject: (reason: Error) => void): void {
  resolveRequest = resolve;
  rejectRequest = reject;
}
/** Return a pending network request without touching a real service. @returns Controllable response promise. */
function deferredFetch(): Promise<Response> { return new Promise(captureRequest); }
/** Read the test's current active source and presentation identity. @returns Current job identity. */
function readCurrent(): JobIdentity { return current; }
/** Start cancellation using the actual guarded API orchestration. @returns Pending current-or-stale cancellation outcome. */
function beginCancellation(): Promise<CancellationOutcome | null> {
  current = {...SNAPSHOT};
  vi.stubGlobal('fetch',deferredFetch);
  return cancelSnapshot('local-test-authority',SNAPSHOT,readCurrent);
}
/** Deliver an HTTP response with exact or deliberately altered identity. @param identity Returned response identity. @returns Nothing. */
function respond(identity: JobIdentity = SNAPSHOT): void {
  const job: Job = {...identity,status:'CANCELLED'};
  resolveRequest(new Response(JSON.stringify(job),{status:200}));
}
/** Accept cancellation only when all four identity fields match. @returns Test completion promise. */
async function acceptsCurrentCancellation(): Promise<void> {
  const pending = beginCancellation();
  respond();
  expect((await pending)?.job?.status).toBe('CANCELLED');
  vi.unstubAllGlobals();
}
/** Suppress a successful old cancellation after a raw draft edit. @returns Test completion promise. */
async function ignoresStaleSuccess(): Promise<void> {
  const pending = beginCancellation();
  current = {...SNAPSHOT,epoch:3};
  respond();
  expect(await pending).toBeNull();
  vi.unstubAllGlobals();
}
/** Suppress an old cancellation error after the active job changes. @returns Test completion promise. */
async function ignoresStaleFailure(): Promise<void> {
  const pending = beginCancellation();
  current = {...SNAPSHOT,jobId:'job-b',sourceHash:'source-b'};
  rejectRequest(new Error('Obsolete cancellation failure.'));
  expect(await pending).toBeNull();
  vi.unstubAllGlobals();
}
/** Suppress an obsolete cancellation error after a raw draft epoch changes. @returns Test completion promise. */
async function ignoresEditedFailure(): Promise<void> {
  const pending = beginCancellation();
  current = {...SNAPSHOT,epoch:3};
  rejectRequest(new Error('Failure for an earlier draft.'));
  expect(await pending).toBeNull();
  vi.unstubAllGlobals();
}
/** Reject cancellation responses that claim the epoch but name another source. @returns Test completion promise. */
async function rejectsWrongSource(): Promise<void> {
  const pending = beginCancellation();
  respond({...SNAPSHOT,sourceHash:'different-source'});
  expect(await pending).toBeNull();
  vi.unstubAllGlobals();
}
/** Reject cancellation responses that claim the epoch but name another job. @returns Test completion promise. */
async function rejectsWrongJob(): Promise<void> {
  const pending = beginCancellation();
  respond({...SNAPSHOT,jobId:'different-job'});
  expect(await pending).toBeNull();
  vi.unstubAllGlobals();
}
/** Retain a current network failure as a user-visible cancellation notice. @returns Test completion promise. */
async function reportsCurrentFailure(): Promise<void> {
  const pending = beginCancellation();
  rejectRequest(new Error('Current cancellation failure.'));
  expect((await pending)?.error).toBe('Current cancellation failure.');
  vi.unstubAllGlobals();
}
/** Require source, job, revision and epoch equality independently. @returns Nothing. */
function checksAllIdentityFields(): void {
  expect(sameIdentity(SNAPSHOT,{...SNAPSHOT})).toBe(true);
  expect(sameIdentity(SNAPSHOT,{...SNAPSHOT,revision:2})).toBe(false);
  expect(sameIdentity(SNAPSHOT,{...SNAPSHOT,epoch:3})).toBe(false);
  expect(sameIdentity(SNAPSHOT,{...SNAPSHOT,jobId:'other'})).toBe(false);
  expect(sameIdentity(SNAPSHOT,{...SNAPSHOT,sourceHash:'other'})).toBe(false);
}

test('accepts exact current cancellation',acceptsCurrentCancellation);
test('ignores cancellation success after an invalid raw draft edit',ignoresStaleSuccess);
test('ignores cancellation failure after active job changes',ignoresStaleFailure);
test('ignores cancellation failure after a raw draft edit',ignoresEditedFailure);
test('rejects cancellation response with another source hash',rejectsWrongSource);
test('rejects cancellation response with another job ID',rejectsWrongJob);
test('reports a current cancellation failure',reportsCurrentFailure);
test('compares every active identity field',checksAllIdentityFields);
