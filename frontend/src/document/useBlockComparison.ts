import {useEffect,useRef,useState} from 'react';
import type {MutableRefObject} from 'react';
import type {Controller} from './controller';
import {contentSnapshot} from './gesture';
import {digest} from './api';
import {comparisonKey,comparisonBase,comparisonRequest,comparisonPayload,comparisonArmsMatch,decodeModel,type ComparisonSelection,type ComparisonData,type ModelFile} from './blockComparison';
const INITIAL:ComparisonSelection={mode:'blocks',leftId:'',rightId:'',scope:3,left:null,right:null};
interface Outcome {readonly key:string;readonly data:ComparisonData}
interface UIContext {readonly controller:Controller;readonly live:MutableRefObject<ComparisonSelection>;readonly active:MutableRefObject<AbortController|null>;readonly requestKey:MutableRefObject<string>;readonly current:MutableRefObject<string>;readonly uploads:MutableRefObject<{left:number;right:number}>;readonly setSelection:(value:ComparisonSelection)=>void;readonly setNotice:(value:string)=>void;readonly setOutcome:(value:Outcome|null)=>void;readonly setBusy:(value:boolean)=>void}
/** Own ephemeral upload and comparison lifetimes independently of document mutations. @param controller Current authority/controller. @returns UI state and explicit actions. */
export function useBlockComparison(controller:Controller) {
  const [selection,setSelection]=useState<ComparisonSelection>(INITIAL),[notice,setNotice]=useState('Choose two formula blocks or local Alloy models.'),[outcome,setOutcome]=useState<Outcome|null>(null),[busy,setBusy]=useState(false);
  const requestKey=useRef(''),live=useRef(selection),active=useRef<AbortController|null>(null),uploads=useRef({left:0,right:0});live.current=selection;
  const state=controller.current.current.document,key=comparisonKey(state,selection),current=useRef(key);current.current=key;
  const ui:UIContext={controller,live,active,requestKey,current,uploads,setSelection,setNotice,setOutcome,setBusy};
  /** Fence changed content/options without aborting a newly started matching request. @returns Nothing. */
  function fence():void {if(requestKey.current!==key) {active.current?.abort();active.current=null;setBusy(false);}if(outcome&&outcome.key!==key) {setOutcome(null);setNotice('Model changed. Run comparison again for the current draft and options.');}}
  /** Clear deleted live arm IDs while retaining surviving selections for a fresh run. @returns Nothing. */
  function retainArms():void {const ids=new Set(state.module.nodes.map(nodeIdentity));if(selection.leftId&&!ids.has(selection.leftId)||selection.rightId&&!ids.has(selection.rightId)) changeComparisonSelection(ui,{...selection,leftId:ids.has(selection.leftId)?selection.leftId:'',rightId:ids.has(selection.rightId)?selection.rightId:''});}
  useEffect(comparisonLifetime.bind(null,ui),[]);useEffect(fence,[key]);useEffect(retainArms,[contentSnapshot(state)]);
  return {selection,change:changeComparisonSelection.bind(null,ui),upload:upload.bind(null,ui),inspect:inspect.bind(null,ui),compare:compare.bind(null,ui),notice,busy:busy&&active.current!==null,data:outcome?.key===key?outcome.data:null};
}
/** Cancel browser waiting when this authority unmounts; server cleanup retains its deadline. @param ui UI context. @returns Cleanup. */
function comparisonLifetime(ui:UIContext):()=>void {
  /** Suppress uploads and delayed evidence after unmount. @returns Nothing. */
  function cancel():void {ui.active.current?.abort();ui.active.current=null;ui.uploads.current.left++;ui.uploads.current.right++;}
  return cancel;
}
/** Change UI-only selection and synchronously suppress older evidence. @param ui Context. @param next New controls. @returns Nothing. */
export function changeComparisonSelection(ui:UIContext,next:ComparisonSelection):void {ui.active.current?.abort();ui.active.current=null;ui.live.current=next;ui.current.current=comparisonKey(ui.controller.current.current.document,next);ui.setSelection(next);ui.setBusy(false);ui.setOutcome(null);ui.setNotice('Selection changed. Run comparison again for the current draft and options.');}
/** Load, hash and inspect one local bounded file without persistence. @param ui Context. @param side Arm identity. @param file Local file. @returns Completion. */
async function upload(ui:UIContext,side:'left'|'right',file:File|null):Promise<void> {
  const generation=++ui.uploads.current[side],origin=contentSnapshot(ui.controller.current.current.document);changeComparisonSelection(ui,{...ui.live.current,[side]:null});if(!file) return;
  try {
    if(file.size>32768) throw new Error('Local Alloy files must be at most 32 KiB.');
    const source=decodeModel(await file.arrayBuffer()),sourceHash=await digest(source);
    if(generation!==ui.uploads.current[side]||origin!==contentSnapshot(ui.controller.current.current.document)) return;
    const model:ModelFile={filename:file.name,source,sourceHash,predicates:[],predicate:'',inspection:''};
    changeComparisonSelection(ui,{...ui.live.current,[side]:model});await inspect(ui,side,model);
  } catch(error) {if(generation===ui.uploads.current[side]) ui.setNotice(message(error));}
}
/** Parse hash-bound source and populate only server-derived predicate choices. @param ui Context. @param side Arm. @param model Memory-only file. @returns Completion. */
async function inspect(ui:UIContext,side:'left'|'right',model:ModelFile):Promise<void> {
  const origin=ui.controller.current.current.document,abort=new AbortController(),originKey=ui.current.current;ui.active.current?.abort();ui.active.current=abort;ui.requestKey.current=originKey;ui.setBusy(true);ui.setNotice(`Inspecting ${side} model…`);
  try {
    const data=await comparisonRequest(ui.controller.token,origin,'comparison-model',{...comparisonBase(origin),source:model.source,sourceHash:model.sourceHash},abort.signal);
    if(abort.signal.aborted||originKey!==comparisonKey(ui.controller.current.current.document,ui.live.current)||data.sourceHash!==model.sourceHash) return;
    if(!Array.isArray(data.predicates)) throw new Error('Missing parser-derived predicate descriptors.');
    const updated={...model,predicates:data.predicates,predicate:'',inspection:contentSnapshot(origin)+origin.epoch};
    changeComparisonSelection(ui,{...ui.live.current,[side]:updated});ui.setNotice('Model inspected. Select a predicate to compare.');
  } catch(error) {if(!abort.signal.aborted&&originKey===ui.current.current) ui.setNotice(message(error));}
  finally {if(ui.active.current===abort) {ui.active.current=null;ui.setBusy(false);}}
}
/** Run explicit comparison and publish only exact current evidence. @param ui UI context. @returns Completion. */
async function compare(ui:UIContext):Promise<void> {
  const origin=ui.controller.current.current.document,controls=ui.live.current,originKey=comparisonKey(origin,controls),abort=new AbortController();ui.active.current?.abort();ui.active.current=abort;ui.requestKey.current=originKey;ui.setBusy(true);ui.setOutcome(null);ui.setNotice('Comparing four bounded truth categories…');
  try {
    const payload=comparisonPayload(origin,controls),data=await comparisonRequest(ui.controller.token,origin,payload.route,payload.body,abort.signal);
    if(abort.signal.aborted||originKey!==comparisonKey(ui.controller.current.current.document,ui.live.current)) return;
    if(!comparisonArmsMatch(data,controls)) throw new Error('Comparison arm/options identity mismatch.');
    ui.setOutcome({key:originKey,data});ui.setNotice('Comparison completed for this exact draft and selection.');
  } catch(error) {if(!abort.signal.aborted&&originKey===ui.current.current) ui.setNotice(message(error));}
  finally {if(ui.active.current===abort) {ui.active.current=null;ui.setBusy(false);}}
}
/** Report public failures without claiming equivalence. @param error Failure. @returns User-facing notice. */
function message(error:unknown):string {return error instanceof Error?error.message:'Comparison unavailable; no agreement established.';}

/** Read an owned expression identity. @param node Current node. @returns Identity. */
function nodeIdentity(node:{id:string}):string {return node.id;}
