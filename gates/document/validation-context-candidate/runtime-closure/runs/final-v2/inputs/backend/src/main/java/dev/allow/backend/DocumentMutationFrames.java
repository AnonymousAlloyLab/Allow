package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.Base64;

/** Immutable finalization envelopes preserve exact original request and response bytes. */
final class DocumentMutationFrames {
    /** Prevents construction of the stateless frame assembler. */
    private DocumentMutationFrames() {}

    /** Requires a successful private bridge dispatch, never inferring database rollback.
     * @param envelope validated private bridge response
     * @return internal operation data
     * @throws IOException bridge unavailable or malformed
     */
    static JsonNode data(JsonNode envelope) throws IOException {
        if (!envelope.path("status").asText().equals("OK") || !envelope.path("data").isObject()) {
            throw new IOException("Document persistence unavailable");
        }
        return envelope.get("data");
    }

    /** Constructs a bounded terminal rejection body with the observed accepted head.
     * @param code independently established deterministic rejection
     * @param head observed immutable accepted revision
     * @param diagnostics bounded worker diagnostics
     * @return response payload, checked again under the store lock
     */
    static ObjectNode denied(String code, long head, JsonNode diagnostics) {
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("code", code).put("acceptedRevision", head);
        data.set("diagnostics", diagnostics.deepCopy());
        return data;
    }

    /** Builds a successful public artifact envelope before entering final SQL.
     * @param attempt exact admitted generation
     * @param artifact independently checked immutable candidate
     * @param revision proposed new revision, including creation revision zero
     * @param remapping server-created temporary ID translation
     * @return complete success payload
     */
    static ObjectNode accepted(DocumentAttempt attempt, JsonNode artifact, long revision, JsonNode remapping) {
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("documentId", attempt.document())
                .put("revision", revision).put("sourceHash", artifact.path("sourceHash").textValue())
                .put("policyVersion", artifact.path("policyVersion").textValue());
        data.set("artifact", artifact.deepCopy());
        data.set("idRemapping", remapping.deepCopy());
        ObjectNode provenance = data.putObject("provenance");
        if (attempt.request().operation().equals("HISTORY_COPY")) {
            provenance.set("targetRevision", attempt.request().body().get("targetRevision"));
            provenance.set("direction", attempt.request().body().get("direction"));
        } else provenance.putNull("targetRevision").putNull("direction");
        return data;
    }

    /** Freezes an exact original HTTP outcome into the private owner-fenced frame.
     * @param attempt original request and current nonce
     * @param policy immutable current validator version
     * @param artifact checked artifact, or null for deterministic denial
     * @param outcome complete bounded original response bytes
     * @return closed persistence frame
     */
    static ObjectNode finalizeFrame(DocumentAttempt attempt, String policy, JsonNode artifact, byte[] outcome) {
        DocumentRequest request = attempt.request();
        ObjectNode args = request.identity().put("nonce", attempt.nonce()).put("policyVersion", policy)
                .put("outcomeBase64", Base64.getEncoder().encodeToString(outcome))
                .put("result", artifact == null ? "REJECTED" : "COMMITTED");
        args.set("artifact", artifact == null ? JsonNodeFactory.instance.nullNode() : artifact.deepCopy());
        args.set("expectedRevision", request.body().path("expectedRevision").isMissingNode()
                ? JsonNodeFactory.instance.nullNode() : request.body().get("expectedRevision"));
        args.set("targetRevision", request.operation().equals("HISTORY_COPY") ? request.body().get("targetRevision")
                : JsonNodeFactory.instance.nullNode());
        args.set("direction", request.operation().equals("HISTORY_COPY") ? request.body().get("direction")
                : JsonNodeFactory.instance.nullNode());
        return args;
    }
}
