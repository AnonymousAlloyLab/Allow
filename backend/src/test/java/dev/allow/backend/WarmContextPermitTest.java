package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.mockito.ArgumentCaptor;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Finite tests of the trusted context adapter and exact single-use operation binding. */
class WarmContextPermitTest {
    private static final String FIRST = "a3fd8aa2-9632-417b-944f-9029e725d92e";
    private static final String SECOND = "00000000-0000-0000-0000-000000000002";
    private static final String DOCUMENT = "server:" + FIRST;
    private static final String HASH = "a".repeat(64);

    /** Exact successful context uses the candidate deadline and is consumed once.
     * @throws Exception failed controlled gateway fixture
     */
    @Test
    void readsAndConsumesExactContextOnce() throws Exception {
        DocumentGateway gateway = gateway(envelope());
        WarmRequestBinding binding = binding();
        WarmDeadline deadline = new WarmDeadline(1000);
        WarmContextPermit permit = WarmContextPermit.read(gateway, binding, MissingNode.getInstance(), deadline);
        ArgumentCaptor<JsonNode> arguments = ArgumentCaptor.forClass(JsonNode.class);
        verify(gateway).request(eq("validationContext"), arguments.capture(), same(deadline));
        assertEquals(DOCUMENT, arguments.getValue().path("documentId").asText());
        assertEquals(0, arguments.getValue().path("revision").longValue());
        assertTrue(arguments.getValue().path("ids").isEmpty());
        assertEquals("", permit.consume(binding).artifact().path("source").textValue());
        assertThrows(IOException.class, new Consume(permit, binding));
        verifyNoMoreInteractions(gateway);
    }

    /** Every operation identity component is checked before a context can be consumed.
     * @throws Exception failed controlled gateway fixture
     */
    @Test
    void rejectsEverySubstitutedBindingComponent() throws Exception {
        WarmRequestBinding expected = binding();
        List<WarmRequestBinding> changed = List.of(
                new WarmRequestBinding(SECOND, HASH, DOCUMENT, 0, "policy", HASH, FIRST),
                new WarmRequestBinding(FIRST, "b".repeat(64), DOCUMENT, 0, "policy", HASH, FIRST),
                new WarmRequestBinding(FIRST, HASH, "server:" + SECOND, 0, "policy", HASH, FIRST),
                new WarmRequestBinding(FIRST, HASH, DOCUMENT, 1, "policy", HASH, FIRST),
                new WarmRequestBinding(FIRST, HASH, DOCUMENT, 0, "other-policy", HASH, FIRST),
                new WarmRequestBinding(FIRST, HASH, DOCUMENT, 0, "policy", "b".repeat(64), FIRST),
                new WarmRequestBinding(FIRST, HASH, DOCUMENT, 0, "policy", HASH, SECOND));
        WarmContextPermit permit = WarmContextPermit.read(gateway(envelope()), expected,
                MissingNode.getInstance(), new WarmDeadline(1000));
        for (WarmRequestBinding value : changed) assertThrows(IOException.class, new Consume(permit, value));
        assertNotNull(permit.consume(expected));
        assertThrows(IOException.class, new Consume(permit, expected));
    }

    /** Failed, substituted and malformed private contexts cannot produce a permit.
     * @throws Exception failed controlled gateway fixture
     */
    @Test
    void rejectsFailedAndSubstitutedContext() throws Exception {
        ObjectNode wrongDocument = envelope();
        ((ObjectNode) wrongDocument.path("data")).put("documentId", "server:" + SECOND);
        ObjectNode wrongRevision = envelope();
        ((ObjectNode) wrongRevision.path("data")).put("baseRevision", 1);
        ObjectNode forgedAuthority = envelope();
        ((ObjectNode) forgedAuthority.path("data")).put("successPermitted", true);
        for (ObjectNode result : List.of(envelope().put("status", "UNAVAILABLE"), wrongDocument,
                wrongRevision, forgedAuthority)) {
            assertThrows(IOException.class, new Read(gateway(result), binding(), new WarmDeadline(1000)));
        }
    }

    /** A successful but late gateway return does not reset the admission deadline.
     * @throws Exception failed controlled gateway fixture
     */
    @Test
    void rejectsContextReturnedAfterDeadline() throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        when(gateway.request(eq("validationContext"), any(JsonNode.class), any(WarmDeadline.class)))
                .thenAnswer(new DelayedContext(envelope(), 60));
        assertThrows(IOException.class, new Read(gateway, binding(), new WarmDeadline(20)));
    }

    /** Cancelled admission never asks the gateway to resolve private context.
     * @throws Exception failed controlled gateway fixture
     */
    @Test
    void interruptionPreventsContextRead() throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        Thread.currentThread().interrupt();
        try {
            assertThrows(InterruptedException.class, new Read(gateway, binding(), new WarmDeadline(1000)));
        } finally { Thread.interrupted(); }
        verifyNoInteractions(gateway);
    }

    /** Canonical identity, safe revisions and complete hashes are required at construction. */
    @Test
    void rejectsMalformedBindingAtConstruction() {
        for (String value : List.of("1-1-1-1-1", FIRST.toUpperCase(), "bad", "")) {
            assertThrows(IllegalArgumentException.class, new Construct(value, HASH, DOCUMENT, 0, "policy", HASH, FIRST));
            assertThrows(IllegalArgumentException.class, new Construct(FIRST, HASH, DOCUMENT, 0, "policy", HASH, value));
        }
        for (String value : List.of("", "server:1-1-1-1-1", "server:" + FIRST.toUpperCase(), FIRST)) {
            assertThrows(IllegalArgumentException.class, new Construct(FIRST, HASH, value, 0, "policy", HASH, FIRST));
        }
        for (long revision : new long[]{-1, 9007199254740992L}) {
            assertThrows(IllegalArgumentException.class, new Construct(FIRST, HASH, DOCUMENT, revision, "policy", HASH, FIRST));
        }
        assertThrows(IllegalArgumentException.class, new Construct(FIRST, HASH, DOCUMENT, 0, " ", HASH, FIRST));
        assertThrows(IllegalArgumentException.class, new Construct(FIRST, "bad", DOCUMENT, 0, "policy", HASH, FIRST));
        assertThrows(IllegalArgumentException.class, new Construct(FIRST, HASH, DOCUMENT, 0, "policy", "A".repeat(64), FIRST));
        assertNotNull(new WarmRequestBinding(FIRST, HASH, DOCUMENT, 9007199254740991L, "policy", HASH, FIRST));
    }

    /** Provides one canonical fixed server admission identity.
     * @return immutable operation binding
     */
    private static WarmRequestBinding binding() {
        return new WarmRequestBinding(FIRST, HASH, DOCUMENT, 0, "policy", HASH, FIRST);
    }

    /** Creates the existing closed context shape without inventing a Java cleanup authority flag.
     * @return private fixture envelope
     * @throws IOException fixture artifact encoding failure
     */
    private static ObjectNode envelope() throws IOException {
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("documentId", DOCUMENT)
                .put("baseRevision", 0).put("headObserved", 0);
        data.set("artifact", DocumentArtifacts.empty("policy", HASH));
        data.putObject("ownedIdInventory");
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("status", "OK");
        result.set("data", data);
        return result;
    }

    /** Supplies controlled private gateway output after the existing response decoder boundary.
     * @param response closed fixture result
     * @return mocked operation-only gateway
     * @throws Exception failed mock setup
     */
    private static DocumentGateway gateway(ObjectNode response) throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        when(gateway.request(eq("validationContext"), any(JsonNode.class), any(WarmDeadline.class))).thenReturn(response);
        return gateway;
    }

    /** Carries a checked permit read into a failure assertion. */
    private record Read(DocumentGateway gateway, WarmRequestBinding binding, WarmDeadline deadline) implements Executable {
        /** Performs the actual context validation and post-return deadline check.
         * @throws IOException expected unavailable context
         * @throws InterruptedException expected cancelled operation
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            WarmContextPermit.read(gateway, binding, MissingNode.getInstance(), deadline);
        }
    }

    /** Carries one exact or substituted permit consumption into an assertion. */
    private record Consume(WarmContextPermit permit, WarmRequestBinding binding) implements Executable {
        /** Exercises the actual single-use identity check.
         * @throws IOException substituted or already consumed context
         */
        @Override
        public void execute() throws IOException { permit.consume(binding); }
    }

    /** Carries malformed immutable identity fields into the real constructor. */
    private record Construct(String nonce, String hash, String document, long revision,
            String policy, String build, String pool) implements Executable {
        /** Constructs one candidate identity, expecting malformed fields to be rejected. */
        @Override
        public void execute() { new WarmRequestBinding(nonce, hash, document, revision, policy, build, pool); }
    }

    /** Simulates a private adapter returning only after its original budget has expired. */
    private record DelayedContext(JsonNode envelope, long delay) implements Answer<JsonNode> {
        /** Delays the existing checked context result without changing the supplied deadline.
         * @param invocation controlled mock invocation
         * @return delayed private result
         * @throws InterruptedException cancelled delay
         */
        @Override
        public JsonNode answer(InvocationOnMock invocation) throws InterruptedException {
            Thread.sleep(delay);
            return envelope;
        }
    }
}
