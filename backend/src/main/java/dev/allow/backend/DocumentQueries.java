package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.dto.JobRequest;
import dev.allow.dto.JobView;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

/** Authorized reads, advisory previews and accepted-revision solver selection. */
@Service
final class DocumentQueries {
    private final WorkerLaunchProfile advisoryProfile;
    private final DocumentGateway gateway;
    private final DocumentRuntime runtime;
    private final JobService jobs;
    private final String owner;
    private volatile boolean cleanupSafe = true;
    private record AnalysisRegistration(JsonNode key, String policy, String dependency) {}
    private final Map<String, AnalysisRegistration> analyses = new LinkedHashMap<>();

    /** Connects operation-only persistence, current policy and the bounded solver supervisor.
     * @param gateway scoped private store
     * @param runtime exclusive local incarnation
     * @param jobs existing isolated solver jobs
     * @param policy closed deployment selection
     */
    @Autowired
    DocumentQueries(DocumentGateway gateway, DocumentRuntime runtime, JobService jobs, DeploymentPolicy policy) {
        this(gateway, runtime, jobs, policy, "");
    }

    /** Creates a coordinator whose retained analyses belong to one immutable scope.
     * @param gateway immutable scope bridge
     * @param runtime installation policy
     * @param jobs globally bounded jobs
     * @param policy advisory profile
     * @param owner server-derived job owner
     */
    DocumentQueries(DocumentGateway gateway, DocumentRuntime runtime, JobService jobs, DeploymentPolicy policy, String owner) {
        this.advisoryProfile = policy.advisoryProfile();
        this.gateway = gateway;
        this.runtime = runtime;
        this.jobs = jobs;
        this.owner = owner;
    }

    /** Uses the local default in isolated callers.
     * @param gateway scoped private store
     * @param runtime exclusive local incarnation
     * @param jobs isolated solver jobs
     */
    DocumentQueries(DocumentGateway gateway, DocumentRuntime runtime, JobService jobs) {
        this(gateway, runtime, jobs, new DeploymentPolicy("", "", "DEFAULT"));
    }

    /** Lists bounded document summaries without model content.
     * @return authorized summaries
     * @throws IOException store unavailable
     * @throws InterruptedException interrupted private bridge
     */
    byte[] list() throws IOException, InterruptedException {
        return reply("OK", data("list", JsonNodeFactory.instance.objectNode()));
    }

    /** Reads a current head or immutable historical artifact in its revision envelope.
     * @param document authorized document identifier
     * @param revision historical target, or null for head
     * @return exact source and artifact-bound projection
     * @throws IOException missing or unavailable artifact
     * @throws InterruptedException interrupted private bridge
     */
    byte[] read(String document, Long revision) throws IOException, InterruptedException {
        ObjectNode result = (ObjectNode) readData(document, revision);
        result.set("revision", result.get("requestedRevision"));
        result.remove("requestedRevision");
        return reply("OK", result);
    }

    /** Obtains one scoped historical snapshot without allowing browser-selected scope.
     * @param document document identity
     * @param revision nullable historical revision
     * @return private read response
     * @throws IOException missing or unavailable snapshot
     * @throws InterruptedException interrupted store call
     */
    private JsonNode readData(String document, Long revision) throws IOException, InterruptedException {
        ObjectNode args = JsonNodeFactory.instance.objectNode().put("documentId", document);
        if (revision == null) args.putNull("revision"); else args.put("revision", revision);
        JsonNode result = data("read", args);
        if (!result.has("artifact")) throw new IOException("Document snapshot unavailable");
        return result;
    }

    /** Compares exact current draft formulas or independently inspected model files.
     * @param document authorized route document
     * @param bytes exact bounded HTTP intent
     * @param operation trusted fixed route dispatch
     * @return request-bound isolated result without persistence
     * @throws IOException infrastructure or response failure
     * @throws InterruptedException cancellation after cleanup
     */
    byte[] compare(String document, byte[] bytes, String operation) throws IOException, InterruptedException {
        if (!cleanupSafe) throw new IOException("Document worker cleanup is quarantined");
        DocumentComparison comparison = new DocumentComparison(gateway, runtime);
        try { return comparison.execute(document, bytes, operation); }
        finally { if (!comparison.cleanupSafe()) cleanupSafe = false; }
    }

    /** Applies advisory validation to an exact request without advancing accepted state.
     * @param document authorized document
     * @param bytes retained original HTTP body
     * @return request-bound proposed source or diagnostics
     * @throws IOException malformed body or unavailable infrastructure
     * @throws InterruptedException interrupted child after reaping
     * @throws IllegalArgumentException invalid draft identity or envelope
     */
    byte[] validate(String document, byte[] bytes) throws IOException, InterruptedException {
        JsonNode request = DocumentJson.request(bytes);
        DocumentJson.fields(request, "draftId", "draftEpoch", "baseRevision", "candidate");
        if (!request.path("draftId").isTextual()) throw new IllegalArgumentException("Invalid draft ID");
        UUID.fromString(request.path("draftId").textValue());
        DocumentJson.revision(request, "draftEpoch");
        long base = DocumentJson.revision(request, "baseRevision");
        runtime.requireReady();
        WarmDeadline deadline = new WarmDeadline(10000);
        WorkerCapacity.acquire();
        try {
            return validateOwned(document, base, request, bytes, deadline);
        } finally {
            WorkerCapacity.release();
        }
    }

    /** Selects only the compiled advisory policy while keeping the same public response.
     * @param document authorized document
     * @param base exact requested base revision
     * @param request checked draft envelope
     * @param bytes exact original request bytes
     * @param deadline budget captured before shared admission, never restarted by dispatch
     * @return request-bound advisory response
     * @throws IOException unavailable context, worker or result
     * @throws InterruptedException cancelled private operation
     */
    private byte[] validateOwned(String document, long base, JsonNode request, byte[] bytes, WarmDeadline deadline)
            throws IOException, InterruptedException {
        if (WarmRuntime.enabled()) return validateWarm(document, base, request, bytes, deadline);
        JsonNode candidate = request.path("candidate");
        DocumentValidationContext context = DocumentValidationContext.read(gateway, document, base, candidate.path("module"));
        DocumentWorker worker = new DocumentWorker(advisoryProfile);
        if (!worker.identity().equals(runtime.dependency())) throw new IOException("Validator build changed");
        try {
            JsonNode outcome = worker.validate(candidate, context.artifact(), context.inventory(), runtime.policy());
            return validationReply(request, bytes, outcome);
        } finally {
            try { worker.recovery(); }
            catch (IllegalStateException uncertain) { cleanupSafe = false; }
        }
    }

    /** Keeps context, response construction and final publication within one admitted operation.
     * @param document authorized document
     * @param base exact requested revision
     * @param request checked draft intent
     * @param bytes exact original HTTP request
     * @param deadline original admission budget, including any delayed dispatch
     * @return unchanged envelope after owned cleanup and the final publication fence
     * @throws IOException unavailable, changed, cancelled or expired candidate generation
     * @throws InterruptedException interrupted context or worker
     */
    private byte[] validateWarm(String document, long base, JsonNode request, byte[] bytes, WarmDeadline deadline)
            throws IOException, InterruptedException {
        deadline.check();
        WarmWorkerPool pool = WarmRuntime.current().pool();
        WarmRequestBinding binding = new WarmRequestBinding(UUID.randomUUID().toString(), Hashes.bytes(bytes),
                document, base, runtime.policy(), runtime.dependency(), pool.poolNonce());
        pool.begin();
        JsonNode candidate = request.path("candidate");
        WarmContextPermit context = WarmContextPermit.read(gateway, binding, candidate.path("module"), deadline);
        try (WarmResultLease result = pool.validate(binding, candidate, context, deadline)) {
            return result.publish(validationReply(request, bytes, result.result()));
        }
    }

    /** Binds a preview to exact request bytes, with SOURCE's additional exact-source identity.
     * @param request original draft intent
     * @param bytes exact serialized request
     * @param result independently checked worker envelope
     * @return bounded advisory response
     * @throws IOException malformed worker result or oversized serialization
     */
    private byte[] validationReply(JsonNode request, byte[] bytes, JsonNode result) throws IOException {
        String status = result.path("status").asText();
        if (status.equals("UNAVAILABLE")) return DocumentReplies.status("UNAVAILABLE");
        JsonNode checked = result.path("data");
        if (!checked.path("diagnostics").isArray()) throw new IOException("Missing diagnostics");
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("requestHash", Hashes.bytes(bytes));
        for (String name : new String[]{"draftId", "draftEpoch", "baseRevision"}) data.set(name, request.get(name));
        data.put("supportMode", checked.path("mode").asText("UNAVAILABLE"));
        data.set("diagnostics", draftDiagnostics(checked));
        data.set("proposedSource", checked.has("source") ? checked.get("source") : JsonNodeFactory.instance.nullNode());
        data.set("proposedSourceHash", checked.has("sourceHash") ? checked.get("sourceHash") : JsonNodeFactory.instance.nullNode());
        if (request.path("candidate").path("mode").asText().equals("SOURCE")) {
            data.put("sourceHash", Hashes.text(request.path("candidate").path("source").asText()));
        } else if (checked.has("sourceHash")) data.set("sourceHash", checked.get("sourceHash"));
        return reply(status, data);
    }

    /** Translates fresh server IDs back to submitted draft IDs for advisory diagnostics.
     * @param checked worker content and remapping
     * @return defensive bounded diagnostics in submitted identity space
     * @throws IOException diagnostic limit exceeded
     */
    private JsonNode draftDiagnostics(JsonNode checked) throws IOException {
        JsonNode diagnostics = checked.path("diagnostics").deepCopy();
        if (diagnostics.size() > 64 || JsonWire.encode(diagnostics).length > 32768) throw new IOException("Diagnostic limit");
        Map<String, String> inverse = new LinkedHashMap<>();
        var mappings = checked.path("idRemapping").fields();
        while (mappings.hasNext()) {
            var mapping = mappings.next();
            inverse.put(mapping.getValue().asText(), mapping.getKey());
        }
        for (JsonNode diagnostic : diagnostics) {
            if (diagnostic.isObject() && inverse.containsKey(diagnostic.path("nodeId").asText())) {
                ((ObjectNode) diagnostic).put("nodeId", inverse.get(diagnostic.path("nodeId").asText()));
            }
        }
        return diagnostics;
    }

    /** Resolves an immutable saved command and checks older artifacts against the running policy.
     * @param document authorized document
     * @param bytes closed accepted-analysis selection
     * @return job and complete accepted analysis identity
     * @throws IOException unavailable artifact or infrastructure
     * @throws InterruptedException interrupted read
     */
    synchronized byte[] analyze(String document, byte[] bytes) throws IOException, InterruptedException {
        JsonNode request = DocumentJson.request(bytes);
        DocumentJson.fields(request, "acceptedRevision", "commandKey", "draftEpoch", "exactSourceHash");
        long revision = DocumentJson.revision(request, "acceptedRevision");
        long epoch = DocumentJson.revision(request, "draftEpoch");
        if (!cleanupSafe) throw new IOException("Document worker cleanup is quarantined");
        runtime.requireReady();
        JsonNode artifact = readData(document, revision).path("artifact");
        JsonNode command = SavedAnalysis.command(artifact, request);
        try { dev.allow.worker.SourcePolicy.check(artifact.path("source").textValue()); }
        catch (IllegalArgumentException incompatible) {
            return analysisRejection("SAVED_MODEL_INCOMPATIBLE",
                    "The saved model exceeds current source bounds or uses unsupported imports. Edit and save it before analyzing again.");
        }
        if (!runtime.policy().equals(artifact.path("policyVersion").asText())
                || !runtime.dependency().equals(artifact.path("dependencyHash").asText())) {
            byte[] rejection = revalidateAnalysis(document, artifact, command);
            if (rejection != null) return rejection;
        }
        JobView job = jobs.submit(new JobRequest(artifact.path("source").textValue(), command.path("index").intValue(),
                revision, epoch, "ANALYZE"), owner);
        ObjectNode key = analysisKey(document, revision, epoch, artifact, command, job);
        if (analyses.size() >= 128) analyses.remove(analyses.keySet().iterator().next());
        analyses.put(job.jobId(), new AnalysisRegistration(key.deepCopy(), runtime.policy(), runtime.dependency()));
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("jobId", job.jobId());
        data.set("acceptedAnalysisKey", key);
        data.set("job", JsonWire.decode(JsonWire.encode(job), JsonNode.class));
        return reply("SUBMITTED", data);
    }

    /** Rechecks immutable saved content without creating a replacement artifact or revision.
     * @param document authorized immutable owner
     * @param artifact selected stored artifact
     * @param command selected stored command
     * @return bounded rejection or null after exact current-policy validation
     * @throws IOException unavailable validator, build drift or uncertain cleanup
     * @throws InterruptedException interrupted admission or worker
     */
    private byte[] revalidateAnalysis(String document, JsonNode artifact, JsonNode command)
            throws IOException, InterruptedException {
        WorkerCapacity.acquire();
        try {
            JsonNode inventory = DocumentMutationValidation.inventory(gateway, document, artifact.path("module"));
            DocumentWorker worker = new DocumentWorker();
            if (!worker.identity().equals(runtime.dependency())) throw new IOException("Validator build changed");
            JsonNode outcome;
            try { outcome = worker.revalidate(artifact, inventory, runtime.policy()); }
            finally {
                try { worker.recovery(); }
                catch (IllegalStateException uncertain) {
                    cleanupSafe = false;
                    throw new IOException("Analysis validator cleanup is uncertain", uncertain);
                }
            }
            JsonNode checked = DocumentMutationValidation.checked(outcome);
            if (outcome.path("status").asText().equals("INVALID")) {
                return analysisRejection("SAVED_MODEL_INCOMPATIBLE",
                        "The saved model does not validate under the current policy and whole-module bounds. Edit and save it before analyzing again.");
            }
            if (!SavedAnalysis.matches(artifact, command, checked)) {
                return analysisRejection("SAVED_COMMAND_CHANGED",
                        "The saved command differs under the current policy. Review the command and save the model before analyzing again.");
            }
            return null;
        } finally { WorkerCapacity.release(); }
    }

    /** Returns a fixed content-free explanation for a valid but incompatible saved selection.
     * @param code bounded machine-readable reason
     * @param message fixed user action
     * @return rejected analysis envelope
     * @throws IOException serialization failure
     */
    private byte[] analysisRejection(String code, String message) throws IOException {
        return reply("REJECTED", JsonNodeFactory.instance.objectNode().put("code", code).put("message", message));
    }

    /** Reads accepted-document evidence only through its original full identity binding.
     * @param document authorized document
     * @param jobId opaque solver job
     * @return current or historical labeled result with complete evidence identity
     * @throws IOException unknown, stale-policy or unavailable job
     * @throws InterruptedException interrupted artifact lookup
     */
    synchronized byte[] analysis(String document, String jobId) throws IOException, InterruptedException {
        AnalysisRegistration registration = analyses.get(jobId);
        JsonNode key = registration == null ? null : registration.key();
        if (key == null || !document.equals(key.path("documentId").asText())) throw new IOException("Unknown analysis");
        JsonNode current = readData(document, null);
        JobView job = jobs.get(jobId, owner);
        if (job == null || !job.analysisKey().equals(key.path("jobAnalysisKey").asText())
                || !runtime.policy().equals(registration.policy())
                || !runtime.dependency().equals(registration.dependency())) throw new IOException("Stale analysis");
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("jobId", jobId);
        data.put("historical", current.path("headRevision").longValue() != key.path("acceptedRevision").longValue());
        data.set("acceptedAnalysisKey", key.deepCopy());
        data.set("job", JsonWire.decode(JsonWire.encode(job), JsonNode.class));
        return reply("OK", data);
    }

    /** Reads the exact current private head for AI authorization and stale checks.
     * @param document server-owned document ID
     * @return bounded authorized current snapshot
     * @throws IOException unavailable scoped store
     * @throws InterruptedException interrupted store operation
     */
    JsonNode aiHead(String document) throws IOException, InterruptedException { return readData(document, null); }

    /** Checks an AI candidate using the shared context and fresh isolated worker lane.
     * @param document authorized document
     * @param base exact expected revision
     * @param candidate exact bounded candidate
     * @param millis remaining whole-job budget
     * @return full independently checked module/source or deterministic invalid result
     * @throws IOException unavailable context, worker or cleanup
     * @throws InterruptedException cancelled operation after owned worker cleanup
     */
    JsonNode aiValidate(String document, long base, JsonNode candidate, long millis) throws IOException, InterruptedException {
        runtime.requireReady();
        WarmDeadline deadline = new WarmDeadline(Math.min(10000, millis));
        WorkerCapacity.acquire();
        try { return aiValidateOwned(document, base, candidate, deadline); }
        finally { WorkerCapacity.release(); }
    }

    /** Performs bounded validation after acquiring the existing sole worker admission.
     * @param document authorized document
     * @param base expected base revision
     * @param candidate submitted candidate
     * @param deadline original shared operation deadline
     * @return full trusted worker response
     * @throws IOException unavailable worker or deadline
     * @throws InterruptedException cancelled operation after cleanup
     */
    private JsonNode aiValidateOwned(String document, long base, JsonNode candidate, WarmDeadline deadline)
            throws IOException, InterruptedException {
        DocumentValidationContext context = DocumentValidationContext.read(gateway, document, base, candidate.path("module"), deadline);
        DocumentWorker worker = new DocumentWorker();
        if (!worker.identity().equals(runtime.dependency())) throw new IOException("Validator build changed");
        try {
            JsonNode result = worker.validateBounded(candidate, context.artifact(), context.inventory(), runtime.policy(), deadline.remainingMillis());
            deadline.check();
            return result;
        } finally {
            try { worker.recovery(); }
            catch (IllegalStateException uncertain) { cleanupSafe = false; }
        }
    }

    /** Refuses scope reclamation after uncertain advisory child cleanup.
     * @return whether every attempted advisory child supplied reap/no-start evidence
     */
    boolean cleanupSafe() { return cleanupSafe; }

    /** Builds complete evidence identity without using expression labels as authority.
     * @param document owned document
     * @param revision immutable accepted revision
     * @param epoch presentation generation
     * @param artifact source/policy/dependency identity
     * @param command parser occurrence descriptor
     * @param job independently isolated solver job
     * @return complete accepted identity
     */
    private ObjectNode analysisKey(String document, long revision, long epoch, JsonNode artifact, JsonNode command, JobView job) {
        ObjectNode key = JsonNodeFactory.instance.objectNode().put("documentId", document)
                .put("acceptedRevision", revision).put("draftEpoch", epoch).put("jobAnalysisKey", job.analysisKey());
        for (String field : new String[]{"artifactId", "sourceHash", "policyVersion", "dependencyHash"}) {
            key.set(field, artifact.get(field).deepCopy());
        }
        key.set("commandKey", command.get("commandKey").deepCopy());
        key.set("options", command.get("options").deepCopy());
        return key;
    }

    /** Executes only an installed store operation and separates unavailable state from empty data.
     * @param operation fixed internal operation
     * @param args server-derived arguments
     * @return authorized response data
     * @throws IOException store/protocol failure
     * @throws InterruptedException interrupted private process
     */
    private JsonNode data(String operation, JsonNode args) throws IOException, InterruptedException {
        runtime.requireReady();
        JsonNode result = gateway.request(operation, args);
        if (!result.path("status").asText().equals("OK")) throw new IOException("Document store unavailable");
        return result.path("data").deepCopy();
    }

    /** Encodes a bounded nonterminal response identity.
     * @param status response category
     * @param data authoritative or advisory payload
     * @return complete envelope bytes
     * @throws IOException output limit exceeded
     */
    private byte[] reply(String status, JsonNode data) throws IOException {
        return DocumentReplies.encode(UUID.randomUUID().toString(), status, data);
    }
}
