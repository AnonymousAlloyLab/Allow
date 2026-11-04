import {expect,test,vi} from 'vitest';
import {AdvisoryValidator} from './advisory';
import type {AdvisoryTask} from './advisory';
import {advisoryKey} from './useAdvisory';
import {initialState,selectNode,editSource} from './state';
/** Construct an immediately completed diagnostic-only task. @param key Content key. @param starts Recorded operation keys. @returns Injectable task. */
function task(key:string,starts:string[]):AdvisoryTask {
  /** Record one validation start without any persistence operation. @param signal Owned lifetime. @returns Completion. */
  async function run(signal:AbortSignal):Promise<void> {if(!signal.aborted) starts.push(key);}
  return {key,run};
}
/** Construct a held operation that settles only after response or unmount abort. @param key Content key. @param starts Started operations. @param releases Response continuations. @returns Diagnostic task. */
function held(key:string,starts:string[],releases:Map<string,()=>void>):AdvisoryTask {
  /** Hold the first HTTP slot until response certainty or cancellation. @param signal Owned lifetime. @returns Completion. */
  function run(signal:AbortSignal):Promise<void> {
    starts.push(key);
    /** Register the held continuation. @param resolve Completion consumer. @returns Nothing. */
    function capture(resolve:()=>void):void {releases.set(key,resolve);signal.addEventListener('abort',resolve,{once:true});}
    return new Promise(capture);
  }
  return {key,run};
}
/** Coalesce rapid content edits into one latest complete validation. @returns Completion. */
async function debouncesLatest():Promise<void> {
  vi.useFakeTimers();const scheduler=new AdvisoryValidator(),starts:string[]=[];
  try {
    scheduler.request(task('one',starts));await vi.advanceTimersByTimeAsync(100);
    scheduler.request(task('two',starts));await vi.advanceTimersByTimeAsync(100);
    scheduler.request(task('three',starts));await vi.advanceTimersByTimeAsync(349);expect(starts).toEqual([]);
    await vi.advanceTimersByTimeAsync(1);expect(starts).toEqual(['three']);expect(vi.getTimerCount()).toBe(0);
  } finally {scheduler.dispose();vi.useRealTimers();}
}
/** Keep only one in-flight client request plus the latest pending content. @returns Completion. */
async function serializesLatest():Promise<void> {
  vi.useFakeTimers();const scheduler=new AdvisoryValidator(),starts:string[]=[],releases=new Map<string,()=>void>();
  try {
    scheduler.request(held('active',starts,releases));await vi.advanceTimersByTimeAsync(350);
    scheduler.request(task('obsolete',starts));scheduler.request(task('latest',starts));
    await vi.advanceTimersByTimeAsync(1000);expect(starts).toEqual(['active']);
    releases.get('active')!();await vi.advanceTimersByTimeAsync(350);expect(starts).toEqual(['active','latest']);
    expect(vi.getTimerCount()).toBe(0);
  } finally {scheduler.dispose();vi.useRealTimers();}
}
/** Do not retry unchanged invalid/unavailable input automatically, but retain intentional manual Check. @returns Completion. */
async function noRetryLoop():Promise<void> {
  vi.useFakeTimers();const scheduler=new AdvisoryValidator();let starts=0;
  /** Model a bounded availability failure. @param signal Owned lifetime. @returns Rejected completion. */
  async function unavailable(signal:AbortSignal):Promise<void> {void signal;starts++;throw new Error('busy');}
  try {
    scheduler.request({key:'same',run:unavailable});await vi.advanceTimersByTimeAsync(350);
    scheduler.request({key:'same',run:unavailable});await vi.advanceTimersByTimeAsync(30000);expect(starts).toBe(1);
    scheduler.request({key:'same',run:unavailable},true);await vi.advanceTimersByTimeAsync(0);expect(starts).toBe(2);
  } finally {scheduler.dispose();vi.useRealTimers();}
}
/** Clear queued incomplete-hole work and abort all owned waits on unmount. @returns Completion. */
async function clearsAndDisposes():Promise<void> {
  vi.useFakeTimers();const scheduler=new AdvisoryValidator(),starts:string[]=[],releases=new Map<string,()=>void>();
  try {
    scheduler.request(task('incomplete',starts));scheduler.clearPending();await vi.advanceTimersByTimeAsync(350);expect(starts).toEqual([]);
    scheduler.request(held('active',starts,releases));await vi.advanceTimersByTimeAsync(350);
    scheduler.request(task('queued',starts));scheduler.dispose();await vi.advanceTimersByTimeAsync(30000);
    expect(starts).toEqual(['active']);expect(vi.getTimerCount()).toBe(0);
  } finally {scheduler.dispose();vi.useRealTimers();}
}
/** Selection invalidates presentation while preserving the automatic validation content key. @returns Nothing. */
function ignoresSelectionGeneration():void {
  const state=initialState(),selected=selectNode(state,'selected');
  expect(advisoryKey(selected)).toBe(advisoryKey(state));expect(selected.epoch).not.toBe(state.epoch);
  expect(advisoryKey(editSource(selected,'new source'))).not.toBe(advisoryKey(state));
}
test('automatic source projection debounces rapid edits to latest draft',debouncesLatest);
test('advisory requests serialize one active and only latest pending draft',serializesLatest);
test('unchanged busy/invalid input has no automatic retry loop',noRetryLoop);
test('holes clear pending work and unmount aborts without further requests',clearsAndDisposes);
test('selection-only epoch changes do not request another automatic parse',ignoresSelectionGeneration);
