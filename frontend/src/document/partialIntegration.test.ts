import {expect,test,vi} from 'vitest';
import type {SetStateAction} from 'react';
import type {Accepted,Artifact,DraftModule,DraftNode,Expression,Id,SlotObligation} from './types';
import type {Controller,ViewState} from './controller';
import type {DocumentState} from './state';
import {insert,dropNode,pasteClipboard,copy,removeSelected,changeModule,previewGesture,commitGesture} from './controller';
import {initialState,openAccepted,candidate} from './state';
import {contentSnapshot,type Gesture} from './gesture';
import {checkModule,FORMULA} from './model';
import {DEFAULT_PARTIAL_LIMITS} from './partialAnalysis';
import {construct,newContradiction,paste,replacement} from './operations';
interface Harness {readonly controller:Controller;readonly publications:ViewState[];readonly timers:TimerHandler[]}
/** Assemble two nominal signatures and three independently owned formula roots. @returns Valid reference module. */
function moduleFixture():DraftModule {
  return {version:1,signatures:[{tag:'signature',id:'A',name:'A',multiplicity:'set'},{tag:'signature',id:'B',name:'B',multiplicity:'set'}],fields:[],predicates:[],assertions:[],commands:[],facts:[{tag:'fact',id:'factMain',name:'mainFact',bodyId:'main'},{tag:'fact',id:'factSource',name:'sourceFact',bodyId:'source'},{tag:'fact',id:'factThird',name:'thirdFact',bodyId:'third'}],nodes:[{tag:'some_test',id:'main',operandId:'destination'},{tag:'signature_ref',id:'destination',targetId:'A'},{tag:'not',id:'source',operandId:'sourceHole'},{tag:'hole',id:'sourceHole',expected:FORMULA},{tag:'some_test',id:'third',operandId:'thirdRelation'},{tag:'signature_ref',id:'thirdRelation',targetId:'B'}]};
}
/** Replace one node in a fixture without changing its owning slot. @param module Prior forest. @param replacement New occurrence. @returns Updated forest. */
function withNode(module:DraftModule,replacement:DraftNode):DraftModule {
  const nodes:DraftNode[]=[];for(const node of module.nodes) nodes.push(node.id===replacement.id?replacement:node);
  return {...module,nodes};
}
/** Build an isolated controller and record every publication and scheduled focus. @param module Current draft. @param selected Original selection. @param obligations Original sidecar. @returns Inspectable controller harness. */
function harness(module:DraftModule=moduleFixture(),selected:Id='third',obligations:readonly SlotObligation[]=[]):Harness {
  const artifact:Artifact={artifactId:'acceptedArtifact',mode:'BLOCK_SUPPORTED',source:'accepted source',sourceHash:'acceptedHash',module:moduleFixture() as Artifact['module'],occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:1,dependencyHash:'dependency'};
  const accepted:Accepted={documentId:'document',revision:1,headRevision:1,artifact,provenance:null},publications:ViewState[]=[],timers:TimerHandler[]=[];
  const document={...openAccepted(initialState(),accepted),module,selected,slotObligations:obligations,copies:[{sourceNodeId:'server:old',targetNodeId:'third'}]};
  const current={current:{document,documents:[],target:0,history:null,direction:'UNDO' as const} as ViewState};
  /** Record every published immutable view. @param value View or React reducer. @returns Nothing. */
  function set(value:SetStateAction<ViewState>):void {current.current=typeof value==='function'?value(current.current):value;publications.push(current.current);}
  /** Record focus scheduling without needing a browser DOM. @param callback Scheduled focus. @returns Deterministic timer identity. */
  function schedule(callback:TimerHandler):number {timers.push(callback);return timers.length;}
  vi.stubGlobal('window',{setTimeout:schedule});
  return {controller:{token:'test-authority',current,set},publications,timers};
}
/** Assert rejection changes only the existing notice field and retains reference identities. @param before Pre-gesture state. @param after Published rejection. @returns Nothing. */
function noticeOnly(before:DocumentState,after:DocumentState):void {
  expect({...after,notice:before.notice}).toEqual(before);expect(after.module).toBe(before.module);expect(after.accepted).toBe(before.accepted);
  expect(after.clipboard).toBe(before.clipboard);expect(after.copies).toBe(before.copies);expect(after.slotObligations).toBe(before.slotObligations);
  expect(after.obligationHistory).toBe(before.obligationHistory);expect(after.pendingObligations).toBe(before.pendingObligations);expect(after.notice).not.toBe(before.notice);
}
/** Reject the browser regression before inserting a known formula into a relation slot. @returns Nothing. */
function rejectsPartialNot():void {
  const fixture=harness(),before=fixture.controller.current.current.document;
  try {
    insert(fixture.controller,'not','','variable','destination');
    noticeOnly(before,fixture.controller.current.current.document);expect(fixture.publications).toHaveLength(1);expect(fixture.timers).toHaveLength(0);
    expect(fixture.controller.current.current.document.notice).toMatch(/relation|formula/i);
  } finally {vi.unstubAllGlobals();}
}
/** Preserve the pre-drag selection and unrelated clipboard for rejected copy and move gestures. @returns Nothing. */
function atomicRejectedDrops():void {
  for(const clone of [false,true]) {
    const fixture=harness(),state=fixture.controller.current.current.document;
    fixture.controller.current.current={...fixture.controller.current.current,document:{...state,clipboard:{documentId:'document',baseRevision:1,draftId:state.draftId,contentGeneration:state.contentGeneration,nodeId:'third',cut:false}}};
    const before=fixture.controller.current.current.document;
    try {dropNode(fixture.controller,'source','destination',clone);noticeOnly(before,fixture.controller.current.current.document);expect(fixture.publications).toHaveLength(1);expect(fixture.timers).toHaveLength(0);}
    finally {vi.unstubAllGlobals();}
  }
}
/** Publish exactly one content transition and one focus schedule for a valid drag. @returns Nothing. */
function singleSuccessfulDrop():void {
  const fixture=harness(),before=fixture.controller.current.current.document;
  try {
    dropNode(fixture.controller,'thirdRelation','destination',false);const after=fixture.controller.current.current.document;
    expect(fixture.publications).toHaveLength(1);expect(fixture.timers).toHaveLength(1);expect(after.contentGeneration).toBe(before.contentGeneration+1);
    expect(after.epoch).toBe(before.epoch+1);expect(after.selected).toBe('thirdRelation');expect(after.clipboard).toBeNull();expect(after.accepted).toBe(before.accepted);
  } finally {vi.unstubAllGlobals();}
}
/** Keep explicit destination constraints after incomplete replacement and reject later incompatible filling. @returns Nothing. */
function retainedHoleConstraint():void {
  const module=withNode(moduleFixture(),{tag:'hole',id:'destination',expected:{kind:'relation',columns:['A']}}),fixture=harness(module,'destination');
  try {
    insert(fixture.controller,'union','','variable','destination');const state=fixture.controller.current.current.document;
    expect(state.slotObligations).toEqual([{slot:{ownerId:'main',role:'operand'},expected:{kind:'relation',columns:['A']}}]);
    const union=state.module.nodes.find(isUnion)!;expect(checkModule(state.module,state.slotObligations).complete).toBe(false);
    insert(fixture.controller,'signature_ref','B','variable',union.leftId);noticeOnly(state,fixture.controller.current.current.document);
    insert(fixture.controller,'signature_ref','A','variable',union.leftId);const filled=fixture.controller.current.current.document;
    expect(filled.module).not.toBe(state.module);expect(filled.slotObligations).toEqual(state.slotObligations);
  } finally {vi.unstubAllGlobals();}
}
/** Select a union occurrence for independent constraint assertions. @param node Inspected occurrence. @returns Whether the node is a union expression. */
function isUnion(node:DraftNode):node is Extract<Expression,{leftId:Id}> {return node.tag==='union';}
/** Avoid converting the previous concrete inferred nominal schema into a persistent slot constraint. @returns Nothing. */
function concreteReplacementRemainsFree():void {
  const fixture=harness(moduleFixture(),'destination');
  try {insert(fixture.controller,'signature_ref','B','variable','destination');const state=fixture.controller.current.current.document;expect(state.module.nodes).toContainEqual({tag:'signature_ref',id:state.selected,targetId:'B'});expect(state.slotObligations).toEqual([]);}
  finally {vi.unstubAllGlobals();}
}
/** Reject a clipboard paste without consuming its contents or changing the current destination selection. @returns Nothing. */
function atomicRejectedClipboard():void {
  const fixture=harness(moduleFixture(),'source');
  try {
    copy(fixture.controller,true);const copied=fixture.controller.current.current.document;
    fixture.controller.current.current={...fixture.controller.current.current,document:{...copied,selected:'destination'}};
    const before=fixture.controller.current.current.document;pasteClipboard(fixture.controller);noticeOnly(before,fixture.controller.current.current.document);expect(fixture.timers).toHaveLength(0);
  } finally {vi.unstubAllGlobals();}
}
/** Compare all private violations even when public diagnostics are already saturated. @returns Nothing. */
function enforcementBeyondDisplayCap():void {
  const base=moduleFixture(),facts=[...base.facts],nodes=[...base.nodes];
  for(let i=0;i<70;i++) {facts.push({tag:'fact',id:`badFact${i}`,name:`badName${i}`,bodyId:`badNode${i}`});nodes.push({tag:'signature_ref',id:`badNode${i}`,targetId:'A'});}
  const before={...base,facts,nodes},checked=checkModule(before),after=replacement(before,'destination',construct('not','',before),[]);
  expect(checked.diagnostics).toHaveLength(64);expect(checked.violations.size).toBeGreaterThan(64);expect(newContradiction(before,before)).toBeNull();
  expect(newContradiction(before,after.module)).toMatch(/relation|formula/i);
}
/** Distinguish independent same-parent edges rather than comparing diagnostic text alone. @returns Nothing. */
function oppositeOperandViolation():void {
  const base=moduleFixture(),module=replacement(base,'source',[{tag:'and',id:'both',leftId:'badLeft',rightId:'rightHole'},{tag:'signature_ref',id:'badLeft',targetId:'A'},{tag:'hole',id:'rightHole',expected:null}],[]).module;
  const candidate=replacement(module,'rightHole',[{tag:'signature_ref',id:'badRight',targetId:'A'}],[]);
  expect(newContradiction(module,module)).toBeNull();expect(newContradiction(module,candidate.module)).not.toBeNull();
}
/** Preserve an explicit outer obligation on deletion and remove internal obligations with their owning slots. @returns Nothing. */
function deletionConstraintLifetime():void {
  const module=withNode(moduleFixture(),{tag:'hole',id:'destination',expected:{kind:'relation',columns:['A']}}),fixture=harness(module,'destination');
  try {
    insert(fixture.controller,'union','','variable','destination');const inserted=fixture.controller.current.current.document;
    removeSelected(fixture.controller);const removed=fixture.controller.current.current.document;expect(removed.slotObligations).toEqual(inserted.slotObligations);
    insert(fixture.controller,'signature_ref','B','variable',removed.selected!);noticeOnly(removed,fixture.controller.current.current.document);
    changeModule(fixture.controller,{...removed.module,facts:[],nodes:[]});expect(fixture.controller.current.current.document.slotObligations).toEqual([]);
  } finally {vi.unstubAllGlobals();}
}
/** Copy internal constraints with fresh owning identities while keeping the destination's own conjunction. @returns Nothing. */
function copiedConstraintLifetime():void {
  const base=moduleFixture(),source=withNode(base,{tag:'hole',id:'thirdRelation',expected:{kind:'relation',columns:['A']}});
  const constrained=replacement(source,'thirdRelation',construct('union','',source),[]),clip={documentId:'document',baseRevision:1,draftId:'draft',contentGeneration:1,nodeId:'third',cut:false};
  const result=paste(constrained.module,clip,'source',[],constrained.slotObligations);
  expect(result.error).toBeNull();expect(result.slotObligations).toHaveLength(2);
  expect(result.slotObligations).toContainEqual({slot:{ownerId:result.selected,role:'operand'},expected:{kind:'relation',columns:['A']}});
  expect(constrained.slotObligations).toHaveLength(1);
}
/** Conjoin a copied source's internal expectation with an independent destination expectation. @returns Nothing. */
function independentDestinationConstraint():void {
  const base=moduleFixture(),module=withNode(base,{tag:'hole',id:'destination',expected:{kind:'relation',columns:['A']}});
  const clip={documentId:'document',baseRevision:1,draftId:'draft',contentGeneration:1,nodeId:'thirdRelation',cut:false};
  const result=paste(module,clip,'destination',[]);expect(result.error).not.toBeNull();expect(result.module).toBe(module);expect(result.slotObligations).toEqual([]);
}
/** Reject malformed prior ownership before trusting a guarded replacement analysis. @returns Nothing. */
function invalidPriorAnalysis():void {
  const base=moduleFixture(),invalid=withNode(base,{tag:'not',id:'source',operandId:'source'});
  expect(newContradiction(invalid,invalid)).toContain('ANALYSIS_INVALID_GRAPH');
}
/** Ensure sidecar constraints participate in candidate validation but never enter the public module payload. @returns Nothing. */
function sidecarNeverSerialized():void {
  const base=moduleFixture(),obligations:readonly SlotObligation[]=[{slot:{ownerId:'main',role:'operand'},expected:{kind:'relation',columns:['B']}}],fixture=harness(base,'destination',obligations);
  /** Attempt serialization through the independently checked candidate boundary. @returns Candidate if complete and compatible. */
  function serialize():ReturnType<typeof candidate> {return candidate(fixture.controller.current.current.document);}
  try {expect(checkModule(base,obligations).diagnostics.length).toBeGreaterThan(0);expect(serialize).toThrow();expect(JSON.stringify(base)).not.toContain('slotObligations');}
  finally {vi.unstubAllGlobals();}
}
/** Derive stale timer behavior without allowing a rejected operation to move keyboard focus later. @returns Nothing. */
function staleFocusCannotFire():void {
  const fixture=harness(),focused:Id[]=[];
  /** Record the ID requested by a completed focus callback. @param id Requested DOM identity. @returns Focusable test element. */
  function lookup(id:string):{focus:()=>void} {
    /** Record the focus effect only if the controller actually invokes it. @returns Nothing. */
    function focus():void {focused.push(id);}
    return {focus};
  }
  vi.stubGlobal('document',{getElementById:lookup});
  try {
    insert(fixture.controller,'signature_ref','B','variable','destination');const accepted=fixture.controller.current.current.document;
    insert(fixture.controller,'not','','variable',accepted.selected!);noticeOnly(accepted,fixture.controller.current.current.document);
    for(const timer of fixture.timers) if(typeof timer==='function') timer();expect(focused).toEqual([]);expect(fixture.timers).toHaveLength(1);
  } finally {vi.unstubAllGlobals();}
}
/** Keep a scoped variable rejection atomic even when unrelated parts of the forest remain incomplete. @returns Nothing. */
function scopeRejectedDrops():void {
  const base=moduleFixture(),nodes:readonly DraftNode[]=[{tag:'all_quant',id:'scopeRoot',binder:{id:'localBinder',name:'boundVariable',signatureId:'A'},bodyId:'scopeBody'},{tag:'some_test',id:'scopeBody',operandId:'localReference'},{tag:'variable_ref',id:'localReference',targetId:'localBinder'}];
  const scoped=replacement(base,'third',nodes,[]).module;
  for(const clone of [false,true]) {
    const fixture=harness(scoped),before=fixture.controller.current.current.document;
    try {dropNode(fixture.controller,'localReference','destination',clone);noticeOnly(before,fixture.controller.current.current.document);expect(fixture.controller.current.current.document.notice).toContain('out-of-scope');expect(fixture.timers).toHaveLength(0);}
    finally {vi.unstubAllGlobals();}
  }
}
/** Distinguish new cloned internal violations from unchanged moved internal owning edges. @returns Nothing. */
function clonedAndMovedViolationIdentity():void {
  const base=moduleFixture(),invalid=replacement(base,'source',[{tag:'not',id:'badParent',operandId:'badChild'},{tag:'signature_ref',id:'badChild',targetId:'A'}],[]).module;
  const clipboard={documentId:'document',baseRevision:1,draftId:'draft',contentGeneration:1,nodeId:'badParent',cut:false};
  const cloned=paste(invalid,clipboard,'third',[]);expect(cloned.error).not.toBeNull();expect(cloned.module).toBe(invalid);
  const moved=paste(invalid,{...clipboard,cut:true},'third',[]);expect(moved.error).toBeNull();expect(moved.selected).toBe('badParent');
}
/** Reject either incomplete analysis instead of interpreting exhausted enforcement as an empty compatible set. @returns Nothing. */
function exhaustedAnalysisRejects():void {
  const base=moduleFixture(),limits={...DEFAULT_PARTIAL_LIMITS,worklistPops:0};
  expect(newContradiction(base,base,[],[],limits)).toContain('ANALYSIS_RESOURCE_LIMIT');
  expect(newContradiction(base,base,[],[],{...DEFAULT_PARTIAL_LIMITS,columnVariables:0})).toContain('ANALYSIS_RESOURCE_LIMIT');
}
/** Preserve constraints inside a moved subtree while leaving its old external slot's obligations behind. @returns Nothing. */
function movedInternalConstraint():void {
  const base=moduleFixture(),typed=withNode(base,{tag:'hole',id:'thirdRelation',expected:{kind:'relation',columns:['A']}});
  const constrained=replacement(typed,'thirdRelation',construct('union','',typed),[]),clipboard={documentId:'document',baseRevision:1,draftId:'draft',contentGeneration:1,nodeId:'third',cut:true};
  const moved=paste(constrained.module,clipboard,'source',[],constrained.slotObligations);
  expect(moved.error).toBeNull();expect(moved.slotObligations).toEqual(constrained.slotObligations);
  const union=moved.module.nodes.find(isUnion)!,attempt=replacement(moved.module,union.leftId,[{tag:'signature_ref',id:'incompatible',targetId:'B'}],moved.slotObligations);
  expect(newContradiction(moved.module,attempt.module,moved.slotObligations,attempt.slotObligations)).not.toBeNull();
}
test('PT-001 known partial formula insertion rejects before mutation',rejectsPartialNot);
/** Reject stale bindings and missing destinations without a content transition. @returns Nothing. */
function staleGesture():void {
  const fixture=harness(),state=fixture.controller.current.current.document;
  const gesture:Gesture={kind:'palette',tag:'not',target:'',name:'variable',nonce:'owned',snapshot:contentSnapshot(state)};
  try {
    expect(previewGesture(fixture.controller,gesture,'destination',false).kind).toBe('incompatible');
    commitGesture(fixture.controller,{...gesture,snapshot:'stale'},'third',false);
    noticeOnly(state,fixture.controller.current.current.document);
    const next=fixture.controller.current.current.document;commitGesture(fixture.controller,gesture,'missing',false);
    expect(fixture.controller.current.current.document.module).toBe(next.module);
    expect(fixture.controller.current.current.document.contentGeneration).toBe(next.contentGeneration);
  } finally {vi.unstubAllGlobals();}
}
/** Selection changes preserve a gesture's content binding, while move still checks type. @returns Nothing. */
function gestureSelectionAndMove():void {
  const fixture=harness(),state=fixture.controller.current.current.document;
  const gesture:Gesture={kind:'node',source:'thirdRelation',nonce:'owned',snapshot:contentSnapshot(state)};
  try {
    fixture.controller.current.current={...fixture.controller.current.current,document:{...state,selected:'destination'}};
    expect(previewGesture(fixture.controller,gesture,'destination',false).kind).not.toBe('incompatible');
    commitGesture(fixture.controller,gesture,'destination',false);
    expect(fixture.controller.current.current.document.contentGeneration).toBe(state.contentGeneration+1);
    expect(previewGesture(fixture.controller,gesture,'destination',false).kind).toBe('incompatible');
  } finally {vi.unstubAllGlobals();}
}
/** Reject unknown source and self moves while preserving draft identity. @returns Nothing. */
function gestureInvalidSources():void {
  const fixture=harness(),state=fixture.controller.current.current.document;
  const gesture:Gesture={kind:'node',source:'missing',nonce:'owned',snapshot:contentSnapshot(state)};
  try {
    expect(previewGesture(fixture.controller,gesture,'destination',false).kind).toBe('incompatible');
    commitGesture(fixture.controller,gesture,'destination',false);noticeOnly(state,fixture.controller.current.current.document);
    const self={...gesture,source:'third'},before=fixture.controller.current.current.document;
    expect(previewGesture(fixture.controller,self,'thirdRelation',false).kind).toBe('incompatible');
    commitGesture(fixture.controller,self,'thirdRelation',false);expect(fixture.controller.current.current.document.module).toBe(before.module);
  } finally {vi.unstubAllGlobals();}
}
/** Never label an incomplete candidate as fully checked. @returns Nothing. */
function gestureUnresolved():void {
  const fixture=harness(),state=fixture.controller.current.current.document;
  const gesture:Gesture={kind:'palette',tag:'not',target:'',name:'variable',nonce:'owned',snapshot:contentSnapshot(state)};
  try {expect(previewGesture(fixture.controller,gesture,'third',false).kind).toBe('unresolved');}
  finally {vi.unstubAllGlobals();}
}
test('gesture rejects foreign source and descendant move',gestureInvalidSources);
test('gesture labels incomplete candidates unresolved',gestureUnresolved);
test('gesture rejects stale identity and missing destination atomically',staleGesture);
test('gesture allows selection-only changes but expires after content edit',gestureSelectionAndMove);
test('PT-018 PT-030 copy and move drops preserve pre-gesture state on rejection',atomicRejectedDrops);
test('valid drag publishes exactly one edit and schedules focus once',singleSuccessfulDrop);
test('PT-028 explicit hole constraints survive partial replacement and later filling',retainedHoleConstraint);
test('PT-029 ordinary concrete schema replacement stays unconstrained',concreteReplacementRemainsFree);
test('PT-018 rejected clipboard paste preserves the current clipboard and selection',atomicRejectedClipboard);
test('PT-027 complete enforcement rejects new errors beyond64 display diagnostics',enforcementBeyondDisplayCap);
test('PT-026 structured constraints distinguish opposite operands of the same parent',oppositeOperandViolation);
test('PT-028 PT-032 deletion retains outer slot constraints and removes vanished owners',deletionConstraintLifetime);
test('PT-028 PT-032 copied constrained subtree remaps internal owning slots',copiedConstraintLifetime);
test('PT-032 paste conjoins independent destination constraints',independentDestinationConstraint);
test('PT-031 invalid prior ownership rejects guarded operations',invalidPriorAnalysis);
test('draft-only sidecar constrains candidate validation without a wire field',sidecarNeverSerialized);
test('PT-030 stale focus callbacks cannot activate after rejection',staleFocusCannotFire);
test('PT-019 PT-030 out-of-scope copy and move drops reject without selection or focus changes',scopeRejectedDrops);
test('PT-026 cloned invalid edges reject while unchanged internal move violations retain identity',clonedAndMovedViolationIdentity);
test('PT-031 guarded transitions reject exhausted full analysis',exhaustedAnalysisRejects);
test('PT-028 PT-032 internal explicit constraints travel with their moved owner',movedInternalConstraint);
