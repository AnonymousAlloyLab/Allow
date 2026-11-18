package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.dto.JobRequest;
import dev.allow.dto.JobView;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Accepted registrations retain saved provenance and scope private solver reads. */
final class SavedAnalysisRegistrationTest {
    private final DocumentGateway gateway = mock(DocumentGateway.class);
    private final DocumentRuntime runtime = mock(DocumentRuntime.class);
    private final JobService jobs = mock(JobService.class);
    private final DocumentQueries queries = new DocumentQueries(gateway, runtime, jobs,
            new DeploymentPolicy("", "", "DEFAULT"), "private-owner");

    /** Creates a current compatible saved artifact with a non-first command.
     * @return immutable fixture content
     */
    private ObjectNode artifact() {
        ObjectNode artifact = JsonNodeFactory.instance.objectNode().put("source", "sig A {} run {} check {}")
                .put("artifactId", "saved").put("policyVersion", "policy").put("dependencyHash", "build");
        artifact.put("sourceHash", Hashes.text(artifact.path("source").asText()));
        for (int index = 0; index < 2; index++) {
            ObjectNode command = artifact.withArray("analysisDescriptors").addObject().put("index", index)
                    .put("commandKey", "key-" + index).put("kind", index == 0 ? "run" : "check");
            command.putObject("options").put("overall", 3);
            for (String field : new String[]{"artifactId", "sourceHash", "policyVersion"}) {
                command.set(field, artifact.get(field));
            }
        }
        return artifact;
    }

    /** Supplies an owned historical snapshot and deterministic solver admission.
     * @return submitted response
     * @throws Exception fixture or serialization failure
     */
    private JsonNode submit() throws Exception {
        ObjectNode artifact = artifact();
        ObjectNode envelope = artifact.objectNode().put("status", "OK");
        envelope.putObject("data").put("headRevision", 9).put("requestedRevision", 2).set("artifact", artifact);
        when(gateway.request(eq("read"), any(JsonNode.class))).thenReturn(envelope);
        when(runtime.policy()).thenReturn("policy");
        when(runtime.dependency()).thenReturn("build");
        when(jobs.submit(any(JobRequest.class), eq("private-owner"))).thenReturn(job("bound-key"));
        when(jobs.get("job", "private-owner")).thenReturn(job("bound-key"));
        ObjectNode request = artifact.objectNode().put("acceptedRevision", 2).put("draftEpoch", 7)
                .put("commandKey", "key-1").put("exactSourceHash", artifact.path("sourceHash").asText());
        return JsonWire.decode(queries.analyze("document", JsonWire.encode(request)), JsonNode.class);
    }

    /** Builds immutable bounded solver metadata.
     * @param analysisKey exact solver binding
     * @return solver state
     */
    private JobView job(String analysisKey) {
        return new JobView("job", "QUEUED", artifact().path("sourceHash").asText(), 2, 7,
                analysisKey, "check", "", List.of(), null, null);
    }

    /** Preserves exact saved provenance and marks a retained old revision historical.
     * @throws Exception unexpected coordinator failure
     */
    @Test void submitsExactSecondCommandAndPollsOnlyPrivateOwner() throws Exception {
        JsonNode response = submit();
        assertEquals("SUBMITTED", response.path("status").asText());
        JsonNode key = response.path("data").path("acceptedAnalysisKey");
        assertEquals("saved", key.path("artifactId").asText());
        assertEquals("key-1", key.path("commandKey").asText());
        verify(jobs).submit(new JobRequest(artifact().path("source").asText(), 1, 2, 7, "ANALYZE"), "private-owner");
        JsonNode polled = JsonWire.decode(queries.analysis("document", "job"), JsonNode.class);
        assertTrue(polled.path("data").path("historical").booleanValue());
        assertEquals(key, polled.path("data").path("acceptedAnalysisKey"));
        verify(jobs).get("job", "private-owner");
        assertTrue(queries.cleanupSafe());
    }

    /** Rejects unrelated registrations before reading a private job or persistence.
     * @throws Exception unexpected fixture failure
     */
    @Test void wrongDocumentAndUnknownJobCannotReachPrivateExecution() throws Exception {
        submit();
        clearInvocations(gateway, jobs);
        rejected("other-document", "job");
        rejected("document", "unknown-job");
        verifyNoInteractions(gateway, jobs);
    }

    /** Rejects unavailable owner-bound jobs and mismatched execution identities.
     * @throws Exception unexpected fixture failure
     */
    @Test void absentOwnedJobAndMismatchedJobIdentityCannotExposeEvidence() throws Exception {
        submit();
        when(jobs.get("job", "private-owner")).thenReturn(null);
        rejected("document", "job");
        when(jobs.get("job", "private-owner")).thenReturn(job("other-execution"));
        rejected("document", "job");
    }

    /** Refuses retained evidence after either current execution identity changes.
     * @throws Exception unexpected fixture failure
     */
    @Test void runtimePolicyAndDependencyDriftInvalidateRegistration() throws Exception {
        submit();
        when(runtime.policy()).thenReturn("changed-policy");
        rejected("document", "job");
        when(runtime.policy()).thenReturn("policy");
        when(runtime.dependency()).thenReturn("changed-build");
        rejected("document", "job");
    }

    /** Asserts a refused poll without serializing private job evidence.
     * @param document requested document
     * @param job requested execution
     * @throws Exception unexpected non-rejection failure
     */
    private void rejected(String document, String job) throws Exception {
        try {
            queries.analysis(document, job);
            fail("Private analysis poll must be rejected");
        } catch (IOException expected) {
            assertNotNull(expected.getMessage());
        }
    }
}
