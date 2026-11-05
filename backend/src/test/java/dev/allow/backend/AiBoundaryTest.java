package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.springframework.mock.web.MockHttpServletRequest;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Closed DTO, mode, exact consent and bounded draft-receipt boundary cases. */
class AiBoundaryTest {
    /** Unknown fields, fractional identities and malformed Unicode cannot become authority.
     * @throws IOException fixture serialization failure
     */
    @Test
    void rejectsUnknownAndUnsafeCreateFields() throws IOException {
        ObjectNode value = create();
        value.put("owner", "other");
        assertThrows(IllegalArgumentException.class, new Parse(JsonWire.encode(value)));
        value = create();
        value.put("draftEpoch", 1.5);
        assertThrows(IllegalArgumentException.class, new Parse(JsonWire.encode(value)));
        value = create();
        value.put("sourceHash", "forged");
        assertThrows(AiFailure.class, new Parse(JsonWire.encode(value)));
        assertThrows(IllegalArgumentException.class, new Parse("{\"requestId\":\"a\",\"requestId\":\"b\"}".getBytes(StandardCharsets.UTF_8)));
    }

    /** A changed exact create byte sequence changes the server-computed identity.
     * @throws IOException fixture serialization failure
     */
    @Test
    void retainsExactCreateIdentity() throws IOException {
        byte[] bytes = JsonWire.encode(create());
        AiRequest request = new AiRequest(bytes);
        String original = request.hash();
        bytes[0] = '[';
        assertEquals(original, request.hash());
        AiRequest whitespace = new AiRequest((new String(JsonWire.encode(create()), StandardCharsets.UTF_8) + " ").getBytes(StandardCharsets.UTF_8));
        assertNotEquals(original, whitespace.hash());
    }

    /** OFF never requires provider credentials or admits a job.
     * @throws IOException unavailable fixture serialization
     */
    @Test
    void offAndAnonymousCannotEnableProvider() throws IOException {
        AiConfiguration off = config("OFF", new AccessMode("PRIVATE"));
        assertEquals("OFF", off.view().path("mode").asText());
        assertThrows(AiFailure.class, off::requireEnabled);
        assertThrows(IllegalArgumentException.class, this::anonymousFixture);
        assertThrows(IllegalArgumentException.class, this::unknownMode);
    }

    /** Controller routes independently reject anonymous profile and query aliases.
     * @throws IOException serialization failure
     */
    @Test
    void controllerRejectsAnonymousAndQueryWithoutServiceDispatch() throws IOException {
        AiService service = mock(AiService.class);
        AiController anonymous = new AiController(service, new AccessMode("ANONYMOUS"));
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/ai/v1/config");
        assertThrows(AiFailure.class, new ConfigRoute(anonymous, request));
        request.setQueryString("alias=1");
        AiController privateController = new AiController(service, new AccessMode("PRIVATE"));
        assertThrows(AiFailure.class, new ConfigRoute(privateController, request));
        verifyNoInteractions(service);
    }

    /** Exact consent retries are inert and old attempt consent cannot approve a repair.
     * @throws IOException fixture serialization failure
     */
    @Test
    void exactConsentAndRepairRequireDistinctPayload() throws IOException {
        AiJob job = new AiJob(new AiRequest(JsonWire.encode(create())), "launch");
        job.preview(preview(job, 1, "{\"attempt\":1}"));
        ObjectNode consent = disclosure(job, 1, "{\"attempt\":1}");
        job.consent(consent, "terms");
        job.consent(consent, "terms");
        job.preview(preview(job, 2, "{\"attempt\":2}"));
        assertThrows(AiFailure.class, new Consent(job, consent));
        assertEquals("AWAITING_DISCLOSURE", job.view("terms").path("status").asText());
        assertNull(job.view("terms").path("proposal").textValue());
    }

    /** Receipts are exact, idempotent and short, with no accepted-state mutation.
     * @throws IOException fixture serialization failure
     */
    @Test
    void receiptReplayNeverExtendsExpiryAndCancellationDeniesApply() throws IOException {
        AiJob job = new AiJob(new AiRequest(JsonWire.encode(create())), "launch");
        ObjectNode proposal = JsonNodeFactory.instance.objectNode().put("source", "sig S {}").put("sourceHash", Hashes.text("sig S {}"))
                .put("proposalHash", "hash");
        job.complete(proposal, "REVIEW_READY");
        assertEquals("sig S {}", job.approvable("hash"));
        ObjectNode receipt = job.issueReceipt();
        assertEquals(receipt, job.issueReceipt());
        assertTrue(receipt.path("expiresAt").longValue() <= System.currentTimeMillis() + 10000);
        job.stop("CANCELLED");
        assertThrows(AiFailure.class, job::issueReceipt);
    }

    /** Expiry and post-drain cancellation erase content even without a new create request.
     * @throws IOException fixture serialization failure
     * @throws InterruptedException controlled fixture delay
     */
    @Test
    void expiryAndCancellationScrubRetainedContent() throws IOException, InterruptedException {
        AiJob expired = new AiJob(new AiRequest(JsonWire.encode(create())), "launch", 1);
        expired.drained();
        Thread.sleep(5);
        JsonNode view = expired.view("terms");
        assertEquals("EXPIRED", view.path("status").asText());
        assertTrue(view.path("payload").isNull());
        assertTrue(view.path("beforeSource").isNull());
        assertTrue(view.path("proposal").isNull());
        assertThrows(AiFailure.class, expired::request);
        AiJob cancelled = new AiJob(new AiRequest(JsonWire.encode(create())), "launch");
        cancelled.preview(preview(cancelled, 1, "{\"attempt\":1}"));
        cancelled.stop("CANCELLED");
        assertTrue(cancelled.view("terms").path("payload").isNull());
        cancelled.drained();
        assertThrows(AiFailure.class, cancelled::request);
        assertEquals(0, cancelled.requestSize());
    }

    /** Cancellation retains approval ownership until its real cleanup owner has returned.
     * @throws IOException fixture serialization failure
     * @throws InterruptedException controlled owner synchronization
     */
    @Test
    void cancellationDrainsApprovalWorkerOwnership() throws IOException, InterruptedException {
        AiJob job = new AiJob(new AiRequest(JsonWire.encode(create())), "launch");
        job.drained();
        java.util.concurrent.CountDownLatch ready = new java.util.concurrent.CountDownLatch(1);
        java.util.concurrent.CountDownLatch interrupted = new java.util.concurrent.CountDownLatch(1);
        java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
        Thread owner = new Thread(new ApprovalOwner(job, ready, interrupted, release));
        owner.start();
        assertTrue(ready.await(2, java.util.concurrent.TimeUnit.SECONDS));
        job.stop("CANCELLED");
        assertTrue(interrupted.await(2, java.util.concurrent.TimeUnit.SECONDS));
        assertTrue(job.requestSize() > 0);
        release.countDown();
        job.awaitDrain();
        owner.join(2000);
        assertFalse(owner.isAlive());
        assertEquals(0, job.requestSize());
    }

    /** Manual operations cancel before ordinary validator admission.
     * @throws IOException unavailable mock request stream
     * @throws InterruptedException interrupted mock service
     */
    @Test
    void manualValidationPreemptsAi() throws IOException, InterruptedException {
        DocumentQueries queries = mock(DocumentQueries.class);
        AiService ai = mock(AiService.class);
        DocumentController controller = new DocumentController(mock(DocumentMutations.class), queries, ai);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/documents/server:00000000-0000-4000-8000-000000000001/validate");
        request.setContent("{}".getBytes(StandardCharsets.UTF_8));
        controller.validate("server:00000000-0000-4000-8000-000000000001", request);
        org.mockito.InOrder order = inOrder(ai, queries);
        order.verify(ai).preempt("server:00000000-0000-4000-8000-000000000001");
        order.verify(queries).validate(eq("server:00000000-0000-4000-8000-000000000001"), any(byte[].class));
    }

    /** Constructs complete minimal browser create DTO.
     * @return exact closed input
     */
    private ObjectNode create() {
        ObjectNode value = JsonNodeFactory.instance.objectNode().put("requestId", "00000000-0000-4000-8000-000000000001")
                .put("documentId", "server:00000000-0000-4000-8000-000000000002").put("baseRevision", 0)
                .put("draftId", "00000000-0000-4000-8000-000000000003").put("draftEpoch", 0).put("contentGeneration", 0)
                .put("artifactId", "artifact").put("sourceHash", "a".repeat(64)).put("intent", "Repair the model").put("kind", "SOURCE_EDIT");
        value.putObject("candidate").put("mode", "SOURCE").put("source", "sig Private {}");
        return value;
    }

    /** Builds a closed prepared frame for one exact attempt.
     * @param job immutable job
     * @param attempt exact next index
     * @param payload exact ASCII provider bytes
     * @return closed preview
     */
    private ObjectNode preview(AiJob job, int attempt, String payload) {
        return JsonNodeFactory.instance.objectNode().put("binding", job.binding()).put("attempt", attempt).put("payload", payload)
                .put("payloadHash", Hashes.text(payload)).put("model", "gpt-6.1-sol");
    }

    /** Builds exact user approval for a prepared payload.
     * @param job owned job
     * @param attempt approved attempt
     * @param payload exact prepared bytes
     * @return disclosure body
     */
    private ObjectNode disclosure(AiJob job, int attempt, String payload) {
        return JsonNodeFactory.instance.objectNode().put("binding", job.binding()).put("attempt", attempt)
                .put("payloadHash", Hashes.text(payload)).put("termsVersion", "terms");
    }

    /** Creates a fixture-only closed configuration.
     * @param mode selected mode
     * @param access installation profile
     * @return checked configuration
     * @throws IOException unavailable configured credential
     */
    private AiConfiguration config(String mode, AccessMode access) throws IOException {
        return new AiConfiguration(mode, "/tmp/allow-project", "/tmp/allow-ledger/account.json", 100000, "", "", "", false, access);
    }

    /** Attempts an anonymous installation opt-in.
     * @throws IOException unavailable fixture configuration
     */
    private void anonymousFixture() throws IOException { config("FIXTURE", new AccessMode("ANONYMOUS")); }

    /** Attempts an unknown installation mode.
     * @throws IOException unavailable fixture configuration
     */
    private void unknownMode() throws IOException { config("UNKNOWN", new AccessMode("PRIVATE")); }

    /** Represents mandatory approval cleanup after an interrupt request.
     * @param job exact owner
     * @param ready ownership latch
     * @param interrupted observed stop request
     * @param release externally established cleanup completion
     */
    private record ApprovalOwner(AiJob job, java.util.concurrent.CountDownLatch ready,
            java.util.concurrent.CountDownLatch interrupted, java.util.concurrent.CountDownLatch release) implements Runnable {
        /** Holds ownership through cancellation until actual cleanup is allowed to finish. */
        @Override
        public void run() {
            job.beginApproval();
            ready.countDown();
            boolean done = false;
            while (!done) {
                try { release.await(); done = true; }
                catch (InterruptedException cancelled) { interrupted.countDown(); }
            }
            job.endApproval();
        }
    }

    /** Names a closed DTO admission operation.
     * @param bytes exact request bytes
     */
    private record Parse(byte[] bytes) implements Executable {
        /** Attempts admission. */
        @Override
        public void execute() { new AiRequest(bytes); }
    }

    /** Names a stale consent operation.
     * @param job current proposal
     * @param value stale consent
     */
    private record Consent(AiJob job, JsonNode value) implements Executable {
        /** Attempts exact approval. */
        @Override
        public void execute() { job.consent(value, "terms"); }
    }

    /** Names a guarded controller request.
     * @param controller guarded controller
     * @param request original route
     */
    private record ConfigRoute(AiController controller, MockHttpServletRequest request) implements Executable {
        /** Attempts guarded config read.
         * @throws IOException serialization failure
         */
        @Override
        public void execute() throws IOException { controller.config(request); }
    }
}
