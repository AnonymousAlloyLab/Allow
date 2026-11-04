export type Status = 'QUEUED'|'RUNNING'|'VALIDATED'|'SAT'|'UNSAT'|'INVALID'|'UNSUPPORTED'|'UNKNOWN'|'ERROR'|'TIMEOUT'|'CANCELLED';
export interface Job { jobId: string; status: Status; sourceHash: string; revision: number; epoch: number; [key: string]: unknown }
export type JobIdentity = Pick<Job,'jobId'|'sourceHash'|'revision'|'epoch'>;
export interface CancellationOutcome { readonly job: Job | null; readonly error: string | null }
/** Remove the launch authority from the URL. @returns Token held only in memory. */
export function consumeToken(): string {
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '';
  history.replaceState(null,'',window.location.pathname + window.location.search);
  return token;
}
/** Return whether a response belongs to the current edit. @param job Returned identity. @param revision Expected revision. @param epoch Expected edit epoch. @returns Freshness decision. */
export function isCurrent(job: Pick<Job,'revision'|'epoch'>, revision: number, epoch: number): boolean {
  return job.revision === revision && job.epoch === epoch;
}
/** Compare every field binding a response to an active source snapshot. @param actual Observed job identity. @param expected Required job snapshot. @returns Whether job, source, revision and epoch all match. */
export function sameIdentity(actual: JobIdentity, expected: JobIdentity): boolean {
  return isCurrent(actual,expected.revision,expected.epoch)
    && actual.jobId === expected.jobId && actual.sourceHash === expected.sourceHash;
}
/** Send an authenticated request. @param token Launch authority. @param path Same-origin API path. @param init Request options. @returns Parsed response. @throws Error on HTTP failure. */
async function request(token: string, path: string, init: RequestInit = {}): Promise<Job> {
  const response = await fetch(path,{...init,headers:{'Authorization':`Bearer ${token}`,'Content-Type':'application/json',...init.headers}});
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return await response.json() as Job;
}
/** Submit a validation or analysis job. @param token Launch authority. @param source Alloy text. @param revision Document revision. @param epoch Edit epoch. @param operation Job type. @returns Job response. */
export function submit(token: string, source: string, revision: number, epoch: number, operation: 'VALIDATE'|'ANALYZE'): Promise<Job> {
  return request(token,'/api/jobs',{method:'POST',body:JSON.stringify({source,commandIndex:0,revision,epoch,operation})});
}
/** Read a job. @param token Launch authority. @param id Job identifier. @returns Job response. */
export function readJob(token: string, id: string): Promise<Job> { return request(token,`/api/jobs/${encodeURIComponent(id)}`); }
/** Cancel a job. @param token Launch authority. @param id Job identifier. @returns Job response. */
export function cancelJob(token: string, id: string): Promise<Job> { return request(token,`/api/jobs/${encodeURIComponent(id)}`,{method:'DELETE'}); }
/** Cancel a snapshot while suppressing stale success and failure responses. @param token In-memory launch authority. @param snapshot Exact active job and source identity. @param readCurrent Reads the current identity after the request settles. @returns Current matching outcome, or null when stale or mismatched. */
export async function cancelSnapshot(token: string, snapshot: JobIdentity, readCurrent: () => JobIdentity): Promise<CancellationOutcome | null> {
  try {
    const job = await cancelJob(token,snapshot.jobId);
    return sameIdentity(snapshot,readCurrent()) && sameIdentity(job,snapshot) ? {job,error:null} : null;
  } catch (error) {
    if (!sameIdentity(snapshot,readCurrent())) return null;
    return {job:null,error:error instanceof Error ? error.message : 'Cancellation failed.'};
  }
}
/** Fetch server capabilities. @param token Launch authority. @returns Configuration object. */
export function readConfig(token: string): Promise<Job> { return request(token,'/api/config'); }
