import {captureBlock,libraryLimit,type SavedBlock} from './document/blockLibrary';
import {insertSavedBlock} from './document/controller';
import {BlockComparisonPanel} from './document/BlockComparisonPanel';
import {useEffect,useRef,useState} from 'react';
import {initialState} from './document/state';
import type {Controller,ViewState} from './document/controller';
import {contentSnapshot} from './document/gesture';
import {refresh,changeModule,select,insert,copy,pasteClipboard,removeSelected,dropNode,announce,cancelInteraction,previewGesture,commitGesture} from './document/controller';
import {DeclarationEditor} from './document/DeclarationEditor';
import {ExpressionEditor} from './document/ExpressionEditor';
import {DocumentNavigation,CommitControls,HistoryPanel,SourcePanel,historyShortcut} from './document/DocumentPanels';
import {checkModule} from './document/model';
import {useAdvisory} from './document/useAdvisory';
import {AssistantPanel} from './document/ai/AssistantPanel';
import {useOracleParity} from './document/useOracleParity';
import {BlockComparisonResults} from './document/BlockComparisonResults';
import {OracleParityPanel} from './document/OracleParityPanel';
import type {ParityFrame} from './document/oracleParity';
import './document/styles.css';
/** Create an isolated authority-bound controller. @param token Fresh launch authority. @param online Whether server actions are available. @returns View and actions. */
function useController(token:string,online:boolean):{view:ViewState;controller:Controller} {
  const [view,set]=useState<ViewState>({document:initialState(),documents:[],target:0,history:null,direction:'UNDO'});
  const current=useRef(view),controller:Controller={token,current,set};
  /** Load authenticated inventory on authority change. @returns Nothing. */
  function initialize():void {if(online) void refresh(controller);}
  useEffect(initialize,[token,online]);
  return {view,controller};
}
/** Render the complete isolated typed-document workbench. @param props Current bearer held in memory. @returns Document editor. */
export function DocumentWorkbench(props:{token:string;online?:boolean}) {
  const {view,controller}=useController(props.token,props.online!==false);
  return <main className="document-workbench" onKeyDown={props.online===false?undefined:historyShortcut.bind(null,controller)}>
    <header>
      <h1>Allow</h1>
      <p>Build an Alloy model with blocks, edit its source, and explore examples.</p>
    </header>
    <p role="status" aria-live="polite">{view.document.notice}</p>
    <fieldset disabled={props.online===false}><DocumentNavigation controller={controller} view={view}/></fieldset>
    {view.document.accepted&&<DocumentBody key={`document:${props.token}:${view.document.accepted.documentId}`} controller={controller} view={view} online={props.online!==false}/>}
  </main>;
}
/** Render current draft surfaces separately from immutable history and source. @param props Controller and view. @returns Document panels. */
export function DocumentBody(props:{controller:Controller;view:ViewState;online:boolean}) {
  const {controller,view}=props,state=view.document,diagnostics=[];
  const onValidate=useAdvisory(controller,state,props.online);
  for(const item of checkModule(state.module,state.slotObligations).diagnostics) diagnostics.push(<li key={`${item.nodeId}:${item.message}`}>{item.message}</li>);
  for(const item of [...state.rejectionDiagnostics,...state.validation?.diagnostics??[]]) diagnostics.push(<li key={`server:${item.nodeId}:${item.message}`}>{item.message}</li>);
  return <>
    <fieldset disabled={!props.online}><CommitControls controller={controller} view={view} onValidate={onValidate}/></fieldset>
    <div className="document-layout">
      <BlockWorkspace key={`workspace:${controller.token}:${state.accepted?.documentId}`} controller={controller} view={view} online={props.online}/>
      <p className="source-authority" role="status">{state.mode==='SOURCE'?'Source draft is authoritative. Save or reopen before using visual blocks.':'Unsaved visual edits remain drafts until Save.'}</p>
      <BlockComparisonPanel key={`comparison:${controller.token}:${state.accepted?.documentId}`} controller={controller} view={view} online={props.online}/>
      <details className="support-panel"><summary>Declarations and model structure</summary><fieldset disabled={state.mode==='SOURCE'}><DeclarationEditor module={state.module} onChange={changeModule.bind(null,controller)} onSelect={select.bind(null,controller)}/></fieldset></details>
      <details className="support-panel"><summary>Alloy source and saved model</summary><SourcePanel controller={controller} view={view} online={props.online}/></details>
    </div>
    <AssistantPanel controller={controller} online={props.online}/>
    <section aria-label="Draft diagnostics"><h2>Specific diagnostics</h2><ul>{diagnostics}</ul></section>
    <fieldset disabled={!props.online}><HistoryPanel controller={controller} view={view}/></fieldset>
  </>;
}
/** Bind full expression interactions to the current immutable controller snapshot. @param props View and actions. @returns Typed forest editor. */
function ExpressionSurface(props:{controller:Controller;view:ViewState;parityFrame:ParityFrame|null}) {
  const {controller,view}=props,state=view.document;
  const [entries,setEntries]=useState<readonly SavedBlock[]>([]);
  /** Save immutable content without mutating the draft. @param name Display name. @returns Nothing. */
  function capture(name:string):void {try {const entry=captureBlock(controller.current.current.document,name),next=[...entries,entry],error=libraryLimit(next);if(error) throw new Error(error);setEntries(next);announce(controller,'Saved reusable snapshot in this document session.');} catch(error) {announce(controller,error instanceof Error?error.message:'Capture unavailable.');}}
  /** Rename a shelf snapshot without changing model content. @param entry Current entry. @param name New label. @returns Nothing. */
  function rename(entry:SavedBlock,name:string):void {if(!name.trim()||name.length>64) {announce(controller,'Use a block name of 1–64 characters.');return;}const next=entries.map(renameEntry.bind(null,entry.id,name.trim())),error=libraryLimit(next);if(error) announce(controller,error);else setEntries(next);}
  /** Remove only the selected shelf entry. @param entry Current snapshot. @returns Nothing. */
  function remove(entry:SavedBlock):void {setEntries(entries.filter(keepEntry.bind(null,entry.id)));}
  /** Read the latest controller identity when a gesture starts. @returns Current content binding. */
  function currentSnapshot():string {return contentSnapshot(controller.current.current.document);}
  return <ExpressionEditor parityFrame={props.parityFrame}
    snapshot={JSON.stringify([state.accepted?.documentId,state.baseRevision,state.draftId,state.contentGeneration])}
    entries={entries} onCapture={capture} onRename={rename} onRemove={remove} onSaved={insertSavedBlock.bind(null,controller)}
    module={state.module} slotObligations={state.slotObligations} selected={state.selected}
    onSelect={select.bind(null,controller)}
    onInsert={insert.bind(null,controller)}
    onClipboard={copy.bind(null,controller)}
    onPaste={pasteClipboard.bind(null,controller)}
    onDelete={removeSelected.bind(null,controller)}
    onCancel={cancelInteraction.bind(null,controller)}
    onDropNode={dropNode.bind(null,controller)}
    onNotice={announce.bind(null,controller)}
    onSnapshot={currentSnapshot}
    onPreview={previewGesture.bind(null,controller)}
    onGesture={commitGesture.bind(null,controller)}/>;
}

/** Rename only a matching shelf entry. @param id Identity. @param name Label. @param entry Current entry. @returns Updated entry. */
function renameEntry(id:string,name:string,entry:SavedBlock):SavedBlock {return entry.id===id?{...entry,name}:entry;}
/** Retain all shelf entries except the removed identity. @param id Removed identity. @param entry Candidate. @returns Whether retained. */
function keepEntry(id:string,entry:SavedBlock):boolean {return entry.id!==id;}

/** Share exact parity evidence between controls and the current predicate forest. @param props Authority-bound workspace. @returns Controls and visual editor. */
function BlockWorkspace(props:{controller:Controller;view:ViewState;online:boolean}) {
  const ui=useOracleParity(props.controller,props.online);
  return <div className="block-workspace"><OracleParityPanel ui={ui} module={props.view.document.module} online={props.online}/><fieldset className="visual-authority" disabled={props.view.document.mode==='SOURCE'}><ExpressionSurface controller={props.controller} view={props.view} parityFrame={ui.frame}/></fieldset>{ui.data&&ui.frame?.verdict!=='neutral'&&<details className="parity-evidence"><summary>Parity evidence</summary><BlockComparisonResults data={ui.data}/></details>}</div>;
}
