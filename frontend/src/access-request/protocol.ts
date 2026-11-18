export interface CaptchaMessage {kind:'token'|'expired'|'error';nonce:string;token?:string}
/** Generate a fresh unguessable iframe conversation identifier. @returns Hex nonce. */
export function newNonce():string {return Array.from(crypto.getRandomValues(new Uint8Array(32)),hex).join('');}
/** Encode one random byte. @param byte Random byte. @returns Two hex characters. */
function hex(byte:number):string {return byte.toString(16).padStart(2,'0');}
/** Accept only bounded messages from the current opaque child. @param event Message. @param source Child window. @param nonce Current nonce. @returns Checked payload or null. */
export function captchaMessage(event:MessageEvent,source:Window|null,nonce:string):CaptchaMessage|null {
  if(!source||event.source!==source||event.origin!=='null') return null;
  const data=event.data;if(!data||typeof data!=='object'||Array.isArray(data)||data.nonce!==nonce) return null;
  if(!['token','expired','error'].includes(data.kind)) return null;
  const keys=data.kind==='token'?['kind','nonce','token']:['kind','nonce'];
  if(Object.keys(data).length!==keys.length||Object.keys(data).some(unexpected)) return null;
  if(data.kind==='token'&&(typeof data.token!=='string'||data.token.length<1||data.token.length>4096)) return null;
  return data as CaptchaMessage;
  /** Reject keys outside this message variant. @param key Candidate key. @returns Whether unknown. */
  function unexpected(key:string):boolean {return !keys.includes(key);}
}
/** Exchange closed JSON without cookies or workspace authority. @param path Exact endpoint. @param body Optional payload. @returns Response object. */
export async function accessApi(path:string,body?:unknown):Promise<Record<string,unknown>> {
  const response=await fetch('/api/ai-access/'+path,{method:body?'POST':'GET',credentials:'omit',cache:'no-store',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});
  if(!response.ok) throw new Error(failureMessage(path,response.status));
  const data:unknown=await response.json();if(!data||typeof data!=='object'||Array.isArray(data)) throw new Error('Invalid service response.');
  return data as Record<string,unknown>;
}
/** Explain fixed failures without reflecting provider or applicant data. @param path Operation. @param status HTTP status. @returns Safe message. */
function failureMessage(path:string,status:number):string {
  if(status===429)return 'Too many requests. Please try again later.';
  if(status===400)return path==='verify'?'The code is invalid or expired. Check it or start over.':'Check your request details and try again.';
  return 'The request service is unavailable. Please try again later.';
}
