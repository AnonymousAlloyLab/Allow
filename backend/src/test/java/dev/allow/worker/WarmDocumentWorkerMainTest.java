package dev.allow.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Actual entrypoint processes test protocol semantics, separately from sandbox acceptance. */
class WarmDocumentWorkerMainTest {
    private static final String NONCE = "a3fd8aa2-9632-417b-944f-9029e725d92e";
    private static final String BUILD = "a".repeat(64);
    @TempDir
    private Path directory;

    /** The warm and fresh decoders return identical full validation results.
     * @throws Exception failed test child or malformed result
     */
    @Test
    void agreesWithFreshValidation() throws Exception {
        byte[] request = frame("VALIDATE");
        Reply fresh = execute(false, request, List.of());
        Reply warm = execute(true, request, List.of(NONCE, BUILD));
        assertEquals(0, fresh.exit());
        assertEquals(0, warm.exit());
        assertEquals("ALLOW-WARM-1 " + NONCE + " " + BUILD, warm.lines().get(0));
        assertEquals(2, warm.lines().size());
        assertEquals(fresh.lines(), warm.lines().subList(1, 2));
        assertEquals("VALIDATED", JsonWire.decode(warm.lines().get(1).getBytes(StandardCharsets.UTF_8), JsonNode.class)
                .path("status").asText());
    }

    /** Warm mode rejects durable revalidation while the fresh adapter retains that mode.
     * @throws Exception failed test child
     */
    @Test
    void rejectsRevalidationOnlyInWarmMode() throws Exception {
        Reply warm = execute(true, frame("REVALIDATE"), List.of(NONCE, BUILD));
        Reply fresh = execute(false, frame("REVALIDATE"), List.of());
        assertNotEquals(0, warm.exit());
        assertEquals(1, warm.lines().size());
        assertEquals(0, fresh.exit());
        assertEquals(1, fresh.lines().size());
    }

    /** A second JSON frame is rejected by the same strict one-shot decoder.
     * @throws Exception failed test child
     */
    @Test
    void rejectsSecondPrivateFrame() throws Exception {
        String frame = new String(frame("VALIDATE"), StandardCharsets.UTF_8);
        Reply reply = execute(true, (frame + frame).getBytes(StandardCharsets.UTF_8), List.of(NONCE, BUILD));
        assertNotEquals(0, reply.exit());
        assertEquals(1, reply.lines().size());
    }

    /** Invalid trusted startup arguments never produce READY.
     * @throws Exception failed test child
     */
    @Test
    void rejectsMalformedIdentityBeforeReady() throws Exception {
        for (List<String> args : List.of(List.<String>of(), List.of("bad", BUILD), List.of(NONCE, BUILD.toUpperCase()))) {
            Reply reply = execute(true, new byte[0], args);
            assertNotEquals(0, reply.exit());
            assertTrue(reply.lines().isEmpty());
        }
    }

    /** Empty private input exits unsuccessfully after the public-only bootstrap.
     * @throws Exception failed test child
     */
    @Test
    void emitsReadyForPublicBootstrapOnly() throws Exception {
        Reply reply = execute(true, new byte[0], List.of(NONCE, BUILD));
        assertNotEquals(0, reply.exit());
        assertEquals(List.of("ALLOW-WARM-1 " + NONCE + " " + BUILD), reply.lines());
    }

    /** The exclusive payload cap permits 2097151 JSON bytes plus its one framing newline.
     * @throws Exception failed actual entrypoint or boundary assertion
     */
    @Test
    void agreesAtPayloadAndFramingBoundary() throws Exception {
        for (boolean warm : new boolean[]{false, true}) {
            List<String> identity = warm ? List.of(NONCE, BUILD) : List.of();
            Reply accepted = execute(warm, paddedFrame(2097152), identity);
            assertEquals(0, accepted.exit());
            assertEquals(warm ? 2 : 1, accepted.lines().size());
            Reply rejected = execute(warm, paddedFrame(2097153), identity);
            assertNotEquals(0, rejected.exit());
            assertEquals(warm ? 1 : 0, rejected.lines().size());
        }
    }

    /** Pads valid JSON with legal trailing whitespace and one final framing delimiter.
     * @param framedBytes total bytes including the final newline
     * @return exact-size complete private frame
     * @throws IOException unavailable fixture serialization
     */
    private byte[] paddedFrame(int framedBytes) throws IOException {
        byte[] original = frame("VALIDATE");
        byte[] result = Arrays.copyOf(original, framedBytes);
        Arrays.fill(result, original.length - 1, result.length - 1, (byte) ' ');
        result[result.length - 1] = '\n';
        return result;
    }

    /** Builds one fixed public fixture with the existing private document envelope.
     * @param operation exact requested validation operation
     * @return newline-terminated fixture frame
     * @throws IOException unavailable fixture encoding
     */
    private byte[] frame(String operation) throws IOException {
        ObjectNode value = JsonNodeFactory.instance.objectNode();
        value.put("protocol", 1).put("requestId", NONCE).put("policyVersion", "test-policy").put("operation", operation);
        value.putObject("candidate").put("mode", "SOURCE").put("source", "sig Person {} fact { #Person = 1 }");
        value.putObject("baseArtifact");
        value.putObject("ownedIdInventory");
        return (new String(JsonWire.encode(value), StandardCharsets.UTF_8) + "\n").getBytes(StandardCharsets.UTF_8);
    }

    /** Runs a bounded actual JVM with private fixture files, always reaping the direct child.
     * @param warm whether to select the new fixed entrypoint
     * @param input one fixture frame or malformed input
     * @param arguments trusted identity arguments
     * @return exit code and protocol lines
     * @throws Exception failed fixture process or file access
     */
    private Reply execute(boolean warm, byte[] input, List<String> arguments) throws Exception {
        Path output = Files.createTempFile(directory, "stdout-", ".txt");
        Path error = Files.createTempFile(directory, "stderr-", ".txt");
        List<String> command = new ArrayList<>(List.of(System.getProperty("java.home") + "/bin/java", "-Xmx128m",
                "-cp", System.getProperty("java.class.path"), warm ? WarmDocumentWorkerMain.class.getName()
                : DocumentWorkerMain.class.getName()));
        command.addAll(arguments);
        ProcessBuilder builder = new ProcessBuilder(command).redirectOutput(output.toFile()).redirectError(error.toFile());
        builder.environment().clear();
        Process child = builder.start();
        try {
            child.getOutputStream().write(input);
            child.getOutputStream().close();
            assertTrue(child.waitFor(8, TimeUnit.SECONDS));
            return new Reply(child.exitValue(), Files.readAllLines(output));
        } finally {
            child.destroyForcibly();
            assertTrue(child.waitFor(3, TimeUnit.SECONDS));
        }
    }

    /** Encapsulates one test child outcome without retaining production model state. */
    private record Reply(int exit, List<String> lines) {}
}
