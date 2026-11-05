package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.document.AnonymousModel;
import dev.allow.document.DocumentEngine;
import dev.allow.document.DocumentValidationException;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Current-head, cancellation and existing global worker-lane regression boundaries. */
class AiAuthorityTest {
    /** A changed accepted head or policy cannot publish or authorize an old proposal.
     * @throws IOException fixture serialization failure
     * @throws InterruptedException interrupted mocked head read
     */
    @Test
    void staleHeadAndPolicyDenyCurrentAuthority() throws IOException, InterruptedException {
        DocumentQueries queries = mock(DocumentQueries.class);
        DocumentRuntime runtime = runtime();
        AiService service = new AiService(configuration(), queries, runtime);
        AiJob job = job();
        ObjectNode head = head();
        when(queries.aiHead(anyString())).thenReturn(head);
        try {
            service.current(job);
            head.put("headRevision", 1);
            assertThrows(AiFailure.class, new Current(service, job));
            head.put("headRevision", 0);
            ((ObjectNode) head.path("artifact")).put("policyVersion", "changed");
            assertThrows(AiFailure.class, new Current(service, job));
        } finally { service.close(); }
    }

    /** Staleness during named verification is terminal, never a repair diagnostic.
     * @throws IOException fixture serialization failure
     * @throws InterruptedException interrupted mocked worker
     * @throws DocumentValidationException invalid actual-parser fixture
     */
    @Test
    void staleNamedVerificationNeverBecomesRepairable() throws IOException, InterruptedException, DocumentValidationException {
        DocumentQueries queries = mock(DocumentQueries.class);
        AiService service = new AiService(configuration(), queries, runtime());
        AiJob job = job();
        String source = "sig Private {} pred selected { some Private } run selected for 3 but 4 Int, 3 seq";
        JsonNode checked = checked(source);
        AnonymousModel anonymous = new AnonymousModel(checked.path("module"));
        job.preparedModel(anonymous, source);
        ObjectNode outcome = JsonNodeFactory.instance.objectNode().put("status", "VALIDATED");
        outcome.set("data", checked(anonymous.source()));
        when(queries.aiHead(anyString())).thenReturn(head());
        when(queries.aiValidate(anyString(), anyLong(), any(JsonNode.class), anyLong())).thenReturn(outcome).thenThrow(new AiFailure("STALE_INPUT"));
        try {
            AiFailure failure = assertThrows(AiFailure.class, new Verify(service, job, anonymous.source()));
            assertEquals("STALE_INPUT", failure.code());
        } finally { service.close(); }
    }

    /** AI validation cannot create a second worker or SQL context beside manual work.
     * @throws IOException unavailable fake worker fixture
     * @throws InterruptedException interrupted fixture
     */
    @Test
    void sharedBusyWorkerDeniesBeforeContextMaterialization() throws IOException, InterruptedException {
        DocumentGateway gateway = mock(DocumentGateway.class);
        DocumentQueries queries = new DocumentQueries(gateway, runtime(), mock(JobService.class));
        WorkerCapacity.acquire();
        try { assertThrows(java.util.concurrent.RejectedExecutionException.class, new BusyValidate(queries)); }
        finally { WorkerCapacity.release(); }
        verifyNoInteractions(gateway);
    }

    /** Fixture configuration requires no credential and keeps provider choices trusted.
     * @return closed private configuration
     * @throws IOException unavailable configured credential
     */
    private AiConfiguration configuration() throws IOException {
        return new AiConfiguration("FIXTURE", "/tmp/private-ai-project", "/tmp/private-ledger/data.json", 100000,
                "fixture-v1", "", "", false, new AccessMode("PRIVATE"));
    }

    /** Supplies an installed policy without constructing any real persistence connection.
     * @return mocked immutable runtime
     */
    private DocumentRuntime runtime() {
        DocumentRuntime runtime = mock(DocumentRuntime.class);
        when(runtime.policy()).thenReturn("policy");
        when(runtime.dependency()).thenReturn("dependency");
        return runtime;
    }

    /** Builds exact current accepted identity independent of the draft contents.
     * @return scoped head
     */
    private ObjectNode head() {
        ObjectNode head = JsonNodeFactory.instance.objectNode().put("headRevision", 0);
        head.putObject("artifact").put("artifactId", "artifact").put("sourceHash", "a".repeat(64))
                .put("policyVersion", "policy").put("dependencyHash", "dependency");
        return head;
    }

    /** Builds a bounded exact private create binding.
     * @return independent job
     * @throws IOException fixture serialization failure
     */
    private AiJob job() throws IOException {
        ObjectNode request = JsonNodeFactory.instance.objectNode().put("requestId", "00000000-0000-4000-8000-000000000001")
                .put("documentId", "server:00000000-0000-4000-8000-000000000002").put("baseRevision", 0)
                .put("draftId", "00000000-0000-4000-8000-000000000003").put("draftEpoch", 0).put("contentGeneration", 0)
                .put("artifactId", "artifact").put("sourceHash", "a".repeat(64)).put("intent", "Repair").put("kind", "SOURCE_EDIT");
        request.putObject("candidate").put("mode", "SOURCE").put("source", "sig Private {}");
        return new AiJob(new AiRequest(JsonWire.encode(request)), "launch");
    }

    /** Uses real deterministic Alloy validation only for authored fixture observations.
     * @param source authored bounded source
     * @return full checked data
     * @throws DocumentValidationException invalid fixture
     */
    private JsonNode checked(String source) throws DocumentValidationException {
        ObjectNode candidate = JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", source);
        return new DocumentEngine().validate(candidate, JsonNodeFactory.instance.objectNode(), JsonNodeFactory.instance.objectNode(), "test");
    }

    /** Names an authority observation.
     * @param service trusted service
     * @param job exact original job
     */
    private record Current(AiService service, AiJob job) implements Executable {
        /** Performs a current-head check.
         * @throws IOException unavailable fixture
         * @throws InterruptedException interrupted fixture
         */
        @Override
        public void execute() throws IOException, InterruptedException { service.current(job); }
    }

    /** Names a verifier operation.
     * @param service trusted host
     * @param job exact binding
     * @param source anonymous proposal
     */
    private record Verify(AiService service, AiJob job, String source) implements Executable {
        /** Performs the full named verification path.
         * @throws IOException unavailable fixture
         * @throws InterruptedException interrupted fixture
         */
        @Override
        public void execute() throws IOException, InterruptedException { service.verify(job, source); }
    }

    /** Names a shared-lane admission.
     * @param queries actual scoped query service
     */
    private record BusyValidate(DocumentQueries queries) implements Executable {
        /** Attempts validation while the existing shared permit is occupied.
         * @throws IOException unavailable fixture
         * @throws InterruptedException interrupted fixture
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            queries.aiValidate("server:00000000-0000-4000-8000-000000000001", 0,
                    JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", "sig A {}"), 1000);
        }
    }
}
