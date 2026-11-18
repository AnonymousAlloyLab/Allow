import type {ChangeEvent} from 'react';
import type {DraftModule} from './types';
import type {useOracleParity} from './useOracleParity';
type ParityUI=ReturnType<typeof useOracleParity>;
/** Offer explicit memory-only oracle configuration and bounded checking. @param props Current controls and module. @returns Compact panel. */
export function OracleParityPanel(props:{ui:ParityUI;module:DraftModule;online:boolean}) {
  const {ui}=props,selection=ui.selection,oracle=selection.oracle,predicates=props.module.predicates.map(predicateOption),choices=oracle?.predicates.map(oracleOption);
  /** Update the selected current predicate declaration. @param event Native selection. @returns Nothing. */
  function target(event:ChangeEvent<HTMLSelectElement>):void {ui.change({...selection,targetId:event.target.value});}
  /** Update the parsed oracle predicate. @param event Native selection. @returns Nothing. */
  function predicate(event:ChangeEvent<HTMLSelectElement>):void {if(oracle) ui.change({...selection,oracle:{...oracle,predicate:event.target.value}});}
  /** Update the common scope. @param event Native selection. @returns Nothing. */
  function scope(event:ChangeEvent<HTMLSelectElement>):void {ui.change({...selection,scope:Number(event.target.value)});}
  /** Toggle parity without preserving previous binding evidence. @param event Native checkbox. @returns Nothing. */
  function enable(event:ChangeEvent<HTMLInputElement>):void {ui.change({...selection,enabled:event.target.checked});}
  /** Read one user-designated local reference. @param event Native file input. @returns Nothing. */
  function file(event:ChangeEvent<HTMLInputElement>):void {void ui.upload(event.target.files?.[0]??null);event.target.value='';}
  /** Remove memory-only oracle contents. @returns Nothing. */
  function remove():void {void ui.upload(null);}
  return <section className="oracle-parity" aria-label="Oracle parity"><details open={selection.enabled||undefined}><summary>Oracle parity · compare a predicate with a reference model you upload</summary><p>A user-designated reference is not a correctness guarantee. Complete both models with matching background and ordered parameter schemas. Oracle source stays in this session; it is not sent to an LLM.</p><fieldset disabled={!props.online}><label>Oracle .als file<input type="file" accept=".als" onChange={file}/></label>{oracle&&<><p>{oracle.filename} · {new TextEncoder().encode(oracle.source).length} bytes</p><button onClick={remove}>Remove oracle</button><button onClick={ui.inspect}>Inspect oracle</button><label>Oracle predicate<select value={oracle.predicate} onChange={predicate}><option value="">Select parsed predicate</option>{choices}</select></label></>}<label>Current predicate<select value={selection.targetId} onChange={target}><option value="">Select predicate</option>{predicates}</select></label><label>Parity scope<select value={selection.scope} onChange={scope}>{[1,2,3,4,5].map(scopeOption)}</select></label><label className="parity-toggle"><input type="checkbox" checked={selection.enabled} onChange={enable}/> Enable automatic parity</label><button disabled={!ui.ready||ui.busy} onClick={ui.check}>Check parity</button></fieldset></details><p role="status" aria-live="polite">{ui.notice}</p>{selection.enabled&&!ui.ready&&<p>Parity is neutral. Complete the whole visual module, select both predicates and connect to the server.</p>}</section>;
}
/** Render a declaration identity option. @param predicate Current predicate. @returns Native option. */
function predicateOption(predicate:{id:string;name:string}) {return <option key={predicate.id} value={predicate.id}>{predicate.name}</option>;}
/** Render only parser-derived oracle choices. @param predicate Oracle descriptor. @returns Native option. */
function oracleOption(predicate:{name:string}) {return <option key={predicate.name} value={predicate.name}>{predicate.name}</option>;}
/** Render one finite common scope. @param scope Bound. @returns Native option. */
function scopeOption(scope:number) {return <option key={scope} value={scope}>{scope}</option>;}
