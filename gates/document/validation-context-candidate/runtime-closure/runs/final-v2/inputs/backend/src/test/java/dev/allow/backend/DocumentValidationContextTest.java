package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedConstruction;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Private context boundaries, mandatory authorization and pre-worker denial fixtures. */
class DocumentValidationContextTest {
    private static final String DOCUMENT = "server:00000000-0000-0000-0000-000000000001";
    private static final String FIRST = "server:00000000-0000-0000-0000-000000000002";
    private static final String SECOND = "server:00000000-0000-0000-0000-000000000003";

    /** Source mode still obtains a real private context rather than treating empty IDs as authority.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void missingModuleStillReadsOneContext() throws Exception {
        DocumentGateway gateway = gateway(context());
        DocumentValidationContext.read(gateway, DOCUMENT, 0, MissingNode.getInstance());
        ArgumentCaptor<JsonNode> args = ArgumentCaptor.forClass(JsonNode.class);
        verify(gateway).request(eq("validationContext"), args.capture());
        DocumentJson.fields(args.getValue(), "documentId", "revision", "ids");
        assertEquals(DOCUMENT, args.getValue().path("documentId").textValue());
        assertEquals(0, args.getValue().path("revision").longValue());
        assertTrue(args.getValue().path("ids").isEmpty());
        verifyNoMoreInteractions(gateway);
    }

    /** Traversal retains nested value references and produces sorted, unique canonical IDs.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void sortsAndDeduplicatesAllServerPrefixedValues() throws Exception {
        ArrayNode module = JsonNodeFactory.instance.arrayNode().add(SECOND).add(FIRST).add(SECOND).add("draft:one");
        module.addObject().put("reference", FIRST).put("label", "Person");
        ObjectNode result = context();
        ((ObjectNode) result.path("ownedIdInventory")).put(FIRST, "signature");
        DocumentGateway gateway = gateway(result);
        DocumentValidationContext.read(gateway, DOCUMENT, 0, module);
        ArgumentCaptor<JsonNode> args = ArgumentCaptor.forClass(JsonNode.class);
        verify(gateway).request(eq("validationContext"), args.capture());
        assertEquals(JsonNodeFactory.instance.arrayNode().add(FIRST).add(SECOND), args.getValue().path("ids"));
    }

    /** Returned state never aliases the gateway response or a caller's mutable node.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void retainsExactSourceAndDefensiveCopies() throws Exception {
        ObjectNode result = context();
        ((ObjectNode) result.path("artifact")).put("source", "sig Person {}\r\n// \ud83d\ude80");
        ((ObjectNode) result.path("ownedIdInventory")).put(FIRST, "signature");
        DocumentValidationContext value = DocumentValidationContext.read(gateway(result), DOCUMENT, 0,
                JsonNodeFactory.instance.arrayNode().add(FIRST));
        ((ObjectNode) result.path("artifact")).put("source", "changed");
        ((ObjectNode) value.artifact()).put("source", "changed again");
        ((ObjectNode) value.inventory()).removeAll();
        assertEquals("sig Person {}\r\n// \ud83d\ude80", value.artifact().path("source").textValue());
        assertEquals("signature", value.inventory().path(FIRST).textValue());
    }

    /** Every existing historical kind is admitted only for a requested identifier.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void permitsAllEightHistoricalKinds() throws Exception {
        for (String kind : List.of("signature", "field", "predicate", "fact", "assertion", "command", "binder", "expression")) {
            ObjectNode result = context();
            ((ObjectNode) result.path("ownedIdInventory")).put(FIRST, kind);
            DocumentValidationContext value = DocumentValidationContext.read(gateway(result), DOCUMENT, 0,
                    JsonNodeFactory.instance.arrayNode().add(FIRST));
            assertEquals(kind, value.inventory().path(FIRST).textValue());
        }
    }

    /** Missing ownership remains missing rather than being inferred from a requested ID.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void doesNotInventMissingOwnership() throws Exception {
        DocumentValidationContext value = DocumentValidationContext.read(gateway(context()), DOCUMENT, 0,
                JsonNodeFactory.instance.arrayNode().add(FIRST));
        assertTrue(value.inventory().isEmpty());
    }

    /** Malformed IDs and invalid revisions are denied before a private child is requested.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void rejectsMalformedArgumentsBeforeBridge() throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        assertThrows(IOException.class, new Read(gateway, DOCUMENT, -1, MissingNode.getInstance()));
        assertThrows(IOException.class, new Read(gateway, DOCUMENT, 9007199254740992L, MissingNode.getInstance()));
        assertThrows(IOException.class, new Read(gateway, "server:broken", 0, MissingNode.getInstance()));
        assertThrows(IOException.class, new Read(gateway, DOCUMENT, 0,
                JsonNodeFactory.instance.arrayNode().add("server:broken")));
        verifyNoInteractions(gateway);
    }

    /** The 4096-ID boundary stays bounded, and one extra distinct ID starts no bridge.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void enforcesDistinctIdCountBeforeBridge() throws Exception {
        ArrayNode module = JsonNodeFactory.instance.arrayNode();
        for (int index = 0; index < 4096; index++) module.add("server:" + new UUID(0, index));
        DocumentGateway gateway = gateway(context());
        DocumentValidationContext.read(gateway, DOCUMENT, 0, module);
        verify(gateway).request(eq("validationContext"), any(JsonNode.class));
        clearInvocations(gateway);
        module.add("server:" + new UUID(0, 4096));
        assertThrows(IOException.class, new Read(gateway, DOCUMENT, 0, module));
        verifyNoInteractions(gateway);
    }

    /** A private context cannot substitute document, base or unsafe observed-head values.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void rejectsMismatchedIdentityAndRevisions() throws Exception {
        for (ObjectNode result : invalidIdentities()) assertRejected(result);
    }

    /** Required context and artifact shapes reject missing, extra or nonobject fields.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void rejectsMalformedShapes() throws Exception {
        for (ObjectNode result : invalidShapes()) assertRejected(result);
    }

    /** Unknown, unrequested and nontext inventory entries cannot confer ownership.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void rejectsForeignOrMalformedInventory() throws Exception {
        ObjectNode result = context();
        ((ObjectNode) result.path("ownedIdInventory")).put(SECOND, "signature");
        assertRejected(result);
        for (JsonNode kind : List.of(JsonNodeFactory.instance.textNode("unknown"), JsonNodeFactory.instance.numberNode(1))) {
            result = context();
            ((ObjectNode) result.path("ownedIdInventory")).set(FIRST, kind);
            assertThrows(IOException.class, new Read(gateway(result), DOCUMENT, 0,
                    JsonNodeFactory.instance.arrayNode().add(FIRST)));
        }
        result = context();
        result.set("ownedIdInventory", JsonNodeFactory.instance.arrayNode());
        assertRejected(result);
    }

    /** The base artifact's complete encoded size stays within the inherited 1MiB cap.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void rejectsOversizedBaseArtifact() throws Exception {
        ObjectNode result = context();
        ((ObjectNode) result.path("artifact")).put("source", "x".repeat(1048576));
        assertRejected(result);
    }

    /** A successful context read can use an older immutable base without replacing accepted state.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void permitsObservedHeadBeyondExactBase() throws Exception {
        ObjectNode result = context().put("headObserved", 9);
        assertEquals(result.path("artifact"),
                DocumentValidationContext.read(gateway(result), DOCUMENT, 0, MissingNode.getInstance()).artifact());
    }

    /** A denied context never constructs an Alloy worker and releases the active permit.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void failedContextPreventsWorkerConstruction() throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        when(gateway.request(eq("validationContext"), any(JsonNode.class)))
                .thenReturn(JsonNodeFactory.instance.objectNode().put("status", "ERROR"));
        DocumentQueries queries = new DocumentQueries(gateway, mock(DocumentRuntime.class), mock(JobService.class));
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class)) {
            assertThrows(IOException.class, new Validate(queries, request()));
            assertTrue(workers.constructed().isEmpty());
        }
        WorkerCapacity.acquire();
        WorkerCapacity.release();
    }

    /** Interrupted context transport also prevents worker construction and releases the permit.
     * @throws Exception unexpected fixture failure
     */
    @Test
    void interruptedContextPreventsWorkerConstruction() throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        when(gateway.request(eq("validationContext"), any(JsonNode.class))).thenThrow(new InterruptedException("fixture"));
        DocumentQueries queries = new DocumentQueries(gateway, mock(DocumentRuntime.class), mock(JobService.class));
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class)) {
            assertThrows(InterruptedException.class, new Validate(queries, request()));
            assertTrue(workers.constructed().isEmpty());
        }
        WorkerCapacity.acquire();
        WorkerCapacity.release();
    }

    /** Builds deterministic malformed identity examples without bypassing the public helper.
     * @return responses with substituted or unsafe identity fields
     * @throws IOException fixture artifact serialization failure
     */
    private static List<ObjectNode> invalidIdentities() throws IOException {
        return List.of(context().put("documentId", SECOND), context().put("documentId", 1),
                context().put("baseRevision", 1), context().put("baseRevision", false),
                context().put("headObserved", -1), context().put("headObserved", 9007199254740992L),
                context().put("headObserved", 0.5), context().put("headObserved", "0"));
    }

    /** Builds missing and extra-field examples for both closed context shapes.
     * @return malformed context responses
     * @throws IOException fixture artifact serialization failure
     */
    private static List<ObjectNode> invalidShapes() throws IOException {
        List<ObjectNode> values = new ArrayList<>();
        values.add(context().put("checked", true));
        ObjectNode missing = context();
        missing.remove("headObserved");
        values.add(missing);
        values.add(context().putNull("artifact"));
        ObjectNode extra = context();
        ((ObjectNode) extra.path("artifact")).put("checked", true);
        values.add(extra);
        missing = context();
        ((ObjectNode) missing.path("artifact")).remove("sourceHash");
        values.add(missing);
        return values;
    }

    /** Asserts private-response denial without treating browser-owned IDs as authority.
     * @param result malformed private context
     * @throws Exception fixture gateway configuration failure
     */
    private static void assertRejected(ObjectNode result) throws Exception {
        assertThrows(IOException.class, new Read(gateway(result), DOCUMENT, 0, MissingNode.getInstance()));
    }

    /** Creates one successful bridge envelope whose outer transport is tested independently.
     * @param result scoped context data
     * @return private bridge test double
     * @throws Exception fixture setup failure
     */
    private static DocumentGateway gateway(ObjectNode result) throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        ObjectNode envelope = JsonNodeFactory.instance.objectNode().put("status", "OK");
        envelope.set("data", result);
        when(gateway.request(eq("validationContext"), any(JsonNode.class))).thenReturn(envelope);
        return gateway;
    }

    /** Provides a complete stored-artifact shape with an empty requested-ID map.
     * @return exact-base response fixture
     * @throws IOException fixture serialization failure
     */
    private static ObjectNode context() throws IOException {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("documentId", DOCUMENT)
                .put("baseRevision", 0).put("headObserved", 0);
        result.set("artifact", DocumentArtifacts.empty("policy", "dependency"));
        result.putObject("ownedIdInventory");
        return result;
    }

    /** Supplies a closed source draft to exercise the controller-to-context sequencing.
     * @return exact advisory request bytes
     * @throws IOException fixture serialization failure
     */
    private static byte[] request() throws IOException {
        ObjectNode request = JsonNodeFactory.instance.objectNode().put("draftId", UUID.randomUUID().toString())
                .put("draftEpoch", 0).put("baseRevision", 0);
        request.putObject("candidate").put("mode", "SOURCE").put("source", "sig Person {}");
        return JsonWire.encode(request);
    }

    /** Retains immutable parameters for a context denial assertion. */
    private record Read(DocumentGateway gateway, String document, long revision, JsonNode module) implements Executable {
        /** Executes the checked private context boundary.
         * @throws IOException expected malformed fixture or failed transport
         * @throws InterruptedException expected interrupted fixture
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            DocumentValidationContext.read(gateway, document, revision, module);
        }
    }

    /** Retains an exact advisory request for lifecycle denial assertions. */
    private record Validate(DocumentQueries queries, byte[] bytes) implements Executable {
        /** Invokes actual query sequencing with a controlled persistence failure.
         * @throws IOException expected unavailable context
         * @throws InterruptedException expected interrupted context
         */
        @Override
        public void execute() throws IOException, InterruptedException { queries.validate(DOCUMENT, bytes); }
    }
}
