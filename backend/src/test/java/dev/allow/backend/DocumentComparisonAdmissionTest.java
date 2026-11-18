package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.concurrent.RejectedExecutionException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/** Admission quarantine tests using trusted seams, without launching a real unowned process. */
class DocumentComparisonAdmissionTest {
    /** Uncertain reaping must quarantine global admission instead of recycling a permit.
     * @throws Exception fixture setup failure
     */
    @Test void uncertainCleanupRetainsGlobalPermit() throws Exception {
        DocumentRuntime runtime = mock(DocumentRuntime.class);
        when(runtime.policy()).thenReturn("policy"); when(runtime.dependency()).thenReturn("dependency");
        DocumentGateway gateway = mock(DocumentGateway.class);
        ObjectNode artifact = DocumentArtifacts.empty("policy", "dependency");
        ObjectNode envelope = context(artifact);
        when(gateway.request(eq("validationContext"), any(JsonNode.class), any(WarmDeadline.class))).thenReturn(envelope);
        DocumentWorker worker = mock(DocumentWorker.class);
        when(worker.identity()).thenReturn("dependency");
        when(worker.compare(anyString(), any(), any(), any(), anyString(), anyLong()))
                .thenReturn(JsonNodeFactory.instance.objectNode().put("status", "VALIDATED").set("data", JsonNodeFactory.instance.objectNode()));
        when(worker.recovery()).thenThrow(new IllegalStateException("Unknown cleanup"));
        DocumentComparison operation = new DocumentComparison(gateway, runtime, new Returning(worker));
        try {
            JsonNode result = JsonWire.decode(operation.execute("server:00000000-0000-4000-8000-000000000001", request(artifact), "COMPARISON_MODEL"), JsonNode.class);
            assertEquals("UNAVAILABLE", result.path("status").asText());
            assertFalse(operation.cleanupSafe());
            assertThrows(RejectedExecutionException.class, WorkerCapacity::acquire);
        } finally { WorkerCapacity.release(); }
    }

    /** Builds one closed authorized context response.
     * @param artifact exact base fixture
     * @return private context envelope
     */
    private ObjectNode context(ObjectNode artifact) {
        ObjectNode envelope = JsonNodeFactory.instance.objectNode().put("status", "OK");
        ObjectNode data = envelope.putObject("data").put("documentId", "server:00000000-0000-4000-8000-000000000001")
                .put("baseRevision", 0).put("headObserved", 0);
        data.set("artifact", artifact); data.putObject("ownedIdInventory");
        return envelope;
    }

    /** Encodes a valid exact source inspection intent.
     * @param artifact exact authorized base
     * @return original HTTP request bytes
     * @throws IOException encoding failure
     */
    private byte[] request(ObjectNode artifact) throws IOException {
        String source = "sig A {} pred P { some A }";
        ObjectNode request = JsonNodeFactory.instance.objectNode().put("draftId", "00000000-0000-4000-8000-000000000002")
                .put("draftEpoch", 0).put("baseRevision", 0).put("artifactId", artifact.path("artifactId").asText())
                .put("source", source).put("sourceHash", Hashes.text(source));
        return JsonWire.encode(request);
    }

    /** Returns an injected worker without allowing client-directed launch configuration. */
    private record Returning(DocumentWorker worker) implements DocumentComparison.Factory {
        /** Supplies the trusted lifecycle fixture.
         * @return mock owned worker
         */
        public DocumentWorker create() { return worker; }
    }
}
