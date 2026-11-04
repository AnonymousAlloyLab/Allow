import { useId, useState } from 'react';
import type { ChangeEvent } from 'react';
import type { EGraphIsland, EGraphView, GraphClass, GraphEdge } from './egraph';
import { anonymousJson, islandLabel } from './egraph';
import { certificateLabel, searchCaption, stopLabel } from './egraphLabels';
/** Render one graph class as a readable alternative to the visual preview. @param value Anonymous e-class. @returns Class inventory item. */
function classText(value: GraphClass) {
  return <li key={value.id}><strong>Class {value.id}</strong>: {value.nodes.map(operatorName).join(', ') || 'No displayed nodes'}</li>;
}
/** Read an operator without exposing opaque atom payload in graph labels. @param term Anonymous node. @returns Closed operator tag. */
function operatorName(term: GraphClass['nodes'][number]): string { return term.op; }
/** Render one schematic e-class card. @param value Anonymous e-class. @param index Stable layout position. @returns SVG group. */
function classCard(value: GraphClass, index: number) {
  const x = (index % 3) * 176 + 14;
  const y = Math.floor(index / 3) * 110 + 20;
  return <g key={value.id} transform={`translate(${x},${y})`}><rect width="146" height="52" rx="7"/>
    <text x="9" y="19">Class {value.id}</text><text x="9" y="37" className="graph-ops">{value.nodes.map(operatorName).join(' · ').slice(0,18)}</text></g>;
}
/** Locate the center of a displayed class card. @param classes Displayed class inventory. @param id Class identifier. @returns Coordinate or undefined. */
function classPoint(classes: readonly GraphClass[], id: number): {x: number; y: number} | undefined {
  const index = classes.findIndex(matchesClass.bind(null,id));
  return index < 0 ? undefined : {x:(index % 3) * 176 + 87,y:Math.floor(index / 3) * 110 + 46};
}
/** Match one exact displayed class identifier. @param id Class identifier. @param value Candidate class. @returns Whether identifiers match. */
function matchesClass(id: number, value: GraphClass): boolean { return value.id === id; }
/** Render a directed parent-to-child class dependency. @param classes Displayed cards. @param marker Unique SVG arrow marker. @param edge Ordered dependency. @param index Stable edge position. @returns SVG path and argument label. */
function graphEdge(classes: readonly GraphClass[], marker: string, edge: GraphEdge, index: number) {
  const from = classPoint(classes,edge.from);
  const to = classPoint(classes,edge.to);
  if (!from || !to) return null;
  const self = edge.from === edge.to;
  const bend = 25 + (edge.position % 3) * 9;
  const path = self ? `M ${from.x + 58} ${from.y} C ${from.x + 100} ${from.y - 58}, ${from.x - 20} ${from.y - 58}, ${from.x} ${from.y - 27}`
    : `M ${from.x} ${from.y + 26} Q ${(from.x + to.x) / 2 + bend} ${(from.y + to.y) / 2 + 38}, ${to.x} ${to.y + 29}`;
  return <g className="graph-edge" key={`${edge.from}:${edge.to}:${edge.position}:${index}`}><path d={path} markerEnd={`url(#${marker})`}/>
    <text x={self ? from.x + 76 : (from.x + to.x) / 2 + bend / 2} y={self ? from.y - 30 : (from.y + to.y) / 2 + 48}>{edge.position + 1}</text></g>;
}
/** Render a dependency as accessible text. @param edge Ordered child relation. @param index Stable edge position. @returns Dependency list item. */
function edgeText(edge: GraphEdge, index: number) {
  return <li key={`${edge.from}:${edge.to}:${edge.position}:${index}`}>Class {edge.from} → class {edge.to} · child {edge.position + 1}</li>;
}
/** Dedupe visible edges while retaining operator child positions. @param island Preview owner. @returns Stable unique edges. */
function previewEdges(island: EGraphIsland): readonly GraphEdge[] {
  const seen = new Set<string>();
  const result: GraphEdge[] = [];
  for (const edge of island.preview.edges ?? []) {
    const key = `${edge.from}:${edge.to}:${edge.position}`;
    if (!seen.has(key)) { seen.add(key); result.push(edge); }
  }
  return result;
}
/** Show bounded classes and directed child dependencies with a textual alternative. @param props Island data. @returns Graph preview. */
function GraphPreview(props: {island: EGraphIsland}) {
  const marker = `arrow-${useId().replace(/:/g,'')}`;
  const classes = props.island.preview.classes ?? [];
  const edges = previewEdges(props.island);
  const height = Math.max(110,Math.ceil(classes.length / 3) * 110 + 30);
  return <details><summary>Graph preview · {classes.length} displayed classes</summary>
    {classes.length > 0 ? <><div className="egraph-scroll"><svg className="egraph-svg" viewBox={`0 0 540 ${height}`} role="img" aria-label="Anonymous e-class membership and directed child dependencies">
      <title>Arrows connect parent classes to child classes; numbers are child positions</title>
      <defs><marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>
      {edges.map(graphEdge.bind(null,classes,marker))}{classes.map(classCard)}</svg></div>
      <ol className="graph-text">{classes.map(classText)}</ol>
      <details><summary>Directed child dependencies · {edges.length}</summary><ul className="graph-text">{edges.map(edgeText)}</ul>
        {!edges.length && <p>No child dependencies are displayed.</p>}</details></> : <p>No graph preview is available.</p>}
    {props.island.preview.truncated && <p>Graph preview is truncated; search termination is reported separately.</p>}
    <p>Arrows point from parent to child class. Numbers identify ordered child positions; cards group equivalent nodes.</p>
    <details><summary>Complete displayed graph data</summary><pre>{anonymousJson(props.island.preview)}</pre></details>
  </details>;
}
/** Render one numeric engine counter. @param entry Counter name and value. @returns Statistic item. */
function statistic(entry: [string,number]) { return <div key={entry[0]}><dt>{entry[0]}</dt><dd>{entry[1]}</dd></div>; }
/** Inspect or download only the certificate attached to this current result. @param props Island and anonymous download label. @returns Proof details. */
function ProofDetails(props: {island: EGraphIsland}) {
  const value = props.island;
  const encoded = value.certificate ? `data:application/json;charset=utf-8,${encodeURIComponent(anonymousJson(value.certificate))}` : null;
  return <details><summary>Proof details</summary><p>Local replay checks concrete endpoints and supported rules. The running JVM and parser are not verified by Lean.</p>
    <pre>{anonymousJson(value.proofSummary)}</pre>
    {encoded && <><a className="certificate-download" href={encoded} download={`allow-proof-${value.rootPath.join('-') || '0'}.json`}>Download anonymous certificate</a>
      <details><summary>Inspect certificate</summary><pre>{anonymousJson(value.certificate)}</pre></details></>}
  </details>;
}
/** Render one read-only anonymous extraction with independent evidence and search states. @param props Selected optimization island. @returns Island result. */
function IslandDetails(props: {island: EGraphIsland}) {
  const value = props.island;
  const checked = value.certificateStatus === 'CHECKED' && value.input !== null && value.extracted !== null;
  return <section className="egraph-island" aria-label={islandLabel(value)}><div className="egraph-badges">
    <span className={checked ? 'evidence checked' : 'evidence'}>{certificateLabel(checked ? 'CHECKED' : value.certificateStatus === 'CHECKED' ? 'UNAVAILABLE' : value.certificateStatus)}</span>
    <span className="termination">{stopLabel(value.stopReason)}</span></div>
    <p>{checked ? searchCaption(value.stopReason) : 'No checked extracted-equivalence result is available for this root.'}</p>
    {checked && <><div className="extraction-cost"><span>Tree cost</span><strong>{value.inputCost} → {value.extractedCost}</strong><small>Unit cost per node occurrence</small></div>
      <details open><summary>Anonymous extracted term</summary><pre>{anonymousJson(value.extracted)}</pre></details>
      <details><summary>Anonymous input term</summary><pre>{anonymousJson(value.input)}</pre></details></>}
    <dl className="graph-statistics">{Object.entries(value.stats).map(statistic)}</dl>
    <GraphPreview island={value}/><ProofDetails island={value}/>
  </section>;
}
/** Render an anonymous root option. @param value Island. @param index Stable island position. @returns Native selection option. */
function islandOption(value: EGraphIsland, index: number) { return <option key={`${index}:${value.rootPath.join('.')}`} value={index}>{islandLabel(value)} · {value.certificateStatus}</option>; }
/** Present source-bound optimizations without mutating original source or structural features. @param props Anonymous egraph result. @returns Read-only optimization panel. */
export function EGraphPanel(props: {value: EGraphView}) {
  const [selected,setSelected] = useState(0);
  const id = useId();
  const value = props.value;
  const island = value.islands[selected] ?? value.islands[0];
  /** Select an anonymous occurrence using the native keyboard-accessible control. @param event Selection event. @returns Nothing. */
  function selectIsland(event: ChangeEvent<HTMLSelectElement>): void { setSelected(Number(event.target.value)); }
  return <section className="egraph-panel" aria-label="Anonymous equality optimization"><div className="egraph-heading"><h4>Equality optimization</h4><span>READ ONLY</span></div>
    <p>Anonymous views of supported expression roots. Original Alloy source and its bounded analysis remain unchanged. Different extracted terms do not prove inequivalence.</p>
    <p className="egraph-status">{value.islands.length} root{value.islands.length === 1 ? '' : 's'} · Module status: {value.status}</p>
    {value.truncated && <p className="egraph-warning">Module output is truncated; not every root is represented. This does not establish complete optimization.</p>}
    {island ? <><label htmlFor={id}>Expression root</label><select id={id} value={Math.min(selected,value.islands.length - 1)} onChange={selectIsland}>{value.islands.map(islandOption)}</select>
      <IslandDetails island={island}/></> : <p>No optimization islands are available. No extracted equivalence is claimed.</p>}
    <details><summary>Optimization profile</summary><p>{value.profile}</p><p>Rule registry digest: {value.rulesetDigest}</p><p>Digests identify artifacts; digest equality alone is not an equivalence proof.</p></details>
  </section>;
}
