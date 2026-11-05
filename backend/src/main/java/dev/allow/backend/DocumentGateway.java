package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/** Operation-only private persistence bridge; PostgreSQL access remains in sql_connections. */
@Service
final class DocumentGateway {
    private final Path root;
    private final JsonNode scope;

    /** Stores the trusted installation root provided by the local launcher.
     * @param directory absolute Allow installation
     */
    @Autowired
    DocumentGateway(@Value("${allow.corpus.root:}") String directory) {
        root = directory.isBlank() ? null : Path.of(directory).toAbsolutePath().normalize();
        scope = null;
    }

    /** Creates an immutable bridge for a server-allocated public scope.
     * @param root trusted installation root
     * @param scope closed server-generated identity
     */
    private DocumentGateway(Path root, JsonNode scope) {
        this.root = root;
        this.scope = scope.deepCopy();
    }

    /** Binds a new bridge without changing the private bridge or shared environment.
     * @param identity trusted allocated public scope
     * @return independently scoped bridge
     */
    DocumentGateway scoped(JsonNode identity) { return new DocumentGateway(root, identity); }

    /** Executes one closed operation with an unguessable per-call response identity.
     * @param operation installed CLI operation
     * @param arguments server-owned operation arguments
     * @return complete validated internal envelope
     * @throws IOException unavailable bridge or invalid response
     * @throws InterruptedException caller interruption after child exit
     */
    JsonNode request(String operation, JsonNode arguments) throws IOException, InterruptedException {
        return exchange(operation, arguments, 20000);
    }

    /** Clamps candidate context work to its original admission budget.
     * @param operation installed CLI operation
     * @param arguments server-owned operation arguments
     * @param deadline original advisory success deadline
     * @return complete checked envelope only while the budget remains valid
     * @throws IOException unavailable, malformed or late response
     * @throws InterruptedException cancelled private bridge
     */
    JsonNode request(String operation, JsonNode arguments, WarmDeadline deadline)
            throws IOException, InterruptedException {
        JsonNode result = exchange(operation, arguments, Math.min(20000, deadline.remainingMillis()));
        deadline.check();
        return result;
    }

    /** Exchanges the unchanged closed CLI frame under a caller-selected bounded wait.
     * @param operation installed CLI operation
     * @param arguments server-owned arguments
     * @param millis remaining process wait budget
     * @return complete validated private response
     * @throws IOException unavailable bridge or invalid response
     * @throws InterruptedException interrupted caller after child cleanup
     */
    private JsonNode exchange(String operation, JsonNode arguments, long millis)
            throws IOException, InterruptedException {
        String nonce = UUID.randomUUID().toString();
        ObjectNode frame = com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode();
        int protocol = scope == null ? 1 : 2;
        frame.put("protocol", protocol).put("requestId", nonce).put("operation", operation);
        if (scope != null) frame.set("scope", scope.deepCopy());
        frame.set("args", arguments.deepCopy());
        byte[] input = JsonWire.encode(frame);
        if (input.length >= 3145728) throw new IOException("Persistence frame exceeds limit");
        byte[] output = FrameProcess.exchange(launch(), input, 1572865, millis);
        JsonNode result = DocumentJson.decode(output);
        DocumentJson.fields(result, "protocol", "requestId", "status", "data");
        if (!result.path("protocol").isInt() || result.path("protocol").intValue() != protocol
                || !nonce.equals(result.path("requestId").asText()) || !result.path("data").isObject()) {
            throw new IOException("Persistence response identity mismatch");
        }
        return result;
    }

    /** Starts only the installed private CLI, without inherited SQL or tracing configuration.
     * @return owned bounded child
     * @throws IOException unavailable trusted installation
     */
    private Process launch() throws IOException {
        if (root == null || !Files.isRegularFile(root.resolve(".tools/retrieval-venv/bin/python"))) {
            throw new IOException("Document persistence unavailable");
        }
        ProcessBuilder builder = new ProcessBuilder("/usr/bin/prlimit", "--as=2147483648", "--cpu=20", "--",
                root.resolve(".tools/retrieval-venv/bin/python").toString(), "-B", "-m", "allow_documents.cli");
        builder.directory(root.toFile());
        builder.environment().clear();
        builder.environment().put("PYTHONPATH", root.resolve("retrieval").toString());
        builder.environment().put("PYTHONDONTWRITEBYTECODE", "1");
        builder.environment().put("ALLOW_CORPUS_RUNTIME", root.resolve(".runtime/corpus").toString());
        builder.environment().put("LANGSMITH_TRACING", "false");
        return builder.start();
    }
}
