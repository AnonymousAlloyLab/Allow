package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.*;

/** Identity-based capture of two checked formulas and their joint free environment. */
final class ComparisonSyntax {
    private final JsonNode module;
    private final Map<String, JsonNode> nodes = new LinkedHashMap<>();
    private final Map<String, JsonNode> binders = new LinkedHashMap<>();
    private final Map<String, String> signatures = new LinkedHashMap<>();
    private final Map<String, String> renamed = new LinkedHashMap<>();
    private final LinkedHashSet<String> free = new LinkedHashSet<>();
    private final String prefix;

    /** Indexes a checked independent forest and chooses a collision-free namespace.
     * @param input complete checked module
     */
    ComparisonSyntax(JsonNode input) {
        module = input.deepCopy();
        prefix = namespace(input);
        for (JsonNode sig : module.path("signatures")) signatures.put(sig.path("id").asText(), sig.path("name").asText());
        for (JsonNode pred : module.path("predicates")) for (JsonNode param : pred.path("parameters")) binder(param);
        for (JsonNode node : module.path("nodes")) {
            nodes.put(node.path("id").asText(), node);
            if (node.has("binder")) binder(node.path("binder"));
        }
        ((ObjectNode) module).putArray("commands");
    }

    /** Renames every lexical binder by identity to avoid capture and shadowing.
     * @param binder independently checked binder declaration
     */
    private void binder(JsonNode binder) {
        String id = binder.path("id").asText();
        binders.put(id, binder.deepCopy());
        String name = prefix + "V" + renamed.size();
        renamed.put(id, name);
        ((ObjectNode) binder).put("name", prefix + "Background" + (renamed.size() - 1));
    }

    /** Chooses fresh generated names against every authored name, including lexical binders.
     * @param input complete module
     * @return unused prefix
     */
    private static String namespace(JsonNode input) {
        Set<String> names = new HashSet<>();
        ArrayDeque<JsonNode> pending = new ArrayDeque<>();
        pending.add(input);
        while (!pending.isEmpty()) {
            JsonNode node = pending.removeLast();
            if (node.has("name")) names.add(node.path("name").asText());
            for (JsonNode child : node) pending.add(child);
        }
        String prefix = "allowComparison";
        while (conflicts(names, prefix)) prefix += "X";
        return prefix;
    }

    /** Tests prefix collisions without conflating authored declaration identities.
     * @param names all authored names
     * @param prefix proposed generated prefix
     * @return whether a collision exists
     */
    private static boolean conflicts(Set<String> names, String prefix) {
        for (String name : names) if (name.startsWith(prefix)) return true;
        return false;
    }

    /** Captures the joint free variables of one formula arm.
     * @param id live selected formula
     * @throws IllegalArgumentException nonformula or free variable limit
     */
    void arm(String id) {
        JsonNode root = nodes.get(id);
        if (root == null || !formula(root.path("tag").asText())) throw new IllegalArgumentException("Select a live formula");
        Set<String> internal = new HashSet<>();
        Set<String> references = new LinkedHashSet<>();
        ArrayDeque<String> pending = new ArrayDeque<>();
        pending.add(id);
        while (!pending.isEmpty()) {
            JsonNode node = nodes.get(pending.removeLast());
            if (node.has("binder")) internal.add(node.path("binder").path("id").asText());
            if (node.path("tag").asText().equals("variable_ref")) references.add(node.path("targetId").asText());
            for (String key : new String[]{"leftId", "rightId", "operandId", "bodyId"}) if (node.has(key)) pending.add(node.path(key).asText());
            for (JsonNode arg : node.path("arguments")) pending.add(arg.asText());
        }
        references.removeAll(internal);
        free.addAll(references);
        if (free.size() > 32) throw new IllegalArgumentException("Free-variable limit");
    }

    /** Identifies the closed formula operator family.
     * @param tag checked expression tag
     * @return whether the root denotes a formula
     */
    private static boolean formula(String tag) {
        return Set.of("predicate_call", "all_quant", "some_quant", "not", "and", "or", "implies", "iff",
                "equal", "subset", "some_test", "no_test", "one_test", "lone_test").contains(tag);
    }

    /** Builds the common complete source with two pure helper predicates and four categories.
     * @param left first selected formula
     * @param right second selected formula
     * @param scope common uniform scope
     * @return generated source
     */
    String source(String left, String right, int scope) {
        arm(left); arm(right);
        ModulePrinter printer = new ModulePrinter(module);
        StringBuilder out = new StringBuilder(printer.print());
        String parameters = declarations(false);
        out.append("pred ").append(prefix).append("Left[").append(parameters).append("] { ").append(selected(left, "Left")).append(" }\n");
        out.append("pred ").append(prefix).append("Right[").append(parameters).append("] { ").append(selected(right, "Right")).append(" }\n");
        String args = String.join(",", variableNames());
        String l = prefix + "Left[" + args + "]", r = prefix + "Right[" + args + "]";
        for (int category = 0; category < 4; category++) {
            String body = (category >= 2 ? "not " : "") + l + " and " + (category == 1 || category == 3 ? "not " : "") + r;
            if (!free.isEmpty()) body = "some " + declarations(true) + " | " + body;
            out.append("pred ").append(prefix).append("Category").append(category).append(" { ").append(body).append(" }\n");
            out.append("run ").append(prefix).append("Category").append(category).append(" for ").append(scope).append(" but 4 Int, 3 seq\n");
        }
        return out.toString();
    }

    /** Gives helper-local internal binders names distinct from every shared free parameter.
     * @param id selected helper body root
     * @param side collision-free helper side
     * @return identity-rendered expression with lexical shadowing eliminated
     */
    private String selected(String id, String side) {
        JsonNode copy = module.deepCopy();
        Map<String, JsonNode> indexed = new HashMap<>();
        for (JsonNode pred : copy.path("predicates")) for (JsonNode param : pred.path("parameters")) freeName(param);
        for (JsonNode node : copy.path("nodes")) {
            indexed.put(node.path("id").asText(), node);
            if (node.has("binder")) freeName(node.path("binder"));
        }
        ArrayDeque<String> pending = new ArrayDeque<>();
        pending.add(id);
        int count = 0;
        while (!pending.isEmpty()) {
            JsonNode node = indexed.get(pending.removeLast());
            if (node.has("binder")) ((ObjectNode) node.path("binder")).put("name", prefix + side + "Bound" + count++);
            for (String key : new String[]{"leftId", "rightId", "operandId", "bodyId"}) if (node.has(key)) pending.add(node.path(key).asText());
            for (JsonNode arg : node.path("arguments")) pending.add(arg.asText());
        }
        return new ModulePrinter(copy).selected(id);
    }

    /** Assigns helper parameter names only to free lexical identities in a helper copy.
     * @param binder copied lexical declaration
     */
    private void freeName(JsonNode binder) {
        String id = binder.path("id").asText();
        if (free.contains(id)) ((ObjectNode) binder).put("name", renamed.get(id));
    }

    /** Renders explicit set-valued parameters or original-multiplicity existential variables.
     * @param existential whether singleton original quantifier domains must be retained
     * @return ordered declaration list
     * @throws IllegalArgumentException unbound comparison variable
     */
    private String declarations(boolean existential) {
        List<String> result = new ArrayList<>();
        for (String id : free) {
            JsonNode binder = binders.get(id);
            if (binder == null) throw new IllegalArgumentException("Unbound comparison variable");
            boolean atom = binder.has("signatureId");
            List<String> columns = columns(id);
            String mult = existential && atom ? "one" : "set";
            result.add(renamed.get(id) + ": " + mult + " (" + String.join(" -> ", columns) + ")");
        }
        return String.join(", ", result);
    }

    /** Returns schema names in their original ordered product positions.
     * @param id binder identity
     * @return original signature names
     */
    List<String> columns(String id) {
        JsonNode binder = binders.get(id);
        List<String> result = new ArrayList<>();
        if (binder.has("signatureId")) result.add(signatures.get(binder.path("signatureId").asText()));
        else for (JsonNode column : binder.path("columns")) result.add(signatures.get(column.asText()));
        return result;
    }

    /** Returns stable generated names for positional solver replay.
     * @return ordered free variable names
     */
    List<String> variableNames() {
        List<String> result = new ArrayList<>();
        for (String id : free) result.add(renamed.get(id));
        return result;
    }

    /** Returns original binder identities in joint declaration order.
     * @return immutable free variable identities
     */
    List<String> variables() { return List.copyOf(free); }

    /** Returns one original lexical display name.
     * @param id original binder identity
     * @return authored name
     */
    String name(String id) { return binders.get(id).path("name").asText(); }

    /** Returns the collision-free helper function namespace.
     * @return generated prefix
     */
    String prefix() { return prefix; }
}
