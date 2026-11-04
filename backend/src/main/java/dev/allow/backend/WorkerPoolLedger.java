package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/** Single synchronized owner of warm and fresh process-tree reservations. */
final class WorkerPoolLedger implements AutoCloseable {
    private final WorkerJournal journal;
    private final Path cgroupRoot;
    private final String build;
    private final String policy;
    private final String poolNonce = UUID.randomUUID().toString();
    private final long ownerPid = ProcessHandle.current().pid();
    private final String ownerStart;
    private final String bootId;
    private final long rootDevice;
    private final long rootInode;
    private final WorkerReservation[] slots = new WorkerReservation[2];
    private final long[] generations = new long[2];
    private boolean online = true;
    private boolean closed;

    /** Acquires the private ledger and reconciles old metadata before admitting any spawn.
     * @param directory provisioned private metadata directory
     * @param delegatedRoot trusted private cgroup2 subtree
     * @param build full installed image digest
     * @param policy installed validation policy
     * @return exclusive pool incarnation
     * @throws IOException unsupported containment, durability or old uncertainty
     */
    static WorkerPoolLedger open(Path directory, Path delegatedRoot, String build, String policy) throws IOException {
        WorkerJournal journal = new WorkerJournal(directory);
        try { return new WorkerPoolLedger(journal, delegatedRoot, build, policy); }
        catch (IOException | RuntimeException failure) { journal.close(); throw failure; }
    }

    /** Captures the current owner and initializes its empty private pool node.
     * @param journal acquired durable owner
     * @param root canonical delegated root
     * @param build installed digest
     * @param policy installed validation policy
     * @throws IOException unsupported containment or reconciliation
     */
    private WorkerPoolLedger(WorkerJournal journal, Path root, String build, String policy) throws IOException {
        this.journal = journal;
        this.cgroupRoot = root;
        this.build = build;
        this.policy = policy;
        this.ownerStart = WorkerReservation.startTicks(ownerPid);
        this.bootId = Files.readString(Path.of("/proc/sys/kernel/random/boot_id")).trim();
        if (!root.isAbsolute() || !root.toRealPath().equals(root) || !Files.getFileStore(root).type().equals("cgroup2")) {
            throw new IOException("Private cgroup delegation required");
        }
        this.rootDevice = (Long) Files.getAttribute(root, "unix:dev", LinkOption.NOFOLLOW_LINKS);
        this.rootInode = (Long) Files.getAttribute(root, "unix:ino", LinkOption.NOFOLLOW_LINKS);
        reconcile(journal.readForRoot(cgroupRoot));
        initializeGroup();
        persist();
    }

    /** Creates the process-free parent and enables already delegated bounded controllers.
     * @throws IOException incomplete delegation
     */
    private void initializeGroup() throws IOException {
        Path pool = cgroupRoot.resolve("pool-" + poolNonce);
        Files.createDirectory(pool);
        Files.writeString(pool.resolve("cgroup.subtree_control"), "+memory +pids");
        String controls = Files.readString(pool.resolve("cgroup.subtree_control"));
        if (!controls.contains("memory") || !controls.contains("pids")) throw new IOException("Worker controllers unavailable");
    }

    /** Conservatively reconciles exact old identities; an unkeyed attempt is never absence.
     * @param prior previously forced metadata, or null initially
     * @throws IOException any incomplete or unsafe previous incarnation
     */
    private void reconcile(ObjectNode prior) throws IOException {
        if (prior == null) return;
        for (int index = 0; index < 2; index++) generations[index] = prior.path("generations").get(index).longValue();
        for (JsonNode slot : prior.path("slots")) {
            if (slot.isNull()) continue;
            boolean ownerAbsent = !prior.path("bootId").textValue().equals(bootId)
                    || WorkerReservation.absent(prior.path("ownerPid").longValue(), prior.path("ownerStartTicks").textValue());
            if (!ownerAbsent) throw new IOException("Prior worker owner remains present");
            reconcileSlot(slot);
        }
    }

    /** Requires exact group emptiness and old direct-child absence before restart release.
     * @param slot old generation metadata
     * @throws IOException spawn gap, missing group or incomplete cleanup evidence
     */
    private void reconcileSlot(JsonNode slot) throws IOException {
        if (slot.path("attempted").booleanValue()
                && !WorkerReservation.absent(slot.path("childPid").longValue(), slot.path("childStartTicks").textValue())) {
            throw new IOException("Prior worker spawn remains uncertain");
        }
        try (WorkerCgroup group = WorkerCgroup.open(cgroupRoot, slot.path("group").textValue())) {
            if (group.device() != slot.path("device").longValue() || group.inode() != slot.path("inode").longValue()
                    || !group.empty()) throw new IOException("Prior worker group remains uncertain");
            group.captureTerminal();
            group.remove();
        }
    }

    /** Reserves at most one warm worker before creating any process.
     * @return exclusive one-use capability
     * @throws IOException unavailable or full pool
     */
    synchronized WorkerReservation reserveStandby() throws IOException { return reserve(true); }
    /** Reserves a fresh solver or durable worker in the same two-tree ledger.
     * @return exclusive fresh launch capability
     * @throws IOException unavailable or active pool
     */
    synchronized WorkerReservation reserveFresh() throws IOException { return reserve(false); }

    /** Atomically enforces live, unassigned and active bounds before durable reservation.
     * @param standby whether admission occupies the single standby position
     * @return forced generation record
     * @throws IOException capacity, containment or journal failure
     */
    private WorkerReservation reserve(boolean standby) throws IOException {
        requireOnline();
        int free = -1;
        for (int index = 0; index < slots.length; index++) {
            WorkerReservation current = slots[index];
            if (current == null) free = index;
            else if (standby ? current.unassigned() : current.active()) throw new IOException("Worker capacity reached");
        }
        if (free < 0 || generations[free] == Long.MAX_VALUE) throw new IOException("Worker capacity reached");
        long reservedAt = System.nanoTime();
        long generation = ++generations[free];
        String relative = "pool-" + poolNonce + "/slot-" + free + "-g" + generation;
        WorkerCgroup group;
        try { group = WorkerCgroup.create(cgroupRoot, relative); }
        catch (IOException | RuntimeException failure) { creationFailed(failure); throw failure; }
        WorkerReservation reservation = new WorkerReservation(free, generation, standby, group, reservedAt);
        slots[free] = reservation;
        persist();
        return reservation;
    }

    /** Disables this incarnation after failed containment setup, even if retirement cannot persist.
     * @param failure original creation failure whose identity and cause must be preserved
     */
    private void creationFailed(Exception failure) {
        try { disable(); }
        catch (IOException | RuntimeException retirement) {
            if (retirement != failure) failure.addSuppressed(retirement);
        }
    }

    /** Forces the attempted marker before ProcessBuilder.start, even if start later throws.
     * @param token exact reserved generation
     * @throws IOException stale, expired or cancelled admission
     */
    synchronized void markSpawnAttempt(WorkerReservation token) throws IOException {
        requireOnline();
        owned(token);
        if (token.phase() != WorkerReservation.Phase.RESERVED || token.poisoned()
                || expired(token.startupDeadline())) throw new IOException("Worker startup unavailable");
        token.attempting();
        persist();
    }

    /** Captures and forces a direct child incarnation before the public bootstrap is written.
     * @param token exact attempted generation
     * @param child direct ProcessBuilder result; never a PID-only handle
     * @throws IOException attachment or durability uncertainty
     */
    synchronized void attach(WorkerReservation token, Process child) throws IOException {
        owned(token);
        if (!token.attempted() || token.child() != null || child == null) throw new IOException("Worker attachment rejected");
        try { token.attach(child); persist(); }
        catch (IOException failure) { uncertain(token); throw failure; }
    }

    /** Admits a single READY only after the transport verifies its entire exact line.
     * @param token attached warm generation
     * @param nonce decoded generation nonce
     * @param image decoded captured image identity
     * @throws IOException stale, duplicate, cancelled or expired READY
     */
    synchronized void markReady(WorkerReservation token, String nonce, String image) throws IOException {
        markReady(token, nonce, image, System.nanoTime());
    }

    /** Binds idle expiry to the actual transport READY observation rather than scheduler delay.
     * @param token attached warm generation
     * @param nonce decoded generation nonce
     * @param image decoded captured image identity
     * @param observedReadyNanos transport's monotonic exact READY completion time
     * @throws IOException stale, duplicate, cancelled or expired READY
     */
    synchronized void markReady(WorkerReservation token, String nonce, String image, long observedReadyNanos) throws IOException {
        requireOnline();
        owned(token);
        if (!build.equals(image)) { disable(); throw new IOException("Worker image changed"); }
        if (!token.unassigned() || token.phase() != WorkerReservation.Phase.STARTING || token.child() == null
                || !token.nonce().equals(nonce) || token.poisoned() || expired(token.startupDeadline())
                || observedReadyNanos - (token.startupDeadline() - 5_000_000_000L) < 0
                || System.nanoTime() - observedReadyNanos < 0) {
            throw new IOException("Worker READY rejected");
        }
        token.ready(observedReadyNanos);
        persist();
    }

    /** Consumes a warm generation after the coordinator consumes the exact CLEAN context permit.
     * @param token ready generation
     * @param requestNonce server-created operation UUID
     * @param admittedNanos monotonic operation admission instant
     * @throws IOException stale, replayed, cancelled or expired handoff
     */
    synchronized void assign(WorkerReservation token, String requestNonce, long admittedNanos) throws IOException {
        requireOnline();
        owned(token);
        long now = System.nanoTime();
        if (token.phase() != WorkerReservation.Phase.READY || token.poisoned() || expired(token.idleDeadline())
                || now - admittedNanos < 0 || now - admittedNanos >= 10_000_000_000L || !canonicalUuid(requestNonce)) {
            throw new IOException("Worker handoff rejected");
        }
        for (WorkerReservation peer : slots) {
            if (peer != null && peer != token && peer.active()) throw new IOException("Worker active capacity reached");
        }
        token.assign(requestNonce, admittedNanos);
        persist();
    }

    /** Records only staging state, leaving response bytes in the private owned lease.
     * @param token exact assigned generation
     * @throws IOException invalid or cancelled stage
     */
    synchronized void stage(WorkerReservation token) throws IOException {
        owned(token);
        if (token.phase() != WorkerReservation.Phase.ASSIGNED || token.poisoned()) throw new IOException("Worker stage rejected");
        token.stage();
        persist();
    }

    /** Makes cancellation sticky even after cleanup and before publication.
     * @param token exact still-reserved generation
     * @throws IOException stale identity or failed durable cancellation
     */
    synchronized void cancel(WorkerReservation token) throws IOException {
        owned(token);
        token.poison();
        persist();
    }

    /** Cleans an owned tree; expiry suppresses progress without inferring process absence.
     * @param token exact generation
     * @param deadlineNanos bounded cleanup waiting deadline
     * @param transport owner that closes and joins all private stream tasks
     * @throws IOException incomplete owned cleanup
     * @throws InterruptedException caller interruption; reservation is retained
     */
    synchronized void cleanup(WorkerReservation token, long deadlineNanos, AutoCloseable transport)
            throws IOException, InterruptedException {
        owned(token);
        if (token.phase() == WorkerReservation.Phase.CLEAN) return;
        if (token.phase() != WorkerReservation.Phase.STAGED) token.poison();
        try { persist(); } catch (IOException failure) { uncertain(token); }
        boolean unresolved = token.phase() == WorkerReservation.Phase.UNKNOWN;
        try {
            physicalCleanup(token, deadlineNanos, transport);
            token.group().captureTerminal();
            if (unresolved) throw new IOException("Worker cleanup remains unknown");
            token.group().remove();
            token.group().close();
            token.clean();
            persist();
        } catch (InterruptedException failure) { uncertain(token); throw failure; }
        catch (Exception failure) { uncertain(token); throw new IOException("Worker cleanup unconfirmed", failure); }
    }

    /** Attempts physical cleanup even after journal uncertainty, always closing transport tasks.
     * @param token retained generation, including UNKNOWN
     * @param deadline monotonic bounded wait deadline
     * @param transport sole task and stream owner
     * @throws IOException incomplete physical cleanup
     * @throws InterruptedException interrupted owned wait
     */
    private void physicalCleanup(WorkerReservation token, long deadline, AutoCloseable transport)
            throws IOException, InterruptedException {
        Exception failure = null;
        try { retireAndReap(token, deadline); }
        catch (Exception error) { failure = error; }
        try { transport.close(); }
        catch (Exception error) {
            if (failure == null) failure = error;
            else failure.addSuppressed(error);
        }
        if (failure instanceof InterruptedException interrupted) throw interrupted;
        if (failure != null) throw new IOException("Worker physical cleanup incomplete", failure);
    }

    /** Attempts both descriptor kill and direct-child reap even if one observation fails.
     * @param token generation being retired
     * @param deadline monotonic cleanup deadline
     * @throws IOException missing attachment or unresolved group
     * @throws InterruptedException interrupted owned wait
     */
    private void retireAndReap(WorkerReservation token, long deadline) throws IOException, InterruptedException {
        IOException failure = null;
        try { token.group().kill(); }
        catch (IOException error) { failure = error; }
        try { reapChild(token, deadline); }
        catch (IOException error) {
            if (failure == null) failure = error;
            else failure.addSuppressed(error);
        }
        while (!token.group().empty()) {
            if (expired(deadline)) throw new IOException("Worker group empty unconfirmed");
            TimeUnit.NANOSECONDS.sleep(Math.min(1_000_000L, Math.max(1, deadline - System.nanoTime())));
        }
        if (failure != null) throw failure;
    }

    /** Reaps the retained Process object; never reconstructs destructive authority from a PID.
     * @param token generation retaining its original direct child
     * @param deadline monotonic waiting deadline
     * @throws IOException missing attachment or unconfirmed reap
     * @throws InterruptedException interrupted owned wait
     */
    private void reapChild(WorkerReservation token, long deadline) throws IOException, InterruptedException {
        Process child = token.child();
        if (token.attempted() && child == null) throw new IOException("Worker spawn remains uncertain");
        if (child == null) return;
        child.destroyForcibly();
        long remaining = Math.max(0, deadline - System.nanoTime());
        if (!child.waitFor(remaining, TimeUnit.NANOSECONDS)) throw new IOException("Worker reap unconfirmed");
        child.getOutputStream().close();
        child.getInputStream().close();
        child.getErrorStream().close();
    }

    /** Linearizes publication under this monitor after the caller's same-lock full final scan.
     * @param token cleaned staged result
     * @param requestNonce exact current operation
     * @param currentImage freshly scanned full installed image, never a cached earlier boolean
     * @param nowNanos current monotonic instant after the final scan
     * @throws IOException stale, expired, cancelled or changed publication
     */
    synchronized void publish(WorkerReservation token, String requestNonce, String currentImage, long nowNanos) throws IOException {
        requireOnline();
        owned(token);
        if (!build.equals(currentImage)) { disable(); throw new IOException("Worker image changed"); }
        if (!token.publishable(requestNonce, nowNanos)) throw new IOException("Worker publication rejected");
        token.publish();
        persist();
    }

    /** Removes one resolved slot only after all exact cleanup obligations were recorded.
     * @param token cleaned and resolved generation
     * @throws IOException stale, unresolved or failed durable release
     */
    synchronized void release(WorkerReservation token) throws IOException {
        owned(token);
        if (!token.releasable()) throw new IOException("Worker release rejected");
        slots[token.slot()] = null;
        try { persist(); token.release(); }
        catch (IOException failure) { slots[token.slot()] = token; uncertain(token); throw failure; }
    }

    /** Disables the incarnation and poisons every outstanding generation after an observed mismatch.
     * @throws IOException failed durable retirement; in-memory authority remains disabled
     */
    synchronized void disable() throws IOException {
        online = false;
        for (WorkerReservation token : slots) if (token != null) token.poison();
        persist();
    }

    /** Retains uncertain ownership and disables every future admission.
     * @param token uncertain generation
     */
    private void uncertain(WorkerReservation token) {
        online = false;
        token.unknown();
        try { persist(); } catch (IOException ignored) { /* Durable earlier reservation still blocks restart. */ }
    }

    /** Requires the exact object capability still owned in its generation slot.
     * @param token presented capability
     * @throws IOException stale or foreign capability
     */
    private void owned(WorkerReservation token) throws IOException {
        if (closed || token == null || token.slot() < 0 || token.slot() >= 2 || slots[token.slot()] != token) {
            throw new IOException("Worker ownership rejected");
        }
    }
    /** Rejects offline incarnations without falling back to uncontained fresh launches.
     * @throws IOException disabled or closed pool
     */
    private void requireOnline() throws IOException { if (!online || closed) throw new IOException("Worker pool unavailable"); }
    /** Tests monotonic expiry without relying on wall-clock time.
     * @param deadline absolute monotonic nanoseconds
     * @return whether expiry has occurred
     */
    private static boolean expired(long deadline) { return System.nanoTime() - deadline >= 0; }
    /** Requires a canonical server-created operation nonce.
     * @param value candidate UUID
     * @return whether the canonical lower-case spelling is accepted
     */
    private static boolean canonicalUuid(String value) {
        return value != null && value.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");
    }

    /** Persists the full metadata-only ledger, disabling authority on any durability failure.
     * @throws IOException failed forced record
     */
    private void persist() throws IOException {
        ObjectNode state = JsonNodeFactory.instance.objectNode().put("schema", 1).put("poolNonce", poolNonce)
                .put("ownerPid", ownerPid).put("ownerStartTicks", ownerStart).put("bootId", bootId)
                .put("build", build).put("policy", policy).put("cgroupRoot", cgroupRoot.toString());
        var counts = state.putArray("generations");
        var records = state.putArray("slots");
        for (int index = 0; index < slots.length; index++) {
            counts.add(generations[index]);
            if (slots[index] == null) records.addNull();
            else slots[index].write(records.addObject());
        }
        try { journal.write(state); }
        catch (IOException failure) { online = false; throw failure; }
    }

    /** Returns the immutable public bootstrap owner PID.
     * @return current server PID
     */
    long ownerPid() { return ownerPid; }
    /** Returns the immutable owner start ticks.
     * @return decimal kernel incarnation
     */
    String ownerStartTicks() { return ownerStart; }
    /** Returns the current boot identity.
     * @return canonical UUID
     */
    String bootId() { return bootId; }
    /** Returns the random pool incarnation.
     * @return canonical UUID
     */
    String poolNonce() { return poolNonce; }
    /** Returns the pinned delegated root.
     * @return canonical cgroup path
     */
    Path cgroupRoot() { return cgroupRoot; }
    /** Returns the pinned root device.
     * @return kernel device number
     */
    long rootDevice() { return rootDevice; }
    /** Returns the pinned root inode.
     * @return kernel inode number
     */
    long rootInode() { return rootInode; }
    /** Reports whether admission remains available.
     * @return false after any observed uncertainty or shutdown
     */
    synchronized boolean online() { return online && !closed; }
    /** Returns a bounded copy for coordinator shutdown, never mutable slot storage.
     * @return zero to two outstanding capabilities
     */
    synchronized WorkerReservation[] reservations() {
        return java.util.Arrays.stream(slots).filter(java.util.Objects::nonNull).toArray(WorkerReservation[]::new);
    }

    /** Stops admission without relinquishing durable ownership while any tree remains unresolved.
     * @throws IOException outstanding reservations or failed lock close
     */
    @Override
    public synchronized void close() throws IOException {
        if (closed) return;
        disable();
        for (WorkerReservation token : slots) if (token != null) throw new IOException("Worker cleanup required before close");
        journal.close();
        closed = true;
    }
}
