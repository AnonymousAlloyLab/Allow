import type {ChangeEvent} from 'react';
import type {Props} from './ExpressionEditor';
import type {Check,DraftNode,Id} from './types';
import {blockKind} from './blockLibrary';
import {groupTitle,nodeLabel,operatorSymbol} from './blockCatalog';
interface SelectionProps extends Props {readonly index:ReadonlyMap<Id,DraftNode>;readonly checked:Check;readonly expectation:string;readonly label:string;readonly onLabel:(value:string)=>void}
/** Show what is selected, what its slot accepts, and every keyboard-equivalent action on it. @param props Editor props with lookups and capture name. @returns Contextual toolbar. */
export function SelectionBar(props:SelectionProps) {
  const node=props.selected?props.index.get(props.selected):undefined,hole=node?.tag==='hole';
  /** Track the reusable block name without affecting quantifier names. @param event Native input. @returns Nothing. */
  function change(event:ChangeEvent<HTMLInputElement>):void {props.onLabel(event.target.value);}
  /** Save the selected subtree under the typed name, then clear the field. @returns Nothing. */
  function capture():void {props.onCapture(props.label);props.onLabel('');}
  return <div className="selection-bar" role="group" aria-label="Selected block">
    <div className="selection-summary">{node?<><span className="selection-chip" data-block-kind={blockKind(node.tag)}><span className="block-symbol" aria-hidden="true">{hole?'＋':operatorSymbol(node.tag)}</span>{node.tag==='hole'?'Empty slot':nodeLabel(props.module,node,props.checked)}</span><span className="selection-expect">Slot accepts <strong>{props.expectation}</strong></span></>:<span className="selection-empty">Nothing selected. Click a block or a dashed empty slot on the canvas.</span>}</div>
    <BlockActions {...props}/>
    <div className="capture-row"><label className="capture-field"><span>Reuse later</span><input value={props.label} maxLength={64} placeholder="Name this block" onChange={change} disabled={!node||hole}/></label><button className="secondary" disabled={!node||hole||!props.label.trim()} onClick={capture} title="Save a copy of the selected block to your reusable blocks">Save selected block</button></div>
  </div>;
}
/** Render visible keyboard-equivalent subtree actions. @param props Actions. @returns Buttons. */
function BlockActions(props:Props) {
  return <div className="document-actions" role="toolbar" aria-label="Block actions">
    <button disabled={!props.selected} onClick={props.onClipboard.bind(null,false)} aria-keyshortcuts="Control+C Meta+C" title="Copy (Ctrl/Cmd+C)">Copy <kbd>Ctrl/Cmd+C</kbd></button>
    <button disabled={!props.selected} onClick={props.onClipboard.bind(null,true)} aria-keyshortcuts="Control+X Meta+X" title="Cut (Ctrl/Cmd+X)">Cut <kbd>Ctrl/Cmd+X</kbd></button>
    <button onClick={props.onPaste} aria-keyshortcuts="Control+V Meta+V" title="Paste (Ctrl/Cmd+V) into the selected slot">Paste <kbd>Ctrl/Cmd+V</kbd></button>
    <button className="danger-quiet" disabled={!props.selected} onClick={props.onDelete} aria-keyshortcuts="Delete" title="Delete the selected block, leaving an empty slot">Delete <kbd>Del</kbd></button>
  </div>;
}
/** Explain the semantic block colors with text so color is never the only cue, next to quick-add actions for new formula roots. @param props Optional declaration creator. @returns Canvas toolbar. */
export function CanvasToolbar(props:{onAdd?:(tag:RootTag)=>void}) {
  const items=[],adds=[];for(const kind of ['formula','relation','quantifier','reference','hole'] as const) items.push(<li key={kind} data-block-kind={kind}>{groupTitle(kind)}</li>);
  if(props.onAdd) for(const tag of ['predicate','fact','assertion'] as const) adds.push(<button key={tag} type="button" className="ghost" onClick={props.onAdd.bind(null,tag)}>＋ {tag.charAt(0).toUpperCase()+tag.slice(1)}</button>);
  return <div className="canvas-toolbar"><ul className="canvas-legend" aria-label="Block colors">{items}</ul>{adds.length>0&&<div className="canvas-add" role="group" aria-label="Add to model">{adds}<button type="button" className="ghost" onClick={openDeclarations}>Rename or edit declarations…</button></div>}</div>;
}
export type RootTag='signature'|'predicate'|'fact'|'assertion';
/** Open and reveal the declarations drawer below the canvas. @returns Nothing. */
export function openDeclarations():void {
  const panel=document.getElementById('declarations-panel');if(!(panel instanceof HTMLDetailsElement)) return;
  panel.open=true;panel.scrollIntoView({behavior:'smooth',block:'start'});
}
