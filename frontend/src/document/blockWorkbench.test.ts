import {expect,test} from 'vitest';
import {Fixture} from './fixtures';
import {initialState,editModule} from './state';
import type {DocumentState} from './state';
import type {Accepted,DraftModule} from './types';
import {captureBlock,prepareSavedBlock,libraryLimit} from './blockLibrary';
import {nodeIndex,checkModule,subtree} from './model';
import {construct,replaceSubtree} from './operations';
import {contentSnapshot} from './gesture';
import {prepareInsert,previewGesture,type Controller} from './controller';
import {inventoryChoices,evaluateChoice,type InventoryInput} from './blockInventory';
import {changeComparisonSelection} from './useBlockComparison';
import {comparisonFailure,comparisonIdentity,comparisonKey,comparisonPayload,decodeModel,type ComparisonData,type ComparisonSelection} from './blockComparison';
/** Create a bounded accepted-context fixture without contacting a server. @param module Complete forest. @returns Local state. */
function stateFor(module:DraftModule=new Fixture().build('all_quant')):DocumentState {
  const accepted={documentId:'doc',revision:1,headRevision:1,artifact:{artifactId:'artifact',policyVersion:1,dependencyHash:'dependency'}} as Accepted;
  return {...initialState(),module,accepted,baseRevision:1,selected:module.predicates[0].bodyId};
}
/** Snapshot remains reusable after unrelated content edits and freshens all internal bindings. @returns Nothing. */
function immutableReuse():void {
  const state=stateFor(),entry=captureBlock(state,'Reusable quantifier'),root=entry.root;
  const destination=state.module.predicates[1].bodyId,changed=editModule(state,replaceSubtree(state.module,destination,construct('some_test','',state.module)));
  const result=prepareSavedBlock(changed,entry,changed.module.predicates[1].bodyId);
  expect(result.error).toBeNull();expect(entry.root).toBe(root);expect(entry.nodes[0].id).toBe(root);
  const ids=subtree(result.module,result.selected),old=new Set(entry.nodes.map(nodeId));for(const id of ids) expect(old.has(id)).toBe(false);
  const nodes=nodeIndex(result.module),quantifier=nodes.get(result.selected)!;expect('binder' in quantifier).toBe(true);
  if('binder' in quantifier) {const references=[...ids].map(nodes.get.bind(nodes)).filter(variableReference);expect(references.some(matchesTarget.bind(null,quantifier.binder.id))).toBe(true);}
  expect(checkModule(result.module,result.slotObligations).resourceFailure).toBeNull();
}
/** Reject foreign, changed-environment, out-of-scope and source-authoritative insertion atomically. @returns Nothing. */
function rejectedReuse():void {
  const state=stateFor(),entry=captureBlock(state,'Saved'),destination=state.module.predicates[1].bodyId;
  for(const changed of [{...state,mode:'SOURCE' as const},{...state,accepted:{...state.accepted!,documentId:'other'}},{...state,module:{...state.module,signatures:state.module.signatures.slice(1)}}]) {
    const result=prepareSavedBlock(changed,entry,changed.module.predicates[1].bodyId);expect(result.error).toBeTruthy();expect(result.module).toBe(changed.module);
  }
  const quantifier=nodeIndex(state.module).get(entry.root)!;if('binder' in quantifier) {
    const scoped=captureBlock({...state,selected:quantifier.bodyId},'Scoped');expect(prepareSavedBlock(state,scoped,destination).error).toContain('scope');
  }
  expect(libraryLimit(Array.from({length:25},repeatEntry.bind(null,entry)))).toContain('24');
}
/** Filtering uses exact applicable reference candidates and the same transaction guard as insertion. @returns Nothing. */
function filterParity():void {
  const state=stateFor(new Fixture().build('not')),destination=state.selected!,controller={current:{current:{document:state}}} as Controller;
  const input:InventoryInput={module:state.module,checked:checkModule(state.module),selected:destination,snapshot:contentSnapshot(state),name:'x',entries:[],preview:previewGesture.bind(null,controller)};
  const choices=inventoryChoices(input),reference=choices.find(signatureReference)!;
  expect(evaluateChoice(input,reference).kind).toBe('incompatible');expect(prepareInsert(state,reference.tag,reference.target,'x',destination).error).toBeTruthy();
  expect(evaluateChoice(input,choices.find(andChoice)!).kind).toBe('unresolved');
  expect(inventoryChoices({...input,selected:null}).some(signatureReference)).toBe(true);
}
/** Strict local decoding and response fencing reject malformed bytes and changed controls. @returns Nothing. */
function comparisonFences():void {
  expect(decodeModel(new TextEncoder().encode('sig A {}').buffer)).toBe('sig A {}');expect(decodeInvalid).toThrow();expect(decodeOversized).toThrow('32 KiB');
  const state=stateFor(),selection:ComparisonSelection={mode:'blocks',leftId:state.selected!,rightId:state.selected!,scope:3,left:null,right:null};
  expect(comparisonKey(state,selection)).not.toBe(comparisonKey({...state,contentGeneration:state.contentGeneration+1},selection));
  /** Reject comparison against a retained stale AST under source authority. @returns Nothing. */
  function sourcePayload():void {comparisonPayload({...state,mode:'SOURCE'},selection);}
  expect(sourcePayload).toThrow('authoritative');
  const data={requestHash:'hash',documentId:'doc',draftId:state.draftId,draftEpoch:state.epoch,baseRevision:1,artifactId:'artifact',policyVersion:1,dependencyHash:'dependency'} as ComparisonData;
  expect(comparisonIdentity(data,state,'hash')).toBe(true);expect(comparisonIdentity(data,state,'other')).toBe(false);expect(comparisonIdentity(data,{...state,epoch:state.epoch+1},'hash')).toBe(false);
}
/** Read node identity. @param node Node. @returns Identity. */
function nodeId(node:{id:string}):string {return node.id;}
/** Narrow a variable reference for binding assertions. @param node Node. @returns Whether variable. */
function variableReference(node:unknown):node is {tag:'variable_ref';targetId:string} {return !!node&&typeof node==='object'&&'tag' in node&&node.tag==='variable_ref';}
/** Match copied variable target. @param id Fresh binder. @param node Reference. @returns Match. */
function matchesTarget(id:string,node:unknown):boolean {return variableReference(node)&&node.targetId===id;}
/** Repeat an entry for quota verification. @param entry Snapshot. @returns Same snapshot. */
function repeatEntry(entry:ReturnType<typeof captureBlock>):ReturnType<typeof captureBlock> {return entry;}
/** Find concrete signature constructor. @param choice Inventory entry. @returns Match. */
function signatureReference(choice:{tag:string}):boolean {return choice.tag==='signature_ref';}
/** Find conjunction constructor. @param choice Inventory entry. @returns Match. */
function andChoice(choice:{tag:string}):boolean {return choice.tag==='and';}
test('reusable snapshots survive content edits and freshen owned binders',immutableReuse);
test('reusable dependencies and SOURCE authority reject atomically',rejectedReuse);
test('contextual filter and final exact transaction share rejection semantics',filterParity);
test('comparison upload decoding and exact identity fences fail closed',comparisonFences);

/** Decode a deliberately malformed UTF8 byte. @returns Nothing. */
function decodeInvalid():void {decodeModel(new Uint8Array([255]).buffer);}
/** Reject an oversized local file before decoding. @returns Nothing. */
function decodeOversized():void {decodeModel(new ArrayBuffer(32769));}

/** Surface a background mismatch and reset completed wording immediately on scope changes. @returns Nothing. */
function comparisonControlFeedback():void {
  expect(comparisonFailure('UNSUPPORTED',{reason:'background mismatch'})).toContain('different background declarations or facts');
  const state=stateFor(),selection:ComparisonSelection={mode:'blocks',leftId:state.selected!,rightId:state.selected!,scope:3,left:null,right:null};
  let notice='Comparison completed for this exact draft and selection.',cleared=false;
  /** Record the user-visible feedback produced by the real selection action. @param value Status. @returns Nothing. */
  function setNotice(value:string):void {notice=value;}
  /** Record evidence invalidation from the real selection action. @param value New evidence. @returns Nothing. */
  function setOutcome(value:unknown):void {cleared=value===null;}
  const ui={controller:{current:{current:{document:state}}},active:{current:null},live:{current:selection},current:{current:comparisonKey(state,selection)},setSelection:ignoreControl,setBusy:ignoreControl,setNotice,setOutcome} as unknown as Parameters<typeof changeComparisonSelection>[0];
  changeComparisonSelection(ui,{...selection,scope:4});
  expect(cleared).toBe(true);expect(notice).toContain('Run comparison again');expect(notice).not.toContain('completed');
  expect(ui.current.current).not.toBe(comparisonKey(state,selection));
}
/** Accept unrelated UI setters in a real selection transition fixture. @param value Setter payload. @returns Nothing. */
function ignoreControl(value:unknown):void {void value;}
test('comparison rejection reasons and changed-scope feedback remain actionable',comparisonControlFeedback);
