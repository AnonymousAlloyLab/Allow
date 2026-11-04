package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Exact private sequence evidence; encoder reconstruction and response reserialization are explicit. */
final class WarmSequenceRecords {
    /** Prevents construction of the stateless evidence helper. */
    private WarmSequenceRecords() {}

    /** Records the retained generation and actual directly owned process incarnation.
     * @param token real production reservation
     * @return closed identity snapshot
     * @throws IOException missing actual attachment
     */
    static ObjectNode identity(WorkerReservation token) throws IOException {
        WarmProbeFiles.require(token.childPid() > 0 && token.childStartTicks().matches("[0-9]+"), "Sequence identity missing");
        return JsonNodeFactory.instance.objectNode().put("slot", token.slot()).put("generation", token.generation())
                .put("workerNonce", token.nonce()).put("group", token.group().relative())
                .put("pid", token.childPid()).put("start_ticks", token.childStartTicks());
    }

    /** Captures a read-only reference to the real transport for its independently observed READY clock.
     * @param pool actual same-incarnation coordinator
     * @param token current selected generation
     * @return real production transport, never a reconstructed readiness timestamp
     * @throws Exception unavailable or substituted transport
     */
    static WarmTransport transport(WarmWorkerPool pool, WorkerReservation token) throws Exception {
        Field pending = WarmWorkerPool.class.getDeclaredField("pending");
        Field reservation = WarmStandby.class.getDeclaredField("token");
        Field channel = WarmStandby.class.getDeclaredField("transport");
        pending.setAccessible(true);
        reservation.setAccessible(true);
        channel.setAccessible(true);
        Object worker = ((AtomicReference<?>) pending.get(pool)).get();
        WarmProbeFiles.require(worker instanceof WarmStandby && reservation.get(worker) == token, "Transport generation mismatch");
        Object value;
        while ((value = channel.get(worker)) == null && System.nanoTime() < token.startupDeadline()) TimeUnit.MILLISECONDS.sleep(1);
        WarmProbeFiles.require(value instanceof WarmTransport, "Actual sequence transport unavailable");
        return (WarmTransport) value;
    }

    /** Reuses the actual production encoder without silently adapting any registered fixture value.
     * @param binding actual isolated operation binding
     * @param request exact registered fixture values with its new nonce
     * @param context newly gate-assumed context
     * @param record operation evidence
     * @throws Exception encoding failure or semantic adaptation
     */
    static void frame(WarmRequestBinding binding, JsonNode request, DocumentValidationContext context,
            ObjectNode record) throws Exception {
        Method method = WarmWorkerPool.class.getDeclaredMethod("frame", WarmRequestBinding.class,
                JsonNode.class, DocumentValidationContext.class);
        method.setAccessible(true);
        byte[] bytes = (byte[]) method.invoke(null, binding, request.path("candidate"), context);
        WarmProbeFiles.require(JsonWire.decode(bytes, JsonNode.class).equals(request), "Sequence request changed");
        payload(record, "frame", bytes);
        record.put("frameObservation", "PRODUCTION_ENCODER_RECONSTRUCTION_NOT_PIPE_CAPTURE");
    }

    /** Keeps complete pool output, exact nonce/source and registered support-mode expectations.
     * @param request exact operation frame
     * @param planned pinned fixture and mode expectation
     * @param bytes full compact JSON response without a framing delimiter
     * @param record private operation evidence
     * @throws IOException malformed, unrelated or unexpected validation result
     */
    static void response(JsonNode request, JsonNode planned, byte[] bytes, ObjectNode record) throws IOException {
        JsonNode value = DocumentJson.decode(bytes);
        DocumentJson.fields(value, "protocol", "requestId", "status", "data");
        JsonNode data = value.path("data");
        WarmProbeFiles.require(value.path("protocol").isInt() && value.path("protocol").intValue() == 1
                && value.path("requestId").equals(request.path("requestId")) && value.path("status").asText().equals("VALIDATED")
                && data.path("mode").equals(planned.path("expected_mode"))
                && data.path("source").equals(request.path("candidate").path("source")), "Sequence response changed");
        WarmProbeFiles.require(Hashes.bytes(data.path("source").textValue().getBytes(StandardCharsets.UTF_8))
                .equals(data.path("sourceHash").textValue()), "Sequence source digest changed");
        payload(record, "response", bytes);
        record.put("responseCapture", "RESERIALIZED_COMPLETE_POOL_RESPONSE")
                .put("status", value.path("status").asText()).put("mode", data.path("mode").asText());
    }

    /** Binds complete compact JSON evidence without claiming an independent pipe capture.
     * @param record private operation evidence
     * @param prefix fixed frame or response role
     * @param bytes complete compact JSON representation
     */
    private static void payload(ObjectNode record, String prefix, byte[] bytes) {
        record.put(prefix + "Base64", Base64.getEncoder().encodeToString(bytes))
                .put(prefix + "Bytes", bytes.length).put(prefix + "Sha256", Hashes.bytes(bytes));
    }
}
