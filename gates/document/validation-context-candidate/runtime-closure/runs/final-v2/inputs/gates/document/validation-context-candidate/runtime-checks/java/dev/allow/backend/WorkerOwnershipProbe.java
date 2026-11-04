package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.file.Path;

/** Actual fresh sandbox validation with authored private ownership inventories. */
public final class WorkerOwnershipProbe {
    private static final String ID = "server:00000000-0000-4000-8000-000000000011";
    private static final String OTHER = "server:00000000-0000-4000-8000-000000000012";
    private final Path target;

    /** Binds one isolated copied worker build.
     * @param target temporary target root
     */
    private WorkerOwnershipProbe(Path target) { this.target = target; }

    /** Runs missing, foreign, wrong-kind and positive-control inventory cases.
     * @param args one absolute copied target path
     * @throws Exception worker, fixture or assertion failure
     * @throws IllegalArgumentException invalid target path
     * @throws AssertionError unexpected validation outcome
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !Path.of(args[0]).isAbsolute()) throw new IllegalArgumentException("target");
        WorkerOwnershipProbe probe = new WorkerOwnershipProbe(Path.of(args[0]));
        probe.check(JsonNodeFactory.instance.objectNode(), "INVALID", "missing");
        probe.check(JsonNodeFactory.instance.objectNode().put(OTHER, "signature"), "INVALID", "foreign");
        probe.check(JsonNodeFactory.instance.objectNode().put(ID, "field"), "INVALID", "wrong-kind");
        probe.check(JsonNodeFactory.instance.objectNode().put(ID, "signature"), "VALIDATED", "positive");
        System.out.println("PASS four actual private worker inventory cases");
    }

    /** Creates a complete single-signature block candidate without unowned references.
     * @return authored candidate using an existing-looking server identity
     */
    private ObjectNode candidate() {
        ObjectNode candidate = JsonNodeFactory.instance.objectNode().put("mode", "BLOCK_SUPPORTED");
        ObjectNode module = candidate.putObject("module").put("version", 1);
        module.putArray("signatures").addObject().put("tag", "signature").put("id", ID)
                .put("name", "Person").put("multiplicity", "set");
        for (String name : new String[]{"fields", "predicates", "facts", "assertions", "commands", "nodes"}) {
            module.putArray(name);
        }
        candidate.putArray("presentationCopies");
        return candidate;
    }

    /** Runs one new real sandbox worker and checks its outcome and confirmed exit.
     * @param inventory authored private server-ID mapping
     * @param expected expected worker status
     * @param label fixture label
     * @throws Exception validation or launcher failure
     * @throws AssertionError outcome or process ownership mismatch
     */
    private void check(ObjectNode inventory, String expected, String label) throws Exception {
        BubblewrapLauncher launcher = new BubblewrapLauncher(target, true);
        DocumentWorker worker = new DocumentWorker(launcher, ProcessIdentity::startTicks);
        JsonNode base = DocumentArtifacts.empty("fixture-policy", launcher.identity());
        JsonNode result = worker.validate(candidate(), base, inventory, "fixture-policy");
        JsonNode proof = worker.recovery();
        if (!expected.equals(result.path("status").asText()) || proof.path("noWorkerStarted").asBoolean(true)
                || proof.path("workerPid").longValue() <= 0 || proof.path("workerStartTicks").asText().isEmpty()) {
            throw new AssertionError(label + " status=" + result.path("status"));
        }
        System.out.println(label + " status=" + expected + " worker_reaped=" + proof.path("workerPid").longValue());
    }
}
