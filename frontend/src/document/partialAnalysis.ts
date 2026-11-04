import type {DraftModule,Id,Check,SlotObligation,PartialFact,PartialLimits,ResourceFailure,EnforcementViolation,DestinationConstraint} from './types';
import {unknownShapes,typeFact,factTokens,violation,intersectShapes,sameFact} from './partialShapes';
import {ruleGraph,constructorSort} from './partialRules';
import type {Equation,RuleGraph} from './partialRules';
import {equalitySupports,transposeSupports,compositionSupports} from './partialSupports';
import {destinations} from './partialDestinations';
export const DEFAULT_PARTIAL_LIMITS:PartialLimits={columnVariables:4096,equations:32768,violations:65536,worklistPops:262144,refinements:262144};
type ExactCheck=Pick<Check,'types'|'scopes'|'diagnostics'|'complete'>;
export interface AnalysisResult {readonly facts:ReadonlyMap<Id,PartialFact>;readonly destinations:ReadonlyMap<Id,DestinationConstraint>;readonly violations:ReadonlyMap<string,EnforcementViolation>;readonly resourceFailure:ResourceFailure|null}
/** Bounded monotone refinement over one fixed canonical equation inventory. */
class PartialAnalysis {
  private readonly facts=new Map<Id,PartialFact>();
  private readonly violations=new Map<string,EnforcementViolation>();
  private readonly dependencies=new Map<Id,Set<number>>();
  private readonly pending:number[]=[];
  private readonly queued=new Set<number>();
  private readonly counters:Record<keyof PartialLimits,number>={columnVariables:0,equations:0,violations:0,worklistPops:0,refinements:0};
  private failure:ResourceFailure|null=null;
  private readonly graph:RuleGraph;
  /** Bind immutable inputs and seed structural result sorts. @param module Forest. @param checked Exact projections. @param obligations Explicit retained slots. @param limits Resource bounds. */
  constructor(private readonly module:DraftModule,checked:ExactCheck,obligations:readonly SlotObligation[],private readonly limits:PartialLimits) {
    if(obligations.length>limits.equations) {
      this.failure={code:'ANALYSIS_RESOURCE_LIMIT',counter:'equations',limit:limits.equations};
      this.graph={equations:[],slots:new Map(),valid:true};
    } else this.graph=ruleGraph(module,obligations);
    for(const node of module.nodes) {
      const sort=constructorSort(node,checked),exact=checked.types.get(node.id);
      this.facts.set(node.id,exact?typeFact(exact):{sort,shapes:sort==='relation'?unknownShapes():[]});
    }
  }
  /** Count bounded operations and fail closed before exceeding a cap. @param counter Versioned budget. @param amount Increment. @returns Whether analysis may continue. */
  private count(counter:keyof PartialLimits,amount=1):boolean {
    this.counters[counter]+=amount;
    if(this.counters[counter]>this.limits[counter]) this.failure={code:'ANALYSIS_RESOURCE_LIMIT',counter,limit:this.limits[counter]};
    return !this.failure;
  }
  /** Queue an existing equation once; refinement never allocates new equations. @param index Fixed inventory position. @returns Nothing. */
  private enqueue(index:number):void {if(!this.queued.has(index)) {this.queued.add(index);this.pending.push(index);}}
  /** Publish only a stricter fact and wake its pre-existing dependent equations. @param id Node. @param fact Refined fact. @returns Nothing. */
  private refine(id:Id,fact:PartialFact):void {
    const prior=this.facts.get(id);if(!prior||sameFact(prior,fact)||this.failure) return;
    if(!this.count('refinements')) return;
    this.facts.set(id,fact);
    for(const index of this.dependencies.get(id)??[]) this.enqueue(index);
  }
  /** Record one complete enforcement violation independently of capped display diagnostics. @param equation Rule. @param expected Required fact tokens. @param actual Actual fact tokens. @param message Explanation. @returns Nothing. */
  private reject(equation:Equation,expected:readonly string[],actual:readonly string[],message:string):void {
    const value=violation({ownerId:equation.ownerId,role:equation.role,rule:equation.rule,expected,actual,relatedIds:equation.relatedIds??[]},equation.ids[0],message);
    if(this.violations.has(value.key)||!this.count('violations')) return;
    this.violations.set(value.key,value);
  }
  /** Reject invalid explicit nominal schemas without inventing declarations. @param equation Destination rule. @param report Final collection pass. @returns Whether its schema is valid. */
  private validExpected(equation:Equation,report:boolean):boolean {
    const expected=equation.expected;if(!expected||expected==='relation'||expected.kind==='formula') return true;
    const declared=new Set<Id>();for(const signature of this.module.signatures) declared.add(signature.id);
    let valid=expected.columns.length>=1&&expected.columns.length<=8;for(const column of expected.columns) if(!declared.has(column)) valid=false;
    if(!valid&&report) this.reject(equation,['declared-schema-width1..8'],factTokens(typeFact(expected)),'Invalid nominal destination schema.');
    return valid;
  }
  /** Apply one required sort/schema while retaining constructor facts on contradiction. @param equation Expectation. @param report Whether collecting final violations. @returns Nothing. */
  private expectation(equation:Equation,report:boolean):void {
    const id=equation.ids[0],prior=this.facts.get(id)!;
    if(!this.validExpected(equation,report)) return;
    const base=equation.expected==='relation'?{sort:'relation' as const,shapes:unknownShapes()}:typeFact(equation.expected!);
    const selected=[];for(const shape of base.shapes) if(!equation.widths||equation.widths.includes(shape.columns.length)) selected.push(shape);
    const required={...base,shapes:selected};
    if(prior.sort!=='unknown'&&prior.sort!==required.sort) {
      if(report) this.reject(equation,factTokens(required),factTokens(prior),`Expected ${required.sort}; actual ${prior.sort}.`);
      return;
    }
    const shapes=prior.sort==='unknown'?required.shapes:intersectShapes(prior.shapes,required.shapes);
    if(required.sort==='relation'&&!shapes.length) {
      if(report) this.reject(equation,factTokens(required),factTokens(prior),'Ordered nominal schema or relation width constraint mismatch.');
      return;
    }
    if(!report) this.refine(id,{sort:required.sort,shapes});
  }
  /** Propagate one fixed relation equation through supported finite widths and known columns. @param equation Relational rule. @param report Final violation pass. @returns Nothing. */
  private relation(equation:Equation,report:boolean):void {
    const facts:PartialFact[]=[];for(const id of equation.ids) {const fact=this.facts.get(id)!;if(fact.sort!=='relation') return;facts.push(fact);}
    const domains=[];for(const fact of facts) domains.push(fact.shapes);
    const support=equation.rule==='equal'?equalitySupports(domains[0],domains[1]):equation.rule==='transpose'?transposeSupports(domains[0],domains[1]):compositionSupports(equation.rule as 'join'|'product',domains[0],domains[1],domains[2]);
    let supported=true;for(const shapes of support.inputs) if(!shapes.length) supported=false;
    if(!supported) {
      const tokens:string[]=[];for(const fact of facts) tokens.push(...factTokens(fact));
      if(report) this.reject(equation,[equation.rule],tokens,`Known ${equation.rule} nominal schema, endpoint or width contradiction.`);
      return;
    }
    if(!report) for(let index=0;index<support.inputs.length;index++) this.refine(equation.ids[index],{sort:'relation',shapes:support.inputs[index]});
  }
  /** Dispatch a pre-registered equation without creating work recursively. @param equation Fixed rule. @param report Final violation pass. @returns Nothing. */
  private apply(equation:Equation,report:boolean):void {if(equation.rule==='expect') this.expectation(equation,report);else this.relation(equation,report);}
  /** Initialize bounded dependency indexes only after validating ownership. @returns Whether setup completed. */
  private initialize():boolean {
    if(this.failure) return false;
    if(!this.graph.valid) {this.failure={code:'ANALYSIS_INVALID_GRAPH'};return false;}
    if(!this.count('columnVariables',this.module.nodes.length*8)||!this.count('equations',this.graph.equations.length)) return false;
    let index=0;for(const equation of this.graph.equations) {
      for(const id of equation.ids) {const rows=this.dependencies.get(id)??new Set<number>();rows.add(index);this.dependencies.set(id,rows);}
      this.enqueue(index++);
    }
    return true;
  }
  /** Complete fixed-point enforcement or expose explicit failure; partial sets never authorize edits. @returns Analysis result. */
  run():AnalysisResult {
    if(this.initialize()) {
      let cursor=0;
      while(cursor<this.pending.length&&!this.failure) {
        const index=this.pending[cursor++];this.queued.delete(index);
        if(!this.count('worklistPops')) break;
        this.apply(this.graph.equations[index],false);
      }
      if(!this.failure) for(const equation of this.graph.equations) {this.apply(equation,true);if(this.failure) break;}
    }
    return {facts:this.facts,destinations:destinations(this.module,this.graph,this.facts),violations:this.violations,resourceFailure:this.failure};
  }
}
/** Analyze all partial result and destination constraints independently of exact completion. @param module Forest. @param checked Exact projections. @param obligations Retained explicit slots. @param limits Optional lower test budgets. @returns Complete enforcement or explicit failure. */
export function analyzePartial(module:DraftModule,checked:ExactCheck,obligations:readonly SlotObligation[],limits:PartialLimits=DEFAULT_PARTIAL_LIMITS):AnalysisResult {
  const bounded={...DEFAULT_PARTIAL_LIMITS};
  for(const key of Object.keys(bounded) as (keyof PartialLimits)[]) {
    const value=limits[key];bounded[key]=Number.isNaN(value)?0:Math.max(0,Math.floor(Math.min(DEFAULT_PARTIAL_LIMITS[key],value)));
  }
  return new PartialAnalysis(module,checked,obligations,bounded).run();
}
