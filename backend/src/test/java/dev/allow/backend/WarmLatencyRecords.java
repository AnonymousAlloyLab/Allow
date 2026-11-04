package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.Base64;

/** Bounded in-memory request evidence, encoded only after every component has stopped. */
final class WarmLatencyRecords {
    private final ObjectNode[] rows = new ObjectNode[120];
    private final byte[][] responses = new byte[120][];
    private int count;

    /** Creates fixed finite storage without preallocating response payloads. */
    WarmLatencyRecords() {}

    /** Allocates one small attempted-row record before its operation.
     * @param index registered zero-based request index
     * @param warmups number of registered warmups
     * @return retained mutable observation record
     * @throws IOException out-of-order or excessive request
     */
    ObjectNode row(int index, int warmups) throws IOException {
        if (index != count || count >= rows.length) throw new IOException("Row bound or order violated");
        ObjectNode row = JsonNodeFactory.instance.objectNode().put("index", index)
                .put("phase", index < warmups ? "WARMUP" : "MEASURED").put("outcome", "FAILED");
        String[] nullable = {"previousEndToAdmissionGapNs", "conditionStartNs", "conditionEndNs",
                "conditionDurationNs", "initializationStartNs", "initializationEndNs", "teardownStartNs",
                "teardownEndNs", "capacityAcquiredNs", "callStartNs", "callEndNs", "serializedNs",
                "publicationEndNs", "capacityReleasedNs", "requestNonce", "freshRecovery", "admission",
                "consumed", "failure", "admissionObservedNs"};
        for (String name : nullable) row.putNull(name);
        rows[count++] = row;
        return row;
    }

    /** Retains complete serialized bytes without constructing a base64 duplicate.
     * @param index admitted request index
     * @param bytes exact canonical complete response bytes
     * @throws IOException excessive response or duplicate storage
     */
    void response(int index, byte[] bytes) throws IOException {
        if (bytes.length == 0 || bytes.length > 1048576 || responses[index] != null) {
            throw new IOException("Response bound violated");
        }
        responses[index] = bytes;
        rows[index].put("responseBytes", bytes.length);
    }

    /** Emits all attempted records after teardown, preserving failed attempts.
     * @param report report receiving rows and untouched request indices
     * @param expected registered total attempts
     */
    void emit(ObjectNode report, int expected) {
        ArrayNode output = report.putArray("rows");
        for (int index = 0; index < count; index++) {
            if (responses[index] == null) rows[index].putNull("responseBase64");
            else rows[index].put("responseBase64", Base64.getEncoder().encodeToString(responses[index]));
            output.add(rows[index]);
        }
        ArrayNode skipped = report.putArray("notExecuted");
        for (int index = count; index < expected; index++) skipped.add(index);
    }

    /** Formats a bounded exception tree without losing suppressed cleanup failures.
     * @param error retained operation or teardown exception
     * @return finite structured exception observation
     */
    static ObjectNode failure(Throwable error) {
        ObjectNode value = JsonNodeFactory.instance.objectNode().put("class", error.getClass().getName());
        String message = String.valueOf(error.getMessage());
        value.put("message", message.substring(0, Math.min(message.length(), 2048)));
        ArrayNode suppressed = value.putArray("suppressed");
        for (Throwable item : error.getSuppressed()) {
            suppressed.addObject().put("class", item.getClass().getName()).put("message", String.valueOf(item.getMessage()));
        }
        return value;
    }

    /** Checks the minimal immediate envelope so obvious errors stop before another request.
     * @param response checked production response
     * @throws IOException failed validation or absent canonical operation identity
     */
    static void successful(JsonNode response) throws IOException {
        if (!"VALIDATED".equals(response.path("status").asText())) throw new IOException("Validation did not succeed");
        JsonNode data = response.path("data");
        if (!"BLOCK_SUPPORTED".equals(data.path("mode").asText())
                || !data.path("module").path("nodes").isArray() || data.path("module").path("nodes").size() != 500) {
            throw new IOException("Expected BLOCK_SUPPORTED 500-node response");
        }
        String nonce = response.path("requestId").asText();
        if (!java.util.UUID.fromString(nonce).toString().equals(nonce)) throw new IOException("Invalid response nonce");
    }
}
