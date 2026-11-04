package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/** Retains independent kernel events and original Process identity across production release. */
final class WarmProbeWitness implements AutoCloseable {
    private final WorkerReservation token;
    private final SeekableByteChannel events;
    private final ObjectNode observations = JsonNodeFactory.instance.objectNode();
    private Process child;
    private long pid;
    private String start = "";

    /** Opens independent events before the production owner may remove the captured group.
     * @param ledger actual production owner
     * @param token actual reserved generation
     * @throws IOException unavailable or substituted group
     */
    WarmProbeWitness(WorkerPoolLedger ledger, WorkerReservation token) throws IOException {
        this.token = token;
        Path group = ledger.cgroupRoot().resolve(token.group().relative());
        WarmProbeFiles.require((long) Files.getAttribute(group, "unix:dev") == token.group().device()
                && (long) Files.getAttribute(group, "unix:ino") == token.group().inode(), "Group identity changed");
        events = Files.newByteChannel(group.resolve("cgroup.events"), Set.of(StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS));
        observations.put("group", token.group().relative()).put("device", token.group().device()).put("inode", token.group().inode());
        observations.put("initialIndependentEvents", readEvents()).put("slot", token.slot()).put("generation", token.generation());
        observeChild(token.child());
    }

    /** Retains the original direct child, including a gate-injected preattachment failure.
     * @param process actual ProcessBuilder child or null before spawn
     * @throws IOException unavailable child incarnation
     */
    void observeChild(Process process) throws IOException {
        if (process == null || child != null) return;
        child = process;
        pid = process.pid();
        start = token.childStartTicks().isEmpty() ? WorkerReservation.startTicks(pid) : token.childStartTicks();
        observations.put("pid", pid).put("startTicks", start);
    }

    /** Reads only the captured kernel events descriptor with a finite bound.
     * @return actual events text
     * @throws IOException unavailable or excessive metadata
     */
    private String readEvents() throws IOException {
        events.position(0);
        ByteBuffer data = ByteBuffer.allocate(4096);
        while (events.read(data) > 0) WarmProbeFiles.require(data.hasRemaining(), "Events exceed limit");
        data.flip();
        return StandardCharsets.US_ASCII.decode(data).toString();
    }

    /** Records an independent observation before cleanup when the generation is still present.
     * @throws IOException unavailable independent observation
     */
    void observeLive() throws IOException {
        observeChild(token.child());
        observations.put("beforeCleanupIndependentEvents", readEvents());
        observations.put("observedPhase", token.phase().name());
    }

    /** Retains the production serializer's operational descriptor without reading its bootstrap pipe.
     * @param metadata exact descriptor reconstructed from retained trusted generation metadata
     */
    void bootstrap(ObjectNode metadata) {
        observations.set("productionBootstrapMetadata", metadata.deepCopy());
        observations.put("bootstrapObservation", "SAME_TRUSTED_SERIALIZER_METADATA_NOT_PIPE_CAPTURE");
    }

    /** Captures exact terminal receipts and requires actual direct-child reap and incarnation absence.
     * @return retained kernel and production lifecycle evidence
     * @throws IOException unconfirmed cleanup
     * @throws InterruptedException interrupted independent wait
     */
    ObjectNode terminal() throws IOException, InterruptedException {
        observeChild(token.child());
        if (child != null) {
            WarmProbeFiles.require(child.waitFor(0, TimeUnit.MILLISECONDS) && !child.isAlive(), "Child reap unconfirmed");
            WarmProbeFiles.require(WorkerReservation.absent(pid, start), "Owned incarnation remains present");
            observations.put("exitCode", child.exitValue()).put("directChildReaped", true);
        } else WarmProbeFiles.require(!token.attempted(), "Attempted worker lacks retained Process");
        observations.put("finalPhase", token.phase().name());
        ObjectNode counters = observations.putObject("terminalCounters");
        for (var entry : token.group().terminal().entrySet()) counters.put(entry.getKey(), entry.getValue());
        try { observations.put("finalIndependentEvents", readEvents()); }
        catch (IOException removed) { observations.put("finalIndependentEventsUnavailable", removed.getClass().getSimpleName()); }
        return observations.deepCopy();
    }

    /** Returns positive emptiness only from actual captured terminal events.
     * @return whether exactly one populated-zero line was retained
     */
    boolean populatedZero() {
        String value = token.group().terminal().getOrDefault("cgroup.events", "");
        return value.lines().filter("populated 0"::equals).count() == 1 && !value.contains("populated 1");
    }

    /** Supplies the exact original process incarnation for independent outer absence checks.
     * @return identity object, or null when no process was spawned
     */
    ObjectNode identity() {
        return pid == 0 ? null : JsonNodeFactory.instance.objectNode().put("pid", pid).put("start_ticks", start);
    }

    /** Returns the retained real reservation, never a reconstructed capability.
     * @return actual generation object
     */
    WorkerReservation token() { return token; }

    /** Closes only this gate observer's independent kernel descriptor.
     * @throws IOException failed independent descriptor close
     */
    @Override
    public void close() throws IOException { events.close(); }
}
