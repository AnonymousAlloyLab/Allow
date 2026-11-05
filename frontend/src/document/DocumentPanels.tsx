import {useState} from 'react';
import type {ChangeEvent,KeyboardEvent} from 'react';
import type {Controller,ViewState} from './controller';
import {create,openDocument,refresh,save,transmit,previewHistory,restore,changeSource,announce,publishDocument} from './controller';
import {TextControl,SelectControl,type Option} from './controls';
import {candidate,selectNode} from './state';
import {AcceptedAnalysisPanel} from './AcceptedAnalysisPanel';
/** Render model navigation and explicit create/open actions. @param props Controller/view. @returns Native model controls. */
export function DocumentNavigation(props:{controller:Controller;view:ViewState}) {
  const [title,setTitle]=useState('Untitled model'),[id,setId]=useState(''),options:Option[]=[];
  for(const item of props.view.documents) options.push({id:item.documentId,label:item.title});
  /** Create a model with a recoverable pending request. @returns Nothing. */
  function add():void {void create(props.controller,title);}
  /** Explicitly replace the visible draft with a selected saved model. @returns Nothing. */
  function open():void {if(id) void openDocument(props.controller,id);}
  /** Refresh the model list. @returns Nothing. */
  function reload():void {void refresh(props.controller);}
  return <section aria-label="Documents" className="document-navigation">
    <TextControl label="New model name" value={title} onChange={setTitle}/>
    <button disabled={!!props.view.document.pending} onClick={add}>Create model</button>
    <SelectControl label="Your models" value={id} options={options} onChange={setId}/>
    <button disabled={!id||!!props.view.document.pending} onClick={open}>{props.view.document.dirty?'Open and discard unsaved changes':'Open model'}</button>
    <button onClick={reload}>Refresh</button>
  </section>;
}
/** Render check/save/recovery actions with advanced request details collapsed. @param props Controller/view and shared validation slot. @returns Draft actions. */
export function CommitControls(props:{controller:Controller;view:ViewState;onValidate:()=>void}) {
  const state=props.view.document;
  let complete=true;
  try {candidate(state);} catch {complete=false;}
  /** Save a complete candidate as a new version. @returns Nothing. */
  function commit():void {void save(props.controller);}
  /** Recover the exact pending save. @returns Nothing. */
  function retry():void {if(state.pending) void transmit(props.controller,state.pending);}
  return <section aria-label="Draft acceptance" className="document-savebar">
    <strong>{state.dirty?'Unsaved changes':'Saved version'}</strong>
    <button disabled={!complete||!state.accepted} onClick={props.onValidate}>Check model</button>
    <button disabled={!complete||!state.accepted||!!state.pending} onClick={commit}>Save version</button>
    {state.pending&&<><span>Waiting for save confirmation.</span><button onClick={retry}>Recover save</button></>}
    <details><summary>Save details</summary><p>Draft mode: {state.mode}; based on version {state.baseRevision}.</p>
      {state.pending&&<p>Pending request: {state.pending.key}. Recovery resends identical bytes; a network error does not establish rollback.</p>}
      <p>Pending model data stays in this tab. After restarting your browser, inspect the saved model and version history before resubmitting changes.</p>
    </details>
  </section>;
}
/** Render explicitly previewed historical targets in an advanced disclosure. @param props Controller/view. @returns Append-only version navigation. */
export function HistoryPanel(props:{controller:Controller;view:ViewState}) {
  const [target,setTarget]=useState('0'),[direction,setDirection]=useState('UNDO');
  /** Preview a selected immutable version. @returns Nothing. */
  function preview():void {void previewHistory(props.controller,Number(target),direction==='REDO'?'REDO':'UNDO');}
  /** Save previewed content as a fresh version. @returns Nothing. */
  function apply():void {void restore(props.controller);}
  const history=props.view.history,state=props.view.document;
  return <details className="document-history"><summary>Version history and provenance</summary>
    <p>Saved version {state.accepted?.headRevision??'none'}. Undo/Redo creates a new version; earlier versions remain unchanged.</p>
    <TextControl label="Version to restore" value={target} onChange={setTarget}/>
    <SelectControl label="Direction" value={direction} options={[{id:'UNDO',label:'Undo'},{id:'REDO',label:'Redo'}]} onChange={setDirection}/>
    <button disabled={!state.accepted} onClick={preview}>Preview Undo/Redo target</button>
    {history&&<><p>Target version {history.revision}</p><pre>{history.artifact.source}</pre>
      <button disabled={!!state.pending} onClick={apply}>{state.dirty?'Replace unsaved changes with this version':'Restore as a new version'}</button>
      <p>Artifact {history.artifact.artifactId}; navigation cursor {state.historyCursor??'none'}.</p>
    </>}
  </details>;
}
/** Render live Alloy projection beside blocks, preserving raw edits independently. @param props Controller/view. @returns Source and accepted evidence. */
export function SourcePanel(props:{controller:Controller;view:ViewState;online?:boolean}) {
  const state=props.view.document,source=state.mode==='SOURCE'?state.source:state.preview??state.historicalPreview??state.source;
  /** Keep raw source edits separate from the saved version. @param event Input. @returns Nothing. */
  function change(event:ChangeEvent<HTMLTextAreaElement>):void {changeSource(props.controller,event.target.value);}
  /** Invalidate source-selection evidence without requesting another parse. @returns Nothing. */
  function selection():void {const current=props.controller.current.current.document;publishDocument(props.controller,selectNode(current,current.selected));}
  /** Explicitly resume the prior separate block candidate. @returns Nothing. */
  function blocks():void {publishDocument(props.controller,{...selectNode(state,state.selected),mode:'BLOCK_SUPPORTED',dirty:true,contentGeneration:state.contentGeneration+1,clipboard:null,notice:'Block editing resumed. Check and save when ready.'});}
  return <section aria-label="Source and accepted artifact" className="document-source">
    <h2>Alloy source</h2>
    <p>{state.mode==='SOURCE'?'Editing source directly.':state.preview?'Live block preview.':state.dirty?'Previous source preview; complete blocks are checked automatically.':'Source for the saved model.'}</p>
    <label>Source<textarea id="document-source-draft" value={source} onChange={change} onSelect={selection} spellCheck={false}/></label>
    {state.mode==='SOURCE'&&<button disabled={!state.accepted?.artifact.module} onClick={blocks}>Resume block editing</button>}
    {props.online===false&&<p>Copy the visible source or export it below. A prior preview may not include unfinished block edits.</p>}
    {props.online===false&&<><button onClick={copySource.bind(null,props.controller,source)}>Copy visible source</button><button onClick={downloadSource.bind(null,source)}>Export visible source</button></>}
    <AcceptedAnalysisPanel controller={props.controller} view={props.view} online={props.online!==false}/>
    <AcceptedPanel controller={props.controller} view={props.view}/>
  </section>;
}
/** Copy visible text and report browser clipboard denial without losing the draft. @param controller Current view. @param source Visible source. @returns Completion. */
async function copySource(controller:Controller,source:string):Promise<void> {
  try {await navigator.clipboard.writeText(source);announce(controller,'Visible source copied.');}
  catch {announce(controller,'Clipboard unavailable. Select the source text and copy it manually.');}
}
/** Download exactly the currently displayed source text. @param source Visible text, possibly a prior preview. @returns Nothing. */
function downloadSource(source:string):void {
  const url=URL.createObjectURL(new Blob([source],{type:'text/plain;charset=utf-8'})),link=document.createElement('a');
  link.href=url;link.download='allow-source.als';link.click();URL.revokeObjectURL(url);
}
/** Render immutable source/provenance in a disclosure with freshness-gated map navigation. @param props Controller/view. @returns Saved-version details. */
function AcceptedPanel(props:{controller:Controller;view:ViewState}) {
  const state=props.view.document,accepted=state.accepted,locations=[];
  if(!accepted) return null;
  /** Recheck all presentation bindings before selecting a saved source interval. @param occurrenceId Map identity. @returns Nothing. */
  function navigate(occurrenceId:string):void {
    const current=props.controller.current.current.document,artifact=current.accepted?.artifact;
    if(!artifact||current.dirty||current.epoch!==state.epoch||current.source!==artifact.source||artifact.artifactId!==accepted!.artifact.artifactId) {announce(props.controller,'This location belongs to an earlier version.');return;}
    for(const span of artifact.occurrences) if(span.occurrenceId===occurrenceId) {
      const input=document.getElementById('document-source-draft') as HTMLTextAreaElement|null;
      input?.focus();input?.setSelectionRange(span.startUtf16,span.endUtf16);return;
    }
  }
  for(const span of accepted.artifact.occurrences) locations.push(<button key={span.occurrenceId} disabled={state.dirty} onClick={navigate.bind(null,span.occurrenceId)}>{span.role} {span.startUtf16}–{span.endUtf16}</button>);
  return <details><summary>Saved source and provenance · version {accepted.revision}</summary>
    <p>{accepted.artifact.mode==='TEXT_ONLY'?'Text-only model':'Block-supported model'}</p><pre>{accepted.artifact.source}</pre>
    <div aria-label="Accepted occurrence locations">{locations}</div>
    <p>Artifact {accepted.artifact.artifactId}; policy {accepted.artifact.policyVersion}; source hash {accepted.artifact.sourceHash}.</p>
    <details><summary>Comments and orphan notices</summary><pre>{JSON.stringify(accepted.artifact.trivia,null,2)}</pre></details>
  </details>;
}
/** Route block history shortcuts without intercepting native text editing. @param controller Current view. @param event Keyboard event. @returns Nothing. */
export function historyShortcut(controller:Controller,event:KeyboardEvent):void {
  const target=event.target as HTMLElement;
  if(['INPUT','TEXTAREA','SELECT'].includes(target.tagName)||target.isContentEditable||!target.closest('.document-blocks')) return;
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z') {
    event.preventDefault();const state=controller.current.current.document,cursor=state.historyCursor??state.accepted?.headRevision??0;
    void previewHistory(controller,Math.max(0,cursor+(event.shiftKey?1:-1)),event.shiftKey?'REDO':'UNDO');
  }
}
