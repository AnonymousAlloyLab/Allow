import {signalExpired} from '../../publicSession';
import {serializeRequest} from '../api';
const BASE='/api/ai/v1';
/** Read bounded UTF8 response bytes before JSON allocation. @param response HTTP response. @returns Strict text. @throws Error Invalid or oversized response. */
async function read(response:Response):Promise<string> {
  if(!response.body) throw new Error('Assistant unavailable.');
  const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let bytes=0,result='';
  try {while(true) {const chunk=await reader.read();if(chunk.done) break;bytes+=chunk.value.length;if(bytes>1048576) throw new Error('Assistant unavailable.');result+=decoder.decode(chunk.value,{stream:true});}return result+decoder.decode();}
  finally {await reader.cancel().catch(ignore);reader.releaseLock();}
}
/** Ignore stream cleanup failure after a closed response error. @returns Nothing. */
function ignore():void {}
/** Send one bounded private AI request with no browser persistence. @param token Current authority. @param path Fixed relative route. @param body Closed JSON or omitted GET. @param signal Request cancellation. @returns Envelope data. @throws Error Closed availability error. */
export async function call(token:string,path:string,body?:unknown,signal?:AbortSignal):Promise<unknown> {
  const controller=new AbortController(),timer=setTimeout(controller.abort.bind(controller),15000);
  /** Forward the owning panel's cancellation. @returns Nothing. */
  function abort():void {controller.abort();}
  if(signal?.aborted) abort();else signal?.addEventListener('abort',abort,{once:true});
  try {
    const response=await fetch(BASE+path,{method:body===undefined?'GET':'POST',body:body===undefined?undefined:serializeRequest(body),signal:controller.signal,cache:'no-store',credentials:'omit',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'}});
    signalExpired(response,token);
    if(response.status===403&&path==='/config') return {mode:'OFF',model:'',termsVersion:''};
    let value:unknown;try {value=JSON.parse(await read(response));} catch {throw new Error('Assistant unavailable.');}
    if(!value||typeof value!=='object'||!('protocol' in value)||value.protocol!==1||!('status' in value)||!('data' in value)) throw new Error('Assistant unavailable.');
    if(!response.ok) throw new Error(typeof value.status==='string'&&/^[A-Z_]{1,64}$/.test(value.status)?value.status:'Assistant unavailable.');
    return value.data;
  } finally {clearTimeout(timer);signal?.removeEventListener('abort',abort);}
}
/** Build a route from an opaque server handle only. @param id Server job handle. @param suffix Closed action. @returns Encoded route. */
export function route(id:string,suffix='' ):string {return `/jobs/${encodeURIComponent(id)}${suffix}`;}
