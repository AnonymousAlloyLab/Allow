// @vitest-environment jsdom
import {act} from 'react';
import {createRoot,type Root} from 'react-dom/client';
import {afterEach,expect,test,vi} from 'vitest';
import {AccessRequest} from './AccessRequest';
import {captchaMessage} from './protocol';
let root:Root|null=null;
/** Unmount and remove all isolated stubs. @returns Completion. */
async function cleanup():Promise<void>{if(root)await act(unmount);root=null;document.body.innerHTML='';vi.unstubAllGlobals();}
/** Remove the mounted request owner. @returns Nothing. */
function unmount():void{root?.unmount();}
afterEach(cleanup);
/** Mount the isolated page with checked public config. @param enabled Feature state. @returns Fetch mock. */
async function mount(enabled=true){const fetcher=vi.fn().mockResolvedValueOnce(response(enabled?{enabled,siteKey:'public-key'}:{enabled:false}));vi.stubGlobal('fetch',fetcher);vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT',true);document.body.innerHTML='<div id="test"></div>';root=createRoot(document.getElementById('test')!);await act(render);return fetcher;}
/** Render the request entry independently of the workbench. @returns Nothing. */
function render():void{root!.render(<AccessRequest/>);}
/** Build a successful bounded protocol reply. @param data Reply object. @returns Response. */
function response(data:unknown):Response{return new Response(JSON.stringify(data),{status:200});}
/** Fill required fields using native DOM inputs. @returns Nothing. */
function fill():void{field('name').value='Ada';field('email').value='ada@example.test';field('organization').value='Research';field('purpose').value='Explore model reasoning for specification workflows.';(field('acknowledged') as HTMLInputElement).checked=true;}
/** Resolve a named form field. @param name Field name. @returns Native field. */
function field(name:string):HTMLInputElement|HTMLTextAreaElement{return document.querySelector(`[name="${name}"]`)!;}
/** Submit the currently displayed form. @returns Nothing. */
function submit():void{document.querySelector('form')!.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}
/** Retrieve the private nonce through the public initialization message. @returns Nonce and child source. */
async function token(){const frame=document.querySelector('iframe')!,send=vi.spyOn(frame.contentWindow!,'postMessage');await act(load);const init=send.mock.calls[0][0] as {nonce:string};return {nonce:init.nonce,source:frame.contentWindow!};
  /** Trigger the exact child initialization boundary. @returns Nothing. */
  function load():void{frame.dispatchEvent(new Event('load'));}
}
/** Deliver one checked captcha result. @param nonce Bound nonce. @param source Bound child. @returns Completion. */
async function solve(nonce:string,source:Window):Promise<void>{await act(deliver);
  /** Dispatch only the expected opaque-child payload. @returns Nothing. */
  function deliver():void{window.dispatchEvent(new MessageEvent('message',{origin:'null',source,data:{kind:'token',nonce,token:'provider-token'}}));}
}
/** Prove form binding survives verification and no authority or persistence is used. @returns Completion. */
async function flow():Promise<void>{const fetcher=await mount(),conversation=await token();fill();await solve(conversation.nonce,conversation.source);fetcher.mockResolvedValueOnce(response({status:'CODE_SENT',challenge:'bound-challenge',expiresAt:Date.now()+600000}));await act(submit);expect(document.querySelector('[name="purpose"]')).toBeNull();field('code').value='01234567';fetcher.mockResolvedValueOnce(response({status:'REQUESTED',requestId:'review-reference'}));await act(submit);expect(document.body.textContent).toContain('pending manual review');const payload=JSON.parse(fetcher.mock.calls[2][1].body);expect(payload).toEqual({challenge:'bound-challenge',code:'01234567'});expect(fetcher.mock.calls[1][1]).toMatchObject({credentials:'omit',headers:{'Content-Type':'application/json'}});expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({name:'Ada',email:'ada@example.test',acknowledged:true});expect(document.body.textContent).not.toContain('access token:');}
/** Reject spoofed, stale and extra-field provider messages. @returns Completion. */
async function isolation():Promise<void>{await mount();const {nonce,source}=await token();const data={kind:'token',nonce,token:'okay'};expect(captchaMessage(new MessageEvent('message',{origin:location.origin,source,data}),source,nonce)).toBeNull();expect(captchaMessage(new MessageEvent('message',{origin:'null',source:window,data}),source,nonce)).toBeNull();expect(captchaMessage(new MessageEvent('message',{origin:'null',source,data:{...data,extra:true}}),source,nonce)).toBeNull();expect(captchaMessage(new MessageEvent('message',{origin:'null',source,data}),source,'old')).toBeNull();expect(document.querySelector('iframe')!.getAttribute('sandbox')).toBe('allow-scripts');}
/** Keep OFF visible and prevent incomplete forms reaching external work. @returns Completion. */
async function disabled():Promise<void>{const fetcher=await mount(false);expect(document.body.textContent).toContain('Email verification settings are pending');expect(document.querySelector('iframe')).toBeNull();expect(document.querySelector('button')!.disabled).toBe(true);await act(submit);expect(fetcher).toHaveBeenCalledTimes(1);}
/** Browser validation blocks malformed applicant data even with a valid captcha. @returns Completion. */
async function validation():Promise<void>{const fetcher=await mount(),conversation=await token();await solve(conversation.nonce,conversation.source);field('email').value='not-an-email';await act(submit);expect(fetcher).toHaveBeenCalledTimes(1);}
/** Ignore an in-flight challenge response after the page owner unmounts. @returns Completion. */
async function stale():Promise<void>{const fetcher=await mount(),conversation=await token();fill();await solve(conversation.nonce,conversation.source);let finish!:(response:Response)=>void;fetcher.mockReturnValueOnce(new Promise(resolve));await act(submit);await act(unmount);await act(complete);expect(document.body.textContent).not.toContain('Check your email');
  /** Hold the challenge response for a retired page owner. @param accept Deferred resolver. @returns Nothing. */
  function resolve(accept:(response:Response)=>void):void{finish=accept;}
  /** Complete after owner retirement. @returns Nothing. */
  function complete():void{finish(response({status:'CODE_SENT',challenge:'late',expiresAt:Date.now()+600000}));}
}
test('request binds immutable form and verifies with challenge and code only',flow);
test('captcha messages require exact opaque source nonce and closed shape',isolation);
test('OFF keeps intake visible and disabled',disabled);
test('browser validation blocks invalid applicant fields',validation);
test('unmounted page rejects stale challenge completion',stale);
