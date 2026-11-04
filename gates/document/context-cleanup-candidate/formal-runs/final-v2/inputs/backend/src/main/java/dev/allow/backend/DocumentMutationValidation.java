package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.LinkedHashSet;
import java.util.Set;

/** Resolves only authorized immutable context before isolated whole-document validation. */
final class DocumentMutationValidation {
    /** Prevents construction of the context resolver. */
    private DocumentMutationValidation() {}

    /** Reads one immutable authorized revision with head and artifact provenance.
     * @param gateway private store bridge
     * @param document authorized document identity
     * @param revision selected history revision or null for current head
     * @return authorized read envelope
     * @throws IOException missing or malformed stored context
     * @throws InterruptedException interrupted read after child reaping
     */
    static JsonNode read(DocumentGateway gateway, String document, JsonNode revision)
            throws IOException, InterruptedException {
        var args = JsonNodeFactory.instance.objectNode().put("documentId", document);
        args.set("revision", revision == null ? JsonNodeFactory.instance.nullNode() : revision.deepCopy());
        JsonNode data = DocumentMutationFrames.data(gateway.request("read", args));
        DocumentJson.revision(data, "headRevision");
        DocumentJson.revision(data, "requestedRevision");
        if (!data.path("artifact").isObject()) throw new IOException("Missing accepted artifact");
        return data;
    }

    /** Collects only submitted existing server identifiers for bounded history ownership lookup.
     * @param gateway private scope-bound persistence bridge
     * @param document authorized document identity
     * @param candidate complete candidate or historical module
     * @return existing ID-to-kind inventory, without unrelated history
     * @throws IOException invalid or oversized inventory
     * @throws InterruptedException interrupted lookup after reaping
     */
    static JsonNode inventory(DocumentGateway gateway, String document, JsonNode candidate)
            throws IOException, InterruptedException {
        Set<String> ids = identifiers(candidate);
        var args = JsonNodeFactory.instance.objectNode().put("documentId", document);
        var requested = args.putArray("ids");
        ids.forEach(requested::add);
        JsonNode data = DocumentMutationFrames.data(gateway.request("ownedIds", args));
        if (!data.path("ids").isObject()) throw new IOException("Invalid ownership inventory");
        return data.get("ids").deepCopy();
    }

    /** Traverses the bounded candidate without inferring authority from display labels.
     * @param candidate already request-bounded candidate
     * @return distinct server identifiers occurring in submitted content
     * @throws IOException inventory cardinality exceeds the private protocol
     */
    private static Set<String> identifiers(JsonNode candidate) throws IOException {
        Set<String> ids = new LinkedHashSet<>();
        ArrayDeque<JsonNode> pending = new ArrayDeque<>();
        pending.add(candidate);
        while (!pending.isEmpty()) {
            JsonNode value = pending.removeFirst();
            if (value.isTextual() && value.textValue().matches("server:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) {
                ids.add(value.textValue());
                if (ids.size() > 4096) throw new IOException("Ownership inventory exceeds limit");
            }
            if (value.isContainerNode()) value.forEach(pending::addLast);
        }
        return ids;
    }

    /** Rejects malformed worker schemas as availability, never fabricated deterministic errors.
     * @param envelope isolated worker response
     * @return exact checked worker payload
     * @throws IOException incomplete or unsupported result
     */
    static JsonNode checked(JsonNode envelope) throws IOException {
        JsonNode data = envelope.path("data");
        try {
            if (envelope.path("status").asText().equals("INVALID")) {
                DocumentJson.fields(data, "code", "diagnostics");
                if (!Set.of("INVALID_DRAFT", "TYPE_MISMATCH", "UNBOUND_SYMBOL", "UNSUPPORTED_FRAGMENT",
                        "INVALID_UNDO_TARGET").contains(data.path("code").asText())) throw new IOException("Invalid rejection code");
            } else if (envelope.path("status").asText().equals("VALIDATED")) {
                DocumentJson.fields(data, "mode", "source", "sourceHash", "module", "occurrences", "trivia",
                        "analysisDescriptors", "diagnostics", "idRemapping");
                if (!data.path("idRemapping").isObject()) throw new IOException("Missing ID remapping");
            } else throw new IOException("Document validator unavailable");
            if (!data.path("diagnostics").isArray() || data.path("diagnostics").size() > 64
                    || dev.allow.worker.JsonWire.encode(data.get("diagnostics")).length > 32768) throw new IOException("Invalid diagnostics");
            return data;
        } catch (IllegalArgumentException failure) {
            throw new IOException("Invalid worker payload", failure);
        }
    }
}
