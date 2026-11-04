package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** One finite gate case using actual production capabilities and explicitly assumed CLEAN context. */
final class WarmProbeSession {
    private final JsonNode item;
    private final JsonNode fixture;
    private final String build;
    private final String policy;
    private final WarmProbeFiles files;
    private final WorkerPoolLedger ledger;
    private final WarmImageLauncher launcher;
    private final Map<WorkerReservation, WarmProbeWitness> witnesses = new IdentityHashMap<>();
    private final ObjectNode facts = JsonNodeFactory.instance.objectNode();
    private final ArrayNode evidence = JsonNodeFactory.instance.arrayNode();
    private WarmWorkerPool pool;
    private Process direct;
    private WarmTransport transport;

    /** Creates a separate actual ledger incarnation so UNKNOWN cases cannot be reused by later cases.
     * @param root copied installation
     * @param cases registered manifest
     * @param group verified delegated root
     * @param build full installed identity
     * @param item one registered case
     * @throws Exception invalid fixture, installation or private journal
     */
    private WarmProbeSession(Path root, Path cases, Path group, String build, JsonNode item) throws Exception {
        this.item = item;
        this.fixture = WarmProbeFiles.fixture(cases, item);
        this.build = build;
        this.policy = fixture.path("policyVersion").textValue();
        this.files = new WarmProbeFiles(root);
        String id = item.path("id").textValue();
        WarmProbeFiles.require(id.matches("[a-z0-9-]+"), "Invalid case identity");
        Path journal = root.resolve(".runtime/warm-pool/journal").resolve(id);
        Files.createDirectory(journal, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
        ledger = WorkerPoolLedger.open(journal, group, build, policy);
        launcher = new WarmImageLauncher(root, root.resolve("backend/target"), build);
        facts.put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL").put("poolNonce", ledger.poolNonce());
        evidence.add(files.save(id + "-fixture.json", fixture));
    }

    /** Runs and physically retires one finite case, retaining failure evidence without optimistic release.
     * @param root copied installation
     * @param cases frozen manifest
     * @param group verified private delegation
     * @param build installed full image identity
     * @param item registered case
     * @return finite outcome with bound evidence
     * @throws Exception report storage failure
     */
    static ObjectNode execute(Path root, Path cases, Path group, String build, JsonNode item) throws Exception {
        if (item.path("id").asText().equals("sequence-refill-aba") || item.path("id").asText().equals("idle-expiry-demand")) {
            return WarmProbeSequence.execute(root, cases, group, build, item);
        }
        WarmProbeSession session = null;
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("id", item.path("id").textValue())
                .put("classification", item.path("kind").textValue()).put("status", "BLOCKED");
        Exception failure = null;
        try { session = new WarmProbeSession(root, cases, group, build, item); session.run(); }
        catch (Exception error) { failure = error; }
        if (session != null) {
            try { session.finish(result); }
            catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        }
        if (failure == null) result.put("status", "PASS");
        else result.set("failure", failure(failure));
        return result;
    }

    /** Dispatches only the nine registered gate behaviors; no browser or environment selects authority.
     * @throws Exception actual capability, process or lifecycle failure
     * @throws IOException unregistered case identity
     */
    private void run() throws Exception {
        switch (item.path("id").textValue()) {
            case "normal-cold" -> normal(false, false);
            case "normal-ready-hit" -> normal(true, false);
            case "double-consume" -> normal(true, true);
            case "revalidate-fresh" -> fresh();
            case "startup-failure" -> startupFailure();
            case "preattach-failure" -> preattachFailure();
            case "postattach-unknown" -> postattachUnknown();
            case "shutdown-ready" -> shutdownReady();
            case "shutdown-starting" -> shutdownStarting();
            default -> throw new IOException("Unregistered probe case");
        }
    }

    /** Validates and publishes one complete response through the actual advisory pool.
     * @param readyHit whether readiness precedes admission
     * @param replay whether to attempt reuse of the consumed context
     * @throws Exception failed actual worker or publication
     */
    private void normal(boolean readyHit, boolean replay) throws Exception {
        WarmDeadline deadline = new WarmDeadline(10000);
        startPool();
        if (readyHit) { waitReady(); deadline = new WarmDeadline(10000); }
        facts.put("readyBeforeAdmission", readyHit);
        WarmRequestBinding binding = binding();
        WarmContextPermit permit = assumedPermit(binding);
        WorkerCapacity.acquire();
        try (WarmResultLease lease = pool.validate(binding, fixture.path("candidate"), permit, deadline)) {
            capture(false);
            JsonNode response = lease.result();
            validateResponse(response, binding.nonce());
            evidence.add(files.save(id() + "-response.json", response));
            byte[] published = lease.publish(JsonWire.encode(response));
            WarmProbeFiles.require(java.util.Arrays.equals(published, JsonWire.encode(response)), "Publication bytes changed");
            facts.put("published", true);
            if (replay) rejectReplay(binding, permit);
        } finally { WorkerCapacity.release(); }
    }

    /** Requires replay denial specifically at the consumed context boundary.
     * @param binding original admitted identity
     * @param permit already consumed private context
     * @throws Exception unexpected second response or unrelated startup failure
     */
    private void rejectReplay(WarmRequestBinding binding, WarmContextPermit permit) throws Exception {
        try (WarmResultLease unexpected = pool.validate(binding, fixture.path("candidate"), permit, new WarmDeadline(10000))) {
            throw new IOException("Second context consumption unexpectedly succeeded");
        } catch (IOException denied) {
            WarmProbeFiles.require("Unavailable context permit".equals(denied.getMessage()), "Replay failed for unrelated reason");
            facts.put("secondConsumptionRejected", true);
        }
        capture(true);
    }

    /** Constructs only the test-assumed CLEAN bridge objects; production has no bypass or test switch.
     * @param binding fresh server-created operation identity
     * @return explicitly assumed context permit for ownership-only runtime testing
     * @throws Exception reflected gate construction failure
     */
    private WarmContextPermit assumedPermit(WarmRequestBinding binding) throws Exception {
        Constructor<DocumentValidationContext> contextType = DocumentValidationContext.class
                .getDeclaredConstructor(JsonNode.class, JsonNode.class);
        contextType.setAccessible(true);
        DocumentValidationContext context = contextType.newInstance(fixture.path("baseArtifact"), fixture.path("ownedIdInventory"));
        Constructor<WarmContextPermit> permitType = WarmContextPermit.class
                .getDeclaredConstructor(WarmRequestBinding.class, DocumentValidationContext.class);
        permitType.setAccessible(true);
        return permitType.newInstance(binding, context);
    }

    /** Creates a fresh exact operation identity without mutating the registered source fixture.
     * @return binding to current policy, full build and pool incarnation
     * @throws IOException unavailable fixture encoding
     */
    private WarmRequestBinding binding() throws IOException {
        return new WarmRequestBinding(UUID.randomUUID().toString(), Hashes.bytes(JsonWire.encode(fixture)),
                "server:00000000-0000-0000-0000-000000000001", 0, policy, build, ledger.poolNonce());
    }

    /** Starts one actual lazy standby and captures its group before private validation.
     * @throws Exception failed reservation or observer creation
     */
    private void startPool() throws Exception {
        pool = new WarmWorkerPool(ledger, launcher, build, policy);
        pool.begin();
        capture(false);
        facts.put("initialReservations", ledger.reservations().length);
    }

    /** Waits for actual production READY without modifying lifecycle state.
     * @throws Exception failed or expired startup
     * @throws IOException no generation became ready within its startup budget
     */
    private void waitReady() throws Exception {
        long end = System.nanoTime() + 5_000_000_000L;
        while (System.nanoTime() < end) {
            WorkerReservation[] values = ledger.reservations();
            for (WorkerReservation token : values) {
                if (token.phase() == WorkerReservation.Phase.READY) { capture(true); return; }
                WarmProbeFiles.require(token.phase() != WorkerReservation.Phase.UNKNOWN, "Standby startup became unknown");
            }
            TimeUnit.MILLISECONDS.sleep(1);
        }
        throw new IOException("Standby did not become READY");
    }

    /** Retains all currently owned generations, including the bounded replacement started on consumption.
     * @param awaitAttachment whether process capture must precede the impending pool shutdown
     * @throws Exception unavailable group or incomplete startup
     */
    private void capture(boolean awaitAttachment) throws Exception {
        for (WorkerReservation token : ledger.reservations()) {
            WarmProbeWitness witness = witnesses.get(token);
            if (witness == null) { witness = new WarmProbeWitness(ledger, token); witnesses.put(token, witness); }
            if (awaitAttachment) awaitAttached(token);
            witness.observeChild(token.child());
            if (token.child() != null) witness.bootstrap(bootstrap(token));
            if (token.phase() != WorkerReservation.Phase.CLEAN && token.phase() != WorkerReservation.Phase.RELEASED) witness.observeLive();
        }
    }

    /** Waits only for metadata attachment, leaving the production helper's gate and phase untouched.
     * @param token observed actual generation
     * @throws Exception missing attachment after a bounded wait
     */
    private void awaitAttached(WorkerReservation token) throws Exception {
        long end = token.startupDeadline();
        while (token.child() == null && token.phase() != WorkerReservation.Phase.RELEASED && System.nanoTime() < end) {
            TimeUnit.MILLISECONDS.sleep(1);
        }
        WarmProbeFiles.require(token.child() != null, "Observed worker lost attachment before capture");
    }

    /** Executes ordinary fresh REVALIDATE inside the same actual helper and ledger containment path.
     * @throws Exception failed helper, response, task receipt or cleanup
     */
    private void fresh() throws Exception {
        WorkerReservation token = spawn(false, true);
        recordBootstrap(token, "PRODUCTION_BOOTSTRAP_METADATA");
        launcher.releaseBootstrap(ledger, token);
        launcher.awaitFreshSandbox(token);
        AtomicBoolean completed = new AtomicBoolean();
        Completion receipt = new Completion(completed);
        ObjectNode frame = fixture.deepCopy();
        frame.put("requestId", UUID.randomUUID().toString());
        WorkerCapacity.acquire();
        try {
            byte[] bytes = FrameProcess.exchange(direct, JsonWire.encode(frame), 1048577, 10000, receipt);
            JsonNode response = JsonWire.decode(bytes, JsonNode.class);
            validateResponse(response, frame.path("requestId").textValue());
            evidence.add(files.save(id() + "-response.json", response));
            WarmProbeFiles.require(completed.get(), "Fresh stream task receipt missing");
            ledger.cleanup(token, System.nanoTime() + 2_500_000_000L, receipt);
            ledger.release(token);
        } finally { WorkerCapacity.release(); }
        facts.put("freshEntryPoint", "DocumentWorkerMain").put("operation", "REVALIDATE");
    }

    /** Injects only an invalid public bootstrap after actual durable attachment.
     * @throws Exception unexpected readiness or incomplete failed-start cleanup
     */
    private void startupFailure() throws Exception {
        WorkerReservation token = spawn(true, true);
        FailureNotice notice = new FailureNotice();
        transport = new WarmTransport(direct, token.nonce(), build, notice);
        direct.getOutputStream().write("{}\n".getBytes(StandardCharsets.UTF_8));
        direct.getOutputStream().flush();
        boolean rejected = false;
        try { transport.awaitReady(new WarmDeadline(3000)); }
        catch (IOException failure) { rejected = true; }
        WarmProbeFiles.require(rejected && transport.readyNanos() == 0 && direct.waitFor(2, TimeUnit.SECONDS)
                && direct.exitValue() == 70, "Malformed bootstrap did not fail startup");
        facts.put("injectedBootstrap", "{}\\n").put("startupRejected", true);
        ledger.cancel(token);
        ledger.cleanup(token, System.nanoTime() + 2_500_000_000L, this::closeDirect);
        ledger.release(token);
    }

    /** Exercises a real spawned helper whose identity was never committed to its reservation.
     * @throws Exception failed physical cleanup or optimistic logical release
     */
    private void preattachFailure() throws Exception {
        WorkerReservation token = spawn(true, false);
        expectUnknownCleanup(token);
        facts.put("fault", "ACTUAL_SPAWN_BEFORE_LEDGER_ATTACH");
    }

    /** Retains logical uncertainty after attachment while still killing and reaping the actual tree.
     * @throws Exception unexpected capacity release or missing physical cleanup
     */
    private void postattachUnknown() throws Exception {
        WorkerReservation token = spawn(true, true);
        recordBootstrap(token, "PRODUCTION_BOOTSTRAP_METADATA");
        transport = new WarmTransport(direct, token.nonce(), build, new FailureNotice());
        launcher.releaseBootstrap(ledger, token);
        transport.awaitReady(new WarmDeadline(5000));
        ledger.markReady(token, token.nonce(), build, transport.readyNanos());
        synchronized (ledger) { token.unknown(); }
        expectUnknownCleanup(token);
        facts.put("fault", "GATE_INJECTED_POSTATTACH_UNKNOWN_STATE");
    }

    /** Requires physical cleanup without allowing UNKNOWN to regain logical release authority.
     * @param token exact actual generation
     * @throws Exception missing expected uncertainty or actual cleanup evidence
     */
    private void expectUnknownCleanup(WorkerReservation token) throws Exception {
        boolean rejected = false;
        try { ledger.cleanup(token, System.nanoTime() + 2_500_000_000L, this::closeDirect); }
        catch (IOException failure) { rejected = true; }
        WarmProbeFiles.require(rejected && token.phase() == WorkerReservation.Phase.UNKNOWN
                && ledger.reservations().length == 1 && !ledger.online(), "UNKNOWN capacity was not retained");
        WarmProbeFiles.require(!direct.isAlive() && token.group().empty(), "UNKNOWN physical cleanup incomplete");
        token.group().captureTerminal();
        boolean releaseRejected = false;
        try { ledger.release(token); } catch (IOException failure) { releaseRejected = true; }
        WarmProbeFiles.require(releaseRejected, "UNKNOWN release accepted");
        facts.put("unknownReleaseRejected", true).put("physicalCleanupComplete", true);
    }

    /** Stops a ready unassigned generation through the actual production pool close path.
     * @throws Exception failed readiness or shutdown
     */
    private void shutdownReady() throws Exception {
        startPool();
        waitReady();
        facts.put("readyBeforeShutdown", true);
        pool.close();
    }

    /** Observes shutdown entry while the attached ledger phase is STARTING, without editing state.
     * @throws Exception unavailable startup publication barrier or incomplete shutdown
     */
    private void shutdownStarting() throws Exception {
        startPool();
        WorkerReservation token = ledger.reservations()[0];
        awaitAttached(token);
        WarmStandby standby = pendingStandby();
        Closing close = new Closing(pool);
        Thread thread = new Thread(close, "gate-starting-pool-close");
        thread.setDaemon(true);
        try {
            synchronized (standby) {
                WarmProbeFiles.require(token.phase() == WorkerReservation.Phase.STARTING, "Starting barrier was missed");
                capture(false);
                facts.put("shutdownBarrier", "GATE_MONITOR_BARRIER_BEFORE_LEDGER_READY_PUBLICATION")
                        .put("phaseAtCloseEntry", token.phase().name()).put("attachedBeforeClose", true)
                        .put("startingChildPid", token.childPid()).put("startingChildStartTicks", token.childStartTicks())
                        .put("noPrivateHandoff", true).put("rawReadyEmission", "NOT_ASSERTED");
                thread.start();
                observeClosed(token);
            }
        } finally {
            if (thread.getState() != Thread.State.NEW) thread.join(5000);
        }
        WarmProbeFiles.require(!thread.isAlive() && close.failure.get() == null, "Starting shutdown did not complete");
        facts.put("closeThreadJoined", true).put("closeThreadFailed", false);
    }

    /** Reads the actual pending owner solely to coordinate a gate observation monitor.
     * @return existing production standby object
     * @throws Exception unavailable pending generation
     */
    private WarmStandby pendingStandby() throws Exception {
        Field field = WarmWorkerPool.class.getDeclaredField("pending");
        field.setAccessible(true);
        Object value = ((AtomicReference<?>) field.get(pool)).get();
        WarmProbeFiles.require(value instanceof WarmStandby, "Pending standby unavailable");
        return (WarmStandby) value;
    }

    /** Observes real close entry while the held monitor prevents the ledger READY transition.
     * @param token exact attached STARTING reservation
     * @throws Exception missing close entry or unexpected state change
     */
    private void observeClosed(WorkerReservation token) throws Exception {
        Field field = WarmWorkerPool.class.getDeclaredField("closed");
        field.setAccessible(true);
        long end = System.nanoTime() + 1_000_000_000L;
        while (!field.getBoolean(pool) && System.nanoTime() < end) TimeUnit.MILLISECONDS.sleep(1);
        WarmProbeFiles.require(field.getBoolean(pool) && token.phase() == WorkerReservation.Phase.STARTING,
                "Shutdown did not enter while STARTING");
        facts.put("poolClosedObservedWhileStarting", true).put("standbyMonitorHeldAtObservation", true);
    }

    /** Creates actual containment before spawn and optionally persists child identity before any input.
     * @param standby whether this is a warm reservation
     * @param attach whether the case reaches the durable child-identity barrier
     * @return actual generation capability
     * @throws Exception failed production launch or observer binding
     */
    private WorkerReservation spawn(boolean standby, boolean attach) throws Exception {
        WorkerReservation token = standby ? ledger.reserveStandby() : ledger.reserveFresh();
        WarmProbeWitness witness = new WarmProbeWitness(ledger, token);
        witnesses.put(token, witness);
        ledger.markSpawnAttempt(token);
        direct = launcher.spawn(ledger, standby ? WarmWorkerMode.WARM_DOCUMENT : WarmWorkerMode.FRESH_DOCUMENT);
        witness.observeChild(direct);
        if (attach) ledger.attach(token, direct);
        return token;
    }

    /** Retains the exact trusted descriptor constructed by the production serializer, without touching its pipe.
     * @param token durably attached worker
     * @param classification observation boundary
     * @throws Exception inaccessible metadata serializer or evidence storage failure
     */
    private void recordBootstrap(WorkerReservation token, String classification) throws Exception {
        ObjectNode observation = JsonNodeFactory.instance.objectNode().put("classification", classification);
        observation.set("descriptor", bootstrap(token));
        evidence.add(files.save(id() + "-bootstrap.json", observation));
    }

    /** Calls only the actual public-descriptor serializer for a read-only gate observation.
     * @param token durably attached production reservation
     * @return exact serializer metadata
     * @throws Exception unavailable gate reflection seam
     */
    private ObjectNode bootstrap(WorkerReservation token) throws Exception {
        Method method = WarmImageLauncher.class.getDeclaredMethod("bootstrap", WorkerPoolLedger.class, WorkerReservation.class);
        method.setAccessible(true);
        return (ObjectNode) method.invoke(launcher, ledger, token);
    }

    /** Checks the complete response envelope identity while preserving all semantic data in evidence.
     * @param response actual worker output
     * @param nonce exact private request identity
     * @throws IOException failed actual validation or substituted response
     */
    private void validateResponse(JsonNode response, String nonce) throws IOException {
        DocumentJson.fields(response, "protocol", "requestId", "status", "data");
        WarmProbeFiles.require(response.path("protocol").isInt() && response.path("protocol").intValue() == 1
                && nonce.equals(response.path("requestId").textValue())
                && response.path("status").asText().equals("VALIDATED") && response.path("data").isObject(),
                "Actual validation response unavailable");
        validateData(response.path("data"));
    }

    /** Requires a complete real engine result and exact source preservation where the fixture declares source.
     * @param data complete private result body retained in evidence
     * @throws IOException incomplete output or altered authored source
     */
    private void validateData(JsonNode data) throws IOException {
        DocumentJson.fields(data, "mode", "source", "sourceHash", "module", "occurrences", "trivia",
                "analysisDescriptors", "diagnostics", "idRemapping");
        WarmProbeFiles.require(data.path("source").isTextual() && !data.path("source").textValue().isBlank()
                && Hashes.bytes(data.path("source").textValue().getBytes(StandardCharsets.UTF_8))
                .equals(data.path("sourceHash").asText()), "Incomplete validated source");
        for (String field : new String[]{"occurrences", "trivia", "analysisDescriptors", "diagnostics"}) {
            WarmProbeFiles.require(data.path(field).isArray(), "Incomplete validated collection");
        }
        WarmProbeFiles.require(data.path("idRemapping").isObject(), "Incomplete identity remapping");
        if (fixture.path("candidate").path("mode").asText().equals("SOURCE")) {
            WarmProbeFiles.require(data.path("source").equals(fixture.path("candidate").path("source")), "Authored source changed");
        } else if (fixture.path("operation").asText().equals("REVALIDATE")) {
            WarmProbeFiles.require(data.path("source").equals(fixture.path("baseArtifact").path("source")), "Historical source changed");
        }
    }

    /** Reaps the original child even if its durable attachment failed before transport creation.
     * @throws Exception unresolved owned child or stream task
     */
    private void closeDirect() throws Exception {
        if (direct != null) {
            direct.destroyForcibly();
            WarmProbeFiles.require(direct.waitFor(2, TimeUnit.SECONDS), "Gate retained helper was not reaped");
        }
        if (transport != null) transport.close();
        else if (direct != null) {
            direct.getOutputStream().close();
            direct.getInputStream().close();
            direct.getErrorStream().close();
        }
    }

    /** Closes all active scheduling, records actual receipts and checks the registered logical outcome.
     * @param result mutable case result
     * @throws Exception unconfirmed actual cleanup or unavailable evidence
     */
    private void finish(ObjectNode result) throws Exception {
        Exception failure = null;
        try { if (pool != null) { capture(true); pool.close(); } }
        catch (Exception error) { failure = error; }
        try { cleanupOutstanding(); closeDirect(); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        facts.set("retainedCoordinatorFailures", WarmProbeFailures.retained(pool));
        try { summarize(result); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        for (WarmProbeWitness witness : witnesses.values()) witness.close();
        try { ledger.close(); }
        catch (IOException retained) { if (!item.path("expected_capacity_retained").asBoolean()) throw retained; }
        if (failure != null) throw failure;
    }

    /** Attempts physical retirement after unexpected exceptions without inventing release for UNKNOWN.
     * @throws Exception unresolved cleanup other than the explicitly registered UNKNOWN outcome
     */
    private void cleanupOutstanding() throws Exception {
        for (WorkerReservation token : ledger.reservations()) {
            if (token.phase() == WorkerReservation.Phase.UNKNOWN) {
                WarmProbeFiles.require(token.group().empty(), "Unknown group still populated");
                token.group().captureTerminal();
                continue;
            }
            ledger.cancel(token);
            ledger.cleanup(token, System.nanoTime() + 2_500_000_000L, this::closeDirect);
            ledger.release(token);
        }
    }

    /** Writes exact kernel receipts and distinguishes physical emptiness from retained logical capacity.
     * @param result mutable finite case report
     * @throws Exception missing positive evidence or different registered disposition
     */
    private void summarize(ObjectNode result) throws Exception {
        ArrayNode groups = facts.putArray("groups");
        ArrayNode identities = result.putArray("identities");
        boolean empty = !witnesses.isEmpty();
        for (WarmProbeWitness witness : witnesses.values()) {
            groups.add(witness.terminal());
            empty &= witness.populatedZero();
            if (witness.identity() != null) identities.add(witness.identity());
        }
        boolean retained = ledger.reservations().length != 0;
        WarmProbeFiles.require(empty && retained == item.path("expected_capacity_retained").asBoolean(), "Cleanup disposition mismatch");
        result.putObject("cleanup").put("status", retained ? "UNKNOWN" : "PASS").put("populatedZero", empty)
                .put("directChildReaped", true).put("capacityRetained", retained);
        facts.put("remainingReservations", ledger.reservations().length).put("ledgerOnline", ledger.online());
        evidence.add(files.save(id() + "-ownership.json", facts));
        result.set("evidence", evidence);
        result.put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL");
    }

    /** Returns the already validated finite case identifier.
     * @return registered case basename
     */
    private String id() { return item.path("id").textValue(); }

    /** Preserves bounded exception provenance without printing fixture or response contents.
     * @param failure actual failed probe operation
     * @return private bounded failure chain
     */
    private static ObjectNode failure(Exception failure) {
        return WarmProbeFailures.describe(failure);
    }

    /** Owns the one actual shutdown caller used by the STARTING monitor barrier. */
    private static final class Closing implements Runnable {
        private final WarmWorkerPool pool;
        private final AtomicReference<Exception> failure = new AtomicReference<>();
        /** Retains the exact isolated production pool being closed.
         * @param pool actual production coordinator
         */
        private Closing(WarmWorkerPool pool) { this.pool = pool; }
        /** Invokes real shutdown once and retains failure without interrupting another owner. */
        @Override
        public void run() {
            try { pool.close(); }
            catch (Exception error) { failure.set(error); }
        }
    }

    /** Captures the real fresh transport's task-termination receipt. */
    private record Completion(AtomicBoolean observed) implements FrameProcess.Completion, AutoCloseable {
        /** Records the production transport callback after its actual task join. */
        @Override
        public void closed() { observed.set(true); }

        /** Refuses a logical cleanup receipt if the actual task callback was absent.
         * @throws IOException missing task termination
         */
        @Override
        public void close() throws IOException { WarmProbeFiles.require(observed.get(), "Fresh tasks not closed"); }
    }

    /** Nonblocking reader callback; it never acquires production ledger or lifecycle monitors. */
    private static final class FailureNotice implements WarmTransport.FailureSink {
        private final AtomicReference<IOException> failure = new AtomicReference<>();
        /** Retains the first bounded protocol failure.
         * @param value actual reader failure
         */
        @Override
        public void failed(IOException value) { failure.compareAndSet(null, value); }
    }
}
