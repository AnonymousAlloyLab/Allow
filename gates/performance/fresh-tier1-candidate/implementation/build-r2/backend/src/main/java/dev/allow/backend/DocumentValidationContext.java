package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;

/** Exact authorized base and requested historical IDs from one private SQL snapshot. */
final class DocumentValidationContext {
    private static final Set<String> KINDS = Set.of("signature", "field", "predicate", "fact",
            "assertion", "command", "binder", "expression");
    private final JsonNode artifact;
    private final JsonNode inventory;

    /** Retains defensive copies without exposing mutable bridge response objects.
     * @param artifact exact immutable base content
     * @param inventory requested scoped historical ID kinds
     */
    private DocumentValidationContext(JsonNode artifact, JsonNode inventory) {
        this.artifact = artifact.deepCopy();
        this.inventory = inventory.deepCopy();
    }

    /** Reads one authorized context, including when the candidate has no server IDs.
     * @param gateway one-shot private persistence bridge
     * @param document canonical route document
     * @param revision exact requested base
     * @param module submitted module, or a missing/null node for source mode
     * @return complete checked context after bridge exit
     * @throws IOException malformed context or unavailable persistence
     * @throws InterruptedException interruption after bridge reaping
     */
    static DocumentValidationContext read(DocumentGateway gateway, String document, long revision,
            JsonNode module) throws IOException, InterruptedException {
        Set<String> wanted = identifiers(module);
        ObjectNode args = arguments(document, revision, wanted);
        JsonNode envelope;
        try {
            envelope = gateway.request("validationContext", args);
        } catch (IllegalArgumentException failure) {
            throw new IOException("Malformed validation context envelope", failure);
        }
        if (!envelope.path("status").asText().equals("OK")) throw new IOException("Validation context unavailable");
        return checked(envelope.path("data"), document, revision, wanted);
    }

    /** Builds bounded sorted arguments without accepting browser-supplied authority.
     * @param document canonical route document
     * @param revision exact safe base revision
     * @param wanted sorted unique requested IDs
     * @return closed private arguments
     * @throws IOException invalid identity, revision or encoded argument size
     */
    private static ObjectNode arguments(String document, long revision, Set<String> wanted) throws IOException {
        identifier(document);
        if (revision < 0 || revision > 9007199254740991L) throw new IOException("Invalid context revision");
        ObjectNode args = JsonNodeFactory.instance.objectNode().put("documentId", document).put("revision", revision);
        ArrayNode ids = args.putArray("ids");
        for (String id : wanted) ids.add(id);
        if (JsonWire.encode(args).length > 262144) throw new IOException("Context arguments exceed limit");
        return args;
    }

    /** Preserves the existing module-value traversal while bounding distinct server IDs.
     * @param module candidate module, absent for source mode
     * @return lexicographically sorted distinct canonical server IDs
     * @throws IOException malformed server ID or inventory overflow
     */
    private static Set<String> identifiers(JsonNode module) throws IOException {
        Set<String> ids = new TreeSet<>();
        ArrayDeque<JsonNode> pending = new ArrayDeque<>();
        if (module != null) pending.add(module);
        while (!pending.isEmpty()) {
            JsonNode value = pending.removeLast();
            if (value.isTextual() && value.textValue().startsWith("server:")) {
                identifier(value.textValue());
                ids.add(value.textValue());
                if (ids.size() > 4096) throw new IOException("Identity inventory exceeds limit");
            }
            for (JsonNode child : value) pending.add(child);
        }
        return ids;
    }

    /** Rejects noncanonical identifiers before launching a private bridge.
     * @param value opaque server identifier
     * @throws IOException malformed or noncanonical identifier
     */
    private static void identifier(String value) throws IOException {
        try {
            if (value == null || !value.startsWith("server:")
                    || !value.equals("server:" + UUID.fromString(value.substring(7)))) {
                throw new IllegalArgumentException("Invalid server identifier");
            }
        } catch (IllegalArgumentException failure) {
            throw new IOException("Invalid context identifier", failure);
        }
    }

    /** Rejects substituted, oversized or structurally incomplete private results.
     * @param data closed context response
     * @param document exact requested document
     * @param revision exact requested base
     * @param wanted exact requested ID set
     * @return defensive checked context, without assigning semantic parser authority
     * @throws IOException malformed private response
     */
    private static DocumentValidationContext checked(JsonNode data, String document, long revision,
            Set<String> wanted) throws IOException {
        try {
            DocumentJson.fields(data, "documentId", "baseRevision", "headObserved", "artifact", "ownedIdInventory");
            if (!data.path("documentId").isTextual() || !document.equals(data.path("documentId").textValue())
                    || DocumentJson.revision(data, "baseRevision") != revision
                    || DocumentJson.revision(data, "headObserved") < revision) {
                throw new IOException("Validation context identity mismatch");
            }
            JsonNode artifact = data.path("artifact");
            DocumentJson.fields(artifact, "artifactId", "mode", "source", "sourceHash", "module", "occurrences",
                    "trivia", "analysisDescriptors", "policyVersion", "dependencyHash");
            if (JsonWire.encode(artifact).length > 1048576) throw new IOException("Context artifact exceeds limit");
            JsonNode inventory = data.path("ownedIdInventory");
            checkInventory(inventory, wanted);
            return new DocumentValidationContext(artifact, inventory);
        } catch (IllegalArgumentException failure) {
            throw new IOException("Malformed validation context", failure);
        }
    }

    /** Checks the returned subset and closed ID kinds without inventing missing ownership.
     * @param inventory private scoped definition map
     * @param wanted exact requested IDs
     * @throws IOException unknown key, kind or map shape
     */
    private static void checkInventory(JsonNode inventory, Set<String> wanted) throws IOException {
        if (!inventory.isObject()) throw new IOException("Identity inventory unavailable");
        var entries = inventory.fields();
        while (entries.hasNext()) {
            var entry = entries.next();
            if (!wanted.contains(entry.getKey()) || !entry.getValue().isTextual()
                    || !KINDS.contains(entry.getValue().textValue())) {
                throw new IOException("Invalid context inventory");
            }
        }
    }

    /** Supplies the exact base without exposing retained mutable state.
     * @return defensive base artifact copy
     */
    JsonNode artifact() { return artifact.deepCopy(); }

    /** Supplies historical ownership without exposing retained mutable state.
     * @return defensive requested-ID inventory copy
     */
    JsonNode inventory() { return inventory.deepCopy(); }
}
