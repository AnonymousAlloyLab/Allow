package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Err;
import java.io.IOException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Constructs one checked common background and two selected predicate calls. */
final class ComparisonModelsMerge {
    private final ObjectNode left, right, first, second;
    private final Map<String, String> mapping = new HashMap<>();
    private final String prefix = "Cmp" + UUID.randomUUID().toString().replace("-", "");
    private int serial;
    private final Set<String> names = new HashSet<>();
    /** Creates a merger.
     * @param left first checked module
     * @param right second checked module
     * @param a first selection
     * @param b second selection
     */
    ComparisonModelsMerge(ObjectNode left, ObjectNode right, String a, String b) {
        this.left = left; this.right = right;
        first = ComparisonModelsSupport.predicate(left, a); second = ComparisonModelsSupport.predicate(right, b);
        collectNames(left); collectNames(right);
    }
    /** Prepares a checked module.
     * @return checked comparison module
     * @throws Err parser failure
     * @throws IOException temporary file failure
     * @throws IllegalArgumentException incompatible background
     */
    ComparisonModels.Prepared prepare() throws Err, IOException {
        ObjectNode a = ComparisonModelsSupport.background(left, first), b = ComparisonModelsSupport.background(right, second);
        if (!new ModuleEquivalence(a, b).matches()) throw new IllegalArgumentException("background mismatch");
        mapDeclarations(); checkParameters(); ObjectNode correspondence = correspondence();
        copySelected(); String[] arms = wrapper();
        JsonNode parameters = left.path("predicates").get(left.path("predicates").size() - 1).path("parameters");
        for (int i = 0; i < parameters.size(); i++) ((ObjectNode) correspondence.path("parameters").get(i))
            .put("sharedId", parameters.get(i).path("id").asText());
        new ModuleChecker(left).check();
        EngineData.roundTrip(left, new ModulePrinter(left).print());
        return new ComparisonModels.Prepared(left.deepCopy(), arms[0], arms[1], correspondence);
    }
    /** Maps each retained declaration by unique name and category.
     * @throws IllegalArgumentException declaration mismatch
     */
    private void mapDeclarations() {
        for (String key : List.of("signatures", "fields", "predicates", "facts", "assertions")) {
            for (JsonNode r : right.path(key)) {
                if (r == second) continue;
                boolean found = false;
                for (JsonNode l : left.path(key)) if (l != first && l.path("name").equals(r.path("name"))) {
                    mapping.put(r.path("id").asText(), l.path("id").asText()); found = true; break;
                }
                if (!found) throw new IllegalArgumentException("background declaration mismatch");
            }
        }
    }
    /** Checks positional nominal parameter schema correspondence.
     * @throws IllegalArgumentException schema mismatch
     */
    private void checkParameters() {
        JsonNode a = first.path("parameters"), b = second.path("parameters");
        if (a.size() != b.size() || a.size() > 16) throw new IllegalArgumentException("parameter arity mismatch");
        for (int i = 0; i < a.size(); i++) {
            JsonNode x = a.get(i).path("columns"), y = b.get(i).path("columns");
            if (x.size() != y.size()) throw new IllegalArgumentException("parameter schema mismatch");
            for (int j = 0; j < x.size(); j++) if (!x.get(j).asText().equals(mapping.get(y.get(j).asText())))
                throw new IllegalArgumentException("parameter schema mismatch");
        }
    }
    /** Projects correspondence.
     * @return predicate, parameter and declaration correspondence
     */
    private ObjectNode correspondence() {
        ObjectNode out = JsonNodeFactory.instance.objectNode();
        out.put("leftPredicate", first.path("name").asText()).put("rightPredicate", second.path("name").asText());
        ArrayNode pairs = out.putArray("parameters");
        for (int i = 0; i < first.path("parameters").size(); i++) {
            JsonNode a = first.path("parameters").get(i), b = second.path("parameters").get(i);
            ObjectNode pair = pairs.addObject().put("leftName", a.path("name").asText()).put("rightName", b.path("name").asText());
            ArrayNode columns = pair.putArray("columns");
            for (JsonNode col : a.path("columns")) columns.add(ComparisonModelsSupport.name(left, col.asText()));
        }
        ArrayNode shared = out.putArray("declarations");
        for (String key : List.of("signatures", "fields")) for (JsonNode item : left.path(key))
            shared.addObject().put("kind", item.path("tag").asText()).put("name", item.path("name").asText());
        return out;
    }
    /** Copies selected right tree and freshens its local names. */
    private void copySelected() {
        first.put("name", freshName()); ObjectNode copied = second.deepCopy(); copied.put("name", freshName());
        for (JsonNode param : copied.path("parameters")) ((ObjectNode) param).put("name", freshName());
        Set<String> owned = ComparisonModelsSupport.subtree(right, second.path("bodyId").asText());
        ArrayNode nodes = left.withArray("nodes");
        for (JsonNode original : right.path("nodes")) if (owned.contains(original.path("id").asText())) {
            ObjectNode node = original.deepCopy();
            if (node.has("binder")) ((ObjectNode) node.path("binder")).put("name", freshName());
            rewrite(node); nodes.add(node);
        }
        rewrite(copied); left.withArray("predicates").add(copied);
    }
    /** Constructs a wrapper.
     * @return two calls sharing wrapper parameter identities
     */
    private String[] wrapper() {
        ObjectNode pred = left.withArray("predicates").addObject().put("tag", "predicate").put("id", ComparisonModelsSupport.id()).put("name", freshName());
        ArrayNode params = pred.putArray("parameters");
        for (JsonNode original : first.path("parameters")) {
            ObjectNode param = params.addObject().put("tag", "parameter").put("id", ComparisonModelsSupport.id()).put("name", freshName());
            param.set("columns", original.path("columns").deepCopy());
        }
        String a = call(first.path("id").asText(), params), b = call(second.path("id").asText(), params);
        String root = ComparisonModelsSupport.id(); pred.put("bodyId", root);
        left.withArray("nodes").addObject().put("tag", "and").put("id", root).put("leftId", a).put("rightId", b);
        return new String[]{a, b};
    }
    /** Constructs a call.
     * @param target selected predicate
     * @param params shared parameter definitions
     * @return call identity
     */
    private String call(String target, ArrayNode params) {
        ArrayNode nodes = left.withArray("nodes"); String id = ComparisonModelsSupport.id();
        ObjectNode call = nodes.addObject().put("tag", "predicate_call").put("id", id).put("predicateId", target);
        ArrayNode args = call.putArray("arguments");
        for (JsonNode param : params) { String arg = ComparisonModelsSupport.id(); args.add(arg);
            nodes.addObject().put("tag", "variable_ref").put("id", arg).put("targetId", param.path("id").asText()); }
        return id;
    }
    /** Rewrites declaration references.
     * @param node isolated copied JSON subtree
     */
    private void rewrite(JsonNode node) {
        if (node.isObject()) { ObjectNode object = (ObjectNode) node; Iterator<Map.Entry<String, JsonNode>> fields = object.fields();
            while (fields.hasNext()) { Map.Entry<String, JsonNode> e = fields.next(); JsonNode value = e.getValue();
                if (value.isTextual() && mapping.containsKey(value.asText())) object.put(e.getKey(), mapping.get(value.asText())); else rewrite(value); }
        } else if (node.isArray()) { ArrayNode array = (ArrayNode) node;
            for (int i = 0; i < array.size(); i++) { JsonNode value = array.get(i);
                if (value.isTextual() && mapping.containsKey(value.asText())) array.set(i, JsonNodeFactory.instance.textNode(mapping.get(value.asText()))); else rewrite(value); }
        }
    }
    /** Collects existing names to prevent collisions.
     * @param module checked source module
     */
    private void collectNames(JsonNode module) {
        for (String key : List.of("signatures", "fields", "predicates", "facts", "assertions"))
            for (JsonNode item : module.path(key)) {
                names.add(item.path("name").asText());
                for (JsonNode param : item.path("parameters")) names.add(param.path("name").asText());
            }
        for (JsonNode node : module.path("nodes")) if (node.has("binder")) names.add(node.path("binder").path("name").asText());
    }
    /** Allocates a generated name.
     * @return collision-resistant valid name
     */
    private String freshName() {
        String name;
        do { name = prefix + serial++; } while (!names.add(name));
        return name;
    }
}
