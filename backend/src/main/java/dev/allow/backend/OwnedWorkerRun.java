package dev.allow.backend;

import java.io.IOException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/** Keeps fresh worker ownership visible even when startup fails before returning a process. */
final class OwnedWorkerRun implements AutoCloseable {
    private final SandboxLauncher original;
    private final WarmRuntime runtime;
    private final WorkerReservation reservation;
    private volatile Process child;
    private volatile boolean stopping;
    private final CompletableFuture<Void> completion = new CompletableFuture<>();
    private boolean transportStarted;
    private boolean transportClosed;
    private boolean clean;

    /** Reserves shared live capacity only in the selected pooled installation.
     * @param original existing trusted fresh launcher
     * @throws IOException unavailable selected runtime or capacity
     */
    OwnedWorkerRun(SandboxLauncher original) throws IOException {
        this.original = original;
        runtime = WarmRuntime.enabled() ? WarmRuntime.current() : null;
        if (runtime == null) reservation = null;
        else {
            synchronized (runtime) {
                runtime.requireAccepting();
                reservation = runtime.ledger().reserveFresh();
                runtime.registerFresh(this);
            }
        }
    }

    /** Starts the unchanged entrypoint inside an enabled generation's owned containment.
     * @return directly owned helper/bubblewrap process
     * @throws IOException launch or bootstrap failure
     * @throws InterruptedException cancelled startup
     */
    Process launch() throws IOException, InterruptedException {
        if (child != null) throw new IOException("Fresh worker launch already attempted");
        if (runtime == null) { child = original.launch(); return child; }
        requireRunning();
        if (!(original instanceof BubblewrapLauncher installed)) throw new IOException("Unsupported selected launcher");
        String current = runtime.pool().verifyImage();
        if (!current.equals(original.identity())) {
            runtime.ledger().disable();
            throw new IOException("Fresh worker build changed");
        }
        WarmWorkerMode mode = installed.freshMode();
        runtime.ledger().markSpawnAttempt(reservation);
        child = runtime.launcher().spawn(runtime.ledger(), mode);
        runtime.ledger().attach(reservation, child);
        requireRunning();
        runtime.launcher().releaseBootstrap(runtime.ledger(), reservation);
        runtime.launcher().awaitFreshSandbox(reservation);
        requireRunning();
        return child;
    }

    /** Exchanges one existing document frame and records actual transport task termination.
     * @param input exact existing private frame
     * @param maximum unchanged output cap
     * @param millis unchanged fresh exchange deadline
     * @return complete existing worker response
     * @throws IOException frame, process or deadline failure
     * @throws InterruptedException cancelled exchange
     */
    byte[] exchange(byte[] input, int maximum, long millis) throws IOException, InterruptedException {
        if (runtime == null) return FrameProcess.exchange(child, input, maximum, millis);
        beginTransport();
        return FrameProcess.exchange(child, input, maximum, millis, this::transportFinished);
    }

    /** Records that independently supervised solver stream tasks have been started.
     * @throws IOException shutdown won before transport admission
     */
    void beginTransport() throws IOException { requireRunning(); transportStarted = true; }

    /** Records positive task termination after all owned streams were closed. */
    void transportFinished() { transportClosed = true; }

    /** Returns the retained child even when attach or bootstrap threw.
     * @return actual owned process, or null before a successful spawn
     */
    Process child() { return child; }

    /** Returns identity retained before bootstrap, even when startup subsequently failed.
     * @return kernel start ticks, or null when no such observation was established
     */
    String observedStartTicks() {
        if (reservation == null || reservation.childStartTicks().isEmpty()) return null;
        return reservation.childStartTicks();
    }

    /** Distinguishes an unkeyed managed launch attempt from proved absence of any attempt.
     * @return whether no-worker-started recovery would invent an absence claim
     */
    boolean startupUncertain() { return reservation != null && reservation.attempted() && child == null; }

    /** Reports whether this installation requires the shared live-tree cleanup adapter.
     * @return whether pooling selected managed fresh containment
     */
    boolean managed() { return runtime != null; }

    /** Reports positive cleanup only after the complete owned close returned successfully.
     * @return whether process-tree and transport ownership have been discharged
     */
    boolean clean() { return clean; }

    /** Refuses a cleanup receipt when a managed transport failed to establish task termination.
     * @throws IOException incomplete stream task ownership
     */
    private void requireTransportClosed() throws IOException {
        if (transportStarted && !transportClosed) throw new IOException("Fresh worker transport remains uncertain");
    }

    /** Reaps and releases only after exact group emptiness and transport completion.
     * @throws IOException unresolved process-tree or stream ownership
     * @throws InterruptedException interrupted cleanup, retaining the reservation
     */
    @Override
    public synchronized void close() throws IOException, InterruptedException {
        if (clean) return;
        try {
            closeOwned();
            completion.complete(null);
            if (runtime != null) runtime.finishedFresh(this);
        } catch (IOException | InterruptedException failure) {
            completion.completeExceptionally(failure);
            throw failure;
        }
        requireRunning();
    }

    /** Establishes exact physical cleanup before completing the shared shutdown receipt.
     * @throws IOException incomplete group or transport ownership
     * @throws InterruptedException interrupted owned cleanup
     */
    private void closeOwned() throws IOException, InterruptedException {
        if (runtime == null) {
            if (child != null) FrameProcess.reap(child);
            clean = child == null || !child.isAlive();
            return;
        }
        runtime.ledger().cleanup(reservation, System.nanoTime() + 2_500_000_000L, this::requireTransportClosed);
        runtime.ledger().release(reservation);
        clean = true;
    }

    /** Makes shutdown sticky and stops exact owned processes without releasing their reservation.
     * @throws IOException cancellation or kernel control failed
     */
    void requestStop() throws IOException {
        stopping = true;
        if (runtime == null) return;
        synchronized (runtime.ledger()) {
            if (reservation.phase() == WorkerReservation.Phase.RELEASED) return;
            IOException failure = null;
            try { runtime.ledger().cancel(reservation); } catch (IOException error) { failure = error; }
            try { reservation.group().kill(); }
            catch (IOException error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
            Process owned = child;
            if (owned != null && owned.isAlive()) owned.destroyForcibly();
            if (failure != null) throw failure;
        }
    }

    /** Awaits the original owning runner's cleanup instead of stealing its stream-task authority.
     * @throws IOException failed or unresolved cleanup
     * @throws InterruptedException interrupted shutdown
     */
    void awaitStopped() throws IOException, InterruptedException {
        try { completion.get(5, TimeUnit.SECONDS); }
        catch (ExecutionException | TimeoutException failure) { throw new IOException("Fresh cleanup remains unresolved", failure); }
    }

    /** Rejects successful work after shutdown has linearized for this owned run.
     * @throws IOException stopped run
     */
    private void requireRunning() throws IOException {
        if (stopping) throw new IOException("Fresh worker stopped");
    }
}
