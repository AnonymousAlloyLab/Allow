import {signalExpired} from '../publicSession';
import type {Envelope,ListData,Accepted,CommitData,Validation,Pending,Candidate,MutationData} from './types';
export const BASE='/api/v1/documents';
/** Serialize a bounded exact mutation or validation body. @param value Closed request value. @returns Original UTF8 JSON body. @throws Error on request size excess. */
export function serializeRequest(value:unknown):string {
  const body=JSON.stringify(value);
  if(new TextEncoder().encode(body).length>262144) throw new Error('Document request exceeds262144 UTF8 bytes.');
  return body;
}
/** Reject invalid Unicode before UTF8 replacement encoding. @param source Exact input. @returns Whether Unicode scalar encoding is valid. */
export function validUnicode(source:string):boolean {
  for(let i=0;i<source.length;i++) {
    const unit=source.charCodeAt(i);
    if(unit>=0xd800&&unit<=0xdbff) {const next=source.charCodeAt(++i);if(!(next>=0xdc00&&next<=0xdfff)) return false;}
    else if(unit>=0xdc00&&unit<=0xdfff) return false;
  }
  return true;
}
/** Hash exact strict UTF8 bytes. @param source Exact text. @returns SHA256. @throws Error for invalid Unicode. */
export async function digest(source:string):Promise<string> {
  if(!validUnicode(source)) throw new Error('Unpaired UTF16 surrogate.');
  const value=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(source)),parts:string[]=[];
  for(const byte of new Uint8Array(value)) parts.push(byte.toString(16).padStart(2,'0'));
  return parts.join('');
}
/** Send a closed same-origin authenticated request. @param token Fresh launch authority. @param path Endpoint. @param body Exact retained body. @param signal Optional bounded session cancellation. @returns Protocol envelope. @throws Error for unavailable/invalid transport. */
export async function request<T>(token:string,path:string,body?:string,signal?:AbortSignal):Promise<Envelope<T>> {
  const response=await fetch(path,{method:body===undefined?'GET':'POST',body,signal,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'}});
  signalExpired(response,token);
  const envelope:unknown=await response.json();
  if(!envelope||typeof envelope!=='object'||!('protocol' in envelope)||envelope.protocol!==1||!('status' in envelope)||!('data' in envelope)) throw new Error(`Unavailable document protocol (${response.status}); retry exact pending request.`);
  return envelope as Envelope<T>;
}
/** Read authorized document summaries. @param token Authority. @returns Summary envelope. */
export function listDocuments(token:string):Promise<Envelope<ListData>> {return request(token,BASE);}
/** Create an empty accepted document. @param token Authority. @param title Display title. @param key Stable request key. @returns Creation receipt. */
export function createDocument(token:string,title:string,key:string):Promise<Envelope<CommitData>> {return request(token,BASE,JSON.stringify({idempotencyKey:key,title}));}
/** Fetch immutable authorized artifact/head. @param token Authority. @param documentId Owned document. @param revision Optional historical target. @returns Read envelope. */
export function readDocument(token:string,documentId:string,revision?:number):Promise<Envelope<Accepted>> {
  const query=revision===undefined?'':`?revision=${revision}`;
  return request(token,`${BASE}/${encodeURIComponent(documentId)}${query}`);
}
/** Persist exact request bytes in session state before sending. @param documentId Document. @param candidate Complete candidate. @param revision Expected head. @param draftId Draft. @param epoch Origin epoch. @returns Pending exact request. */
export function prepareCommit(documentId:string,candidate:Candidate,revision:number,draftId:string,epoch:number):Pending {
  const key=crypto.randomUUID();
  return {route:`${BASE}/${encodeURIComponent(documentId)}/commit`,method:'POST',key,body:serializeRequest({idempotencyKey:key,expectedRevision:revision,candidate}),draftId,epoch};
}
/** Prepare append-only historical copy. @param documentId Document. @param revision Current head. @param targetRevision Selected target. @param direction Explicit navigation direction. @param draftId Draft. @param epoch Origin epoch. @returns Exact request. */
export function prepareHistory(documentId:string,revision:number,targetRevision:number,direction:'UNDO'|'REDO',draftId:string,epoch:number):Pending {
  const key=crypto.randomUUID(),body=serializeRequest({idempotencyKey:key,expectedRevision:revision,targetRevision,direction});
  return {route:`${BASE}/${encodeURIComponent(documentId)}/history-copy`,method:'POST',key,body,draftId,epoch};
}
/** Retry the exact original serialized request. @param token Current authority. @param pending Retained request. @returns Original or new durable outcome. */
export function sendPending(token:string,pending:Pending):Promise<Envelope<MutationData>> {return request(token,pending.route,pending.body);}
/** Send advisory validation using exact serialized bytes. @param token Authority. @param documentId Document. @param body Frozen validation request. @param signal Optional session cancellation. @returns Advisory response. */
export function validateDraft(token:string,documentId:string,body:string,signal?:AbortSignal):Promise<Envelope<Validation>> {return request(token,`${BASE}/${encodeURIComponent(documentId)}/validate`,body,signal);}
