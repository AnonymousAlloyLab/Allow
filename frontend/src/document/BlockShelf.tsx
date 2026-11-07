import {useState,type ReactNode} from 'react';
import type {DragEvent} from 'react';
import {blockKind,type SavedBlock} from './blockLibrary';
import type {BlockChoice} from './blockInventory';
import {operatorSymbol,paletteLabel} from './ExpressionEditor';
export interface ShelfProps {readonly expectation:string;readonly choices:readonly BlockChoice[];readonly pending:boolean;readonly selected:string|null;readonly name:string;readonly onName:(value:string)=>void;readonly onChoice:(choice:BlockChoice)=>void;readonly onDrag:(choice:BlockChoice,event:DragEvent)=>void;readonly onEnd:()=>void;readonly onCapture:(name:string)=>void;readonly onRename:(entry:SavedBlock,name:string)=>void;readonly onRemove:(entry:SavedBlock)=>void}
/** Render one discoverable candidate with its exact-context reason. @param props Current choice and callbacks. @returns Native keyboard/draggable action. */
function ChoiceCard(props:ShelfProps&{choice:BlockChoice;manage:boolean}) {
  const {choice}=props,blocked=choice.fit.kind==='incompatible',pending=choice.fit.kind==='unavailable'&&choice.fit.message!=='Preview budget reached; explicit insertion rechecks the guard.';
  const disabled=blocked||pending||!props.selected;
  return <div className="shelf-choice"><button className="palette-card" data-operator={choice.tag} data-block-kind={blockKind(choice.tag)} draggable={!disabled} disabled={disabled} onDragStart={props.onDrag.bind(null,choice)} onDragEnd={props.onEnd} onClick={props.onChoice.bind(null,choice)} title={choice.fit.message}>
    <span className="block-symbol" aria-hidden="true">{operatorSymbol(choice.tag)}</span><span>{choice.entry?choice.entry.name:choice.target?choice.label:paletteLabel(choice.tag)}<small>{choice.fit.kind}</small></span>
  </button>{props.manage&&<small>{choice.fit.message}</small>}{choice.entry&&<EntryActions {...props} entry={choice.entry}/>}</div>;
}
/** Rename and remove snapshots without editing the model. @param props Entry callbacks. @returns Labeled controls. */
function EntryActions(props:ShelfProps&{entry:SavedBlock}) {
  const [name,setName]=useState(props.entry.name);
  /** Track the local rename field. @param event Native input. @returns Nothing. */
  function change(event:React.ChangeEvent<HTMLInputElement>):void {setName(event.target.value);}
  return <details><summary>Manage {props.entry.name}</summary><label>Block name<input value={name} maxLength={64} onChange={change}/></label><button onClick={props.onRename.bind(null,props.entry,name)}>Rename</button><button onClick={props.onRemove.bind(null,props.entry)}>Remove</button></details>;
}
/** Render filtered constructors/references and immutable named reusable entries. @param props Inventory and actions. @returns Compact accessible shelf. */
export function BlockShelf(props:ShelfProps) {
  const [manage,setManage]=useState(false),visible:ReactNode[]=[],saved:ReactNode[]=[];let hidden=0;
  for(const choice of props.choices) {if(choice.fit.kind==='incompatible') hidden++;if(manage||choice.fit.kind!=='incompatible') (choice.entry?saved:visible).push(<ChoiceCard key={choice.key} {...props} choice={choice} manage={manage}/>);}
  /** Change the all-choices visibility without changing model content. @returns Nothing. */
  function toggle():void {setManage(!manage);}
  /** Track the quantifier/capture label input. @param event Native field event. @returns Nothing. */
  function change(event:React.ChangeEvent<HTMLInputElement>):void {props.onName(event.target.value);}
  return <fieldset className="block-shelf"><legend>Blocks and reusable shelf</legend><p>Expected destination: {props.expectation}</p><label>New block / quantifier name<input value={props.name} maxLength={64} onChange={change}/></label><button disabled={!props.selected} onClick={props.onCapture.bind(null,props.name)}>Save selected block</button><p>Copies keep internal bindings. Predicate calls use current definitions.</p><button aria-pressed={manage} onClick={toggle}>{manage?'Show compatible choices':'Manage all choices'} ({hidden} hidden)</button><p role="status">{props.pending?'Checking edit location…':'Edit-location checks current.'}</p><h3>Reusable blocks</h3><div className="block-palette">{saved.length?saved:<p>{props.choices.some(isSavedChoice)?'No saved blocks fit this location. Use Manage all choices to inspect them.':'No saved blocks yet.'}</p>}</div><h3>Constructors and references</h3><div className="block-palette">{visible}</div></fieldset>;
}

/** Distinguish a filtered shelf from a library that has never captured a block. @param choice Inventory candidate. @returns Whether reusable. */
function isSavedChoice(choice:BlockChoice):boolean {return !!choice.entry;}
