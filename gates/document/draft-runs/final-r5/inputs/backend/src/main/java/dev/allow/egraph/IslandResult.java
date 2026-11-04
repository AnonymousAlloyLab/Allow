package dev.allow.egraph;
import java.util.List;
import java.util.Map;
/** Bounded anonymous result independent of solver outcome.
     */
public record IslandResult(List<Integer> rootPath, String certificateStatus, String stopReason,
        Term input, Term extracted, Integer inputCost, Integer extractedCost, Map<String, Long> stats,
        Map<String, Object> preview, Map<String, Object> proofSummary, Certificate certificate) {
    /** Freezes presentation collections.
     * @param rootPath numeric root address
     * @param certificateStatus replay status
     * @param stopReason termination
     * @param input checked input
     * @param extracted checked output
     * @param inputCost input tree cost
     * @param extractedCost output tree cost
     * @param stats engine counters
     * @param preview bounded graph
     * @param proofSummary proof counts
     * @param certificate bounded replay artifact
     */
    public IslandResult {
        rootPath = List.copyOf(rootPath); stats = Map.copyOf(stats);
        preview = freezeMap(preview); proofSummary = freezeMap(proofSummary);
    }
    /** Copies a nested presentation map recursively.
     * @param original caller-owned map
     * @return recursively immutable values
     */
    private static Map<String, Object> freezeMap(Map<String, Object> original) {
        Map<String, Object> result = new java.util.LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : original.entrySet()) result.put(entry.getKey(), freeze(entry.getValue()));
        return Map.copyOf(result);
    }
    /** Copies nested list/map values without mutable collection escape.
     * @param value presentation value
     * @return immutable equivalent
     * @throws IllegalArgumentException when a map has non-string keys
     */
    private static Object freeze(Object value) {
        if (value instanceof List<?> list) {
            List<Object> result = new java.util.ArrayList<>();
            for (Object child : list) result.add(freeze(child));
            return List.copyOf(result);
        }
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> result = new java.util.LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!(entry.getKey() instanceof String key)) throw new IllegalArgumentException("Presentation key");
                result.put(key, freeze(entry.getValue()));
            }
            return Map.copyOf(result);
        }
        return value;
    }

}
