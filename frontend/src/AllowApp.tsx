import {DocumentWorkbench} from './DocumentWorkbench';
import {CorpusPanel} from './CorpusPanel';

/** Keep the editor mounted while navigating to the private predicate library.
 * @param props In-memory local launch authority.
 * @returns The document editor and locally stored retrieval library.
 */
export function AllowApp(props:{token:string;anonymous?:boolean;online?:boolean}) {
  return <div className="allow-app">
    <nav className="allow-navigation" aria-label="Workspace sections">
      <a href="#editor">Editor</a>{!props.anonymous&&<a href="#predicate-library">Predicate library</a>}
    </nav>
    <div id="editor"><DocumentWorkbench token={props.token} online={props.online??true}/></div>
    {!props.anonymous&&<aside id="predicate-library" className="allow-library" aria-label="Private predicate retrieval">
      <CorpusPanel token={props.token}/>
    </aside>}
  </div>;
}
