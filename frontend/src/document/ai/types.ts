import type {Candidate} from '../types';
import type {DocumentState} from '../state';
export type Kind='SOURCE_EDIT'|'EXPLANATION';
export interface Config {readonly mode:'OFF'|'FIXTURE'|'REMOTE_ASSISTED';readonly model:string;readonly termsVersion:string}
export interface Proposal {readonly source:string;readonly explanation:string;readonly projection:string;readonly sourceHash:string;readonly proposalHash:string}
export interface Job {readonly id:string;readonly status:string;readonly binding:string;readonly expiresAt:string;readonly attempt:number;readonly beforeSource:string|null;readonly payload:string|null;readonly payloadHash:string|null;readonly model:string;readonly termsVersion:string;readonly code:string|null;readonly proposal?:Proposal|null}
export interface Receipt {readonly receiptId:string;readonly jobId:string;readonly binding:string;readonly proposalHash:string;readonly source:string;readonly sourceHash:string;readonly expiresAt:string}
export interface Snapshot {readonly key:string;readonly document:DocumentState;readonly candidate:Candidate}
export interface Create {readonly requestId:string;readonly documentId:string;readonly baseRevision:number;readonly draftId:string;readonly draftEpoch:number;readonly contentGeneration:number;readonly artifactId:string;readonly sourceHash:string;readonly candidate:Candidate;readonly intent:string;readonly kind:Kind}
export interface Undo {readonly prior:DocumentState;readonly appliedKey:string;readonly receiptId:string}
export interface AssistantState {readonly config:Config|null;readonly job:Job|null;readonly snapshot:Snapshot|null;readonly undo:Undo|null;readonly busy:boolean;readonly notice:string}
