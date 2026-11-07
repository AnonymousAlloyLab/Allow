import {useEffect,useMemo,useRef,useState} from 'react';
import type {MutableRefObject} from 'react';
import type {Controller} from './controller';
import {advisoryKey} from './useAdvisory';
import {AdvisoryValidator} from './advisory';
import {candidate} from './state';
import {digest} from './api';
import {comparisonBase,comparisonRequest,decodeModel,type ModelFile} from './blockComparison';
import {parityKey,parityReady,parityAutomaticReady,parityEvidence,parityVerdict,type ParitySelection,type ParityData,type ParityFrame} from './oracleParity';
interface Outcome {key:string;data:ParityData}
export interface Runtime {activation?:number;availability?:string;validatedContent?:string;alive:boolean;generation:number;key:string;online:boolean;selection:ParitySelection;active:AbortController|null;inspection:AbortController|null}
export interface Context {controller:Controller;runtime:MutableRefObject<Runtime>;scheduler:AdvisoryValidator;setSelection:(value:ParitySelection)=>void;setOutcome:(value:Outcome|null)=>void;setNotice:(value:string)=>void;setBusy:(value:boolean)=>void}
const INITIAL:ParitySelection={enabled:false,targetId:'',scope:3,oracle:null};
/** Allocate the one serialized parity queue owned by this document view. @returns Scheduler. */
function createScheduler():AdvisoryValidator {return new AdvisoryValidator();}
/** Own memory-only oracle input, automatic checks and exact render-time evidence. @param controller Authority. @param online Availability. @returns Controls and current frame. */
export function useOracleParity(controller:Controller,online:boolean) {
  const [selection,setSelection]=useState<ParitySelection>(INITIAL),[outcome,setOutcome]=useState<Outcome|null>(null),[notice,setNotice]=useState('Upload a reference predicate to check bounded parity.'),[busy,setBusy]=useState(false);
  const scheduler=useMemo(createScheduler,[]),state=controller.current.current.document;
  const runtime=useRef<Runtime>({alive:true,generation:0,key:'',online,selection,active:null,inspection:null});
  const activation=parityActivation(runtime.current,online,selection.enabled),key=parityKey(controller.token,state,selection,online,activation);Object.assign(runtime.current,{key,online,selection});
  const context:Context={controller,runtime,scheduler,setSelection,setOutcome,setNotice,setBusy};
  useEffect(lifetime.bind(null,context),[]);
  useEffect(automatic.bind(null,context),[key,state.validation]);
  const valid=parityReady(state,selection,online),data=valid&&outcome?.key===key?outcome.data:null,verdict=data?parityVerdict(data):null;
  const frame:ParityFrame|null=selection.enabled&&state.module.predicates.some(isTarget.bind(null,selection.targetId))?{targetId:selection.targetId,scope:selection.scope,verdict:verdict??'neutral'}:null;
  const currentNotice=!valid?'Parity is neutral: disabled, offline, incomplete or missing predicate selections.':outcome&&outcome.key!==key?'Parity is neutral: content or options changed; current checks are pending.':notice;
  return {selection,change:change.bind(null,context),upload:upload.bind(null,context),inspect:inspectCurrent.bind(null,context),check:queue.bind(null,context,true),notice:currentNotice,busy,data,frame,ready:valid};
}
/** Dispose browser waits and invalidate every asynchronous file callback. @param context Owned state. @returns Cleanup. */
export function lifetime(context:Context):()=>void {
  /** Clear all owned lifetimes on document or authority unmount. @returns Nothing. */
  function dispose():void {const live=context.runtime.current;live.alive=false;live.generation++;live.active?.abort();live.inspection?.abort();context.scheduler.dispose();}
  return dispose;
}
/** Queue only current eligible content after advisory validation completes. @param context Owned state. @returns Nothing. */
function automatic(context:Context):void {
  const live=context.runtime.current,state=context.controller.current.current.document;
  if(!parityReady(state,live.selection,live.online)) {context.scheduler.clearPending();live.active?.abort();context.setOutcome(null);return;}
  if(parityAutomaticReady(state)) live.validatedContent=advisoryKey(state);
  if(parityAutomaticReady(state)||live.validatedContent===advisoryKey(state)) queue(context,false);else context.scheduler.clearPending();
}
/** Change options synchronously so callbacks cannot restore disabled or replaced evidence. @param context Owned state. @param next New options. @returns Nothing. */
function change(context:Context,next:ParitySelection):void {
  const live=context.runtime.current;live.selection=next;live.key=parityKey(context.controller.token,context.controller.current.current.document,next,live.online,parityActivation(live,live.online,next.enabled));
  context.setSelection(next);context.setOutcome(null);context.setNotice('Parity is neutral: options changed; current checks are pending.');context.scheduler.clearPending();
  if(!next.enabled) live.active?.abort();
}
/** Read one bounded UTF-8 file and preserve descriptors across ordinary document edits. @param context Owned state. @param file Local source or removal. @returns Completion. */
export async function upload(context:Context,file:File|null):Promise<void> {
  const live=context.runtime.current,generation=++live.generation;live.inspection?.abort();change(context,{...live.selection,oracle:null});if(!file) return;
  try {
    if(!file.name.toLowerCase().endsWith('.als')) throw new Error('Choose an .als oracle file.');
    if(file.size>32768) throw new Error('Oracle files must be at most 32 KiB.');
    const source=decodeModel(await file.arrayBuffer()),sourceHash=await digest(source);
    if(!live.alive||live.generation!==generation) return;
    const model:ModelFile={filename:file.name,source,sourceHash,predicate:'',predicates:[],inspection:''};change(context,{...live.selection,oracle:model});await inspect(context,model,generation);
  } catch(error) {if(live.alive&&live.generation===generation) context.setNotice(message(error));}
}
/** Retry parser inspection explicitly without retrying unchanged failures automatically. @param context Owned state. @returns Completion. */
async function inspectCurrent(context:Context):Promise<void> {const live=context.runtime.current;if(live.selection.oracle) await inspect(context,live.selection.oracle,live.generation);}
/** Populate choices from the parser while binding completion to the upload lifetime. @param context Owned state. @param model Exact uploaded file. @param generation Upload generation. @returns Completion. */
async function inspect(context:Context,model:ModelFile,generation:number):Promise<void> {
  const live=context.runtime.current,origin=context.controller.current.current.document,abort=new AbortController();live.inspection?.abort();live.inspection=abort;context.setNotice('Inspecting oracle predicates…');
  try {
    const data=await comparisonRequest(context.controller.token,origin,'comparison-model',{...comparisonBase(origin),source:model.source,sourceHash:model.sourceHash},abort.signal);
    if(!live.alive||abort.signal.aborted||live.generation!==generation||live.selection.oracle?.sourceHash!==model.sourceHash) return;
    if(data.sourceHash!==model.sourceHash||!validPredicates(data.predicates)) throw new Error('Malformed parser-derived oracle descriptors.');
    change(context,{...live.selection,oracle:{...model,predicates:data.predicates!,inspection:model.sourceHash}});context.setNotice('Select a parsed oracle predicate and a current predicate, then enable parity.');
  } catch(error) {if(live.alive&&!abort.signal.aborted&&live.generation===generation) context.setNotice(message(error));}
  finally {if(live.inspection===abort) live.inspection=null;}
}
/** Reject malformed parser choice lists before rendering labels. @param value Untrusted parser descriptors. @returns Whether well formed. */
function validPredicates(value:unknown):boolean {
  if(!Array.isArray(value)||value.length>256) return false;
  for(const item of value) {if(!item||typeof item.name!=='string'||!Array.isArray(item.parameters)) return false;for(const parameter of item.parameters) if(typeof parameter?.name!=='string'||!Array.isArray(parameter.columns)||!parameter.columns.every(isString)) return false;}
  return true;
}
/** Recognize a plain descriptor string. @param value Untrusted value. @returns Whether string. */
function isString(value:unknown):boolean {return typeof value==='string';}
/** Queue one frozen parity request with latest coalescing and explicit manual retries. @param context Owned state. @param manual Explicit Check. @returns Nothing. */
export function queue(context:Context,manual:boolean):void {
  const live=context.runtime.current,state=context.controller.current.current.document,selection=live.selection,key=live.key;
  if(!live.alive||!parityReady(state,selection,live.online)) return;
  /** Run a frozen independently validated candidate without saving. @param signal Scheduler lifetime. @returns Completion. */
  async function run(signal:AbortSignal):Promise<void> {
    if(!live.alive||live.key!==key||signal.aborted) return;
    const abort=new AbortController();live.active=abort;context.setBusy(true);context.setOutcome(null);context.setNotice('Checking four bounded truth categories…');
    try {
      const oracle=selection.oracle!,body={...comparisonBase(state),candidate:candidate(state),targetId:selection.targetId,oracle:{source:oracle.source,sourceHash:oracle.sourceHash,predicate:oracle.predicate},scope:selection.scope};
      const data=await comparisonRequest(context.controller.token,state,'oracle-parity',body,AbortSignal.any([signal,abort.signal])) as ParityData;
      if(!live.alive||live.key!==key||signal.aborted||abort.signal.aborted) return;
      if(!parityEvidence(data,selection)) throw new Error('Parity response identity mismatch.');
      context.setOutcome({key,data});context.setNotice(parityVerdict(data)?'Bounded parity check completed.':data.classification==='NO_INSTANCES'?'No admissible bounded instances; facts may be inconsistent or required domains empty.':'Parity inconclusive: no color established.');
    } catch(error) {if(live.alive&&live.key===key&&!signal.aborted&&!abort.signal.aborted) context.setNotice(message(error));}
    finally {if(live.active===abort) {live.active=null;if(live.alive) context.setBusy(false);}}
  }
  context.scheduler.request({key,run},manual);
}
/** Explain a neutral failure without suggesting equivalence. @param error Availability or input failure. @returns Notice. */
function message(error:unknown):string {return `${error instanceof Error?error.message:'Parity unavailable.'} No bounded verdict established.`;}

/** Match an existing predicate declaration for neutral frame placement. @param id Selected identity. @param predicate Current declaration. @returns Whether selected. */
function isTarget(id:string,predicate:{id:string}):boolean {return predicate.id===id;}

/** Separate activation and availability transitions from unchanged failure retries. @param live Owned runtime. @param online Server availability. @param enabled User opt-in. @returns Monotonic activation generation. */
export function parityActivation(live:Runtime,online:boolean,enabled:boolean):number {
  const availability=JSON.stringify([online,enabled]);if(live.availability!==availability) {live.availability=availability;live.activation=(live.activation??0)+1;}return live.activation??0;
}
