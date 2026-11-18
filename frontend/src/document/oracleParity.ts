import {validParityCategories,validParityPayload} from './parityValidation';
import type {DocumentState} from './state';
import {candidate} from './state';
import {comparisonKey,type ModelFile,type ComparisonData} from './blockComparison';
export interface ParitySelection {readonly enabled:boolean;readonly targetId:string;readonly scope:number;readonly oracle:ModelFile|null}
export interface ParityData extends ComparisonData {readonly targetId?:string;readonly oracle?:{sourceHash:string;predicate:string}}
export interface ParityFrame {readonly targetId:string;readonly verdict:'match'|'difference'|'neutral';readonly scope:number}
/** Bind parity to the full draft, options and availability at render time. @param token Authority. @param state Draft. @param selection Options. @param online Availability. @param activation Enable/availability generation. @returns Exact identity. */
export function parityKey(token:string,state:DocumentState,selection:ParitySelection,online:boolean,activation=0):string {return JSON.stringify([token,online,activation,comparisonKey(state,{mode:'blocks',leftId:selection.targetId,rightId:'',scope:selection.scope,left:selection.oracle,right:null}),selection.enabled]);}
/** Require a complete supported module and an actual predicate declaration. @param state Draft. @param selection Options. @param online Availability. @returns Whether checks are permitted. */
export function parityReady(state:DocumentState,selection:ParitySelection,online:boolean):boolean {
  if(!online||!selection.enabled||!state.accepted||state.mode!=='BLOCK_SUPPORTED'||!selection.oracle?.predicate||!state.module.predicates.some(matchesTarget.bind(null,selection.targetId))) return false;
  try {candidate(state);return true;} catch {return false;}
}
/** Match only a selected declaration identity. @param id Target. @param declaration Predicate. @returns Match. */
function matchesTarget(id:string,declaration:{id:string}):boolean {return declaration.id===id;}
/** Require four finished categories and replayed SAT truth pairs before granting any color. @param data Evidence. @returns Bounded verdict or neutral. */
export function parityVerdict(data:Pick<ParityData,'categories'>):'match'|'difference'|null {
  const categories=data.categories;if(!categories||!validParityCategories(categories)) return null;
  if(categories.leftOnly.status==='SAT'||categories.rightOnly.status==='SAT') return 'difference';
  return categories.both.status==='SAT'||categories.neither.status==='SAT'?'match':null;
}
/** Check target, oracle, scope and shared correspondence independently of transport success. @param data Evidence. @param selection Frozen options. @returns Whether evidence belongs to this check. */
export function parityEvidence(data:ParityData,selection:ParitySelection):boolean {
  const oracle=selection.oracle;
  return validParityPayload(data)&&!!oracle&&data.targetId===selection.targetId&&data.oracle?.sourceHash===oracle.sourceHash&&data.oracle?.predicate===oracle.predicate&&data.right?.sourceHash===oracle.sourceHash&&data.right?.predicate===oracle.predicate&&data.scope===selection.scope&&data.bitwidth===4&&data.maxseq===3&&!!data.sourceHash&&!!data.moduleHash&&!!data.correspondence&&data.correspondence.rightPredicate===oracle.predicate&&!!data.left?.sourceHash&&data.correspondence.leftPredicate===data.left?.predicate;
}
/** Wait for successful current advisory validation before automatically sharing costly capacity. @param state Draft. @returns Whether automatic checking can start. */
export function parityAutomaticReady(state:DocumentState):boolean {return !state.dirty||!!state.validation&&state.validation.draftId===state.draftId&&state.validation.draftEpoch===state.epoch&&state.validation.baseRevision===state.baseRevision&&!state.pending;}
