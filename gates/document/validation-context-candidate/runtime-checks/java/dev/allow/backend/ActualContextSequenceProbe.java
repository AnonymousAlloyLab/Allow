package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Offline real scoped context bridge and fresh sandbox worker sequence probe. */
public final class ActualContextSequenceProbe {
    private final Path root;
    private final Path target;
    private final DocumentGateway gateway;

    /** Retains installation and isolated worker-copy roots.
     * @param root active private store installation
     * @param target isolated target copy
     */
    private ActualContextSequenceProbe(Path root, Path target) {
        this.root = root;
        this.target = target;
        this.gateway = new DocumentGateway(root.toString());
    }

    /** Runs two scoped context reads followed by distinct actual sandbox workers.
     * @param args absolute installation and copied-target paths
     * @throws Exception input, scope, process or validation failure
     * @throws IllegalArgumentException incorrect path arguments
     * @throws AssertionError lifecycle or command mismatch
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !Path.of(args[0]).isAbsolute() || !Path.of(args[1]).isAbsolute()) {
            throw new IllegalArgumentException("absolute root and target required");
        }
        ActualContextSequenceProbe probe = new ActualContextSequenceProbe(Path.of(args[0]), Path.of(args[1]));
        String document = probe.document();
        long first = probe.runOne(document);
        long second = probe.runOne(document);
        if (first == second) throw new AssertionError("worker PID reused");
        System.out.println("PASS real context transactions, distinct workers and exact command");
    }

    /** Selects an already authorized document without printing identity or authority.
     * @return server-owned document identifier
     * @throws Exception bridge or missing fixture
     * @throws AssertionError no scoped document is available
     */
    private String document() throws Exception {
        JsonNode result = gateway.request("list", JsonNodeFactory.instance.objectNode());
        JsonNode docs = result.path("data").path("documents");
        if (!"OK".equals(result.path("status").asText()) || !docs.isArray() || docs.isEmpty()) {
            throw new AssertionError("no authorized document available");
        }
        return docs.get(0).path("documentId").textValue();
    }

    /** Runs context, confirms its bridge exit, then runs and reaps a fresh validator.
     * @param document authorized existing document
     * @return reaped worker PID
     * @throws Exception bridge, launch, validation or assertion failure
     * @throws AssertionError context or worker lifecycle mismatch
     */
    private long runOne(String document) throws Exception {
        ChildMonitor monitor = new ChildMonitor();
        Thread watcher = new Thread(monitor, "context-child-monitor");
        watcher.start();
        DocumentValidationContext context;
        try { context = DocumentValidationContext.read(gateway, document, 0, MissingNode.getInstance()); }
        finally { monitor.stop(); watcher.join(); }
        monitor.verify();
        BubblewrapLauncher launcher = new BubblewrapLauncher(target, true);
        checkCommand(launcher.command(target.resolve("solver/alloy.jar")));
        String dependency = BuildIdentity.read(target);
        DocumentWorker worker = new DocumentWorker(launcher, ProcessIdentity::startTicks);
        ObjectNode candidate = JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", "sig Person {}");
        JsonNode result = worker.validate(candidate, context.artifact(), context.inventory(), "document-v1:" + dependency);
        JsonNode proof = worker.recovery();
        if (!"VALIDATED".equals(result.path("status").asText()) || proof.path("noWorkerStarted").asBoolean(true)
                || proof.path("workerPid").longValue() <= 0 || proof.path("workerStartTicks").asText().isEmpty()) {
            throw new AssertionError("worker did not validate and reap");
        }
        System.out.println("bridge_pid=" + monitor.pid() + " bridge_ticks=" + monitor.ticks()
                + " worker_pid=" + proof.path("workerPid").longValue() + " worker_ticks=" + proof.path("workerStartTicks").asText());
        return proof.path("workerPid").longValue();
    }

    /** Compares the complete command against the frozen launcher protocol.
     * @param actual production launcher command
     * @throws IOException platform path cannot be resolved
     * @throws AssertionError any argument differs
     */
    private void checkCommand(List<String> actual) throws IOException {
        Path home = Path.of(System.getProperty("java.home")).toRealPath();
        List<String> expected = List.of("/usr/bin/prlimit", "--as=2147483648", "--cpu=12", "--fsize=8388608",
                "/usr/bin/bwrap", "--unshare-all", "--new-session", "--die-with-parent", "--cap-drop", "ALL",
                "--ro-bind", home.toString(), home.toString(), "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                "--ro-bind", "/etc/java-17-openjdk", "/etc/java-17-openjdk", "--ro-bind", target.resolve("classes").toString(), "/app/classes",
                "--ro-bind", target.resolve("dependency").toString(), "/app/dependency", "--ro-bind", target.resolve("solver/alloy.jar").toString(), "/app/solver.jar",
                "--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev", "--chdir", "/tmp", home.resolve("bin/java").toString(),
                "-Xmx512m", "-Xss512k", "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=2", "-XX:MaxMetaspaceSize=128m",
                "-XX:CompressedClassSpaceSize=64m", "-XX:ReservedCodeCacheSize=48m", "-Djava.awt.headless=true",
                "-Dfile.encoding=UTF-8", "-Djava.io.tmpdir=/tmp", "-cp", "/app/classes:/app/solver.jar:/app/dependency/*",
                "dev.allow.worker.DocumentWorkerMain");
        if (!actual.equals(expected)) throw new AssertionError("launcher command differs");
        System.out.println("launcher_command=" + actual);
    }

    /** Monitors only direct children of this standalone probe during a single bridge call. */
    private static final class ChildMonitor implements Runnable {
        private volatile boolean active = true;
        private volatile long found;
        private volatile String start;
        /** Stops the bounded observer before worker launch. */
        private void stop() { active = false; }
        /** Returns the observed bridge PID.
         * @return child PID
         */
        private long pid() { return found; }
        /** Returns the observed kernel incarnation.
         * @return start ticks
         */
        private String ticks() { return start; }
        /** Samples owned direct children until the bridge call completes. */
        @Override
        public void run() {
            while (active) {
                ProcessHandle.current().children().forEach(this::capture);
                try { Thread.sleep(1); } catch (InterruptedException failure) { Thread.currentThread().interrupt(); return; }
            }
        }
        /** Captures the current child and its kernel start ticks.
         * @param process direct owned child
         */
        private void capture(ProcessHandle process) {
            try { String value = ProcessIdentity.startTicks(process.pid()); found = process.pid(); start = value; }
            catch (IOException ignored) { /* A child that already exited cannot be identified. */ }
        }
        /** Requires a captured child and confirms it has exited before worker launch.
         * @throws AssertionError missing or still-live bridge
         */
        private void verify() {
            if (found <= 0 || start == null || ProcessHandle.of(found).map(ProcessHandle::isAlive).orElse(false)) {
                throw new AssertionError("bridge identity or exit unavailable");
            }
        }
    }
}
