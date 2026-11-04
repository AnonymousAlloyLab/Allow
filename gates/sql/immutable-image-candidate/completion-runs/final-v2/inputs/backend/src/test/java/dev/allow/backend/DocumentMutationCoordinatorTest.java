package dev.allow.backend;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.invocation.InvocationOnMock;

/** Coordinator regressions use a private bridge seam; real SQL storage has independent tests. */
final class DocumentMutationCoordinatorTest {
    private DocumentGateway gateway;
    private DocumentRuntime runtime;
    private DocumentWorker worker;
    private DocumentMutations mutations;
    private final List<String> calls = new ArrayList<>();
    private byte[] stored;
    private String finalizeMode;
    private String workerMode;
    private int finalizations;
    private boolean loseAdmission;

    /** Initializes isolated mocks without creating subprocesses or claiming parser acceptance.
     * @throws Exception unavailable fixture serialization
     */
    @BeforeEach
    void setup() throws Exception {
        gateway = mock(DocumentGateway.class);
        runtime = mock(DocumentRuntime.class);
        worker = mock(DocumentWorker.class);
        when(runtime.policy()).thenReturn("policy");
        when(runtime.dependency()).thenReturn("dependency");
        when(worker.identity()).thenReturn("dependency");
        when(gateway.request(anyString(), any(JsonNode.class))).thenAnswer(this::bridge);
        when(worker.validate(any(), any(), any(), anyString())).thenAnswer(this::validation);
        when(worker.recovery()).thenReturn(JsonNodeFactory.instance.objectNode().putNull("workerPid")
                .putNull("workerStartTicks").put("noWorkerStarted", true));
        mutations = new DocumentMutations(gateway, runtime, this::newWorker);
        finalizeMode = "NORMAL";
        workerMode = "UNAVAILABLE";
    }

    /** Supplies an owned fake validator without permitting real engine fallback.
     * @return isolated mock worker
     */
    private DocumentWorker newWorker() { return worker; }

    /** Dispatches closed private operations through the test bridge seam.
     * @param invocation mocked bridge invocation
     * @return fixed operation result
     * @throws IOException injected final acknowledgement loss
     */
    private JsonNode bridge(InvocationOnMock invocation) throws IOException {
        String operation = invocation.getArgument(0);
        JsonNode args = invocation.getArgument(1);
        calls.add(operation);
        ObjectNode data = JsonNodeFactory.instance.objectNode();
        if (operation.equals("receipt")) return envelope(receipt(data));
        if (operation.equals("admit") && loseAdmission) { loseAdmission = false; throw new IOException("Lost admission acknowledgement"); }
        if (operation.equals("admit") || operation.equals("recover") || operation.equals("recoverUnstarted")) {
            return envelope(data.put("status", "ADMITTED").put("nonce", UUID.randomUUID().toString())
                    .put("documentId", args.path("documentId").asText().equals("CREATE") ? "server:" + UUID.randomUUID()
                            : args.path("documentId").textValue()).put("policyVersion", "policy"));
        }
        if (operation.equals("read")) return envelope(readData());
        if (operation.equals("ownedIds")) { data.putObject("ids"); return envelope(data); }
        if (operation.equals("finalize")) return finish(args);
        throw new IOException("Unexpected private operation");
    }

    /** Produces exact receipt bytes only after the simulated transaction committed.
     * @param data mutable result fixture
     * @return private receipt result
     */
    private JsonNode receipt(ObjectNode data) {
        if (stored == null) return data.put("status", "ABSENT");
        return data.put("status", "REPLAY").put("responseBase64", Base64.getEncoder().encodeToString(stored));
    }

    /** Provides a head-zero valid empty accepted fixture without invoking Alloy.
     * @return authorized read snapshot
     * @throws IOException fixture encoding failure
     */
    private JsonNode readData() throws IOException {
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("headRevision", 0).put("requestedRevision", 0);
        data.set("artifact", DocumentArtifacts.empty("policy", "dependency"));
        return data;
    }

    /** Injects one stale race, known rollback or post-commit acknowledgement loss.
     * @param args complete private final frame
     * @return simulated transaction result
     * @throws IOException lost acknowledgement after recording exact bytes
     * @throws IllegalArgumentException injected strict decoder failure
     */
    private JsonNode finish(JsonNode args) throws IOException {
        finalizations++;
        if (finalizeMode.equals("MALFORMED")) throw new IllegalArgumentException("Malformed final bridge fields");
        if (finalizeMode.equals("STALE") && finalizations == 1) {
            return envelope(JsonNodeFactory.instance.objectNode().put("status", "STALE_REVISION").put("acceptedRevision", 1));
        }
        if (finalizeMode.equals("KNOWN")) return DocumentJson.envelope(UUID.randomUUID().toString(), "KNOWN_ROLLBACK",
                JsonNodeFactory.instance.objectNode());
        stored = Base64.getDecoder().decode(args.path("outcomeBase64").textValue());
        if (finalizeMode.equals("LOST")) throw new IOException("Lost final acknowledgement");
        return envelope(JsonNodeFactory.instance.objectNode().put("status", args.path("result").textValue())
                .put("responseBase64", Base64.getEncoder().encodeToString(stored)));
    }

    /** Returns complete invalid or unavailable validator fixtures, never a stub success.
     * @param invocation mocked validator call
     * @return private worker response
     */
    private JsonNode validation(InvocationOnMock invocation) {
        ObjectNode data = JsonNodeFactory.instance.objectNode();
        if (workerMode.equals("INVALID")) {
            data.put("code", "TYPE_MISMATCH"); data.putArray("diagnostics");
            return DocumentJson.envelope(UUID.randomUUID().toString(), "INVALID", data);
        }
        return DocumentJson.envelope(UUID.randomUUID().toString(), workerMode, data);
    }

    /** Wraps a private operation success separately from its operation status.
     * @param data internal result
     * @return private envelope
     */
    private JsonNode envelope(JsonNode data) {
        return DocumentJson.envelope(UUID.randomUUID().toString(), "OK", data);
    }

    /** Constructs one exact original create or commit request.
     * @param create true for reserved creation namespace
     * @return immutable request fixture
     * @throws IOException invalid fixture JSON
     */
    private DocumentRequest request(boolean create) throws IOException {
        String document = create ? "CREATE" : "server:11111111-1111-4111-8111-111111111111";
        ObjectNode body = JsonNodeFactory.instance.objectNode().put("idempotencyKey", "abcdefghijklmnop");
        if (create) body.put("title", "Example");
        else { body.put("expectedRevision", 0); body.putObject("candidate").put("mode", "SOURCE").put("source", ""); }
        String route = "/api/v1/documents" + (create ? "" : "/" + document + "/commit");
        return new DocumentRequest(document, route, create ? "CREATE" : "COMMIT", JsonWire.encode(body));
    }

    /** Proved empty creation persists exact terminal bytes and retries bypass admission.
     * @throws Exception coordinator failure
     */
    @Test
    void creationAndReceiptReplay() throws Exception {
        byte[] first = mutations.mutate(request(true));
        assertEquals("COMMITTED", DocumentJson.decode(first).path("status").textValue());
        calls.clear();
        assertEquals(new String(first, java.nio.charset.StandardCharsets.UTF_8),
                new String(mutations.mutate(request(true)), java.nio.charset.StandardCharsets.UTF_8));
        assertEquals(List.of("receipt"), calls);
    }

    /** A post-commit bridge error reports uncertainty and original exact retry recovers success.
     * @throws Exception coordinator failure
     */
    @Test
    void lostFinalAcknowledgementRecoversOriginalEnvelope() throws Exception {
        finalizeMode = "LOST";
        assertEquals("UNKNOWN_COMMIT_OUTCOME", DocumentJson.decode(mutations.mutate(request(true))).path("status").textValue());
        byte[] recovered = mutations.mutate(request(true));
        assertEquals(Base64.getEncoder().encodeToString(stored), Base64.getEncoder().encodeToString(recovered));
        assertEquals(1, finalizations);
    }

    /** Unchecked strict-decoder failure after final send cannot become a rollback claim.
     * @throws Exception coordinator failure
     */
    @Test
    void malformedFinalBridgeReplyIsUncertain() throws Exception {
        finalizeMode = "MALFORMED";
        assertEquals("UNKNOWN_COMMIT_OUTCOME", DocumentJson.decode(mutations.mutate(request(true))).path("status").textValue());
        assertEquals(1, finalizations);
    }

    /** Explicit PostgreSQL rollback is kept separate from uncertain acknowledgement loss.
     * @throws Exception coordinator failure
     */
    @Test
    void knownRollbackRemainsDistinct() throws Exception {
        finalizeMode = "KNOWN";
        assertEquals("KNOWN_ROLLBACK", DocumentJson.decode(mutations.mutate(request(true))).path("status").textValue());
    }

    /** A stale final CAS rebuilds one rejection using the actual store-observed head.
     * @throws Exception coordinator failure
     */
    @Test
    void staleRaceBecomesDurableRejection() throws Exception {
        finalizeMode = "STALE";
        workerMode = "INVALID";
        JsonNode response = DocumentJson.decode(mutations.mutate(request(false)));
        assertEquals("REJECTED", response.path("status").textValue());
        assertEquals("STALE_REVISION", response.path("data").path("code").textValue());
        assertEquals(1, response.path("data").path("acceptedRevision").longValue());
        assertEquals(2, finalizations);
    }

    /** A completed unavailable validator is recoverable but never creates accepted history.
     * @throws Exception coordinator failure
     */
    @Test
    void unavailableValidatorRetainsReapedAttemptForRecovery() throws Exception {
        assertThrows(IOException.class, this::unavailableMutation);
        assertEquals(0, finalizations);
        calls.clear();
        assertThrows(IOException.class, this::unavailableMutation);
        assertTrue(calls.contains("recover"));
        assertTrue(!calls.contains("admit"));
    }

    /** Calls the same exact unavailable commit from a documented assertion callback.
     * @throws Exception truthful worker availability error
     */
    private void unavailableMutation() throws Exception { mutations.mutate(request(false)); }

    /** Changed installed worker bytes cannot enter admission but cannot block stored replay.
     * @throws Exception coordinator failure
     */
    @Test
    void changedWorkerBuildBlocksNewAdmissionButNotReplay() throws Exception {
        when(worker.identity()).thenReturn("changed-dependency");
        assertThrows(IOException.class, this::createMutation);
        assertEquals(List.of("receipt"), calls);
        stored = DocumentReplies.encode(UUID.randomUUID().toString(), "COMMITTED", JsonNodeFactory.instance.objectNode());
        calls.clear();
        assertEquals(Base64.getEncoder().encodeToString(stored), Base64.getEncoder().encodeToString(mutations.mutate(request(true))));
        assertEquals(List.of("receipt"), calls);
    }

    /** Calls creation through a documented assertion callback.
     * @throws Exception coordinator rejection of changed build
     */
    private void createMutation() throws Exception { mutations.mutate(request(true)); }

    /** Lost admission acknowledgement recovers no-start provenance and validates exactly once.
     * @throws Exception coordinator failure
     */
    @Test
    void lostAdmissionAcknowledgementRecoversBeforeWorkerStarts() throws Exception {
        loseAdmission = true;
        workerMode = "INVALID";
        assertThrows(IOException.class, this::unavailableMutation);
        org.mockito.Mockito.verify(worker, org.mockito.Mockito.never()).validate(any(), any(), any(), anyString());
        calls.clear();
        assertEquals("REJECTED", DocumentJson.decode(mutations.mutate(request(false))).path("status").textValue());
        assertTrue(calls.contains("recoverUnstarted"));
        org.mockito.Mockito.verify(worker, org.mockito.Mockito.times(1)).validate(any(), any(), any(), anyString());
    }

    /** Complete deterministic worker diagnostics are stored as exact rejected receipts.
     * @throws Exception coordinator failure
     */
    @Test
    void deterministicInvalidityGetsReceipt() throws Exception {
        workerMode = "INVALID";
        JsonNode response = DocumentJson.decode(mutations.mutate(request(false)));
        assertEquals("REJECTED", response.path("status").textValue());
        assertEquals("TYPE_MISMATCH", response.path("data").path("code").textValue());
        assertEquals(1, finalizations);
    }

    /** Missing diagnostic fields fail as availability rather than invented INVALID_DRAFT.
     * @throws Exception coordinator failure
     */
    @Test
    void malformedWorkerCannotCreateDenialReceipt() throws Exception {
        workerMode = "INVALID_MALFORMED";
        assertThrows(IOException.class, this::unavailableMutation);
        assertEquals(0, finalizations);
    }
}
