package dev.allow.egraph;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
/** Generic recursive e-matching over a rebuilt finite snapshot.
     */
final class Matcher {
    private final EGraph graph;
    private final RunBudget budget;
    /** Binds a finite search snapshot.
     * @param graph rebuilt graph
     * @param budget expansion resources
     */
    Matcher(EGraph graph, RunBudget budget) { this.graph = graph; this.budget = budget; }
    /** Enumerates substitutions modulo class equality.
     * @param pattern finite registry pattern
     * @param root candidate class
     * @param initial preceding bindings
     * @return deterministic substitutions
     */
    List<Map<String, Integer>> match(JsonNode pattern, int root, Map<String, Integer> initial) {
        budget.match();
        if (pattern.isTextual()) {
            Integer previous = initial.get(pattern.asText());
            if (previous != null) return graph.find(previous) == graph.find(root) ? List.of(initial) : List.of();
            Map<String, Integer> next = new LinkedHashMap<>(initial);
            next.put(pattern.asText(), graph.find(root)); return List.of(Map.copyOf(next));
        }
        List<Map<String, Integer>> result = new ArrayList<>();
        for (int member : graph.members(root)) {
            Term node = graph.node(member);
            if (node.op().equals(pattern.get(0).asText()) && node.children().size() == pattern.size() - 1) {
                result.addAll(operands(pattern, member, initial));
            }
        }
        return result;
    }
    /** Matches ordered operands without losing repeated-variable constraints.
     * @param pattern operator pattern
     * @param member concrete node
     * @param initial existing bindings
     * @return combined matches
     */
    private List<Map<String, Integer>> operands(JsonNode pattern, int member, Map<String, Integer> initial) {
        List<Map<String, Integer>> states = List.of(initial);
        for (int i = 1; i < pattern.size(); i++) {
            List<Map<String, Integer>> next = new ArrayList<>();
            for (Map<String, Integer> state : states) next.addAll(match(pattern.get(i), graph.children(member).get(i - 1), state));
            states = next;
        }
        return states;
    }
}
