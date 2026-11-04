package dev.allow.corpus;

import java.util.List;

/** Strict worker response.
 * @param status discovery or admission status
 * @param targetSlots anonymous discovery results
 * @param record admitted or partial evidence
 * @param reason fixed diagnostic code
 */
public record CorpusResponse(String status, List<Integer> targetSlots, Object record, String reason) { }
