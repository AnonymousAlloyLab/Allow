import {expect,test,vi} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {ExpressionEditor} from './ExpressionEditor';
import {Fixture} from './fixtures';
import {digest} from './api';
import {AdvisoryValidator} from './advisory';
import {initialState,openAccepted} from './state';
import type {Controller,ViewState} from './controller';
import {parityVerdict,parityKey,type ParitySelection} from './oracleParity';
import {upload,lifetime,queue,type Context,type Runtime} from './useOracleParity';
/** Create one fully replayed SAT category fixture. @param left Candidate truth. @param right Oracle truth. @returns Category evidence. */
function sat(left:boolean,right:boolean) {return {status:'SAT',left,right,evidenceHash:'a'.repeat(64),witness:{states:[{atoms:[],relations:[]}],traceLength:1,loopState:-1,truncated:false,fullInstanceHash:'b'.repeat(64)},assignment:[]};}
/** Exercise all completed category combinations plus malformed and unknown outcomes. @returns Nothing. */
function truthTable():void {
  for(let mask=0;mask<16;mask++) {
    const categories={both:mask&1?sat(true,true):{status:'UNSAT'},leftOnly:mask&2?sat(true,false):{status:'UNSAT'},rightOnly:mask&4?sat(false,true):{status:'UNSAT'},neither:mask&8?sat(false,false):{status:'UNSAT'}};
    expect(parityVerdict({categories})).toBe(mask&6?'difference':mask&9?'match':null);
    expect(parityVerdict({categories:{...categories,both:{status:'UNKNOWN'}}})).toBeNull();
  }
  expect(parityVerdict({categories:{both:sat(true,true),leftOnly:{status:'UNSAT'},rightOnly:{status:'UNSAT'}}})).toBeNull();
  expect(parityVerdict({categories:{both:sat(true,true),leftOnly:sat(true,true),rightOnly:{status:'UNSAT'},neither:{status:'UNSAT'}}})).toBeNull();
  for(const malformed of [{...sat(true,true),evidenceHash:'bad'},{...sat(true,true),witness:{states:[],truncated:false,fullInstanceHash:'b'.repeat(64)}}]) expect(parityVerdict({categories:{both:malformed,leftOnly:{status:'UNSAT'},rightOnly:{status:'UNSAT'},neither:{status:'UNSAT'}}})).toBeNull();
}
/** Accept component callbacks while examining accessible frame markup. @param values Callback arguments. @returns Nothing. */
function ignore(...values:unknown[]):void {void values;}
/** Frame one complete predicate root without marking unrelated roots. @returns Nothing. */
function forestFrame():void {
  const module=new Fixture().build('not'),targetId=module.predicates[0].id;
  const markup=renderToStaticMarkup(<ExpressionEditor parityFrame={{targetId,verdict:'match',scope:3}} entries={[]} onCapture={ignore} onRename={ignore} onRemove={ignore} onSaved={ignore} snapshot="parity" module={module} selected={null} onSelect={ignore} onInsert={ignore} onClipboard={ignore} onPaste={ignore} onDelete={ignore} onDropNode={ignore} onCancel={ignore} onNotice={ignore}/>);
  expect(markup.match(/data-parity="match"/g)).toHaveLength(1);expect(markup).toContain('Bounded match · scope 3, bitwidth 4, maximum sequence 3');expect(markup).toContain('parity-match');
  const neutral=renderToStaticMarkup(<ExpressionEditor entries={[]} onCapture={ignore} onRename={ignore} onRemove={ignore} onSaved={ignore} snapshot="parity" module={module} selected={null} onSelect={ignore} onInsert={ignore} onClipboard={ignore} onPaste={ignore} onDelete={ignore} onDropNode={ignore} onCancel={ignore} onNotice={ignore}/>);
  expect(neutral).not.toContain('data-parity=');
}
/** Create an isolated upload lifecycle without a mounted browser. @returns Context fixture. */
function contextFixture():Context {
  const document=initialState(),controller={token:'authority',current:{current:{document} as ViewState},set:ignore} as Controller;
  const selection:ParitySelection={enabled:false,targetId:'',scope:3,oracle:null},runtime={current:{alive:true,generation:0,key:'key',online:true,selection,active:null,inspection:null} as Runtime};
  return {controller,runtime,scheduler:new AdvisoryValidator(),setSelection:ignore,setOutcome:ignore,setNotice:ignore,setBusy:ignore};
}
/** Delayed upload bytes cannot restore removed or unmounted oracle state. @returns Completion. */
async function staleUpload():Promise<void> {
  const context=contextFixture();let release!:(bytes:ArrayBuffer)=>void;
  /** Hold a browser file read until a replacement or unmount. @param resolve Byte continuation. @returns Nothing. */
  function capture(resolve:(bytes:ArrayBuffer)=>void):void {release=resolve;}
  /** Read the held source. @returns Byte promise. */
  function arrayBuffer():Promise<ArrayBuffer> {return new Promise(capture);}
  const file={name:'oracle.als',size:9,arrayBuffer} as File;
  const first=upload(context,file);await upload(context,null);release(new TextEncoder().encode('sig A {}').buffer);await first;expect(context.runtime.current.selection.oracle).toBeNull();
  const second=upload(context,file);lifetime(context)();release(new TextEncoder().encode('sig B {}').buffer);await second;expect(context.runtime.current.selection.oracle).toBeNull();
}
/** Every authority and availability transition changes the exact evidence presentation key. @returns Nothing. */
function publicationIdentity():void {
  const state=initialState(),selection:ParitySelection={enabled:true,targetId:'pred',scope:3,oracle:null},key=parityKey('token',state,selection,true);
  expect(parityKey('other',state,selection,true)).not.toBe(key);expect(parityKey('token',state,selection,false)).not.toBe(key);
  expect(parityKey('token',state,{...selection,enabled:false},true)).not.toBe(key);expect(parityKey('token',{...state,epoch:state.epoch+1},selection,true)).not.toBe(key);
  expect(parityKey('token',state,{...selection,targetId:'other'},true)).not.toBe(key);expect(parityKey('token',state,{...selection,scope:4},true)).not.toBe(key);
}
test('parity verdict requires all four completed replayed truth categories',truthTable);
test('parity frames exactly the selected whole predicate with visible bounds',forestFrame);
test('delayed oracle file reads are discarded after replacement and unmount',staleUpload);
test('parity publication key changes immediately for authority, epoch, availability and options',publicationIdentity);

/** Ignore late completed responses after edits, disable and lifetime disposal. @returns Completion. */
async function lateResponses():Promise<void> {
  for(const transition of ['edit','disable','unmount']) {
    const context=contextFixture(),module=new Fixture().build('not'),state=openAccepted(initialState(),{documentId:'document',revision:1,headRevision:1,provenance:null,artifact:{artifactId:'artifact',mode:'BLOCK_SUPPORTED',source:'',sourceHash:'hash',module:module as never,occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:'policy',dependencyHash:'dependency'}});
    context.controller.current.current={...context.controller.current.current,document:state};
    context.runtime.current.selection={enabled:true,targetId:module.predicates[0].id,scope:3,oracle:{filename:'oracle.als',source:'sig A {}',sourceHash:'oracle',predicate:'p',predicates:[],inspection:'oracle'}};
    let release!:(response:Response)=>void,started!:()=>void,published=0;
    /** Register request-start notification. @param resolve Continuation. @returns Nothing. */
    function start(resolve:()=>void):void {started=resolve;}
    const began=new Promise<void>(start);
    /** Hold HTTP completion beyond a local transition. @param input URL. @param init HTTP body. @returns Delayed response. */
    async function fetch(input:RequestInfo|URL,init?:RequestInit):Promise<Response> {
      void input;const request=JSON.parse(String(init?.body)),requestHash=await digest(String(init?.body));
      /** Capture the stale server response continuation. @param resolve Response callback. @returns Nothing. */
      function capture(resolve:(response:Response)=>void):void {release=resolve;}
      const response=new Promise<Response>(capture);Object.assign(context,{setOutcome:count});started();
      release=newResponse.bind(null,release,{...request,requestHash,documentId:'document',policyVersion:'policy',dependencyHash:'dependency'});return response;
    }
    /** Count only attempted evidence publication. @param value Outcome. @returns Nothing. */
    function count(value:unknown):void {if(value) published++;}
    vi.stubGlobal('fetch',fetch);queue(context,true);await began;
    if(transition==='unmount') lifetime(context)();else {context.runtime.current.key=transition;if(transition==='disable') context.runtime.current.active?.abort();}
    release(new Response());await new Promise<void>(finish);expect(published).toBe(0);context.scheduler.dispose();vi.unstubAllGlobals();
  }
}
/** Build a late envelope while keeping the fetch continuation readable. @param resolve Response callback. @param data Echoed response. @param ignored Placeholder. @returns Nothing. */
function newResponse(resolve:(response:Response)=>void,data:unknown,ignored:Response):void {void ignored;resolve(new Response(JSON.stringify({protocol:1,status:'OK',requestId:'request',data})));}
/** Settle asynchronous response publication callbacks. @param resolve Completion callback. @returns Nothing. */
function finish(resolve:()=>void):void {setTimeout(resolve,10);}
test('late parity responses cannot publish after edits, disable or unmount',lateResponses);
