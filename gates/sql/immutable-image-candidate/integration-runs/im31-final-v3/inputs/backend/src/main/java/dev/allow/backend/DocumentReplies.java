package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.Base64;
import java.util.UUID;

/** Bounded exact HTTP envelopes and unchanged receipt recovery. */
final class DocumentReplies {
    /** Prevents construction of the response encoder. */
    private DocumentReplies() {}

    /** Serializes a new envelope without changing persisted receipt bytes.
     * @param requestId original response identity
     * @param status closed operation status
     * @param data bounded response payload
     * @return complete UTF-8 JSON response
     * @throws IOException response exceeds the complete serialized limit
     */
    static byte[] encode(String requestId, String status, JsonNode data) throws IOException {
        byte[] bytes = JsonWire.encode(DocumentJson.envelope(requestId, status, data));
        if (bytes.length > 1048576) throw new IOException("Document response exceeds limit");
        return bytes;
    }

    /** Creates a content-free availability or protocol error envelope.
     * @param status truthful failure category
     * @return bounded serialized response
     * @throws IOException serialization failure
     */
    static byte[] status(String status) throws IOException {
        return encode(UUID.randomUUID().toString(), status, JsonNodeFactory.instance.objectNode());
    }

    /** Recovers stored exact original bytes after a validated private bridge response.
     * @param data internal receipt/finalization result
     * @return unchanged stored response
     * @throws IOException malformed or oversized receipt
     */
    static byte[] stored(JsonNode data) throws IOException {
        if (!data.path("responseBase64").isTextual() || data.path("responseBase64").textValue().length() > 1398104) {
            throw new IOException("Invalid stored response");
        }
        try {
            byte[] bytes = Base64.getDecoder().decode(data.path("responseBase64").textValue());
            if (bytes.length > 1048576) throw new IOException("Stored response exceeds limit");
            JsonNode envelope = DocumentJson.decode(bytes);
            DocumentJson.fields(envelope, "protocol", "requestId", "status", "data");
            if (!envelope.path("protocol").isInt() || envelope.path("protocol").intValue() != 1
                    || !envelope.path("requestId").isTextual() || !envelope.path("data").isObject()
                    || !java.util.Set.of("COMMITTED", "REJECTED").contains(envelope.path("status").asText())) {
                throw new IOException("Invalid stored envelope");
            }
            UUID.fromString(envelope.path("requestId").textValue());
            return bytes;
        } catch (IllegalArgumentException failure) {
            throw new IOException("Invalid stored response", failure);
        }
    }
}
