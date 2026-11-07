package dev.allow.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.document.DocumentEngine;
import dev.allow.document.ComparisonEngine;
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
        exchange(protocol, false);
    }

    /** Executes the same bounded one-shot exchange for fresh and advisory entry points.
     * @param protocol original output stream reserved for the private protocol
     * @param advisoryOnly whether durable revalidation must be rejected
     * @throws IOException malformed frame or output failure
     */
    static void exchange(PrintStream protocol, boolean advisoryOnly) throws IOException {
        byte[] input = System.in.readNBytes(2097153);
        if (input.length > 2097152 || input.length == 0 || input[input.length - 1] != '\n') {
            throw new IOException("Invalid document frame");
        }
        JsonNode request = JsonWire.decode(input, JsonNode.class);
        validate(request);
        if (advisoryOnly && !request.path("operation").asText().equals("VALIDATE")) {
            throw new IOException("Invalid advisory operation");
        }
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
                || !Set.of("VALIDATE", "REVALIDATE", "COMPARE", "COMPARISON_MODEL", "COMPARE_MODELS", "ORACLE_PARITY").contains(request.path("operation").asText())) {
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
            response.put("status", comparison(request) ? "UNSUPPORTED" : "INVALID").set("data", data);
        } catch (edu.mit.csail.sdg.alloy4.Err | IllegalArgumentException rejected) {
            if (comparison(request)) {
                response.put("status", "UNSUPPORTED").set("data", JsonNodeFactory.instance.objectNode()
                        .put("reason", reason(rejected)));
            } else response.put("status", "UNAVAILABLE").set("data", JsonNodeFactory.instance.objectNode());
        } catch (Exception | StackOverflowError unavailable) {
            response.put("status", comparison(request) ? "ERROR" : "UNAVAILABLE").set("data", JsonNodeFactory.instance.objectNode());
        }
        return response;
    }

    /** Dispatches only server-selected validation modes inside the sandbox.
     * @param request authenticated internal context
     * @return independent checked content
     * @throws DocumentValidationException deterministic invalid candidate
     * @throws IOException isolated parser failure
     * @throws edu.mit.csail.sdg.alloy4.Err unsupported Alloy source
     */
    private static JsonNode engine(JsonNode request) throws DocumentValidationException, IOException, edu.mit.csail.sdg.alloy4.Err {
        if (comparison(request)) return new ComparisonEngine().execute(request.path("operation").asText(), request.path("candidate"),
                request.path("baseArtifact"), request.path("ownedIdInventory"), request.path("policyVersion").asText());
        DocumentEngine engine = new DocumentEngine();
        if (request.path("operation").asText().equals("REVALIDATE")) {
            return engine.revalidate(request.path("baseArtifact"), request.path("ownedIdInventory"),
                    request.path("policyVersion").textValue());
        }
        return engine.validate(request.path("candidate"), request.path("baseArtifact"),
                request.path("ownedIdInventory"), request.path("policyVersion").textValue());
    }
    /** Identifies the closed expensive comparison operations.
     * @param request owned internal frame
     * @return whether comparison dispatch is selected
     */
    private static boolean comparison(JsonNode request) {
        return Set.of("COMPARE", "COMPARISON_MODEL", "COMPARE_MODELS", "ORACLE_PARITY").contains(request.path("operation").asText());
    }

    /** Bounds authored rejection text without reflecting source fragments or paths.
     * @param failure deterministic admission failure
     * @return bounded diagnostic
     */
    private static String reason(Exception failure) {
        if (failure instanceof edu.mit.csail.sdg.alloy4.Err) return "Alloy rejected unsupported model syntax or typing.";
        String text = failure.getMessage();
        return text == null ? "Unsupported comparison input." : text.substring(0, Math.min(200, text.length()));
    }

}
