package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.document.AnonymousModel;
import dev.allow.worker.Hashes;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;

/** Volatile exact-bound private proposal and owned execution lifetime. */
final class AiJob {
    private final String id = UUID.randomUUID().toString();
    private final String nonce = UUID.randomUUID().toString();
    private AiRequest request;
    private final String requestId;
    private final String requestHash;
    private final String documentId;
    private final int requestSize;
    private final String binding;
    private final long deadline;
    private final long expiresAt;
    private final CountDownLatch done = new CountDownLatch(1);
    private String status = "CREATING";
    private String code;
    private String payload;
    private String payloadHash;
    private String beforeSource;
    private int attempt;
    private boolean consented;
    private boolean stopped;
    private Process process;
    private Thread runner;
    private Thread approvalOwner;
    private volatile CountDownLatch approvalDone = new CountDownLatch(0);
    private AnonymousModel anonymous;
    private String verifiedAnonymous;
    private String verifiedNamed;
    private ObjectNode proposal;
    private ObjectNode receipt;

    /** Freezes original bytes and fresh launch authority without retaining bearer values.
     * @param request exact bounded create input
     * @param installation fresh server launch and configuration binding
     */
    AiJob(AiRequest request, String installation) { this(request, installation, 60000); }

    /** Supports deterministic shorter expiry fixtures without extending production lifetime.
     * @param request exact create
     * @param installation launch/configuration identity
     * @param lifetimeMillis bounded private test lifetime
     * @throws IllegalArgumentException invalid longer or nonpositive lifetime
     */
    AiJob(AiRequest request, String installation, long lifetimeMillis) {
        if (lifetimeMillis <= 0 || lifetimeMillis > 60000) throw new IllegalArgumentException("Invalid job lifetime");
        deadline = System.nanoTime() + lifetimeMillis * 1_000_000;
        expiresAt = System.currentTimeMillis() + lifetimeMillis;
        this.request = request;
        requestId = request.text("requestId");
        requestHash = request.hash();
        documentId = request.text("documentId");
        requestSize = request.size();
        binding = Hashes.text(installation + ":" + request.hash());
    }

    /** Returns opaque job identity.
     * @return canonical UUID
     */
    String id() { return id; }

    /** Returns the private IPC request nonce.
     * @return unpredictable request nonce
     */
    String nonce() { return nonce; }

    /** Returns exact immutable browser and server binding.
     * @return binding digest
     */
    String binding() { return binding; }

    /** Supplies the closed immutable create input.
     * @return retained request
     * @throws AiFailure content already expired or cancelled
     */
    synchronized AiRequest request() {
        if (request == null) throw new AiFailure(code == null ? "EXPIRED" : code);
        return request;
    }

    /** Returns noncontent exact-create retry identity.
     * @return original UUID key
     */
    String requestId() { return requestId; }

    /** Returns original byte equality token after payload deletion.
     * @return exact create hash
     */
    String requestHash() { return requestHash; }

    /** Returns only the affected document handle for cancellation routing.
     * @return opaque document identity
     */
    String documentId() { return documentId; }

    /** Returns the retained logical content reservation.
     * @return conservative original input size, or zero after scrubbing
     */
    synchronized int requestSize() { return request == null ? 0 : requestSize; }

    /** Checks deadline and explicit cancellation before any authority-bearing action.
     * @return bounded positive remaining milliseconds
     * @throws AiFailure denied or malformed boundary state
     */
    synchronized long remaining() {
        if (stopped) throw new AiFailure(code == null ? "CANCELLED" : code);
        long millis = (deadline - System.nanoTime()) / 1_000_000;
        if (millis <= 0) throw new AiFailure("EXPIRED");
        return millis;
    }

    /** Binds actual owned processes and the synchronous driver before publication.
     * @param process owned child or null before launch
     */
    synchronized void attach(Process process) {
        this.process = process;
        runner = Thread.currentThread();
        if (stopped && process != null) process.destroyForcibly();
    }

    /** Retains local inverse names and the exact independently checked initial source.
     * @param anonymous local structural mapping
     * @param before checked source for review only
     */
    synchronized void preparedModel(AnonymousModel anonymous, String before) {
        remaining();
        this.anonymous = anonymous;
        beforeSource = before;
    }

    /** Returns only anonymous checked input for the provider process.
     * @return freshly printed anonymous source
     */
    synchronized String anonymousSource() { return anonymous.source(); }

    /** Restores names under the exact original slot inventory.
     * @param module independently checked anonymous proposed module
     * @return named candidate requiring new independent validation
     */
    synchronized String restore(JsonNode module) { remaining(); return anonymous.restore(module); }

    /** Publishes the exact next attempt for explicit browser consent.
     * @param data closed bridge prepared request
     * @throws AiFailure denied or malformed boundary state
     */
    synchronized void preview(JsonNode data) {
        remaining();
        DocumentJson.fields(data, "binding", "attempt", "payload", "payloadHash", "model");
        int next = data.path("attempt").intValue();
        if (!data.path("attempt").isInt() || next != attempt + 1 || next > 2
                || !binding.equals(data.path("binding").asText()) || !data.path("model").asText().equals("gpt-6.1-sol")
                || !data.path("payload").isTextual()) throw new AiFailure("IPC_INVALID");
        String exact = data.path("payload").textValue();
        if (exact.length() > 4096 || !StandardCharsets.US_ASCII.newEncoder().canEncode(exact)
                || !Hashes.text(exact).equals(data.path("payloadHash").asText())) throw new AiFailure("IPC_INVALID");
        payload = exact;
        payloadHash = Hashes.text(exact);
        attempt = next;
        consented = false;
        status = "AWAITING_DISCLOSURE";
    }

    /** Confirms only the current exact disclosed bytes; duplicate confirmation is inert.
     * @param data closed disclosure identity
     * @param terms current operator terms
     * @throws AiFailure denied or malformed boundary state
     */
    synchronized void consent(JsonNode data, String terms) {
        remaining();
        DocumentJson.fields(data, "binding", "attempt", "payloadHash", "termsVersion");
        if (!binding.equals(data.path("binding").asText()) || !data.path("attempt").isInt()
                || data.path("attempt").intValue() != attempt || payloadHash == null
                || !payloadHash.equals(data.path("payloadHash").asText()) || !terms.equals(data.path("termsVersion").asText())) {
            throw new AiFailure("STALE_INPUT");
        }
        consented = true;
        notifyAll();
    }

    /** Waits without worker or SQL ownership for this attempt's explicit approval.
     * @return true only for current exact consent
     * @throws InterruptedException cancellation of the owned driver
     */
    synchronized boolean awaitConsent() throws InterruptedException {
        while (!consented) wait(remaining());
        remaining();
        status = "GENERATING";
        return true;
    }

    /** Records an independently validated source pair for final-result correspondence.
     * @param source exact anonymous source
     * @param named independently checked restored source
     */
    synchronized void verified(String source, String named) {
        remaining();
        verifiedAnonymous = source;
        verifiedNamed = named;
        status = "VERIFYING";
    }

    /** Requires the final source to equal the independently verified anonymous candidate.
     * @param source final model source
     * @return corresponding validated named source
     * @throws AiFailure denied or malformed boundary state
     */
    synchronized String namedResult(String source) {
        remaining();
        if (verifiedAnonymous == null || !verifiedAnonymous.equals(source)) throw new AiFailure("INVALID_PROPOSAL");
        return verifiedNamed;
    }

    /** Installs only the independently checked terminal proposal.
     * @param proposal source edit or explanation proposal
     * @param status REVIEW_READY or SUGGESTION
     */
    synchronized void complete(ObjectNode proposal, String status) {
        remaining();
        this.proposal = proposal.deepCopy();
        this.status = status;
    }

    /** Retains a sanitized failure while preventing all later publication.
     * @param code closed terminal category
     */
    synchronized void fail(String code) {
        if (!stopped) { this.code = code; status = code.equals("EXPIRED") ? "EXPIRED" : "FAILED"; }
        stopped = true;
        if (done.getCount() == 0 && approvalDone.getCount() == 0) scrub();
        notifyAll();
    }

    /** Cancels publication and requests stop without claiming that cleanup has finished.
     * @param reason CANCELLED, STALE_INPUT or EXPIRED
     */
    synchronized void stop(String reason) {
        stopped = true;
        code = reason;
        status = reason.equals("EXPIRED") ? "EXPIRED" : "CANCELLED";
        if (process != null && process.isAlive()) process.destroyForcibly();
        if (runner != null && done.getCount() != 0) runner.interrupt();
        if (approvalOwner != null) approvalOwner.interrupt();
        if (done.getCount() == 0 && approvalDone.getCount() == 0) scrub();
        notifyAll();
    }

    /** Marks observed execution cleanup and drops the runner/process references. */
    synchronized void drained() {
        process = null;
        runner = null;
        done.countDown();
        if (stopped && approvalDone.getCount() == 0) scrub();
        notifyAll();
    }

    /** Drops every retained content buffer after owned execution can no longer use it. */
    private void scrub() {
        request = null;
        anonymous = null;
        payload = null;
        payloadHash = null;
        beforeSource = null;
        verifiedAnonymous = null;
        verifiedNamed = null;
        proposal = null;
        receipt = null;
    }

    /** Waits for the original owner to finish cleanup, preserving interruption afterwards. */
    void awaitDrain() {
        boolean interrupted = false;
        while (done.getCount() != 0 || approvalDone.getCount() != 0) {
            try { done.await(); approvalDone.await(); }
            catch (InterruptedException ignored) { interrupted = true; }
        }
        if (interrupted) Thread.currentThread().interrupt();
    }

    /** Identifies a known stopped outcome without erasing its original safe failure.
     * @return whether execution or capability already terminated
     */
    synchronized boolean stopped() { return stopped; }

    /** Tests retained lifetime without resurrecting a stopped capability.
     * @return whether the volatile record has expired
     */
    boolean expired() { return System.nanoTime() - deadline >= 0; }

    /** Takes ownership of an approval validator even after the graph has drained.
     * @throws AiFailure stale or overlapping approval
     */
    synchronized void beginApproval() {
        remaining();
        if (approvalDone.getCount() != 0) throw new AiFailure("BUSY");
        approvalDone = new CountDownLatch(1);
        approvalOwner = Thread.currentThread();
    }

    /** Releases approval ownership only after its existing worker/context cleanup returns. */
    synchronized void endApproval() {
        approvalOwner = null;
        approvalDone.countDown();
        if (stopped && done.getCount() == 0) scrub();
        notifyAll();
    }

    /** Reads only a validated edit source for approval.
     * @param hash exact proposal hash
     * @return named source
     * @throws AiFailure denied or malformed boundary state
     */
    synchronized String approvable(String hash) {
        remaining();
        if (!status.equals("REVIEW_READY") || proposal == null || !proposal.path("proposalHash").asText().equals(hash)) {
            throw new AiFailure("INVALID_PROPOSAL");
        }
        return proposal.path("source").asText();
    }

    /** Returns an existing exact receipt after external current-authority checks.
     * @return defensive receipt or null
     */
    synchronized ObjectNode receipt() { return receipt == null ? null : receipt.deepCopy(); }

    /** Issues one short local-only receipt without extending any previous grant.
     * @return authenticated-response receipt
     */
    synchronized ObjectNode issueReceipt() {
        remaining();
        if (receipt == null) {
            receipt = JsonNodeFactory.instance.objectNode().put("receiptId", UUID.randomUUID().toString()).put("jobId", id)
                    .put("binding", binding).put("proposalHash", proposal.path("proposalHash").asText())
                    .put("source", proposal.path("source").asText()).put("sourceHash", proposal.path("sourceHash").asText())
                    .put("expiresAt", Math.min(expiresAt, System.currentTimeMillis() + 10000));
        }
        return receipt.deepCopy();
    }

    /** Produces a closed nonsecret scoped view with exact payload displayed inertly.
     * @param terms current terms version
     * @return defensive job view
     */
    synchronized ObjectNode view(String terms) {
        if (expired()) stop("EXPIRED");
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("id", id).put("status", status).put("binding", binding)
                .put("expiresAt", expiresAt).put("attempt", attempt).put("payload", stopped ? null : payload).put("payloadHash", stopped ? null : payloadHash)
                .put("model", "gpt-6.1-sol").put("termsVersion", terms).put("code", code).put("beforeSource", stopped ? null : beforeSource);
        result.set("proposal", stopped || proposal == null ? JsonNodeFactory.instance.nullNode() : proposal.deepCopy());
        return result;
    }
}
