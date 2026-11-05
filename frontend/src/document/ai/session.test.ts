import {test,expect,vi} from 'vitest';
import {initialState,editSource} from '../state';
import type {Controller,ViewState} from '../controller';
import {AssistantSession,INITIAL} from './session';
import type {AssistantState,Job} from './types';
import {digest} from '../api';
/** Ignore test state publications. @returns Nothing. */
function ignore():void {}
/** Create a controller whose source is deliberately different from its stale preview. @returns Controller. */
function controller():Controller {
  const original=initialState(),document={...editSource(original,'sig Person {}'),baseRevision:1,preview:'STALE_DISPLAY_ONLY',accepted:{documentId:'document',revision:1,headRevision:1,provenance:null,artifact:{artifactId:'artifact',mode:'TEXT_ONLY' as const,source:'old',sourceHash:'base',module:null,occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:'policy',dependencyHash:'dependency'}}};
  const view:ViewState={document,documents:[],target:0,history:null,direction:'UNDO'};return {token:'private-test-token',current:{current:view},set:ignore};
}
/** Encode a local closed server response. @param data Bounded data. @param status HTTP status. @returns Response. */
function reply(data:unknown,status=200):Response {return new Response(JSON.stringify({protocol:1,status:'OK',data}),{status});}
/** Build an exact prepared job for mocked transport tests. @returns Job. */
async function prepared():Promise<Job> {const payload='{"anonymous":"sig Slot0 {}"}';return {id:'job',status:'AWAITING_DISCLOSURE',binding:'binding',expiresAt:new Date(Date.now()+60000).toISOString(),attempt:1,beforeSource:'sig Person {}',payload,payloadHash:await digest(payload),model:'gpt-6.1-sol',termsVersion:'terms-v1',code:null,proposal:null};}
/** Capture exact candidate, fresh per-repair consent and server cancellation. @returns Completion. */
async function disclosureLifecycle():Promise<void> {
  vi.useFakeTimers();const repairHash=await digest('repair payload'),c=controller(),job=await prepared(),calls:{path:string;body:unknown}[]=[],holder={view:INITIAL};let stage=0;
  /** Retain the latest assistant presentation. @param view Next state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Supply explicit creation, consent, repair and cancel responses. @param path Request URL. @param init Fetch options. @returns Response. */
  async function fetcher(path:RequestInfo|URL,init?:RequestInit):Promise<Response> {
    const url=String(path),body=init?.body?JSON.parse(String(init.body)):null;calls.push({path:url,body});
    if(url.endsWith('/config')) return reply({mode:'FIXTURE',model:'fixture',termsVersion:'terms',limits:{}});
    if(url.endsWith('/disclosure')) {stage=1;return reply({...job,status:'GENERATING'});}
    if(url.endsWith('/cancel')) return reply({...job,status:'CANCELLED'});
    if(init?.method==='GET'&&stage===1) return reply({...job,attempt:2,payload:'repair payload',payloadHash:repairHash});
    return reply(job);
  }
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(c,publish);
  try {await session.initialize();await session.prepare('SOURCE_EDIT','intent');expect((calls[1].body as {candidate:{source:string}}).candidate.source).toBe('sig Person {}');expect(calls).toHaveLength(2);
    await session.send();expect(calls.filter(isDisclosure)).toHaveLength(1);await vi.advanceTimersByTimeAsync(2000);expect(holder.view.job?.attempt).toBe(2);expect(calls.filter(isDisclosure)).toHaveLength(1);
    await session.cancel();expect(calls.some(isCancel)).toBe(true);await vi.advanceTimersByTimeAsync(10000);expect(holder.view.job?.status).toBe('CANCELLED');
  } finally {session.dispose();vi.useRealTimers();vi.unstubAllGlobals();}
}
/** Identify disclosure calls. @param call Captured call. @returns Whether consent dispatch. */
function isDisclosure(call:{path:string}):boolean {return call.path.endsWith('/disclosure');}
/** Identify server cancel calls. @param call Captured call. @returns Whether cancel. */
function isCancel(call:{path:string}):boolean {return call.path.endsWith('/cancel');}
/** Deny stale application and stop polling on observed content change. @returns Completion. */
async function staleCancellation():Promise<void> {
  const c=controller(),job=await prepared(),paths:string[]=[],holder={view:INITIAL};
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Reply without introducing provider side effects. @param path URL. @returns Response. */
  async function fetcher(path:RequestInfo|URL):Promise<Response> {paths.push(String(path));return reply(job);}
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(c,publish);
  try {await session.prepare('SOURCE_EDIT','intent');c.current.current={...c.current.current,document:editSource(c.current.current.document,'sig Changed {}')};session.observe();await Promise.resolve();expect(holder.view.snapshot).toBeNull();expect(paths.some(cancelPath)).toBe(true);await session.send();expect(paths.some(disclosurePath)).toBe(false);}
  finally {session.dispose();vi.unstubAllGlobals();}
}
/** Identify a cancel URL. @param path URL. @returns Whether cancel. */
function cancelPath(path:string):boolean {return path.endsWith('/cancel');}
/** Identify disclosure URL. @param path URL. @returns Whether disclosure. */
function disclosurePath(path:string):boolean {return path.endsWith('/disclosure');}
/** Hide ordinary public-mode forbidden config quietly. @returns Completion. */
async function publicOff():Promise<void> {
  const holder={view:INITIAL};
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Return public forbidden without an expiry signal. @returns Response. */
  async function forbidden():Promise<Response> {return reply({},403);}
  vi.stubGlobal('fetch',forbidden);const session=new AssistantSession(controller(),publish);
  try {await session.initialize();expect(holder.view.config?.mode).toBe('OFF');expect(holder.view.notice).toBe('');} finally {session.dispose();vi.unstubAllGlobals();}
}
/** Expire a retained proposal locally and deny subsequent approval requests. @returns Completion. */
async function retainedExpiry():Promise<void> {
  vi.useFakeTimers();const job={...await prepared(),status:'REVIEW_READY',expiresAt:new Date(Date.now()+500).toISOString()},holder={view:INITIAL},paths:string[]=[];
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Reply with a short-lived reviewed job. @param path Request URL. @returns Response. */
  async function fetcher(path:RequestInfo|URL):Promise<Response> {paths.push(String(path));return reply(job);}
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(controller(),publish);
  try {await session.prepare('SOURCE_EDIT','intent');await vi.advanceTimersByTimeAsync(501);expect(holder.view.job?.status).toBe('EXPIRED');expect(holder.view.snapshot).toBeNull();await session.apply();expect(paths).toHaveLength(1);}
  finally {session.dispose();vi.useRealTimers();vi.unstubAllGlobals();}
}
test('retained proposal expires without server approval or draft mutation',retainedExpiry);
/** Release an expired active poll and erase every retained provider buffer. @returns Completion. */
async function activeExpiry():Promise<void> {
  vi.useFakeTimers();const job={...await prepared(),status:'GENERATING',expiresAt:new Date(Date.now()+100).toISOString()},holder={view:INITIAL},paths:string[]=[];
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Return an active short-lived job. @param path Request URL. @returns Response. */
  async function fetcher(path:RequestInfo|URL):Promise<Response> {paths.push(String(path));return reply(job);}
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(controller(),publish);
  try {await session.prepare('SOURCE_EDIT','intent');await vi.advanceTimersByTimeAsync(501);expect(holder.view.job?.status).toBe('EXPIRED');expect(holder.view.busy).toBe(false);expect(holder.view.snapshot).toBeNull();expect(holder.view.job?.payload).toBeNull();expect(holder.view.job?.beforeSource).toBeNull();expect(holder.view.job?.proposal).toBeNull();expect(paths).toHaveLength(1);}
  finally {session.dispose();vi.useRealTimers();vi.unstubAllGlobals();}
}
/** Fence a delayed cancelled creation so it cannot overwrite a newer preparation. @returns Completion. */
async function cancelledPrepareRace():Promise<void> {
  const firstJob=await prepared(),newJob={...firstJob,id:'new-job'},holder={view:INITIAL};let creations=0,release:((value:Response)=>void)|null=null;
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Hold only the first create response. @param resolve Promise resolver. @returns Nothing. */
  function hold(resolve:(value:Response)=>void):void {release=resolve;}
  const delayed=new Promise<Response>(hold);
  /** Return a newer job while the cancelled create is still in flight. @param path Request URL. @param init HTTP options. @returns Response. */
  async function fetcher(path:RequestInfo|URL,init?:RequestInit):Promise<Response> {if(String(path).endsWith('/jobs')&&init?.method==='POST') {creations++;return creations===1?delayed:reply(newJob);}return reply({...firstJob,status:'CANCELLED'});}
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(controller(),publish);
  try {const first=session.prepare('SOURCE_EDIT','first');await Promise.resolve();await session.cancel();await session.prepare('SOURCE_EDIT','second');expect(holder.view.job?.id).toBe('new-job');const snapshot=holder.view.snapshot;(release! as (value:Response)=>void)(reply(firstJob));await first;expect(holder.view.job?.id).toBe('new-job');expect(holder.view.snapshot).toBe(snapshot);expect(holder.view.busy).toBe(false);}
  finally {session.dispose();vi.unstubAllGlobals();}
}
test('active poll crossing expiry becomes terminal and erases retained payload/source',activeExpiry);
test('late cancelled prepare cannot erase a newer operation snapshot or job',cancelledPrepareRace);
/** Clear content-bearing network buffers after cancellation and terminal failure. @returns Completion. */
async function terminalBuffers():Promise<void> {
  const job=await prepared(),holder={view:INITIAL};let failed=false;
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Supply bounded content on both normal and failed terminal jobs. @returns Response. */
  async function fetcher():Promise<Response> {return reply({...job,status:failed?'FAILED':job.status});}
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(controller(),publish);
  try {await session.prepare('SOURCE_EDIT','intent');expect(holder.view.job?.payload).not.toBeNull();await session.cancel();expect(holder.view.job?.payload).toBeNull();expect(holder.view.job?.beforeSource).toBeNull();failed=true;await session.prepare('SOURCE_EDIT','new');expect(holder.view.job?.status).toBe('FAILED');expect(holder.view.job?.payload).toBeNull();expect(holder.view.snapshot).toBeNull();}
  finally {session.dispose();vi.unstubAllGlobals();}
}
/** Applying drops delivered network content while retaining deliberate local draft undo. @returns Completion. */
async function appliedBuffers():Promise<void> {
  const received=await prepared(),source='sig Person {}\npred p {some Person}',sourceHash=await digest(source),job={...received,status:'REVIEW_READY',proposal:{source,sourceHash,proposalHash:'proposal',projection:'BLOCK_SUPPORTED',explanation:'suggestion'}},holder={view:INITIAL},c=controller();
  /** Retain status. @param view New state. @returns Nothing. */
  function publish(view:AssistantState):void {holder.view=view;}
  /** Supply exact approval receipt or current job. @param path Request URL. @returns Response. */
  async function fetcher(path:RequestInfo|URL):Promise<Response> {return String(path).endsWith('/approve')?reply({receiptId:'receipt',jobId:job.id,binding:job.binding,proposalHash:'proposal',source,sourceHash,expiresAt:Date.now()+5000}):reply(job);}
  vi.stubGlobal('fetch',fetcher);const session=new AssistantSession(c,publish);
  try {await session.prepare('SOURCE_EDIT','intent');await session.apply();expect(holder.view.job?.status).toBe('APPLIED');expect(holder.view.job?.payload).toBeNull();expect(holder.view.job?.proposal).toBeNull();expect(holder.view.job?.beforeSource).toBeNull();expect(holder.view.undo).not.toBeNull();expect(c.current.current.document.source).toBe(source);session.undo();expect(c.current.current.document.source).toBe('sig Person {}');}
  finally {session.dispose();vi.unstubAllGlobals();}
}
test('terminal cancellation and failure erase retained provider content',terminalBuffers);
test('application clears network buffers while retaining intentional one-use draft undo',appliedBuffers);
test('exact candidate prepare, explicit fresh repair consent, bounded polling and server cancellation',disclosureLifecycle);
test('observed draft changes cancel server work and prevent disclosure',staleCancellation);
test('public forbidden configuration quietly hides the assistant',publicOff);
