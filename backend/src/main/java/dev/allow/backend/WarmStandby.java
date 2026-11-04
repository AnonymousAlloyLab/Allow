package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicReference;

/** One contained process generation, including startup, idle, request and terminal ownership. */
final class WarmStandby implements Runnable, WarmTransport.FailureSink {
    private final WarmWorkerPool pool;
    private final WorkerPoolLedger ledger;
    private final WarmImageLauncher launcher;
    private final WorkerReservation token;
    private final String build;
    private final AtomicReference<IOException> problem = new AtomicReference<>();
    private final CompletableFuture<WarmStandby> readiness = new CompletableFuture<>();
    private volatile Process child;
    private volatile WarmTransport transport;
    private volatile WarmDeadline requestDeadline;
    private volatile Thread requestThread;
    private volatile String operation = "";
    private volatile boolean cleanupAttempted;

    /** Retains one already durable reservation; no private model is stored here.
     * @param pool bounded coordinator
     * @param ledger exclusive generation owner
     * @param launcher pinned public bootstrap launcher
     * @param token already reserved group
     * @param build expected complete executable identity
     */
    WarmStandby(WarmWorkerPool pool, WorkerPoolLedger ledger, WarmImageLauncher launcher,
            WorkerReservation token, String build) {
        this.pool = pool;
        this.ledger = ledger;
        this.launcher = launcher;
        this.token = token;
        this.build = build;
    }

    /** Starts one helper and records readiness within the original reservation deadline. */
    @Override
    public void run() {
        try {
            launch();
            WarmDeadline startup = WarmDeadline.fromStart(token.startupDeadline() - 5_000_000_000L, 5000);
            transport.awaitReady(startup);
            finishStartup();
        } catch (Exception failure) {
            failed(new IOException("Warm worker startup unavailable", failure));
            readiness.completeExceptionally(problem.get());
            retireQuietly();
        }
    }

    /** Persists the direct child before releasing only public bootstrap bytes.
     * @throws IOException unavailable reservation, process or bootstrap
     */
    private synchronized void launch() throws IOException {
        check();
        ledger.markSpawnAttempt(token);
        child = launcher.spawn(ledger, WarmWorkerMode.WARM_DOCUMENT);
        ledger.attach(token, child);
        transport = new WarmTransport(child, token.nonce(), build, this);
        launcher.releaseBootstrap(ledger, token);
    }

    /** Advertises READY only if retirement did not win while the reader was waiting.
     * @throws IOException cancelled or expired startup
     */
    private synchronized void finishStartup() throws IOException {
        check();
        ledger.markReady(token, token.nonce(), build, transport.readyNanos());
        readiness.complete(this);
    }

    /** Awaits the same startup shared by the single pending standby reference.
     * @param deadline original request admission deadline
     * @return this ready generation
     * @throws IOException failed or expired startup
     * @throws InterruptedException caller cancellation
     */
    WarmStandby awaitReady(WarmDeadline deadline) throws IOException, InterruptedException {
        try {
            WarmStandby result = readiness.get(deadline.remainingMillis(), TimeUnit.MILLISECONDS);
            deadline.check();
            check();
            return result;
        } catch (ExecutionException | TimeoutException failure) {
            throw new IOException("Warm worker unavailable", failure);
        }
    }

    /** Consumes the checked context once under the generation and ledger locks.
     * @param binding current admitted operation
     * @param permit exact fresh CLEAN-backed context authority
     * @param deadline original request deadline
     * @return consumed context for immediate one-frame encoding
     * @throws IOException stale or failed handoff
     * @throws InterruptedException caller cancellation
     */
    synchronized DocumentValidationContext assign(WarmRequestBinding binding, WarmContextPermit permit,
            WarmDeadline deadline) throws IOException, InterruptedException {
        check();
        deadline.check();
        if (phase() != WorkerReservation.Phase.READY || !operation.isEmpty()) {
            throw new IOException("Warm worker already consumed");
        }
        synchronized (ledger) {
            pool.verifyImage();
            deadline.check();
            DocumentValidationContext context = permit.consume(binding);
            operation = binding.nonce();
            requestDeadline = deadline;
            requestThread = Thread.currentThread();
            ledger.assign(token, binding.nonce(), deadline.startedNanos());
            return context;
        }
    }

    /** Exchanges one already bounded frame without holding the cleanup monitor.
     * @param input serialized existing private protocol
     * @param deadline original admission deadline
     * @return complete private response bytes
     * @throws IOException failed one-use exchange
     * @throws InterruptedException caller cancellation
     */
    byte[] exchange(byte[] input, WarmDeadline deadline) throws IOException, InterruptedException {
        check();
        WarmTransport owner = transport;
        if (owner == null) throw new IOException("Warm transport unavailable");
        byte[] bytes = owner.exchange(input, deadline);
        check();
        return bytes;
    }

    /** Stages only metadata, then proves physical cleanup before yielding a private result lease.
     * @param deadline original success deadline
     * @throws IOException failed, cancelled or incomplete cleanup
     * @throws InterruptedException caller cancellation
     */
    synchronized void stageAndClean(WarmDeadline deadline) throws IOException, InterruptedException {
        check();
        deadline.check();
        ledger.stage(token);
        cleanupAttempted = true;
        ledger.cleanup(token, deadline.expiresNanos(), this::closeTransport);
        check();
        deadline.check();
    }

    /** Performs the fresh final fence and publication under the exact same owner monitor.
     * @param binding current result owner
     * @param deadline original success deadline
     * @throws IOException cancelled, stale, expired or changed publication
     * @throws InterruptedException caller cancellation
     */
    synchronized void publish(WarmRequestBinding binding, WarmDeadline deadline) throws IOException, InterruptedException {
        check();
        if (!operation.equals(binding.nonce())) throw new IOException("Warm result ownership mismatch");
        try {
            synchronized (ledger) {
                String image = pool.verifyImage();
                deadline.check();
                check();
                ledger.publish(token, binding.nonce(), image, System.nanoTime());
                ledger.release(token);
                deadline.check();
                IOException failure = problem.get();
                if (failure != null) throw failure;
            }
        } finally {
            if (phase() == WorkerReservation.Phase.RELEASED) { detach(); pool.released(this); }
        }
    }

    /** Marks a reader failure without acquiring a lifecycle or ledger lock.
     * @param failure bounded infrastructure-only failure
     */
    @Override
    public void failed(IOException failure) {
        problem.compareAndSet(null, failure);
    }

    /** Reports whether the watcher should attempt retirement once.
     * @param now current monotonic clock
     * @return whether an owned, not-yet-cleaned generation expired or failed
     */
    boolean needsRetirement(long now) {
        synchronized (ledger) {
            WorkerReservation.Phase phase = token.phase();
            if (phase == WorkerReservation.Phase.RELEASED) return false;
            if (cleanupAttempted && phase == WorkerReservation.Phase.UNKNOWN) return false;
            if (problem.get() != null || token.poisoned()) return true;
            if (requestThread != null && requestThread.isInterrupted()) return true;
            if (requestDeadline != null) return now - requestDeadline.expiresNanos() >= 0;
            if (phase == WorkerReservation.Phase.READY) return now - token.idleDeadline() >= 0;
            return !cleanupAttempted && now - token.startupDeadline() >= 0;
        }
    }

    /** Cancels a selected pending generation unless a different operation already consumed it.
     * @param nonce caller's admitted operation nonce
     */
    synchronized void abortRequest(String nonce) {
        if (!operation.isEmpty() && !operation.equals(nonce)) return;
        failed(new IOException("Warm operation cancelled"));
        retireQuietly();
    }

    /** Cancels only the operation that actually consumed this generation.
     * @param nonce caller's admitted operation nonce
     */
    void abortOperation(String nonce) {
        if (!operation.equals(nonce)) return;
        failed(new IOException("Warm operation cancelled"));
        retireQuietly();
    }

    /** Attempts bounded cancellation cleanup once, retaining uncertainty and exact ownership.
     * @throws IOException incomplete cancellation or cleanup
     * @throws InterruptedException caller interruption during owned cleanup
     */
    synchronized void retire() throws IOException, InterruptedException {
        if (phase() == WorkerReservation.Phase.RELEASED) { detach(); pool.released(this); return; }
        failed(new IOException("Warm generation retired"));
        readiness.completeExceptionally(problem.get());
        IOException cancellation = null;
        try { ledger.cancel(token); } catch (IOException failure) { cancellation = failure; }
        if (!cleanupAttempted) {
            cleanupAttempted = true;
            ledger.cleanup(token, System.nanoTime() + 2_000_000_000L, this::closeTransport);
        }
        if (phase() == WorkerReservation.Phase.CLEAN) {
            ledger.release(token);
            detach();
            pool.released(this);
        }
        if (cancellation != null) throw cancellation;
        if (phase() != WorkerReservation.Phase.RELEASED) throw new IOException("Warm cleanup remains uncertain");
    }

    /** Contains watcher/startup failures without freeing an unresolved reservation. */
    void retireQuietly() {
        try { retire(); }
        catch (InterruptedException failure) { Thread.currentThread().interrupt(); }
        catch (IOException failure) { problem.compareAndSet(null, failure); }
    }

    /** Closes all lifetime tasks even when attachment failed before readers existed.
     * @throws IOException retained direct child or stream failure
     * @throws InterruptedException interrupted owned reap
     */
    private void closeTransport() throws IOException, InterruptedException {
        Process owned = child;
        if (owned != null && owned.isAlive()) {
            owned.destroyForcibly();
            if (!owned.waitFor(2, TimeUnit.SECONDS)) throw new IOException("Warm direct child remains alive");
        }
        WarmTransport owner = transport;
        if (owner != null) owner.close();
        else if (owned != null) {
            owned.getOutputStream().close();
            owned.getInputStream().close();
            owned.getErrorStream().close();
        }
    }

    /** Rejects sticky failures or already released generations.
     * @throws IOException generation is no longer usable
     */
    private void check() throws IOException {
        IOException failure = problem.get();
        if (failure != null) throw failure;
        synchronized (ledger) {
            if (token.phase() == WorkerReservation.Phase.RELEASED || token.poisoned()) {
                throw new IOException("Warm generation unavailable");
            }
        }
    }

    /** Reads lifecycle state under the same monitor that owns every token transition.
     * @return exact currently observed phase
     */
    private WorkerReservation.Phase phase() { synchronized (ledger) { return token.phase(); } }

    /** Drops process, stream and thread references only after terminal release. */
    private void detach() {
        child = null;
        transport = null;
        requestThread = null;
        requestDeadline = null;
        operation = "";
    }
}
