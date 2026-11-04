/** Candidate integration interface only; no production import or authorization. */
import type {Id,Schema,Type,Diagnostic,Parameter} from '../../../frontend/src/document/types';
/** An owning edge survives replacement of its child expression identity. */
export interface SlotAddress {readonly ownerId:Id;readonly role:'body'|'operand'|'left'|'right'|'argument';readonly index?:number}
/** Explicit retained constraint; parent constraints are recomputed, never copied from old inferred types. */
export interface SlotObligation {readonly slot:SlotAddress;readonly expected:Type}
/** One finite possible width; null columns remain nominally unresolved, never fabricated IDs. */
export interface SchemaShape {readonly columns:readonly (Id|null)[]}
/** Alternative widths are unique, sorted1..8; known columns refine monotonically by exact identity. */
export interface PartialFact {readonly sort:'unknown'|'formula'|'relation';readonly shapes:readonly SchemaShape[]}
/** Stable exact identity; all arrays are ordered and canonical, unrelated to display text. */
export interface ViolationIdentity {readonly ownerId:Id;readonly role:string;readonly rule:string;readonly expected:readonly string[];readonly actual:readonly string[];readonly relatedIds:readonly Id[]}
/** Key is JSON.stringify([ownerId,role,rule,expected,actual,relatedIds]), never a hash or message. */
export interface EnforcementViolation {readonly key:string;readonly identity:ViolationIdentity;readonly nodeId:Id;readonly message:string}
/** Fixed per-analysis caps; lower overrides are permitted only for deterministic tests. */
export interface PartialLimits {readonly columnVariables:number;readonly equations:number;readonly violations:number;readonly worklistPops:number;readonly refinements:number}
/** A complete analysis is mandatory for both sides of guarded violation-set comparison. */
export interface ResourceFailure {readonly code:'ANALYSIS_RESOURCE_LIMIT';readonly counter:keyof PartialLimits;readonly limit:number}
/** Structured slot constraints are computed once and also feed the accessible display adapter. */
export interface DestinationConstraint {readonly slot:SlotAddress;readonly sort:'formula'|'relation';readonly exact:Schema|null;readonly widths:readonly number[];readonly descriptions:readonly string[]}
/** Existing Check projections remain exact; partial relation shapes never enter types. */
export interface PartialCheck {
  readonly diagnostics:readonly Diagnostic[];
  readonly types:ReadonlyMap<Id,Type>;
  readonly scopes:ReadonlyMap<Id,readonly Parameter[]>;
  readonly complete:boolean;
  readonly facts:ReadonlyMap<Id,PartialFact>;
  readonly destinations:ReadonlyMap<Id,DestinationConstraint>;
  readonly violations:ReadonlyMap<string,EnforcementViolation>;
  readonly resourceFailure:ResourceFailure|null;
}
/** Expected production signature: checkModule(module:DraftModule, obligations:readonly SlotObligation[]=[], limits?:PartialLimits):Check. */
export type CheckIntegrationContract = PartialCheck;
