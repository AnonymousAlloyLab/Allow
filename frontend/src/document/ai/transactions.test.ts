import {test,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import {initialState,editSource,selectNode} from '../state';
import type {DocumentState} from '../state';
import {emptyModule} from '../model';
import {digest} from '../api';
import {capture,apply,matching,undoEdit,identity} from './transactions';
import type {Job,Receipt} from './types';
import {AssistantReview} from './AssistantPanel';
import {AssistantSession,INITIAL} from './session';
/** Build a source draft with explicit accepted knowledge. @returns Independent authored draft. */
function draft():DocumentState {const state=initialState();return {...editSource(state,'// original\nsig Person {}'),accepted:{documentId:'server:document',revision:1,headRevision:1,provenance:null,artifact:{artifactId:'artifact',mode:'BLOCK_SUPPORTED',source:'sig Person {}',sourceHash:'base',module:{...emptyModule(),nodes:[]},occurrences:[],trivia:[],analysisDescriptors:[],policyVersion:'policy',dependencyHash:'dependency'}},baseRevision:1};}
/** Construct an expiring exact local receipt. @returns Receipt. */
async function receipt():Promise<Receipt> {return {receiptId:'receipt',jobId:'job',binding:'binding',proposalHash:'proposal',source:'sig Person {}\npred p {some Person}',sourceHash:await digest('sig Person {}\npred p {some Person}'),expiresAt:new Date(Date.now()+5000).toISOString()};}
/** Check apply/undo as isolated draft transactions with no durable mutation. @returns Completion. */
async function applyUndo():Promise<void> {
  const original=draft(),snapshot=capture(original),received=await receipt(),consumed=new Set<string>(),transaction=apply(original,snapshot,received,consumed)!;
  expect(transaction.document.accepted).toBe(original.accepted);expect(transaction.document.pending).toBeNull();expect(transaction.document.mode).toBe('SOURCE');
  expect(transaction.document.source).toBe(received.source);expect(transaction.document.epoch).toBeGreaterThan(original.epoch);
  expect(apply(original,snapshot,received,consumed)).toBeNull();
  const restored=undoEdit(transaction.document,transaction.undo)!;
  expect(restored.source).toBe(original.source);expect(restored.slotObligations).toBe(original.slotObligations);expect(restored.copies).toBe(original.copies);
  expect(restored.epoch).toBeGreaterThan(transaction.document.epoch);expect(restored.accepted).toBe(original.accepted);
  expect(undoEdit(restored,transaction.undo)).toBeNull();
}
/** Reject stale epochs, pending save, expired receipts and intervening undo edits. @returns Completion. */
async function staleReceipt():Promise<void> {
  const original=draft(),snapshot=capture(original),received=await receipt();
  expect(apply(selectNode(original,null),snapshot,received,new Set())).toBeNull();
  expect(apply(original,snapshot,{...received,expiresAt:new Date(0).toISOString()},new Set())).toBeNull();
  const transaction=apply(original,snapshot,received,new Set())!;
  expect(undoEdit(editSource(transaction.document,'sig Changed {}'),transaction.undo)).toBeNull();
  expect(identity(original)).not.toBe(identity(selectNode(original,null)));
}
/** Recompute exact receipt source hashes and compare the reviewed proposal. @returns Completion. */
async function receiptBinding():Promise<void> {
  const received=await receipt(),job:Job={id:'job',status:'REVIEW_READY',binding:'binding',attempt:1,beforeSource:null,expiresAt:received.expiresAt,payload:null,payloadHash:null,model:'gpt-6.1-sol',termsVersion:'terms',code:null,proposal:{source:received.source,sourceHash:received.sourceHash,proposalHash:'proposal',projection:'BLOCK_SUPPORTED',explanation:'suggestion'}};
  expect(await matching(received,job)).toBe(true);expect(await matching({...received,source:'substituted'},job)).toBe(false);expect(await matching({...received,binding:'foreign'},job)).toBe(false);
}
/** Ensure provider text is escaped and explanations cannot apply. @returns Nothing. */
function inertReview():void {
  const original=draft(),controller={token:'authority',current:{current:{document:original,documents:[],target:0,history:null,direction:'UNDO' as const}},set:ignore},session=new AssistantSession(controller,ignore);
  const job:Job={id:'job',status:'SUGGESTION',binding:'binding',expiresAt:new Date(Date.now()+5000).toISOString(),attempt:1,beforeSource:null,payload:null,payloadHash:null,model:'model',termsVersion:'terms',code:null,proposal:{source:'',sourceHash:'',proposalHash:'',projection:'AI_SUGGESTION',explanation:'<img src=x onerror=alert(1)>'}};
  const markup=renderToStaticMarkup(createElement(AssistantReview,{view:{...INITIAL,job},session,online:true}));
  expect(markup).toContain('&lt;img');expect(markup).not.toContain('<img');expect(markup).not.toContain('Apply to draft');expect(markup).not.toContain('Save version');
}
/** Ignore an unused test state publication. @returns Nothing. */
function ignore():void {}
test('AI apply and dedicated undo retain saved history and exact previous content',applyUndo);
test('stale and expired receipts and intervening content edits reject application or undo',staleReceipt);
test('receipt identity and exact source digest match current reviewed proposal',receiptBinding);
test('assistant renders hostile model text inertly and explanation has no Apply',inertReview);
