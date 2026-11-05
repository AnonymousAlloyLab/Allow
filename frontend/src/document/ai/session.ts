import type {Controller} from '../controller';
import {publishDocument} from '../controller';
import type {AssistantState,Create,Job,Kind,Snapshot} from './types';
import {call,route} from './api';
import * as checks from './checks';
import {digest} from '../api';
import {apply,capture,identity,matching,undoEdit} from './transactions';
export const INITIAL:AssistantState={config:null,job:null,snapshot:null,undo:null,busy:false,notice:''};
const ACTIVE=['CREATING','AWAITING_DISCLOSURE','GENERATING','VERIFYING'];
/** Own one mounted authority's private assistant requests and polling lifetime. */
export class AssistantSession {
  private view:AssistantState=INITIAL;
  private controller:Controller;
  private online=true;
  private disposed=false;
  private request=new AbortController();
  private timer:ReturnType<typeof setTimeout>|null=null;
  private delay=500;
  private generation=0;
  private readonly consumed=new Set<string>();
  private readonly notify:(state:AssistantState)=>void;
  /** Bind the controller and React setter without exposing mutable authority. @param controller Workbench controller. @param notify React state publisher. */
  constructor(controller:Controller,notify:(state:AssistantState)=>void) {this.controller=controller;this.notify=notify;}
  /** Refresh current references without changing authority. @param controller Latest controller. @param online Whether server actions are allowed. @returns Nothing. */
  connect(controller:Controller,online:boolean):void {this.controller=controller;this.online=online;}
  /** Publish bounded assistant state only while mounted. @param changes Partial new state. @returns Nothing. */
  private publish(changes:Partial<AssistantState>):void {if(changes.job&&['EXPIRED','CANCELLED','FAILED','APPLIED'].includes(changes.job.status)) changes={...changes,job:{...changes.job,payload:null,payloadHash:null,proposal:null,beforeSource:null},snapshot:null,busy:false};this.view={...this.view,...changes};if(!this.disposed) this.notify(this.view);}
  /** Discover private assistance quietly when it is unavailable publicly. @returns Completion. */
  async initialize():Promise<void> {try {if(this.online) this.publish({config:checks.config(await call(this.controller.token,'/config',undefined,this.request.signal))});} catch {this.publish({config:null});}}
  /** Cancel stale work and invalidate an undo after any observed draft change. @returns Nothing. */
  observe():void {
    const current=identity(this.controller.current.current.document),snapshot=this.view.snapshot;
    if(this.view.undo&&current!==this.view.undo.appliedKey) this.publish({undo:null});
    if(snapshot&&(!this.online||current!==snapshot.key)&&this.view.job) {void this.cancel();this.publish({snapshot:null,notice:'Assistant proposal is stale. Prepare again from the current draft.'});}
  }
  /** Prepare exact current candidate; no disclosure occurs here. @param kind Closed feature. @param intent Reviewed natural-language intent. @returns Completion. */
  async prepare(kind:Kind,intent:string):Promise<void> {
    if(!this.online||this.view.busy||this.disposed) return;
    const generation=++this.generation;this.clearTimer();this.delay=500;
    try {
      const snapshot=capture(this.controller.current.current.document),accepted=snapshot.document.accepted!;
      const body:Create={requestId:crypto.randomUUID(),documentId:accepted.documentId,baseRevision:snapshot.document.baseRevision,draftId:snapshot.document.draftId,draftEpoch:snapshot.document.epoch,contentGeneration:snapshot.document.contentGeneration,artifactId:accepted.artifact.artifactId,sourceHash:accepted.artifact.sourceHash,candidate:snapshot.candidate,intent,kind};
      this.publish({busy:true,snapshot,job:null,notice:'Preparing anonymous payload. Nothing has been sent to the provider.'});
      const job=checks.job(await call(this.controller.token,'/jobs',body,this.request.signal));
      if(generation===this.generation&&this.current(snapshot)) {this.publish({job,busy:false});this.schedule();} else {await this.cancelJob(job);if(generation===this.generation) this.publish({busy:false,snapshot:null,notice:'Draft changed while preparing. Prepare again.'});}
    } catch {if(generation===this.generation) this.publish({busy:false,notice:'Could not prepare assistant request. The draft is unchanged.'});}
  }
  /** Check a captured snapshot immediately before every action. @param snapshot Frozen draft. @returns Whether still current and live. */
  private current(snapshot:Snapshot):boolean {return !this.disposed&&this.online&&this.view.snapshot===snapshot&&(!this.view.job||Date.now()<Date.parse(this.view.job.expiresAt))&&identity(this.controller.current.current.document)===snapshot.key;}
  /** Explicitly consent to exactly the currently previewed attempt. @returns Completion. */
  async send():Promise<void> {
    const {job,snapshot}=this.view;if(!job||!snapshot||!this.current(snapshot)||this.view.busy||job.status!=='AWAITING_DISCLOSURE') return;
    const generation=this.generation;this.publish({busy:true,notice:'Checking the exact preview before disclosure.'});
    try {if(!job.payload||await digest(job.payload)!==job.payloadHash||!this.current(snapshot)||Date.now()>=Date.parse(job.expiresAt)) throw new Error('Stale');const next=checks.job(await call(this.controller.token,route(job.id,'/disclosure'),{binding:job.binding,attempt:job.attempt,payloadHash:job.payloadHash,termsVersion:job.termsVersion},this.request.signal));if(generation===this.generation) {if(this.current(snapshot)) this.publish({job:next,busy:false});this.schedule();}}
    catch {if(generation===this.generation) {this.publish({busy:false,notice:'Disclosure outcome unavailable. Refresh status; do not create another request.'});this.schedule();}}
  }
  /** Schedule a bounded non-dispatching status read. @returns Nothing. */
  private schedule():void {
    this.clearTimer();const job=this.view.job;
    if(!job||!this.online||this.disposed) return;
    if(!ACTIVE.includes(job.status)) {if(['REVIEW_READY','SUGGESTION'].includes(job.status)) this.timer=setTimeout(this.expire.bind(this),Math.max(0,Date.parse(job.expiresAt)-Date.now()));return;}
    if(Date.now()>=Date.parse(job.expiresAt)) {this.expire();return;}
    this.timer=setTimeout(this.poll.bind(this),this.delay);this.delay=Math.min(5000,this.delay*1.5);
  }
  /** Expire a retained proposal without changing the local draft. @returns Nothing. */
  private expire():void {const job=this.view.job;if(job&&[...ACTIVE,'REVIEW_READY','SUGGESTION'].includes(job.status)) {this.generation++;this.clearTimer();this.publish({job:{...job,status:'EXPIRED',payload:null,payloadHash:null,proposal:null,beforeSource:null},snapshot:null,busy:false,notice:'Assistant proposal expired. Prepare again.'});}}
  /** Read current status without resuming any provider effect. @returns Completion. */
  private async poll():Promise<void> {
    const {job,snapshot}=this.view,generation=this.generation;if(!job||!snapshot) return;
    if(Date.now()>=Date.parse(job.expiresAt)) {this.expire();return;}
    if(!this.current(snapshot)) {this.observe();return;}
    try {const next=checks.job(await call(this.controller.token,route(job.id),undefined,this.request.signal));if(next.id!==job.id||next.binding!==job.binding) throw new Error('Invalid');if(this.current(snapshot)&&this.view.job?.id===job.id) this.publish({job:next,busy:false});}
    catch {if(generation===this.generation) this.publish({busy:false,notice:'Assistant status unavailable. Cancellation remains available.'});}
    if(generation===this.generation) this.schedule();
  }
  /** Request current approval then atomically compare actual draft and receipt. @returns Completion. */
  async apply():Promise<void> {
    const {job,snapshot}=this.view;if(!job?.proposal||!snapshot||!this.current(snapshot)||this.view.busy||job.status!=='REVIEW_READY') return;
    const generation=this.generation;this.publish({busy:true});
    try {
      const receipt=checks.receipt(await call(this.controller.token,route(job.id,'/approve'),{binding:job.binding,proposalHash:job.proposal.proposalHash},this.request.signal));
      if(!await matching(receipt,job)||!this.current(snapshot)||Date.now()>=Date.parse(job.expiresAt)||Date.parse(receipt.expiresAt)>Date.parse(job.expiresAt)||Date.parse(receipt.expiresAt)>Date.now()+10000) throw new Error('Stale');
      const transaction=apply(this.controller.current.current.document,snapshot,receipt,this.consumed);
      if(!transaction) throw new Error('Stale');
      this.clearTimer();publishDocument(this.controller,transaction.document);this.publish({job:{...job,status:'APPLIED'},snapshot:null,undo:transaction.undo,busy:false,notice:'Applied to draft only. Save version remains a separate action.'});
    } catch {if(generation===this.generation) this.publish({busy:false,notice:'Approval is stale or unavailable. The draft is unchanged.'});}
  }
  /** Undo this one local AI edit without touching saved history. @returns Nothing. */
  undo():void {const transaction=this.view.undo;if(!transaction) return;const document=undoEdit(this.controller.current.current.document,transaction);if(document) publishDocument(this.controller,document);this.publish({undo:null,notice:document?'AI draft edit undone.':'Undo unavailable after another operation.'});}
  /** Clear a pending timer without claiming server cancellation. @returns Nothing. */
  private clearTimer():void {if(this.timer) clearTimeout(this.timer);this.timer=null;}
  /** Send a server cancellation independent of the polling request. @param job Exact owned job. @returns Completion. */
  private async cancelJob(job:Job):Promise<void> {try {await call(this.controller.token,route(job.id,'/cancel'),{binding:job.binding});} catch { /* Ownership cleanup is enforced server-side even after client disconnect. */ }}
  /** Cancel server work and stop local polling without replacing the draft. @returns Completion. */
  async cancel():Promise<void> {const job=this.view.job;this.generation++;this.clearTimer();this.publish({job:job?{...job,status:'CANCELLED'}:null,snapshot:null,busy:false,notice:'Cancellation requested. The draft is unchanged.'});if(job&&this.online) await this.cancelJob(job);}
  /** End requests on unmount or capability replacement. @returns Nothing. */
  dispose():void {this.disposed=true;this.generation++;this.clearTimer();this.request.abort();if(this.view.job&&this.online) void this.cancelJob(this.view.job);}
}
