import {useMemo,useEffect} from 'react';
import type {Controller} from './controller';
import {validate} from './controller';
import {candidate} from './state';
import type {DocumentState} from './state';
import {AdvisoryValidator} from './advisory';
/** Identify content independently of selection-only presentation changes. @param state Draft state. @returns Stable generation key. */
export function advisoryKey(state:DocumentState):string {return JSON.stringify([state.accepted?.documentId,state.draftId,state.contentGeneration,state.baseRevision,state.mode]);}
/** Validate only the exact latest content generation scheduled by this task. @param controller Current browser view. @param key Scheduled content. @param signal Lifetime cancellation. @returns Completion. */
async function validateCurrent(controller:Controller,key:string,signal:AbortSignal):Promise<void> {
  if(signal.aborted||advisoryKey(controller.current.current.document)!==key) return;
  await validate(controller,signal);
}
/** Queue a complete dirty candidate or clear queued work for holes. @param controller Latest draft ref. @param scheduler Owned serial queue. @param manual Explicit action. @returns Nothing. */
function queue(controller:Controller,scheduler:AdvisoryValidator,manual=false):void {
  const state=controller.current.current.document;
  if(!state.accepted||(!manual&&!state.dirty)) {scheduler.clearPending();return;}
  try {candidate(state);} catch {scheduler.clearPending();return;}
  const key=advisoryKey(state);
  scheduler.request({key,run:validateCurrent.bind(null,controller,key)},manual);
}
/** Create a single-owner advisory scheduler for current authority. @returns New serial diagnostic queue. */
function createScheduler():AdvisoryValidator {return new AdvisoryValidator();}
/** Register unmount cleanup without resetting on every content edit. @param scheduler Owned queue. @returns Cleanup callback. */
function cleanup(scheduler:AdvisoryValidator):()=>void {return scheduler.dispose.bind(scheduler);}
/** Debounce live code projection and share its single validation slot with the manual button. @param controller Current authority/ref. @param state Rendered content generation. @returns Manual validation action. */
export function useAdvisory(controller:Controller,state:DocumentState):()=>void {
  const scheduler=useMemo(createScheduler,[controller.token]);
  useEffect(cleanup.bind(null,scheduler),[scheduler]);
  useEffect(queue.bind(null,controller,scheduler,false),[scheduler,state.draftId,state.contentGeneration,state.baseRevision,state.mode,state.accepted?.documentId]);
  return queue.bind(null,controller,scheduler,true);
}
