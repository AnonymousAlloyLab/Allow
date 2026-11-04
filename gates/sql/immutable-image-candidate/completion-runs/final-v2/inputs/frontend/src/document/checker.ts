import type {DraftModule,DraftNode,Id,Type,Parameter,Check,Diagnostic,Expression,Schema,SlotObligation,PartialLimits,EnforcementViolation} from './types';
import {children,FORMULA,issue,nodeIndex,sameType,schemaValid,findVariable} from './model';
import {validName} from '../model';
import {fieldsGrouped} from './fieldOrder';
import {analyzePartial,DEFAULT_PARTIAL_LIMITS} from './partialAnalysis';
import {violation} from './partialShapes';
import {appendPartialDiagnostics} from './partialDisplay';
/** Independent finite draft checker; parser acceptance remains server authority. */
export class Checker {
  private readonly module:DraftModule;
  private readonly index:ReadonlyMap<Id,DraftNode>;
  private readonly diagnostics:Diagnostic[]=[];
  private readonly types=new Map<Id,Type>();
  private readonly scopes=new Map<Id,readonly Parameter[]>();
  private readonly owned=new Set<Id>();
  private readonly ids=new Set<Id>();
  private readonly names=new Set<string>();
  private complete=true;
  private readonly violations=new Map<string,EnforcementViolation>();
  /** Bind immutable checker inputs. @param module Candidate forest. @param obligations Retained local slot constraints. @param limits Optional lower analysis budgets. */
  constructor(module:DraftModule,private readonly obligations:readonly SlotObligation[]=[],private readonly limits?:PartialLimits) { this.module=module;this.index=nodeIndex(module); }
  /** Validate declarations, ownership and all dependent roots. @returns Bounded result. */
  check():Check {
    this.declarations();
    if(!fieldsGrouped(this.module)) this.error('module','Fields must be grouped by signature owner order; submitted order is not normalized.','exact-01',[],this.fieldOrderFacts());
    for(const pred of this.module.predicates) this.expect(pred.bodyId,pred.parameters,FORMULA,0);
    for(const root of [...this.module.facts,...this.module.assertions]) this.expect(root.bodyId,[],FORMULA,0);
    for(const node of this.module.nodes) if(!this.owned.has(node.id)) this.error(node.id,'Unreachable expression.','exact-02');
    this.dependencies();
    this.commands();
    return this.finish();
  }
  /** Record full enforcement and bounded display independently. @param id Identity. @param message Explanation. @param rule Stable rule identifier. @param expected Required facts. @param actual Offending facts. @returns Nothing. */
  private error(id:Id,message:string,rule:string,expected:readonly string[]=[],actual:readonly string[]=[]):void {
    issue(this.diagnostics,id,message);
    const value=violation({ownerId:id,role:'node',rule,expected,actual,relatedIds:[]},id,message);
    this.violations.set(value.key,value);
  }
  /** Combine complete enforcement with the existing bounded diagnostic projection. @returns Shared check. */
  private finish():Check {
    const base={diagnostics:this.diagnostics,types:this.types,scopes:this.scopes,complete:this.complete&&this.diagnostics.length===0};
    const partial=analyzePartial(this.module,base,this.obligations,this.limits);
    appendPartialDiagnostics(this.diagnostics,this.violations,partial.violations);
    for(const [key,value] of partial.violations) this.violations.set(key,value);
    const limit=Math.min(DEFAULT_PARTIAL_LIMITS.violations,this.limits?.violations??DEFAULT_PARTIAL_LIMITS.violations);
    const resourceFailure=partial.resourceFailure??(this.violations.size>limit?{code:'ANALYSIS_RESOURCE_LIMIT' as const,counter:'violations' as const,limit}:null);
    if(resourceFailure) issue(this.diagnostics,'module',resourceFailure.code);
    return {...base,...partial,violations:this.violations,resourceFailure,complete:base.complete&&this.violations.size===0&&!resourceFailure};
  }
  /** Enforce globally unique identifiers and names. @param id Identity. @param name Optional display name. @returns Nothing. */
  private identity(id:Id,name?:string):void {
    if(this.ids.has(id)) this.error(id,'Duplicate identity.','exact-03');
    this.ids.add(id);
    if(name===undefined) return;
    if(!validName(name)||name.length>64||name.startsWith('allow_')) this.error(id,'Invalid or reserved name.','exact-04',[],[name]);
    if(this.names.has(name)) this.error(id,'Names must be globally unique.','exact-05',[],[name]);
    this.names.add(name);
  }
  /** Validate declaration schema and bounded parameters. @returns Nothing. */
  private declarations():void {
    const m=this.module, declarations=[...m.signatures,...m.fields,...m.predicates,...m.facts,...m.assertions,...m.commands];
    if(declarations.length>128||m.nodes.length>512) this.error('module','Declaration/node budget exceeded.','exact-06',['128','512'],[String(declarations.length),String(m.nodes.length)]);
    for(const decl of declarations) this.identity(decl.id,'name' in decl?decl.name:undefined);
    for(const node of m.nodes) {
      this.identity(node.id);
      if('binder' in node) this.identity(node.binder.id,node.binder.name);
    }
    for(const field of m.fields) {
      if(!schemaValid(m,[field.ownerSignatureId,...field.rangeColumns])) this.error(field.id,'Field owner/range must be declared; full width 1..8.','exact-07',[],[field.ownerSignatureId,...field.rangeColumns]);
      if(field.rangeColumns.length>1&&field.multiplicity!=='set') this.error(field.id,'Tuple range permits set multiplicity only.','exact-08',[],[field.multiplicity,...field.rangeColumns]);
    }
    for(const pred of m.predicates) {
      if(pred.parameters.length>16) this.error(pred.id,'At most16 parameters.','exact-09',['16'],[String(pred.parameters.length)]);
      for(const param of pred.parameters) {
        this.identity(param.id,param.name);
        if(!schemaValid(m,param.columns)) this.error(param.id,'Parameter requires declared nonempty nominal schema.','exact-10',[],param.columns);
      }
    }
  }
  /** Check a formula or required schema. @param id Root. @param env Scope. @param expected Required type. @param depth Current depth. @returns Inferred type. */
  private expect(id:Id,env:readonly Parameter[],expected:Type,depth:number):Type|null {
    const actual=this.visit(id,env,depth);
    if(actual&&!sameType(actual,expected)) this.error(id,`Expected ${this.describe(expected)}; actual ${this.describe(actual)}.`,'exact-11',[expected.kind,...(expected.kind==='relation'?expected.columns:[])],[actual.kind,...(actual.kind==='relation'?actual.columns:[])]);
    return actual;
  }
  /** Format exact schemas for diagnostics. @param type Type. @returns Stable text. */
  private describe(type:Type):string { return type.kind==='formula'?'formula':`relation [${type.columns.join(', ')}]`; }
  /** Visit an owned expression once under lexical scope. @param id Identity. @param env Scope. @param depth Depth. @returns Inferred type or unresolved. */
  private visit(id:Id,env:readonly Parameter[],depth:number):Type|null {
    if(depth>=32) {this.error(id,'Depth limit32 exceeded.','exact-12');return null;}
    if(this.owned.has(id)) {this.error(id,'Shared child or cycle.','exact-13');return null;}
    this.owned.add(id);this.scopes.set(id,env);
    const node=this.index.get(id);
    if(!node) {this.error(id,'Dangling child.','exact-14');return null;}
    if(node.tag==='hole') {this.complete=false;return null;}
    const type=this.infer(node,env,depth);
    if(type) this.types.set(id,type);
    return type;
  }
  /** Dispatch closed constructor rules. @param node Expression. @param env Scope. @param depth Depth. @returns Exact type. */
  private infer(node:Expression,env:readonly Parameter[],depth:number):Type|null {
    if('targetId' in node) return this.reference(node,env);
    if(node.tag==='predicate_call') return this.call(node,env,depth);
    if('binder' in node) {
      const binder:Parameter={tag:'parameter',id:node.binder.id,name:node.binder.name,columns:[node.binder.signatureId]};
      if(!schemaValid(this.module,binder.columns)) this.error(node.id,'Unknown quantifier signature.','exact-15',[],[node.binder.signatureId]);
      this.expect(node.bodyId,[...env,binder],FORMULA,depth+1);return FORMULA;
    }
    if('operandId' in node) return this.unary(node,env,depth);
    return this.binary(node,env,depth);
  }
  /** Resolve stable declarations and lexical variables. @param node Reference. @param env Scope. @returns Exact declared type. */
  private reference(node:Extract<Expression,{targetId:Id}>,env:readonly Parameter[]):Type|null {
    let columns:Schema|undefined;
    if(node.tag==='signature_ref') for(const sig of this.module.signatures) if(sig.id===node.targetId) columns=[sig.id];
    if(node.tag==='field_ref') for(const field of this.module.fields) if(field.id===node.targetId) columns=[field.ownerSignatureId,...field.rangeColumns];
    if(node.tag==='variable_ref') columns=findVariable(env,node.targetId)?.columns;
    if(!columns) {this.error(node.id,'Unknown declaration or out-of-scope binder.','exact-16',[],[node.targetId,...(node.tag==='variable_ref'?this.scopeFacts(env):[])]);return null;}
    return {kind:'relation',columns};
  }
  /** Validate ordered call arguments. @param node Call. @param env Scope. @param depth Depth. @returns Formula. */
  private call(node:Extract<Expression,{tag:'predicate_call'}>,env:readonly Parameter[],depth:number):Type {
    let parameters:readonly Parameter[]|undefined;
    for(const pred of this.module.predicates) if(pred.id===node.predicateId) parameters=pred.parameters;
    if(!parameters) this.error(node.id,'Unknown predicate.','exact-17',[],[node.predicateId]);
    if(parameters&&parameters.length!==node.arguments.length) this.error(node.id,'Predicate argument count mismatch.','exact-18',[node.predicateId,String(parameters.length)],[node.predicateId,String(node.arguments.length)]);
    for(let i=0;i<node.arguments.length;i++) {
      const param=parameters?.[i];
      if(param) this.expect(node.arguments[i],env,{kind:'relation',columns:param.columns},depth+1);
      else this.visit(node.arguments[i],env,depth+1);
    }
    return FORMULA;
  }
  /** Check unary operators. @param node Unary expression. @param env Scope. @param depth Depth. @returns Exact result. */
  private unary(node:Extract<Expression,{operandId:Id}>,env:readonly Parameter[],depth:number):Type|null {
    const input=this.visit(node.operandId,env,depth+1);
    if(!input) return null;
    if(node.tag==='not') {
      if(input.kind!=='formula') this.error(node.id,'not requires formula.','exact-19');
      return FORMULA;
    }
    if(input.kind!=='relation') {this.error(node.id,'Expected nonempty relation schema.','exact-20');return null;}
    if(node.tag==='transpose') {
      if(input.columns.length!==2) {this.error(node.id,'Transpose requires exactly2 columns.','exact-21',['2'],[String(input.columns.length)]);return null;}
      return {kind:'relation',columns:[input.columns[1],input.columns[0]]};
    }
    return FORMULA;
  }
  /** Check binary operators including exact join endpoints. @param node Binary expression. @param env Scope. @param depth Depth. @returns Inferred formula or exact relation schema. */
  private binary(node:Extract<Expression,{leftId:Id}>,env:readonly Parameter[],depth:number):Type|null {
    const left=this.visit(node.leftId,env,depth+1),right=this.visit(node.rightId,env,depth+1);
    const boolean=['and','or','implies','iff'].includes(node.tag);
    if(boolean) {
      if(left&&left.kind!=='formula'||right&&right.kind!=='formula') this.error(node.id,'Boolean operands require formulas.','exact-22');
      return FORMULA;
    }
    if(left&&left.kind!=='relation'||right&&right.kind!=='relation') {this.error(node.id,'Operands require relations.','exact-23');return null;}
    if(!left||!right||left.kind!=='relation'||right.kind!=='relation') return null;
    if(node.tag==='product') return this.resultSchema(node.id,[...left.columns,...right.columns]);
    if(node.tag==='join') {
      if(left.columns.at(-1)!==right.columns[0]) {this.error(node.id,'Join nominal endpoint mismatch.','exact-24',[left.columns.at(-1)!],[right.columns[0]]);return null;}
      return this.resultSchema(node.id,[...left.columns.slice(0,-1),...right.columns.slice(1)]);
    }
    if(!sameType(left,right)) this.error(node.id,'Ordered nominal schemas must be identical.','exact-25',left.columns,right.columns);
    return node.tag==='equal'||node.tag==='subset'?FORMULA:left;
  }
  /** Validate derived schema bounds. @param id Node. @param columns Ordered derived signature identities. @returns Valid relation type. */
  private resultSchema(id:Id,columns:Schema):Type|null {
    if(!schemaValid(this.module,columns)) {this.error(id,'Result schema must be nonempty and width<=8.','exact-26',['width1..8','declared-columns'],columns);return null;}
    return {kind:'relation',columns};
  }
  /** Preserve exact submitted field ownership order in grouping violations. @returns Ordered field identity facts. */
  private fieldOrderFacts():readonly string[] {const facts:string[]=[];for(const field of this.module.fields) facts.push(field.id,field.ownerSignatureId);return facts;}
  /** Preserve lexical identity and ordered schemas in scope-error keys. @param env Visible bindings. @returns Exact scope facts. */
  private scopeFacts(env:readonly Parameter[]):readonly string[] {
    const facts:string[]=[];for(const parameter of env) facts.push(parameter.id,...parameter.columns);return facts;
  }
  /** Identify the exact dependency edges participating in the root cycle. @param edges Dependency graph. @param root Predicate. @returns Canonical cycle-edge facts. */
  private cycleFacts(edges:ReadonlyMap<Id,ReadonlySet<Id>>,root:Id):readonly string[] {
    const facts:string[]=[];
    for(const [source,targets] of edges) for(const target of targets) {
      const fromRoot=source===root||this.reaches(edges,root,source,new Set());
      const toRoot=target===root||this.reaches(edges,target,root,new Set());
      if(fromRoot&&toRoot) facts.push(JSON.stringify([source,target]));
    }
    return facts.sort();
  }
  /** Check command target kinds/options. @returns Nothing. */
  private commands():void {
    for(const command of this.module.commands) {
      let valid=false;
      for(const pred of this.module.predicates) if(command.tag==='run'&&command.targetId===pred.id&&pred.parameters.length===0) valid=true;
      for(const assertion of this.module.assertions) if(command.tag==='check'&&command.targetId===assertion.id) valid=true;
      if(!valid) this.error(command.id,'run needs nullary predicate; check needs assertion.','exact-27',[],[command.tag,command.targetId]);
      if(command.uniformScope<1||command.uniformScope>5||!Number.isInteger(command.uniformScope)||command.bitwidth!==4||command.maxseq!==3) this.error(command.id,'Invalid bounded command options.','exact-28',[],[String(command.uniformScope),String(command.bitwidth),String(command.maxseq)]);
    }
  }
  /** Reject finite predicate dependency cycles. @returns Nothing. */
  private dependencies():void {
    const edges=new Map<Id,Set<Id>>();
    for(const pred of this.module.predicates) {
      const calls=new Set<Id>();
      for(const id of this.collect(pred.bodyId)) {
        const node=this.index.get(id);
        if(node?.tag==='predicate_call') calls.add(node.predicateId);
      }
      edges.set(pred.id,calls);
    }
    for(const pred of this.module.predicates) if(this.reaches(edges,pred.id,pred.id,new Set())) this.error(pred.id,'Recursive predicate dependency.','exact-29',[],this.cycleFacts(edges,pred.id));
  }
  /** Collect bounded descendants. @param root Root. @returns Descendant IDs. */
  private collect(root:Id):ReadonlySet<Id> {
    const seen=new Set<Id>(),pending=[root];
    while(pending.length) {const id=pending.pop()!;if(seen.has(id)) continue;seen.add(id);const node=this.index.get(id);if(node) pending.push(...children(node));}
    return seen;
  }
  /** Search dependency paths. @param edges Graph. @param start Source. @param target Target. @param seen Visited. @returns Reachable. */
  private reaches(edges:ReadonlyMap<Id,ReadonlySet<Id>>,start:Id,target:Id,seen:Set<Id>):boolean {
    if(seen.has(start)) return false;
    seen.add(start);
    for(const next of edges.get(start)??[]) if(next===target||this.reaches(edges,next,target,seen)) return true;
    return false;
  }
}
