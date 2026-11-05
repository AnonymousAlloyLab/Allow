package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/** Coordinates exact scoped receipt recovery, isolated validation and owner-fenced SQL commits. */
@Service
final class DocumentMutations {
    private final DocumentGateway gateway;
    private final DocumentRuntime runtime;
    private final DocumentMutationWorkers.Factory workers;
    private final Map<String, DocumentAttempt> pending = new ConcurrentHashMap<>();
    private final Map<String, DocumentRequest> unstarted = new ConcurrentHashMap<>();

    /** Binds the private persistence bridge and installed workspace policy.
     * @param gateway operation-only scoped store
     * @param runtime exclusive initialized workspace incarnation
     */
    @Autowired
    DocumentMutations(DocumentGateway gateway, DocumentRuntime runtime) {
        this(gateway, runtime, DocumentWorker::new);
    }

    /** Supplies a documented worker factory for isolated coordinator tests.
     * @param gateway operation-only store
     * @param runtime current workspace policy
     * @param workers owned validator factory
     */
    DocumentMutations(DocumentGateway gateway, DocumentRuntime runtime, DocumentMutationWorkers.Factory workers) {
        this.gateway = gateway;
        this.runtime = runtime;
        this.workers = workers;
    }

    /** Verifies retained attempts before an expired public workspace may be purged.
     * @return whether all retained workers are finished and reaped or never started
     */
    boolean cleanupSafe() {
        for (DocumentAttempt attempt : pending.values()) {
            try { attempt.recovery(); }
            catch (IOException | IllegalStateException uncertain) { return false; }
        }
        return true;
    }

    /** Performs a mutation while preserving exact original receipt authority across failures.
     * @param request authenticated endpoint's exact bounded original intent
     * @return complete bounded original HTTP response bytes
     * @throws IOException unavailable pre-finalization context or serialization
     * @throws InterruptedException interrupted pre-finalization child after reaping
     */
    byte[] mutate(DocumentRequest request) throws IOException, InterruptedException {
        runtime.requireReady();
        JsonNode receipt = DocumentMutationFrames.data(gateway.request("receipt", request.identity()));
        byte[] recovered = receipt(request, receipt);
        if (recovered != null) return recovered;
        request.validate();
        WorkerCapacity.acquire();
        try {
            return admitted(request);
        } finally {
            WorkerCapacity.release();
        }
    }

    /** Resolves an existing receipt before allocating worker capacity or parsing new intent.
     * @param request original incoming request
     * @param data authorized private receipt response
     * @return exact stored response or null when absent
     * @throws IOException malformed or oversized receipt
     */
    private byte[] receipt(DocumentRequest request, JsonNode data) throws IOException {
        String status = data.path("status").asText();
        if (status.equals("REPLAY")) {
            DocumentAttempt old = pending.get(request.pendingKey());
            if (old != null && old.request().identity().equals(request.identity())) pending.remove(request.pendingKey(), old);
            DocumentRequest before = unstarted.get(request.pendingKey());
            if (before != null && before.identity().equals(request.identity())) unstarted.remove(request.pendingKey(), before);
            return DocumentReplies.stored(data);
        }
        if (status.equals("ABSENT") || status.equals("ADMITTED")) return null;
        if (java.util.Set.of("IDEMPOTENCY_CONFLICT", "NOT_FOUND", "IN_PROGRESS", "CAPACITY_PRE_ADMISSION", "STALE_OWNER").contains(status)) return DocumentReplies.status(status);
        throw new IOException("Receipt lookup unavailable");
    }

    /** Resumes a finished admitted generation or reserves a new bounded attempt.
     * @param request complete original intent after receipt miss
     * @return terminal or truthful availability response
     * @throws IOException unavailable admission or validation context
     * @throws InterruptedException interrupted child after cleanup
     */
    private byte[] admitted(DocumentRequest request) throws IOException, InterruptedException {
        DocumentAttempt old = pending.get(request.pendingKey());
        if (old != null && !old.request().identity().equals(request.identity())) {
            return DocumentReplies.status("IDEMPOTENCY_CONFLICT");
        }
        DocumentRequest before = unstarted.get(request.pendingKey());
        if (before != null && !before.identity().equals(request.identity())) return DocumentReplies.status("IDEMPOTENCY_CONFLICT");
        if (old == null && before == null && pending.size() + unstarted.size() >= 64) return DocumentReplies.status("CAPACITY_PRE_ADMISSION");
        DocumentWorker worker = workers.create();
        if (!runtime.dependency().equals(worker.identity())) throw new IOException("Validator build changed during launch");
        JsonNode data = admission(request, old, before);
        byte[] known = receipt(request, data);
        if (known != null) return known;
        return begin(old != null ? old.request() : before != null ? before : request, worker, data);
    }

    /** Records no-start provenance before admission and recovers a lost admission reply.
     * @param request exact current request
     * @param old completed known-nonce generation, when any
     * @param before exact request whose admission reply was lost before worker startup
     * @return private admission result
     * @throws IOException unavailable admission acknowledgement
     * @throws InterruptedException interrupted bridge after reaping
     */
    private JsonNode admission(DocumentRequest request, DocumentAttempt old, DocumentRequest before)
            throws IOException, InterruptedException {
        if (old != null) {
            try { return DocumentMutationFrames.data(gateway.request("recover", old.recovery())); }
            catch (IllegalStateException failure) { throw new IOException("Worker reaping proof unavailable", failure); }
        }
        DocumentRequest original = before == null ? request : before;
        unstarted.put(original.pendingKey(), original);
        if (before != null) {
            ObjectNode proof = original.identity().put("ownerPid", ProcessHandle.current().pid())
                    .put("ownerStartTicks", ProcessIdentity.startTicks(ProcessHandle.current().pid())).put("noWorkerStarted", true);
            JsonNode recovered = DocumentMutationFrames.data(gateway.request("recoverUnstarted", proof));
            if (!recovered.path("status").asText().equals("ABSENT")) return recovered;
        }
        JsonNode data = DocumentMutationFrames.data(gateway.request("admit", original.admission()));
        if (java.util.Set.of("CAPACITY_PRE_ADMISSION", "IDEMPOTENCY_CONFLICT", "NOT_FOUND").contains(data.path("status").asText())) {
            unstarted.remove(original.pendingKey(), original);
        }
        return data;
    }

    /** Retains the owner nonce before any child starts and marks completion after reaping.
     * @param request preserved first request identity
     * @param worker newly owned isolated validator
     * @param admission private admitted scope and nonce
     * @return exact terminal response or availability
     * @throws IOException unavailable context or encoding
     * @throws InterruptedException interrupted child after reaping
     */
    private byte[] begin(DocumentRequest request, DocumentWorker worker, JsonNode admission)
            throws IOException, InterruptedException {
        if (!admission.path("status").asText().equals("ADMITTED")) {
            return DocumentReplies.status(admission.path("status").asText("UNAVAILABLE"));
        }
        if (!admission.path("nonce").isTextual() || !admission.path("documentId").isTextual()) {
            throw new IOException("Admission policy mismatch");
        }
        DocumentAttempt attempt = new DocumentAttempt(request, worker, admission);
        pending.put(request.pendingKey(), attempt);
        unstarted.remove(request.pendingKey());
        try {
            if (!runtime.policy().equals(admission.path("policyVersion").asText())) return DocumentReplies.status("REVALIDATE");
            return evaluate(attempt);
        } finally {
            attempt.finish();
        }
    }

    /** Selects proved empty creation or exact authorized base context for a full edit.
     * @param attempt current admitted generation
     * @return terminal response or availability without fabricated acceptance
     * @throws IOException unavailable context or worker
     * @throws InterruptedException interrupted owned child
     */
    private byte[] evaluate(DocumentAttempt attempt) throws IOException, InterruptedException {
        if (attempt.request().operation().equals("CREATE")) {
            JsonNode artifact = DocumentArtifacts.empty(runtime.policy(), runtime.dependency());
            return persist(attempt, artifact, DocumentMutationFrames.accepted(attempt, artifact, 0,
                    JsonNodeFactory.instance.objectNode()));
        }
        JsonNode current = DocumentMutationValidation.read(gateway, attempt.document(), null);
        long head = current.path("headRevision").longValue();
        if (head != attempt.request().body().path("expectedRevision").longValue()) {
            return persist(attempt, null, denial("STALE_REVISION", head));
        }
        return validate(attempt, current.path("artifact"), head);
    }

    /** Validates current edit or unchanged historical content inside the isolated worker.
     * @param attempt current worker and owner nonce
     * @param base current authorized artifact
     * @param head expected current revision
     * @return stored terminal outcome or availability
     * @throws IOException malformed validator response or unavailable context
     * @throws InterruptedException interrupted owned child after reaping
     */
    private byte[] validate(DocumentAttempt attempt, JsonNode base, long head)
            throws IOException, InterruptedException {
        DocumentRequest request = attempt.request();
        JsonNode result;
        if (request.operation().equals("HISTORY_COPY")) {
            long target = request.body().path("targetRevision").longValue();
            if (target > head) return persist(attempt, null, denial("INVALID_UNDO_TARGET", head));
            JsonNode old = DocumentMutationValidation.read(gateway, attempt.document(), request.body().get("targetRevision"));
            JsonNode inventory = DocumentMutationValidation.inventory(gateway, attempt.document(), old.path("artifact").path("module"));
            result = attempt.worker().revalidate(old.path("artifact"), inventory, runtime.policy());
        } else {
            JsonNode candidate = request.body().get("candidate");
            JsonNode inventory = DocumentMutationValidation.inventory(gateway, attempt.document(), candidate);
            result = attempt.worker().validate(candidate, base, inventory, runtime.policy());
        }
        return validated(attempt, result, head);
    }

    /** Converts only a complete registered worker result into a terminal outcome.
     * @param attempt admitted original request
     * @param result isolated nonce-checked worker response
     * @param head observed accepted head
     * @return exact committed or rejected response
     * @throws IOException incomplete result, encoding or finalization error
     * @throws InterruptedException interrupted finalization handled as uncertainty
     */
    private byte[] validated(DocumentAttempt attempt, JsonNode result, long head)
            throws IOException, InterruptedException {
        JsonNode data = DocumentMutationValidation.checked(result);
        if (result.path("status").asText().equals("INVALID")) {
            return persist(attempt, null, DocumentMutationFrames.denied(data.path("code").textValue(), head,
                    data.get("diagnostics")));
        }
        JsonNode artifact = DocumentArtifacts.checked(data, runtime.policy(), runtime.dependency());
        return persist(attempt, artifact, DocumentMutationFrames.accepted(attempt, artifact, head + 1,
                data.get("idRemapping")));
    }

    /** Creates an explicit coordinator-established stale or history-target denial.
     * @param code exact deterministic reason
     * @param head observed head to recheck under the store lock
     * @return bounded rejection data
     */
    private ObjectNode denial(String code, long head) {
        return DocumentMutationFrames.denied(code, head, JsonNodeFactory.instance.arrayNode());
    }

    /** Bounds each exact response before SQL and resolves a bounded stale-head race.
     * @param attempt original identity and current nonce
     * @param artifact checked accepted candidate or null
     * @param data public terminal payload
     * @return exact stored outcome or truthful uncertainty/availability
     * @throws IOException response serialization exceeds limits
     * @throws InterruptedException retained for compatibility with interrupted orchestration
     */
    private byte[] persist(DocumentAttempt attempt, JsonNode artifact, JsonNode data)
            throws IOException, InterruptedException {
        for (int retry = 0; retry < 3; retry++) {
            byte[] outcome = DocumentReplies.encode(attempt.request().requestId(), artifact == null ? "REJECTED" : "COMMITTED", data);
            ObjectNode frame = DocumentMutationFrames.finalizeFrame(attempt, runtime.policy(), artifact, outcome);
            JsonNode result = finalize(frame);
            String status = result.path("status").asText();
            if (java.util.Set.of("COMMITTED", "REJECTED", "REPLAY").contains(status)) {
                try {
                    byte[] stored = DocumentReplies.stored(result);
                    pending.remove(attempt.request().pendingKey(), attempt);
                    return stored;
                }
                catch (IOException failure) { return DocumentReplies.status("UNKNOWN_COMMIT_OUTCOME"); }
            }
            if (!status.equals("STALE_REVISION")) return DocumentReplies.status(status);
            long head = DocumentJson.revision(result, "acceptedRevision");
            artifact = null;
            data = denial("STALE_REVISION", head);
        }
        return DocumentReplies.status("UNAVAILABLE");
    }

    /** Validates final operation status before disclosing any definite outcome.
     * @param data bounded private finalization payload
     * @return known status or conservative uncertain acknowledgement
     */
    private JsonNode finalizedData(JsonNode data) {
        if (java.util.Set.of("COMMITTED", "REJECTED", "REPLAY", "STALE_REVISION", "REVALIDATE",
                "STALE_OWNER", "IDEMPOTENCY_CONFLICT", "REVISION_EXHAUSTED").contains(data.path("status").asText())) return data;
        return JsonNodeFactory.instance.objectNode().put("status", "UNKNOWN_COMMIT_OUTCOME");
    }

    /** Treats every lost finalization acknowledgement as uncertain unless explicitly rolled back.
     * @param frame bounded frozen finalization request
     * @return internal result with original receipt bytes where known
     * @throws IOException only response encoding failures outside the uncertain bridge path
     */
    private JsonNode finalize(ObjectNode frame) throws IOException {
        try {
            JsonNode envelope = gateway.request("finalize", frame);
            String status = envelope.path("status").asText();
            if (status.equals("OK")) return finalizedData(envelope.path("data"));
            return JsonNodeFactory.instance.objectNode().put("status", status.equals("KNOWN_ROLLBACK")
                    ? "KNOWN_ROLLBACK" : "UNKNOWN_COMMIT_OUTCOME");
        } catch (IOException | RuntimeException failure) {
            return JsonNodeFactory.instance.objectNode().put("status", "UNKNOWN_COMMIT_OUTCOME");
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            return JsonNodeFactory.instance.objectNode().put("status", "UNKNOWN_COMMIT_OUTCOME");
        }
    }
}
