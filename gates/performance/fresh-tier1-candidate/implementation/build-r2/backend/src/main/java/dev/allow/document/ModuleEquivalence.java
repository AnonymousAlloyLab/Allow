package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Compares checked modules modulo IDs and ordered associative boolean grouping. */
final class ModuleEquivalence {
    private final Side left;
    private final Side right;

    /**
     * Creates an equivalence comparison over two checked modules.
     * @param left first checked module
     * @param right second checked module
     */
    ModuleEquivalence(JsonNode left, JsonNode right) {
        this.left = new Side(left);
        this.right = new Side(right);
    }

    /**
     * Compares declarations, bodies and command order.
     * @return whether the modules are equivalent
     */
    boolean matches() {
        return declarations("signatures") && declarations("fields") && declarations("predicates")
            && declarations("facts") && declarations("assertions") && declarations("commands");
    }

    /**
     * Compares one ordered declaration category.
     * @param category module collection key
     * @return whether the collection matches
     */
    private boolean declarations(String category) {
        JsonNode l = left.module.path(category);
        JsonNode r = right.module.path(category);
        if (l.size() != r.size()) return false;
        for (int i = 0; i < l.size(); i++) if (!declaration(l.get(i), r.get(i))) return false;
        return true;
    }

    /**
     * Compares one declaration's closed data and body.
     * @param a first declaration
     * @param b second declaration
     * @return whether equivalent
     */
    private boolean declaration(JsonNode a, JsonNode b) {
        if (!a.path("tag").equals(b.path("tag")) || !a.path("name").equals(b.path("name"))) return false;
        if (!a.path("multiplicity").equals(b.path("multiplicity"))) return false;
        if (!sameRef(a, b, "ownerSignatureId") || !sameRef(a, b, "targetId")) return false;
        if (!sameArray(a.path("rangeColumns"), b.path("rangeColumns"))) return false;
        if (!a.path("uniformScope").equals(b.path("uniformScope")) || !a.path("bitwidth").equals(b.path("bitwidth"))
                || !a.path("maxseq").equals(b.path("maxseq"))) return false;
        if (!parameters(a.path("parameters"), b.path("parameters"))) return false;
        if (a.has("bodyId") != b.has("bodyId")) return false;
        return !a.has("bodyId") || expression(a.path("bodyId").textValue(), b.path("bodyId").textValue());
    }

    /**
     * Compares ordered parameter names and schemas.
     * @param a first parameter array
     * @param b second parameter array
     * @return whether equivalent
     */
    private boolean parameters(JsonNode a, JsonNode b) {
        if (a.isMissingNode() || b.isMissingNode()) return a.isMissingNode() && b.isMissingNode();
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) {
            if (!a.get(i).path("name").equals(b.get(i).path("name"))
                    || !sameArray(a.get(i).path("columns"), b.get(i).path("columns"))) return false;
        }
        return true;
    }

    /**
     * Compares referenced declared names in an optional field.
     * @param a first object
     * @param b second object
     * @param field reference field
     * @return whether both absent or resolving to the same name
     */
    private boolean sameRef(JsonNode a, JsonNode b, String field) {
        if (a.has(field) != b.has(field)) return false;
        return !a.has(field) || left.name(a.path(field).textValue()).equals(right.name(b.path(field).textValue()));
    }

    /**
     * Compares ordered arrays of signature references.
     * @param a first schema
     * @param b second schema
     * @return whether corresponding signature names match
     */
    private boolean sameArray(JsonNode a, JsonNode b) {
        if (a.isMissingNode() || b.isMissingNode()) return a.isMissingNode() && b.isMissingNode();
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) if (!left.name(a.get(i).textValue()).equals(right.name(b.get(i).textValue()))) return false;
        return true;
    }

    /**
     * Compares one expression pair recursively.
     * @param leftId first expression ID
     * @param rightId second expression ID
     * @return whether equivalent
     */
    private boolean expression(String leftId, String rightId) {
        JsonNode a = left.nodes.get(leftId);
        JsonNode b = right.nodes.get(rightId);
        String tag = a.path("tag").textValue();
        if (!tag.equals(b.path("tag").textValue())) return false;
        if (tag.equals("and") || tag.equals("or")) return associative(tag, leftId, rightId);
        if (!sameRef(a, b, "targetId") || !sameRef(a, b, "predicateId")) return false;
        if (!binder(a.path("binder"), b.path("binder"))) return false;
        for (String field : List.of("operandId", "leftId", "rightId", "bodyId")) {
            if (a.has(field) != b.has(field)) return false;
            if (a.has(field) && !expression(a.path(field).textValue(), b.path(field).textValue())) return false;
        }
        JsonNode argsA = a.path("arguments");
        JsonNode argsB = b.path("arguments");
        if (argsA.size() != argsB.size()) return false;
        for (int i = 0; i < argsA.size(); i++) if (!expression(argsA.get(i).textValue(), argsB.get(i).textValue())) return false;
        return true;
    }

    /**
     * Compares a quantifier binder by name and nominal domain.
     * @param a first binder
     * @param b second binder
     * @return whether equivalent
     */
    private boolean binder(JsonNode a, JsonNode b) {
        if (a.isMissingNode() || b.isMissingNode()) return a.isMissingNode() && b.isMissingNode();
        return a.path("name").equals(b.path("name")) && sameRef(a, b, "signatureId");
    }

    /**
     * Compares ordered operands after associative flattening.
     * @param tag shared boolean tag
     * @param leftId first root
     * @param rightId second root
     * @return whether flattened operands match
     */
    private boolean associative(String tag, String leftId, String rightId) {
        List<String> a = new ArrayList<>();
        List<String> b = new ArrayList<>();
        left.flatten(tag, leftId, a);
        right.flatten(tag, rightId, b);
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) if (!expression(a.get(i), b.get(i))) return false;
        return true;
    }

    /** Immutable indices local to one checked module. */
    private static final class Side {
        private final JsonNode module;
        private final Map<String, String> names = new HashMap<>();
        private final Map<String, JsonNode> nodes = new HashMap<>();

        /**
         * Builds stable name and node indices.
         * @param module checked module
         */
        private Side(JsonNode module) {
            this.module = module;
            index();
        }

        /** Indexes all declarations, parameters, quantifier binders and nodes. */
        private void index() {
            for (String key : List.of("signatures", "fields", "predicates", "facts", "assertions")) {
                for (JsonNode item : module.path(key)) named(item);
            }
            for (JsonNode predicate : module.path("predicates")) {
                for (JsonNode parameter : predicate.path("parameters")) named(parameter);
            }
            for (JsonNode node : module.path("nodes")) {
                nodes.put(node.path("id").textValue(), node);
                if (node.has("binder")) named(node.path("binder"));
            }
        }

        /**
         * Records a uniquely named declaration or binder.
         * @param n named object
         */
        private void named(JsonNode n) {
            names.put(n.path("id").textValue(), n.path("name").textValue());
        }

        /**
         * Resolves one checked declaration identity.
         * @param id stable identity
         * @return globally unique name
         */
        private String name(String id) {
            return names.get(id);
        }

        /**
         * Flattens consecutive same-tag boolean nodes in traversal order.
         * @param tag boolean tag
         * @param id current node ID
         * @param result flattened IDs
         */
        private void flatten(String tag, String id, List<String> result) {
            JsonNode n = nodes.get(id);
            if (!tag.equals(n.path("tag").textValue())) result.add(id);
            else {
                flatten(tag, n.path("leftId").textValue(), result);
                flatten(tag, n.path("rightId").textValue(), result);
            }
        }
    }
}
