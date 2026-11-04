package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

/** Real-clock idle observation with no deadline/state injection or implicit restart demand. */
final class WarmSequenceIdle {
    /** Prevents construction of the fixed finite idle observer. */
    private WarmSequenceIdle() {}

    /** Observes actual expiry, terminal ownership and two seconds with no admission calls.
     * @param ledger actual same-incarnation owner
     * @param token ready unassigned worker
     * @param transport real transport readiness-clock observer
     * @param journal actual private metadata directory
     * @param witness retained independent group/process observer
     * @return bounded phase/clock and durable generation evidence
     * @throws Exception early retirement, failed cleanup or unexpected self-refill
     */
    static ObjectNode observe(WorkerPoolLedger ledger, WorkerReservation token, WarmTransport transport,
            Path journal, WarmProbeWitness witness) throws Exception {
        long ready = transport.readyNanos();
        long deadline = token.idleDeadline();
        WarmProbeFiles.require(ready > 0 && deadline == ready + 30_000_000_000L
                && token.phase() == WorkerReservation.Phase.READY, "Idle READY clock unavailable");
        ObjectNode value = JsonNodeFactory.instance.objectNode();
        value.set("expired", WarmSequenceRecords.identity(token));
        value.put("transportReadyNanos", ready).put("idleDeadlineNanos", deadline);
        long observed = awaitRelease(ledger, token, deadline, value.putArray("phaseSamples"));
        value.put("releasedObservedNanos", observed);
        witness.terminal();
        WarmProbeFiles.require(witness.populatedZero(), "Idle terminal group emptiness unavailable");
        value.put("terminalCleanupObservedBeforeQuiet", true);
        quiet(ledger, journal, value);
        return value;
    }

    /** Records bounded phase brackets; a later observation is not an exact retirement timestamp.
     * @param ledger actual ledger synchronization boundary
     * @param token exact idle worker
     * @param deadline unchanged production idle deadline
     * @param samples bounded observed phase records
     * @return actual time when RELEASED was observed
     * @throws Exception early retirement, UNKNOWN or late cleanup observation
     * @throws IOException finite observation count exceeded
     */
    private static long awaitRelease(WorkerPoolLedger ledger, WorkerReservation token, long deadline,
            ArrayNode samples) throws Exception {
        while (samples.size() < 800) {
            synchronized (ledger) {
                WorkerReservation.Phase phase = token.phase();
                int count = ledger.reservations().length;
                long now = System.nanoTime();
                samples.addObject().put("observedNanos", now).put("phase", phase.name()).put("reservations", count);
                WarmProbeFiles.require(now >= deadline || phase == WorkerReservation.Phase.READY && count == 1,
                        "Early idle retirement observed");
                WarmProbeFiles.require(ledger.online() && now <= deadline + 3_000_000_000L, "Idle cleanup observation unavailable");
                if (phase == WorkerReservation.Phase.RELEASED) {
                    WarmProbeFiles.require(count == 0, "Idle expiry retained reservation");
                    return now;
                }
                WarmProbeFiles.require(phase == WorkerReservation.Phase.READY || phase == WorkerReservation.Phase.RETIRING
                        || phase == WorkerReservation.Phase.CLEAN, "Idle lifecycle failed");
            }
            TimeUnit.MILLISECONDS.sleep(50);
        }
        throw new IOException("Idle observation sample cap reached");
    }

    /** Checks a genuine quiet interval and unchanged monotone counters without calling begin.
     * @param ledger actual online empty owner
     * @param journal private durable metadata directory
     * @param value finite idle evidence
     * @throws Exception new reservation, offline owner or changed generation counters
     */
    private static void quiet(WorkerPoolLedger ledger, Path journal, ObjectNode value) throws Exception {
        JsonNode before = generations(journal);
        value.set("generationsBefore", before);
        ArrayNode samples = value.putArray("quietSamples");
        long start = sampleEmpty(ledger, samples);
        long end = start;
        value.put("quietStartNanos", start).put("noBeginDuringQuiet", true);
        while (end - start < 2_000_000_000L && samples.size() < 150) {
            TimeUnit.MILLISECONDS.sleep(20);
            end = sampleEmpty(ledger, samples);
        }
        WarmProbeFiles.require(end - start >= 2_000_000_000L, "Quiet interval sample cap reached");
        JsonNode after = generations(journal);
        value.put("quietEndNanos", end);
        value.set("generationsAfter", after);
        WarmProbeFiles.require(before.equals(after), "Hidden idle generation advance");
    }

    /** Samples exact empty and online state under the ledger monitor before reading its timestamp.
     * @param ledger actual same-incarnation owner
     * @param samples finite quiet evidence
     * @return timestamp of this complete actual observation
     * @throws IOException unexpected admission or offline owner
     */
    private static long sampleEmpty(WorkerPoolLedger ledger, ArrayNode samples) throws IOException {
        synchronized (ledger) {
            int count = ledger.reservations().length;
            boolean online = ledger.online();
            long now = System.nanoTime();
            samples.addObject().put("observedNanos", now).put("reservations", count).put("online", online);
            WarmProbeFiles.require(online && count == 0, "Idle pool refilled without demand");
            return now;
        }
    }

    /** Reads atomic operational metadata without opening or disturbing the POSIX lock file.
     * @param directory actual private journal directory
     * @return exact two monotone generation counters
     * @throws IOException malformed or aliased journal evidence
     */
    private static JsonNode generations(Path directory) throws IOException {
        Path path = directory.resolve("pool.json");
        WarmProbeFiles.require(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS) && Files.size(path) <= 32768,
                "Idle journal metadata unavailable");
        JsonNode value = JsonWire.decode(Files.readAllBytes(path), JsonNode.class);
        JsonNode counters = value.path("generations");
        WarmProbeFiles.require(counters.isArray() && counters.size() == 2, "Idle generation counters unavailable");
        for (JsonNode counter : counters) WarmProbeFiles.require(counter.isIntegralNumber() && counter.longValue() >= 0,
                "Invalid idle generation counter");
        return counters.deepCopy();
    }
}
