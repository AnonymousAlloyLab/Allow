import {expect,test,vi} from 'vitest';
import {readFileSync,writeFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import type {DraftModule,Diagnostic,Expression} from './types';
import {Fixture,TAGS} from './fixtures';
import {checkModule} from './model';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const PATH=resolve(ROOT,'backend/src/test/resources/document-type-cases.json');
interface TypeCase {
  readonly caseId:string;readonly tag:Expression['tag'];readonly variant:'positive'|'negative';
  readonly expectedAccepted:boolean;readonly expectedDiagnosticCategory:null;
  readonly module:DraftModule;readonly typescriptDiagnostics:readonly Diagnostic[];
}
interface SharedCases {readonly protocol:1;readonly scope:string;readonly tagInventory:readonly Expression['tag'][];readonly cases:readonly TypeCase[]}
/** Run the existing fixture builder under reproducible valid UUID generation, restoring crypto afterwards. @param tag Closed constructor. @param bad Whether this is the existing denial fixture. @param seed Unique deterministic case range. @returns Exact finite fixture. */
function deterministicModule(tag:Expression['tag'],bad:boolean,seed:number):DraftModule {
  let sequence=seed;
  /** Generate a deterministic fixture-only UUIDv4 with no runtime authority. @returns Stable syntactically valid UUID. */
  function nextUUID():ReturnType<Crypto['randomUUID']> {
    sequence++;
    return `00000000-0000-4000-8000-${sequence.toString(16).padStart(12,'0')}`;
  }
  const random=vi.spyOn(globalThis.crypto,'randomUUID').mockImplementation(nextUUID);
  try {return new Fixture().build(tag,bad);} finally {random.mockRestore();}
}
/** Build one stored case directly from the existing constructor fixture. @param tag Expression tag. @param bad Denial variant. @param index Ordered tag index. @returns Shared case with no invented diagnostic category. */
function buildCase(tag:Expression['tag'],bad:boolean,index:number):TypeCase {
  const module=deterministicModule(tag,bad,(index*2+(bad?2:1))*1024),checked=checkModule(module);
  return {caseId:`${tag}-${bad?'negative':'positive'}`,tag,variant:bad?'negative':'positive',expectedAccepted:!bad,
    expectedDiagnosticCategory:null,module,typescriptDiagnostics:checked.diagnostics};
}
/** Build the full46-case inventory without changing production checkers or fixture helpers. @returns Deterministic shared artifact. */
function buildCases():SharedCases {
  const cases:TypeCase[]=[];
  for(let index=0;index<TAGS.length;index++) {
    cases.push(buildCase(TAGS[index],false,index));
    cases.push(buildCase(TAGS[index],true,index));
  }
  return {protocol:1,scope:'Finite TypeScript/Java checker agreement inputs only; no Lean refinement, Alloy parser or browser correspondence claim.',tagInventory:[...TAGS],cases};
}
/** Explicitly regenerate only when requested, then verify exact stored inputs and every finite outcome. @returns Nothing. */
function verifiesSharedCases():void {
  const expected=buildCases();
  const environment=(globalThis as unknown as {process:{env:Readonly<Record<string,string|undefined>>}}).process.env;
  if(environment.ALLOW_GENERATE_DOCUMENT_TYPE_CASES==='1') writeFileSync(PATH,JSON.stringify(expected,null,2)+'\n');
  const stored=JSON.parse(readFileSync(PATH,'utf8')) as SharedCases;
  const wire=JSON.parse(readFileSync(resolve(ROOT,'spec/document-wire-draft.json'),'utf8'));
  expect(stored).toEqual(expected);
  expect(stored.cases).toHaveLength(46);expect(stored.tagInventory).toHaveLength(23);
  expect([...stored.tagInventory].sort()).toEqual(Object.keys(wire.expressions).sort());
  const seen=new Set<string>();
  for(const item of stored.cases) {
    expect(seen.has(item.caseId)).toBe(false);seen.add(item.caseId);
    const checked=checkModule(item.module);
    expect(checked.complete,item.caseId).toBe(item.expectedAccepted);
    expect(checked.diagnostics,item.caseId).toEqual(item.typescriptDiagnostics);
    expect(item.expectedDiagnosticCategory).toBe(null);
  }
}
test('shared deterministic46-case inventory exactly matches existing builders and all23 wire tags',verifiesSharedCases);
