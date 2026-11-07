import type {ChangeEvent} from 'react';
import type {Controller,ViewState} from './controller';
import {checkModule,children,nodeIndex} from './model';
import type {DraftModule,Check} from './types';
import {paletteLabel} from './ExpressionEditor';
import {contentSnapshot} from './gesture';
import {useBlockComparison} from './useBlockComparison';
import type {ComparisonSelection,ModelFile} from './blockComparison';
import {BlockComparisonResults} from './BlockComparisonResults';
type ComparisonUI=ReturnType<typeof useBlockComparison>;
/** Offer explicit live-block and two-local-model comparison without editing the working model. @param props Current document/controller. @returns Bounded comparison controls. */
export function BlockComparisonPanel(props:{controller:Controller;view:ViewState;online:boolean}) {
  const ui=useBlockComparison(props.controller),state=props.view.document,checked=checkModule(state.module,state.slotObligations),options=formulaOptions(state.module,checked);
  const available=props.online&&state.mode==='BLOCK_SUPPORTED'&&!!state.accepted,enabled=available&&!ui.busy&&(ui.selection.mode==='files'?!!ui.selection.left?.predicate&&!!ui.selection.right?.predicate:checked.complete&&!!ui.selection.leftId&&!!ui.selection.rightId);
  /** Select comparison mode without changing the draft. @param event Native control. @returns Nothing. */
  function mode(event:ChangeEvent<HTMLSelectElement>):void {ui.change({...ui.selection,mode:event.target.value as ComparisonSelection['mode']});}
  /** Set bounded common solver scope. @param event Native control. @returns Nothing. */
  function scope(event:ChangeEvent<HTMLSelectElement>):void {ui.change({...ui.selection,scope:Number(event.target.value)});}
  return <section className="block-comparison" aria-label="Compare alternative formulas"><h2>Compare alternatives</h2><p>Compare both formulas on the same instance and shared variable assignment. Original declarations and all facts remain assumptions, including facts containing a selected arm. Run/check commands add no assumptions.</p><fieldset disabled={!available}><label>Comparison mode<select value={ui.selection.mode} onChange={mode}><option value="blocks">Current blocks</option><option value="files">Local model files</option></select></label><label>Uniform scope<select value={ui.selection.scope} onChange={scope}>{[1,2,3,4,5].map(scopeOption)}</select></label>{ui.selection.mode==='blocks'?<LiveArms ui={ui} options={options} selected={state.selected}/>:<div className="file-comparison-arms"><FileArm side="left" ui={ui} identity={contentSnapshot(state)+state.epoch}/><FileArm side="right" ui={ui} identity={contentSnapshot(state)+state.epoch}/></div>}<button disabled={!enabled} onClick={ui.compare}>Compare A and B</button></fieldset>{!available&&<p>Comparison unavailable while source draft is authoritative or server is offline.</p>}{ui.selection.mode==='blocks'&&!checked.complete&&<p>Complete the model before comparing live formula blocks.</p>}<p role="status" aria-live="polite">{ui.notice}</p>{ui.data&&<BlockComparisonResults data={ui.data}/>}</section>;
}
/** Render a finite scope option. @param scope Uniform bound. @returns Native option. */
function scopeOption(scope:number) {return <option key={scope} value={scope}>{scope}</option>;}
/** Select two live formula IDs or assign the currently selected forest block. @param props UI context. @returns Native arm controls. */
function LiveArms(props:{ui:ComparisonUI;options:readonly {id:string;label:string}[];selected:string|null}) {
  const {ui}=props;
  /** Select first live arm. @param event Native input. @returns Nothing. */
  function left(event:ChangeEvent<HTMLSelectElement>):void {ui.change({...ui.selection,leftId:event.target.value});}
  /** Select second live arm. @param event Native input. @returns Nothing. */
  function right(event:ChangeEvent<HTMLSelectElement>):void {ui.change({...ui.selection,rightId:event.target.value});}
  /** Assign one arm from current forest selection. @param side Arm field. @returns Nothing. */
  function assign(side:'leftId'|'rightId'):void {if(props.selected&&props.options.some(matchesOption.bind(null,props.selected))) ui.change({...ui.selection,[side]:props.selected});}
  const options=props.options.map(nodeOption),ids=new Set(props.options.map(optionIdentity));
  return <div className="live-comparison-arms"><label>Formula A<select value={ids.has(ui.selection.leftId)?ui.selection.leftId:''} onChange={left}><option value="">Select formula A</option>{options}</select></label><button disabled={!props.selected||!ids.has(props.selected)} onClick={assign.bind(null,'leftId')}>Use selected block as A</button><label>Formula B<select value={ids.has(ui.selection.rightId)?ui.selection.rightId:''} onChange={right}><option value="">Select formula B</option>{options}</select></label><button disabled={!props.selected||!ids.has(props.selected)} onClick={assign.bind(null,'rightId')}>Use selected block as B</button></div>;
}
/** Match selectable node identity. @param id Selection. @param option Formula choice. @returns Match. */
function matchesOption(id:string,option:{id:string}):boolean {return id===option.id;}
/** Return a node option identity. @param option Choice. @returns Identity. */
function optionIdentity(option:{id:string}):string {return option.id;}
/** Render a labeled formula option. @param option Choice. @returns Native option. */
function nodeOption(option:{id:string;label:string}) {return <option key={option.id} value={option.id}>{option.label}</option>;}
/** Provide one local file picker and only parser-derived predicate choices. @param props Arm and UI context. @returns Native upload controls. */
function FileArm(props:{side:'left'|'right';ui:ComparisonUI;identity:string}) {
  const {side,ui}=props,model=ui.selection[side],label=side==='left'?'A':'B',current=model?.inspection===props.identity,options=[];
  for(const predicate of model?.predicates??[]) options.push(<option key={predicate.name} value={predicate.name}>{predicate.name}({predicate.parameters.map(parameterLabel).join(', ')})</option>);
  /** Read a chosen file into bounded in-memory state. @param event Native picker. @returns Nothing. */
  function file(event:ChangeEvent<HTMLInputElement>):void {void ui.upload(side,event.target.files?.[0]??null);event.target.value='';}
  /** Select an inspected predicate and invalidate previous evidence. @param event Native select. @returns Nothing. */
  function predicate(event:ChangeEvent<HTMLSelectElement>):void {if(model) ui.change({...ui.selection,[side]:{...model,predicate:event.target.value}});}
  /** Remove uploaded source from memory. @returns Nothing. */
  function remove():void {void ui.upload(side,null);}
  /** Reinspect exact source after a draft identity change. @returns Nothing. */
  function inspect():void {if(model) void ui.inspect(side,model);}
  return <fieldset><legend>Model file {label}</legend><label>Local Alloy file {label}<input type="file" accept=".als,text/plain" onChange={file} disabled={ui.busy}/></label>{model&&<><p>{model.filename} · {new TextEncoder().encode(model.source).length} bytes</p><button onClick={remove}>Remove file {label}</button><button disabled={ui.busy} onClick={inspect}>Inspect file {label}</button><label>Predicate {label}<select disabled={!current||ui.busy} value={current?model.predicate:''} onChange={predicate}><option value="">Select parsed predicate</option>{current&&options}</select></label>{!current&&<p>Inspection required for this draft.</p>}<details><summary>Local source {label}</summary><p>Source SHA256: {model.sourceHash}</p><pre>{model.source}</pre></details></>}<p>Maximum 32 KiB; kept in memory. Models must share the same checked background. Selected parameters pair by position and schema; differing backgrounds are rejected.</p></fieldset>;
}
/** Format a parsed parameter schema. @param parameter Parsed descriptor. @returns Label. */
function parameterLabel(parameter:ModelFile['predicates'][number]['parameters'][number]):string {return `${parameter.name}: ${parameter.columns.join(' → ')}`;}

/** Name formula choices by declaration and ownership path rather than opaque node IDs. @param module Current forest. @param checked Current types. @returns Human-readable formula options. */
function formulaOptions(module:DraftModule,checked:Check):{id:string;label:string}[] {
  const options:{id:string;label:string}[]=[],index=nodeIndex(module),seen=new Set<string>(),queue:{id:string;path:string}[]=[];
  for(const declaration of [...module.predicates,...module.facts,...module.assertions]) queue.push({id:declaration.bodyId,path:`${declaration.tag} ${declaration.name}`});
  while(queue.length) {
    const item=queue.shift()!;if(seen.has(item.id)) continue;seen.add(item.id);
    const node=index.get(item.id);if(!node) continue;
    const label=node.tag==='hole'?'Unresolved hole':paletteLabel(node.tag),path=`${item.path} / ${label}`;
    if(checked.types.get(node.id)?.kind==='formula') options.push({id:node.id,label:path});
    const owned=children(node);for(let position=0;position<owned.length;position++) queue.push({id:owned[position],path:`${path} (${owned.length===1?'body':position===0?'left':'right'})`});
  }
  return options;
}
