// @vitest-environment jsdom
import {readFileSync} from 'node:fs';
import {afterEach,expect,test,vi} from 'vitest';
const script=readFileSync('public/request-ai-access/captcha.js','utf8');
/** Restore each local bridge harness. @returns Nothing. */
function cleanup():void{vi.unstubAllGlobals();document.head.innerHTML='';document.body.innerHTML='';}
afterEach(cleanup);
/** Evaluate the real classic bridge against an isolated fake window. @returns Harness. */
function harness(){const parent={postMessage:vi.fn()},listeners:Record<string,(event:unknown)=>void>={},fakeWindow:Record<string,unknown>={};let callbacks:Record<string,unknown>={};const grecaptcha={render:vi.fn(render),reset:vi.fn()};const location={origin:'https://allow.example'};
  /** Capture provider callbacks without loading Google. @param element Target. @param options Provider callbacks. @returns Widget identifier. */
  function render(element:string,options:Record<string,unknown>):number{expect(element).toBe('captcha');expect(options.size).toBe('compact');callbacks=options;return 0;}
  /** Capture the local window listener. @param name Event name. @param callback Event callback. @returns Nothing. */
  function add(name:string,callback:(event:unknown)=>void):void{listeners[name]=callback;}
  fakeWindow.addEventListener=add;new Function('window','parent','location','document','grecaptcha',script)(fakeWindow,parent,location,document,grecaptcha);
  /** Send a synthetic parent event into the real bridge. @param data Candidate data. @param origin Candidate origin. @param source Candidate parent. @returns Nothing. */
  function receive(data:unknown,origin=location.origin,source:unknown=parent):void{listeners.message({data,origin,source});}
  /** Mark the provider ready locally. @returns Nothing. */
  function ready():void{(fakeWindow.allowCaptchaLoaded as ()=>void)();}
  /** Return the provider callback captured by real rendering. @param kind Callback key. @returns Callback. */
  function callback(kind:string):(...args:unknown[])=>void{return callbacks[kind] as (...args:unknown[])=>void;}
  return {parent,receive,ready,callback,grecaptcha};
}
/** Reject hostile initialization before any provider resource is created. @returns Nothing. */
function initialization():void{const h=harness(),data={kind:'initialize',nonce:'a'.repeat(64),siteKey:'public-key'};h.receive(data,'null');h.receive(data,'https://allow.example',{});h.receive({...data,pii:'private'});h.receive({...data,nonce:'short'});expect(document.getElementById('provider')).toBeNull();h.receive(data);expect(document.getElementById('provider')?.getAttribute('src')).toBe('https://www.google.com/recaptcha/api.js?onload=allowCaptchaLoaded&render=explicit');h.ready();expect(h.grecaptcha.render).toHaveBeenCalledTimes(1);}
/** Expire tokens and reset with a new nonce without leaking applicant data. @returns Nothing. */
function callbacks():void{const h=harness(),nonce='a'.repeat(64);h.receive({kind:'initialize',nonce,siteKey:'public-key'});h.ready();h.callback('callback')('token');expect(h.parent.postMessage).toHaveBeenLastCalledWith({kind:'token',nonce,token:'token'},'https://allow.example');h.callback('expired-callback')();expect(h.parent.postMessage).toHaveBeenLastCalledWith({kind:'expired',nonce},'https://allow.example');h.callback('error-callback')();expect(h.parent.postMessage).toHaveBeenLastCalledWith({kind:'error',nonce},'https://allow.example');h.receive({kind:'initialize',nonce:'b'.repeat(64),siteKey:'public-key'});expect(h.grecaptcha.reset).toHaveBeenCalledWith(0);h.callback('callback')('x'.repeat(4097));expect(h.parent.postMessage).toHaveBeenLastCalledWith({kind:'error',nonce:'b'.repeat(64)},'https://allow.example');}
test('real classic bridge validates parent source origin nonce and closed shape',initialization);
test('real classic bridge handles provider result expiry error and nonce reset',callbacks);
