// @vitest-environment jsdom
import {expect,test,vi} from 'vitest';
import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {webcrypto} from 'node:crypto';
import {DocumentBody} from '../DocumentWorkbench';
import {Fixture} from './fixtures';
import {initialState,openAccepted} from './state';
import type {Controller,ViewState} from './controller';
import {digest} from './api';
/** Build a complete independently named document with different predicate identities. @param id Document identity. @returns Workbench view. */
function view(id:string):ViewState {
  const module=new Fixture().build('not'),artifact={artifactId:`artifact-${id}`,mode:'BLOCK_SUPPORTED' as const,source:'sig A {}',sourceHash:'a'.repeat(64),module:module as never,occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:'policy',dependencyHash:'dependency'};
  return {document:openAccepted(initialState(),{documentId:id,revision:1,headRevision:1,artifact,provenance:null}),documents:[],target:0,history:null,direction:'UNDO'};
}
/** Accept controller notifications outside the isolated rendered fixture. @param value Callback payload. @returns Nothing. */
function ignore(value:unknown):void {void value;}
/** Return checked parser choices without external services or persistence. @param input Endpoint. @param init Request. @returns Bounded protocol response. */
async function response(input:RequestInfo|URL,init?:RequestInit):Promise<Response> {
  if(!String(input).endsWith('/comparison-model')) return new Response(JSON.stringify({protocol:1,status:'OK',data:{mode:'OFF'}}));
  const body=String(init?.body),request=JSON.parse(body),data={...request,requestHash:await digest(body),documentId:'first',policyVersion:'policy',dependencyHash:'dependency',predicates:[{name:'Reference',parameters:[]}]};delete data.source;
  return new Response(JSON.stringify({protocol:1,status:'OK',data}));
}
/** Flush bounded asynchronous file reading, parser response and inventory effects. @param resolve Completion callback. @returns Nothing. */
function delay(resolve:()=>void):void {setTimeout(resolve,60);}
/** Mount an uploaded oracle then replace documents twice, proving actual DOM removal and cleanup. @returns Completion. */
async function documentLifetime():Promise<void> {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT',true);vi.stubGlobal('crypto',webcrypto);vi.stubGlobal('fetch',response);
  const host=document.createElement('div'),root=createRoot(host),first=view('first'),controller:Controller={token:'authority',current:{current:first},set:ignore};document.body.append(host);
  try {
    await act(render.bind(null,root,controller,first));const old=host.querySelector('.block-workspace')!;
    const input=old.querySelector('input[type=file]')!,file={name:'old-oracle.als',size:8,arrayBuffer:bytes} as File;Object.defineProperty(input,'files',{value:[file]});
    await act(change.bind(null,input));await act(wait);expect(old.textContent).toContain('old-oracle.als');
    const enable=old.querySelector('input[type=checkbox]') as HTMLInputElement;await act(toggle.bind(null,enable));expect(enable.checked).toBe(true);
    for(const id of ['second','third']) {const next=view(id);await act(render.bind(null,root,controller,next));expect(host.querySelectorAll('.block-workspace')).toHaveLength(1);expect(host.textContent).not.toContain('old-oracle.als');expect(old.isConnected).toBe(false);expect(host.querySelectorAll('.block-comparison')).toHaveLength(1);expect((host.querySelector('input[type=checkbox]') as HTMLInputElement).checked).toBe(false);}
  } finally {await act(unmount.bind(null,root));host.remove();vi.unstubAllGlobals();}
}
/** Supply exact local file bytes asynchronously. @returns UTF8 source. */
async function bytes():Promise<ArrayBuffer> {return new TextEncoder().encode('sig A {}').buffer;}
/** Dispatch a real DOM file selection. @param input File input. @returns Nothing. */
function change(input:Element):void {input.dispatchEvent(new Event('change',{bubbles:true}));}
/** Flush current effects inside the React act boundary. @returns Completion. */
async function wait():Promise<void> {await new Promise<void>(delay);}
/** Render a replacement document using the same owner and real reconciler. @param root React root. @param controller Current owner. @param next Replacement view. @returns Nothing. */
function render(root:ReturnType<typeof createRoot>,controller:Controller,next:ViewState):void {controller.current.current=next;root.render(<DocumentBody controller={controller} view={next} online/>);}
/** Dispose all mounted hooks and browser waits. @param root React root. @returns Nothing. */
function unmount(root:ReturnType<typeof createRoot>):void {root.unmount();}
test('document replacement removes the previous real DOM workspace and memory-only oracle',documentLifetime);

/** Toggle parity using a native DOM checkbox activation. @param input Enable input. @returns Nothing. */
function toggle(input:HTMLInputElement):void {input.click();}
