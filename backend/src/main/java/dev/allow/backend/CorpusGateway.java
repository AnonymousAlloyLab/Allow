package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/** Supervises the local, read-only corpus bridge; HTTP clients never supply vectors or pool labels. */
@Service
final class CorpusGateway {
    private final Path root;
    private final Semaphore capacity = new Semaphore(2);

    /** Stores an explicit trusted installation root; an absent configuration disables corpus requests.
     * @param directory Allow installation root supplied by its launcher
     */
    CorpusGateway(@Value("${allow.corpus.root:}") String directory) {
        root = directory.isBlank() ? null : Path.of(directory).toAbsolutePath().normalize();
    }

    /** Executes one bounded metadata or stored-record retrieval request.
     * @param operation status, list or search
     * @param recordId stored immutable record identity, empty outside search
     * @param limit maximum returned records
     * @return strict response with an echoed private request nonce
     * @throws IOException unavailable runtime or invalid bridge response
     * @throws InterruptedException interrupted execution
     * @throws RejectedExecutionException concurrent capacity exhausted
     */
    JsonNode request(String operation, String recordId, int limit) throws IOException, InterruptedException {
        if (root == null || !Files.isRegularFile(root.resolve(".tools/retrieval-venv/bin/python"))) {
            throw new IOException("Corpus runtime unavailable");
        }
        if (!capacity.tryAcquire()) throw new RejectedExecutionException("Corpus capacity reached");
        try {
            String nonce = UUID.randomUUID().toString();
            byte[] input = JsonWire.encode(Map.of("protocol", 1, "requestId", nonce,
                    "operation", operation, "recordId", recordId, "limit", limit));
            return execute(input, nonce);
        } finally {
            capacity.release();
        }
    }

    /** Starts only the installed bridge with a fixed argument vector and bounded child resources.
     * @return owned local process
     * @throws IOException unavailable executable
     */
    private Process launch() throws IOException {
        ProcessBuilder builder = new ProcessBuilder("/usr/bin/prlimit", "--as=2147483648", "--cpu=20", "--",
                root.resolve(".tools/retrieval-venv/bin/python").toString(), "-B", "-m", "allow_retrieval.cli");
        builder.directory(root.toFile());
        builder.environment().put("PYTHONPATH", root.resolve("retrieval").toString());
        builder.environment().put("PYTHONDONTWRITEBYTECODE", "1");
        builder.environment().put("ALLOW_CORPUS_RUNTIME", root.resolve(".runtime/corpus").toString());
        builder.environment().put("LANGSMITH_TRACING", "false");
        builder.environment().put("OPENBLAS_NUM_THREADS", "1");
        return builder.start();
    }

    /** Drains both output pipes concurrently while enforcing a wall deadline and complete reaping.
     * @param input small trusted request frame
     * @param nonce required response identity
     * @return decoded bounded result
     * @throws IOException failed or malformed child result
     * @throws InterruptedException interrupted execution
     */
    private JsonNode execute(byte[] input, String nonce) throws IOException, InterruptedException {
        Process process = launch();
        JobControl control = new JobControl();
        control.attach(process);
        ExecutorService readers = Executors.newFixedThreadPool(2);
        Future<byte[]> stdout = readers.submit(new BoundedCapture(process.getInputStream(), 2097152, control));
        Future<byte[]> stderr = readers.submit(new BoundedCapture(process.getErrorStream(), 16384, control));
        try {
            try (var output = process.getOutputStream()) { output.write(input); output.write('\n'); }
            if (!process.waitFor(20, TimeUnit.SECONDS)) throw new IOException("Corpus deadline exceeded");
            byte[] result = stdout.get(2, TimeUnit.SECONDS);
            stderr.get(2, TimeUnit.SECONDS);
            if (process.exitValue() != 0) throw new IOException("Corpus bridge failed");
            return decode(result, nonce);
        } catch (ExecutionException | TimeoutException error) {
            throw new IOException("Corpus bridge output unavailable", error);
        } finally {
            control.stop();
            process.waitFor();
            readers.shutdownNow();
        }
    }

    /** Rejects malformed envelopes, unrelated responses and unexpected protocol/status values.
     * @param bytes complete child output
     * @param nonce expected request identity
     * @return validated response envelope
     * @throws IOException invalid output
     */
    private JsonNode decode(byte[] bytes, String nonce) throws IOException {
        JsonNode result = JsonWire.decode(bytes, JsonNode.class);
        if (!result.isObject() || result.path("protocol").asInt(-1) != 1
                || !nonce.equals(result.path("requestId").asText()) || !result.has("data")
                || !java.util.Set.of("OK", "UNAVAILABLE", "ERROR", "FORBIDDEN", "NOT_FOUND")
                    .contains(result.path("status").asText())) {
            throw new IOException("Corpus bridge identity mismatch");
        }
        return result;
    }
}
