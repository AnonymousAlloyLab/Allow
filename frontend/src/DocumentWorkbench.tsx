import {captureBlock,libraryLimit,type SavedBlock} from './document/blockLibrary';
import {insertSavedBlock} from './document/controller';
import {BlockComparisonPanel} from './document/BlockComparisonPanel';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {initialState} from './document/state';
import type {Controller,ViewState} from './document/controller';
import {contentSnapshot} from './document/gesture';
import {refresh,changeModule,changeSource,select,insert,copy,pasteClipboard,removeSelected,dropNode,announce,cancelInteraction,previewGesture,commitGesture} from './document/controller';
import {StructurePanel} from './document/StructurePanel';
import {DeclarationEditor} from './document/DeclarationEditor';
import {addDeclaration} from './document/declarations';
import type {RootTag} from './document/CanvasParts';
import {ExpressionEditor} from './document/ExpressionEditor';
import {DocumentNavigation,CommitControls,HistoryPanel,SourcePanel,historyShortcut} from './document/DocumentPanels';
import {AcceptedAnalysisPanel} from './document/AcceptedAnalysisPanel';
import {checkModule} from './document/model';
import {useAdvisory} from './document/useAdvisory';
import {AssistantPanel} from './document/ai/AssistantPanel';
import {useOracleParity} from './document/useOracleParity';
import {BlockComparisonResults} from './document/BlockComparisonResults';
import {OracleParityPanel} from './document/OracleParityPanel';
import type {ParityFrame} from './document/oracleParity';
import type {DocumentState} from './document/state';
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
    <h1 className="sr-only">Allow model editor</h1>
    <fieldset className="model-bar-frame" disabled={props.online===false}><DocumentNavigation controller={controller} view={view}/></fieldset>
    {view.document.accepted?<DocumentBody key={`document:${props.token}:${view.document.accepted.documentId}`} controller={controller} view={view} online={props.online!==false}/>:<WelcomePanel/>}
    <p className="status-bar" role="status" aria-live="polite"><span className="status-dot" aria-hidden="true"/>{view.document.notice}</p>
  </main>;
}
/** Explain the three-step workflow before any model is open. @returns Orientation panel. */
function WelcomePanel() {
  return <section className="welcome" aria-label="Getting started"><h2>Start modeling</h2><p>Allow is a visual editor for Alloy. Every block you place is explicit Alloy source that you can read, edit and run.</p>
    <ol className="welcome-steps">
      <li><strong>Create or open a model</strong><span>Name a new model above and press Create model, or pick one from Your models.</span></li>
      <li><strong>Build with blocks</strong><span>Drag blocks from the palette onto dashed empty slots, or select a slot and click a block.</span></li>
      <li><strong>Check, save and run</strong><span>Check model validates the draft, Save version stores it, and Run analysis searches for instances or counterexamples.</span></li>
    </ol></section>;
}
/** Collect local and server diagnostics for the draft; while text is authoritative the block draft is not checked locally. @param state Current draft. @returns Rendered list items. */
function draftDiagnostics(state:DocumentState):ReactNode[] {
  const diagnostics:ReactNode[]=[];
  if(state.mode!=='SOURCE') for(const item of checkModule(state.module,state.slotObligations).diagnostics) diagnostics.push(<li key={`${item.nodeId}:${item.message}`}>{item.message}</li>);
  for(const item of [...state.rejectionDiagnostics,...state.validation?.diagnostics??[]]) diagnostics.push(<li key={`server:${item.nodeId}:${item.message}`}>{item.message}</li>);
  return diagnostics;
}
/** Render current draft surfaces separately from immutable history and source. @param props Controller and view. @returns Document panels. */
export function DocumentBody(props:{controller:Controller;view:ViewState;online:boolean}) {
  const {controller,view}=props,state=view.document,[open,setCode]=useState(false),diagnostics=draftDiagnostics(state),code=open||!props.online;
  const onValidate=useAdvisory(controller,state,props.online),title=view.documents.find(matchesDocument.bind(null,state.accepted?.documentId))?.title;
  /** Show or hide the explicit Alloy source beside the canvas. @returns Nothing. */
  function toggleCode():void {setCode(!open);}
  return <>
    <div className="document-header">
      <fieldset disabled={!props.online}><CommitControls controller={controller} view={view} onValidate={onValidate} title={title} problems={diagnostics.length}/></fieldset>
      {props.online&&<button type="button" className="code-toggle" aria-pressed={code} aria-controls="alloy-source-drawer" onClick={toggleCode}><span aria-hidden="true">{'</>'}</span> {code?'Hide Alloy source':'Show Alloy source'}</button>}
    </div>
    <p className={`source-authority${state.mode==='SOURCE'?' is-source':''}`} role="status">{state.mode==='SOURCE'?'You are editing Alloy text directly, so blocks are locked. Save the text, or choose Resume block editing in the source panel.':'Block edits stay a draft until you choose Save version.'}</p>
    <div className={`document-layout${code?' with-code':''}`}>
      <BlockWorkspace key={`workspace:${controller.token}:${state.accepted?.documentId}`} controller={controller} view={view} online={props.online}/>
      <aside id="alloy-source-drawer" className="code-drawer" aria-label="Alloy source panel" hidden={!code}><SourcePanel controller={controller} view={view} online={props.online}/></aside>
    </div>
    <SupportPanels {...props} diagnostics={diagnostics}/>
  </>;
}
/** Render analysis, diagnostics, comparison, declarations, assistant and history below the canvas. @param props Controller, view and collected diagnostics. @returns Labeled support panels. */
function SupportPanels(props:{controller:Controller;view:ViewState;online:boolean;diagnostics:ReactNode[]}) {
  const {controller,view}=props,state=view.document,count=props.diagnostics.length;
  return <div className="support-stack">
    <section className="run-panel" aria-label="Run analysis"><AcceptedAnalysisPanel controller={controller} view={view} online={props.online}/></section>
    <details className="support-panel" open={count>0||undefined}><summary><span className="support-title">Problems</span><span className={`support-count${count?' has-problems':''}`}>{count?`${count} to fix`:'None'}</span><span className="support-hint">Type, scope and server diagnostics for this draft</span></summary>
      <section aria-label="Draft diagnostics"><h2>Specific diagnostics</h2>{count?<ul className="diagnostic-list">{props.diagnostics}</ul>:<p className="empty-note">No problems found in this draft.</p>}</section></details>
    <details className="support-panel"><summary><span className="support-title">Compare alternatives</span><span className="support-hint">Find bounded instances where two formulas or predicates differ</span></summary>
      <BlockComparisonPanel key={`comparison:${controller.token}:${state.accepted?.documentId}`} controller={controller} view={view} online={props.online}/></details>
    <details className="support-panel" id="declarations-panel"><summary><span className="support-title">Declarations and model structure</span><span className="support-hint">Signatures, fields, predicates, facts, assertions and commands</span></summary>
      <fieldset disabled={state.mode==='SOURCE'}><DeclarationEditor module={state.module} onChange={changeModule.bind(null,controller)} onSelect={select.bind(null,controller)}/></fieldset></details>
    <AssistantPanel controller={controller} online={props.online}/>
    <fieldset className="history-frame" disabled={!props.online}><HistoryPanel controller={controller} view={view}/></fieldset>
  </div>;
}
/** Match the open document summary for its visible title. @param id Open document identity. @param item Summary candidate. @returns Exact identity match. */
function matchesDocument(id:string|undefined,item:{readonly documentId:string}):boolean {return item.documentId===id;}
/** Bind full expression interactions to the current immutable controller snapshot. @param props View and actions. @returns Typed forest editor. */
function ExpressionSurface(props:{controller:Controller;view:ViewState;parityFrame:ParityFrame|null}) {
  const {controller,view}=props,state=view.document;
  const [entries,setEntries]=useState<readonly SavedBlock[]>([]);
  /** Save immutable content without mutating the draft. @param name Display name. @returns Nothing. */
  function capture(name:string):void {try {const entry=captureBlock(controller.current.current.document,name),next=[...entries,entry],error=libraryLimit(next);if(error) throw new Error(error);setEntries(next);announce(controller,`Saved “${entry.name}” to your reusable blocks for this document session.`);} catch(error) {announce(controller,error instanceof Error?error.message:'Capture unavailable.');}}
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
    onAdd={addRoot.bind(null,controller)}
    onSnapshot={currentSnapshot}
    onPreview={previewGesture.bind(null,controller)}
    onGesture={commitGesture.bind(null,controller)}/>;
}

/** Add a declaration from the canvas through the same path as the declarations editor. @param controller Current draft. @param tag Declaration kind. @returns Nothing. */
function addRoot(controller:Controller,tag:RootTag):void {changeModule(controller,addDeclaration(controller.current.current.document.module,tag));}
/** Write a structure change into the authoritative source draft and say what changed. @param controller Current draft. @param source New text. @param notice Status text. @returns Nothing. */
function editText(controller:Controller,source:string,notice:string):void {changeSource(controller,source);announce(controller,notice);}
/** Rename only a matching shelf entry. @param id Identity. @param name Label. @param entry Current entry. @returns Updated entry. */
function renameEntry(id:string,name:string,entry:SavedBlock):SavedBlock {return entry.id===id?{...entry,name}:entry;}
/** Retain all shelf entries except the removed identity. @param id Removed identity. @param entry Candidate. @returns Whether retained. */
function keepEntry(id:string,entry:SavedBlock):boolean {return entry.id!==id;}

/** Share exact parity evidence between controls and the current predicate forest. @param props Authority-bound workspace. @returns Visual editor followed by its parity controls. */
function BlockWorkspace(props:{controller:Controller;view:ViewState;online:boolean}) {
  const ui=useOracleParity(props.controller,props.online);
  const state=props.view.document;
  return <div className="block-workspace"><StructurePanel module={state.module} source={state.source} textMode={state.mode==='SOURCE'} onModule={changeModule.bind(null,props.controller)} onSource={editText.bind(null,props.controller)} onNotice={announce.bind(null,props.controller)}/><fieldset className="visual-authority" disabled={props.view.document.mode==='SOURCE'}><ExpressionSurface controller={props.controller} view={props.view} parityFrame={ui.frame}/></fieldset><OracleParityPanel ui={ui} module={props.view.document.module} online={props.online}/>{ui.data&&ui.frame?.verdict!=='neutral'&&<details className="parity-evidence"><summary>Parity evidence</summary><BlockComparisonResults data={ui.data}/></details>}</div>;
}
