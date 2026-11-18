import {useState} from 'react';
import {DocumentWorkbench} from './DocumentWorkbench';
import {CorpusPanel} from './CorpusPanel';
type View='editor'|'library';

/** Keep the editor mounted while switching to the private predicate library.
 * @param props In-memory local launch authority.
 * @returns The document editor and locally stored retrieval library.
 */
export function AllowApp(props:{token:string;anonymous?:boolean;online?:boolean}) {
  const [view,setView]=useState<View>('editor'),library=!props.anonymous;
  return <div className="allow-app">
    <header className="app-bar">
      <a className="app-brand" href="#editor" onClick={showEditor.bind(null,setView)}><span className="app-mark" aria-hidden="true">A</span><span><strong>Allow</strong><small>Alloy modeling workbench</small></span></a>
      <nav className="app-views" aria-label="Workspace sections">
        <ViewButton view="editor" current={view} onSelect={setView} label="Model editor"/>
        {library&&<ViewButton view="library" current={view} onSelect={setView} label="Predicate library"/>}
      </nav>
      <div className="app-meta">
        <span className="app-session">{props.anonymous?'Temporary workspace':'Private local session'}</span>
        <a className="app-link" href="/request-ai-access" target="_blank" rel="noopener noreferrer" title="Opens in a new tab so this session and any unsaved draft stay open">Request AI access ↗</a>
      </div>
    </header>
    <div id="editor" hidden={view!=='editor'}><DocumentWorkbench token={props.token} online={props.online??true}/></div>
    {library&&<aside id="predicate-library" className="allow-library" aria-label="Private predicate retrieval" hidden={view!=='library'}>
      <CorpusPanel token={props.token}/>
    </aside>}
  </div>;
}
/** Render one section switch that hides, rather than unmounts, the other section. @param props Target view, current view, label and setter. @returns Native button. */
function ViewButton(props:{view:View;current:View;label:string;onSelect:(view:View)=>void}) {
  return <button type="button" className="app-view" aria-current={props.view===props.current?'page':undefined} onClick={props.onSelect.bind(null,props.view)}>{props.label}</button>;
}
/** Return to the editor from the brand link without reloading the page. @param setView View setter. @returns Nothing. */
function showEditor(setView:(view:View)=>void):void {setView('editor');}
