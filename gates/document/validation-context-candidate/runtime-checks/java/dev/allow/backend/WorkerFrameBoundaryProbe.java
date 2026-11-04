package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Path;

/** Structural adversarial boundary probe; its oversized candidate is not a valid public draft. */
public final class WorkerFrameBoundaryProbe {
    private static final int LIMIT = 2097152;
    private static final String NONCE = "00000000-0000-4000-8000-000000000000";
    private final Path child;

    /** Retains the explicitly supplied fixture executable path.
     * @param child one-shot local fixture script
     */
    private WorkerFrameBoundaryProbe(Path child) { this.child = child; }

    /** Runs all three exact private serialized-frame boundary cases.
     * @param args one absolute fixture path
     * @throws Exception any failed assertion or process error
     * @throws IllegalArgumentException missing or relative fixture path
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !Path.of(args[0]).isAbsolute()) throw new IllegalArgumentException("fixture path");
        WorkerFrameBoundaryProbe probe = new WorkerFrameBoundaryProbe(Path.of(args[0]));
        for (int size : new int[]{LIMIT - 1, LIMIT, LIMIT + 1}) probe.verify(size);
        System.out.println("PASS structural private worker frame boundaries");
    }

    /** Builds the same ordered envelope as the real worker with a fixed-length nonce.
     * @param candidate structural candidate payload
     * @return serialized frame length excluding transport newline
     * @throws IOException encoding failed
     */
    private int encodedLength(JsonNode candidate) throws IOException {
        ObjectNode frame = JsonNodeFactory.instance.objectNode();
        frame.put("protocol", 1).put("requestId", NONCE).put("policyVersion", "p").put("operation", "VALIDATE");
        frame.set("candidate", candidate.deepCopy());
        frame.set("baseArtifact", JsonNodeFactory.instance.objectNode());
        frame.set("ownedIdInventory", JsonNodeFactory.instance.objectNode());
        return JsonWire.encode(frame).length;
    }

    /** Exercises one actual worker call and checks launch, response and exit evidence.
     * @param size exact desired serialized bytes excluding newline
     * @throws Exception probe failure
     * @throws AssertionError unexpected size, execution or reaping
     */
    private void verify(int size) throws Exception {
        ObjectNode candidate = JsonNodeFactory.instance.objectNode().put("padding", "");
        int overhead = encodedLength(candidate);
        candidate.put("padding", "x".repeat(size - overhead));
        if (encodedLength(candidate) != size) throw new AssertionError("fixture size");
        Launcher launcher = new Launcher(child);
        DocumentWorker worker = new DocumentWorker(launcher, ProcessIdentity::startTicks);
        try {
            JsonNode result = worker.validate(candidate, JsonNodeFactory.instance.objectNode(),
                    JsonNodeFactory.instance.objectNode(), "p");
            if (size >= LIMIT || launcher.count != 1 || result.path("data").path("bytes").intValue() != size
                    || !"UNAVAILABLE".equals(result.path("status").textValue())) throw new AssertionError("acceptance");
            JsonNode proof = worker.recovery();
            if (proof.path("workerPid").longValue() <= 0 || proof.path("workerStartTicks").asText().isEmpty()
                    || proof.path("noWorkerStarted").asBoolean(true) || launcher.process.isAlive()) {
                throw new AssertionError("reaping evidence");
            }
        } catch (IOException error) {
            if (size < LIMIT || launcher.count != 0 || !worker.recovery().path("noWorkerStarted").asBoolean()
                    || !"Internal validation context exceeds limit".equals(error.getMessage())) throw error;
        }
        System.out.println("frame_bytes=" + size + " launches=" + launcher.count + " expected=" + (size < LIMIT ? "child" : "denied"));
    }

    /** Counts invocations and owns the child created solely for this probe. */
    private static final class Launcher implements SandboxLauncher {
        private final Path script;
        private int count;
        private Process process;

        /** Binds the local test fixture.
         * @param script absolute fixture path
         */
        private Launcher(Path script) { this.script = script; }

        /** Starts exactly one fixture process through the existing launcher seam.
         * @return owned one-shot child
         * @throws IOException launch failed
         */
        @Override
        public Process launch() throws IOException {
            count++;
            process = new ProcessBuilder("/usr/bin/python3", script.toString()).start();
            return process;
        }
    }
}
