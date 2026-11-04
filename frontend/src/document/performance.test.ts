import {expect,test} from 'vitest';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {cpus,totalmem,platform,release,arch,hostname} from 'node:os';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import type {DraftModule,Expression,Id} from './types';
import {emptyModule,checkModule,children} from './model';
import {slotConstraints} from './operations';
import {Fixture,TAGS} from './fixtures';
const NODE=(globalThis as unknown as {process:{version:string;versions:{v8:string}}}).process;
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const A='server:00000000-0000-4000-8000-000000001000';
const B='server:00000000-0000-4000-8000-000000001001';
const PREDICATE='server:00000000-0000-4000-8000-000000001002';
interface EditEvent {readonly nodeId:Id;readonly targetId:Id}
interface BenchFixture {readonly module:DraftModule;readonly source:string;readonly references:readonly Id[];readonly edits:readonly EditEvent[]}
/** Generate a deterministic balanced tree:167 two-node leaves plus166 binary nodes equals500. */
class BalancedFixture {
  private readonly nodes:Expression[]=[];
  private readonly references:Id[]=[];
  private counter=0;
  /** Allocate a deterministic, distinct fixture identity. @returns Fixture-only draft UUID. */
  private id():Id {this.counter++;return `draft:00000000-0000-4000-8000-${this.counter.toString(16).padStart(12,'0')}`;}
  /** Append one complete owned node. @param node Closed constructor. @returns Node identity. */
  private add(node:Expression):Id {this.nodes.push(node);return node.id;}
  /** Build one formula leaf with an exact unary nominal reference. @returns Formula root identity. */
  private leaf():Id {
    const id=this.id(),targetId=this.references.length%2===0?A:B;
    this.add({tag:'signature_ref',id,targetId});this.references.push(id);
    return this.add({tag:'some_test',id:this.id(),operandId:id});
  }
  /** Balance each conjunction by leaf count, keeping left/right order explicit. @param count Number of formula leaves. @returns Owned root. */
  private branch(count:number):Id {
    if(count===1) return this.leaf();
    const leftId=this.branch(Math.floor(count/2)),rightId=this.branch(Math.ceil(count/2));
    return this.add({tag:'and',id:this.id(),leftId,rightId});
  }
  /** Produce an immutable500-node module and a frozen1100-event edit sequence. @returns Reproducible benchmark input. */
  build():BenchFixture {
    const bodyId=this.branch(167),module:DraftModule={...emptyModule(),nodes:[...this.nodes],
      signatures:[{tag:'signature',id:A,name:'A',multiplicity:'set'},{tag:'signature',id:B,name:'B',multiplicity:'set'}],
      predicates:[{tag:'predicate',id:PREDICATE,name:'model',parameters:[],bodyId}],
      commands:[{tag:'run',id:'server:00000000-0000-4000-8000-000000001003',targetId:PREDICATE,uniformScope:3,bitwidth:4,maxseq:3}]};
    const index=new Map<Id,Expression>();for(const node of this.nodes) index.set(node.id,node);
    const source=`sig A {}\nsig B {}\npred model { ${printFixture(bodyId,index)} }\nrun model for 3 but 4 Int, 3 seq\n`;
    return {module,source,references:[...this.references],edits:editSequence(module,this.references)};
  }
}
/** Print only the benchmark's three owned constructors; no general parser correspondence claim. @param id Root. @param index Complete node table. @returns Deterministic Alloy text. */
function printFixture(id:Id,index:ReadonlyMap<Id,Expression>):string {
  const node=index.get(id);
  if(node?.tag==='signature_ref') return node.targetId===A?'A':'B';
  if(node?.tag==='some_test') return `(some ${printFixture(node.operandId,index)})`;
  if(node?.tag==='and') return `(${printFixture(node.leftId,index)} and ${printFixture(node.rightId,index)})`;
  throw new Error('Unexpected benchmark constructor.');
}
/** Freeze one deterministic signature toggle per edit,100 warmups followed by1000 measured events. @param module Initial candidate. @param references Ordered leaf identities. @returns Exact edit program. */
function editSequence(module:DraftModule,references:readonly Id[]):readonly EditEvent[] {
  const targets=new Map<Id,Id>(),events:EditEvent[]=[];
  for(const node of module.nodes) if(node.tag==='signature_ref') targets.set(node.id,node.targetId);
  for(let event=0;event<1100;event++) {
    const nodeId=references[(event*37)%references.length],targetId=targets.get(nodeId)===A?B:A;
    targets.set(nodeId,targetId);events.push({nodeId,targetId});
  }
  return events;
}
/** Apply an immutable leaf edit without changing ownership, registry order or counts. @param module Prior candidate. @param event Frozen toggle. @returns New candidate. */
function applyEdit(module:DraftModule,event:EditEvent):DraftModule {
  const nodes:Expression[]=[];
  for(const node of module.nodes) {
    if(node.tag==='hole') throw new Error('Benchmark cannot contain holes.');
    nodes.push(node.id===event.nodeId&&node.tag==='signature_ref'?{...node,targetId:event.targetId}:node);
  }
  return {...module,nodes};
}
/** Measure tree depth independently of node registry order. @param module Forest. @returns Maximum expression depth including root. */
function maximumDepth(module:DraftModule):number {
  const index=new Map();for(const node of module.nodes) index.set(node.id,node);
  /** Traverse one owned path. @param id Expression identity. @returns Path depth. */
  function depth(id:Id):number {
    const node=index.get(id);if(!node) throw new Error('Dangling benchmark node.');
    let maximum=0;for(const child of children(node)) maximum=Math.max(maximum,depth(child));
    return maximum+1;
  }
  let maximum=0;for(const predicate of module.predicates) maximum=Math.max(maximum,depth(predicate.bodyId));
  return maximum;
}
/** Execute immutable edit plus independent checker and all partial-slot descriptions. @param module Prior candidate. @param event Frozen edit. @returns New checked candidate. */
function previewStep(module:DraftModule,event:EditEvent):DraftModule {
  const next=applyEdit(module,event),checked=checkModule(next),constraints=slotConstraints(next,checked);
  if(!checked.complete||constraints.size!==500) throw new Error('Invalid benchmark edit or missing slot constraint.');
  return next;
}
/** Warm up100 edits, then time exactly1000 headless checker preview events including allocation and constraint derivation. @param fixture Frozen input. @returns Millisecond sample vector. */
function measure(fixture:BenchFixture):readonly number[] {
  let module=fixture.module;const samples:number[]=[];
  for(let event=0;event<100;event++) module=previewStep(module,fixture.edits[event]);
  for(let event=100;event<1100;event++) {
    const start=performance.now();module=previewStep(module,fixture.edits[event]);samples.push(performance.now()-start);
  }
  return samples;
}
/** Hash exact bytes or UTF8 text. @param bytes Serialized input. @returns Lowercase SHA256. */
function sha256(bytes:string|Uint8Array):string {return createHash('sha256').update(bytes).digest('hex');}
/** Read optional Linux container metadata without requiring a specific cgroup layout. @param path System metadata path. @returns Literal bound or unavailable marker. */
function optionalSystemFile(path:string):string {try {return readFileSync(path,'utf8').trim();} catch {return 'unavailable';}}
/** Record the actual shared reference host and runtime, explicitly excluding unavailable browser data. @returns Reproduction metadata. */
function referenceHost():Record<string,unknown> {
  const processors=cpus();
  return {hostname:hostname(),os:platform(),kernel:release(),architecture:arch(),cpu_model:processors[0]?.model??'unknown',
    logical_cpus:processors.length,reported_memory_bytes:totalmem(),node:NODE.version,v8:NODE.versions.v8,
    vitest:'4.1.12',typescript:'5.7.3',cgroup_cpu_max:optionalSystemFile('/sys/fs/cgroup/cpu.max'),
    cgroup_memory_max:optionalSystemFile('/sys/fs/cgroup/memory.max'),
    environment:'Shared development container; no exclusive CPU reservation or browser runtime.',browser:'UNAVAILABLE_NOT_MEASURED'};
}
/** Extract nearest-rank percentiles from1000 actual event durations. @param samples Millisecond observations. @returns Descriptive statistics without browser target assertions. */
function statistics(samples:readonly number[]):Record<string,number> {
  const ordered=[...samples].sort(numericOrder);let sum=0;for(const sample of ordered) sum+=sample;
  return {sample_count:ordered.length,p50_ms:ordered[Math.ceil(ordered.length*.5)-1],p95_ms:ordered[Math.ceil(ordered.length*.95)-1],
    p99_ms:ordered[Math.ceil(ordered.length*.99)-1],minimum_ms:ordered[0],maximum_ms:ordered.at(-1)!,mean_ms:sum/ordered.length};
}
/** Sort observations numerically. @param a First sample. @param b Second sample. @returns Ascending comparison. */
function numericOrder(a:number,b:number):number {return a-b;}
/** Hash every direct checker/fixture input and the frozen operator inventory used here. @returns Relative-path digest map. */
function sourceHashes():Record<string,string> {
  const result:Record<string,string>={};
  for(const path of ['frontend/src/document/performance.test.ts','frontend/src/document/model.ts','frontend/src/document/checker.ts',
    'frontend/src/document/operations.ts','frontend/src/document/fieldOrder.ts','frontend/src/document/types.ts',
    'frontend/src/document/fixtures.ts','frontend/src/document/model.test.ts','frontend/src/document/performance-node.d.ts',
    'frontend/src/model.ts','frontend/package.json','frontend/package-lock.json','spec/document-wire-draft.json']) {
    result[path]=sha256(readFileSync(resolve(ROOT,path)));
  }
  return result;
}
/** Independently inventory all23 TypeScript positive/negative constructor fixtures against frozen wire tags. @returns Honest finite coverage matrix and remaining refinement gaps. */
function typedFixtureInventory():Record<string,unknown> {
  const wire=JSON.parse(readFileSync(resolve(ROOT,'spec/document-wire-draft.json'),'utf8')),expected=Object.keys(wire.expressions).sort();
  const rows=[],gaps:string[]=[];
  for(const tag of TAGS) {
    const positive=checkModule(new Fixture().build(tag)),negative=checkModule(new Fixture().build(tag,true));
    rows.push({tag,positive_fixture_accepted:positive.complete,negative_fixture_rejected:!negative.complete,negative_diagnostic_count:negative.diagnostics.length});
    if(!positive.complete||negative.complete) gaps.push(`${tag}: fixture expectation failed`);
  }
  if(JSON.stringify([...TAGS].sort())!==JSON.stringify(expected)) gaps.push('TypeScript tag inventory differs from frozen wire expression tags.');
  return {expected_tag_count:expected.length,registered_tag_count:TAGS.length,scope:'Finite TypeScript checker fixtures only',rows,gaps,
    not_established:['Lean oracle correspondence or universal TypeScript refinement','Java differential agreement','Real browser keyboard/render/accessibility behavior','All constructor paths in the500-node benchmark (which uses signature_ref/some_test/and only)']};
}
/** Save exact deterministic inputs and observed timings with explicit scientific limits. @param fixture Input. @param samples Actual observations. @returns Report object. */
function record(fixture:BenchFixture,samples:readonly number[]):Record<string,unknown> {
  const fixtureBytes=JSON.stringify(fixture,null,2)+'\n',fixturePath='gates/document/headless-preview-fixture.json';
  writeFileSync(resolve(ROOT,fixturePath),fixtureBytes);
  const report={status:'HEADLESS_CHECKER_MEASURED_BROWSER_TARGET_UNVERIFIED',measured_at_utc:new Date().toISOString(),
    reproduction:'cd frontend && npm test -- src/document/performance.test.ts',host:referenceHost(),source_hashes:sourceHashes(),
    fixture:{path:fixturePath,sha256:sha256(fixtureBytes),source_sha256:sha256(fixture.source),source_utf8_bytes:new TextEncoder().encode(fixture.source).length,
      expression_nodes:fixture.module.nodes.length,maximum_depth:maximumDepth(fixture.module),formula_leaves:167,balanced_by:'Each conjunction splits remaining leaf count floor/ceil.',
      edit_sequence_sha256:sha256(JSON.stringify(fixture.edits)),warmup_events:100,measured_events:1000},
    measurement:{unit:'milliseconds',clock:'node:perf_hooks performance.now()',interval:'Immutable leaf toggle through checkModule plus slotConstraints, including local allocation and validity checks.',
      percentile_method:'Nearest rank: sorted[ceil(p*n)-1]',samples_ms:samples,
      excluded:['Browser reducer dispatch/commit/frame/render','DOM/React rendering','HTTP/server/Alloy parser/worker startup','Solver latency','Fixture construction/output serialization'],...statistics(samples)},
    typed_fixture_inventory:typedFixtureInventory(),browser_preview_target:{p95_ms:50,status:'UNVERIFIED_BROWSER_UNAVAILABLE'},
    limitations:['Headless timing cannot close inherited browser-preview or authoritative-diagnostic latency gates.','Generated fixture source is not Alloy-parser-tested by this benchmark.','Shared host scheduling and garbage collection are included; no confidence interval or exclusive-host claim.']};
  writeFileSync(resolve(ROOT,'gates/document/headless-preview-performance.json'),JSON.stringify(report,null,2)+'\n');
  return report;
}
/** Produce reproducible500-node headless evidence without asserting an unmeasured browser target. @returns Nothing. */
function benchmark():void {
  const fixture=new BalancedFixture().build(),initial=sha256(JSON.stringify(fixture));
  expect(fixture.module.nodes).toHaveLength(500);expect(fixture.edits).toHaveLength(1100);
  expect(maximumDepth(fixture.module)).toBeLessThanOrEqual(32);expect(new TextEncoder().encode(fixture.source).length).toBeLessThanOrEqual(32768);
  expect(checkModule(fixture.module).complete).toBe(true);
  const samples=measure(fixture),report=record(fixture,samples);
  expect(samples).toHaveLength(1000);expect(sha256(JSON.stringify(fixture))).toBe(initial);
  expect((report.typed_fixture_inventory as {gaps:unknown[]}).gaps).toEqual([]);
  for(const sample of samples) expect(Number.isFinite(sample)&&sample>=0).toBe(true);
}
test('records exactly500-node100-warmup1000-edit headless checker benchmark',benchmark,30000);
