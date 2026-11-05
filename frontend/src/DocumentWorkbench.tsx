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
    {view.document.accepted&&<DocumentBody controller={controller} view={view} online={props.online!==false}/>}
  </main>;
}
/** Render current draft surfaces separately from immutable history and source. @param props Controller and view. @returns Document panels. */
function DocumentBody(props:{controller:Controller;view:ViewState;online:boolean}) {
  const {controller,view}=props,state=view.document,diagnostics=[];
  const onValidate=useAdvisory(controller,state,props.online);
  for(const item of checkModule(state.module,state.slotObligations).diagnostics) diagnostics.push(<li key={`${item.nodeId}:${item.message}`}>{item.message}</li>);
  for(const item of [...state.rejectionDiagnostics,...state.validation?.diagnostics??[]]) diagnostics.push(<li key={`server:${item.nodeId}:${item.message}`}>{item.message}</li>);
  return <>
    <fieldset disabled={!props.online}><CommitControls controller={controller} view={view} onValidate={onValidate}/></fieldset>
    <div className="document-layout">
      <DeclarationEditor module={state.module} onChange={changeModule.bind(null,controller)} onSelect={select.bind(null,controller)}/>
      <ExpressionSurface controller={controller} view={view}/>
      <SourcePanel controller={controller} view={view} online={props.online}/>
    </div>
    <section aria-label="Draft diagnostics"><h2>Specific diagnostics</h2><ul>{diagnostics}</ul></section>
    <fieldset disabled={!props.online}><HistoryPanel controller={controller} view={view}/></fieldset>
  </>;
}
/** Bind full expression interactions to the current immutable controller snapshot. @param props View and actions. @returns Typed forest editor. */
function ExpressionSurface(props:{controller:Controller;view:ViewState}) {
  const {controller,view}=props,state=view.document;
  /** Read the latest controller identity when a gesture starts. @returns Current content binding. */
  function currentSnapshot():string {return contentSnapshot(controller.current.current.document);}
  return <ExpressionEditor
    snapshot={JSON.stringify([state.accepted?.documentId,state.baseRevision,state.draftId,state.contentGeneration])}
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
