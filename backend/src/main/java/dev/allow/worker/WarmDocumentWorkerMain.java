package dev.allow.worker;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.UUID;

/** Public-only bootstrap followed by exactly one private advisory validation. */
public final class WarmDocumentWorkerMain {
    /** Prevents construction of the fixed child entry point. */
    private WarmDocumentWorkerMain() {}

    /** Initializes only the reviewed public bootstrap, then accepts one validation frame.
     * @param arguments fixed helper-owned worker nonce and sealed build identity
     * @throws IOException invalid trusted arguments or private framing
     * @throws ClassNotFoundException incomplete application image
     */
    public static void main(String[] arguments) throws IOException, ClassNotFoundException {
        PrintStream protocol = System.out;
        System.setOut(System.err);
        validateArguments(arguments);
        bootstrap();
        protocol.print("ALLOW-WARM-1 " + arguments[0] + " " + arguments[1] + "\n");
        protocol.flush();
        if (protocol.checkError()) throw new IOException("Warm readiness output failed");
        DocumentWorkerMain.exchange(protocol, true);
    }

    /** Rejects any request-selected mode, malformed nonce, or noncanonical digest.
     * @param arguments fixed helper-owned identity arguments
     * @throws IOException invalid identity arguments
     */
    private static void validateArguments(String[] arguments) throws IOException {
        if (arguments.length != 2 || !arguments[1].matches("[0-9a-f]{64}")) {
            throw new IOException("Invalid warm identity");
        }
        try {
            if (!UUID.fromString(arguments[0]).toString().equals(arguments[0])) {
                throw new IOException("Invalid warm nonce");
            }
        } catch (IllegalArgumentException malformed) {
            throw new IOException("Invalid warm nonce", malformed);
        }
    }

    /** Performs exactly the approved empty JSON round-trip and initialized class loads.
     * @throws IOException unexpected public codec behavior
     * @throws ClassNotFoundException missing reviewed bootstrap class
     */
    private static void bootstrap() throws IOException, ClassNotFoundException {
        byte[] empty = "{}".getBytes(StandardCharsets.UTF_8);
        JsonNode decoded = JsonWire.decode(empty, JsonNode.class);
        if (!Arrays.equals(empty, JsonWire.encode(decoded))) {
            throw new IOException("Unexpected public bootstrap encoding");
        }
        ClassLoader loader = WarmDocumentWorkerMain.class.getClassLoader();
        Class.forName("dev.allow.document.DocumentEngine", true, loader);
        Class.forName("edu.mit.csail.sdg.parser.CompUtil", true, loader);
    }
}
