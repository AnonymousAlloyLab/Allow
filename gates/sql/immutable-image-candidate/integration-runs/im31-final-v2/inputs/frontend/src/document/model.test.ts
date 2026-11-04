import {expect,test} from 'vitest';
import type {Expression,DraftModule,DraftNode} from './types';
import {Fixture,TAGS} from './fixtures';
import {checkModule,freshId,emptyModule,FORMULA} from './model';
import {construct,hole,replaceSubtree,cloneSubtree,paste,copyProvenance,slotConstraint} from './operations';
/** Accept each independently assembled constructor's exact nominal fixture. @param tag Constructor. @returns Nothing. */
function acceptsTag(tag:Expression['tag']):void {const result=checkModule(new Fixture().build(tag));expect(result.diagnostics).toEqual([]);expect(result.complete).toBe(true);}
/** Deny each constructor's invalid nominal/scope/arity fixture. @param tag Constructor. @returns Nothing. */
function deniesTag(tag:Expression['tag']):void {const result=checkModule(new Fixture().build(tag,true));expect(result.complete).toBe(false);expect(result.diagnostics.length).toBeGreaterThan(0);}
for(const tag of TAGS) {test(`independent whole-module ${tag} accepts`,acceptsTag.bind(null,tag));test(`independent whole-module ${tag} denies`,deniesTag.bind(null,tag));}
/** Reject child sharing, dangling ownership and predicate recursion. @returns Nothing. */
function rejectsMalformed():void {
  const module=new Fixture().build('and'),nodes=[...module.nodes],root=nodes[nodes.length-3];
  let binary:Extract<DraftNode,{leftId:string}>|undefined;
  for(const node of nodes) if(node.tag==='and') binary=node;
  expect(binary).toBeDefined();
  const shared={...binary!,rightId:binary!.leftId},candidate=replaceNode(module,shared);
  expect(checkModule(candidate).complete).toBe(false);
  const dangling=replaceNode(module,{...binary!,rightId:'missing'});
  expect(checkModule(dangling).complete).toBe(false);
  const pred=module.predicates[0],call:Expression={tag:'predicate_call',id:freshId(),predicateId:pred.id,arguments:[]};
  const recursive=replaceSubtree(module,pred.bodyId,[call]);
  expect(checkModule(recursive).diagnostics.some(hasRecursion)).toBe(true);
}
/** Match a dependency-cycle diagnostic. @param item Diagnostic. @returns Cycle found. */
function hasRecursion(item:{message:string}):boolean {return item.message.includes('Recursive');}
/** Replace one fixture node by identity. @param module Prior. @param replacement New node. @returns Immutable candidate. */
function replaceNode(module:DraftModule,replacement:DraftNode):DraftModule {const nodes:DraftNode[]=[];for(const node of module.nodes) nodes.push(node.id===replacement.id?replacement:node);return {...module,nodes};}
/** Clone quantified subtrees capture-avoidably with unique names and binder identities. @returns Nothing. */
function clonesBinders():void {
  const module=new Fixture().build('all_quant'),source=module.predicates[0].bodyId,clone=cloneSubtree(module,source),original=new Map();
  for(const node of module.nodes) original.set(node.id,node);
  const copied=replaceSubtree(module,source,clone.nodes);
  expect(checkModule(copied).complete).toBe(true);
  for(const node of clone.nodes) {
    expect(original.has(node.id)).toBe(false);
    if('binder' in node) expect(node.binder.id).not.toBe((original.get(source) as Extract<Expression,{binder:unknown}>).binder.id);
  }
}
/** Retain authorized accepted-base comment provenance through repeated draft copies. @returns Nothing. */
function copiesCopies():void {
  const first=new Map([['server:original','draft:first']]),copies=copyProvenance([],first);
  const second=copyProvenance(copies,new Map([['draft:first','draft:second'],['draft:new','draft:third']]));
  expect(second).toEqual([{sourceNodeId:'server:original',targetNodeId:'draft:first'},{sourceNodeId:'server:original',targetNodeId:'draft:second'}]);
}
/** Keep holes unresolved and show nominal constraints rather than invented types. @returns Nothing. */
function unresolvedSlots():void {
  const body=hole(FORMULA),module={...emptyModule(),facts:[{tag:'fact' as const,id:freshId(),name:'factName',bodyId:body.id}],nodes:[body]};
  expect(checkModule(module).complete).toBe(false);
  expect(slotConstraint(module,body.id)).toBe('formula');
  const nodes=construct('join','',module),joined=replaceSubtree(module,body.id,nodes);
  expect(slotConstraint(joined,(nodes[0] as Extract<Expression,{leftId:string}>).leftId)).toContain('left-last = right-first');
}
test('rejects malformed forests and recursive calls',rejectsMalformed);
test('freshens copied quantifier ownership and bound references',clonesBinders);
test('copy-of-copy keeps base comment provenance without draft source IDs',copiesCopies);
test('holes retain explicit unresolved nominal constraints',unresolvedSlots);
/** Deny escaping external variables while preserving the entire previous draft. @returns Nothing. */
function rejectsCapture():void {
  const module=new Fixture().build('variable_ref'),source=module.predicates[0].bodyId,target=module.predicates[1].bodyId;
  const clipboard={documentId:'document',baseRevision:1,draftId:'draft',contentGeneration:1,nodeId:source,cut:false};
  const result=paste(module,clipboard,target,[]);
  expect(result.error).toContain('out-of-scope');expect(result.module).toBe(module);
  expect(paste(module,clipboard,source,[]).error).toContain('descendant');
}
/** Move preserves subtree and binder identities, whereas copy freshens both. @returns Nothing. */
function movesQuantifier():void {
  const module=new Fixture().build('all_quant'),source=module.predicates[0].bodyId,target=module.predicates[1].bodyId;
  const clipboard={documentId:'document',baseRevision:1,draftId:'draft',contentGeneration:1,nodeId:source,cut:true};
  const moved=paste(module,clipboard,target,[]);
  expect(moved.error).toBe(null);expect(moved.selected).toBe(source);
  expect(checkModule(moved.module).complete).toBe(false);
  expect(checkModule(moved.module).diagnostics).toEqual([]);
  const copied=paste(module,{...clipboard,cut:false},target,[]);
  expect(copied.error).toBe(null);expect(copied.selected).not.toBe(source);
  expect(checkModule(copied.module).complete).toBe(true);
}
test('copy denies external variable escape and descendant destination atomically',rejectsCapture);
test('move preserves IDs and leaves source draft hole; copy freshens IDs',movesQuantifier);
