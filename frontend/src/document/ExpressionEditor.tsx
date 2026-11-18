import type {ParityFrame} from './oracleParity';
import {BlockShelf} from './BlockShelf';
import {SelectionBar,CanvasToolbar,openDeclarations,type RootTag} from './CanvasParts';
import {focusNewSignature} from './StructurePanel';
import {useBlockInventory,type BlockChoice} from './blockInventory';
import {blockKind,type SavedBlock} from './blockLibrary';
import {useState,useRef,useEffect} from 'react';
import {dragEndNotice,type Gesture,type Fit} from './gesture';
import type {DragEvent,KeyboardEvent} from 'react';
import type {DraftModule,DraftNode,Expression,Id,Check,SlotObligation} from './types';
import {children,checkModule,nodeIndex,subtree,typeLabel} from './model';
import {slotConstraints} from './operations';
import {blockHint,fitBadge,matchesId,nodeLabel,operatorSymbol} from './blockCatalog';
export {operatorSymbol,paletteLabel} from './blockCatalog';
export interface Props {
 readonly parityFrame?:ParityFrame|null;
 readonly entries:readonly SavedBlock[];readonly onCapture:(name:string)=>void;readonly onRename:(entry:SavedBlock,name:string)=>void;readonly onRemove:(entry:SavedBlock)=>void;readonly onSaved:(entry:SavedBlock,target:Id)=>void;
 readonly module:DraftModule;readonly slotObligations?:readonly SlotObligation[];readonly selected:Id|null;readonly snapshot:string;readonly onSelect:(id:Id)=>void;
 readonly onInsert:(tag:Expression['tag'],target:Id,name:string,destination:Id)=>void;
 readonly onClipboard:(cut:boolean)=>void;readonly onPaste:()=>void;readonly onDelete:()=>void;
 readonly onCancel:()=>void;readonly onDropNode:(source:Id,target:Id,copy:boolean)=>void;readonly onNotice:(message:string)=>void;
 readonly onAdd?:(tag:RootTag)=>void;readonly onSnapshot?:()=>string;readonly onPreview?:(gesture:Gesture,target:Id,copy:boolean)=>Fit;readonly onGesture?:(gesture:Gesture,target:Id,copy:boolean)=>void;
}
type Hover={readonly id:Id;readonly fit:Fit};
interface DragState {readonly active:{current:Gesture|null};readonly cache:{current:{key:string;fit:Fit}|null};readonly hovered:{current:Hover|null};readonly setHover:(value:Hover|null)=>void;readonly setDragging:(value:boolean)=>void}
interface DragHandlers {readonly startChoice:(choice:BlockChoice,event:DragEvent)=>void;readonly startNode:(source:Id,event:DragEvent)=>void;readonly over:(destination:Id,event:DragEvent)=>void;readonly away:()=>void;readonly drop:(destination:Id,event:DragEvent)=>void;readonly end:()=>void}
/** Render the palette, the selection toolbar and the independently checked block canvas. @param props Draft callbacks. @returns Accessible editor. */
export function ExpressionEditor(props:Props) {
  const [name,setName]=useState('variable'),[label,setLabel]=useState(''),[hover,setHover]=useState<Hover|null>(null),[dragging,setDragging]=useState(false);
  const checked=checkModule(props.module,props.slotObligations),constraints=slotConstraints(props.module,checked),index=nodeIndex(props.module);
  const drag:DragState={active:useRef<Gesture|null>(null),cache:useRef<{key:string;fit:Fit}|null>(null),hovered:useRef<Hover|null>(null),setHover,setDragging};
  const inventory=useBlockInventory({module:props.module,checked,selected:props.selected,snapshot:props.snapshot,name,entries:props.entries,obligations:props.slotObligations,preview:props.onPreview});
  useEffect(clearGesture.bind(null,drag),[props.snapshot]);
  const handlers=dragHandlers(props,drag,name,index,checked),expectation=props.selected?constraints.get(props.selected)??'unresolved constraint':'select a body or child slot';
  /** Insert the exact constructor/reference pair or frozen reusable snapshot. @param choice Inventory item. @returns Nothing. */
  function choose(choice:BlockChoice):void {if(!props.selected) {props.onNotice('Select an empty slot or a block on the canvas first, or drag this block onto a slot.');return;}if(choice.entry) props.onSaved(choice.entry,props.selected);else props.onInsert(choice.tag,choice.target,name,props.selected);}
  /** Cancel current drag and preserve existing Escape action. @param event Keyboard event. @returns Nothing. */
  function keydown(event:KeyboardEvent):void {if(event.key==='Escape') clearGesture(drag);shortcuts(props,event);}
  const feedback=hover?`${fitBadge(hover.fit.kind)} — ${hover.fit.message}`:dragging?'Dragging block. Move it onto a highlighted slot; release to drop, Esc to cancel.':'Drag a block onto a dashed empty slot, or select a slot and click a block in the palette.';
  return <section aria-label="Typed block editor" className="document-blocks" data-dragging={dragging?'true':undefined} onKeyDown={keydown}><h2 className="sr-only">Typed blocks</h2>
    <BlockShelf expectation={expectation} choices={inventory.choices} pending={inventory.pending} selected={props.selected} name={name} onName={setName} onChoice={choose} onDrag={handlers.startChoice} onEnd={handlers.end} onRename={props.onRename} onRemove={props.onRemove}/>
    <div className="canvas-column">
      <SelectionBar {...props} index={index} checked={checked} expectation={expectation} label={label} onLabel={setLabel}/>
      <p className={`drag-feedback${hover?` fit-${hover.fit.kind}`:''}`} role="status" aria-live="polite">{feedback}</p>
      <CanvasToolbar onAdd={props.onAdd}/>
      <Forest {...props} constraints={constraints} index={index} checked={checked} handlers={handlers} hover={hover}/>
      <p className="canvas-tips">Drag a placed block to move it · hold Ctrl/Cmd while dropping to copy · Esc cancels a drag · Ctrl/Cmd+Z previews undo</p>
    </div></section>;
}
const DRAG_TYPE='application/x-allow-gesture';
/** Create gesture callbacks bound to the latest props and owned drag refs. @param props Editor props. @param drag Gesture refs and setters. @param name Quantifier binder name. @param index Node lookup. @param checked Current analysis. @returns Drag callbacks. */
function dragHandlers(props:Props,drag:DragState,name:string,index:ReadonlyMap<Id,DraftNode>,checked:Check):DragHandlers {
  /** Begin a current context-bound shelf gesture. @param choice Exact inventory item. @param event Browser event. @returns Nothing. */
  function startChoice(choice:BlockChoice,event:DragEvent):void {
    const base={nonce:crypto.randomUUID(),snapshot:props.snapshot};startGesture(drag,choice.entry?{...base,kind:'saved',entry:choice.entry}:{...base,kind:'palette',tag:choice.tag,target:choice.target,name},event);
    props.onNotice(`Dragging ${choice.entry?.name??choice.label}. Move it onto a typed slot.`);}
  /** Begin an owned subtree gesture. @param source Node identity. @param event Browser drag. @returns Nothing. */
  function startNode(source:Id,event:DragEvent):void {startGesture(drag,{kind:'node',source,nonce:crypto.randomUUID(),snapshot:props.snapshot},event);const node=index.get(source);props.onNotice(`Dragging ${node&&node.tag!=='hole'?nodeLabel(props.module,node,checked):'block'}. Move it onto a typed slot.`);}
  /** Preview only the current hovered destination. @param destination Node identity. @param event Browser drag. @returns Nothing. */
  function over(destination:Id,event:DragEvent):void {
    if(!drag.active.current||!Array.from(event.dataTransfer.types).includes(DRAG_TYPE)) return;
    event.preventDefault();event.stopPropagation();const copy=drag.active.current.kind!=='node'||event.ctrlKey||event.metaKey,key=JSON.stringify([drag.active.current.nonce,props.onSnapshot?.()??props.snapshot,destination,copy]);
    if(drag.cache.current?.key!==key) drag.cache.current={key,fit:props.onPreview?.(drag.active.current,destination,copy)??{kind:'incompatible',message:'Drag unavailable.'}};
    publishHover(drag,{id:destination,fit:drag.cache.current.fit});event.dataTransfer.dropEffect=['incompatible','unavailable'].includes(drag.cache.current.fit.kind)?'none':copy?'copy':'move';
  }
  /** Clear a stale destination preview while the pointer is over empty canvas. @returns Nothing. */
  function away():void {publishHover(drag,null);}
  /** Commit only this editor's exact active gesture. @param destination Slot. @param event Browser drop. @returns Nothing. */
  function drop(destination:Id,event:DragEvent):void {
    event.preventDefault();event.stopPropagation();const gesture=drag.active.current,nonce=event.dataTransfer.getData(DRAG_TYPE);clearGesture(drag);
    if(!gesture||nonce!==gesture.nonce) {props.onNotice('Foreign or stale drag; draft unchanged.');return;}
    props.onGesture?.(gesture,destination,event.ctrlKey||event.metaKey);}
  return {startChoice,startNode,over,away,drop,end:finishGesture.bind(null,drag,props.onNotice)};
}
/** Publish a destination preview only when it changes, avoiding a render per dragover event. @param drag Gesture refs. @param next Destination preview or none. @returns Nothing. */
function publishHover(drag:DragState,next:Hover|null):void {
  const last=drag.hovered.current;if(last===next||(last&&next&&last.id===next.id&&last.fit===next.fit)) return;
  drag.hovered.current=next;drag.setHover(next);
}
/** Invalidate the active gesture and its bounded preview. @param drag Gesture refs and setters. @returns Nothing. */
function clearGesture(drag:DragState):void {drag.active.current=null;drag.cache.current=null;drag.hovered.current=null;drag.setHover(null);drag.setDragging(false);}
/** Finish an unfinished drag without replacing a successful drop notice. @param drag Gesture refs. @param notice Persistent notice action. @returns Nothing. */
function finishGesture(drag:DragState,notice:(value:string)=>void):void {
  const message=dragEndNotice(drag.active.current,drag.cache.current?.fit??null);clearGesture(drag);if(message) notice(message);
}
/** Write only an opaque gesture nonce into the browser transport. @param drag Gesture refs. @param gesture Frozen descriptor. @param event Browser drag. @returns Nothing. */
function startGesture(drag:DragState,gesture:Gesture,event:DragEvent):void {
  event.stopPropagation();drag.active.current=gesture;drag.cache.current=null;drag.hovered.current=null;event.dataTransfer.effectAllowed=gesture.kind==='node'?'copyMove':'copy';event.dataTransfer.setData(DRAG_TYPE,gesture.nonce);drag.setDragging(true);
}
/** Route block shortcuts without intercepting native text editing. @param props Actions. @param event Key. @returns Nothing. */
function shortcuts(props:Props,event:KeyboardEvent):void {
  const target=event.target as HTMLElement;
  if(['INPUT','TEXTAREA','SELECT'].includes(target.tagName)||target.isContentEditable) return;
  const modified=event.ctrlKey||event.metaKey,key=event.key.toLowerCase();
  if(modified&&['c','x','v'].includes(key)) {
    event.preventDefault();if(key==='v') props.onPaste();else props.onClipboard(key==='x');
  } else if(event.key==='Delete') {event.preventDefault();props.onDelete();}
  else if(event.key==='Escape') props.onCancel();
}
interface ForestProps extends Props {constraints:ReadonlyMap<Id,string>;index:ReadonlyMap<Id,DraftNode>;checked:Check;handlers:DragHandlers;hover:Hover|null}
/** Render every owned declaration body as its own card on the canvas. @param props Forest. @returns Roots. */
function Forest(props:ForestProps) {
  const roots=[];
  for(const declaration of [...props.module.predicates,...props.module.facts,...props.module.assertions]) {
    const framed=props.parityFrame?.targetId===declaration.id,empty=emptySlots(props,declaration.bodyId);
    roots.push(<div key={declaration.id} data-parity={framed?props.parityFrame!.verdict:undefined} className={`forest-root${framed?` parity-frame parity-${props.parityFrame!.verdict}`:''}`}>{framed&&<p className="parity-label" role="status">Bounded {props.parityFrame!.verdict} · scope {props.parityFrame!.scope}, bitwidth 4, maximum sequence 3</p>}
      <div className="root-heading"><h3><span className={`root-kind root-${declaration.tag}`}>{declaration.tag}</span> {declaration.name}{'parameters' in declaration&&declaration.parameters.length>0&&<span className="root-params">[{declaration.parameters.map(parameterText.bind(null,props.module)).join(', ')}]</span>}</h3><span className={`root-status${empty?' has-empty':''}`}>{empty?`${empty} empty slot${empty===1?'':'s'}`:'✓ Complete'}</span></div>
      <Branch {...props} id={declaration.bodyId} depth={0}/></div>);
  }
  return <div className="block-canvas" aria-label="Owned expression forest" onDragOver={props.handlers.away}>{roots.length?roots:<div className="canvas-empty"><strong>No formulas yet.</strong><p>Add signatures and fields in the panel above, then a predicate, fact or assertion. Each one appears here as a card with an empty formula slot to fill with blocks.</p>{props.onAdd&&<div className="canvas-empty-actions"><button type="button" className="secondary" onClick={focusNewSignature}>＋ Add signature</button><button type="button" className="primary" onClick={props.onAdd.bind(null,'predicate')}>＋ Add predicate</button><button type="button" className="ghost" onClick={openDeclarations}>Open declarations</button></div>}</div>}</div>;
}
/** Count unresolved holes owned by one declaration body. @param props Forest lookups. @param root Body identity. @returns Number of empty slots. */
function emptySlots(props:ForestProps,root:Id):number {let count=0;for(const id of subtree(props.module,root)) if(props.index.get(id)?.tag==='hole') count++;return count;}
/** Format one predicate parameter with its ordered nominal schema. @param module Declarations. @param parameter Ordered parameter. @returns Readable parameter text. */
function parameterText(module:DraftModule,parameter:{readonly name:string;readonly columns:readonly Id[]}):string {
  const columns=parameter.columns.map(signatureName.bind(null,module));return `${parameter.name}: ${columns.join(' -> ')||'?'}`;
}
/** Resolve a signature name for display only. @param module Declarations. @param id Signature identity. @returns Name or a placeholder. */
function signatureName(module:DraftModule,id:Id):string {return module.signatures.find(matchesId.bind(null,id))?.name??'?';}
/** Display known structural sort without fabricating unresolved nominal columns. @param module Declaration names. @param id Expression identity. @param checked Shared partial and exact analysis. @returns Honest structural result label. */
function resultLabel(module:DraftModule,id:Id,checked:Check):string {
  const exact=checked.types.get(id),fact=checked.facts.get(id);
  if(exact) return typeLabel(module,exact);
  if(fact?.sort==='formula') return 'formula';
  if(fact?.sort==='relation') {
    const widths=new Set<number>();for(const shape of fact.shapes) widths.add(shape.columns.length);
    return widths.size===1?`relation; width ${[...widths][0]}, nominal schema unresolved`:'relation; nominal schema unresolved';
  }
  return 'unresolved constraint';
}
/** Render a bounded branch with expected schema and programmatic error association. @param props Node and forest. @returns Native selectable blocks. */
function Branch(props:ForestProps&{id:Id;depth:number}) {
  const node=props.index.get(props.id),branches=[],errors=[];
  if(!node||props.depth>=32) return <p role="alert">Missing node or depth limit.</p>;
  for(const child of children(node)) branches.push(<Branch key={child} {...props} id={child} depth={props.depth+1}/>);
  for(const error of props.checked.diagnostics) if(error.nodeId===node.id) errors.push(<li key={error.message}>{error.message}</li>);
  const hole=node.tag==='hole',selected=props.selected===node.id,fit=props.hover?.id===node.id?props.hover.fit:null,description=`constraint-${node.id}`,label=hole?'Empty slot · drop or choose a block':nodeLabel(props.module,node,props.checked);
  return <div className={`document-branch${hole?' is-hole':''}${selected?' is-selected':''}${errors.length?' has-errors':''}`}>
    <button className={`${hole?'block-slot':'block-node'}${fit?` fit-${fit.kind}`:''}`} data-block-kind={blockKind(node.tag)} id={`block-${node.id}`} draggable={!hole} onDragStart={props.handlers.startNode.bind(null,node.id)} onDragEnd={props.handlers.end} onDragOver={props.handlers.over.bind(null,node.id)} onDrop={props.handlers.drop.bind(null,node.id)} onClick={props.onSelect.bind(null,node.id)} aria-pressed={selected} aria-describedby={description} title={hole?'Empty slot: drop a block here, or select it and click a block in the palette':blockHint(node.tag)}>
      <span className="block-symbol" aria-hidden="true">{hole?'＋':operatorSymbol(node.tag)}</span><span className="block-label">{label}</span>{fit&&<span className={`fit-badge fit-${fit.kind}`}>{fitBadge(fit.kind)}</span>}<span className="sr-only"> · </span><span className="block-type">{resultLabel(props.module,node.id,props.checked)}</span></button>
    <p id={description} className="node-expect">Slot accepts: {props.constraints.get(node.id)??'unresolved constraint'}</p>{errors.length>0&&<ul className="node-errors">{errors}</ul>}<div className="document-children block-children">{branches}</div></div>;
}
