package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/** Gate-only retained actual pool, with read-only observations and assumed CLEAN context. */
final class WarmLatencyPool {
    private final WorkerPoolLedger ledger;
    private final WarmWorkerPool pool;
    private final String build;
    private final String fixtureHash;
    private final Field requestNonce;
    private final Field generationCounts;
    private final Map<WorkerReservation, Process> generations = new IdentityHashMap<>();
    private boolean poolClosed;
    private boolean ledgerClosed;

    /** Creates an independent actual journal and lazy coordinator in copied targets.
     * @param root copied installation root
     * @param group delegated worker root
     * @param journal unique private journal directory
     * @param build exact copied installed identity
     * @param fixtureHash frozen registered request digest
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception unavailable containment or private observation seam
     */
    WarmLatencyPool(Path root, Path group, Path journal, String build, String fixtureHash) throws Exception {
        this.build = build;
        this.fixtureHash = fixtureHash;
        requestNonce = WorkerReservation.class.getDeclaredField("requestNonce");
        requestNonce.setAccessible(true);
        generationCounts = WorkerPoolLedger.class.getDeclaredField("generations");
        generationCounts.setAccessible(true);
        Files.createDirectory(journal, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
        WarmImageLauncher launcher = new WarmImageLauncher(root, root.resolve("backend/target"), build);
        ledger = WorkerPoolLedger.open(journal, group, build, "document-v1");
        pool = new WarmWorkerPool(ledger, launcher, build, "document-v1");
    }

    /** Observes current advisory availability without awaiting or mutating READY.
     * @return exact admission phase and pending generation identity
     */
    ObjectNode admission() {
        synchronized (ledger) {
            remember();
            for (WorkerReservation token : ledger.reservations()) {
                if (token.unassigned()) {
                    String phase = token.phase() == WorkerReservation.Phase.READY ? "READY" : "STARTING";
                    return identity(token).put("phase", phase).put("actualPhase", token.phase().name());
                }
            }
            return JsonNodeFactory.instance.objectNode().put("poolNonce", ledger.poolNonce()).put("phase", "EMPTY");
        }
    }

    /** Explicitly conditions only the separate READY profile before admission.
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception startup failure, UNKNOWN or readiness expiry
     */
    void condition() throws Exception {
        pool.begin();
        long end = System.nanoTime() + 5_000_000_000L;
        while (System.nanoTime() < end) {
            ObjectNode observed = admission();
            if ("READY".equals(observed.path("phase").asText())) return;
            for (WorkerReservation token : ledger.reservations()) {
                if (token.phase() == WorkerReservation.Phase.UNKNOWN) throw new IOException("Unknown startup");
            }
            TimeUnit.MILLISECONDS.sleep(1);
        }
        throw new IOException("Conditional READY expired");
    }

    /** Runs the unchanged advisory coordinator and final publication fence.
     * @param fixture exact immutable registered validation input
     * @param row current bounded timing record
     * @param records bounded response buffer owner
     * @param index exact response buffer index
     * @return canonical complete bytes returned by actual publication
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception actual validation, context, cleanup or publication failure
     */
    byte[] execute(JsonNode fixture, ObjectNode row, WarmLatencyRecords records, int index) throws Exception {
        WarmDeadline deadline = WarmDeadline.fromStart(row.path("startNs").asLong(), 10000);
        WarmRequestBinding binding = new WarmRequestBinding(UUID.randomUUID().toString(), fixtureHash,
                "server:00000000-0000-0000-0000-000000000001", 0, "document-v1", build, ledger.poolNonce());
        pool.begin();
        synchronized (ledger) { remember(); }
        WarmContextPermit permit = WarmSemanticProtocol.permit(binding, WarmSemanticProtocol.context(fixture));
        row.put("requestNonce", binding.nonce());
        row.put("callStartNs", System.nanoTime());
        try (WarmResultLease lease = pool.validate(binding, fixture.path("candidate"), permit, deadline)) {
            row.put("callEndNs", System.nanoTime());
            row.set("consumed", consumed(binding.nonce()));
            JsonNode response = lease.result();
            byte[] bytes = JsonWire.encode(response);
            row.put("serializedNs", System.nanoTime());
            records.response(index, bytes);
            WarmLatencyRecords.successful(response);
            byte[] published = lease.publish(bytes);
            row.put("publicationEndNs", System.nanoTime());
            return published;
        }
    }

    /** Retains only references and identities before publication clears production metadata.
     * @param nonce exact admitted request identity
     * @return consumed CLEAN generation observation
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception absent or ambiguous exact consumption identity
     */
    private ObjectNode consumed(String nonce) throws Exception {
        synchronized (ledger) {
            remember();
            ObjectNode result = null;
            for (WorkerReservation token : ledger.reservations()) {
                if (nonce.equals(requestNonce.get(token))) {
                    if (result != null) throw new IOException("Ambiguous consumed generation");
                    result = identity(token).put("requestNonce", nonce).put("pid", token.childPid())
                            .put("startTicks", token.childStartTicks()).put("phaseBeforePublish", token.phase().name());
                }
            }
            if (result == null || !"CLEAN".equals(result.path("phaseBeforePublish").asText())) {
                throw new IOException("Consumed CLEAN generation absent");
            }
            return result;
        }
    }

    /** Captures live token and Process references without file reads or lifecycle writes. */
    private void remember() {
        for (WorkerReservation token : ledger.reservations()) {
            Process observed = generations.get(token);
            if (observed == null) generations.put(token, token.child());
        }
    }

    /** Encodes an exact local generation identity without inspecting the filesystem.
     * @param token actual retained production reservation
     * @return stable pool, group and generation metadata
     */
    private ObjectNode identity(WorkerReservation token) {
        return JsonNodeFactory.instance.objectNode().put("poolNonce", ledger.poolNonce()).put("slot", token.slot())
                .put("generation", token.generation()).put("workerNonce", token.nonce())
                .put("group", token.group().relative()).put("device", token.group().device()).put("inode", token.group().inode());
    }

    /** Retains the last spare attachment outside request timings before production shutdown.
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception uncertain or expired attempted spare attachment
     */
    private void captureSpare() throws Exception {
        for (WorkerReservation token : ledger.reservations()) {
            while (token.child() == null && token.phase() != WorkerReservation.Phase.RELEASED
                    && System.nanoTime() < token.startupDeadline()) {
                remember();
                TimeUnit.MILLISECONDS.sleep(1);
            }
            remember();
            if (token.attempted() && generations.get(token) == null) throw new IOException("Spare child unobserved");
        }
    }

    /** Closes actual ownership while retaining both capture and shutdown failures.
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception incomplete physical or logical cleanup
     */
    void close() throws Exception {
        Exception failure = null;
        try { captureSpare(); } catch (Exception error) { failure = error; }
        try { pool.close(); poolClosed = true; }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        try { ledger.close(); ledgerClosed = true; }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        if (failure != null) throw failure;
    }

    /** Writes post-teardown terminal receipts and positively checks original child absence.
     * @param output report generation array
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception missing production receipt or retained child incarnation
     */
    void terminals(ArrayNode output) throws Exception {
        for (Map.Entry<WorkerReservation, Process> entry : generations.entrySet()) {
            WorkerReservation token = entry.getKey();
            Process child = entry.getValue();
            ObjectNode item = identity(token).put("pid", token.childPid()).put("startTicks", token.childStartTicks())
                    .put("phase", token.phase().name()).put("attempted", token.attempted());
            output.add(item);
            ObjectNode counters = item.putObject("terminalCounters");
            for (var counter : token.group().terminal().entrySet()) counters.put(counter.getKey(), counter.getValue());
            if (child != null) terminalChild(item, token, child);
            else if (token.attempted()) throw new IOException("Attempted generation lacks Process receipt");
            if (token.group().terminal().isEmpty()) throw new IOException("Missing terminal group counters");
        }
        requireCompleteInventory();
    }

    /** Rejects missing retired generations instead of inventing terminal ownership receipts.
     * @throws IllegalAccessException unavailable read-only generation counter observation
     * @throws IOException incomplete observed generation inventory
     */
    private void requireCompleteInventory() throws IllegalAccessException, IOException {
        long[] counts = (long[]) generationCounts.get(ledger);
        if (counts[0] + counts[1] != generations.size()) throw new IOException("Generation inventory incomplete");
    }

    /** Checks direct child termination and exact kernel incarnation absence after cleanup.
     * @param item terminal record receiving checks
     * @param token exact generation metadata
     * @param child original retained Process object
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception process still running or missing release
     */
    private void terminalChild(ObjectNode item, WorkerReservation token, Process child) throws Exception {
        boolean reaped = child.waitFor(0, TimeUnit.MILLISECONDS) && !child.isAlive();
        boolean absent = WorkerReservation.absent(token.childPid(), token.childStartTicks());
        item.put("directChildReaped", reaped).put("pidStartAbsent", absent);
        if (!reaped || !absent || token.phase() != WorkerReservation.Phase.RELEASED) {
            throw new IOException("Generation terminal ownership incomplete");
        }
        item.put("exitCode", child.exitValue());
    }

    /** Reports actual coordinator and ledger close outcomes.
     * @return finite logical cleanup observation
     */
    ObjectNode cleanup() {
        return JsonNodeFactory.instance.objectNode().put("poolClosed", poolClosed).put("ledgerClosed", ledgerClosed)
                .put("remainingReservations", ledger.reservations().length);
    }
}
