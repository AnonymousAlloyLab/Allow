import type {Diagnostic,EnforcementViolation} from './types';
import {issue} from './model';
/** Match a complete exact-type error to the same explicit expected constraint. @param legacy Existing complete error. @param partial Partial violation. @returns Whether one display message already covers the same expectation. */
function sameExpectation(legacy:EnforcementViolation,partial:EnforcementViolation):boolean {
  if(legacy.identity.rule!=='exact-11'||legacy.nodeId!==partial.nodeId) return false;
  const expected=legacy.identity.expected,tokens=expected[0]==='formula'?['formula']:['relation',JSON.stringify(expected.slice(1))];
  return JSON.stringify(tokens)===JSON.stringify(partial.identity.expected);
}
/** Detect a legacy parent message that already explains this specific partial rule. @param legacy Existing exact-checker error. @param partial Candidate message. @returns Semantic display coverage only. */
function covered(legacy:EnforcementViolation,partial:EnforcementViolation):boolean {
  if(sameExpectation(legacy,partial)) return true;
  if(legacy.identity.ownerId!==partial.identity.ownerId||partial.identity.role.endsWith(':explicit')) return false;
  const rule=legacy.identity.rule,kind=partial.identity.rule;
  if(kind==='expect') return ['exact-19','exact-20','exact-21','exact-22','exact-23'].includes(rule);
  if(kind==='equal') return rule==='exact-25';
  if(kind==='transpose') return rule==='exact-21';
  if(kind==='join') return rule==='exact-24'||rule==='exact-26';
  return kind==='product'&&rule==='exact-26';
}
/** Fill remaining display capacity with novel partial errors, preserving full private enforcement separately. @param diagnostics Capped user projection. @param legacy Complete legacy violations. @param partial Complete partial violations. @returns Nothing. */
export function appendPartialDiagnostics(diagnostics:Diagnostic[],legacy:ReadonlyMap<string,EnforcementViolation>,partial:ReadonlyMap<string,EnforcementViolation>):void {
  for(const value of partial.values()) {
    let represented=false;
    for(const prior of legacy.values()) if(covered(prior,value)) {represented=true;break;}
    if(!represented) for(const prior of diagnostics) if(prior.nodeId===value.nodeId&&prior.message===value.message) represented=true;
    if(!represented) issue(diagnostics,value.nodeId,value.message);
  }
}
