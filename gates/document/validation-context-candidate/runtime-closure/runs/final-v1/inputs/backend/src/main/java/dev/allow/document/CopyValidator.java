package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/** Validates explicit expression-comment transfer requests against the exact base. */
final class CopyValidator {
    private final JsonNode base;
    private final JsonNode candidate;
    private final Map<String, JsonNode> oldNodes = new HashMap<>();
    private final Map<String, JsonNode> newNodes = new HashMap<>();
    private final Set<String> destinations = new HashSet<>();

    /**
     * Creates a copy validator for two checked module snapshots.
     * @param base exact authorized base artifact
     * @param candidate checked candidate module before ID remapping
     */
    CopyValidator(JsonNode base, JsonNode candidate) {
        this.base = base;
        this.candidate = candidate;
    }

    /**
     * Validates the closed bounded copy map.
     * @param copies copy entries
     * @throws IllegalArgumentException for invalid or unauthorized mappings
     */
    void check(JsonNode copies) {
        if (!copies.isArray() || copies.size() > 512) throw new IllegalArgumentException("copy array");
        for (JsonNode node : base.path("module").path("nodes")) oldNodes.put(node.path("id").asText(), node);
        for (JsonNode node : candidate.path("nodes")) newNodes.put(node.path("id").asText(), node);
        if (!copies.isEmpty() && !base.path("mode").asText().equals("BLOCK_SUPPORTED")) {
            throw new IllegalArgumentException("copy base mode");
        }
        for (JsonNode copy : copies) entry(copy);
    }

    /**
     * Checks source, fresh destination, role compatibility and uniqueness.
     * @param copy closed copy entry
     * @throws IllegalArgumentException for an invalid entry
     */
    private void entry(JsonNode copy) {
        if (!copy.isObject() || copy.size() != 2 || !copy.path("sourceNodeId").isTextual()
                || !copy.path("targetNodeId").isTextual()) throw new IllegalArgumentException("copy shape");
        String source = copy.path("sourceNodeId").textValue();
        String target = copy.path("targetNodeId").textValue();
        JsonNode old = oldNodes.get(source);
        JsonNode next = newNodes.get(target);
        if (!source.startsWith("server:") || !target.startsWith("draft:") || old == null || next == null
                || !destinations.add(target) || !old.path("tag").equals(next.path("tag"))) {
            throw new IllegalArgumentException("copy identity or role");
        }
    }
}
