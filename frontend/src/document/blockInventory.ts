import {useEffect,useRef,useState} from 'react';
import type {DraftModule,Expression,Id,Check,SlotObligation} from './types';
import type {Fit,Gesture} from './gesture';
import type {SavedBlock} from './blockLibrary';
export interface BlockChoice {readonly key:string;readonly label:string;readonly tag:Expression['tag'];readonly target:Id;readonly entry?:SavedBlock;readonly fit:Fit}
export interface InventoryInput {readonly module:DraftModule;readonly checked:Check;readonly selected:Id|null;readonly snapshot:string;readonly name:string;readonly entries:readonly SavedBlock[];readonly obligations?:readonly SlotObligation[];readonly preview?:(gesture:Gesture,target:Id,copy:boolean)=>Fit}
export const OPERATORS:readonly Expression['tag'][]=['not','some_test','no_test','one_test','lone_test','and','or','implies','iff','equal','subset','transpose','union','intersection','difference','join','product'];
/** Append a reference candidate independently of other reference constructors. @param output Inventory. @param tag Applicable operator. @param id Identity. @param label Display name. @returns Nothing. */
function reference(output:BlockChoice[],tag:Expression['tag'],id:Id,label:string):void {output.push({key:`${tag}:${id}`,tag,target:id,label,fit:{kind:'unavailable',message:'Checking destination…'}});}
/** Enumerate the current finite inventory, including applicable reference/operator pairs. @param input Current context. @returns Unchecked choices. */
export function inventoryChoices(input:InventoryInput):BlockChoice[] {
  const result:BlockChoice[]=[];
  for(const tag of OPERATORS) reference(result,tag,'',tag);
  for(const item of input.module.signatures) {reference(result,'signature_ref',item.id,`Signature · ${item.name}`);reference(result,'all_quant',item.id,`For every · ${item.name}`);reference(result,'some_quant',item.id,`For some · ${item.name}`);}
  for(const item of input.module.fields) reference(result,'field_ref',item.id,`Field · ${item.name}`);
  for(const item of input.module.predicates) reference(result,'predicate_call',item.id,`Call · ${item.name}`);
  for(const item of input.checked.scopes.get(input.selected??'')??[]) reference(result,'variable_ref',item.id,`Variable · ${item.name}`);
  for(const entry of input.entries) result.push({key:`saved:${entry.id}`,label:entry.name,tag:entry.nodes[0].tag as Expression['tag'],target:'',entry,fit:{kind:'unavailable',message:'Checking destination…'}});
  return result;
}
/** Evaluate one candidate through the same preparation guard as click/drop. @param input Context. @param choice Candidate. @returns Honest status. */
export function evaluateChoice(input:InventoryInput,choice:BlockChoice):Fit {
  if(!input.selected) return {kind:'unresolved',message:'Select a destination before inserting.'};
  if(input.checked.resourceFailure) return {kind:'unavailable',message:'Destination analysis unavailable.'};
  const base={nonce:'inventory',snapshot:input.snapshot};
  const gesture:Gesture=choice.entry?{...base,kind:'saved',entry:choice.entry}:{...base,kind:'palette',tag:choice.tag,target:choice.target,name:input.name};
  return input.preview?.(gesture,input.selected,true)??{kind:'unavailable',message:'Preview unavailable.'};
}
/** Build one bounded inventory asynchronously; old generations cannot publish after a context change. @param input Exact current context. @returns Current choices and progress. */
export function useBlockInventory(input:InventoryInput):{choices:readonly BlockChoice[];pending:boolean} {
  const key=JSON.stringify([input.snapshot,input.selected,input.name,input.entries,input.obligations]);
  const latest=useRef(input);latest.current=input;
  const [result,setResult]=useState<{key:string;choices:readonly BlockChoice[];pending:boolean}>({key:'',choices:[],pending:true});
  /** Yield after each exact preparation instead of blocking render with 192 full analyses. @returns Timer cleanup. */
  function schedule():()=>void {
    const context=latest.current,choices=inventoryChoices(context);let canceled=false,index=0,timer:ReturnType<typeof setTimeout>;
    /** Advance a single bounded candidate and publish small incremental batches. @returns Nothing. */
    function step():void {
      if(canceled) return;
      if(index<choices.length&&index<192) {const choice=choices[index];choices[index]={...choice,fit:evaluateChoice(context,choice)};index++;}
      const pending=index<Math.min(192,choices.length);
      if(!pending) for(let rest=index;rest<choices.length;rest++) choices[rest]={...choices[rest],fit:{kind:'unavailable',message:'Preview budget reached; explicit insertion rechecks the guard.'}};
      if(index%8===0||!pending) setResult({key,choices:[...choices],pending});
      if(pending) timer=setTimeout(step,0);
    }
    timer=setTimeout(step,0);
    /** Cancel remaining work for the old exact context. @returns Nothing. */
    function cancel():void {canceled=true;clearTimeout(timer);}
    return cancel;
  }
  useEffect(schedule,[key]);
  return result.key===key?result:{choices:inventoryChoices(input),pending:true};
}
