import type {DraftModule,Id,Multiplicity,Schema,Predicate,Parameter} from './types';
import {type Declaration,updateDeclaration,deleteDeclaration,addDeclaration,addParameter,replaceItem} from './declarations';
import {TextControl,SelectControl,SchemaControl,MultiplicityControl,signatureOptions,type Option} from './controls';
interface Props {readonly module:DraftModule;readonly onChange:(module:DraftModule)=>void;readonly onSelect:(id:Id)=>void}
interface RowProps extends Props {readonly item:Declaration}
/** Render all declaration kinds and explicit creation controls. @param props Immutable module and consumers. @returns Editors. */
export function DeclarationEditor(props:Props) {
  /** Add an explicit declaration draft. @param tag Kind. @returns Nothing. */
  function add(tag:Declaration['tag']):void {props.onChange(addDeclaration(props.module,tag));}
  const buttons=[],rows=[];
  for(const tag of ['signature','field','predicate','fact','assertion','run','check'] as const) buttons.push(<button key={tag} onClick={add.bind(null,tag)}>Add {tag}</button>);
  for(const item of [...props.module.signatures,...props.module.fields,...props.module.predicates,...props.module.facts,...props.module.assertions,...props.module.commands]) rows.push(<DeclarationRow key={item.id} {...props} item={item}/>);
  return <section aria-label="Declaration editors"><h2>Declarations</h2><div className="document-actions">{buttons}</div>{rows}</section>;
}
/** Render a declaration's labeled controls and body selector. @param props Row. @returns Native editors. */
function DeclarationRow(props:RowProps) {
  /** Replace a complete declaration. @param item Updated row. @returns Nothing. */
  function update(item:Declaration):void {props.onChange(updateDeclaration(props.module,item));}
  /** Change a syntax label, preserving identity. @param name New label. @returns Nothing. */
  function rename(name:string):void {if('name' in props.item) update({...props.item,name});}
  /** Remove only explicitly selected declaration. @returns Nothing. */
  function remove():void {props.onChange(deleteDeclaration(props.module,props.item));}
  const item=props.item;
  return <fieldset><legend>{item.tag}</legend>{'name' in item&&<TextControl label="Name" value={item.name} onChange={rename}/>}<DeclarationFields {...props} update={update}/>{'bodyId' in item&&<button onClick={props.onSelect.bind(null,item.bodyId)}>Select {item.tag} body</button>}<button onClick={remove}>Delete {item.tag}</button><details><summary>Declaration identity</summary><small>{item.id}</small></details></fieldset>;
}
/** Dispatch the closed declaration-specific editor. @param props Row and update. @returns Relevant controls. */
function DeclarationFields(props:RowProps&{update:(item:Declaration)=>void}) {
  const item=props.item;
  /** Change declared multiplicity. @param multiplicity Closed value. @returns Nothing. */
  function multiplicity(multiplicity:Multiplicity):void {if(item.tag==='signature'||item.tag==='field') props.update({...item,multiplicity});}
  /** Change owning signature. @param ownerSignatureId Exact identity. @returns Nothing. */
  function owner(ownerSignatureId:Id):void {if(item.tag==='field') props.update({...item,ownerSignatureId});}
  /** Change ordered field range. @param rangeColumns Schema. @returns Nothing. */
  function range(rangeColumns:Schema):void {if(item.tag==='field') props.update({...item,rangeColumns});}
  if(item.tag==='signature') return <MultiplicityControl value={item.multiplicity} onChange={multiplicity}/>;
  if(item.tag==='field') return <><SelectControl label="Owner signature" value={item.ownerSignatureId} options={signatureOptions(props.module)} onChange={owner}/><SchemaControl module={props.module} columns={item.rangeColumns} onChange={range}/><MultiplicityControl value={item.multiplicity} onChange={multiplicity}/></>;
  if(item.tag==='predicate') return <ParameterEditor module={props.module} predicate={item} onChange={props.update}/>;
  if(item.tag==='run'||item.tag==='check') return <CommandFields item={item} module={props.module} onChange={props.update}/>;
  return null;
}
/** Render set-valued ordered predicate parameters. @param props Predicate and update. @returns Parameter controls. */
function ParameterEditor(props:{module:DraftModule;predicate:Predicate;onChange:(item:Predicate)=>void}) {
  /** Append a parameter. @returns Nothing. */
  function add():void {props.onChange(addParameter(props.predicate,props.module.signatures[0]?.id??''));}
  /** Replace an ordered parameter. @param parameter Updated parameter. @returns Nothing. */
  function update(parameter:Parameter):void {props.onChange({...props.predicate,parameters:replaceItem(props.predicate.parameters,parameter)});}
  /** Remove one parameter; dependencies remain diagnostic. @param id Target. @returns Nothing. */
  function remove(id:Id):void {const parameters:Parameter[]=[];for(const param of props.predicate.parameters) if(param.id!==id) parameters.push(param);props.onChange({...props.predicate,parameters});}
  const rows=[];for(const parameter of props.predicate.parameters) rows.push(<ParameterRow key={parameter.id} module={props.module} parameter={parameter} onChange={update} onDelete={remove.bind(null,parameter.id)}/>);
  return <fieldset><legend>Ordered set-valued parameters</legend>{rows}<button disabled={props.predicate.parameters.length>=16} onClick={add}>Add parameter</button></fieldset>;
}
/** Render one parameter schema/name. @param props Parameter callbacks. @returns Native row. */
function ParameterRow(props:{module:DraftModule;parameter:Parameter;onChange:(item:Parameter)=>void;onDelete:()=>void}) {
  /** Rename parameter without changing binder identity. @param name Syntax name. @returns Nothing. */
  function rename(name:string):void {props.onChange({...props.parameter,name});}
  /** Change exact declared schema. @param columns Ordered columns. @returns Nothing. */
  function columns(columns:Schema):void {props.onChange({...props.parameter,columns});}
  return <fieldset><legend>Parameter</legend><TextControl label="Parameter name" value={props.parameter.name} onChange={rename}/><SchemaControl module={props.module} columns={props.parameter.columns} onChange={columns}/><button onClick={props.onDelete}>Delete parameter</button></fieldset>;
}
/** Render bounded command targets and options. @param props Command/environment. @returns Controls. */
function CommandFields(props:{item:Extract<Declaration,{tag:'run'|'check'}>;module:DraftModule;onChange:(item:Declaration)=>void}) {
  /** Change exact target. @param targetId Declaration identity. @returns Nothing. */
  function target(targetId:Id):void {props.onChange({...props.item,targetId});}
  /** Change explicit bounded uniform scope. @param value Decimal scope. @returns Nothing. */
  function scope(value:string):void {props.onChange({...props.item,uniformScope:Number(value)});}
  const options:Option[]=[],scopes:Option[]=[];
  if(props.item.tag==='run') {for(const pred of props.module.predicates) if(pred.parameters.length===0) options.push({id:pred.id,label:pred.name});}
  else for(const assertion of props.module.assertions) options.push({id:assertion.id,label:assertion.name});
  for(let i=1;i<=5;i++) scopes.push({id:String(i),label:String(i)});
  return <><SelectControl label="Command target" value={props.item.targetId} options={options} onChange={target}/><SelectControl label="Uniform scope" value={String(props.item.uniformScope)} options={scopes} onChange={scope}/><p>Bitwidth4 · maxseq3</p></>;
}
