package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Path;

/** Finite sequential component experiment; buffers results until all owned work stops. */
final class WarmLatencySeries {
    private final Path root;
    private final JsonNode plan;
    private final JsonNode fixture;
    private final ObjectNode report;
    private final ObjectNode timing;
    private final ObjectNode cpu;
    private final ArrayNode terminals;
    private final WarmLatencyRecords records = new WarmLatencyRecords();
    private final String profile;
    private final int warmups;
    private final int expected;
    private WarmLatencyPool pool;
    private long previousEnd;

    /** Captures immutable declarations before allocating any pool ownership.
     * @param root canonical copied installation
     * @param plan frozen finite variant declaration
     * @param fixture registered immutable validation frame
     * @param report output object populated after teardown
     */
    WarmLatencySeries(Path root, JsonNode plan, JsonNode fixture, ObjectNode report) {
        this.root = root;
        this.plan = plan;
        this.fixture = fixture;
        this.report = report;
        profile = plan.path("profile").asText();
        warmups = plan.path("warmups").asInt();
        expected = warmups + plan.path("measured").asInt();
        timing = report.putObject("timing");
        cpu = report.putObject("cpu");
        terminals = report.putArray("generations");
    }

    /** Executes every registered attempt unless a failure stops the finite variant.
     * @throws Exception accounting or report finalization failure
     */
    void run() throws Exception {
        Exception failure = null;
        try { initialize(); attempts(); }
        catch (Exception error) { failure = error; }
        try { teardown(); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        records.emit(report, expected);
        report.put("status", failure == null ? "COMPLETE" : "FAILED");
        if (failure == null) report.putNull("failure");
        else report.set("failure", WarmLatencyRecords.failure(failure));
    }

    /** Initializes only the retained nonempty-profile coordinator outside request timings.
     * @throws Exception unavailable production ledger or helper
     */
    private void initialize() throws Exception {
        timing.put("initializationStartNs", System.nanoTime());
        if (profile.equals("POOL_SERIAL") || profile.equals("POOL_READY")) pool = createPool("series");
        timing.put("initializationEndNs", System.nanoTime());
    }

    /** Samples the measured boundary once and immediately admits each next operation.
     * @throws Exception first failed admitted operation or accounting sample
     */
    private void attempts() throws Exception {
        for (int index = 0; index < expected; index++) {
            if (index == warmups) {
                cpu.set("beforeMeasured", WarmLatencyResources.cpu(Path.of(plan.path("cpuStat").asText())));
                timing.put("measurementStartNs", System.nanoTime());
            }
            attempt(index);
        }
        timing.put("measurementEndNs", System.nanoTime());
        cpu.set("afterMeasured", WarmLatencyResources.cpu(Path.of(plan.path("cpuStat").asText())));
    }

    /** Admits one operation and always retains its actual terminal timing.
     * @param index exact registered attempt index
     * @throws Exception first operation or per-empty-incarnation cleanup failure
     */
    private void attempt(int index) throws Exception {
        ObjectNode row = records.row(index, warmups);
        long cycle = System.nanoTime();
        row.put("cycleStartNs", cycle);
        Exception failure = null;
        try { prepare(row, index); request(row, index); }
        catch (Exception error) { failure = error; row.set("failure", WarmLatencyRecords.failure(error)); }
        try { closeEmpty(row); }
        catch (Exception error) {
            if (failure == null) failure = error; else failure.addSuppressed(error);
            row.set("failure", WarmLatencyRecords.failure(failure));
        }
        long cycleEnd = row.path(profile.equals("POOL_EMPTY") ? "teardownEndNs" : "endNs").asLong(0);
        if (cycleEnd == 0) cycleEnd = System.nanoTime();
        row.put("cycleEndNs", cycleEnd).put("cycleDurationNs", cycleEnd - cycle);
        if (failure != null) throw failure;
        row.put("outcome", "SUCCESS");
    }

    /** Performs separately reported empty initialization or explicit READY conditioning.
     * @param row current attempt observation
     * @param index unique registered attempt index
     * @throws Exception unavailable cold owner or conditional readiness
     */
    private void prepare(ObjectNode row, int index) throws Exception {
        if (profile.equals("POOL_EMPTY")) {
            row.put("initializationStartNs", System.nanoTime());
            pool = createPool("empty-" + index);
            row.put("initializationEndNs", System.nanoTime());
        }
        if (profile.equals("POOL_READY")) {
            long start = System.nanoTime();
            row.put("conditionStartNs", start);
            pool.condition();
            long end = System.nanoTime();
            row.put("conditionEndNs", end).put("conditionDurationNs", end - start);
        }
    }

    /** Times actual capacity admission through serialization, publication and permit release.
     * @param row bounded observation record
     * @param index response buffer index
     * @throws Exception production worker or exact output failure
     */
    private void request(ObjectNode row, int index) throws Exception {
        long start = System.nanoTime();
        row.put("startNs", start);
        if (previousEnd != 0) row.put("previousEndToAdmissionGapNs", start - previousEnd);
        if (pool != null) {
            row.put("admissionObservedNs", System.nanoTime());
            row.set("admission", pool.admission());
        }
        boolean held = false;
        try {
            WorkerCapacity.acquire();
            held = true;
            row.put("capacityAcquiredNs", System.nanoTime());
            if (profile.equals("FRESH")) WarmLatencyFresh.execute(fixture, row, records, index);
            else pool.execute(fixture, row, records, index);
        } finally {
            if (held) { WorkerCapacity.release(); row.put("capacityReleasedNs", System.nanoTime()); }
            long end = System.nanoTime();
            row.put("endNs", end).put("durationNs", end - start);
            previousEnd = end;
        }
    }

    /** Closes one empty-profile incarnation within the explicitly separate full cycle.
     * @param row attempt receiving teardown instants
     * @throws Exception incomplete actual owned teardown
     */
    private void closeEmpty(ObjectNode row) throws Exception {
        if (!profile.equals("POOL_EMPTY") || pool == null) return;
        row.put("teardownStartNs", System.nanoTime());
        try { pool.close(); pool.terminals(terminals); report.set("cleanup", pool.cleanup()); }
        finally { row.put("teardownEndNs", System.nanoTime()); }
        pool = null;
    }

    /** Creates the next unique private journal using the same pinned production image.
     * @param name finite registered incarnation basename
     * @return actual coordinator owner
     * @throws Exception unavailable containment or source identity
     */
    private WarmLatencyPool createPool(String name) throws Exception {
        return new WarmLatencyPool(root, Path.of(plan.path("cgroupRoot").asText()),
                root.resolve(".runtime/warm-pool/journal").resolve(name), report.path("buildSha256").asText(),
                plan.path("fixtureSha256").asText());
    }

    /** Stops the retained spare and emits CPU tail and terminal receipts after the block.
     * @throws Exception incomplete owned cleanup or kernel accounting
     */
    private void teardown() throws Exception {
        timing.put("teardownStartNs", System.nanoTime());
        if (!timing.has("measurementEndNs")) timing.put("measurementEndNs", System.nanoTime());
        if (!cpu.has("afterMeasured")) cpu.set("afterMeasured", WarmLatencyResources.cpu(Path.of(plan.path("cpuStat").asText())));
        Exception failure = null;
        try { closeRetained(); } catch (Exception error) { failure = error; }
        timing.put("teardownEndNs", System.nanoTime());
        cpu.set("afterTeardown", WarmLatencyResources.cpu(Path.of(plan.path("cpuStat").asText())));
        if (failure != null) throw failure;
    }

    /** Closes retained production ownership and preserves receipt failures independently.
     * @throws Exception incomplete pool or terminal group evidence
     */
    private void closeRetained() throws Exception {
        if (pool == null) {
            if (!report.has("cleanup")) report.putObject("cleanup").put("poolClosed", true)
                    .put("ledgerClosed", true).put("remainingReservations", 0);
            return;
        }
        Exception failure = null;
        try { pool.close(); } catch (Exception error) { failure = error; }
        report.set("cleanup", pool.cleanup());
        try { pool.terminals(terminals); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        if (failure != null) throw failure;
    }
}
