import {useEffect,useRef,useState} from 'react';
import type {MutableRefObject} from 'react';
import {Results} from '../Results';
import type {Controller,ViewState} from './controller';
import {publishDocument} from './controller';
import {selectNode} from './state';
import {SelectControl,type Option} from './controls';
import {analysisSnapshot,currentAnalysis,runAnalysis} from './analysis';
import type {AnalysisEvent,AnalysisSnapshot} from './analysis';
interface Outcome {readonly snapshot:AnalysisSnapshot;readonly event:AnalysisEvent}
interface AnalysisUI {
  readonly controller:Controller;readonly command:MutableRefObject<string>;
  readonly active:MutableRefObject<AbortController|null>;readonly setOutcome:(outcome:Outcome)=>void;
}
/** Cancel the browser session; server work is not claimed cancelled. @param active Current lifetime. @returns Nothing. */
function stop(active:MutableRefObject<AbortController|null>):void {active.current?.abort('view changed');active.current=null;}
/** Install cleanup for epoch/artifact/source/command changes and unmount. @param active Active run. @returns Cleanup callback. */
function lifetime(active:MutableRefObject<AbortController|null>):()=>void {return stop.bind(null,active);}
/** Start exactly one bounded session against the current accepted command. @param ui Latest refs and render consumer. @returns Nothing. */
function start(ui:AnalysisUI):void {
  stop(ui.active);
  const selected=analysisSnapshot(ui.controller.current.current.document,ui.command.current);
  if(!selected) return;
  const snapshot:AnalysisSnapshot=selected;
  const controller=new AbortController();ui.active.current=controller;
  /** Read all live bindings again before accepting each delayed result. @returns Current snapshot or no current evidence. */
  function current():AnalysisSnapshot|null {return analysisSnapshot(ui.controller.current.current.document,ui.command.current);}
  /** Avoid React updates after unmount/replacement. @param event Checked response state. @returns Nothing. */
  function emit(event:AnalysisEvent):void {if(ui.active.current===controller) ui.setOutcome({snapshot,event});}
  ui.setOutcome({snapshot,event:{kind:'waiting',data:null,notice:'Starting analysis…'}});
  void runAnalysis({token:ui.controller.token,snapshot,controller,current,emit});
}
/** Render the full bounded Results view only for a completely current accepted identity. @param props Controller/view. @returns Analysis controls and evidence. */
export function AcceptedAnalysisPanel(props:{controller:Controller;view:ViewState}) {
  const [command,setCommand]=useState(''),[outcome,setOutcome]=useState<Outcome|null>(null);
  const active=useRef<AbortController|null>(null),selected=useRef(command),state=props.view.document,options:Option[]=[];
  selected.current=command;
  for(const descriptor of state.accepted?.artifact.analysisDescriptors??[]) options.push({id:descriptor.commandKey,label:descriptor.label});
  useEffect(lifetime.bind(null,active),[state.draftId,state.epoch,state.contentGeneration,state.accepted?.artifact.artifactId,state.accepted?.documentId,state.dirty,command]);
  const ui:AnalysisUI={controller:props.controller,command:selected,active,setOutcome};
  /** Change selected command and synchronously fence older asynchronous responses. @param value Command key. @returns Nothing. */
  function changeCommand(value:string):void {
    stop(active);selected.current=value;setCommand(value);
    const current=props.controller.current.current.document;
    publishDocument(props.controller,selectNode(current,current.selected));
  }
  const snapshot=analysisSnapshot(state,command),data=outcome?.event.data;
  const current=!!data&&!!outcome&&currentAnalysis(data,outcome.snapshot,snapshot);
  return <fieldset className="document-analysis"><legend>Explore this model</legend>
    <SelectControl label="Command" value={command} options={options} onChange={changeCommand}/>
    <button disabled={!snapshot} onClick={start.bind(null,ui)}>Run analysis</button>
    {current&&data?<Results job={data.job} notice={outcome!.event.notice}/>:<AnalysisNotice outcome={outcome} dirty={state.dirty}/>}
  </fieldset>;
}
/** Keep stale or unavailable evidence separate from current result badges. @param props Last event and draft status. @returns Plain explanatory notice. */
function AnalysisNotice(props:{outcome:Outcome|null;dirty:boolean}) {
  if(props.dirty) return <p>Save your changes before analyzing this model.</p>;
  if(!props.outcome) return <p>Select a command to look for an instance or counterexample.</p>;
  if(props.outcome.event.kind==='current'||props.outcome.event.kind==='historical') return <p>Historical analysis: the model, command or selection changed. Run again for a current result.</p>;
  return <p role="status">{props.outcome.event.notice}</p>;
}
