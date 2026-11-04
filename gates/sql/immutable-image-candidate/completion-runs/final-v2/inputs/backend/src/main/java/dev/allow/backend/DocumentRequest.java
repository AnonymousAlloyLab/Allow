package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.Base64;
import java.util.UUID;

/** Exact original mutation identity; generated validation artifacts are deliberately separate. */
final class DocumentRequest {
    private final String document;
    private final String route;
    private final String operation;
    private final String requestId;
    private final String encoded;
    private final JsonNode body;

    /** Decodes only bounded original intent and retains exact bytes for receipt authority.
     * @param document owned document ID or reserved CREATE namespace
     * @param route exact fixed endpoint path
     * @param operation fixed coordinator operation
     * @param bytes exact original strict JSON body
     * @throws IOException malformed UTF-8 or JSON
     * @throws IllegalArgumentException invalid envelope key
     */
    DocumentRequest(String document, String route, String operation, byte[] bytes) throws IOException {
        if (bytes.length > 262144) throw new IllegalArgumentException("Request exceeds limit");
        this.document = document;
        this.route = route;
        this.operation = operation;
        requestId = UUID.randomUUID().toString();
        encoded = Base64.getEncoder().encodeToString(bytes);
        body = DocumentJson.request(bytes);
        if (!body.isObject() || !body.path("idempotencyKey").isTextual()
                || !body.path("idempotencyKey").textValue().matches("[A-Za-z0-9_-]{16,128}")) {
            throw new IllegalArgumentException("Invalid idempotency key");
        }
    }

    /** Produces the closed receipt identity used before new candidate validation.
     * @return new private bridge arguments
     */
    ObjectNode identity() {
        return JsonNodeFactory.instance.objectNode().put("documentId", document)
                .put("key", body.path("idempotencyKey").textValue()).put("method", "POST")
                .put("route", route).put("bodyBase64", encoded);
    }

    /** Validates operation-specific fields only after authorized receipt lookup.
     * @throws IllegalArgumentException malformed new mutation
     */
    void validate() {
        if (operation.equals("CREATE")) {
            DocumentJson.fields(body, "idempotencyKey", "title");
            String title = body.path("title").asText("");
            if (!body.path("title").isTextual() || title.codePointCount(0, title.length()) < 1
                    || title.codePointCount(0, title.length()) > 128) throw new IllegalArgumentException("Invalid title");
        } else if (operation.equals("COMMIT")) {
            DocumentJson.fields(body, "idempotencyKey", "expectedRevision", "candidate");
            DocumentJson.revision(body, "expectedRevision");
            if (!body.path("candidate").isObject()) throw new IllegalArgumentException("Invalid candidate");
        } else {
            DocumentJson.fields(body, "idempotencyKey", "expectedRevision", "targetRevision", "direction");
            DocumentJson.revision(body, "expectedRevision");
            DocumentJson.revision(body, "targetRevision");
            if (!java.util.Set.of("UNDO", "REDO").contains(body.path("direction").asText())) {
                throw new IllegalArgumentException("Invalid history direction");
            }
        }
    }

    /** Creates admission arguments binding the actual trusted supervisor incarnation.
     * @return private admission frame
     * @throws IOException process identity unavailable
     */
    ObjectNode admission() throws IOException {
        ObjectNode args = identity().put("operation", operation).put("ownerPid", ProcessHandle.current().pid())
                .put("ownerStartTicks", ProcessIdentity.startTicks(ProcessHandle.current().pid()));
        args.set("expectedRevision", body.has("expectedRevision") ? body.get("expectedRevision").deepCopy()
                : JsonNodeFactory.instance.nullNode());
        return args;
    }

    /** Returns a defensive decoded intent snapshot.
     * @return submitted original body
     */
    JsonNode body() { return body.deepCopy(); }

    /** Returns the fixed operation selected by the authenticated endpoint.
     * @return CREATE, COMMIT or HISTORY_COPY
     */
    String operation() { return operation; }

    /** Returns the owned document namespace.
     * @return document ID or CREATE
     */
    String document() { return document; }

    /** Returns the server response identity that is persisted unchanged on terminal outcome.
     * @return original request identifier
     */
    String requestId() { return requestId; }

    /** Keys recoverable in-memory work without making digest equality authoritative.
     * @return document/key namespace
     */
    String pendingKey() { return document + ":" + body.path("idempotencyKey").textValue(); }
}
