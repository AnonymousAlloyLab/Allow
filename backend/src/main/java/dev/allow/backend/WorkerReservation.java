package dev.allow.backend;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.util.UUID;

/** Opaque, single-generation capability; only the synchronized ledger mutates its state. */
final class WorkerReservation {
    /** Operational phases; UNKNOWN never authorizes capacity release. */
    enum Phase { RESERVED, STARTING, READY, ASSIGNED, STAGED, RETIRING, CLEAN, RELEASED, UNKNOWN }
    private final int slot;
    private final long generation;
    private final String nonce;
    private final boolean standby;
    private final long startupDeadline;
    private final WorkerCgroup group;
    private volatile Phase phase = Phase.RESERVED;
    private volatile Process child;
    private volatile long childPid;
    private volatile String childStart = "";
    private volatile boolean attempted;
    private volatile boolean poisoned;
    private volatile boolean assigned;
    private volatile boolean published;
    private volatile String requestNonce = "";
    private volatile long idleDeadline;
    private volatile long requestDeadline;

    /** Creates a nonreusable capability before any launch attempt.
     * @param slot bounded slot index
     * @param generation monotone slot generation
     * @param standby whether this is an unassigned warm worker
     * @param group already opened empty contained group
     * @param now monotonic reservation instant
     */
    WorkerReservation(int slot, long generation, boolean standby, WorkerCgroup group, long now) {
        this.slot = slot;
        this.generation = generation;
        this.standby = standby;
        this.group = group;
        this.nonce = UUID.randomUUID().toString();
        this.startupDeadline = now + 5_000_000_000L;
        this.assigned = !standby;
    }

    /** Returns the reserved index.
     * @return zero or one
     */
    int slot() { return slot; }
    /** Returns the monotone generation.
     * @return positive generation
     */
    long generation() { return generation; }
    /** Returns the public bootstrap nonce.
     * @return canonical UUID
     */
    String nonce() { return nonce; }
    /** Returns the exact captured group.
     * @return descriptor owner
     */
    WorkerCgroup group() { return group; }
    /** Returns the direct owned child.
     * @return attached process or null before attachment
     */
    Process child() { return child; }
    /** Returns the observed child PID.
     * @return zero until attachment
     */
    long childPid() { return childPid; }
    /** Returns the observed child incarnation.
     * @return Linux start ticks or empty before attachment
     */
    String childStartTicks() { return childStart; }
    /** Returns the current lifecycle state.
     * @return operational phase
     */
    Phase phase() { return phase; }
    /** Reports whether spawn was ever attempted.
     * @return sticky attempt marker
     */
    boolean attempted() { return attempted; }
    /** Reports sticky cancellation or failure.
     * @return whether successful publication is forbidden
     */
    boolean poisoned() { return poisoned; }
    /** Reports an outstanding unassigned warm reservation.
     * @return whether the standby budget is occupied
     */
    boolean unassigned() { return standby && !assigned && phase != Phase.RELEASED; }
    /** Reports an occupied active reservation.
     * @return whether the active budget is occupied
     */
    boolean active() { return assigned && phase != Phase.RELEASED; }
    /** Returns startup expiry.
     * @return monotonic nanoseconds
     */
    long startupDeadline() { return startupDeadline; }
    /** Returns READY expiry.
     * @return monotonic nanoseconds
     */
    long idleDeadline() { return idleDeadline; }

    /** Marks the durable pre-spawn barrier. */
    void attempting() { attempted = true; phase = Phase.STARTING; }
    /** Attaches an exact direct child before public bootstrap release.
     * @param process direct ProcessBuilder child
     * @throws IOException unavailable Linux incarnation
     */
    void attach(Process process) throws IOException {
        child = process;
        childPid = process.pid();
        childStart = startTicks(childPid);
        ProcessHandle parent = process.toHandle().parent().orElse(null);
        if (parent == null || parent.pid() != ProcessHandle.current().pid()) throw new IOException("Worker is not a direct child");
    }
    /** Records validated READY under the ledger lock.
     * @param now readiness instant
     */
    void ready(long now) { phase = Phase.READY; idleDeadline = now + 30_000_000_000L; }
    /** Consumes this one-use generation after the trusted context adapter succeeds.
     * @param request admitted operation nonce
     * @param admitted monotonic admission instant
     */
    void assign(String request, long admitted) {
        assigned = true;
        requestNonce = request;
        requestDeadline = admitted + 10_000_000_000L;
        phase = Phase.ASSIGNED;
    }
    /** Records a response without retaining any response bytes. */
    void stage() { phase = Phase.STAGED; }
    /** Makes failure sticky, including cancellation after cleanup. */
    void poison() {
        poisoned = true;
        if (phase != Phase.CLEAN && phase != Phase.UNKNOWN) phase = Phase.RETIRING;
    }
    /** Records cleanup uncertainty without freeing the reservation. */
    void unknown() { poisoned = true; phase = Phase.UNKNOWN; }
    /** Records observed exact cleanup, never inferred from a timer. */
    void clean() { phase = Phase.CLEAN; }
    /** Records the publication linearization point. */
    void publish() { published = true; }
    /** Detaches the process reference only after terminal release. */
    void release() { phase = Phase.RELEASED; child = null; requestNonce = ""; }

    /** Checks publication authority without allowing an earlier cached fence.
     * @param request current operation nonce
     * @param now current monotonic time
     * @return whether this cleaned one-use result may publish
     */
    boolean publishable(String request, long now) {
        return phase == Phase.CLEAN && assigned && !poisoned && !published
                && requestNonce.equals(request) && now - requestDeadline < 0;
    }
    /** Checks terminal outcome before removing a cleaned reservation.
     * @return whether no private outcome remains unresolved
     */
    boolean releasable() { return phase == Phase.CLEAN && (poisoned || published || !assigned || !standby); }

    /** Serializes operational metadata only; private frames never enter the journal.
     * @param node empty slot record
     */
    void write(ObjectNode node) {
        node.put("slot", slot).put("generation", generation).put("nonce", nonce).put("standby", standby);
        node.put("phase", phase.name()).put("attempted", attempted).put("poisoned", poisoned);
        node.put("assigned", assigned).put("published", published).put("childPid", childPid);
        node.put("childStartTicks", childStart).put("group", group.relative());
        node.put("device", group.device()).put("inode", group.inode());
    }

    /** Reads Linux identity without interpreting a command name as whitespace-delimited fields.
     * @param pid positive kernel PID
     * @return exact decimal start ticks
     * @throws IOException missing or malformed process identity
     */
    static String startTicks(long pid) throws IOException {
        String stat = Files.readString(Path.of("/proc", Long.toString(pid), "stat"));
        int end = stat.lastIndexOf(')');
        String[] fields = end < 0 ? new String[0] : stat.substring(end + 2).split(" ");
        if (fields.length < 20 || !fields[19].matches("[0-9]+")) throw new IOException("Worker identity unavailable");
        return fields[19];
    }

    /** Observes absence of this exact incarnation, treating unreadable state as uncertainty.
     * @param pid prior observed PID
     * @param start prior observed start ticks
     * @return whether the exact old incarnation is absent
     * @throws IOException inaccessible process metadata
     */
    static boolean absent(long pid, String start) throws IOException {
        if (pid <= 0 || !start.matches("[0-9]+")) return false;
        try { return !startTicks(pid).equals(start); }
        catch (NoSuchFileException missing) { return true; }
    }
}
