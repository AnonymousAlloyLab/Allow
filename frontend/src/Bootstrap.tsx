import {useEffect,useState} from 'react';
import {AllowApp} from './AllowApp';
import {PublicApp} from './PublicApp';
/** Select the explicit server mode before exposing either workspace flow. @param props Private launch capability, if any. @returns Mode-specific application. */
export function Bootstrap(props:{token:string}) {
  const [mode,setMode]=useState<'loading'|'PRIVATE'|'ANONYMOUS'|'unavailable'>('loading');
  useEffect(loadMode.bind(null,setMode),[]);
  if(mode==='PRIVATE') return <AllowApp token={props.token}/>;
  if(mode==='ANONYMOUS') return <PublicApp/>;
  return <main><h1>Allow</h1><p role="status">{mode==='loading'?'Connecting…':'Service unavailable. Reload to retry.'}</p></main>;
}
/** Read only the server's closed public mode. @param setMode Mode consumer. @returns Cleanup. */
function loadMode(setMode:(mode:'PRIVATE'|'ANONYMOUS'|'unavailable')=>void):()=>void {
  const controller=new AbortController();
  void fetch('/api/public/config',{cache:'no-store',credentials:'omit',signal:controller.signal}).then(readMode).then(setMode).catch(failed.bind(null,controller,setMode));
  return controller.abort.bind(controller);
}
/** Validate the minimal public configuration. @param response Server response. @returns Closed mode. @throws Error on invalid response. */
async function readMode(response:Response):Promise<'PRIVATE'|'ANONYMOUS'> {
  if(!response.ok) throw new Error('Unavailable configuration.');const data:unknown=await response.json();
  if(!data||typeof data!=='object'||!('mode' in data)||(data.mode!=='PRIVATE'&&data.mode!=='ANONYMOUS')) throw new Error('Invalid configuration.');
  return data.mode;
}
/** Avoid stale updates after unmount. @param controller Request owner. @param setMode Mode consumer. @returns Nothing. */
function failed(controller:AbortController,setMode:(mode:'unavailable')=>void):void {if(!controller.signal.aborted) setMode('unavailable');}
