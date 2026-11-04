package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** One immutable semantic fixture with complete private output and actual cleanup evidence. */
final class WarmSemanticCase {
    private final Path root;
    private final String variant;
    private final String build;
    private final JsonNode item;
    private final JsonNode fixture;
    private final byte[] input;
    private final ObjectNode record;
    private final ObjectNode ownership = JsonNodeFactory.instance.objectNode();
    private final ArrayNode identities = JsonNodeFactory.instance.arrayNode();
    private WarmSemanticOwned owned;
    private Process direct;

    /** Reads one exact bounded fixture before granting any process authority.
     * @param root copied installation
     * @param variant fixed gate route
     * @param build full executable identity
     * @param item exact manifest row
     * @throws IOException unavailable or changed fixture
     */
    private WarmSemanticCase(Path root, String variant, String build, JsonNode item) throws IOException {
        this.root = root;
        this.variant = variant;
        this.build = build;
        this.item = item;
        input = input(root, item);
        fixture = JsonWire.decode(input, JsonNode.class);
        WarmProbeFiles.require(fixture.path("operation").asText().equals(item.path("operation").asText()), "Operation changed");
        record = JsonNodeFactory.instance.objectNode().put("schemaVersion", 1).put("profile", "DEFAULT").put("variant", variant)
                .put("inputSha256", Hashes.bytes(input)).put("inputBytes", input.length).put("buildIdentity", build)
                .put("outcome", "NOT_EXECUTED").put("noWorkerStarted", true).put("noPrivateHandoff", true)
                .put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL");
    }

    /** Executes exactly one registered route and persists failures without advancing after uncertainty.
     * @param root copied installation
     * @param variant fixed baseline or candidate
     * @param group verified private delegated root
     * @param build immutable full image identity
     * @param item frozen manifest row
     * @return bound finite case outcome
     * @throws Exception unavailable immutable evidence storage
     */
    static ObjectNode execute(Path root, String variant, Path group, String build, JsonNode item) throws Exception {
        WarmSemanticCase session = new WarmSemanticCase(root, variant, build, item);
        ObjectNode row = JsonNodeFactory.instance.objectNode().put("id", item.path("name").asText()).put("status", "BLOCKED");
        Exception failure = null;
        try { session.run(group); }
        catch (Exception error) { failure = error; }
        try { session.finish(row); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        if (failure == null) row.put("status", "PASS");
        else row.set("failure", WarmSemanticProtocol.failure(failure));
        session.save(row);
        return row;
    }

    /** Dispatches only the frozen operation/profile combination.
     * @param group verified delegated root
     * @throws Exception actual route, boundary or cleanup failure
     */
    private void run(Path group) throws Exception {
        if (variant.equals("W0")) {
            record.put("route", "FRESH_DEFAULT_BUBBLEWRAP");
            if (input.length >= 2097152) {
                record.put("outcome", "INPUT_REJECTED").put("rejectionCode", "PRIVATE_INPUT_LIMIT");
                expected();
                return;
            }
            baseline();
        } else {
            owned = new WarmSemanticOwned(root, group, build, item.path("name").textValue());
            if (fixture.path("operation").asText().equals("REVALIDATE")) owned.fresh(fixture, input, record);
            else owned.advisory(fixture, input, record);
        }
        expected();
    }

    /** Uses the unchanged actual DEFAULT sandbox and bounded frame transport for baseline semantics.
     * @throws Exception unavailable baseline launch, frame or owned task termination
     */
    private void baseline() throws Exception {
        BubblewrapLauncher launcher = new BubblewrapLauncher(root.resolve("backend/target"), true, WorkerLaunchProfile.DEFAULT);
        WarmProbeFiles.require(launcher.identity().equals(build), "Baseline image changed");
        direct = launcher.launch();
        record.put("noWorkerStarted", false);
        String ticks = ProcessIdentity.startTicks(direct.pid());
        identities.addObject().put("pid", direct.pid()).put("start_ticks", ticks);
        record.put("workerPid", direct.pid()).put("workerStartTicks", ticks).put("noWorkerStarted", false);
        AtomicBoolean completed = new AtomicBoolean();
        WarmSemanticOwned.Completion tasks = new WarmSemanticOwned.Completion(completed);
        record.put("noPrivateHandoff", false);
        byte[] output = FrameProcess.exchange(direct, input, 1048577, 10000, tasks);
        WarmProbeFiles.require(completed.get(), "Baseline tasks remain active");
        WarmSemanticProtocol.response(fixture, output, "ACTUAL_STDOUT_FRAME", record);
    }

    /** Checks only registered output status or precise boundary classification, never an arbitrary exit.
     * @throws IOException different expected response or rejection boundary
     */
    private void expected() throws IOException {
        String outcome = record.path("outcome").asText();
        if (item.path("name").asText().equals("context-invalid-policyVersion") && variant.equals("W1")) {
            WarmProbeFiles.require(outcome.equals("BINDING_INPUT_REJECTED") && record.path("noPrivateHandoff").asBoolean(),
                    "Blank policy was not rejected at binding");
        } else if (item.path("expectedProbeReject").asBoolean()) {
            WarmProbeFiles.require(outcome.equals("INPUT_REJECTED") && record.path("noPrivateHandoff").asBoolean(),
                    "Expected exact private input rejection");
        } else WarmProbeFiles.require(outcome.equals("COMPLETE_RESPONSE")
                && record.path("workerStatus").equals(item.path("expectedStatus")), "Unexpected semantic outcome");
    }

    /** Retires actual owned work before recording capacity or direct-child absence.
     * @param row finite case outcome receiving checked cleanup
     * @throws Exception unconfirmed physical cleanup or exact identity absence
     */
    private void finish(ObjectNode row) throws Exception {
        if (owned != null) owned.finish(record, ownership, identities, row);
        else {
            if (direct != null) {
                FrameProcess.reap(direct);
                WarmProbeFiles.require(direct.waitFor(0, TimeUnit.MILLISECONDS)
                        && WorkerReservation.absent(direct.pid(), record.path("workerStartTicks").asText()), "Baseline reap unconfirmed");
                record.put("workerExitCode", direct.exitValue()).put("reaped", true);
            }
            ownership.put("perWorkerCgroup", false).put("containment", "OUTER_PRIVATE_SCOPE_ONLY").putArray("groups");
            row.putObject("cleanup").put("status", "PASS").put("populatedZero", false)
                    .put("directChildReaped", true).put("capacityRetained", false).put("outerScopeCleanupRequired", true);
        }
        row.put("route", record.path("route").asText()).set("identities", identities);
        row.put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL");
    }

    /** Writes complete private results and receipts exactly once, preserving failures unchanged.
     * @param row case summary receiving content-addressed references
     * @throws IOException private evidence storage failure
     */
    private void save(ObjectNode row) throws IOException {
        WarmProbeFiles files = new WarmProbeFiles(root);
        String id = WarmSemanticProtocol.basename(item.path("name").textValue());
        row.set("record", files.save(id + "-result.json", record));
        row.set("ownership", files.save(id + "-ownership.json", ownership));
    }

    /** Reads a regular registered bounded fixture without following any path alias.
     * @param root copied installation
     * @param item registered exact file identity
     * @return original fixture bytes, including any significant JSON whitespace
     * @throws IOException changed input, traversal or excessive capture
     */
    private static byte[] input(Path root, JsonNode item) throws IOException {
        String id = item.path("name").asText();
        WarmProbeFiles.require(id.matches("[A-Za-z0-9_-]+"), "Invalid fixture name");
        Path relative = Path.of(item.path("path").textValue());
        WarmProbeFiles.require(relative.equals(Path.of("fixtures/semantic", id + ".json")), "Invalid fixture path");
        Path path = root.resolve(".gate").resolve(relative);
        WarmProbeFiles.require(path.toRealPath().equals(path) && Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS), "Fixture alias");
        byte[] bytes;
        try (var stream = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
            bytes = stream.readNBytes(2097153);
            WarmProbeFiles.require(stream.read() == -1, "Fixture exceeds capture limit");
        }
        WarmProbeFiles.require(bytes.length == item.path("bytes").intValue()
                && Hashes.bytes(bytes).equals(item.path("sha256").asText()), "Fixture identity changed");
        return bytes;
    }
}
