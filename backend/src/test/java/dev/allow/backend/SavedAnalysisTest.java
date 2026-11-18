package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import org.junit.jupiter.api.Test;
import org.mockito.MockedConstruction;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

/** Saved provenance remains distinct from current parser command admission. */
final class SavedAnalysisTest {
    private JsonNode workerOutcome;
    private boolean uncertainRecovery;

    /** Keeps coordinator and solver seam together for negative dispatch assertions. */
    private record Service(DocumentQueries queries, JobService jobs) {}
    /** Builds a saved two-command artifact.
     * @return saved content
     * @throws Exception fixture decoding failure */
    private ObjectNode artifact() throws Exception {
        ObjectNode value = (ObjectNode) JsonWire.decode(("{\"artifactId\":\"saved\",\"policyVersion\":\"old-policy\","
                + "\"dependencyHash\":\"old-build\",\"source\":\"sig A {} run {} check {}\",\"analysisDescriptors\":[]}").getBytes(), JsonNode.class);
        value.put("sourceHash", Hashes.text(value.path("source").asText()));
        for (int index = 0; index < 2; index++) {
            ObjectNode command = value.withArray("analysisDescriptors").addObject();
            command.put("index", index).put("commandKey", "key-" + index)
                    .put("kind", index == 0 ? "run" : "check").put("label", "command-" + index);
            command.putObject("options").put("overall", index + 3).put("bitwidth", 4).put("maxseq", 3);
            for (String field : new String[]{"artifactId", "sourceHash", "policyVersion"}) command.set(field, value.get(field));
        }
        return value;
    }

    /** Builds a selection for the distinguishing second command.
     * @param artifact saved content
     * @return selection */
    private ObjectNode request(ObjectNode artifact) {
        ObjectNode value = artifact.objectNode().put("commandKey", "key-1");
        value.set("exactSourceHash", artifact.get("sourceHash"));
        return value;
    }

    /** Preserves saved identity.
     * @throws Exception fixture decoding failure */
    @Test void oldPolicyRetainsExactSecondCommandAndNeverMutatesStoredArtifact() throws Exception {
        ObjectNode artifact = artifact(), original = artifact.deepCopy();
        JsonNode selected = SavedAnalysis.command(artifact, request(artifact));
        assertEquals(1, selected.path("index").intValue());
        assertTrue(SavedAnalysis.matches(artifact, selected, artifact.deepCopy()));
        assertEquals(original, artifact);
    }

    /** Rejects invalid client and stored bindings.
     * @throws Exception fixture decoding failure */
    @Test void rejectsWrongHashUnknownKeyAndCorruptExactSource() throws Exception {
        ObjectNode artifact = artifact(), request = request(artifact);
        request.put("exactSourceHash", "wrong");
        assertRejected(artifact, request);
        request.set("exactSourceHash", artifact.get("sourceHash"));
        request.put("commandKey", "unknown");
        assertRejected(artifact, request);
        request.put("commandKey", "key-1");
        artifact.put("source", "replacement");
        assertRejected(artifact, request);
    }

    /** Checks rejection without a callback that obscures the selected inputs.
     *
     * @param artifact immutable saved content
     *
     * @param request client selection
     */
    private void assertRejected(ObjectNode artifact, ObjectNode request) {
        try {
            SavedAnalysis.command(artifact, request);
            fail("Selection should be rejected");
        } catch (IllegalArgumentException expected) { assertNotNull(expected.getMessage()); }
    }

    /** A genuine worker INVALID envelope rejects analysis before solver dispatch, even off head.
     * @throws Exception unexpected service or fixture failure
     */
    @Test void currentValidationInvalidRejectsHistoricalSavedSelectionWithoutDispatch() throws Exception {
        ObjectNode artifact = artifact(), original = artifact.deepCopy();
        DocumentGateway gateway = historicalGateway(artifact);
        DocumentRuntime runtime = runtime("current-policy");
        JobService jobs = mock(JobService.class);
        DocumentQueries queries = new DocumentQueries(gateway, runtime, jobs);
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class, this::invalidWorker)) {
            JsonNode response = analyze(queries, artifact);
            assertEquals("REJECTED", response.path("status").asText());
            assertEquals("SAVED_MODEL_INCOMPATIBLE", response.path("data").path("code").asText());
            assertTrue(response.path("data").path("message").asText().contains("Edit and save"));
            assertEquals(1, workers.constructed().size());
            DocumentWorker worker = workers.constructed().get(0);
            verify(worker).revalidate(eq(original), any(JsonNode.class), eq("current-policy"));
            verify(worker).recovery();
        }
        verifyNoInteractions(jobs);
        assertEquals(original, artifact);
        assertTrue(queries.cleanupSafe());
        verify(gateway).request(eq("read"), any(JsonNode.class));
        verify(gateway).request(eq("ownedIds"), any(JsonNode.class));
        verifyNoMoreInteractions(gateway);
        WorkerCapacity.acquire();
        WorkerCapacity.release();
    }

    /** Rejects a successfully parsed artifact when its exact selected descriptor changed.
     * @throws Exception unexpected fixture failure
     */
    @Test void changedValidatedCommandRejectsWithoutSolverDispatch() throws Exception {
        ObjectNode artifact = artifact();
        workerOutcome = validated(artifact);
        ((ObjectNode) workerOutcome.path("data").path("analysisDescriptors").get(1)).put("label", "changed");
        Service service = service(artifact, "current-policy");
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class, this::outcomeWorker)) {
            JsonNode response = analyze(service.queries(), artifact);
            assertEquals("REJECTED", response.path("status").asText());
            assertEquals("SAVED_COMMAND_CHANGED", response.path("data").path("code").asText());
            assertEquals("The saved command differs under the current policy. Review the command and save the model before analyzing again.",
                    response.path("data").path("message").asText());
            verify(workers.constructed().get(0)).recovery();
        }
        verifyNoInteractions(service.jobs());
    }

    /** A build-only mismatch still requires current validation before admission.
     * @throws Exception unexpected fixture failure
     */
    @Test void dependencyOnlyMismatchRevalidatesAndRejectsChangedCommand() throws Exception {
        ObjectNode artifact = artifact();
        workerOutcome = validated(artifact);
        ((ObjectNode) workerOutcome.path("data").path("analysisDescriptors").get(1)).put("kind", "run");
        Service service = service(artifact, "old-policy");
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class, this::outcomeWorker)) {
            assertEquals("SAVED_COMMAND_CHANGED", analyze(service.queries(), artifact).path("data").path("code").asText());
            assertEquals(1, workers.constructed().size());
            verify(workers.constructed().get(0)).revalidate(eq(artifact), any(JsonNode.class), eq("old-policy"));
        }
        verifyNoInteractions(service.jobs());
    }

    /** Unavailable worker output never becomes a deterministic rejection or solver job.
     * @throws Exception unexpected fixture failure
     */
    @Test void unavailableValidatorDoesNotDispatchOrQuarantineReapedWorker() throws Exception {
        ObjectNode artifact = artifact();
        workerOutcome = artifact.objectNode().put("status", "UNAVAILABLE");
        Service service = service(artifact, "current-policy");
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class, this::outcomeWorker)) {
            unavailable(service.queries(), artifact);
            verify(workers.constructed().get(0)).recovery();
        }
        assertTrue(service.queries().cleanupSafe());
        verifyNoInteractions(service.jobs());
    }

    /** Uncertain recovery quarantines the coordinator and blocks later admissions.
     * @throws Exception unexpected fixture failure
     */
    @Test void uncertainRecoveryQuarantinesWithoutDispatch() throws Exception {
        ObjectNode artifact = artifact();
        workerOutcome = validated(artifact);
        uncertainRecovery = true;
        Service service = service(artifact, "current-policy");
        try (MockedConstruction<DocumentWorker> workers = mockConstruction(DocumentWorker.class, this::outcomeWorker)) {
            unavailable(service.queries(), artifact);
            assertFalse(service.queries().cleanupSafe());
            unavailable(service.queries(), artifact);
            assertEquals(1, workers.constructed().size());
        }
        verifyNoInteractions(service.jobs());
        WorkerCapacity.acquire();
        WorkerCapacity.release();
    }

    /** Creates a current runtime and an explicitly observed solver dispatch seam.
     * @param artifact stored historical content
     * @param policy current runtime policy
     * @return coordinator and solver seam
     * @throws Exception fixture setup failure
     */
    private Service service(ObjectNode artifact, String policy) throws Exception {
        DocumentRuntime runtime = runtime(policy);
        JobService jobs = mock(JobService.class);
        return new Service(new DocumentQueries(historicalGateway(artifact), runtime, jobs), jobs);
    }

    /** Supplies explicit frozen current execution identity for every service fixture.
     * @param policy current parser policy
     * @return installation identity seam
     */
    private DocumentRuntime runtime(String policy) {
        DocumentRuntime runtime = mock(DocumentRuntime.class);
        when(runtime.policy()).thenReturn(policy);
        when(runtime.dependency()).thenReturn("current-build");
        return runtime;
    }

    /** Invokes the distinguishing historical command through the public service boundary.
     * @param queries coordinator under test
     * @param artifact exact saved source identity
     * @return decoded response
     * @throws Exception read or serialization failure
     */
    private JsonNode analyze(DocumentQueries queries, ObjectNode artifact) throws Exception {
        ObjectNode selection = request(artifact).put("acceptedRevision", 2).put("draftEpoch", 7);
        return JsonWire.decode(queries.analyze("saved-document", JsonWire.encode(selection)), JsonNode.class);
    }

    /** Requires infrastructure failure instead of private solver evidence.
     * @param queries coordinator under test
     * @param artifact exact saved source
     * @throws Exception unexpected non-infrastructure failure
     */
    private void unavailable(DocumentQueries queries, ObjectNode artifact) throws Exception {
        try {
            analyze(queries, artifact);
            fail("Unavailable validation must not admit analysis");
        } catch (java.io.IOException expected) { assertNotNull(expected.getMessage()); }
    }

    /** Builds the closed successful worker payload without copying saved authority fields.
     * @param artifact exact saved source and descriptors
     * @return valid response envelope
     */
    private ObjectNode validated(ObjectNode artifact) {
        ObjectNode envelope = artifact.objectNode().put("status", "VALIDATED");
        ObjectNode data = envelope.putObject("data").put("mode", "STRUCTURED");
        for (String field : new String[]{"source", "sourceHash", "analysisDescriptors"}) {
            data.set(field, artifact.get(field).deepCopy());
        }
        data.putObject("module");
        for (String field : new String[]{"occurrences", "trivia", "diagnostics"}) data.putArray(field);
        data.putObject("idRemapping");
        return envelope;
    }

    /** Configures a single owned worker response and optional recovery uncertainty.
     * @param worker constructed owned worker seam
     * @param context observed construction arguments
     * @throws Exception fixture setup failure
     */
    private void outcomeWorker(DocumentWorker worker, MockedConstruction.Context context) throws Exception {
        assertTrue(context.arguments().isEmpty());
        when(worker.identity()).thenReturn("current-build");
        when(worker.revalidate(any(JsonNode.class), any(JsonNode.class), anyString())).thenReturn(workerOutcome);
        if (uncertainRecovery) doThrow(new IllegalStateException("unreaped")).when(worker).recovery();
    }

    /** Supplies immutable historical revision two while the current head is nine.
     * @param artifact saved historical content
     * @return scoped persistence test double
     * @throws Exception fixture setup failure
     */
    private DocumentGateway historicalGateway(ObjectNode artifact) throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        ObjectNode read = artifact.objectNode().put("status", "OK");
        ObjectNode snapshot = read.putObject("data").put("headRevision", 9).put("requestedRevision", 2);
        snapshot.set("artifact", artifact);
        when(gateway.request(eq("read"), any(JsonNode.class))).thenReturn(read);
        ObjectNode owned = artifact.objectNode().put("status", "OK");
        owned.putObject("data").putObject("ids");
        when(gateway.request(eq("ownedIds"), any(JsonNode.class))).thenReturn(owned);
        return gateway;
    }

    /** Supplies a deterministic current-worker historical-content rejection.
     * @param worker owned worker construction test double
     * @param context actual worker construction details
     * @throws Exception fixture setup failure
     */
    private void invalidWorker(DocumentWorker worker, MockedConstruction.Context context) throws Exception {
        assertTrue(context.arguments().isEmpty());
        when(worker.identity()).thenReturn("current-build");
        ObjectNode invalid = com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode().put("status", "INVALID");
        invalid.putObject("data").put("code", "INVALID_UNDO_TARGET").putArray("diagnostics");
        when(worker.revalidate(any(JsonNode.class), any(JsonNode.class), eq("current-policy"))).thenReturn(invalid);
    }

    /** Rejects fresh command substitution.
     * @throws Exception fixture decoding failure */
    @Test void rejectsChangedSelectedOccurrenceAndOptionsRatherThanSubstitution() throws Exception {
        ObjectNode artifact = artifact();
        JsonNode selected = SavedAnalysis.command(artifact, request(artifact));
        for (String field : new String[]{"index", "kind", "label", "options"}) {
            ObjectNode checked = artifact.deepCopy();
            ((ObjectNode) checked.path("analysisDescriptors").get(1)).put(field, "changed");
            assertFalse(SavedAnalysis.matches(artifact, selected, checked), field);
        }
        ObjectNode checked = artifact.deepCopy();
        checked.put("source", "different source");
        assertFalse(SavedAnalysis.matches(artifact, selected, checked));
        checked = artifact.deepCopy();
        checked.withArray("analysisDescriptors").remove(1);
        assertFalse(SavedAnalysis.matches(artifact, selected, checked));
    }
}
