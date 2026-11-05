import {useEffect,useRef,useState} from 'react';
import {AllowApp} from './AllowApp';
import {createSession,resumeSession,endSession,readToken,writeToken,EXPIRED_EVENT,type PublicSession} from './publicSession';
interface Status {readonly phase:'checking'|'ready'|'active'|'expired'|'unavailable';readonly session:PublicSession|null;readonly message:string;readonly generation:number}
/** Render explicit anonymous enrollment and preserve an expired editor for export. @returns Public workspace. */
export function PublicApp() {
  const [status,setStatus]=useState<Status>({phase:'checking',session:null,message:'Checking workspace…',generation:0}),current=useRef(status),busy=useRef(false);
  current.current=status;
  /** Publish one state while keeping event callbacks current. @param next New session state. @returns Nothing. */
  function update(next:Status):void {current.current=next;setStatus(next);}
  /** Retire only the matching active capability. @param token Prior session token. @returns Nothing. */
  function expire(token:string):void {if(current.current.session?.token!==token) return;writeToken('');update({...current.current,session:{...current.current.session,token:''},phase:'expired',message:'This temporary workspace has expired. Copy or export your draft before starting another.'});}
  /** Confirm an existing tab capability with the server. @returns Completion. */
  async function resume():Promise<void> {
    const token=readToken();if(!token) {update({...current.current,phase:'ready',message:''});return;}
    try {const session=await resumeSession(token);if(session) update({...current.current,phase:'active',session,message:''});else {writeToken('');update({...current.current,phase:'ready',message:'The previous workspace has expired.'});}}
    catch {update({...current.current,phase:'unavailable',message:'Workspace status is unavailable. Retry to resume this tab.'});}
  }
  /** Start only on explicit user action, preserving an old draft until confirmed. @returns Completion. */
  async function start():Promise<void> {
    if(busy.current) return;
    if(current.current.session&&!window.confirm('Starting a new workspace replaces the visible draft. Copy or export it first. Continue?')) return;
    busy.current=true;update({...current.current,message:'Starting temporary workspace…'});
    try {const session=await createSession(),stored=writeToken(session.token);update({phase:'active',session,message:stored?'':'This browser cannot retain the workspace on reload.',generation:current.current.generation+1});}
    catch(error) {update({...current.current,message:error instanceof Error?error.message:'Workspace unavailable.'});} finally {busy.current=false;}
  }
  /** End current server scope but retain the visible draft. @returns Completion. */
  async function end():Promise<void> {
    const token=current.current.session?.token;if(!token||busy.current) return;busy.current=true;
    try {await endSession(token);expire(token);} catch {update({...current.current,message:'Could not end the workspace. Try again.'});} finally {busy.current=false;}
  }
  useEffect(publicInit.bind(null,resume),[]);
  useEffect(sessionLifetime.bind(null,status.session,status.phase,expire),[status.session,status.phase]);
  return <><header className="public-session"><h1>Temporary workspace</h1><p>Each workspace is private to its session and expires after 30 minutes. After expiry, access ends and the workspace is scheduled for deletion; cleanup may be delayed. Copy or export anything you want to keep.</p><p role="status">{status.message}</p>{status.phase==='unavailable'&&<button onClick={resume}>Retry workspace status</button>}{(status.phase==='ready'||status.phase==='expired')&&<button onClick={start}>Start temporary workspace</button>}{status.phase==='active'&&<><p>Expires: <time dateTime={status.session?.expiresAt}>{status.session?.expiresAt}</time></p><button onClick={end}>End workspace</button></>}</header>{status.session&&<AllowApp key={status.generation} token={status.session.token} anonymous online={status.phase==='active'}/>}</>;
}
/** Start a single resume check. @param resume Async initializer. @returns Nothing. */
function publicInit(resume:()=>Promise<void>):void {void resume();}
/** Install expiration and authenticated-response fences for one session. @param session Checked session. @param phase Current phase. @param expire Expiry action. @returns Cleanup callback. */
function sessionLifetime(session:PublicSession|null,phase:Status['phase'],expire:(token:string)=>void):()=>void {
  if(!session||phase!=='active') return noop;
  const until=performance.now()+session.lifetimeSeconds*1000,wallUntil=Date.now()+session.lifetimeSeconds*1000;
  /** Recheck monotonic elapsed time when a sleeping tab resumes. @returns Nothing. */
  function check():void {if(performance.now()>=until||Date.now()>=wallUntil) expire(session!.token);}
  /** Ignore a delayed rejection belonging to an earlier capability. @param event Session event. @returns Nothing. */
  function rejected(event:Event):void {if((event as CustomEvent<string>).detail===session!.token) expire(session!.token);}
  const timer=window.setTimeout(check,session.lifetimeSeconds*1000);window.addEventListener(EXPIRED_EVENT,rejected);document.addEventListener('visibilitychange',check);
  /** Remove all callbacks for the retired session. @returns Nothing. */
  function cleanup():void {window.clearTimeout(timer);window.removeEventListener(EXPIRED_EVENT,rejected);document.removeEventListener('visibilitychange',check);}
  return cleanup;
}
/** Empty effect cleanup when no capability is active. @returns Nothing. */
function noop():void {}
