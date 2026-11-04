package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Exact-byte, Unicode, immutable-envelope and process-lifecycle regression fixtures. */
class DocumentBoundaryTest {
    /** Original route spelling and JSON whitespace remain part of receipt authority.
     * @throws IOException malformed fixture
     */
    @Test
    void preservesOriginalRequestBytesAndRoute() throws IOException {
        byte[] body = "{\"title\": \"A\", \"idempotencyKey\":\"abcdefghijklmnop\"}".getBytes(StandardCharsets.UTF_8);
        DocumentRequest request = new DocumentRequest("CREATE", "/api/v1/documents", "CREATE", body);
        request.validate();
        assertArrayEquals(body, Base64.getDecoder().decode(request.identity().path("bodyBase64").textValue()));
        assertEquals("/api/v1/documents", request.identity().path("route").textValue());
        body[0] = '[';
        assertEquals('{', Base64.getDecoder().decode(request.identity().path("bodyBase64").textValue())[0]);
    }

    /** Duplicate JSON keys cannot be hidden by a tree-decoder last-value choice. */
    @Test
    void rejectsDuplicateKeys() {
        assertThrows(IOException.class, new Decode("{\"key\":1,\"key\":2}".getBytes(StandardCharsets.UTF_8)));
        assertThrows(IllegalArgumentException.class, new PublicDecode("{\"key\":1,\"key\":2}".getBytes(StandardCharsets.UTF_8)));
    }

    /** Invalid byte sequences and escaped lone surrogates never become replacement characters. */
    @Test
    void rejectsInvalidUnicode() {
        assertThrows(IOException.class, new Decode(new byte[]{'{', '"', 'x', '"', ':', '"', (byte) 0xc3, '"', '}'}));
        assertThrows(IOException.class, new Decode("{\"x\":\"\\ud800\"}".getBytes(StandardCharsets.UTF_8)));
    }

    /** Unknown new mutation fields cannot supply their own checked or authority flags.
     * @throws IOException malformed fixture
     */
    @Test
    void rejectsClientAuthorityFields() throws IOException {
        byte[] body = "{\"title\":\"A\",\"idempotencyKey\":\"abcdefghijklmnop\",\"checked\":true}".getBytes(StandardCharsets.UTF_8);
        DocumentRequest request = new DocumentRequest("CREATE", "/api/v1/documents", "CREATE", body);
        assertThrows(IllegalArgumentException.class, request::validate);
    }

    /** Empty revision zero is complete and receives fresh artifact identities without commands.
     * @throws IOException serialization failure
     */
    @Test
    void constructsDistinctEmptyArtifacts() throws IOException {
        ObjectNode first = DocumentArtifacts.empty("policy", "dependency");
        ObjectNode second = DocumentArtifacts.empty("policy", "dependency");
        assertNotEquals(first.path("artifactId"), second.path("artifactId"));
        assertEquals("", first.path("source").textValue());
        assertEquals(0, first.path("analysisDescriptors").size());
        assertEquals(1, first.path("module").path("version").intValue());
    }

    /** Returning a receipt preserves its original formatting and response request identity.
     * @throws IOException malformed fixture
     */
    @Test
    void replaysExactOriginalEnvelope() throws IOException {
        byte[] bytes = "{\"protocol\":1, \"requestId\":\"c134e810-a5a1-4f01-9690-286267103b9b\",\"status\":\"REJECTED\",\"data\":{}}".getBytes(StandardCharsets.UTF_8);
        JsonNode frame = JsonNodeFactory.instance.objectNode().put("responseBase64", Base64.getEncoder().encodeToString(bytes));
        assertArrayEquals(bytes, DocumentReplies.stored(frame));
    }

    /** One local-principal lease spans both old solver and new document validation work. */
    @Test
    void deniesConcurrentPrincipalLease() {
        WorkerCapacity.acquire();
        try {
            assertThrows(java.util.concurrent.RejectedExecutionException.class, WorkerCapacity::acquire);
        } finally {
            WorkerCapacity.release();
        }
    }

    /** A small well-framed process response is returned only after exit.
     * @throws Exception unavailable local fixture executable
     */
    @Test
    void exchangesAndReapsFrame() throws Exception {
        Process child = new ProcessBuilder("/bin/cat").start();
        byte[] result = FrameProcess.exchange(child, "{}".getBytes(StandardCharsets.UTF_8), 16, 1000);
        assertArrayEquals("{}\n".getBytes(StandardCharsets.UTF_8), result);
        assertFalse(child.isAlive());
    }

    /** Blocked stdin cannot bypass the external deadline or retain an active child.
     * @throws IOException unavailable local fixture executable
     */
    @Test
    void deadlineIncludesBlockedInputAndReaping() throws IOException {
        Process child = new ProcessBuilder("/bin/sleep", "2").start();
        assertThrows(IOException.class, new Exchange(child));
        assertFalse(child.isAlive());
    }

    /** Supplies one documented malformed byte fixture to the assertion framework. */
    private record Decode(byte[] bytes) implements Executable {
        /** Executes the strict decoder without replacing malformed data.
         * @throws IOException intended invalid fixture
         */
        @Override
        public void execute() throws IOException { DocumentJson.decode(bytes); }
    }

    /** Distinguishes client-malformed input from an unavailable private bridge frame. */
    private record PublicDecode(byte[] bytes) implements Executable {
        /** Executes the HTTP-specific decoder.
         * @throws IllegalArgumentException intended malformed request result
         */
        @Override
        public void execute() { DocumentJson.request(bytes); }
    }

    /** Owns a child whose stdin deliberately never drains. */
    private record Exchange(Process child) implements Executable {
        /** Exercises deadline handling with a payload larger than a pipe buffer.
         * @throws IOException expected deadline
         * @throws InterruptedException interrupted fixture
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            FrameProcess.exchange(child, new byte[2097152], 16, 100);
        }
    }
}
