package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.Hashes;

/** Exact saved command authority and transient current-parser correspondence. */
final class SavedAnalysis {
    /** Prevents construction of the selection helper. */
    private SavedAnalysis() {}

    /** Resolves only a descriptor bound to the exact stored artifact and requested source.
     * @param artifact authorized immutable stored artifact
     * @param request closed browser selection
     * @return uniquely bound stored command
     * @throws IllegalArgumentException invalid source or command selection
     */
    static JsonNode command(JsonNode artifact, JsonNode request) {
        if (!request.path("exactSourceHash").isTextual() || !request.path("commandKey").isTextual()
                || !artifact.path("source").isTextual()
                || !Hashes.text(artifact.path("source").textValue()).equals(artifact.path("sourceHash").asText())
                || !artifact.path("sourceHash").equals(request.path("exactSourceHash"))) {
            throw new IllegalArgumentException("Saved source selection mismatch");
        }
        JsonNode selected = null;
        int index = 0;
        for (JsonNode command : artifact.path("analysisDescriptors")) {
            if (command.path("commandKey").equals(request.path("commandKey"))
                    && command.path("artifactId").equals(artifact.path("artifactId"))
                    && command.path("sourceHash").equals(artifact.path("sourceHash"))
                    && command.path("policyVersion").equals(artifact.path("policyVersion"))
                    && command.path("index").isInt() && command.path("index").intValue() == index) {
                if (selected != null) throw new IllegalArgumentException("Ambiguous saved command");
                selected = command;
            }
            index++;
        }
        if (selected == null) throw new IllegalArgumentException("Unknown saved command");
        return selected;
    }

    /** Checks the same exact source and selected occurrence, without command substitution.
     * @param artifact authorized saved content
     * @param selected bound stored command
     * @param checked current-parser validated content
     * @return whether exact source and selected command are unchanged
     */
    static boolean matches(JsonNode artifact, JsonNode selected, JsonNode checked) {
        if (!artifact.path("source").equals(checked.path("source"))
                || !artifact.path("sourceHash").equals(checked.path("sourceHash"))) return false;
        JsonNode commands = checked.path("analysisDescriptors");
        int index = selected.path("index").intValue();
        if (!commands.isArray() || index < 0 || index >= commands.size()) return false;
        JsonNode fresh = commands.get(index);
        for (String field : new String[]{"index", "kind", "label", "options"}) {
            if (!selected.has(field) || !selected.path(field).equals(fresh.path(field))) return false;
        }
        return true;
    }
}
