package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;

/** Actual DEFAULT document worker policy with its original disabled-pool cleanup path. */
final class WarmLatencyFresh {
    /** Prevents construction of the stateless fresh adapter. */
    private WarmLatencyFresh() {}

    /** Constructs, validates, serializes and obtains the production recovery receipt.
     * @param fixture immutable registered validation input
     * @param row current small timed observation record
     * @param records bounded response buffer owner
     * @param index exact response buffer index
     * @return complete canonical response bytes
     * @throws Exception actual production worker or receipt failure
     */
    static byte[] execute(JsonNode fixture, ObjectNode row, WarmLatencyRecords records, int index) throws Exception {
        DocumentWorker worker = new DocumentWorker(WorkerLaunchProfile.DEFAULT);
        Exception failure = null;
        try {
            row.put("callStartNs", System.nanoTime());
            JsonNode response = worker.validate(fixture.path("candidate"), fixture.path("baseArtifact"),
                    fixture.path("ownedIdInventory"), fixture.path("policyVersion").asText());
            row.put("callEndNs", System.nanoTime());
            byte[] bytes = JsonWire.encode(response);
            row.put("serializedNs", System.nanoTime()).put("requestNonce", response.path("requestId").asText());
            records.response(index, bytes);
            WarmLatencyRecords.successful(response);
            return bytes;
        } catch (Exception error) { failure = error; throw error; }
        finally {
            try { row.set("freshRecovery", worker.recovery()); }
            catch (Exception receipt) { if (failure == null) throw receipt; else failure.addSuppressed(receipt); }
        }
    }
}
