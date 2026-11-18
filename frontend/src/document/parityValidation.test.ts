import {expect,test,vi} from 'vitest';
import {validParityPayload,validParityCategories} from './parityValidation';
import {parityActivation,type Runtime} from './useOracleParity';
import {AdvisoryValidator} from './advisory';
/** Build a closed valid parity response for independent mutation checks. @returns Successful payload. */
function fixture() {
  const hash='a'.repeat(64),witness={states:[{atoms:[{id:'A$0',memberships:['A']}],relations:[{name:'r',arity:1,tuples:[['A$0']]}]}],traceLength:1,loopState:-1,truncated:false,fullInstanceHash:hash};
  const assignment=[{id:'shared',name:'x',leftName:'x',rightName:'y',columns:['A'],truncated:false,tuples:[['A$0']]}];
  return {synthesizedSourceHash:hash,categories:{both:{status:'SAT',left:true,right:true,evidenceHash:hash,witness,assignment},leftOnly:{status:'UNSAT'},rightOnly:{status:'UNSAT'},neither:{status:'UNSAT'}},classification:'AGREEMENT',moduleHash:hash,scope:3,bitwidth:4,maxseq:3,sourceHash:hash,left:{sourceHash:hash,predicate:'candidate'},right:{sourceHash:hash,predicate:'oracle'},oracle:{sourceHash:hash,predicate:'oracle'},correspondence:{leftPredicate:'candidate',rightPredicate:'oracle',parameters:[{leftName:'x',rightName:'y',columns:['A'],sharedId:'shared'}],declarations:[{kind:'signature',name:'A'}]},targetId:'target',requestHash:hash,documentId:'document',draftId:'draft',draftEpoch:1,baseRevision:1,artifactId:'artifact',policyVersion:'policy',dependencyHash:'dependency'};
}
/** Mutate one JSON path in an independent cloned response. @param path Target path. @param value Replacement. @returns Malformed payload. */
function mutate(path:string,value:unknown):unknown {
  const result=structuredClone(fixture()) as unknown as Record<string,unknown>,parts=path.split('.');let object=result;
  for(const part of parts.slice(0,-1)) object=object[part] as Record<string,unknown>;object[parts[parts.length-1]]=value;return result;
}
/** Reject malformed nested evidence and identities before any renderer sees them. @returns Nothing. */
function mutationBoundary():void {
  expect(validParityPayload(fixture())).toBe(true);
  const cases:[string,unknown][]=[['sourceHash','bad'],['moduleHash','bad'],['left.sourceHash','bad'],['correspondence.parameters',null],['correspondence.declarations',null],['correspondence.parameters.0.sharedId','other'],['categories.both.witness.states',[null]],['categories.both.witness.states',[{}]],['categories.both.assignment',[null]],['categories.both.witness.truncated',null],['categories.both.witness.traceLength',2],['categories.both.witness.loopState',1],['categories.both.witness.states.0.atoms.0.memberships',[]],['categories.both.witness.states.0.relations.0.tuples',[[]]],['categories.both.assignment.0.columns',[]],['categories.both.assignment.0.truncated',null],['classification','DISTINGUISHED']];
  for(const [path,value] of cases) expect(validParityPayload(mutate(path,value)),path).toBe(false);
  expect(validParityCategories({...fixture().categories,neither:{status:'UNSAT',extra:true}})).toBe(false);
  expect(validParityCategories({...fixture().categories,both:{...fixture().categories.both,extra:true}})).toBe(false);
  expect(validParityPayload({...fixture(),extra:true})).toBe(false);
}
/** Preserve serial execution while activation ABA creates exactly one new automatic attempt. @returns Completion. */
async function activationABA():Promise<void> {
  vi.useFakeTimers();
  try {for(const mode of ['disable','offline']) for(const inflight of [false,true]) await activationCase(mode,inflight);} finally {vi.useRealTimers();}
}
/** Exercise one settled or in-flight disable/availability ABA transition. @param mode Transition kind. @param inflight Whether original request is active. @returns Completion. */
async function activationCase(mode:string,inflight:boolean):Promise<void> {
  const scheduler=new AdvisoryValidator(),live={activation:0,availability:'',alive:true} as Runtime;let starts=0,release!:()=>void;
  /** Hold the original operation until explicitly released. @param resolve Completion callback. @returns Nothing. */
  function capture(resolve:()=>void):void {release=resolve;}
  /** Run one serialized request, optionally holding its first completion. @param signal Lifetime signal. @returns Completion. */
  async function run(signal:AbortSignal):Promise<void> {void signal;starts++;if(inflight&&starts===1) await new Promise<void>(capture);}
  const first=String(parityActivation(live,true,true));scheduler.request({key:first,run});await vi.advanceTimersByTimeAsync(350);expect(starts).toBe(1);
  parityActivation(live,mode!=='offline',mode!=='disable');scheduler.clearPending();const renewed=String(parityActivation(live,true,true));expect(renewed).not.toBe(first);
  scheduler.request({key:renewed,run});await vi.advanceTimersByTimeAsync(350);expect(starts).toBe(inflight?1:2);
  if(inflight) {release();await vi.advanceTimersByTimeAsync(350);expect(starts).toBe(2);}
  scheduler.request({key:renewed,run});await vi.advanceTimersByTimeAsync(1000);expect(starts).toBe(2);scheduler.dispose();
}
test('closed parity payload rejects malformed nested witnesses, schemas and source identities',mutationBoundary);
test('settled and in-flight disable and offline ABA each schedule one fresh serialized check',activationABA);
