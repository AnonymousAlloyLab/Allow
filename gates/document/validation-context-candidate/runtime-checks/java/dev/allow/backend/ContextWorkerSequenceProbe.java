package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.List;

/** Offline joined one-shot fixture bridge and actual isolated validator process probe. */
public final class ContextWorkerSequenceProbe {
    private static final String DOCUMENT = "server:00000000-0000-4000-8000-000000000001";
    private final Path target;
    private final Path fixture;

    /** Binds separate copied build and throwaway bridge fixture directories.
     * @param target isolated copy of the compiled build
     * @param fixture private temporary fixture root
     */
    private ContextWorkerSequenceProbe(Path target, Path fixture) { this.target = target; this.fixture = fixture; }

    /** Exercises two independent bridge and actual sandbox worker lifetimes.
     * @param args isolated target copy and fixture directory
     * @throws Exception fixture, launch or assertion failure
     * @throws IllegalArgumentException invalid fixture paths
     * @throws AssertionError identity or lifecycle invariant failed
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !Path.of(args[0]).isAbsolute() || !Path.of(args[1]).isAbsolute()) {
            throw new IllegalArgumentException("absolute target and fixture required");
        }
        ContextWorkerSequenceProbe probe = new ContextWorkerSequenceProbe(Path.of(args[0]), Path.of(args[1]));
        probe.installBridge();
        long first = probe.runOne();
        long second = probe.runOne();
        if (first == second) throw new AssertionError("worker PID reused");
        probe.mutationDenied();
        System.out.println("PASS two bridge exits, fresh worker PIDs and copied-build mutation denial");
    }

    /** Creates a nonce-bound one-shot bridge fixture with a real process identity marker.
     * @throws IOException fixture creation failed
     */
    private void installBridge() throws IOException {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("documentId", DOCUMENT)
                .put("baseRevision", 0).put("headObserved", 0);
        result.set("artifact", DocumentArtifacts.empty("fixture-policy", "fixture-dependency"));
        result.putObject("ownedIdInventory");
        Files.write(fixture.resolve("context.json"), JsonWire.encode(result));
        Path executable = fixture.resolve(".tools/retrieval-venv/bin/python");
        Files.createDirectories(executable.getParent());
        String root = fixture.toString();
        String script = "#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n"
                + "f=json.load(sys.stdin)\nr=Path(" + JsonWireString.quote(root) + ")\n"
                + "(r/'bridge.pid').write_text(str(os.getpid()))\n"
                + "d=json.loads((r/'context.json').read_text())\n"
                + "print(json.dumps({'protocol':1,'requestId':f['requestId'],'status':'OK','data':d}))\n";
        Files.writeString(executable, script);
        Files.setPosixFilePermissions(executable, PosixFilePermissions.fromString("rwx------"));
    }

    /** Reads context after fixture bridge exit and invokes one fresh actual sandbox worker.
     * @return owned reaped sandbox process ID
     * @throws Exception bridge, worker or assertion failure
     * @throws AssertionError unexpected lifecycle, flags or response
     */
    private long runOne() throws Exception {
        DocumentValidationContext context = DocumentValidationContext.read(new DocumentGateway(fixture.toString()),
                DOCUMENT, 0, MissingNode.getInstance());
        long bridge = Long.parseLong(Files.readString(fixture.resolve("bridge.pid")));
        if (ProcessHandle.of(bridge).map(ProcessHandle::isAlive).orElse(false)) throw new AssertionError("bridge alive");
        BubblewrapLauncher launcher = new BubblewrapLauncher(target, true);
        List<String> command = launcher.command(target.resolve("solver/alloy.jar"));
        if (!command.containsAll(List.of("--as=2147483648", "--cpu=12", "-Xmx512m", "-Xss512k",
                "-XX:+UseSerialGC", "dev.allow.worker.DocumentWorkerMain"))) throw new AssertionError("flags");
        DocumentWorker worker = new DocumentWorker(launcher, ProcessIdentity::startTicks);
        ObjectNode candidate = JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", "sig Person {}");
        JsonNode result = worker.validate(candidate, context.artifact(), context.inventory(), "fixture-policy");
        JsonNode proof = worker.recovery();
        if (proof.path("noWorkerStarted").asBoolean(true) || proof.path("workerPid").longValue() <= 0
                || proof.path("workerStartTicks").asText().isEmpty() || !result.path("status").isTextual()) {
            throw new AssertionError("worker result or exit evidence");
        }
        System.out.println("bridge_exited=" + bridge + " worker_reaped=" + proof.path("workerPid").longValue());
        return proof.path("workerPid").longValue();
    }

    /** Changes only the copied build after capture and verifies launch fails before spawning.
     * @throws IOException copied-build read or write failed
     * @throws AssertionError changed build was launched
     */
    private void mutationDenied() throws IOException {
        BubblewrapLauncher launcher = new BubblewrapLauncher(target, true);
        Files.writeString(target.resolve("classes/probe-build-mutation"), "changed");
        try {
            Process child = launcher.launch();
            FrameProcess.reap(child);
            throw new AssertionError("changed build launched");
        } catch (IOException expected) {
            if (!"Build changed; restart required".equals(expected.getMessage())) throw expected;
        }
    }

    /** Encodes one fixture path as an exact JSON string for the test-only Python program. */
    private static final class JsonWireString {
        /** Prevents construction of this stateless helper. */
        private JsonWireString() { }
        /** Quotes a path using the production JSON encoder.
         * @param value path text
         * @return JSON string literal
         * @throws IOException encoding failed
         */
        private static String quote(String value) throws IOException {
            return new String(JsonWire.encode(value), java.nio.charset.StandardCharsets.UTF_8);
        }
    }
}
