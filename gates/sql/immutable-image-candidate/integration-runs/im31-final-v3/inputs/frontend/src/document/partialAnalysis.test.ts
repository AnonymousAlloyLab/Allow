import {expect,test} from 'vitest';
import type {DraftModule,DraftNode,Expression,Id,SlotObligation} from './types';
import {checkModule,emptyModule} from './model';
import {construct,replaceSubtree,newContradiction} from './operations';
import {TAGS} from './fixtures';
import {DEFAULT_PARTIAL_LIMITS} from './partialAnalysis';
const RELATION=['signature_ref','field_ref','variable_ref','transpose','union','intersection','difference','join','product'];
/** Assemble a small independent declared environment with a selected owned formula root. @param nodes Owned forest. @param bodyId Fact root. @returns Draft. */
function moduleWith(nodes:readonly DraftNode[],bodyId:Id):DraftModule {
  return {...emptyModule(),signatures:[{tag:'signature',id:'A',name:'A',multiplicity:'set'},{tag:'signature',id:'B',name:'B',multiplicity:'set'}],
    fields:[{tag:'field',id:'AB',name:'fieldAB',ownerSignatureId:'A',rangeColumns:['B'],multiplicity:'set'},
      {tag:'field',id:'wide',name:'fieldWide',ownerSignatureId:'A',rangeColumns:Array(7).fill('A'),multiplicity:'set'}],
    facts:[{tag:'fact',id:'fact',name:'factMain',bodyId}],nodes};
}
/** Make constructor shape holes, retaining valid declarations and lexical variable scope. @param tag Closed tag. @param opposite Whether opposite-sort destination. @returns Draft and constructor ID. */
function operatorModule(tag:Expression['tag'],opposite:boolean):{module:DraftModule;id:Id} {
  const target=tag==='field_ref'?'AB':tag==='variable_ref'?'parameter':tag==='predicate_call'?'callee':'A';
  let module=moduleWith([{tag:'hole',id:'destination',expected:null}],'destination');
  module={...module,facts:[],predicates:[{tag:'predicate',id:'main',name:'predMain',parameters:[{tag:'parameter',id:'parameter',name:'paramMain',columns:['A']}],bodyId:'destination'},
    {tag:'predicate',id:'callee',name:'predCallee',parameters:[],bodyId:'calleeBody'}],nodes:[...module.nodes,{tag:'hole',id:'calleeBody',expected:{kind:'formula'}}]};
  const nodes=construct(tag,target,module),relation=RELATION.includes(tag),wrap=opposite?!relation:relation;
  const replacement:DraftNode[]=wrap?[{tag:'some_test',id:'outer',operandId:nodes[0].id},...nodes]:[...nodes];
  return {module:replaceSubtree(module,'destination',replacement),id:nodes[0].id};
}
/** Every closed tag retains known sort and rejects the opposite destination with holes. @param tag Profile member. @returns Nothing. */
function verifiesProfile(tag:Expression['tag']):void {
  const good=operatorModule(tag,false),bad=operatorModule(tag,true),checked=checkModule(good.module);
  expect(checked.facts.get(good.id)?.sort).toBe(RELATION.includes(tag)?'relation':'formula');
  expect(checked.resourceFailure).toBeNull();expect(checked.violations.size).toBe(0);
  expect(checkModule(bad.module).violations.size).toBeGreaterThan(0);
  if(hasHole(good.module)) expect(checked.complete).toBe(false);
}
for(const tag of TAGS) test(`partial23 profile ${tag} preserves known result sort with holes`,verifiesProfile.bind(null,tag));
/** The observed browser counterexample is rejected by shared analysis rather than save completion. @returns Nothing. */
function rejectsNotHole():void {
  const before=moduleWith([{tag:'some_test',id:'some',operandId:'person'},{tag:'signature_ref',id:'person',targetId:'A'}],'some');
  const after=replaceSubtree(before,'person',[{tag:'not',id:'not',operandId:'missing'},{tag:'hole',id:'missing',expected:{kind:'formula'}}]);
  expect(newContradiction(before,after)).toContain('relation');expect(checkModule(after).types.has('not')).toBe(false);
  expect(checkModule(after).facts.get('not')?.sort).toBe('formula');
}
/** Reproduce same-parent diagnostic collisions and preserve true no-op prior errors. @returns Nothing. */
function distinguishesOperandViolations():void {
  const before=moduleWith([{tag:'and',id:'and',leftId:'left',rightId:'right'},{tag:'signature_ref',id:'left',targetId:'A'},{tag:'hole',id:'right',expected:{kind:'formula'}}],'and');
  const after=replaceSubtree(before,'right',[{tag:'signature_ref',id:'newRight',targetId:'A'}]);
  expect(newContradiction(before,before)).toBeNull();expect(newContradiction(before,after)).not.toBeNull();
  const keys:string[]=[];for(const row of checkModule(after).violations.values()) if(row.identity.ownerId==='and'&&row.identity.rule==='expect') keys.push(row.identity.role);
  expect(keys).toContain('left');expect(keys).toContain('right');
}
/** Enforcement remains complete when presentation diagnostics have reached their cap. @returns Nothing. */
function enforcesBeyondDisplayCap():void {
  let module=moduleWith([{tag:'some_test',id:'lateSome',operandId:'late'},{tag:'signature_ref',id:'late',targetId:'A'}],'lateSome');
  const facts=[...module.facts],nodes=[...module.nodes];
  for(let i=0;i<65;i++) {facts.unshift({tag:'fact',id:`fact${i}`,name:`factName${i}`,bodyId:`bad${i}`});nodes.unshift({tag:'signature_ref',id:`bad${i}`,targetId:'A'});}
  module={...module,facts,nodes};
  const after=replaceSubtree(module,'late',[{tag:'not',id:'lateNot',operandId:'lateHole'},{tag:'hole',id:'lateHole',expected:null}]);
  expect(checkModule(module).diagnostics).toHaveLength(64);expect(newContradiction(module,module)).toBeNull();expect(newContradiction(module,after)).not.toBeNull();
  expect(checkModule(after).violations.size).toBeGreaterThan(64);
  const permuted={...after,nodes:[...after.nodes].reverse(),facts:[...after.facts].reverse()};
  expect([...checkModule(permuted).violations.keys()].sort()).toEqual([...checkModule(after).violations.keys()].sort());
}
/** Independent retained slot constraints survive even when the removed hole no longer exists. @returns Nothing. */
function retainsExactObligation():void {
  const obligations:SlotObligation[]=[{slot:{ownerId:'some',role:'operand'},expected:{kind:'relation',columns:['A']}}];
  const module=moduleWith([{tag:'some_test',id:'some',operandId:'union'},{tag:'union',id:'union',leftId:'l',rightId:'r'},{tag:'hole',id:'l',expected:null},{tag:'hole',id:'r',expected:null}],'some');
  const checked=checkModule(module,obligations);
  expect(checked.violations.size).toBe(0);expect(checked.types.has('union')).toBe(false);
  expect(checked.facts.get('l')?.shapes).toEqual([{columns:['A']}]);
  const after=replaceSubtree(module,'l',[{tag:'signature_ref',id:'b',targetId:'B'}]);
  expect(checkModule(after,obligations).violations.size).toBeGreaterThan(0);
}
/** Product minimum widths and transpose fixed widths reject without missing nominal schemas. @returns Nothing. */
function enforcesPartialWidths():void {
  const product=moduleWith([{tag:'some_test',id:'some',operandId:'product'},{tag:'product',id:'product',leftId:'wideRef',rightId:'hole'},
    {tag:'field_ref',id:'wideRef',targetId:'wide'},{tag:'hole',id:'hole',expected:null}],'some');
  expect(checkModule(product).violations.size).toBeGreaterThan(0);
  const transpose=moduleWith([{tag:'some_test',id:'some',operandId:'transpose'},{tag:'transpose',id:'transpose',operandId:'hole'},{tag:'hole',id:'hole',expected:null}],'some');
  const constraint:SlotObligation[]=[{slot:{ownerId:'some',role:'operand'},expected:{kind:'relation',columns:['A']}}];
  expect(checkModule(transpose,constraint).violations.size).toBeGreaterThan(0);
  expect(checkModule(transpose).facts.get('hole')?.shapes).toEqual([{columns:[null,null]}]);
}
/** Canonical finite propagation fails closed on exhausted counters and malformed ownership. @returns Nothing. */
function rejectsIncompleteAnalysis():void {
  const {module}=operatorModule('union',false),limits={...DEFAULT_PARTIAL_LIMITS,worklistPops:0};
  expect(checkModule(module,[],limits).resourceFailure?.code).toBe('ANALYSIS_RESOURCE_LIMIT');
  expect(checkModule(module,[],{...DEFAULT_PARTIAL_LIMITS,columnVariables:0}).resourceFailure?.code).toBe('ANALYSIS_RESOURCE_LIMIT');
  const cyclic=moduleWith([{tag:'not',id:'cycle',operandId:'cycle'}],'cycle');
  expect(checkModule(cyclic).resourceFailure?.code).toBe('ANALYSIS_INVALID_GRAPH');
}
/** Scope errors remain complete enforcement even when other expression children are holes. @returns Nothing. */
function retainsScopeFailures():void {
  const module=moduleWith([{tag:'and',id:'and',leftId:'some',rightId:'hole'},{tag:'some_test',id:'some',operandId:'external'},
    {tag:'variable_ref',id:'external',targetId:'outOfScope'},{tag:'hole',id:'hole',expected:null}],'and');
  let found=false;for(const row of checkModule(module).violations.values()) if(row.message.includes('out-of-scope')) found=true;expect(found).toBe(true);
}
test('observed some(not HOLE) rejected',rejectsNotHole);
test('same-parent distinct operands have independent enforcement identities',distinguishesOperandViolations);
test('more than64 prior errors cannot hide a late new violation',enforcesBeyondDisplayCap);
test('explicit destination obligation constrains later incomplete replacement',retainsExactObligation);
test('partial widths preserve product and transpose constraints',enforcesPartialWidths);
test('resource exhaustion and malformed graph fail closed',rejectsIncompleteAnalysis);
test('unrelated holes never hide out-of-scope references',retainsScopeFailures);
/** Prior-invalid nodes cannot hide changed missing declarations, argument counts or command facts. @returns Nothing. */
function distinguishesLegacyFacts():void {
  const missing=moduleWith([{tag:'some_test',id:'some',operandId:'missing'},{tag:'signature_ref',id:'missing',targetId:'unknownA'}],'some');
  const changed=replaceReference(missing,'missing','unknownB');
  expect(newContradiction(missing,missing)).toBeNull();expect(newContradiction(missing,changed)).not.toBeNull();
  const base=moduleWith([{tag:'hole',id:'hole',expected:{kind:'formula'}}],'hole');
  const command={tag:'check' as const,id:'cmd',targetId:'missingAssertion',uniformScope:0,bitwidth:4 as const,maxseq:3 as const};
  const before={...base,commands:[command]},after={...base,commands:[{...command,uniformScope:9}]};
  expect(newContradiction(before,before)).toBeNull();expect(newContradiction(before,after)).not.toBeNull();
  const invalidCount=operatorModule('predicate_call',false).module;
  let call:Extract<Expression,{tag:'predicate_call'}>|undefined;for(const node of invalidCount.nodes) if(node.tag==='predicate_call') call=node;expect(call).toBeDefined();
  const first=withCallArgs(invalidCount,call!,['arg1'],'arg1');
  const second=withCallArgs(first,call!,['arg1','arg2'],'arg2');
  expect(newContradiction(first,second)).not.toBeNull();
}
/** The full merged private set, including legacy rules, obeys the violation budget. @returns Nothing. */
function boundsMergedViolations():void {
  const module=moduleWith([{tag:'some_test',id:'some',operandId:'missing'},{tag:'signature_ref',id:'missing',targetId:'unknown'}],'some');
  expect(checkModule(module,[],{...DEFAULT_PARTIAL_LIMITS,violations:0}).resourceFailure).toEqual({code:'ANALYSIS_RESOURCE_LIMIT',counter:'violations',limit:0});
}
test('same-node changes to missing identities and command facts are new violations',distinguishesLegacyFacts);
test('legacy and partial violations share one explicit complete-set budget',boundsMergedViolations);
/** Check whether a fixture still contains a draft-only unresolved expression. @param module Fixture. @returns Whether a hole exists. */
function hasHole(module:DraftModule):boolean {for(const node of module.nodes) if(node.tag==='hole') return true;return false;}
/** Change only a reference target while preserving its occurrence identity. @param module Prior fixture. @param id Reference identity. @param targetId Missing target. @returns Changed fixture. */
function replaceReference(module:DraftModule,id:Id,targetId:Id):DraftModule {
  const nodes:DraftNode[]=[];for(const node of module.nodes) nodes.push(node.id===id&&'targetId' in node?{...node,targetId}:node);return {...module,nodes};
}
/** Change one call arity and append its new owned argument hole. @param module Prior fixture. @param call Existing call. @param args Argument identities. @param addedId New hole identity. @returns Changed fixture. */
function withCallArgs(module:DraftModule,call:Extract<Expression,{tag:'predicate_call'}>,args:readonly Id[],addedId:Id):DraftModule {
  const nodes:DraftNode[]=[];for(const node of module.nodes) nodes.push(node.id===call.id?{...call,arguments:args}:node);nodes.push({tag:'hole',id:addedId,expected:null});return {...module,nodes};
}
/** Explicit partial constraints cannot introduce undeclared signature identities. @returns Nothing. */
function rejectsUnknownExpectedSchema():void {
  const module=moduleWith([{tag:'some_test',id:'some',operandId:'hole'},{tag:'hole',id:'hole',expected:{kind:'relation',columns:['missingSignature']}}],'some');
  expect([...checkModule(module).violations.values()].map(violationMessage)).toContain('Invalid nominal destination schema.');
}
/** Extract an enforcement message for an exact assertion. @param row Enforcement row. @returns Display explanation. */
function violationMessage(row:{message:string}):string {return row.message;}
test('explicit holes preserve declared nominal schema boundaries',rejectsUnknownExpectedSchema);
/** An unrelated legacy issue must not suppress a new partial error within the remaining display budget. @returns Nothing. */
function displaysPartialBesideLegacy():void {
  const module=moduleWith([{tag:'some_test',id:'some',operandId:'not'},{tag:'not',id:'not',operandId:'hole'},{tag:'hole',id:'hole',expected:null}],'some');
  const changed={...module,commands:[{tag:'check' as const,id:'cmd',targetId:'missing',uniformScope:1,bitwidth:4 as const,maxseq:3 as const}]};
  const messages=checkModule(changed).diagnostics.map(violationMessage);
  expect(messages).toContain('run needs nullary predicate; check needs assertion.');
  expect(messages).toContain('Expected relation; actual formula.');
  expect(messages.length).toBeLessThanOrEqual(64);
}
test('unrelated legacy error does not hide partial diagnostic within display capacity',displaysPartialBesideLegacy);
