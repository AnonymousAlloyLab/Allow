package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;

/** Owned fixed-entrypoint framed graph process with no listener or SQL capability. */
final class AiProcess {
    private final AiConfiguration configuration;
    private final AiService service;
    private final AiJob job;

    /** Binds only trusted installation capabilities, never browser-selected executables.
     * @param configuration closed installation profile
     * @param service authoritative host callbacks
     * @param job exact owned job
     */
    AiProcess(AiConfiguration configuration, AiService service, AiJob job) {
        this.configuration = configuration;
        this.service = service;
        this.job = job;
    }

    /** Executes the real graph, retaining ownership through actual child reap.
     * @throws IOException unavailable process or malformed bounded IPC
     * @throws InterruptedException cancelled host validation after cleanup
     */
    void run() throws IOException, InterruptedException {
        Process process = launch();
        job.attach(process);
        JsonNode terminal;
        try {
            write(process.getOutputStream(), frame(0, "START", start()));
            terminal = exchange(process);
            if (!process.waitFor(job.remaining(), java.util.concurrent.TimeUnit.MILLISECONDS) || process.exitValue() != 0) {
                throw new IOException("AI process unavailable");
            }
        } finally { FrameProcess.reap(process); }
        service.result(job, terminal);
    }

    /** Launches system Python without site initialization, ambient configuration or stderr logs.
     * @return owned graph process
     * @throws IOException missing reviewed entrypoint or failed process launch
     */
    private Process launch() throws IOException {
        Path entry = configuration.root().resolve("services/ai/entry.py");
        if (!Files.isRegularFile(entry)) throw new IOException("AI entry unavailable");
        ProcessBuilder builder = new ProcessBuilder("/usr/bin/prlimit", "--core=0", "/usr/bin/python3", "-I", "-S", "-B", entry.toString());
        builder.directory(configuration.root().toFile());
        builder.environment().clear();
        builder.redirectError(ProcessBuilder.Redirect.DISCARD);
        return builder.start();
    }

    /** Builds the only credential-bearing initial frame without retaining it in the job.
     * @return closed private initial data
     */
    private ObjectNode start() {
        ObjectNode data = configuration.start();
        return data.put("operationId", job.id()).put("source", job.anonymousSource()).put("intent", job.request().text("intent"))
                .put("feature", job.request().text("kind")).put("binding", job.binding());
    }

    /** Consumes strictly ordered bounded frames and answers only expected callback kinds.
     * @param process directly owned graph process
     * @return final inert result only after fixed callback exchange
     * @throws IOException malformed, truncated or oversized child frames
     * @throws InterruptedException cancelled scoped host work
     */
    private JsonNode exchange(Process process) throws IOException, InterruptedException {
        for (int sequence = 1; sequence <= 64; sequence++) {
            job.remaining();
            JsonNode incoming = DocumentJson.decode(line(process.getInputStream()));
            check(incoming, sequence);
            String kind = incoming.path("kind").asText();
            JsonNode data = incoming.path("data");
            if (kind.equals("RESULT")) return data;
            ObjectNode reply = callback(kind, data);
            write(process.getOutputStream(), frame(sequence, "REPLY", reply));
        }
        throw new IOException("AI frame limit");
    }

    /** Enforces exact framing identities before any requested callback is executed.
     * @param incoming decoded bounded child value
     * @param sequence expected monotonic sequence
     * @throws IOException unrelated or malformed frame
     */
    private void check(JsonNode incoming, int sequence) throws IOException {
        DocumentJson.fields(incoming, "protocol", "nonce", "seq", "kind", "data");
        if (!incoming.path("protocol").isInt() || incoming.path("protocol").intValue() != 1
                || !incoming.path("nonce").asText().equals(job.nonce()) || !incoming.path("seq").isInt()
                || incoming.path("seq").intValue() != sequence || !incoming.path("kind").isTextual() || !incoming.path("data").isObject()) {
            throw new IOException("AI frame identity");
        }
    }

    /** Exposes only fixed authority, consent and isolated verification host callbacks.
     * @param kind closed requested operation
     * @param data bounded operation data
     * @return closed callback result
     * @throws IOException unavailable scoped verifier or document
     * @throws InterruptedException cancelled owned host operation
     * @throws AiFailure denied or malformed boundary state
     */
    private ObjectNode callback(String kind, JsonNode data) throws IOException, InterruptedException {
        service.current(job);
        if (kind.equals("AUTH")) {
            DocumentJson.fields(data, "binding");
            if (!data.path("binding").asText().equals(job.binding())) throw new AiFailure("IPC_INVALID");
            return com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode().put("approved", true);
        }
        if (kind.equals("PREPARED")) {
            job.preview(data);
            return com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode().put("approved", job.awaitConsent());
        }
        if (kind.equals("VERIFY")) {
            DocumentJson.fields(data, "source", "timeout");
            if (!data.path("source").isTextual() || !data.path("timeout").isNumber()
                    || data.path("timeout").doubleValue() <= 0 || data.path("timeout").doubleValue() > 10) throw new AiFailure("IPC_INVALID");
            return service.verify(job, data.path("source").textValue());
        }
        throw new AiFailure("IPC_INVALID");
    }

    /** Creates exact versioned private frame metadata.
     * @param sequence monotonic operation index
     * @param kind START or REPLY
     * @param data bounded internal payload
     * @return closed frame
     */
    private ObjectNode frame(int sequence, String kind, ObjectNode data) {
        ObjectNode frame = com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode()
                .put("protocol", 1).put("nonce", job.nonce()).put("seq", sequence).put("kind", kind);
        frame.set("data", data);
        return frame;
    }

    /** Writes only one bounded strict JSON frame and flushes without logging.
     * @param output owned child stdin
     * @param value exact private frame
     * @throws IOException unavailable or oversized transport
     */
    private void write(OutputStream output, ObjectNode value) throws IOException {
        byte[] bytes = dev.allow.worker.JsonWire.encode(value);
        if (bytes.length >= 262144) throw new IOException("AI frame limit");
        output.write(bytes);
        output.write('\n');
        output.flush();
    }

    /** Reads one frame with a strict byte cap; the owner deadline kills stalled children.
     * @param input directly owned child stdout
     * @return one newline-free exact JSON frame
     * @throws IOException truncated, CR-containing or oversized output
     */
    private byte[] line(InputStream input) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        for (int index = 0; index < 262144; index++) {
            int next = input.read();
            if (next == '\n') return bytes.toByteArray();
            if (next < 0 || next == '\r') throw new IOException("AI frame unavailable");
            bytes.write(next);
        }
        throw new IOException("AI frame limit");
    }
}
