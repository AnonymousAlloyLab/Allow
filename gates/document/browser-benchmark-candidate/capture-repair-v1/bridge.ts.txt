import {useLayoutEffect,useRef} from 'react';
import type {Controller,ViewState} from '../src/document/controller';

export interface Committed {readonly mount:object;readonly controller:Controller;readonly view:ViewState;readonly sequence:number}
let latest:Committed|null=null;
let listener:((value:Committed)=>void)|null=null;
let counter=0;
/** Record a commit from the rendered view, never from the mutable controller ref. @param mount Instance identity. @param controller Actual actions. @param view Committed view. @returns Nothing. */
export function committed(mount:object,controller:Controller,view:ViewState):void {
  latest={mount,controller,view,sequence:++counter};listener?.(latest);
}
/** Clear a mounted instance during React cleanup. @param mount Instance identity. @returns Nothing. */
export function unmounted(mount:object):void {if(latest?.mount===mount) latest=null;}
/** Inspect latest committed view. @returns Last committed view if mounted. */
export function current():Committed|null {return latest;}
/** Register exactly one pending commit observer. @param next Observer or null. @returns Nothing. */
export function observe(next:((value:Committed)=>void)|null):void {listener=next;}

/** Observe committed React views and remove the instance on unmount. @param controller Actual actions. @param view Rendered view. @returns Nothing. */
export function useBenchmarkCommit(controller:Controller,view:ViewState):void {
  const mount=useRef<object>({});
  /** Publish only from the commit phase. @returns Nothing. */
  function publish():void {committed(mount.current,controller,view);}
  /** Register mount cleanup. @returns Cleanup callback. */
  function lifetime():()=>void {
    /** Mark the instance unavailable after unmount. @returns Nothing. */
    function cleanup():void {unmounted(mount.current);}
    return cleanup;
  }
  useLayoutEffect(publish);useLayoutEffect(lifetime,[]);
}
