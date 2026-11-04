/** Describe local replay without extending the claim to the running implementation. @param status Replay state. @returns Evidence label. */
export function certificateLabel(status: string): string {
  if (status === 'CHECKED') return 'Equivalence certificate checked';
  if (status === 'FAILED') return 'Certificate check failed';
  return 'Equivalence certificate unavailable';
}
/** Describe registry search termination independently from certificate evidence. @param reason Engine stop reason. @returns Readable termination label. */
export function stopLabel(reason: string): string {
  const labels: Record<string,string> = {
    SATURATED:'Saturated within supported rules',NODE_LIMIT:'Node budget reached',
    ITERATION_LIMIT:'Iteration budget reached',MATCH_LIMIT:'Match budget reached',
    UNION_LIMIT:'Union budget reached',PROOF_LIMIT:'Proof budget reached',
    TIME_LIMIT:'Time budget reached',INPUT_LIMIT:'Input budget reached',
    OUTPUT_LIMIT:'Output budget reached',ERROR:'Optimization unavailable',
  };
  return labels[reason] ?? 'Search termination unavailable';
}
/** Explain the precise evidence boundary of a checked result. @param reason Engine stop reason. @returns Search scope caption. */
export function searchCaption(reason: string): string {
  return reason === 'SATURATED'
    ? 'No further work was found in this finite rule profile. This is not a complete normal form for Alloy.'
    : 'Search is incomplete. A checked extraction remains equivalent under the supported rule profile.';
}
