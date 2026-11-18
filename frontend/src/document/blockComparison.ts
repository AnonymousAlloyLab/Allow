import type {DocumentState} from './state';
import type {Candidate} from './types';
import {candidate} from './state';
import {contentSnapshot} from './gesture';
import {BASE,digest,request,serializeRequest} from './api';
export interface PredicateChoice {readonly name:string;readonly parameters:readonly {name:string;columns:readonly string[]}[]}
export interface ModelFile {readonly filename:string;readonly source:string;readonly sourceHash:string;readonly predicates:readonly PredicateChoice[];readonly predicate:string;readonly inspection:string}
export interface ComparisonSelection {readonly mode:'blocks'|'files';readonly leftId:string;readonly rightId:string;readonly scope:number;readonly left:ModelFile|null;readonly right:ModelFile|null}
export interface ComparisonCategory {readonly status:string;readonly left?:boolean;readonly right?:boolean;readonly evidenceHash?:string;readonly witness?:{readonly states:readonly {readonly atoms:readonly {id:string;memberships:readonly string[]}[];readonly relations:readonly {name:string;arity:number;tuples:readonly (readonly string[])[]}[]}[];readonly truncated:boolean;readonly fullInstanceHash:string};readonly assignment?:readonly {id:string;name:string;columns:readonly string[];tuples:readonly (readonly string[])[];truncated:boolean}[]}
export interface ComparisonCorrespondence {readonly leftPredicate:string;readonly rightPredicate:string;readonly parameters:readonly {leftName:string;rightName:string;columns:readonly string[];sharedId:string}[];readonly declarations:readonly {kind:string;name:string}[]}
export interface ComparisonData {readonly requestHash:string;readonly documentId:string;readonly draftId:string;readonly draftEpoch:number;readonly baseRevision:number;readonly artifactId:string;readonly policyVersion:string|number;readonly dependencyHash:string;readonly sourceHash?:string;readonly moduleHash?:string;readonly scope?:number;readonly bitwidth?:number;readonly maxseq?:number;readonly leftId?:string;readonly rightId?:string;readonly left?:{sourceHash:string;predicate:string};readonly right?:{sourceHash:string;predicate:string};readonly predicates?:readonly PredicateChoice[];readonly categories?:Readonly<Record<string,ComparisonCategory>>;readonly classification?:string;readonly correspondence?:ComparisonCorrespondence;readonly code?:string;readonly reason?:string;readonly message?:string}
/** Bind every comparison presentation to exact content, authority base and UI selection. @param state Current draft. @param selection Current controls. @returns Exact local identity. */
export function comparisonKey(state:DocumentState,selection:ComparisonSelection):string {return JSON.stringify([contentSnapshot(state),state.epoch,state.mode,state.accepted?.artifact.artifactId,state.accepted?.artifact.policyVersion,state.accepted?.artifact.dependencyHash,selection]);}
/** Capture the closed authority envelope without generating a saved revision. @param state Current model. @returns Base request. */
export function comparisonBase(state:DocumentState):{draftId:string;draftEpoch:number;baseRevision:number;artifactId:string} {
  if(!state.accepted||state.mode!=='BLOCK_SUPPORTED') throw new Error('Comparison requires a block-supported document; source draft is authoritative.');
  return {draftId:state.draftId,draftEpoch:state.epoch,baseRevision:state.baseRevision,artifactId:state.accepted.artifact.artifactId};
}
/** Verify echoed authority and exact request bytes before accepting evidence. @param data Returned envelope. @param state Frozen origin. @param hash Exact request hash. @returns Whether identity matches. */
export function comparisonIdentity(data:ComparisonData,state:DocumentState,hash:string):boolean {
  const accepted=state.accepted;
  return !!accepted&&data.requestHash===hash&&data.documentId===accepted.documentId&&data.draftId===state.draftId&&data.draftEpoch===state.epoch&&data.baseRevision===state.baseRevision&&data.artifactId===accepted.artifact.artifactId&&data.policyVersion===accepted.artifact.policyVersion&&data.dependencyHash===accepted.artifact.dependencyHash;
}
/** Strictly decode a bounded local source without touching browser persistence. @param bytes Raw local file. @returns Exact Unicode source. */
export function decodeModel(bytes:ArrayBuffer):string {
  if(bytes.byteLength>32768) throw new Error('Local Alloy files must be at most 32 KiB.');
  const source=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);
  if(!source.trim()) throw new Error('Choose a nonempty Alloy source file.');
  return source;
}
/** Send one bounded request with an independent client lifetime. @param token In-memory authority. @param state Frozen origin. @param route Operation. @param value Closed payload. @param signal Browser cancellation. @returns Bound response. */
export async function comparisonRequest(token:string,state:DocumentState,route:string,value:unknown,signal:AbortSignal):Promise<ComparisonData> {
  const body=serializeRequest(value),hash=await digest(body),response=await request<ComparisonData>(token,`${BASE}/${encodeURIComponent(state.accepted!.documentId)}/${route}`,body,AbortSignal.any([signal,AbortSignal.timeout(12000)]));
  if(response.status!=='OK') throw new Error(comparisonFailure(response.status,response.data));
  if(!comparisonIdentity(response.data,state,hash)) throw new Error('Comparison response identity mismatch.');
  return response.data;
}
/** Build exact live-node or uploaded-predicate comparison request. @param state Frozen draft. @param selection Frozen controls. @returns Route/payload. */
export function comparisonPayload(state:DocumentState,selection:ComparisonSelection):{route:string;body:unknown} {
  const base={...comparisonBase(state),scope:selection.scope};
  if(selection.mode==='blocks') {const value:Candidate=candidate(state);return {route:'compare',body:{...base,candidate:value,leftId:selection.leftId,rightId:selection.rightId}};}
  const {left,right}=selection;if(!left||!right||!left.predicate||!right.predicate) throw new Error('Choose and inspect both local files and select a predicate on each side.');
  if(left.inspection!==contentSnapshot(state)+state.epoch||right.inspection!==contentSnapshot(state)+state.epoch) throw new Error('Draft changed; inspect both local files again.');
  return {route:'compare-models',body:{...base,left:{source:left.source,sourceHash:left.sourceHash,predicate:left.predicate},right:{source:right.source,sourceHash:right.sourceHash,predicate:right.predicate}}};
}
/** Check arm/options echoes independently from transport success. @param data Returned evidence. @param selection Frozen controls. @returns Whether all arms match. */
export function comparisonArmsMatch(data:ComparisonData,selection:ComparisonSelection):boolean {
  if(data.scope!==selection.scope||data.bitwidth!==4||data.maxseq!==3||!data.categories||!data.sourceHash||!data.moduleHash||!validCategories(data.categories)) return false;
  if(selection.mode==='blocks') return data.leftId===selection.leftId&&data.rightId===selection.rightId;
  return data.left?.sourceHash===selection.left?.sourceHash&&data.right?.sourceHash===selection.right?.sourceHash&&data.left?.predicate===selection.left?.predicate&&data.right?.predicate===selection.right?.predicate;
}

/** Validate the four partition outcomes and independently reported SAT truth pairs before displaying them. @param categories Bounded outcome map. @returns Whether evidence shape is safe. */
export function validCategories(categories:Readonly<Record<string,ComparisonCategory>>):boolean {
  const expected:Readonly<Record<string,readonly boolean[]>>={both:[true,true],leftOnly:[true,false],rightOnly:[false,true],neither:[false,false]};
  for(const key of Object.keys(expected)) {const item=categories[key];if(!item) return false;if(item.status==='SAT'&&(item.left!==expected[key][0]||item.right!==expected[key][1]||!item.witness||!item.evidenceHash)) return false;}
  return true;
}
/** Derive honest bounded classification from outcomes rather than trusting a presentation label. @param data Current bound evidence. @returns Safe classification. */
export function comparisonClassification(data:ComparisonData):string {
  const categories=data.categories;if(!categories||!validCategories(categories)) return 'INCONCLUSIVE';
  if(categories.leftOnly.status==='SAT'||categories.rightOnly.status==='SAT') return 'DISTINGUISHED';
  if(Object.values(categories).length===4&&Object.values(categories).every(isUnsat)) return 'NO_INSTANCES';
  if(categories.leftOnly.status==='UNSAT'&&categories.rightOnly.status==='UNSAT') return 'AGREEMENT';
  return 'INCONCLUSIVE';
}
/** Recognize completed UNSAT only. @param category Outcome. @returns Whether unsatisfiable. */
function isUnsat(category:ComparisonCategory):boolean {return category.status==='UNSAT';}

/** Explain bounded public worker rejections without hiding their actionable context. @param status Envelope outcome. @param data Public diagnostic fields. @returns Safe plain-text failure. */
export function comparisonFailure(status:string,data:Pick<ComparisonData,'reason'|'message'|'code'>|null|undefined):string {
  const reason=data?.reason,known:Readonly<Record<string,string>>={'background mismatch':'The models have different background declarations or facts.','background declaration mismatch':'The models have different background declarations or facts.','parameter arity mismatch':'The selected predicates have different numbers of parameters.','parameter schema mismatch':'The selected predicate parameters have different relation schemas.'};
  const detail=reason?(known[reason]??reason.slice(0,240)):data?.message??data?.code??'Comparison unavailable; no agreement established.';
  return `${status}: ${detail}`;
}
