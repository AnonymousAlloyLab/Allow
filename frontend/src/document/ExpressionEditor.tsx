import {useState,useRef,useEffect} from 'react';
import {dragEndNotice,type Gesture,type Fit} from './gesture';
import type {DragEvent,KeyboardEvent} from 'react';
import type {DraftModule,DraftNode,Expression,Id,Check,SlotObligation} from './types';
import {UNARY,BINARY,QUANT,children,checkModule,nodeIndex,typeLabel} from './model';
import {slotConstraints} from './operations';
import {SelectControl,TextControl,signatureOptions,type Option} from './controls';
interface Props {
 readonly module:DraftModule;readonly slotObligations?:readonly SlotObligation[];readonly selected:Id|null;readonly snapshot:string;readonly onSelect:(id:Id)=>void;
 readonly onInsert:(tag:Expression['tag'],target:Id,name:string,destination:Id)=>void;
 readonly onClipboard:(cut:boolean)=>void;readonly onPaste:()=>void;readonly onDelete:()=>void;
 readonly onCancel:()=>void;readonly onDropNode:(source:Id,target:Id,copy:boolean)=>void;readonly onNotice:(message:string)=>void;
 readonly onSnapshot?:()=>string;readonly onPreview?:(gesture:Gesture,target:Id,copy:boolean)=>Fit;readonly onGesture?:(gesture:Gesture,target:Id,copy:boolean)=>void;
}
/** Render full palette and independently checked forest. @param props Draft callbacks. @returns Accessible editor. */
export function ExpressionEditor(props:Props) {
  const [target,setTarget]=useState(''),[name,setName]=useState('variable'),checked=checkModule(props.module,props.slotObligations);
  const [hover,setHover]=useState<{id:Id;fit:Fit}|null>(null),active=useRef<Gesture|null>(null),cache=useRef<{key:string;fit:Fit}|null>(null);
  const constraints=slotConstraints(props.module,checked),index=nodeIndex(props.module);
  useEffect(clearGesture.bind(null,active,cache,setHover),[props.snapshot]);
  /** Insert selected palette entry at current destination. @param tag Closed expression tag. @returns Nothing. */
  function insert(tag:Expression['tag']):void {if(props.selected) props.onInsert(tag,target,name,props.selected);else props.onNotice('Select a body or child slot first.');}
  /** Begin an owned palette gesture. @param tag Constructor. @param event Browser drag. @returns Nothing. */
  function startPalette(tag:Expression['tag'],event:DragEvent):void {startGesture(active,cache,{kind:'palette',tag,target,name,nonce:crypto.randomUUID(),snapshot:props.snapshot},event);props.onNotice(`Dragging ${paletteLabel(tag)}. Move to a typed slot.`);}
  /** Begin an owned subtree gesture. @param source Node identity. @param event Browser drag. @returns Nothing. */
  function startNode(source:Id,event:DragEvent):void {startGesture(active,cache,{kind:'node',source,nonce:crypto.randomUUID(),snapshot:props.snapshot},event);const node=index.get(source);props.onNotice(`Dragging ${node&&node.tag!=='hole'?nodeLabel(props.module,node,checked):'block'}. Move to a typed slot.`);}
  /** Preview only the current hovered destination. @param destination Node identity. @param event Browser drag. @returns Nothing. */
  function over(destination:Id,event:DragEvent):void {
    if(!active.current||!Array.from(event.dataTransfer.types).includes(DRAG_TYPE)) return;
    event.preventDefault();event.stopPropagation();const copy=event.ctrlKey||event.metaKey,key=JSON.stringify([active.current.nonce,props.onSnapshot?.()??props.snapshot,destination,copy]);
    if(cache.current?.key!==key) cache.current={key,fit:props.onPreview?.(active.current,destination,copy)??{kind:'incompatible',message:'Drag unavailable.'}};
    setHover({id:destination,fit:cache.current.fit});event.dataTransfer.dropEffect=cache.current.fit.kind==='incompatible'?'none':copy?'copy':'move';
  }
  /** Commit only this editor's exact active gesture. @param destination Slot. @param event Browser drop. @returns Nothing. */
  function drop(destination:Id,event:DragEvent):void {
    event.preventDefault();event.stopPropagation();const gesture=active.current,nonce=event.dataTransfer.getData(DRAG_TYPE);
    clearGesture(active,cache,setHover);
    if(!gesture||nonce!==gesture.nonce) {props.onNotice('Foreign or stale drag; draft unchanged.');return;}
    props.onGesture?.(gesture,destination,event.ctrlKey||event.metaKey);
  }
  /** Cancel current drag and preserve existing Escape action. @param event Keyboard event. @returns Nothing. */
  function keydown(event:KeyboardEvent):void {if(event.key==='Escape') clearGesture(active,cache,setHover);shortcuts(props,event);}
  return <section aria-label="Typed block editor" className="document-blocks" onKeyDown={keydown}><h2>Typed blocks</h2><Palette constraints={constraints} module={props.module} selected={props.selected} checked={checked} target={target} name={name} onTarget={setTarget} onName={setName} onInsert={insert} onDrag={startPalette} onEnd={finishGesture.bind(null,active,cache,setHover,props.onNotice)}/><BlockActions {...props}/><p className="drag-feedback" role="status" aria-live="polite">{hover?.fit.message??(active.current?'Dragging block. Move to a typed slot.':'Drag a block to a typed slot, or select a slot and choose a block.')}</p><Forest {...props} constraints={constraints} index={index} checked={checked} onDrop={drop} onOver={over} onDrag={startNode} onEnd={finishGesture.bind(null,active,cache,setHover,props.onNotice)} hover={hover}/></section>;
}
const DRAG_TYPE='application/x-allow-gesture';
/** Invalidate the active gesture and its bounded preview. @param active Gesture ref. @param cache Preview ref. @param setHover Feedback setter. @returns Nothing. */
function clearGesture(active:{current:Gesture|null},cache:{current:{key:string;fit:Fit}|null},setHover:(value:null)=>void):void {active.current=null;cache.current=null;setHover(null);}
/** Finish an unfinished drag without replacing a successful drop notice. @param active Gesture ref. @param cache Preview ref. @param setHover Feedback setter. @param notice Persistent notice action. @returns Nothing. */
function finishGesture(active:{current:Gesture|null},cache:{current:{key:string;fit:Fit}|null},setHover:(value:null)=>void,notice:(value:string)=>void):void {
  const message=dragEndNotice(active.current,cache.current?.fit??null);clearGesture(active,cache,setHover);if(message) notice(message);
}
/** Write only an opaque gesture nonce into the browser transport. @param active Gesture ref. @param cache Preview ref. @param gesture Frozen descriptor. @param event Browser drag. @returns Nothing. */
function startGesture(active:{current:Gesture|null},cache:{current:{key:string;fit:Fit}|null},gesture:Gesture,event:DragEvent):void {
  event.stopPropagation();active.current=gesture;cache.current=null;event.dataTransfer.effectAllowed='copyMove';event.dataTransfer.setData(DRAG_TYPE,gesture.nonce);
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
/** Render visible keyboard-equivalent subtree actions. @param props Actions. @returns Buttons. */
function BlockActions(props:Props) {
  return <div className="document-actions"><button disabled={!props.selected} onClick={props.onClipboard.bind(null,false)}>Copy (Ctrl/Cmd+C)</button><button disabled={!props.selected} onClick={props.onClipboard.bind(null,true)}>Cut (Ctrl/Cmd+X)</button><button onClick={props.onPaste}>Paste (Ctrl/Cmd+V)</button><button disabled={!props.selected} onClick={props.onDelete}>Delete selected</button><p>Drag an existing block to move; Ctrl/Cmd-drag copies. Selection preserves clipboard content identity.</p></div>;
}
interface PaletteProps {constraints:ReadonlyMap<Id,string>;module:DraftModule;selected:Id|null;checked:Check;target:Id;name:string;onTarget:(id:Id)=>void;onName:(name:string)=>void;onInsert:(tag:Expression['tag'])=>void;onDrag:(tag:Expression['tag'],event:DragEvent)=>void;onEnd:()=>void}
/** Build scope-aware reference options. @param props Palette state. @returns Identity choices. */
function referenceOptions(props:PaletteProps):readonly Option[] {
  const options:Option[]=[];
  for(const sig of props.module.signatures) options.push({id:sig.id,label:`Signature ${sig.name}`});
  for(const field of props.module.fields) options.push({id:field.id,label:`Field ${field.name}`});
  for(const pred of props.module.predicates) options.push({id:pred.id,label:`Predicate ${pred.name}`});
  for(const param of props.checked.scopes.get(props.selected??'')??[]) options.push({id:param.id,label:`In-scope variable ${param.name}`});
  return options;
}
/** Render all expression constructors in visual groups. @param props Selection/reference context. @returns Full palette. */
function Palette(props:PaletteProps) {
  const groups=[{name:'References',tags:['signature_ref','field_ref','variable_ref','predicate_call']},{name:'Formula',tags:['not','some_test','no_test','one_test','lone_test','and','or','implies','iff','equal','subset']},{name:'Relations',tags:['transpose','union','intersection','difference','join','product']},{name:'Quantifiers',tags:['all_quant','some_quant']}];
  const sections=[];
  for(const group of groups) {const buttons=[];for(const value of group.tags) {const tag=value as Expression['tag'];buttons.push(<button className="palette-card" key={tag} draggable onDragStart={props.onDrag.bind(null,tag)} onDragEnd={props.onEnd} onClick={props.onInsert.bind(null,tag)} data-operator={tag}><span className="block-symbol" aria-hidden="true">{operatorSymbol(tag)}</span><span className="block-label">{paletteLabel(tag)}</span><small className="block-type">{group.name}</small></button>);}sections.push(<div className="palette-group" key={group.name}><h4>{group.name}</h4>{buttons}</div>);}
  const scope=[];for(const variable of props.checked.scopes.get(props.selected??'')??[]) scope.push(<li key={variable.id}>{variable.name}: {typeLabel(props.module,{kind:'relation',columns:variable.columns})}</li>);
  return <fieldset><legend>Complete expression palette</legend><SelectControl label="Declaration or in-scope variable" value={props.target} options={referenceOptions(props)} onChange={props.onTarget}/><TextControl label="Quantifier variable name" value={props.name} onChange={props.onName}/><p>Expected destination: {props.selected?props.constraints.get(props.selected)??'unresolved constraint':'select a declaration body'}</p><ul aria-label="In-scope variables">{scope}</ul><div className="block-palette">{sections}</div></fieldset>;
}
interface ForestProps extends Props {constraints:ReadonlyMap<Id,string>;index:ReadonlyMap<Id,DraftNode>;checked:Check;onDrop:(id:Id,event:DragEvent)=>void;onOver:(id:Id,event:DragEvent)=>void;onDrag:(id:Id,event:DragEvent)=>void;onEnd:()=>void;hover:{id:Id;fit:Fit}|null}
/** Render every owned declaration body. @param props Forest. @returns Roots. */
function Forest(props:ForestProps) {
  const roots=[];
  for(const declaration of [...props.module.predicates,...props.module.facts,...props.module.assertions]) roots.push(<div key={declaration.id}><h3>{declaration.tag} {declaration.name}</h3><Branch {...props} id={declaration.bodyId} depth={0}/></div>);
  return <div className="block-canvas" aria-label="Owned expression forest">{roots.length?roots:<p>Add a predicate, fact or assertion to create a formula root.</p>}</div>;
}
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
  const description=`constraint-${node.id}`,label=node.tag==='hole'?'Drop block · Unresolved hole':nodeLabel(props.module,node,props.checked);
  return <div className="document-branch"><button className={`${node.tag==='hole'?'block-slot':'block-node'} ${props.hover?.id===node.id?`fit-${props.hover.fit.kind}`:''}`} id={`block-${node.id}`} draggable={node.tag!=='hole'} onDragStart={props.onDrag.bind(null,node.id)} onDragEnd={props.onEnd} onDragOver={props.onOver.bind(null,node.id)} onDrop={props.onDrop.bind(null,node.id)} onClick={props.onSelect.bind(null,node.id)} aria-pressed={props.selected===node.id} aria-describedby={description}><span className="block-symbol" aria-hidden="true">{node.tag==='hole'?'＋':operatorSymbol(node.tag)}</span><span className="block-label">{label}</span> · <span className="block-type">{resultLabel(props.module,node.id,props.checked)}</span></button><p id={description}>Expected: {props.constraints.get(node.id)??'unresolved constraint'}</p>{errors.length>0&&<ul>{errors}</ul>}<div className="document-children block-children">{branches}</div></div>;
}

/** Resolve a declaration or visible binder without inventing a name for an invalid reference. @param module Draft declarations. @param node Reference node. @param checked Current scopes. @returns Human-readable block title. */
function nodeLabel(module:DraftModule,node:Expression,checked:Check):string {
  if(node.tag==='signature_ref') return `Signature · ${module.signatures.find(matchesId.bind(null,node.targetId))?.name??'unresolved reference'}`;
  if(node.tag==='field_ref') return `Field · ${module.fields.find(matchesId.bind(null,node.targetId))?.name??'unresolved reference'}`;
  if(node.tag==='variable_ref') return `Variable · ${checked.scopes.get(node.id)?.find(matchesId.bind(null,node.targetId))?.name??'out-of-scope reference'}`;
  if(node.tag==='predicate_call') return `Call predicate · ${module.predicates.find(matchesId.bind(null,node.predicateId))?.name??'unresolved reference'}`;
  if(node.tag==='all_quant'||node.tag==='some_quant') return `${paletteLabel(node.tag)} · ${node.binder.name}: ${module.signatures.find(matchesId.bind(null,node.binder.signatureId))?.name??'unresolved signature'}`;
  return paletteLabel(node.tag);
}
/** Compare a declaration identity without exposing unresolved raw identifiers. @param id Requested identity. @param item Candidate declaration. @returns Exact identity match. */
function matchesId(id:Id,item:{readonly id:Id}):boolean {return item.id===id;}
/** Supply a compact visual symbol while preserving a spoken text label. @param tag Closed constructor. @returns Operator glyph. */
function operatorSymbol(tag:Expression['tag']):string {
  const symbols:Record<Expression['tag'],string>={signature_ref:'S',field_ref:'↦',variable_ref:'x',predicate_call:'ƒ',not:'¬',some_test:'∃',no_test:'∄',one_test:'1',lone_test:'≤1',transpose:'∼',and:'∧',or:'∨',implies:'⇒',iff:'⇔',equal:'=',subset:'⊆',union:'∪',intersection:'∩',difference:'−',join:'·',product:'×',all_quant:'∀',some_quant:'∃'};
  return symbols[tag];
}
/** Give each closed operator a familiar visible palette label. @param tag Exact operator. @returns User-facing block name. */
export function paletteLabel(tag:Expression['tag']):string {
  const labels:Partial<Record<Expression['tag'],string>>={signature_ref:'Signature',field_ref:'Field',variable_ref:'Variable',predicate_call:'Call predicate',some_test:'Some tuples',no_test:'No tuples',one_test:'Exactly one tuple',lone_test:'At most one tuple',all_quant:'For every variable',some_quant:'For some variable',equal:'Equals',subset:'Subset',implies:'Implies',iff:'If and only if'};
  return labels[tag]??tag.charAt(0).toUpperCase()+tag.slice(1);
}
