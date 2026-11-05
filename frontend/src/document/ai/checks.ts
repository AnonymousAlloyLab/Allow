import type {Config,Job,Proposal,Receipt} from './types';
/** Require a closed plain JSON object. @param value Unknown JSON. @param keys Exact field names. @returns Checked object. @throws Error Invalid shape. */
export function object(value:unknown,keys:readonly string[]):Record<string,unknown> {
  if(!value||typeof value!=='object'||Array.isArray(value)) throw new Error('Invalid assistant response.');
  const item=value as Record<string,unknown>;
  if(Object.keys(item).some(unknownKey)||keys.some(missingKey)) throw new Error('Invalid assistant response.');
  /** Check unexpected fields. @param key Field name. @returns Whether forbidden. */
  function unknownKey(key:string):boolean {return !keys.includes(key);}
  /** Check required fields. @param key Field name. @returns Whether absent. */
  function missingKey(key:string):boolean {return !(key in item);}
  return item;
}
/** Require bounded text. @param value Unknown JSON. @param maximum UTF8 ceiling. @returns Checked text. @throws Error Invalid text. */
export function text(value:unknown,maximum=262144):string {if(typeof value!=='string'||new TextEncoder().encode(value).length>maximum) throw new Error('Invalid assistant response.');return value;}
/** Require a server timestamp. @param value Unknown JSON. @returns ISO-compatible timestamp. @throws Error Invalid timestamp. */
function timestamp(value:unknown):string {const result=typeof value==='number'&&Number.isFinite(value)?new Date(value).toISOString():text(value,64);if(!Number.isFinite(Date.parse(result))) throw new Error('Invalid assistant expiry.');return result;}
/** Check nonsecret configured mode. @param value Unknown JSON. @returns Config. @throws Error Invalid shape. */
export function config(value:unknown):Config {
  if(!value||typeof value!=='object') throw new Error('Invalid assistant configuration.');
  const item=value as Record<string,unknown>,mode=item.mode;
  if(mode!=='OFF'&&mode!=='FIXTURE'&&mode!=='REMOTE_ASSISTED') throw new Error('Invalid assistant configuration.');
  return {mode,model:typeof item.model==='string'?text(item.model,128):'',termsVersion:typeof item.termsVersion==='string'?text(item.termsVersion,128):''};
}
/** Check a deterministic proposal envelope. @param value Unknown JSON. @returns Proposal. @throws Error Invalid shape. */
function proposal(value:unknown):Proposal {
  const item=object(value,['source','explanation','projection','sourceHash','proposalHash']);
  return {source:text(item.source,32768),explanation:text(item.explanation,32768),projection:text(item.projection,64),sourceHash:text(item.sourceHash,128),proposalHash:text(item.proposalHash,128)};
}
/** Check one closed bounded server job. @param value Unknown JSON. @returns Job. @throws Error Invalid shape. */
export function job(value:unknown):Job {
  const item=object(value,['id','status','binding','expiresAt','attempt','beforeSource','payload','payloadHash','model','termsVersion','code','proposal']);
  if(!Number.isSafeInteger(item.attempt)||(item.attempt as number)<0||(item.attempt as number)>2) throw new Error('Invalid assistant attempt.');
  return {id:text(item.id,128),status:text(item.status,64),binding:text(item.binding,128),expiresAt:timestamp(item.expiresAt),attempt:item.attempt as number,beforeSource:item.beforeSource===null?null:text(item.beforeSource,32768),payload:item.payload===null?null:text(item.payload),payloadHash:item.payloadHash===null?null:text(item.payloadHash,128),model:text(item.model,128),termsVersion:text(item.termsVersion,128),code:item.code===null?null:text(item.code,128),proposal:item.proposal===null?null:proposal(item.proposal)};
}
/** Check one exact short-lived local apply receipt. @param value Unknown JSON. @returns Receipt. @throws Error Invalid shape. */
export function receipt(value:unknown):Receipt {
  const item=object(value,['receiptId','jobId','binding','proposalHash','source','sourceHash','expiresAt']);
  return {receiptId:text(item.receiptId,128),jobId:text(item.jobId,128),binding:text(item.binding,128),proposalHash:text(item.proposalHash,128),source:text(item.source,32768),sourceHash:text(item.sourceHash,128),expiresAt:timestamp(item.expiresAt)};
}
