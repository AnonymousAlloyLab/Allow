package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.document.AnonymousModel;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Service;

/** Private bounded AI authority, draft-only publication and existing validator integration. */
@Service
final class AiService {
    private final AiConfiguration configuration;
    private final DocumentQueries queries;
    private final DocumentRuntime runtime;
    private final String incarnation = UUID.randomUUID().toString();
    private final Map<String, AiJob> jobs = new LinkedHashMap<>();
    private final ExecutorService executor = Executors.newSingleThreadExecutor(AiService::driverThread);
    private final ScheduledThreadPoolExecutor deadlines = new ScheduledThreadPoolExecutor(1, AiService::deadlineThread);
    private AiJob active;
    private boolean cleanupSafe = true;
    private boolean closed;

    /** Retains trusted installation services without any browser-selected scope.
     * @param configuration closed private provider configuration
     * @param queries private scoped document service
     * @param runtime installed policy and build ownership
     */
    AiService(AiConfiguration configuration, DocumentQueries queries, DocumentRuntime runtime) {
        this.configuration = configuration;
        this.queries = queries;
        this.runtime = runtime;
        deadlines.setRemoveOnCancelPolicy(true);
    }

    /** Returns nonsecret authenticated private configuration.
     * @return closed config value
     */
    ObjectNode config() { return configuration.view(); }

    /** Admits one bounded job or returns the retained original exact-byte retry.
     * @param bytes original bounded strict create bytes
     * @return scoped volatile view
     * @throws AiFailure denied or malformed boundary state
     */
    synchronized ObjectNode create(byte[] bytes) {
        configuration.requireEnabled();
        AiRequest request = new AiRequest(bytes);
        prune();
        for (AiJob job : jobs.values()) {
            if (job.requestId().equals(request.text("requestId"))) {
                if (!job.requestHash().equals(request.hash())) throw new AiFailure("REQUEST_CONFLICT");
                return job.view(terms());
            }
        }
        if (closed || !cleanupSafe || active != null || jobs.size() >= 3 || retainedSize() + bytes.length * 3L + 196608 > 1048576) {
            throw new AiFailure("BUSY");
        }
        AiJob job = new AiJob(request, incarnation + ":" + configuration.binding() + ":" + runtime.policy());
        jobs.put(job.id(), job);
        active = job;
        executor.execute(this::drive);
        return job.view(terms());
    }

    /** Removes only expired inactive volatile buffers, never accounting records. */
    private void prune() {
        Iterator<AiJob> iterator = jobs.values().iterator();
        while (iterator.hasNext()) {
            AiJob job = iterator.next();
            if (job != active && job.expired()) iterator.remove();
        }
    }

    /** Conservatively bounds retained inputs and proposal/source buffers.
     * @return estimated retained byte reservation
     */
    private long retainedSize() {
        long total = 0;
        for (AiJob job : jobs.values()) total += job.requestSize() == 0 ? 0 : job.requestSize() * 3L + 196608;
        return total;
    }

    /** Resolves a handle without disclosing nonexistent or foreign job details.
     * @param id canonical scoped opaque job
     * @return retained owned job
     * @throws AiFailure denied or malformed boundary state
     */
    private synchronized AiJob owned(String id) {
        configuration.requireEnabled();
        AiJob job = jobs.get(id);
        if (job == null) throw new AiFailure("NOT_FOUND");
        return job;
    }

    /** Reads without graph side effects and invalidates observed stale authority.
     * @param id owned job ID
     * @return closed current view
     */
    ObjectNode read(String id) {
        AiJob job = owned(id);
        if (!job.stopped()) {
            try { current(job); }
            catch (AiFailure failure) { job.stop(failure.code().equals("EXPIRED") ? "EXPIRED" : "STALE_INPUT"); }
            catch (IOException unavailable) { job.stop("STALE_INPUT"); }
            catch (InterruptedException cancelled) { Thread.currentThread().interrupt(); job.stop("STALE_INPUT"); }
        }
        return job.view(terms());
    }

    /** Confirms exactly the current prepared attempt after live head checks.
     * @param id owned job
     * @param bytes exact disclosure JSON
     * @return current job state
     * @throws IOException unavailable authoritative head
     * @throws InterruptedException interrupted scoped read
     */
    ObjectNode consent(String id, byte[] bytes) throws IOException, InterruptedException {
        AiJob job = owned(id);
        current(job);
        job.consent(DocumentJson.request(bytes), terms());
        return job.view(terms());
    }

    /** Cancels and drains owned execution before acknowledging termination.
     * @param id owned job
     * @param bytes closed bound cancellation
     * @return terminal view
     */
    ObjectNode cancel(String id, byte[] bytes) {
        AiJob job = owned(id);
        bound(job, DocumentJson.request(bytes), "binding");
        job.stop("CANCELLED");
        job.awaitDrain();
        return job.view(terms());
    }

    /** Issues only a short idempotent draft receipt after ordinary fresh validation.
     * @param id owned job
     * @param bytes exact bound approval
     * @return local-only apply receipt
     * @throws IOException unavailable document or validation context
     * @throws InterruptedException interrupted owned validation
     */
    ObjectNode approve(String id, byte[] bytes) throws IOException, InterruptedException {
        AiJob job = owned(id);
        JsonNode request = DocumentJson.request(bytes);
        bound(job, request, "binding", "proposalHash");
        current(job);
        String source = job.approvable(request.path("proposalHash").asText());
        ObjectNode receipt = job.receipt();
        if (receipt != null) return receipt;
        reserveApproval(job);
        try {
            JsonNode result = validate(job, sourceCandidate(source));
            requireSupported(result);
            current(job);
            return job.issueReceipt();
        } finally {
            job.endApproval();
            synchronized (this) { cleanupSafe &= queries.cleanupSafe(); active = null; }
        }
    }

    /** Reserves the same private global lane for approval validation and cancellation.
     * @param job exact proposal owner
     * @throws AiFailure concurrent or unsafe AI work
     */
    private synchronized void reserveApproval(AiJob job) {
        if (closed || active != null || !cleanupSafe) throw new AiFailure("BUSY");
        job.beginApproval();
        active = job;
    }

    /** Rejects any client-chosen authority or mismatched immutable binding.
     * @param job owned record
     * @param request strict request object
     * @param fields complete allowed keys
     * @throws AiFailure denied or malformed boundary state
     */
    private void bound(AiJob job, JsonNode request, String... fields) {
        DocumentJson.fields(request, fields);
        if (!request.path("binding").isTextual() || !job.binding().equals(request.path("binding").textValue())) {
            throw new AiFailure("STALE_INPUT");
        }
    }

    /** Rechecks authoritative current document identity and installed policy.
     * @param job immutable request scope
     * @throws IOException unavailable scoped document
     * @throws InterruptedException interrupted scoped store read
     * @throws AiFailure denied or malformed boundary state
     */
    void current(AiJob job) throws IOException, InterruptedException {
        job.remaining();
        runtime.requireReady();
        JsonNode head = queries.aiHead(job.request().text("documentId"));
        JsonNode artifact = head.path("artifact");
        if (head.path("headRevision").longValue() != job.request().number("baseRevision")
                || !artifact.path("artifactId").asText().equals(job.request().text("artifactId"))
                || !artifact.path("sourceHash").asText().equals(job.request().text("sourceHash"))
                || !runtime.policy().equals(artifact.path("policyVersion").asText())
                || !runtime.dependency().equals(artifact.path("dependencyHash").asText())) throw new AiFailure("STALE_INPUT");
        job.remaining();
    }

    /** Uses the existing scoped context and single worker admission for every candidate.
     * @param job authorized request
     * @param candidate exact candidate
     * @return complete checked worker response
     * @throws IOException unavailable worker/context
     * @throws InterruptedException interrupted owned child
     */
    private JsonNode validate(AiJob job, JsonNode candidate) throws IOException, InterruptedException {
        current(job);
        JsonNode result = queries.aiValidate(job.request().text("documentId"), job.request().number("baseRevision"), candidate, job.remaining());
        current(job);
        return result;
    }

    /** Establishes complete checked input and a locally held structural inverse map.
     * @param job exact create snapshot
     * @throws IOException unavailable document or worker
     * @throws InterruptedException cancelled owned operation
     */
    private void prepare(AiJob job) throws IOException, InterruptedException {
        JsonNode checked = requireSupported(validate(job, job.request().candidate()));
        AnonymousModel anonymous = new AnonymousModel(checked.path("module"));
        requireSupported(validate(job, sourceCandidate(anonymous.source())));
        job.preparedModel(anonymous, checked.path("source").asText());
    }

    /** Verifies anonymous output, restores its inventory and independently checks named bytes.
     * @param job owned request
     * @param source exact anonymous generated source
     * @return closed trusted observation with anonymous exact source identity
     * @throws IOException unavailable scoped worker
     * @throws InterruptedException cancelled owned work
     */
    ObjectNode verify(AiJob job, String source) throws IOException, InterruptedException {
        JsonNode result = validate(job, sourceCandidate(source));
        if (!result.path("status").asText().equals("VALIDATED")) return invalid(result);
        try {
            String named = job.restore(requireSupported(result).path("module"));
            JsonNode checked = requireSupported(validate(job, sourceCandidate(named)));
            job.verified(source, checked.path("source").asText());
            ObjectNode observation = JsonNodeFactory.instance.objectNode().put("status", "VALIDATED").putNull("code")
                    .put("projection", "BLOCK_SUPPORTED").put("source_hash", Hashes.text(source));
            observation.putObject("evidence").put("policy", runtime.policy()).put("dependency", runtime.dependency());
            return observation;
        } catch (AiFailure unsupported) {
            if (!unsupported.code().equals("UNSUPPORTED_PROFILE")) throw unsupported;
            return invalidCode("SOURCE_PROFILE_INVALID");
        } catch (IllegalArgumentException unsupported) { return invalidCode("SOURCE_PROFILE_INVALID"); }
    }

    /** Requires the narrowed complete supported profile without relabeling text-only output.
     * @param result trusted worker envelope
     * @return checked data
     * @throws AiFailure denied or malformed boundary state
     */
    private JsonNode requireSupported(JsonNode result) {
        if (!result.path("status").asText().equals("VALIDATED") || !result.path("data").path("mode").asText().equals("BLOCK_SUPPORTED")
                || !result.path("data").path("module").isObject()) throw new AiFailure("UNSUPPORTED_PROFILE");
        return result.path("data");
    }

    /** Converts only deterministic worker denials to closed repair categories.
     * @param result trusted worker response
     * @return closed invalid observation
     * @throws AiFailure denied or malformed boundary state
     */
    private ObjectNode invalid(JsonNode result) {
        if (!result.path("status").asText().equals("INVALID")) throw new AiFailure("VERIFIER_UNAVAILABLE");
        String category = result.path("data").path("diagnostics").path(0).path("code").asText();
        String code = category.equals("TYPE_MISMATCH") ? "SOURCE_TYPE_INVALID" : "SOURCE_PARSE_INVALID";
        if (category.equals("UNSUPPORTED_FRAGMENT")) code = "SOURCE_PROFILE_INVALID";
        return invalidCode(code);
    }

    /** Creates only a bounded inert deterministic-failure observation.
     * @param code allowlisted diagnostic category
     * @return complete verification wire value
     */
    private ObjectNode invalidCode(String code) {
        return JsonNodeFactory.instance.objectNode().put("status", "INVALID").put("code", code).putNull("projection")
                .putNull("source_hash").putNull("evidence");
    }

    /** Builds the only supported generated-source candidate shape.
     * @param source exact bounded source
     * @return closed source candidate
     * @throws AiFailure denied or malformed boundary state
     */
    private ObjectNode sourceCandidate(String source) {
        if (source == null || source.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 32768) throw new AiFailure("INVALID_PROPOSAL");
        return JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", source);
    }

    /** Publishes only exact correspondence to the retained trusted verification result.
     * @param job owned job
     * @param result complete child terminal value
     * @throws IOException bounded serialization failure
     * @throws InterruptedException interrupted final authoritative head check
     * @throws AiFailure denied or malformed boundary state
     */
    void result(AiJob job, JsonNode result) throws IOException, InterruptedException {
        current(job);
        DocumentJson.fields(result, "status", "attempts", "binding", "source", "explanation", "verification", "code", "http_status");
        if (!result.path("binding").asText().equals(job.binding()) || !result.path("attempts").isInt()
                || result.path("attempts").intValue() < 0 || result.path("attempts").intValue() > 2) throw new AiFailure("IPC_INVALID");
        String status = result.path("status").asText();
        if (!Set.of("REVIEW_READY", "SUGGESTION").contains(status)) { job.fail(safeCode(result.path("code").asText())); return; }
        boolean explanation = job.request().text("kind").equals("EXPLANATION");
        if (explanation != status.equals("SUGGESTION") || !result.path("source").isTextual() || !result.path("explanation").isTextual()) {
            throw new AiFailure("IPC_INVALID");
        }
        String source = explanation ? "" : job.namedResult(result.path("source").textValue());
        String prose = result.path("explanation").textValue();
        if (prose.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 32768 || (explanation && !result.path("source").asText().isEmpty())) {
            throw new AiFailure("IPC_INVALID");
        }
        ObjectNode proposal = JsonNodeFactory.instance.objectNode().put("source", source).put("explanation", prose)
                .put("projection", explanation ? "AI_SUGGESTION" : "BLOCK_SUPPORTED").put("sourceHash", Hashes.text(source));
        proposal.put("proposalHash", Hashes.bytes(JsonWire.encode(proposal)));
        job.complete(proposal, status);
    }

    /** Restricts error output to fixed protocol categories, never child-provided prose.
     * @param code untrusted child failure
     * @return safe category
     */
    private String safeCode(String code) {
        return Set.of("BUDGET_EXHAUSTED", "PROVIDER_HTTP_ERROR", "PROVIDER_ENVELOPE_INVALID", "PROVIDER_USAGE_INVALID",
                "OUTCOME_UNKNOWN", "LEDGER_UNAVAILABLE", "DISPATCH_REPLAY", "INVALID_PROPOSAL", "EXPIRED", "CONSENT_REQUIRED",
                "PROVIDER_REFUSED", "PROVIDER_INCOMPLETE", "PROVIDER_RESPONSE_TOO_LARGE", "PAYLOAD_LIMIT", "STALE_INPUT",
                "VERIFIER_UNAVAILABLE", "UNSUPPORTED_PROFILE", "BUSY", "IPC_INVALID", "INVALID_REQUEST").contains(code) ? code : "UNAVAILABLE";
    }

    /** Runs the sole admitted orchestration child through cleanup and deadline ownership. */
    private void drive() {
        AiJob job;
        synchronized (this) { job = active; }
        job.attach(null);
        try {
            deadlines.schedule(new Expiry(job), Math.max(1, job.remaining()), TimeUnit.MILLISECONDS);
            prepare(job);
            new AiProcess(configuration, this, job).run();
        } catch (AiFailure failure) { job.fail(safeCode(failure.code())); }
        catch (java.util.concurrent.RejectedExecutionException busy) { job.fail("BUSY"); }
        catch (IOException | InterruptedException | RuntimeException unavailable) { job.fail("UNAVAILABLE"); }
        finally {
            synchronized (this) { cleanupSafe &= queries.cleanupSafe(); active = null; }
            job.drained();
            Thread.interrupted();
        }
    }

    /** Cancels conflicting AI work before an ordinary manual server operation enters admission.
     * @param document affected document, or null for workspace-level manual create
     */
    void preempt(String document) {
        AiJob job;
        synchronized (this) { job = active; }
        if (job != null && (document == null || job.documentId().equals(document))) {
            job.stop("CANCELLED");
            job.awaitDrain();
        }
    }

    /** Reads the configured nonsecret terms version.
     * @return exact terms version
     */
    private String terms() { return configuration.view().path("termsVersion").asText(); }

    /** Creates the single bounded driver thread.
     * @param task owned orchestration task
     * @return daemon thread
     */
    private static Thread driverThread(Runnable task) { return new Thread(task, "allow-ai-driver"); }

    /** Creates the deadline control thread without holding solver or SQL capacity.
     * @param task owned deadline task
     * @return control thread
     */
    private static Thread deadlineThread(Runnable task) { return new Thread(task, "allow-ai-deadline"); }

    /** Retains a named documented deadline callback.
     * @param job exact owned job
     */
    private record Expiry(AiJob job) implements Runnable {
        /** Stops publication and requests owned termination at the original job deadline. */
        @Override
        public void run() { job.stop("EXPIRED"); }
    }

    /** Stops and drains before releasing any installation ownership. */
    @PreDestroy
    void close() {
        synchronized (this) { closed = true; }
        preempt(null);
        executor.shutdownNow();
        deadlines.shutdownNow();
        synchronized (this) {
            for (AiJob job : jobs.values()) job.stop("CANCELLED");
            jobs.clear();
        }
    }
}
