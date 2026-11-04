package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/** Finite same-incarnation lifecycle observations; synthetic context is never a SQL receipt. */
final class WarmProbeSequence {
    private final Path cases;
    private final Path journal;
    private final JsonNode item;
    private final String build;
    private final WarmProbeFiles files;
    private final WorkerPoolLedger ledger;
    private final WarmImageLauncher launcher;
    private final WarmWorkerPool pool;
    private final Map<WorkerReservation, WarmProbeWitness> witnesses = new IdentityHashMap<>();
    private final ObjectNode facts = JsonNodeFactory.instance.objectNode();
    private final ObjectNode lifecycle = facts.putObject("lifecycle");
    private final ArrayNode evidence = JsonNodeFactory.instance.arrayNode();

    /** Creates one actual isolated owner for every operation within the registered case.
     * @param root copied installation
     * @param cases frozen manifest
     * @param group verified delegated root
     * @param build installed full executable identity
     * @param item exact registered lifecycle case
     * @throws Exception invalid fixtures or unavailable private owner
     */
    private WarmProbeSequence(Path root, Path cases, Path group, String build, JsonNode item) throws Exception {
        this.cases = cases;
        this.item = item;
        this.build = build;
        files = new WarmProbeFiles(root);
        JsonNode fixture = WarmProbeFiles.fixture(cases, item);
        journal = root.resolve(".runtime/warm-pool/journal").resolve(item.path("id").textValue());
        Files.createDirectory(journal, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
        ledger = WorkerPoolLedger.open(journal, group, build, fixture.path("policyVersion").textValue());
        launcher = new WarmImageLauncher(root, root.resolve("backend/target"), build);
        pool = new WarmWorkerPool(ledger, launcher, build, fixture.path("policyVersion").textValue());
        facts.put("poolNonce", ledger.poolNonce()).put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL");
        lifecycle.put("kind", item.path("kind").textValue()).put("initialReservations", ledger.reservations().length);
        lifecycle.putArray("steps");
        lifecycle.putArray("observations");
        evidence.add(files.save(id() + "-fixture.json", fixture));
    }

    /** Executes and retires one case while preserving every actual failed outcome.
     * @param root copied installation
     * @param cases frozen manifest
     * @param group verified delegated root
     * @param build full build identity
     * @param item registered case
     * @return finite case result with immutable private evidence
     * @throws Exception evidence storage failure
     */
    static ObjectNode execute(Path root, Path cases, Path group, String build, JsonNode item) throws Exception {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("id", item.path("id").asText())
                .put("classification", item.path("kind").asText()).put("status", "BLOCKED");
        WarmProbeSequence owner = null;
        Exception failure = null;
        try { owner = new WarmProbeSequence(root, cases, group, build, item); owner.run(); }
        catch (Exception error) { failure = error; }
        if (owner != null) {
            try { owner.finish(result); }
            catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
            owner.save(result);
        }
        if (failure == null) result.put("status", "PASS");
        else result.set("failure", WarmProbeFailures.describe(failure));
        return result;
    }

    /** Runs only the two registered finite scenarios without changing clocks or production selection.
     * @throws Exception failed real lifecycle or fixture assertion
     */
    private void run() throws Exception {
        observe("initial");
        WarmProbeFiles.require(ledger.reservations().length == 0 && item.path("steps").isArray(), "Nonempty initial pool");
        if (id().equals("idle-expiry-demand")) idle();
        int index = 0;
        for (JsonNode step : item.path("steps")) {
            if (index > 0) waitReady(pending());
            executeStep(step, index++);
        }
        WarmProbeFiles.require(index == (id().equals("sequence-refill-aba") ? 3 : 1), "Unexpected lifecycle step count");
        capture(true);
        observe("before-shutdown");
    }

    /** Records genuine idle expiry and a bounded no-demand interval before the next explicit admission.
     * @throws Exception missing actual readiness, expiry, cleanup or quiet interval
     */
    private void idle() throws Exception {
        pool.begin();
        capture(true);
        WorkerReservation token = pending();
        WarmTransport transport = WarmSequenceRecords.transport(pool, token);
        waitReady(token);
        observe("idle-ready");
        ObjectNode record = WarmSequenceIdle.observe(ledger, token, transport, journal, witnesses.get(token));
        lifecycle.set("idle", record);
        observe("idle-quiet-complete");
    }

    /** Performs a fresh bound operation through the same actual one-use pool.
     * @param registered exact pinned fixture selection
     * @param index zero-based operation index
     * @throws Exception failed context assumption, actual worker or publication
     */
    private void executeStep(JsonNode registered, int index) throws Exception {
        ObjectNode request = WarmProbeFiles.fixture(cases, registered).deepCopy();
        request.put("requestId", UUID.randomUUID().toString());
        ObjectNode record = ((ArrayNode) lifecycle.path("steps")).addObject();
        record.put("index", index).put("fixture", registered.path("fixture").asText())
                .put("fixture_sha256", registered.path("fixture_sha256").asText()).put("requestId", request.path("requestId").asText());
        long admitted = System.nanoTime();
        record.put("admissionNanos", admitted).put("beforeDemandReservations", ledger.reservations().length);
        if (lifecycle.has("idle")) ((ObjectNode) lifecycle.path("idle")).put("redemandNanos", admitted);
        WorkerCapacity.acquire();
        try {
            WarmDeadline deadline = WarmDeadline.fromStart(admitted, 10000);
            pool.begin();
            capture(true);
            WorkerReservation selected = pending();
            WarmTransport transport = WarmSequenceRecords.transport(pool, selected);
            record.set("selected", WarmSequenceRecords.identity(selected));
            record.put("phaseBeforeValidate", selected.phase().name());
            observe("step-" + index + "-before-validate");
            validate(request, registered, selected, transport, record, deadline);
        } finally { WorkerCapacity.release(); }
        observe("step-" + index + "-published");
    }

    /** Publishes a complete checked result only after actual cleanup and captures its automatic replacement.
     * @param request unchanged fixture semantics with a unique operation nonce
     * @param registered exact expected status/mode fixture selection
     * @param selected captured actual generation
     * @param transport retained read-only readiness-clock observer
     * @param record per-operation private evidence
     * @param deadline original request admission deadline
     * @throws Exception unavailable actual validation, refill or publication
     */
    private void validate(JsonNode request, JsonNode registered, WorkerReservation selected, WarmTransport transport,
            ObjectNode record, WarmDeadline deadline) throws Exception {
        WarmRequestBinding binding = WarmSemanticProtocol.binding(request, JsonWire.encode(request), build, ledger.poolNonce());
        DocumentValidationContext context = WarmSemanticProtocol.context(request);
        WarmSequenceRecords.frame(binding, request, context, record);
        WarmContextPermit permit = WarmSemanticProtocol.permit(binding, context);
        try (WarmResultLease lease = pool.validate(binding, request.path("candidate"), permit, deadline)) {
            capture(true);
            record.set("replacement", WarmSequenceRecords.identity(pending()));
            byte[] response = JsonWire.encode(lease.result());
            WarmSequenceRecords.response(request, registered, response, record);
            WarmProbeFiles.require(java.util.Arrays.equals(response, lease.publish(response)), "Sequence publication bytes changed");
            record.put("published", true).put("publishedNanos", System.nanoTime())
                    .put("phaseAfterPublish", selected.phase().name()).put("transportReadyNanos", transport.readyNanos())
                    .put("idleDeadlineNanos", selected.idleDeadline());
            WarmProbeFiles.require(selected.phase() == WorkerReservation.Phase.RELEASED, "Consumed generation not released");
        }
    }

    /** Finds the single actual unassigned generation without reconstructing authority from metadata.
     * @return exact retained reservation object
     * @throws IOException absent or multiple unassigned workers
     */
    private WorkerReservation pending() throws IOException {
        WorkerReservation found = null;
        for (WorkerReservation token : ledger.reservations()) {
            if (!token.unassigned()) continue;
            WarmProbeFiles.require(found == null, "Multiple pending generations");
            found = token;
        }
        WarmProbeFiles.require(found != null, "Pending generation unavailable");
        return found;
    }

    /** Waits for real ledger readiness under the existing startup deadline.
     * @param token exact current pending generation
     * @throws Exception failed, retired or late startup
     */
    private void waitReady(WorkerReservation token) throws Exception {
        while (token.phase() != WorkerReservation.Phase.READY && System.nanoTime() < token.startupDeadline()) {
            WarmProbeFiles.require(token.phase() == WorkerReservation.Phase.STARTING || token.phase() == WorkerReservation.Phase.RESERVED,
                    "Sequence startup failed");
            TimeUnit.MILLISECONDS.sleep(1);
        }
        WarmProbeFiles.require(token.phase() == WorkerReservation.Phase.READY, "Sequence READY unavailable");
        capture(true);
    }

    /** Opens independent observers for every actual consumed or automatic refill generation.
     * @param attach whether to wait for the existing startup to attach its direct child
     * @throws Exception missing descriptor or actual attachment
     */
    private void capture(boolean attach) throws Exception {
        for (WorkerReservation token : ledger.reservations()) {
            WarmProbeWitness witness = witnesses.get(token);
            if (witness == null) { witness = new WarmProbeWitness(ledger, token); witnesses.put(token, witness); }
            if (attach) {
                while (token.child() == null && System.nanoTime() < token.startupDeadline()
                        && token.phase() != WorkerReservation.Phase.RELEASED) TimeUnit.MILLISECONDS.sleep(1);
                WarmProbeFiles.require(token.child() != null, "Sequence child attachment unavailable");
            }
            witness.observeChild(token.child());
            if (token.child() != null) witness.bootstrap(bootstrap(token));
        }
    }

    /** Reads the production serializer without reading or modifying its bootstrap pipe.
     * @param token actual durably attached worker
     * @return exact trusted descriptor metadata
     * @throws Exception unavailable read-only reflection seam
     */
    private ObjectNode bootstrap(WorkerReservation token) throws Exception {
        Method method = WarmImageLauncher.class.getDeclaredMethod("bootstrap", WorkerPoolLedger.class, WorkerReservation.class);
        method.setAccessible(true);
        return (ObjectNode) method.invoke(launcher, ledger, token);
    }

    /** Captures bounded ledger facts at explicit checkpoints; these are not continuous-time assertions.
     * @param label fixed operation checkpoint
     * @throws IOException observed bounds exceeded or owner offline
     */
    private void observe(String label) throws IOException {
        synchronized (ledger) {
            WorkerReservation[] values = ledger.reservations();
            int unassigned = 0;
            int active = 0;
            for (WorkerReservation token : values) { if (token.unassigned()) unassigned++; if (token.active()) active++; }
            ((ArrayNode) lifecycle.path("observations")).addObject().put("label", label).put("observedNanos", System.nanoTime())
                    .put("reservations", values.length).put("unassigned", unassigned).put("active", active).put("online", ledger.online());
            WarmProbeFiles.require(values.length <= 2 && unassigned <= 1 && active <= 1 && ledger.online(), "Sequence ledger bounds failed");
        }
    }

    /** Retires the same owner and preserves failures before reporting actual terminal evidence.
     * @param result mutable finite result
     * @throws Exception incomplete actual shutdown or evidence
     */
    private void finish(ObjectNode result) throws Exception {
        Exception failure = null;
        try { capture(true); }
        catch (Exception error) { failure = error; }
        try { pool.close(); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        facts.set("retainedCoordinatorFailures", WarmProbeFailures.retained(pool));
        try { summarize(result); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        for (WarmProbeWitness witness : witnesses.values()) {
            try { witness.close(); }
            catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        }
        try { ledger.close(); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        if (failure != null) throw failure;
    }

    /** Requires every known tree to have actual reap and positive terminal group-empty receipts.
     * @param result finite case cleanup and identity fields
     * @throws Exception missing terminal ownership or unexpected worker count
     */
    private void summarize(ObjectNode result) throws Exception {
        ArrayNode groups = facts.putArray("groups");
        ArrayNode identities = result.putArray("identities");
        boolean empty = !witnesses.isEmpty();
        for (WarmProbeWitness witness : witnesses.values()) {
            groups.add(witness.terminal());
            empty &= witness.populatedZero();
            if (witness.identity() != null) identities.add(witness.identity());
            WarmProbeFiles.require(witness.token().phase() == WorkerReservation.Phase.RELEASED, "Sequence generation retained");
        }
        facts.put("remainingReservations", ledger.reservations().length).put("ledgerOnline", ledger.online());
        WarmProbeFiles.require(empty && ledger.reservations().length == 0
                && witnesses.size() == (id().equals("sequence-refill-aba") ? 4 : 3), "Sequence cleanup count mismatch");
        result.putObject("cleanup").put("status", "PASS").put("populatedZero", true)
                .put("directChildReaped", true).put("capacityRetained", false);
        result.put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL");
    }

    /** Stores the complete private sequence and kernel receipt once even for a failed case.
     * @param result finite outcome receiving exact evidence hashes
     * @throws IOException failed private evidence storage
     */
    private void save(ObjectNode result) throws IOException {
        evidence.add(files.save(id() + "-ownership.json", facts));
        result.set("evidence", evidence);
    }

    /** Returns the fixed registered case basename.
     * @return case identifier
     */
    private String id() { return item.path("id").textValue(); }
}
