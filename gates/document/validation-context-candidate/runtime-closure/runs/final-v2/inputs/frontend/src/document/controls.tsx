import type {ChangeEvent} from 'react';
import type {DraftModule,Id,Schema,Multiplicity} from './types';
export interface Option {readonly id:string;readonly label:string}
/** Dispatch exact text input. @param callback Consumer. @param event Input. @returns Nothing. */
export function textChange(callback:(value:string)=>void,event:ChangeEvent<HTMLInputElement|HTMLSelectElement>):void {callback(event.target.value);}
/** Render a labeled input. @param props Label/value/consumer. @returns Native control. */
export function TextControl(props:{label:string;value:string;onChange:(value:string)=>void}) {
  return <label>{props.label}<input value={props.value} onChange={textChange.bind(null,props.onChange)}/></label>;
}
/** Render an exact-ID picker. @param props Label/options/value. @returns Native select. */
export function SelectControl(props:{label:string;value:string;options:readonly Option[];onChange:(value:string)=>void}) {
  const options=[];for(const option of props.options) options.push(<option key={option.id} value={option.id}>{option.label}</option>);
  return <label>{props.label}<select value={props.value} onChange={textChange.bind(null,props.onChange)}><option value="">Choose explicitly</option>{options}</select></label>;
}
/** Build signature options using identity values. @param module Environment. @returns Options. */
export function signatureOptions(module:DraftModule):readonly Option[] {const result:Option[]=[];for(const sig of module.signatures) result.push({id:sig.id,label:sig.name});return result;}
/** Render declared multiplicity. @param props Current value and consumer. @returns Picker. */
export function MultiplicityControl(props:{value:Multiplicity;onChange:(value:Multiplicity)=>void}) {
  /** Dispatch a closed multiplicity. @param value Selected option. @returns Nothing. */
  function change(value:string):void {if(['set','one','lone','some'].includes(value)) props.onChange(value as Multiplicity);}
  const options:Option[]=[];for(const value of ['set','one','lone','some']) options.push({id:value,label:value});
  return <SelectControl label="Multiplicity" value={props.value} options={options} onChange={change}/>;
}
/** Render editable ordered nominal columns. @param props Schema and consumer. @returns Accessible ordered editor. */
export function SchemaControl(props:{module:DraftModule;columns:Schema;onChange:(columns:Schema)=>void}) {
  /** Change one column without mutating others. @param position Column index. @param id Signature. @returns Nothing. */
  function change(position:number,id:Id):void {const next=[...props.columns];next[position]=id;props.onChange(next);}
  /** Append an explicit unresolved column. @returns Nothing. */
  function add():void {props.onChange([...props.columns,'']);}
  /** Remove the last column, retaining nonempty schema shape. @returns Nothing. */
  function remove():void {props.onChange(props.columns.slice(0,-1));}
  const columns=[];
  for(let i=0;i<props.columns.length;i++) columns.push(<SelectControl key={i} label={`Column ${i+1}`} value={props.columns[i]} options={signatureOptions(props.module)} onChange={change.bind(null,i)}/>);
  return <fieldset><legend>Ordered nominal schema (set-valued)</legend>{columns}<button type="button" disabled={props.columns.length>=8} onClick={add}>Add column</button><button type="button" disabled={props.columns.length<=1} onClick={remove}>Remove last column</button></fieldset>;
}
