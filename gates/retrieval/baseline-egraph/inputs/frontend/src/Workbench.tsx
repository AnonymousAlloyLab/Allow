import { useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, MouseEvent } from 'react';
import { PALETTE, atPath, complete, hole, paletteNode, reference, renderModule, replaceNode, validName } from './model';
import type { Node, PaletteItem } from './model';
import { cancelSnapshot, isCurrent, readJob, sameIdentity, submit } from './api';
import type { Job, JobIdentity } from './api';
import { TreeView } from './TreeView';
import { Results } from './Results';
const initialSource = 'sig Person {}\n\npred model { some Person }\nrun model for 3\n';
const initialTree: Node = {op:'some',kind:'formula',children:[reference('Person')]};
const terminal = new Set(['VALIDATED','SAT','UNSAT','INVALID','UNSUPPORTED','UNKNOWN','ERROR','TIMEOUT','CANCELLED']);
interface Props { token: string }
/** Create isolated workbench state. @param token In-memory authority. @returns State and setters. */
function useWorkspace(token: string) {
  const [names,setNames] = useState<readonly string[]>(['Person']);
  const [newName,setNewName] = useState('');
  const [tree,setTree] = useState<Node>(initialTree);
  const [selected,setSelected] = useState<readonly number[]>([]);
  const [source,setSource] = useState(initialSource);
  const [mode,setMode] = useState<'composer'|'text'>('composer');
  const [revision,setRevision] = useState(0);
  const [epoch,setEpoch] = useState(0);
  const [job,setJob] = useState<Job | null>(null);
  const [notice,setNotice] = useState('Select a slot, then choose a block.');
  const current = useRef({revision:0,epoch:0});
  const active = useRef('');
  const activeHash = useRef('');
  return {token,names,setNames,newName,setNewName,tree,setTree,selected,setSelected,source,setSource,mode,setMode,revision,setRevision,epoch,setEpoch,job,setJob,notice,setNotice,current,active,activeHash};
}
type State = ReturnType<typeof useWorkspace>;
/** Invalidate old results immediately. @param state Workbench state. @returns Nothing. */
function invalidate(state: State): void {
  state.current.current = {...state.current.current,epoch:state.current.current.epoch + 1};
  state.setEpoch(state.current.current.epoch); state.setJob(null); state.active.current = '';
  state.activeHash.current = '';
}
/** Insert a compatible item into the candidate. @param state Workbench state. @param path Target path. @param item Block identifier. @returns Nothing. */
function insert(state: State, path: readonly number[], item: string): void {
  const replacement = paletteNode(item,state.names);
  const target = atPath(state.tree,path);
  if (!replacement) { state.setNotice('Choose a declared relation or a supported palette block.'); return; }
  if (!target || target.kind !== replacement.kind) { state.setNotice(`This slot needs ${target?.kind ?? 'a valid item'}.`); return; }
  invalidate(state); state.setTree(replaceNode(state.tree,path,replacement)); state.setSelected(path);
  state.setNotice('Candidate changed. Apply it to validate before committing.');
}
/** Record a draggable palette item. @param event Drag event. @returns Nothing. */
function startDrag(event: DragEvent<HTMLButtonElement>): void { event.dataTransfer.setData('text/plain',event.currentTarget.value); }
/** Insert an activated palette item. @param state Workbench state. @param event Button event. @returns Nothing. */
function choose(state: State, event: MouseEvent<HTMLButtonElement>): void { insert(state,state.selected,event.currentTarget.value); }
/** Update the signature draft. @param state Workbench state. @param event Input event. @returns Nothing. */
function changeName(state: State, event: ChangeEvent<HTMLInputElement>): void { state.setNewName(event.target.value); }
/** Add a valid signature to the candidate. @param state Workbench state. @returns Nothing. */
function addName(state: State): void {
  const name = state.newName.trim();
  if (!validName(name) || state.names.includes(name)) { state.setNotice('Use a unique simple Alloy identifier that is not a keyword.'); return; }
  invalidate(state); state.setNames([...state.names,name]); state.setNewName(''); state.setNotice(`Added ${name} to the candidate.`);
}
/** Clear a selected slot. @param state Workbench state. @returns Nothing. */
function clearSlot(state: State): void {
  const target = atPath(state.tree,state.selected);
  if (!target) return;
  invalidate(state); state.setTree(replaceNode(state.tree,state.selected,hole(target.kind))); state.setNotice('Slot cleared.');
}
/** Switch to a raw text draft on edit. @param state Workbench state. @param event Text input event. @returns Nothing. */
function changeSource(state: State, event: ChangeEvent<HTMLTextAreaElement>): void {
  invalidate(state); state.setSource(event.target.value); state.setMode('text');
  state.setNotice('Text-only draft. Blocks are no longer a projection of this text.');
}
/** Reopen a separate composer candidate. @param state Workbench state. @returns Nothing. */
function startComposer(state: State): void { invalidate(state); state.setMode('composer'); state.setNotice('Composer is a separate candidate; apply to validate it.'); }
/** Schedule a polling delay. @param resolve Promise resolver. @returns Nothing. */
function resolveDelay(resolve: () => void): void { window.setTimeout(resolve,250); }
/** Wait between requests. @returns Delay promise. */
function delay(): Promise<void> { return new Promise(resolveDelay); }
/** Poll until terminal while checking identity. @param state Workbench state. @param first Initial job. @returns Terminal job or null when stale. */
async function waitJob(state: State, first: Job): Promise<Job | null> {
  let result = first;
  while (!terminal.has(result.status)) {
    if (!sameIdentity(result,activeIdentity(state))) return null;
    await delay(); result = await readJob(state.token,result.jobId);
  }
  if (!sameIdentity(result,activeIdentity(state))) return null;
  return result;
}
/** Compute the exact UTF-8 source digest. @param text Source snapshot. @returns Lowercase SHA-256. */
async function sourceHash(text: string): Promise<string> {
  const bytes = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes),hexByte).join('');
}
/** Format one byte. @param value Byte value. @returns Two lowercase hex digits. */
function hexByte(value: number): string { return value.toString(16).padStart(2,'0'); }
/** Commit validated source. @param state Workbench state. @param text Validated source. @returns Nothing. */
function commitCandidate(state: State, text: string): void {
  state.current.current = {...state.current.current,revision:state.current.current.revision + 1};
  state.setRevision(state.current.current.revision); state.setSource(text); state.setJob(null); state.setNotice('Composer candidate validated and applied.');
}
/** Submit and track one snapshot. @param state Workbench state. @param text Source. @param operation Job type. @param commit Commit after validation. @returns Completion promise. */
async function execute(state: State, text: string, operation: 'VALIDATE'|'ANALYZE', commit: boolean): Promise<void> {
  if (!state.token) { state.setNotice('Launch authority is missing. Open the local launch link again.'); return; }
  invalidate(state); const snapshot = {...state.current.current};
  state.setNotice(operation === 'VALIDATE' ? 'Validating candidate…' : 'Running bounded analysis…');
  try {
    const hash = await sourceHash(text);
    const first = await submit(state.token,text,snapshot.revision,snapshot.epoch,operation);
    if (!isCurrent(first,state.current.current.revision,state.current.current.epoch) || first.sourceHash !== hash) return;
    state.active.current = first.jobId; state.activeHash.current = hash; state.setJob(first);
    const result = await waitJob(state,first);
    if (!result || result.sourceHash !== hash) return;
    state.setJob(result); state.setNotice(`Job finished: ${result.status}.`);
    if (commit && result.status === 'VALIDATED') commitCandidate(state,text);
  } catch (error) { if (state.current.current.epoch === snapshot.epoch) state.setNotice(error instanceof Error ? error.message : 'Request failed.'); }
}
/** Validate and apply the candidate. @param state Workbench state. @returns Nothing. */
function apply(state: State): void {
  if (!complete(state.tree)) { state.setNotice('Fill every typed slot before applying.'); return; }
  void execute(state,renderModule(state.names,state.tree),'VALIDATE',true);
}
/** Validate the source draft. @param state Workbench state. @returns Nothing. */
function validate(state: State): void { void execute(state,state.source,'VALIDATE',false); }
/** Analyze the source draft. @param state Workbench state. @returns Nothing. */
function analyze(state: State): void { void execute(state,state.source,'ANALYZE',false); }
/** Cancel the active job. @param state Workbench state. @returns Completion promise. */
async function cancel(state: State): Promise<void> {
  const snapshot = activeIdentity(state);
  if (!snapshot.jobId) return;
  const outcome = await cancelSnapshot(state.token,snapshot,activeIdentity.bind(null,state));
  if (!outcome || !sameIdentity(snapshot,activeIdentity(state))) return;
  if (outcome.job) state.setJob(outcome.job);
  if (outcome.error) state.setNotice(outcome.error);
}
/** Read the active job's source-bound presentation identity. @param state Workbench state. @returns Current job, source hash, revision and epoch. */
function activeIdentity(state: State): JobIdentity {
  return {...state.current.current,jobId:state.active.current,sourceHash:state.activeHash.current};
}
/** Render one palette control. @param state Workbench state. @param item Palette entry. @returns Draggable button. */
function paletteButton(state: State, item: PaletteItem) {
  return <button key={item.op} value={item.op} draggable onDragStart={startDrag} onClick={choose.bind(null,state)}><span>{item.label}</span><small>{item.kind}</small></button>;
}
/** Render one signature control. @param state Workbench state. @param name Signature name. @returns Draggable button. */
function nameButton(state: State, name: string) {
  return <button key={name} value={`ref:${name}`} draggable onDragStart={startDrag} onClick={choose.bind(null,state)}><span>{name}</span><small>relation</small></button>;
}
/** Render the palette. @param props Workbench state. @returns Palette panel. */
function Palette(props: {state: State}) {
  const state = props.state;
  return <aside className="panel palette"><div className="panel-title"><div><span className="panel-index">01</span><h2>Library</h2></div><span>BLOCKS</span></div>
    <p className="hint">Drag a block into a slot, or select a slot and choose a block.</p><h3>DECLARATIONS</h3><div className="name-entry"><label className="sr-only" htmlFor="signature">Signature name
    </label><input id="signature" value={state.newName} onChange={changeName.bind(null,state)} placeholder="Signature name"/><button onClick={addName.bind(null,state)} aria-label="Add signature">+
    </button></div><div className="palette-list">{state.names.map(nameButton.bind(null,state))}</div><h3>LOGIC & RELATIONS</h3>
    <div className="palette-list">{PALETTE.map(paletteButton.bind(null,state))}</div>
    <div className="scope-note">Initial subset · unary signatures, Boolean gates, relation union and multiplicity tests.</div></aside>;
}
/** Render the visual composer. @param props Workbench state. @returns Composer panel. */
function Composer(props: {state: State}) {
  const state = props.state;
  return <section className="panel canvas"><div className="panel-title"><div><span className="panel-index">02</span><h2>Composer</h2></div><span>{state.mode === 'composer' ? 'CANDIDATE' : 'TEXT ONLY'}
    </span></div>{state.mode === 'text' ? <div className="empty-state"><div className="empty-icon">◇</div><h3>Text draft active</h3>
    <p>The previous blocks are not a projection of this draft. Start a separate composer candidate to continue visually.</p>
    <button className="secondary" onClick={startComposer.bind(null,state)}>Open composer candidate</button></div> : <><p className="hint">Select a block to replace it. Dashed slots need a value.</p>
    <div className="tree-area"><TreeView node={state.tree} path={[]} selected={state.selected.join('.')} onSelect={state.setSelected} onDropItem={insert.bind(null,state)}/></div>
    <div className="canvas-actions"><button className="secondary" onClick={clearSlot.bind(null,state)}>Clear selected</button>
    <button className="primary" onClick={apply.bind(null,state)}>Validate & apply ↗</button></div></>}</section>;
}
/** Render the source editor and analysis. @param props Workbench state. @returns Source panel. */
function SourcePanel(props: {state: State}) {
  const state = props.state;
  return <section className="panel code"><div className="panel-title"><div><span className="panel-index">03</span><h2>Alloy source</h2></div><span>EDITABLE</span></div>
    <label className="sr-only" htmlFor="source">Alloy source editor</label><textarea id="source" spellCheck={false} value={state.source} onChange={changeSource.bind(null,state)}/>
    <div className="code-actions"><button className="secondary" onClick={validate.bind(null,state)}>Validate</button><button className="primary" onClick={analyze.bind(null,state)}>Run analysis ↗
    </button><button className="quiet" onClick={cancel.bind(null,state)}>Cancel</button></div><Results job={state.job} notice={state.notice}/></section>;
}
/** Render the local workbench. @param props Launch authority in memory. @returns Workbench interface. */
export function Workbench(props: Props) {
  const state = useWorkspace(props.token);
  return <main><header className="top"><div className="brand"><span className="brand-mark">A</span><div><strong>allow</strong><small>ALLOY WORKBENCH</small></div></div>
    <div className="top-meta">● LOCAL SESSION　 /　 REV {state.revision} · EDIT {state.epoch}</div></header><section className="intro"><div><p className="eyebrow">MODEL WITH CLARITY / 01</p>
    <h1>Make ideas <em>precise.</em></h1><p>Compose a model visually, inspect its Alloy source, and explore bounded results.</p></div><div className="intro-note"><span>LOCAL BY DESIGN</span>
    <p>Your model stays in this local session.</p></div></section><div className="workspace"><Palette state={state}/><Composer state={state}/><SourcePanel state={state}/></div><footer>
    <span>ALLOW / LOCAL WORKBENCH</span><span>BUILT FOR THOUGHTFUL MODELING</span></footer></main>;
}
