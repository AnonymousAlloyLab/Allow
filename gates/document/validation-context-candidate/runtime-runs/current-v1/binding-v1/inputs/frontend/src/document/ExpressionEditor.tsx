import {useState} from 'react';
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
}
/** Render full palette and independently checked forest. @param props Draft callbacks. @returns Accessible editor. */
export function ExpressionEditor(props:Props) {
  const [target,setTarget]=useState(''),[name,setName]=useState('variable'),checked=checkModule(props.module,props.slotObligations);
  const constraints=slotConstraints(props.module,checked),index=nodeIndex(props.module);
  /** Insert selected palette entry at current destination. @param tag Closed expression tag. @returns Nothing. */
  function insert(tag:Expression['tag']):void {if(props.selected) props.onInsert(tag,target,name,props.selected);else props.onNotice('Select a body or child slot first.');}
  /** Apply palette drag or same-draft subtree drag. @param destination Selected drop slot. @param event Browser drop. @returns Nothing. */
  function drop(destination:Id,event:DragEvent):void {
    event.preventDefault();event.stopPropagation();const value=event.dataTransfer.getData('text/plain');
    if(value.startsWith('node:')) {applyNodeDrop(props,value.slice(5),destination,event.ctrlKey||event.metaKey);return;}
    const allowed:readonly string[]=['signature_ref','field_ref','variable_ref','predicate_call',...UNARY,...BINARY,...QUANT];
    if(allowed.includes(value)) props.onInsert(value as Expression['tag'],target,name,destination);
    else props.onNotice('Unsupported drag payload.');
  }
  return <section aria-label="Typed block editor" className="document-blocks" onKeyDown={shortcuts.bind(null,props)}><h2>Typed blocks</h2><Palette constraints={constraints} module={props.module} selected={props.selected} checked={checked} target={target} name={name} onTarget={setTarget} onName={setName} onInsert={insert}/><BlockActions {...props}/><Forest {...props} constraints={constraints} index={index} checked={checked} onDrop={drop}/></section>;
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
interface PaletteProps {constraints:ReadonlyMap<Id,string>;module:DraftModule;selected:Id|null;checked:Check;target:Id;name:string;onTarget:(id:Id)=>void;onName:(name:string)=>void;onInsert:(tag:Expression['tag'])=>void}
/** Build scope-aware reference options. @param props Palette state. @returns Identity choices. */
function referenceOptions(props:PaletteProps):readonly Option[] {
  const options:Option[]=[];
  for(const sig of props.module.signatures) options.push({id:sig.id,label:`Signature ${sig.name}`});
  for(const field of props.module.fields) options.push({id:field.id,label:`Field ${field.name}`});
  for(const pred of props.module.predicates) options.push({id:pred.id,label:`Predicate ${pred.name}`});
  for(const param of props.checked.scopes.get(props.selected??'')??[]) options.push({id:param.id,label:`In-scope variable ${param.name}`});
  return options;
}
/** Store a closed palette tag in native drag data. @param tag Operator. @param event Drag. @returns Nothing. */
function paletteDrag(tag:Expression['tag'],event:DragEvent):void {event.dataTransfer.setData('text/plain',tag);}
/** Render all23 expression constructors. @param props Selection/reference context. @returns Full palette. */
function Palette(props:PaletteProps) {
  const buttons=[],tags:readonly Expression['tag'][]=['signature_ref','field_ref','variable_ref','predicate_call',...UNARY,...BINARY,...QUANT];
  for(const tag of tags) buttons.push(<button key={tag} draggable onDragStart={paletteDrag.bind(null,tag)} onClick={props.onInsert.bind(null,tag)} data-operator={tag}>{paletteLabel(tag)}</button>);
  const scope=[];for(const variable of props.checked.scopes.get(props.selected??'')??[]) scope.push(<li key={variable.id}>{variable.name}: {typeLabel(props.module,{kind:'relation',columns:variable.columns})}</li>);
  return <fieldset><legend>Complete expression palette</legend><SelectControl label="Declaration or in-scope variable" value={props.target} options={referenceOptions(props)} onChange={props.onTarget}/><TextControl label="Quantifier variable name" value={props.name} onChange={props.onName}/><p>Expected destination: {props.selected?props.constraints.get(props.selected)??'unresolved constraint':'select a declaration body'}</p><ul aria-label="In-scope variables">{scope}</ul><div className="document-actions">{buttons}</div></fieldset>;
}
interface ForestProps extends Props {constraints:ReadonlyMap<Id,string>;index:ReadonlyMap<Id,DraftNode>;checked:Check;onDrop:(id:Id,event:DragEvent)=>void}
/** Render every owned declaration body. @param props Forest. @returns Roots. */
function Forest(props:ForestProps) {
  const roots=[];
  for(const declaration of [...props.module.predicates,...props.module.facts,...props.module.assertions]) roots.push(<div key={declaration.id}><h3>{declaration.tag} {declaration.name}</h3><Branch {...props} id={declaration.bodyId} depth={0}/></div>);
  return <div aria-label="Owned expression forest">{roots.length?roots:<p>Add a predicate, fact or assertion to create a formula root.</p>}</div>;
}
/** Allow a drop onto a named destination. @param event Browser drag. @returns Nothing. */
function allowDrop(event:DragEvent):void {event.preventDefault();event.stopPropagation();}
/** Store a same-document owned source identity. @param id Source. @param snapshot Content identity. @param event Drag. @returns Nothing. */
function nodeDrag(id:Id,snapshot:string,event:DragEvent):void {event.stopPropagation();event.dataTransfer.setData('text/plain',`node:${JSON.stringify({nodeId:id,snapshot})}`);}
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
  const description=`constraint-${node.id}`,label=node.tag==='hole'?'Unresolved hole':node.tag.replaceAll('_',' ');
  return <div className="document-branch"><button id={`block-${node.id}`} draggable={node.tag!=='hole'} onDragStart={nodeDrag.bind(null,node.id,props.snapshot)} onDragOver={allowDrop} onDrop={props.onDrop.bind(null,node.id)} onClick={props.onSelect.bind(null,node.id)} aria-pressed={props.selected===node.id} aria-describedby={description}>{label} · {resultLabel(props.module,node.id,props.checked)}</button><p id={description}>Expected: {props.constraints.get(node.id)??'unresolved constraint'}</p>{errors.length>0&&<ul>{errors}</ul>}<div className="document-children">{branches}</div></div>;
}

/** Validate drag source snapshot before applying a local transaction. @param props Current editor. @param payload Exact drag content. @param destination Destination. @param copy Clone modifier. @returns Nothing. */
function applyNodeDrop(props:Props,payload:string,destination:Id,copy:boolean):void {
  try {
    const value:unknown=JSON.parse(payload);
    if(value&&typeof value==='object'&&'nodeId' in value&&typeof value.nodeId==='string'&&'snapshot' in value&&value.snapshot===props.snapshot) {props.onDropNode(value.nodeId,destination,copy);return;}
  } catch {props.onNotice('Malformed dragged source.');return;}
  props.onNotice('Stale or foreign dragged source; draft unchanged.');
}

/** Give each closed operator a familiar visible palette label. @param tag Exact operator. @returns User-facing block name. */
export function paletteLabel(tag:Expression['tag']):string {
  const labels:Partial<Record<Expression['tag'],string>>={signature_ref:'Signature',field_ref:'Field',variable_ref:'Variable',predicate_call:'Call predicate',some_test:'Some tuples',no_test:'No tuples',one_test:'Exactly one tuple',lone_test:'At most one tuple',all_quant:'For every variable',some_quant:'For some variable',equal:'Equals',subset:'Subset',implies:'Implies',iff:'If and only if'};
  return labels[tag]??tag.charAt(0).toUpperCase()+tag.slice(1);
}
