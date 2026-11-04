package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Lazy bounded coordinator; every standby serves at most one private advisory request. */
final class WarmWorkerPool implements AutoCloseable {
    private final WorkerPoolLedger ledger;
    private final WarmImageLauncher launcher;
    private final String build;
    private final String policy;
    private final Set<WarmStandby> live = ConcurrentHashMap.newKeySet();
    private final AtomicReference<WarmStandby> pending = new AtomicReference<>();
    private final ThreadPoolExecutor refill;
    private final ScheduledExecutorService watcher;
    private volatile boolean closed;

    /** Creates bounded coordination threads without eagerly starting a worker JVM.
     * @param ledger exclusive two-tree owner shared with fresh operations
     * @param launcher fixed pinned public bootstrap launcher
     * @param build full installed executable digest
     * @param policy installed validation policy
     */
    WarmWorkerPool(WorkerPoolLedger ledger, WarmImageLauncher launcher, String build, String policy) {
        this.ledger = java.util.Objects.requireNonNull(ledger);
        this.launcher = java.util.Objects.requireNonNull(launcher);
        this.build = java.util.Objects.requireNonNull(build);
        this.policy = java.util.Objects.requireNonNull(policy);
        refill = new ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS,
                new ArrayBlockingQueue<>(1), new PoolThreadFactory("allow-warm-refill"), new ThreadPoolExecutor.AbortPolicy());
        watcher = Executors.newSingleThreadScheduledExecutor(new PoolThreadFactory("allow-warm-deadlines"));
        watcher.scheduleWithFixedDelay(this::inspectDeadlines, 50, 50, TimeUnit.MILLISECONDS);
    }

    /** Returns this pool's immutable local incarnation for context binding.
     * @return canonical UUID
     */
    String poolNonce() { return ledger.poolNonce(); }

    /** Lazily starts at most one standby before the caller resolves its fresh context.
     * @throws IOException unavailable capacity, offline incarnation or failed scheduling
     */
    synchronized void begin() throws IOException {
        requireOnline();
        if (pending.get() != null) return;
        WorkerReservation token = ledger.reserveStandby();
        WarmStandby worker = new WarmStandby(this, ledger, launcher, token, build);
        live.add(worker);
        pending.set(worker);
        try { refill.execute(worker); }
        catch (RejectedExecutionException failure) {
            worker.failed(new IOException("Warm refill unavailable", failure));
            worker.retireQuietly();
            throw new IOException("Warm refill unavailable", failure);
        }
    }

    /** Validates one exact draft only after consuming its fresh context permit.
     * @param binding current server-created admission identity
     * @param candidate exact submitted candidate
     * @param permit one-use CLEAN-backed context permit
     * @param deadline original ten-second admission budget
     * @return cleaned staged result awaiting final public-envelope publication
     * @throws IOException failed, expired or unavailable one-use worker
     * @throws InterruptedException caller cancellation after owned cleanup attempts
     */
    WarmResultLease validate(WarmRequestBinding binding, JsonNode candidate, WarmContextPermit permit,
            WarmDeadline deadline) throws IOException, InterruptedException {
        checkBinding(binding);
        deadline.check();
        begin();
        WarmStandby worker = pending.get();
        if (worker == null) throw new IOException("Warm standby unavailable");
        boolean staged = false;
        try {
            worker.awaitReady(deadline);
            DocumentValidationContext context = worker.assign(binding, permit, deadline);
            consumed(worker);
            byte[] input = frame(binding, candidate, context);
            JsonNode result = response(worker.exchange(input, deadline), binding.nonce());
            worker.stageAndClean(deadline);
            staged = true;
            return new WarmResultLease(worker, binding, deadline, result);
        } catch (IllegalArgumentException failure) {
            throw new IOException("Malformed private warm worker envelope", failure);
        } finally { if (!staged) worker.abortRequest(binding.nonce()); }
    }

    /** Starts at most one replacement only after an actual generation consumption.
     * @param worker consumed generation
     */
    private void consumed(WarmStandby worker) {
        pending.compareAndSet(worker, null);
        try { begin(); }
        catch (IOException ignored) { /* The current operation still requires the online publication fence. */ }
    }

    /** Encodes the existing private protocol after CLEAN without retaining it in coordinator state.
     * @param binding exact operation identity
     * @param candidate submitted candidate
     * @param context freshly consumed authorized context
     * @return bounded private frame without its trailing delimiter
     * @throws IOException excessive frame size
     */
    private static byte[] frame(WarmRequestBinding binding, JsonNode candidate, DocumentValidationContext context)
            throws IOException {
        ObjectNode frame = JsonNodeFactory.instance.objectNode().put("protocol", 1).put("requestId", binding.nonce())
                .put("policyVersion", binding.policy()).put("operation", "VALIDATE");
        frame.set("candidate", candidate.deepCopy());
        frame.set("baseArtifact", context.artifact());
        frame.set("ownedIdInventory", context.inventory());
        byte[] bytes = JsonWire.encode(frame);
        if (bytes.length >= 2097152) throw new IOException("Internal validation context exceeds limit");
        return bytes;
    }

    /** Preserves every existing fresh document-worker response-envelope check.
     * @param bytes complete bounded private response
     * @param nonce exact admitted operation
     * @return checked private response
     * @throws IOException malformed encoding or mismatched response identity
     * @throws IllegalArgumentException malformed closed envelope
     */
    private static JsonNode response(byte[] bytes, String nonce) throws IOException {
        JsonNode result = DocumentJson.decode(bytes);
        DocumentJson.fields(result, "protocol", "requestId", "status", "data");
        if (!result.path("protocol").isInt() || result.path("protocol").intValue() != 1
                || !nonce.equals(result.path("requestId").asText())
                || !Set.of("VALIDATED", "INVALID", "UNAVAILABLE").contains(result.path("status").asText())) {
            throw new IOException("Document worker identity mismatch");
        }
        return result;
    }

    /** Rejects a permit from another policy, executable build or pool incarnation.
     * @param binding current internal admission identity
     * @throws IOException stale or substituted context authority
     */
    private void checkBinding(WarmRequestBinding binding) throws IOException {
        requireOnline();
        if (binding == null || !policy.equals(binding.policy()) || !build.equals(binding.build())
                || !poolNonce().equals(binding.poolNonce())) throw new IOException("Warm operation binding mismatch");
    }

    /** Recomputes full executable identity and permanently disables an observed mismatch.
     * @return exact currently scanned full build
     * @throws IOException any observed executable mismatch or disabled incarnation
     */
    String verifyImage() throws IOException {
        requireOnline();
        try { return launcher.verify(); }
        catch (IOException failure) {
            try { ledger.disable(); } catch (IOException disabled) { failure.addSuppressed(disabled); }
            throw failure;
        }
    }

    /** Removes terminal references without taking a pool lock from a worker cleanup monitor.
     * @param worker terminal released generation
     */
    void released(WarmStandby worker) {
        pending.compareAndSet(worker, null);
        live.remove(worker);
    }

    /** Retires expired or failed generations once; expiry alone never requests a refill. */
    private void inspectDeadlines() {
        long now = System.nanoTime();
        for (WarmStandby worker : live) {
            if (closed || worker.needsRetirement(now)) worker.retireQuietly();
        }
    }

    /** Requires a live contained incarnation, with no uncontained fallback.
     * @throws IOException shutdown or uncertain cleanup
     */
    private void requireOnline() throws IOException {
        if (closed || !ledger.online()) throw new IOException("Warm worker pool unavailable");
    }

    /** Stops scheduling without interrupting journal owners; the caller retains the shared ledger.
     * @throws IOException unresolved worker ownership or retained coordinator task
     * @throws InterruptedException shutdown interruption, with capacity retained
     */
    @Override
    public void close() throws IOException, InterruptedException {
        synchronized (this) { closed = true; }
        watcher.shutdown();
        refill.shutdown();
        for (WarmStandby worker : live) worker.retireQuietly();
        if (!refill.awaitTermination(2, TimeUnit.SECONDS) || !watcher.awaitTermination(2, TimeUnit.SECONDS)
                || !live.isEmpty()) throw new IOException("Warm pool shutdown remains incomplete");
    }

    /** Names bounded daemon coordinator threads without granting any alternate launch authority. */
    private static final class PoolThreadFactory implements ThreadFactory {
        private final String name;
        /** Stores a fixed diagnostic thread name.
         * @param name fixed coordinator role
         */
        private PoolThreadFactory(String name) { this.name = name; }
        /** Creates one coordinator thread.
         * @param task executor-owned task
         * @return named daemon thread
         */
        @Override
        public Thread newThread(Runnable task) {
            Thread thread = new Thread(task, name);
            thread.setDaemon(true);
            return thread;
        }
    }
}
