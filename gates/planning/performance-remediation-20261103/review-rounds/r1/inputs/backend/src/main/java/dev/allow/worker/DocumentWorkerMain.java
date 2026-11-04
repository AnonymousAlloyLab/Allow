package dev.allow.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.document.DocumentEngine;
import dev.allow.document.DocumentValidationException;
import java.io.IOException;
import java.io.PrintStream;
import java.util.HashSet;
import java.util.Set;

/** One-shot document adapter in the same restricted JVM/sandbox as the solver. */
public final class DocumentWorkerMain {
    /** Prevents construction of this child entry point. */
    private DocumentWorkerMain() {}

    /** Reads and emits one bounded private frame, redirecting library logging to stderr.
     * @param arguments unused fixed entry-point arguments
     * @throws IOException malformed frame or output failure
     */
    public static void main(String[] arguments) throws IOException {
        PrintStream protocol = System.out;
        System.setOut(System.err);
        byte[] input = System.in.readNBytes(2097153);
        if (input.length > 2097152 || input.length == 0 || input[input.length - 1] != '\n') {
            throw new IOException("Invalid document frame");
        }
        JsonNode request = JsonWire.decode(input, JsonNode.class);
        validate(request);
        byte[] output = JsonWire.encode(execute(request));
        if (output.length >= 1048576) throw new IOException("Document result exceeds limit");
        protocol.write(output);
        protocol.write('\n');
        protocol.flush();
    }

    /** Requires the complete server-owned validation context.
     * @param request parsed internal envelope
     * @throws IOException invalid operation identity
     */
    private static void validate(JsonNode request) throws IOException {
        Set<String> fields = new HashSet<>();
        request.fieldNames().forEachRemaining(fields::add);
        if (!fields.equals(Set.of("protocol", "requestId", "policyVersion", "operation", "candidate", "baseArtifact", "ownedIdInventory"))
                || !request.path("protocol").isInt() || request.path("protocol").intValue() != 1
                || !request.path("requestId").isTextual() || !request.path("policyVersion").isTextual()
                || !Set.of("VALIDATE", "REVALIDATE").contains(request.path("operation").asText())) {
            throw new IOException("Invalid document context");
        }
    }

    /** Distinguishes deterministic invalid input from unavailable validation infrastructure.
     * @param request strict internal request
     * @return bounded response with echoed identity
     */
    private static JsonNode execute(JsonNode request) {
        ObjectNode response = JsonNodeFactory.instance.objectNode();
        response.put("protocol", 1).put("requestId", request.path("requestId").textValue());
        try {
            JsonNode result = engine(request);
            response.put("status", "VALIDATED").set("data", result);
        } catch (DocumentValidationException invalid) {
            ObjectNode data = JsonNodeFactory.instance.objectNode().put("code", invalid.code());
            data.set("diagnostics", invalid.diagnostics());
            response.put("status", "INVALID").set("data", data);
        } catch (Exception | StackOverflowError unavailable) {
            response.put("status", "UNAVAILABLE").set("data", JsonNodeFactory.instance.objectNode());
        }
        return response;
    }

    /** Dispatches only server-selected validation modes inside the sandbox.
     * @param request authenticated internal context
     * @return independent checked content
     * @throws DocumentValidationException deterministic invalid candidate
     */
    private static JsonNode engine(JsonNode request) throws DocumentValidationException {
        DocumentEngine engine = new DocumentEngine();
        if (request.path("operation").asText().equals("REVALIDATE")) {
            return engine.revalidate(request.path("baseArtifact"), request.path("ownedIdInventory"),
                    request.path("policyVersion").textValue());
        }
        return engine.validate(request.path("candidate"), request.path("baseArtifact"),
                request.path("ownedIdInventory"), request.path("policyVersion").textValue());
    }
}
