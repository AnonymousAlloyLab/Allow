/** Local corpus metadata and ranked evidence, kept separate from the editable workbench. */
export interface CorpusRecord { id: string; family: string; split: string; n: number; status: string }
export interface CorpusStatus { records: number; full: number; vectors: number; revoked: number; journal_sequence: number }
export interface CorpusHit {
  recordId: string; family: string; score: number; canonicalSimilarity: number; predicateCosine: number;
  sharedPositive: number; sharedNegative: number; contextCompatible: boolean; positiveCount: number; negativeCount: number;
}
export interface CorpusSearch { queryRecordId: string; modelId: string; exact: boolean; candidateCount: number; weights: readonly number[]; results: readonly CorpusHit[] }
type ObjectValue = Record<string, unknown>;

/** Require an object before reading server metadata. @param value Parsed JSON. @returns Object fields. */
function object(value: unknown): ObjectValue {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid corpus response.');
  return value as ObjectValue;
}
/** Validate one finite numeric field. @param value Server field. @returns Finite number. */
function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('Invalid corpus measurement.');
  return value;
}
/** Validate one text field. @param value Server field. @returns Plain text. */
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid corpus metadata.');
  return value;
}
/** Read an authenticated corpus envelope. @param token Launch authority. @param path Fixed endpoint. @param body Optional query. @returns Data fields. */
async function request(token: string, path: string, body?: ObjectValue): Promise<ObjectValue> {
  const response = await fetch(`/api/corpus/${path}`, {method:body ? 'POST' : 'GET',
    headers:{Authorization:`Bearer ${token}`,...(body ? {'Content-Type':'application/json'} : {})},
    ...(body ? {body:JSON.stringify(body)} : {})});
  if (!response.ok) throw new Error(response.status === 503 ? 'Start the local corpus service to browse its records.' : 'Corpus request failed.');
  const envelope = object(await response.json());
  if (envelope.protocol !== 1 || envelope.status !== 'OK') throw new Error('The corpus is unavailable or quarantined.');
  return object(envelope.data);
}
/** Decode bounded corpus counters. @param token Launch authority. @returns Current local counts. */
export async function corpusStatus(token: string): Promise<CorpusStatus> {
  const data = await request(token,'status');
  return {records:number(data.records),full:number(data.full),vectors:number(data.vectors),
    revoked:number(data.revoked),journal_sequence:number(data.journal_sequence)};
}
/** Decode one stored record selector. @param value Server row. @returns Safe selector metadata. */
function record(value: unknown): CorpusRecord {
  const row = object(value);
  return {id:text(row.id),family:text(row.family),split:text(row.split),n:number(row.n),status:text(row.status)};
}
/** Fetch the bounded selectable record list. @param token Launch authority. @returns Stored record summaries. */
export async function corpusRecords(token: string): Promise<readonly CorpusRecord[]> {
  const data = await request(token,'records');
  if (!Array.isArray(data.records)) throw new Error('Invalid corpus record list.');
  return data.records.map(record);
}
/** Decode a ranked result without interpreting similarity as proof. @param value Server row. @returns Numeric score breakdown. */
function hit(value: unknown): CorpusHit {
  const row = object(value);
  if (typeof row.contextCompatible !== 'boolean') throw new Error('Invalid corpus compatibility status.');
  return {recordId:text(row.recordId),family:text(row.family),score:number(row.score),
    canonicalSimilarity:number(row.canonicalSimilarity),predicateCosine:number(row.predicateCosine),
    sharedPositive:number(row.sharedPositive),sharedNegative:number(row.sharedNegative),
    contextCompatible:row.contextCompatible,positiveCount:number(row.positiveCount),negativeCount:number(row.negativeCount)};
}
/** Validate a response against the selected stored query identity. @param value Envelope data. @param query Expected record. @returns Ranked evidence. */
export function decodeSearch(value: unknown, query: string): CorpusSearch {
  const data = object(value);
  if (data.queryRecordId !== query || !Array.isArray(data.results) || !Array.isArray(data.weights)
      || typeof data.exact !== 'boolean') throw new Error('Corpus query identity changed.');
  return {queryRecordId:query,modelId:text(data.modelId),exact:data.exact,
    candidateCount:number(data.candidateCount),weights:data.weights.map(number),results:data.results.map(hit)};
}
/** Retrieve candidates using only an existing server-owned query record. @param token Authority. @param query Record identity. @returns Scored candidates. */
export async function corpusSearch(token: string, query: string): Promise<CorpusSearch> {
  return decodeSearch(await request(token,'search',{recordId:query,limit:5}),query);
}
