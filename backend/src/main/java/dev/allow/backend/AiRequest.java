package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.Hashes;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.UUID;

/** Exact bounded create bytes, distinct from authoritative head observations. */
final class AiRequest {
    private final JsonNode value;
    private final byte[] bytes;

    /** Freezes only the closed public input, without trusting supplied artifact claims.
     * @param bytes exact original strict JSON bytes
     * @throws AiFailure denied or malformed boundary state
     */
    AiRequest(byte[] bytes) {
        value = DocumentJson.request(bytes);
        DocumentJson.fields(value, "requestId", "documentId", "baseRevision", "draftId", "draftEpoch", "contentGeneration",
                "artifactId", "sourceHash", "candidate", "intent", "kind");
        uuid(text("requestId"));
        uuid(text("draftId"));
        if (!text("documentId").matches("server:[0-9a-f-]{36}")) throw new AiFailure("INVALID_REQUEST");
        uuid(text("documentId").substring(7));
        for (String key : new String[]{"baseRevision", "draftEpoch", "contentGeneration"}) DocumentJson.revision(value, key);
        if (!Set.of("SOURCE_EDIT", "EXPLANATION").contains(text("kind"))) throw new AiFailure("INVALID_REQUEST");
        if (text("intent").isBlank() || text("intent").getBytes(StandardCharsets.UTF_8).length > 4096) throw new AiFailure("INVALID_REQUEST");
        if (!text("sourceHash").matches("[0-9a-f]{64}") || text("artifactId").length() > 256) throw new AiFailure("INVALID_REQUEST");
        candidate();
        this.bytes = bytes.clone();
    }

    /** Reads a bounded exact string without coercion.
     * @param key required input field
     * @return string value
     * @throws AiFailure denied or malformed boundary state
     */
    String text(String key) {
        if (!value.path(key).isTextual()) throw new AiFailure("INVALID_REQUEST");
        return value.path(key).textValue();
    }

    /** Returns a strict safe integer.
     * @param key required input field
     * @return nonnegative browser-compatible value
     */
    long number(String key) { return DocumentJson.revision(value, key); }

    /** Supplies the exact closed draft candidate, retaining ordinary validation authority.
     * @return defensive candidate copy
     * @throws AiFailure denied or malformed boundary state
     */
    JsonNode candidate() {
        JsonNode candidate = value.path("candidate");
        String mode = candidate.path("mode").asText();
        if (mode.equals("SOURCE")) {
            DocumentJson.fields(candidate, "mode", "source");
            if (!candidate.path("source").isTextual()
                    || candidate.path("source").asText().getBytes(StandardCharsets.UTF_8).length > 32768) throw new AiFailure("INVALID_REQUEST");
        } else if (mode.equals("BLOCK_SUPPORTED")) DocumentJson.fields(candidate, "mode", "module", "presentationCopies");
        else throw new AiFailure("UNSUPPORTED_PROFILE");
        return candidate.deepCopy();
    }

    /** Computes exact original-byte identity for replay and job binding.
     * @return SHA256 request hash
     */
    String hash() { return Hashes.bytes(bytes); }

    /** Accounts retained exact bytes conservatively.
     * @return serialized original size
     */
    int size() { return bytes.length; }

    /** Requires canonical UUID spelling.
     * @param value untrusted identifier
     * @throws AiFailure denied or malformed boundary state
     */
    private static void uuid(String value) {
        if (!UUID.fromString(value).toString().equals(value)) throw new AiFailure("INVALID_REQUEST");
    }
}
