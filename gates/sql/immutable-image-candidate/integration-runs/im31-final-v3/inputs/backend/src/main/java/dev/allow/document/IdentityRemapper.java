package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Resolves client draft identities against server-provided history inventory. */
final class IdentityRemapper {
    private final Map<String, String> assigned = new LinkedHashMap<>();
    private final JsonNode inventory;

    /**
     * Creates a remapper against a trusted, bounded identity inventory.
     * @param inventory server identity-to-kind object
     * @throws IllegalArgumentException if inventory is not an object
     */
    IdentityRemapper(JsonNode inventory) {
        if (!inventory.isObject()) throw new IllegalArgumentException("identity inventory");
        this.inventory = inventory;
    }

    /**
     * Produces a remapped independent module after checking every definition.
     * @param module checked draft module
     * @return remapped module copy
     */
    JsonNode remap(JsonNode module) {
        collect(module);
        JsonNode result = module.deepCopy();
        rewrite(result);
        return result;
    }

    /**
     * Returns the stable mapping generated during the most recent remap.
     * @return immutable original-to-server ID map
     */
    Map<String, String> mappings() {
        return Map.copyOf(assigned);
    }

    /**
     * Collects definitions across the closed module.
     * @param module checked module
     */
    private void collect(JsonNode module) {
        for (String key : new String[]{"signatures", "fields", "predicates", "facts", "assertions", "commands", "nodes"}) {
            for (JsonNode node : module.path(key)) {
                definition(node, kind(key));
                if (key.equals("predicates")) for (JsonNode param : node.path("parameters")) definition(param, "binder");
                if (key.equals("nodes") && node.has("binder")) definition(node.path("binder"), "binder");
            }
        }
    }

    /**
     * Validates ownership or allocates a fresh identity.
     * @param node definition
     * @param kind stable identity kind
     * @throws IllegalArgumentException if identity is not owned
     */
    private void definition(JsonNode node, String kind) {
        String id = node.path("id").textValue();
        if (id.startsWith("draft:")) assigned.put(id, fresh());
        else if (!kind.equals(inventory.path(id).textValue())) throw new IllegalArgumentException("foreign identity");
    }

    /**
     * Allocates an ID distinct from the trusted subset and prior assignments.
     * @return fresh server identity
     */
    private String fresh() {
        String id;
        do {
            id = "server:" + UUID.randomUUID();
        } while (inventory.has(id) || assigned.containsValue(id));
        return id;
    }

    /**
     * Maps the wire collection to its identity category.
     * @param key module collection
     * @return stable identity kind
     */
    private String kind(String key) {
        return switch (key) {
            case "signatures" -> "signature";
            case "fields" -> "field";
            case "predicates" -> "predicate";
            case "facts" -> "fact";
            case "assertions" -> "assertion";
            case "commands" -> "command";
            default -> "expression";
        };
    }

    /**
     * Rewrites all textual identity references in the isolated copy.
     * @param node object or array to traverse
     */
    private void rewrite(JsonNode node) {
        if (node.isObject()) rewriteObject((ObjectNode) node);
        else if (node.isArray()) rewriteArray((ArrayNode) node);
    }

    /**
     * Rewrites textual values in an object.
     * @param node copied object
     */
    private void rewriteObject(ObjectNode node) {
        Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            JsonNode value = entry.getValue();
            if (value.isTextual() && assigned.containsKey(value.textValue())) node.put(entry.getKey(), assigned.get(value.textValue()));
            else rewrite(value);
        }
    }

    /**
     * Rewrites textual values in an array.
     * @param node copied array
     */
    private void rewriteArray(ArrayNode node) {
        for (int index = 0; index < node.size(); index++) {
            JsonNode value = node.get(index);
            if (value.isTextual() && assigned.containsKey(value.textValue())) node.set(index, node.textNode(assigned.get(value.textValue())));
            else rewrite(value);
        }
    }
}
