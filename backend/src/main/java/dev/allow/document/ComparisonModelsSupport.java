package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Conservative background matching for independently elaborated models. */
final class ComparisonModelsSupport {
    /** Prevents construction. */
    private ComparisonModelsSupport() {}
    /** Allocates an identity.
     * @return fresh worker-only identity
     */
    static String id() { return "server:" + UUID.randomUUID(); }
    /** Finds a declaration name.
     * @param module checked model
     * @param id declaration identity
     * @return declaration name
     * @throws IllegalArgumentException missing identity
     */
    static String name(JsonNode module, String id) {
        for (String key : List.of("signatures", "fields", "predicates", "facts", "assertions"))
            for (JsonNode item : module.path(key)) if (id.equals(item.path("id").asText())) return item.path("name").asText();
        throw new IllegalArgumentException("missing declaration identity");
    }
    /** Finds a predicate.
     * @param module checked model
     * @param name predicate name
     * @return selected predicate
     * @throws IllegalArgumentException missing predicate
     */
    static ObjectNode predicate(ObjectNode module, String name) {
        for (JsonNode pred : module.path("predicates")) if (name.equals(pred.path("name").asText())) return (ObjectNode) pred;
        throw new IllegalArgumentException("selected predicate missing");
    }
    /** Indexes nodes.
     * @param module checked model
     * @return node identity index
     */
    static Map<String, JsonNode> index(JsonNode module) {
        Map<String, JsonNode> result = new HashMap<>();
        for (JsonNode node : module.path("nodes")) result.put(node.path("id").asText(), node);
        return result;
    }
    /** Lists children.
     * @param node expression
     * @return ordered owned child identities
     */
    static List<String> children(JsonNode node) {
        List<String> result = new ArrayList<>();
        for (String key : List.of("operandId", "leftId", "rightId", "bodyId")) if (node.has(key)) result.add(node.path(key).asText());
        for (JsonNode arg : node.path("arguments")) result.add(arg.asText());
        return result;
    }
    /** Collects a subtree.
     * @param module checked model
     * @param root root ID
     * @return owned subtree IDs
     * @throws IllegalArgumentException invalid ownership
     */
    static Set<String> subtree(JsonNode module, String root) {
        Map<String, JsonNode> nodes = index(module); Set<String> result = new HashSet<>(); List<String> todo = new ArrayList<>(); todo.add(root);
        while (!todo.isEmpty()) { String id = todo.remove(todo.size() - 1); JsonNode node = nodes.get(id);
            if (node == null || !result.add(id)) throw new IllegalArgumentException("invalid expression ownership");
            todo.addAll(children(node)); }
        return result;
    }
    /** Normalizes a background.
     * @param module checked model
     * @param selected selected predicate
     * @return normalized background
     * @throws IllegalArgumentException selected dependency
     */
    static ObjectNode background(ObjectNode module, JsonNode selected) {
        ObjectNode copy = module.deepCopy(); String selectedId = selected.path("id").asText();
        Set<String> owned = subtree(copy, selected.path("bodyId").asText());
        for (JsonNode node : copy.path("nodes")) if (!owned.contains(node.path("id").asText())
                && selectedId.equals(node.path("predicateId").asText())) throw new IllegalArgumentException("background depends on selected predicate");
        ArrayNode preds = copy.withArray("predicates");
        for (int i = preds.size() - 1; i >= 0; i--) if (selectedId.equals(preds.get(i).path("id").asText())) preds.remove(i);
        for (String key : List.of("signatures", "fields", "predicates", "facts", "assertions")) sort(copy.withArray(key));
        normalizeBinders(copy);
        return copy;
    }
    /** Sorts declarations.
     * @param values declaration collection
     */
    private static void sort(ArrayNode values) {
        List<JsonNode> items = new ArrayList<>(); values.forEach(items::add);
        items.sort(Comparator.comparing(ComparisonModelsSupport::itemName)); values.removeAll(); items.forEach(values::add);
    }
    /** Reads a declaration name.
     * @param node declaration
     * @return name
     */
    private static String itemName(JsonNode node) { return node.path("name").asText(); }
    /** Normalizes local binder names.
     * @param module mutable background
     */
    private static void normalizeBinders(ObjectNode module) {
        Map<String, JsonNode> nodes = index(module); int[] next = {0};
        for (JsonNode pred : module.path("predicates")) {
            for (JsonNode param : pred.path("parameters")) ((ObjectNode) param).put("name", "binder" + next[0]++);
            normalizeTree(nodes, pred.path("bodyId").asText(), next);
        }
        for (String key : List.of("facts", "assertions")) for (JsonNode item : module.path(key)) normalizeTree(nodes, item.path("bodyId").asText(), next);
    }
    /** Normalizes one tree.
     * @param nodes node index
     * @param id current expression
     * @param next deterministic counter
     */
    private static void normalizeTree(Map<String, JsonNode> nodes, String id, int[] next) {
        JsonNode node = nodes.get(id);
        if (node.has("binder")) ((ObjectNode) node.path("binder")).put("name", "binder" + next[0]++);
        for (String child : children(node)) normalizeTree(nodes, child, next);
    }
}
