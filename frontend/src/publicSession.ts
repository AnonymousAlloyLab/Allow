export interface PublicSession {readonly token:string;readonly expiresAt:string;readonly lifetimeSeconds:number}
export const EXPIRED_EVENT='allow-session-expired';
const STORAGE_KEY='allow.public.session';
/** Send the expired signal for an authenticated request without exposing its token. @param response Server response. @param token Request capability. @returns Nothing. */
export function signalExpired(response:Response,token:string):void {if(response.status===401) window.dispatchEvent(new CustomEvent(EXPIRED_EVENT,{detail:token}));}
/** Read a tab-scoped capability if storage is available. @returns Token or empty value. */
export function readToken():string {try {return sessionStorage.getItem(STORAGE_KEY)??'';} catch {return '';}}
/** Store or remove only the tab-scoped capability. @param token Token or empty value. @returns Whether storage succeeded. */
export function writeToken(token:string):boolean {try {if(token) sessionStorage.setItem(STORAGE_KEY,token);else sessionStorage.removeItem(STORAGE_KEY);return true;} catch {return false;}}
/** Validate the closed session data returned by the server. @param data Unknown response. @param token Existing or newly issued token. @returns Checked session. @throws Error on malformed response. */
function checked(data:unknown,token:string):PublicSession {
  if(!data||typeof data!=='object'||!('expiresAt' in data)||typeof data.expiresAt!=='string'||!Number.isFinite(Date.parse(data.expiresAt))||!('lifetimeSeconds' in data)||typeof data.lifetimeSeconds!=='number'||!Number.isFinite(data.lifetimeSeconds)||data.lifetimeSeconds<=0||data.lifetimeSeconds>1800||token.length<32) throw new Error('Invalid workspace response.');
  return {token,expiresAt:data.expiresAt,lifetimeSeconds:data.lifetimeSeconds};
}
/** Request an explicit new temporary workspace. @returns Session or a capacity/unavailability error. @throws Error when enrollment fails. */
export async function createSession():Promise<PublicSession> {
  const response=await fetch('/api/public/workspaces',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',cache:'no-store',credentials:'omit'});
  if(response.status===429) throw new Error('All temporary workspaces are busy. Please try again in about a minute.');
  if(!response.ok) throw new Error('Temporary workspaces are unavailable. Please try again.');
  const data:unknown=await response.json();
  if(!data||typeof data!=='object'||!('token' in data)||typeof data.token!=='string') throw new Error('Invalid workspace response.');
  return checked(data,data.token);
}
/** Resume only a server-confirmed capability. @param token Tab capability. @returns Session or null when expired. @throws Error for temporary failures. */
export async function resumeSession(token:string):Promise<PublicSession|null> {
  const response=await fetch('/api/public/workspaces/current',{headers:{Authorization:`Bearer ${token}`},cache:'no-store',credentials:'omit'});
  if(response.status===401) return null;
  if(!response.ok) throw new Error('Workspace status is unavailable. Retry without losing your session.');
  return checked(await response.json(),token);
}
/** Explicitly request session retirement. @param token Tab capability. @returns Completion. @throws Error on unavailable service. */
export async function endSession(token:string):Promise<void> {
  const response=await fetch('/api/public/workspaces/current',{method:'DELETE',headers:{Authorization:`Bearer ${token}`},cache:'no-store',credentials:'omit'});
  if(response.status!==204&&response.status!==401) throw new Error('Could not end the workspace. Try again.');
}
