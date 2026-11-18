import {Fragment,useState,type FormEvent} from 'react';
import type {DraftModule,Field,Multiplicity,Schema,Signature} from './types';
import {deleteDeclaration,updateDeclaration} from './declarations';
import {textChange} from './controls';
import {validName} from '../model';
import {MULTIPLICITIES,appendSignature,fieldNames,fieldText,insertField,nameProblem,nextName,sourceSignatures,topLevelNames,unownedFields,withField,withSignature,withoutSignature,type SourceSignature} from './structure';
export interface StructureProps {
  readonly module:DraftModule;readonly source:string;readonly textMode:boolean;
  readonly onModule:(module:DraftModule,notice:string)=>void;
  readonly onSource:(source:string,notice:string)=>void;
  readonly onNotice:(notice:string)=>void;
}
interface Choice {readonly id:string;readonly label:string}
interface NewFieldProps {readonly owner:string;readonly ownerName:string;readonly ranges:readonly Choice[];readonly taken:ReadonlySet<string>;readonly onAdd:(name:string,multiplicity:Multiplicity,range:string)=>void;readonly onNotice:(notice:string)=>void}
const SIGNATURE_COUNT:Record<Multiplicity,string>={set:'any number of atoms',one:'exactly one atom',lone:'at most one atom',some:'at least one atom'};
const SIGNATURE_CHOICES:readonly Choice[]=[{id:'set',label:'(any)'},{id:'one',label:'one'},{id:'lone',label:'lone'},{id:'some',label:'some'}];
const FIELD_CHOICES:readonly Choice[]=[{id:'set',label:'set'},{id:'one',label:'one'},{id:'lone',label:'lone'},{id:'some',label:'some'}];
const FIELD_COUNT:Record<Multiplicity,string>={set:'set (any number)',one:'one (exactly one)',lone:'lone (zero or one)',some:'some (one or more)'};
const NO_NAMES:ReadonlySet<string>=new Set();
/** Show every signature with its fields as code-shaped cards whose add controls work while editing blocks or text. @param props Draft, source text, editing mode and change consumers. @returns Collapsible structure panel. */
export function StructurePanel(props:StructureProps) {
  const text=props.textMode?sourceSignatures(props.source):[];
  const summary=props.textMode?`${count(text.length,'signature declaration')} in the Alloy text`:`${count(props.module.signatures.length,'signature')} · ${count(props.module.fields.length,'field')}`;
  return <details className="structure-panel" id="structure-panel" open>
    <summary><span className="support-title">Signatures and fields</span><span className="support-hint">{summary}</span></summary>
    <p className={`structure-note${props.textMode?' is-text':''}`}>{props.textMode?'You are editing Alloy text, so new signatures and fields are written into the source. Rename or remove them in the text, then save.':'A signature is a set of things in your model, such as Person or File. Fields relate them, such as owner or parent. Add them at any time; the formulas below can use them straight away.'}</p>
    <div className="sig-grid">{props.textMode?<TextCards {...props} signatures={text}/>:<BlockCards {...props}/>}<NewSignature {...props} signatures={text}/></div>
  </details>;
}
/** Open the structure panel and put the cursor in the new-signature name. @returns Nothing. */
export function focusNewSignature():void {
  const panel=document.getElementById('structure-panel'),input=document.getElementById('new-signature-name');
  if(panel instanceof HTMLDetailsElement) panel.open=true;
  if(input instanceof HTMLInputElement) {input.scrollIntoView({behavior:'smooth',block:'center'});input.focus({preventScroll:true});}
}
/** Render one card per block-mode signature, plus fields that lost their owner. @param props Structure props. @returns Cards. */
function BlockCards(props:StructureProps) {
  const cards=[],orphans=unownedFields(props.module);
  for(const signature of props.module.signatures) cards.push(<SignatureCard key={signature.id} {...props} signature={signature}/>);
  if(orphans.length) cards.push(<OrphanCard key="unowned" {...props} fields={orphans}/>);
  if(!props.module.signatures.length) cards.push(<p key="empty" className="sig-empty">No signatures yet. Name your first one, for example Person or File.</p>);
  return <>{cards}</>;
}
/** Render an editable signature with its fields. @param props Structure props and the signature. @returns Signature card. */
function SignatureCard(props:StructureProps&{signature:Signature}) {
  const {module,signature}=props,rows=[];
  for(const field of module.fields) if(field.ownerSignatureId===signature.id) rows.push(<FieldRow key={field.id} {...props} field={field}/>);
  /** Rename in place; formulas refer to the signature's identity, so they follow. @param name Typed name. @returns Nothing. */
  function rename(name:string):void {const taken=topLevelNames(module);taken.delete(signature.name);props.onModule(updateDeclaration(module,{...signature,name}),nameProblem(name,taken)??`Signature renamed to ${name}.`);}
  /** Change how many atoms the signature has. @param value Multiplicity keyword. @returns Nothing. */
  function multiplicity(value:string):void {if(isMultiplicity(value)) props.onModule(updateDeclaration(module,{...signature,multiplicity:value}),`${signature.name} now has ${SIGNATURE_COUNT[value]}.`);}
  /** Remove the signature and the fields declared on it. @returns Nothing. */
  function remove():void {props.onModule(withoutSignature(module,signature),`Removed signature ${signature.name}${rows.length?` and its ${count(rows.length,'field')}`:''}. Anything else that used it is listed under Problems.`);}
  /** Add a field owned by this signature. @param name Field name. @param value Multiplicity. @param range Range signature identity. @returns Nothing. */
  function add(name:string,value:Multiplicity,range:string):void {props.onModule(withField(module,{owner:signature.id,name,multiplicity:value,range:[range]}),`Added field ${name} to ${signature.name}.`);}
  return <article className="sig-card" data-block-kind="reference" aria-label={`Signature ${signature.name}`}>
    <div className="sig-head"><Pick label={`How many ${signature.name} atoms`} value={signature.multiplicity} choices={SIGNATURE_CHOICES} onChange={multiplicity}/><code className="kw">sig</code><NameInput label="Signature name" value={signature.name} onChange={rename}/><code className="punct">{'{'}</code>
      <button type="button" className="icon-button danger-quiet" aria-label={`Delete signature ${signature.name}`} title="Delete this signature and its fields" onClick={remove}>×</button></div>
    {rows.length?<ul className="field-list">{rows}</ul>:<p className="field-empty">No fields yet.</p>}
    <NewField owner={signature.id} ownerName={signature.name} ranges={signatureChoices(module)} taken={fieldNames(module,signature.id)} onAdd={add} onNotice={props.onNotice}/>
    <code className="sig-close punct">{'}'}</code>
  </article>;
}
/** Render fields whose owner signature is missing, with an owner picker. @param props Structure props and the unowned fields. @returns Card. */
function OrphanCard(props:StructureProps&{fields:readonly Field[]}) {
  const rows=[];for(const field of props.fields) rows.push(<FieldRow key={field.id} {...props} field={field} owners/>);
  return <article className="sig-card is-orphan" aria-label="Fields without a signature"><div className="sig-head"><strong>Fields without a signature</strong></div><p className="field-empty">Choose the signature each field belongs to.</p><ul className="field-list">{rows}</ul></article>;
}
/** Render one editable field as `name : multiplicity Range`. @param props Structure props, the field, and whether to show an owner picker. @returns List item. */
function FieldRow(props:StructureProps&{field:Field;owners?:boolean}) {
  const {module,field}=props;
  /** Publish a changed field. @param next Field. @param notice Status text. @returns Nothing. */
  function update(next:Field,notice:string):void {props.onModule(updateDeclaration(module,next),notice);}
  /** Rename in place. @param name Typed name. @returns Nothing. */
  function rename(name:string):void {const taken=fieldNames(module,field.ownerSignatureId);taken.delete(field.name);update({...field,name},nameProblem(name,taken)??`Field renamed to ${name}.`);}
  /** Change the field multiplicity. @param value Keyword. @returns Nothing. */
  function multiplicity(value:string):void {if(isMultiplicity(value)) update({...field,multiplicity:value},`${field.name} is now ${FIELD_COUNT[value]}.`);}
  /** Change the range columns. @param columns Signature identities. @returns Nothing. */
  function range(columns:Schema):void {update({...field,rangeColumns:columns},`${field.name} now relates to ${columnNames(module,columns)}.`);}
  /** Move the field to another signature. @param owner Signature identity. @returns Nothing. */
  function owner(owner:string):void {update({...field,ownerSignatureId:owner},`${field.name} now belongs to ${columnNames(module,[owner])}.`);}
  /** Delete only this field. @returns Nothing. */
  function remove():void {props.onModule(deleteDeclaration(module,field),`Removed field ${field.name}.`);}
  return <li className="field-row">
    {props.owners&&<Pick label={`Signature that owns ${field.name}`} value={field.ownerSignatureId} choices={signatureChoices(module)} onChange={owner}/>}
    <NameInput label="Field name" value={field.name} onChange={rename}/><span className="punct">:</span>
    <Pick label={`Multiplicity of ${field.name}`} value={field.multiplicity} choices={FIELD_CHOICES} onChange={multiplicity}/>
    <RangeEditor module={module} columns={field.rangeColumns} label={field.name} onChange={range}/>
    <button type="button" className="icon-button danger-quiet" aria-label={`Delete field ${field.name}`} title="Delete this field" onClick={remove}>×</button>
  </li>;
}
/** Edit the ordered range columns of a field, written `A -> B`. @param props Draft, columns, field name and consumer. @returns Inline range editor. */
function RangeEditor(props:{module:DraftModule;columns:Schema;label:string;onChange:(columns:Schema)=>void}) {
  const choices=signatureChoices(props.module),items=[];
  /** Replace one column. @param position Column index. @param id Signature identity. @returns Nothing. */
  function change(position:number,id:string):void {const next=[...props.columns];next[position]=id;props.onChange(next);}
  /** Relate to one more signature. @returns Nothing. */
  function add():void {props.onChange([...props.columns,props.columns.at(-1)??''])}
  /** Drop the last column. @returns Nothing. */
  function drop():void {props.onChange(props.columns.slice(0,-1));}
  for(let i=0;i<props.columns.length;i++) items.push(<Fragment key={i}>{i>0&&<span className="punct">-&gt;</span>}<Pick label={`Range ${i+1} of ${props.label}`} value={props.columns[i]} choices={choices} onChange={change.bind(null,i)}/></Fragment>);
  return <span className="range-editor">{items}
    <button type="button" className="icon-button" aria-label={`Add a range column to ${props.label}`} title="Relate to one more signature (->)" disabled={props.columns.length>=8} onClick={add}>+</button>
    {props.columns.length>1&&<button type="button" className="icon-button" aria-label={`Remove the last range column of ${props.label}`} title="Remove the last -> column" onClick={drop}>−</button>}</span>;
}
/** Add a field from a name, multiplicity and range; an empty name gets field1, field2, … @param props Owner, range choices, used names and consumers. @returns Inline form. */
function NewField(props:NewFieldProps) {
  const [name,setName]=useState(''),[multiplicity,setMultiplicity]=useState<string>('set'),[range,setRange]=useState('');
  const chosen=hasChoice(props.ranges,range)?range:props.owner;
  /** Validate, add, and clear the name for the next field. @param event Form submission. @returns Nothing. */
  function submit(event:FormEvent):void {
    event.preventDefault();
    const value=name.trim()||nextName('field',props.taken),problem=nameProblem(value,props.taken);
    if(problem) {props.onNotice(problem);return;}
    props.onAdd(value,isMultiplicity(multiplicity)?multiplicity:'set',chosen);setName('');
  }
  return <form className="field-add" onSubmit={submit} aria-label={`Add a field to ${props.ownerName}`}>
    <label className="name-input"><span className="sr-only">New field name for {props.ownerName}</span><input value={name} placeholder="new field" spellCheck={false} onChange={textChange.bind(null,setName)}/></label><span className="punct">:</span>
    <Pick label="New field multiplicity" value={multiplicity} choices={FIELD_CHOICES} onChange={setMultiplicity}/>
    <Pick label="New field range" value={chosen} choices={props.ranges} onChange={setRange}/>
    <button type="submit" className="secondary">＋ Field</button>
  </form>;
}
/** Render text-mode cards for the signature declarations found in the source. @param props Structure props and the declarations. @returns Cards. */
function TextCards(props:StructureProps&{signatures:readonly SourceSignature[]}) {
  const ranges:Choice[]=[],cards=[];
  for(const signature of props.signatures) for(const name of signature.names) ranges.push({id:name,label:name});
  for(let i=0;i<props.signatures.length;i++) cards.push(<TextSignatureCard key={`${i}:${props.signatures[i].names.join()}`} {...props} signature={props.signatures[i]} ranges={ranges}/>);
  if(!cards.length) cards.push(<p key="empty" className="sig-empty">No signature declarations in the text yet.</p>);
  return <>{cards}</>;
}
/** Render one text signature declaration with a field form that writes into its body. @param props Structure props, declaration and range names. @returns Card. */
function TextSignatureCard(props:StructureProps&{signature:SourceSignature;ranges:readonly Choice[]}) {
  const title=props.signature.names.join(', ');
  /** Write the field into this declaration's body. @param name Field name. @param multiplicity Keyword. @param range Signature name. @returns Nothing. */
  function add(name:string,multiplicity:Multiplicity,range:string):void {
    const declaration=fieldText(name,multiplicity,range);
    props.onSource(insertField(props.source,props.signature,declaration),`Added “${declaration}” to sig ${title} in the Alloy source. Save to apply it.`);
  }
  return <article className="sig-card is-text" data-block-kind="reference" aria-label={`Signature ${title}`}>
    <div className="sig-head"><code className="kw">sig</code><code className="sig-name">{title}</code><code className="punct">{'{'}</code></div>
    <p className="field-empty">Its current fields are in the Alloy source.</p>
    <NewField owner={props.signature.names[0]} ownerName={title} ranges={props.ranges} taken={NO_NAMES} onAdd={add} onNotice={props.onNotice}/>
    <code className="sig-close punct">{'}'}</code>
  </article>;
}
/** Add a signature by name in either editing mode; an empty name gets Sig1, Sig2, … @param props Structure props and text declarations. @returns Inline form card. */
function NewSignature(props:StructureProps&{signatures:readonly SourceSignature[]}) {
  const [name,setName]=useState('');
  /** Validate and add the signature, then clear the name. @param event Form submission. @returns Nothing. */
  function submit(event:FormEvent):void {
    event.preventDefault();
    const taken=props.textMode?textNames(props.signatures):topLevelNames(props.module),value=name.trim()||nextName('Sig',taken),problem=nameProblem(value,taken);
    if(problem) {props.onNotice(problem);return;}
    if(props.textMode) props.onSource(appendSignature(props.source,value),`Added “sig ${value} {}” to the Alloy source. Save to apply it.`);
    else props.onModule(withSignature(props.module,value),`Added signature ${value}. Give it fields here, or use it in the formulas below.`);
    setName('');
  }
  return <form className="sig-card sig-new" onSubmit={submit} aria-label="Add a signature">
    <label htmlFor="new-signature-name" className="sig-new-label">New signature</label>
    <div className="sig-new-row"><code className="kw">sig</code><input id="new-signature-name" value={name} placeholder="Name, e.g. Person" spellCheck={false} onChange={textChange.bind(null,setName)}/><button type="submit" className="primary">＋ Signature</button></div>
  </form>;
}
/** Render a native select whose label is read by assistive technology. @param props Label, value, choices and consumer. @returns Compact select. */
function Pick(props:{label:string;value:string;choices:readonly Choice[];onChange:(value:string)=>void}) {
  const options=[];
  if(!hasChoice(props.choices,props.value)) options.push(<option key="unchosen" value={props.value}>Choose…</option>);
  for(const choice of props.choices) options.push(<option key={choice.id} value={choice.id}>{choice.label}</option>);
  return <label className="pick"><span className="sr-only">{props.label}</span><select value={props.value} onChange={textChange.bind(null,props.onChange)}>{options}</select></label>;
}
/** Render an inline name editor that flags names Alloy will reject. @param props Label, value and consumer. @returns Text input. */
function NameInput(props:{label:string;value:string;onChange:(value:string)=>void}) {
  const invalid=!validName(props.value);
  return <label className="name-input"><span className="sr-only">{props.label}</span><input value={props.value} size={Math.max(4,props.value.length+1)} spellCheck={false} aria-invalid={invalid||undefined} title={invalid?'Not a valid Alloy name yet':undefined} onChange={textChange.bind(null,props.onChange)}/></label>;
}
/** List signatures as range choices. @param module Draft. @returns Choices keyed by identity. */
function signatureChoices(module:DraftModule):readonly Choice[] {const result:Choice[]=[];for(const signature of module.signatures) result.push({id:signature.id,label:signature.name});return result;}
/** Spell column identities as signature names. @param module Draft. @param columns Identities. @returns Text such as `A -> B`. */
function columnNames(module:DraftModule,columns:Schema):string {
  const names:string[]=[];
  for(const id of columns) {let name='an unchosen signature';for(const signature of module.signatures) if(signature.id===id) name=signature.name;names.push(name);}
  return names.join(' -> ');
}
/** Collect every signature name declared in the text. @param signatures Declarations. @returns Names. */
function textNames(signatures:readonly SourceSignature[]):Set<string> {const names=new Set<string>();for(const signature of signatures) for(const name of signature.names) names.add(name);return names;}
/** Whether a value is among the choices. @param choices Options. @param value Candidate. @returns Membership. */
function hasChoice(choices:readonly Choice[],value:string):boolean {for(const choice of choices) if(choice.id===value) return true;return false;}
/** Narrow a select value to a multiplicity. @param value Raw value. @returns Whether it is a multiplicity keyword. */
function isMultiplicity(value:string):value is Multiplicity {return (MULTIPLICITIES as readonly string[]).includes(value);}
/** Pluralize a count. @param value Count. @param noun Singular noun. @returns Text such as `2 fields`. */
function count(value:number,noun:string):string {return `${value} ${noun}${value===1?'':'s'}`;}
