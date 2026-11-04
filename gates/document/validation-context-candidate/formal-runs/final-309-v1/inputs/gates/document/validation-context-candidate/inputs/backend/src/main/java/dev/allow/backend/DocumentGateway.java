package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/** Operation-only private persistence bridge; PostgreSQL access remains in sql_connections. */
@Service
final class DocumentGateway {
    private final Path root;

    /** Stores the trusted installation root provided by the local launcher.
     * @param directory absolute Allow installation
     */
    DocumentGateway(@Value("${allow.corpus.root:}") String directory) {
        root = directory.isBlank() ? null : Path.of(directory).toAbsolutePath().normalize();
    }

    /** Executes one closed operation with an unguessable per-call response identity.
     * @param operation installed CLI operation
     * @param arguments server-owned operation arguments
     * @return complete validated internal envelope
     * @throws IOException unavailable bridge or invalid response
     * @throws InterruptedException caller interruption after child exit
     */
    JsonNode request(String operation, JsonNode arguments) throws IOException, InterruptedException {
        String nonce = UUID.randomUUID().toString();
        ObjectNode frame = com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode();
        frame.put("protocol", 1).put("requestId", nonce).put("operation", operation);
        frame.set("args", arguments.deepCopy());
        byte[] input = JsonWire.encode(frame);
        if (input.length >= 3145728) throw new IOException("Persistence frame exceeds limit");
        byte[] output = FrameProcess.exchange(launch(), input, 1572865, 20000);
        JsonNode result = DocumentJson.decode(output);
        DocumentJson.fields(result, "protocol", "requestId", "status", "data");
        if (!result.path("protocol").isInt() || result.path("protocol").intValue() != 1
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
                root.resolve(".tools/retrieval-venv/bin/python").toString(), "-m", "allow_documents.cli");
        builder.directory(root.toFile());
        builder.environment().clear();
        builder.environment().put("PYTHONPATH", root.resolve("retrieval").toString());
        builder.environment().put("ALLOW_CORPUS_RUNTIME", root.resolve(".runtime/corpus").toString());
        builder.environment().put("LANGSMITH_TRACING", "false");
        return builder.start();
    }
}
