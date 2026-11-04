export type Id = string;
export type Schema = readonly Id[];
export type Multiplicity = 'set'|'one'|'lone'|'some';
export type UnaryTag = 'not'|'some_test'|'no_test'|'one_test'|'lone_test'|'transpose';
export type BinaryTag = 'and'|'or'|'implies'|'iff'|'equal'|'subset'|'union'|'intersection'|'difference'|'join'|'product';
export type QuantTag = 'all_quant'|'some_quant';
export interface Binder { readonly id: Id; readonly name: string; readonly signatureId: Id }
export type Expression =
  | {readonly tag:'signature_ref'|'field_ref'|'variable_ref'; readonly id:Id; readonly targetId:Id}
  | {readonly tag:'predicate_call'; readonly id:Id; readonly predicateId:Id; readonly arguments:readonly Id[]}
  | {readonly tag:UnaryTag; readonly id:Id; readonly operandId:Id}
  | {readonly tag:BinaryTag; readonly id:Id; readonly leftId:Id; readonly rightId:Id}
  | {readonly tag:QuantTag; readonly id:Id; readonly binder:Binder; readonly bodyId:Id};
export interface Hole { readonly tag:'hole'; readonly id:Id; readonly expected:Type|null }
export type DraftNode = Expression|Hole;
export type Type = {readonly kind:'formula'}|{readonly kind:'relation'; readonly columns:Schema};
export interface Signature {readonly tag:'signature'; readonly id:Id; readonly name:string; readonly multiplicity:Multiplicity}
export interface Field {readonly tag:'field'; readonly id:Id; readonly name:string; readonly ownerSignatureId:Id; readonly rangeColumns:Schema; readonly multiplicity:Multiplicity}
export interface Parameter {readonly tag:'parameter'; readonly id:Id; readonly name:string; readonly columns:Schema}
export interface Predicate {readonly tag:'predicate'; readonly id:Id; readonly name:string; readonly parameters:readonly Parameter[]; readonly bodyId:Id}
export interface FormulaDeclaration {readonly tag:'fact'|'assertion'; readonly id:Id; readonly name:string; readonly bodyId:Id}
export interface Command {readonly tag:'run'|'check'; readonly id:Id; readonly targetId:Id; readonly uniformScope:number; readonly bitwidth:4; readonly maxseq:3}
export interface Module {
  readonly version:1; readonly signatures:readonly Signature[]; readonly fields:readonly Field[];
  readonly predicates:readonly Predicate[]; readonly facts:readonly FormulaDeclaration[];
  readonly assertions:readonly FormulaDeclaration[]; readonly commands:readonly Command[];
  readonly nodes:readonly Expression[];
}
export interface DraftModule extends Omit<Module,'nodes'> {readonly nodes:readonly DraftNode[]}
export interface PresentationCopy {readonly sourceNodeId:Id; readonly targetNodeId:Id}
export type Candidate = {readonly mode:'SOURCE'; readonly source:string}|{readonly mode:'BLOCK_SUPPORTED'; readonly module:Module; readonly presentationCopies:readonly PresentationCopy[]};
export interface Occurrence {readonly occurrenceId:string;readonly nodeId:Id;readonly role:string;readonly startUtf16:number;readonly endUtf16:number}
export interface AnalysisDescriptor {readonly commandKey:string;readonly index:number;readonly kind:'run'|'check';readonly label:string;readonly artifactId:string;readonly sourceHash:string;readonly policyVersion:string|number;readonly options:Readonly<Record<string,unknown>>}
export interface Artifact {
  readonly artifactId:string; readonly mode:'BLOCK_SUPPORTED'|'TEXT_ONLY'; readonly source:string;
  readonly sourceHash:string; readonly module:Module|null; readonly occurrences:readonly Occurrence[];
  readonly trivia:readonly unknown[]; readonly analysisDescriptors:readonly AnalysisDescriptor[];
  readonly policyVersion:string|number; readonly dependencyHash:string;
}
export interface Accepted {readonly documentId:string;readonly revision:number;readonly headRevision:number;readonly artifact:Artifact;readonly provenance:unknown}
export interface Envelope<T> {readonly protocol:1;readonly requestId:string;readonly status:string;readonly data:T}
export interface Diagnostic {readonly nodeId?:Id;readonly role?:string;readonly code?:string;readonly message:string}
export interface Validation {
  readonly draftId:string;readonly draftEpoch:number;readonly baseRevision:number;readonly requestHash:string;
  readonly supportMode:string;readonly diagnostics:readonly Diagnostic[];readonly proposedSource:string|null;
  readonly proposedSourceHash:string|null;readonly sourceHash?:string;
}
export interface CommitData {readonly documentId:string;readonly revision:number;readonly artifact:Artifact;readonly sourceHash:string;readonly policyVersion:string|number;readonly idRemapping:Readonly<Record<string,string>>;readonly provenance:unknown}
export interface RejectedData {readonly code:string;readonly acceptedRevision:number;readonly diagnostics:readonly Diagnostic[]}
export interface AvailabilityData {readonly code?:string;readonly message?:string}
export type MutationData = CommitData|RejectedData|AvailabilityData;
export interface DocumentSummary {readonly documentId:string;readonly title:string;readonly headRevision:number}
export interface ListData {readonly documents:readonly DocumentSummary[]}
export interface Pending {readonly route:string;readonly method:'POST';readonly body:string;readonly key:string;readonly draftId:string;readonly epoch:number}
export interface Check {readonly diagnostics:readonly Diagnostic[];readonly types:ReadonlyMap<Id,Type>;readonly scopes:ReadonlyMap<Id,readonly Parameter[]>;readonly complete:boolean;readonly facts:ReadonlyMap<Id,PartialFact>;readonly destinations:ReadonlyMap<Id,DestinationConstraint>;readonly violations:ReadonlyMap<string,EnforcementViolation>;readonly resourceFailure:ResourceFailure|null}
/** Stable owning edge; replacing its child does not replace the slot. */
export interface SlotAddress {readonly ownerId:Id;readonly role:'body'|'operand'|'left'|'right'|'argument';readonly index?:number}
/** Browser-only explicit constraint, stored separately from the serialized module. */
export interface SlotObligation {readonly slot:SlotAddress;readonly expected:Type}
/** One possible finite width with unresolved nominal columns represented explicitly. */
export interface SchemaShape {readonly columns:readonly (Id|null)[]}
/** Constructor result sort is independent of operand completion. */
export interface PartialFact {readonly sort:'unknown'|'formula'|'relation';readonly shapes:readonly SchemaShape[]}
/** Canonical violation identity does not use diagnostic display text. */
export interface ViolationIdentity {readonly ownerId:Id;readonly role:string;readonly rule:string;readonly expected:readonly string[];readonly actual:readonly string[];readonly relatedIds:readonly Id[]}
/** Complete enforcement record; diagnostics remain a separately bounded projection. */
export interface EnforcementViolation {readonly key:string;readonly identity:ViolationIdentity;readonly nodeId:Id;readonly message:string}
/** Explicit bounds for one whole-module analysis; tests can lower them. */
export interface PartialLimits {readonly columnVariables:number;readonly equations:number;readonly violations:number;readonly worklistPops:number;readonly refinements:number}
/** Incomplete enforcement always fails closed. */
export type ResourceFailure={readonly code:'ANALYSIS_RESOURCE_LIMIT';readonly counter:keyof PartialLimits;readonly limit:number}|{readonly code:'ANALYSIS_INVALID_GRAPH'};
/** Shared structured destination description, indexed by the current child identity. */
export interface DestinationConstraint {readonly slot:SlotAddress;readonly sort:'formula'|'relation';readonly exact:Schema|null;readonly widths:readonly number[];readonly descriptions:readonly string[]}
