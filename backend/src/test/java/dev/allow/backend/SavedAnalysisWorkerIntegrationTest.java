package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Real saved-source admission and SAT4J execution with only private persistence replaced. */
final class SavedAnalysisWorkerIntegrationTest {
    private static final String SOURCE = "// exact saved text\r\nsig A, B {}\r\nrun { some A } for 2\nrun { no A and some A } for 2\n";
    @TempDir private Path directory;
    private ObjectNode saved;

    /** Revalidates an older immutable artifact and executes its selected second command.
     * @throws Exception failed sandbox, fixture or solver
     */
    @Test
    void historicalTextOnlySecondCommandUsesSavedSourceAndCurrentSolver() throws Exception {
        DocumentGateway gateway = storage();
        DocumentRuntime runtime = runtime(gateway);
        JobService jobs = new JobService();
        try {
            saved = artifact(runtime.policy());
            ObjectNode immutable = saved.deepCopy();
            DocumentQueries queries = new DocumentQueries(gateway, runtime, jobs);
            JsonNode first = execute(queries, 0);
            JsonNode second = execute(queries, 1);
            assertEquals("SAT", first.path("job").path("status").asText(), first.toString());
            assertEquals("UNSAT", second.path("job").path("status").asText(), second.toString());
            assertTrue(second.path("historical").asBoolean());
            assertEquals(immutable, saved, "Current validation must not replace saved history");
            assertTrue(queries.cleanupSafe());
            verify(gateway, times(2)).request(eq("ownedIds"), any(JsonNode.class));
        } finally { jobs.close(); runtime.close(); }
    }

    /** Initializes a real exclusive private runtime using a temporary POSIX directory.
     * @param gateway controlled persistence operations
     * @return ready production runtime
     * @throws Exception unavailable filesystem or build
     */
    private DocumentRuntime runtime(DocumentGateway gateway) throws Exception {
        Path metadata = Files.createDirectories(directory.resolve(".runtime/documents"));
        Files.setPosixFilePermissions(metadata, PosixFilePermissions.fromString("rwx------"));
        return new DocumentRuntime(gateway, directory.toString());
    }

    /** Replaces storage alone, refusing every operation outside the private fixture contract.
     * @return controlled private operation bridge
     * @throws Exception mock configuration failure
     */
    private DocumentGateway storage() throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        when(gateway.request(anyString(), any(JsonNode.class))).thenAnswer(this::stored);
        return gateway;
    }

    /** Returns immutable history and a distinct newer head without database credentials.
     * @param invocation private bridge invocation
     * @return private storage envelope
     * @throws java.io.IOException unexpected persistence mutation
     */
    private JsonNode stored(org.mockito.invocation.InvocationOnMock invocation) throws java.io.IOException {
        String operation = invocation.getArgument(0);
        ObjectNode envelope = JsonNodeFactory.instance.objectNode().put("status", "OK");
        ObjectNode data = envelope.putObject("data");
        switch (operation) {
            case "init" -> data.put("status", "READY");
            case "ownedIds" -> data.putObject("ids");
            case "read" -> {
                JsonNode args = invocation.getArgument(1);
                assertEquals("saved-document", args.path("documentId").asText());
                data.put("headRevision", 9).put("requestedRevision", args.path("revision").isNull() ? 9 : 2);
                data.set("artifact", args.path("revision").isNull()
                        ? saved.deepCopy().put("source", "sig NewHead {} run {} for 1") : saved.deepCopy());
            }
            default -> throw new java.io.IOException("Unexpected persistence operation: " + operation);
        }
        return envelope;
    }

    /** Builds real parser descriptors, retaining old policy and build provenance in storage.
     * @param policy current policy for initial real validation
     * @return old saved immutable artifact
     * @throws Exception failed real document validation
     */
    private ObjectNode artifact(String policy) throws Exception {
        DocumentWorker worker = new DocumentWorker();
        ObjectNode empty = JsonNodeFactory.instance.objectNode();
        ObjectNode candidate = empty.objectNode().put("mode", "SOURCE").put("source", SOURCE);
        JsonNode outcome = worker.validate(candidate, empty, empty, policy);
        assertTrue(worker.recovery().isObject());
        assertEquals("VALIDATED", outcome.path("status").asText(), outcome.toString());
        ObjectNode artifact = (ObjectNode) outcome.path("data").deepCopy();
        artifact.put("artifactId", "old-saved-artifact").put("policyVersion", "old-policy").put("dependencyHash", "old-build");
        assertEquals("TEXT_ONLY", artifact.path("mode").asText());
        assertTrue(artifact.path("module").isNull());
        assertEquals(SOURCE, artifact.path("source").asText());
        assertEquals(2, artifact.path("analysisDescriptors").size());
        for (JsonNode descriptor : artifact.path("analysisDescriptors")) {
            ObjectNode command = (ObjectNode) descriptor;
            command.put("artifactId", "old-saved-artifact").put("policyVersion", "old-policy");
            command.put("commandKey", "saved-command-" + command.path("index").asInt());
            command.set("sourceHash", artifact.get("sourceHash"));
        }
        return artifact;
    }

    /** Submits an exact saved occurrence and polls the real bounded supervisor to completion.
     * @param queries production accepted-analysis coordinator
     * @param index saved command occurrence
     * @return terminal private result with retained provenance
     * @throws Exception worker, solver or timeout failure
     */
    private JsonNode execute(DocumentQueries queries, int index) throws Exception {
        JsonNode command = saved.path("analysisDescriptors").get(index);
        ObjectNode request = saved.objectNode().put("acceptedRevision", 2).put("draftEpoch", 7);
        request.set("commandKey", command.get("commandKey"));
        request.set("exactSourceHash", saved.get("sourceHash"));
        JsonNode submitted = JsonWire.decode(queries.analyze("saved-document", JsonWire.encode(request)), JsonNode.class);
        assertEquals("SUBMITTED", submitted.path("status").asText(), submitted.toString());
        String job = submitted.path("data").path("jobId").asText();
        long deadline = System.nanoTime() + 20_000_000_000L;
        JsonNode result;
        do {
            result = JsonWire.decode(queries.analysis("saved-document", job), JsonNode.class).path("data");
            if (!java.util.Set.of("QUEUED", "RUNNING").contains(result.path("job").path("status").asText())) break;
            Thread.sleep(20);
        } while (System.nanoTime() < deadline);
        assertEquals(submitted.path("data").path("acceptedAnalysisKey"), result.path("acceptedAnalysisKey"));
        assertEquals(saved.path("sourceHash"), result.path("job").path("sourceHash"));
        assertEquals(command.path("commandKey"), result.path("acceptedAnalysisKey").path("commandKey"));
        return result;
    }
}
