import {useState,type ReactNode} from 'react';
import type {ChangeEvent,DragEvent} from 'react';
import {blockKind,type SavedBlock} from './blockLibrary';
import type {BlockChoice} from './blockInventory';
import {blockHint,choiceCode,fitBadge,groupTitle,operatorSymbol,paletteLabel,type BlockGroup} from './blockCatalog';
export interface ShelfProps {readonly expectation:string;readonly choices:readonly BlockChoice[];readonly pending:boolean;readonly selected:string|null;readonly name:string;readonly onName:(value:string)=>void;readonly onChoice:(choice:BlockChoice)=>void;readonly onDrag:(choice:BlockChoice,event:DragEvent)=>void;readonly onEnd:()=>void;readonly onRename:(entry:SavedBlock,name:string)=>void;readonly onRemove:(entry:SavedBlock)=>void}
type ShelfGroup=BlockGroup|'saved';
const BUDGET='Preview budget reached; explicit insertion rechecks the guard.';
/** Render one discoverable candidate with its exact-context reason. @param props Current choice and callbacks. @returns Native keyboard/draggable action. */
function ChoiceCard(props:ShelfProps&{choice:BlockChoice;manage:boolean}) {
  const {choice}=props,blocked=choice.fit.kind==='incompatible',pending=choice.fit.kind==='unavailable'&&choice.fit.message!==BUDGET,disabled=blocked||pending;
  const label=choice.entry?choice.entry.name:choice.target?choice.label:paletteLabel(choice.tag),code=choice.entry?`${paletteLabel(choice.tag)} block`:choiceCode(choice.tag,choice.label,props.name);
  const badge=props.selected?pending?'… Checking':fitBadge(choice.fit.kind):null;
  return <div className="shelf-choice"><button className="palette-card" data-operator={choice.tag} data-block-kind={blockKind(choice.tag)} data-fit={props.selected?choice.fit.kind:undefined} draggable={!disabled} disabled={disabled} onDragStart={props.onDrag.bind(null,choice)} onDragEnd={props.onEnd} onClick={props.onChoice.bind(null,choice)} title={`${blockHint(choice.tag)} ${props.selected?choice.fit.message:'Drag onto a slot, or select a slot first and click.'}`}>
    <span className="block-symbol" aria-hidden="true">{operatorSymbol(choice.tag)}</span><span className="card-text"><span className="card-label">{label}</span><code className="card-code">{code}</code></span>{badge&&<small className={`fit-badge fit-${pending?'unavailable':choice.fit.kind}`}>{badge}</small>}
  </button>{props.manage&&<small className="choice-reason">{choice.fit.message}</small>}{choice.entry&&<EntryActions {...props} entry={choice.entry}/>}</div>;
}
/** Rename and remove snapshots without editing the model. @param props Entry callbacks. @returns Labeled controls. */
function EntryActions(props:ShelfProps&{entry:SavedBlock}) {
  const [name,setName]=useState(props.entry.name);
  /** Track the local rename field. @param event Native input. @returns Nothing. */
  function change(event:ChangeEvent<HTMLInputElement>):void {setName(event.target.value);}
  return <details className="entry-actions"><summary>Manage {props.entry.name}</summary><label>Block name<input value={name} maxLength={64} onChange={change}/></label><button onClick={props.onRename.bind(null,props.entry,name)}>Rename</button><button className="danger-quiet" onClick={props.onRemove.bind(null,props.entry)}>Remove</button></details>;
}
/** Match a choice against the free-text palette filter. @param query Lowercase filter. @param choice Candidate. @returns Whether visible. */
function matchesFilter(query:string,choice:BlockChoice):boolean {
  if(!query) return true;
  return [choice.label,choice.entry?.name??'',paletteLabel(choice.tag),choiceCode(choice.tag,choice.label,''),blockHint(choice.tag)].join(' ').toLowerCase().includes(query);
}
/** Render filtered constructors/references and immutable named reusable entries, grouped by meaning. @param props Inventory and actions. @returns Compact accessible shelf. */
export function BlockShelf(props:ShelfProps) {
  const [manage,setManage]=useState(false),[filter,setFilter]=useState(''),groups:Record<ShelfGroup,ReactNode[]>={saved:[],formula:[],quantifier:[],reference:[],relation:[]},query=filter.trim().toLowerCase();let hidden=0;
  for(const choice of props.choices) {if(choice.fit.kind==='incompatible') hidden++;if((manage||choice.fit.kind!=='incompatible')&&matchesFilter(query,choice)) groups[choice.entry?'saved':blockKind(choice.tag) as BlockGroup].push(<ChoiceCard key={choice.key} {...props} choice={choice} manage={manage}/>);}
  /** Change the all-choices visibility without changing model content. @returns Nothing. */
  function toggle():void {setManage(!manage);}
  /** Track the quantifier binder name. @param event Native field event. @returns Nothing. */
  function change(event:ChangeEvent<HTMLInputElement>):void {props.onName(event.target.value);}
  /** Track the palette filter. @param event Native search field. @returns Nothing. */
  function search(event:ChangeEvent<HTMLInputElement>):void {setFilter(event.target.value);}
  const sections=[],order:readonly BlockGroup[]=props.selected&&!/formula/.test(props.expectation)?['reference','relation','formula','quantifier']:['formula','quantifier','reference','relation'];
  for(const group of order) if(groups[group].length) sections.push(<section key={group} className="shelf-group" data-group={group}><h3>{groupTitle(group)} <span>{groups[group].length}</span></h3>{group==='quantifier'&&<label className="binder-name">Variable name for new quantifiers<input value={props.name} maxLength={64} onChange={change}/></label>}<div className="block-palette">{groups[group]}</div></section>);
  return <fieldset className="block-shelf"><legend>Blocks and reusable shelf</legend>
    <div className={`shelf-target${props.selected?' is-active':''}`}>{props.selected?<>Showing blocks for this slot: <strong>{props.expectation}</strong></>:<>No slot selected. <strong>Drag</strong> any block onto the canvas, or <strong>select a slot</strong> to see only blocks that fit.</>}</div>
    <div className="shelf-tools"><label className="shelf-search"><span className="sr-only">Filter blocks</span><input type="search" value={filter} onChange={search} placeholder="Filter blocks…"/></label>
      <button className="ghost" aria-pressed={manage} onClick={toggle}>{manage?'Show only blocks that fit':`Show all blocks (${hidden} hidden)`}</button></div>
    <p className="shelf-check" role="status">{props.pending?'Checking edit location…':props.selected?'Fit checks are current for this slot.':'Select a slot to check which blocks fit.'}</p>
    <section className="shelf-group" data-group="saved"><h3>{groupTitle('saved')} <span>{groups.saved.length}</span></h3><div className="block-palette">{groups.saved.length?groups.saved:<p className="shelf-empty">{props.choices.some(isSavedChoice)?'No saved blocks fit this slot. Use Show all blocks to see why.':'Select a block on the canvas, name it and choose Save selected block to reuse it here.'}</p>}</div></section>
    {sections}{!sections.length&&<p className="shelf-empty">{query?`No blocks match “${filter.trim()}”.`:'No blocks fit this slot.'}</p>}
    <p className="shelf-note">Saved blocks keep their internal bindings and last for this document session. Predicate calls always use the current definition.</p>
  </fieldset>;
}
/** Distinguish a filtered shelf from a library that has never captured a block. @param choice Inventory candidate. @returns Whether reusable. */
function isSavedChoice(choice:BlockChoice):boolean {return !!choice.entry;}
