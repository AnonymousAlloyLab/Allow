export interface EGraphTerm { readonly op: string; readonly sort: {readonly kind: string; readonly schema: readonly (readonly string[])[]}; readonly atom: string; readonly children: readonly EGraphTerm[] }
export interface GraphEdge { readonly from: number; readonly to: number; readonly position: number }
export interface GraphClass { readonly id: number; readonly nodes: readonly EGraphTerm[] }
export interface EGraphIsland {
  readonly rootPath: readonly number[];
  readonly certificateStatus: string;
  readonly stopReason: string;
  readonly input: EGraphTerm | null;
  readonly extracted: EGraphTerm | null;
  readonly inputCost: number | null;
  readonly extractedCost: number | null;
  readonly stats: Readonly<Record<string,number>>;
  readonly preview: {readonly classes?: readonly GraphClass[]; readonly truncated?: boolean; readonly edges?: readonly GraphEdge[]};
  readonly proofSummary: Readonly<Record<string,unknown>>;
  readonly certificate: unknown | null;
}
export interface EGraphView { readonly profile: string; readonly rulesetDigest: string; readonly status: string; readonly islands: readonly EGraphIsland[]; readonly truncated: boolean }
/** Render bounded anonymous JSON for inspection. @param value Anonymous wire data. @returns Indented JSON. */
export function anonymousJson(value: unknown): string { return JSON.stringify(value,null,2) ?? 'Unavailable'; }
/** Name an anonymous occurrence without introducing source labels. @param island Source-bound optimization island. @returns Numeric occurrence label. */
export function islandLabel(island: EGraphIsland): string { return `Root ${island.rootPath.length ? island.rootPath.join('.') : '0'}`; }
