package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.UUID;

/** Synchronous comparison admission and exact-context publication without persistence. */
final class DocumentComparison {
    private final DocumentGateway gateway;
    private final DocumentRuntime runtime;
    private final Factory workers;

    /** Package-owned worker construction seam, never selected by public input. */
    interface Factory {
        /** Creates a fresh default worker.
         * @return independently owned worker
         * @throws IOException installed worker unavailable
         */
        DocumentWorker create() throws IOException;
    }
    private boolean cleanupSafe = true;

    /** Retains scoped store and installed dependency authority.
     * @param gateway scoped operation-only store
     * @param runtime immutable installed policy
     */
    DocumentComparison(DocumentGateway gateway, DocumentRuntime runtime) { this(gateway, runtime, DocumentWorker::new); }

    /** Injects a trusted worker factory for cleanup and deadline regression tests.
     * @param gateway scoped operation-only store
     * @param runtime installed policy authority
     * @param workers trusted fresh-worker factory
     */
    DocumentComparison(DocumentGateway gateway, DocumentRuntime runtime, Factory workers) {
        this.gateway = gateway; this.runtime = runtime; this.workers = workers;
    }

    /** Validates the closed request and holds global capacity through child cleanup.
     * @param document owned route document
     * @param bytes exact raw HTTP request
     * @param operation server-selected comparison operation
     * @return request-bound complete response or explicit nonsemantic failure
     * @throws IOException unavailable response encoding
     * @throws InterruptedException cancellation after cleanup
     */
    byte[] execute(String document, byte[] bytes, String operation) throws IOException, InterruptedException {
        WarmDeadline deadline = new WarmDeadline(10000);
        JsonNode request = DocumentJson.request(bytes);
        validate(request, operation);
        runtime.requireReady();
        WorkerCapacity.acquire();
        try { return owned(document, request, bytes, operation, deadline); }
        catch (IOException failure) {
            String text = failure.getMessage();
            boolean timeout = System.nanoTime() - deadline.expiresNanos() >= 0 || text != null && text.toLowerCase(java.util.Locale.ROOT).contains("deadline");
            return response(timeout ? "TIMEOUT" : "UNAVAILABLE", identity(document, request, bytes));
        } finally { if (cleanupSafe) WorkerCapacity.release(); }
    }

    /** Executes one default worker and fences publication against a fresh authorized head.
     * @param document owned document
     * @param request closed validated request
     * @param bytes exact original request
     * @param operation trusted dispatch mode
     * @param deadline original aggregate budget
     * @return complete request-bound response
     * @throws IOException stale context, deadline or unavailable child
     * @throws InterruptedException cancellation after child reaping
     */
    private byte[] owned(String document, JsonNode request, byte[] bytes, String operation, WarmDeadline deadline)
            throws IOException, InterruptedException {
        long base = request.path("baseRevision").longValue();
        JsonNode module = request.path("candidate").path("module");
        DocumentValidationContext context = DocumentValidationContext.read(gateway, document, base, module, deadline);
        fence(context, request);
        DocumentWorker worker = workers.create();
        if (!worker.identity().equals(runtime.dependency())) throw new IOException("Comparison worker build changed");
        JsonNode outcome;
        try { outcome = worker.compare(operation, request, context.artifact(), context.inventory(), runtime.policy(), deadline.remainingMillis()); }
        finally {
            try { worker.recovery(); }
            catch (IllegalStateException uncertain) { cleanupSafe = false; }
        }
        if (!cleanupSafe) throw new IOException("Comparison cleanup unavailable");
        fence(DocumentValidationContext.read(gateway, document, base, null, deadline), request);
        deadline.check();
        ObjectNode data = identity(document, request, bytes);
        if (!outcome.path("data").isObject()) throw new IOException("Malformed comparison result");
        if (outcome.path("status").asText().equals("VALIDATED")) ComparisonResult.check(outcome.path("data"), request, operation);
        data.setAll((ObjectNode) outcome.path("data"));
        deadline.check();
        return response(outcome.path("status").asText().equals("VALIDATED") ? "OK" : outcome.path("status").asText(), data);
    }

    /** Requires the exact current base, artifact, installed policy and dependency.
     * @param context fresh authorized store snapshot
     * @param request exact browser base intent
     * @throws IOException stale or substituted context
     */
    private void fence(DocumentValidationContext context, JsonNode request) throws IOException {
        JsonNode artifact = context.artifact();
        if (context.head() != request.path("baseRevision").longValue()
                || !artifact.path("artifactId").equals(request.path("artifactId"))
                || !runtime.policy().equals(artifact.path("policyVersion").asText())
                || !runtime.dependency().equals(artifact.path("dependencyHash").asText())) throw new IOException("Stale comparison context");
        runtime.requireReady();
    }

    /** Checks exact operation-specific fields and scalar identities before context reads.
     * @param request bounded decoded request
     * @param operation trusted route operation
     * @throws IllegalArgumentException malformed closed request
     */
    private void validate(JsonNode request, String operation) {
        switch (operation) {
            case "COMPARE" -> DocumentJson.fields(request, "draftId", "draftEpoch", "baseRevision", "artifactId", "candidate", "leftId", "rightId", "scope");
            case "COMPARISON_MODEL" -> DocumentJson.fields(request, "draftId", "draftEpoch", "baseRevision", "artifactId", "source", "sourceHash");
            case "COMPARE_MODELS" -> DocumentJson.fields(request, "draftId", "draftEpoch", "baseRevision", "artifactId", "left", "right", "scope");
            case "ORACLE_PARITY" -> DocumentJson.fields(request, "draftId", "draftEpoch", "baseRevision", "artifactId", "candidate", "targetId", "oracle", "scope");
            default -> throw new IllegalArgumentException("Invalid comparison operation");
        }
        uuid(request, "draftId"); text(request, "artifactId", 100);
        DocumentJson.revision(request, "draftEpoch"); DocumentJson.revision(request, "baseRevision");
        if (!operation.equals("COMPARISON_MODEL")) {
            long scope = DocumentJson.revision(request, "scope");
            if (scope < 1 || scope > 5) throw new IllegalArgumentException("Comparison scope must be 1 through 5");
        }
        if (operation.equals("COMPARE")) {
            text(request, "leftId", 100); text(request, "rightId", 100);
            if (!request.path("candidate").path("mode").asText().equals("BLOCK_SUPPORTED")) throw new IllegalArgumentException("Complete block draft required");
        } else if (operation.equals("ORACLE_PARITY")) {
            text(request, "targetId", 100); file(request.path("oracle"), true);
            if (!request.path("candidate").path("mode").asText().equals("BLOCK_SUPPORTED")) throw new IllegalArgumentException("Complete block draft required");
        } else if (operation.equals("COMPARISON_MODEL")) file(request, false);
        else { file(request.path("left"), true); file(request.path("right"), true); }
    }

    /** Checks a strict file envelope and exact Unicode source hash without parsing source.
     * @param file exact uploaded source envelope
     * @param selected whether a predicate selection is required
     * @throws IllegalArgumentException invalid hash or source size
     */
    private void file(JsonNode file, boolean selected) {
        if (selected) { DocumentJson.fields(file, "source", "sourceHash", "predicate"); text(file, "predicate", 128); }
        if (!file.path("source").isTextual() || file.path("source").asText().getBytes(StandardCharsets.UTF_8).length > 32768)
            throw new IllegalArgumentException("Model exceeds UTF-8 byte limit");
        text(file, "sourceHash", 64);
        if (!Hashes.text(file.path("source").asText()).equals(file.path("sourceHash").asText())) throw new IllegalArgumentException("Source hash mismatch");
    }

    /** Requires one canonical draft UUID without coercion.
     * @param request exact request
     * @param field UUID field name
     * @throws IllegalArgumentException noncanonical UUID
     */
    private void uuid(JsonNode request, String field) {
        text(request, field, 36);
        String value = request.path(field).asText();
        if (!UUID.fromString(value).toString().equals(value)) throw new IllegalArgumentException("Invalid draft UUID");
    }

    /** Requires a bounded nonempty scalar string.
     * @param request exact containing object
     * @param field required field
     * @param maximum character limit
     * @throws IllegalArgumentException invalid string
     */
    private void text(JsonNode request, String field, int maximum) {
        JsonNode value = request.path(field);
        if (!value.isTextual() || value.asText().isEmpty() || value.asText().length() > maximum) throw new IllegalArgumentException("Invalid comparison identity");
    }

    /** Echoes exact request and installed provenance without saving evidence.
     * @param document owned route document
     * @param request closed browser request
     * @param bytes original request bytes
     * @return complete freshness identity
     */
    private ObjectNode identity(String document, JsonNode request, byte[] bytes) {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("requestHash", Hashes.bytes(bytes)).put("documentId", document)
                .put("policyVersion", runtime.policy()).put("dependencyHash", runtime.dependency());
        for (String name : new String[]{"draftId", "draftEpoch", "baseRevision", "artifactId", "leftId", "rightId", "scope", "sourceHash", "targetId"}) {
            if (request.has(name)) result.set(name, request.path(name));
        }
        if (request.has("scope")) result.put("bitwidth", 4).put("maxseq", 3);
        for (String side : new String[]{"left", "right", "oracle"}) if (request.has(side)) {
            result.putObject(side).put("sourceHash", request.path(side).path("sourceHash").asText())
                    .put("predicate", request.path(side).path("predicate").asText());
        }
        return result;
    }

    /** Encodes only closed result statuses within the existing document response budget.
     * @param status worker/admission status
     * @param data exact response data
     * @return serialized bounded envelope
     * @throws IOException encoding or unknown worker status
     */
    private byte[] response(String status, JsonNode data) throws IOException {
        if (!Set.of("OK", "INVALID", "UNSUPPORTED", "UNAVAILABLE", "TIMEOUT", "ERROR").contains(status)) throw new IOException("Invalid comparison status");
        return DocumentReplies.encode(UUID.randomUUID().toString(), status, data);
    }

    /** Returns positive cleanup evidence for public scope reclamation.
     * @return whether every attempted worker was positively reaped
     */
    boolean cleanupSafe() { return cleanupSafe; }
}
