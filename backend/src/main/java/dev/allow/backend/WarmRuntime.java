package dev.allow.backend;

import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Disabled-by-default installation owner; selection is a trusted compile-time policy. */
@Component
final class WarmRuntime {
    private static final boolean ENABLED = false;
    private static volatile WarmRuntime current;
    private final WorkerPoolLedger ledger;
    private final WarmImageLauncher launcher;
    private final WarmWorkerPool pool;
    private final DocumentRuntime documents;
    private final String build;
    private final Set<OwnedWorkerRun> fresh = new HashSet<>();
    private volatile boolean stopping;

    /** Creates authority only for a separately selected, correctly contained server start.
     * @param runtime already initialized document policy and workspace owner
     * @param directory trusted Allow installation root
     * @throws IOException missing containment, changed build or duplicate owner
     */
    WarmRuntime(DocumentRuntime runtime, @Value("${allow.corpus.root:}") String directory) throws IOException {
        documents = runtime;
        build = runtime.dependency();
        if (!ENABLED) { ledger = null; launcher = null; pool = null; return; }
        synchronized (WarmRuntime.class) {
            if (current != null) throw new IOException("Worker pool already initialized");
            runtime.requireReady();
            Path installation = Path.of(directory).toAbsolutePath().normalize();
            Path group = WarmConfiguration.read(installation);
            ledger = WorkerPoolLedger.open(installation.resolve(".runtime/warm-pool/journal"), group,
                    runtime.dependency(), runtime.policy());
            try {
                launcher = new WarmImageLauncher(installation, Path.of("target"), runtime.dependency());
                pool = new WarmWorkerPool(ledger, launcher, runtime.dependency(), runtime.policy());
                current = this;
            } catch (IOException | RuntimeException failure) {
                try { ledger.close(); } catch (IOException closure) { failure.addSuppressed(closure); }
                throw failure;
            }
        }
    }

    /** Returns the fixed trusted selection without accepting a request or environment override.
     * @return whether this compiled installation selected pooling
     */
    static boolean enabled() { return ENABLED; }

    /** Makes a fresh launcher's observed identity mismatch sticky for the existing pool.
     * @param observed complete newly scanned build identity
     * @throws IOException mismatch against the installed incarnation
     */
    static void observeBuild(String observed) throws IOException {
        WarmRuntime owner = current;
        if (owner != null && !owner.build.equals(observed)) {
            IOException failure = new IOException("Installed worker identity changed");
            observedBuildFailure(failure);
            throw failure;
        }
    }

    /** Retires existing standby authority after a fresh installed-build observation failed.
     * @param failure original observation failure, retaining any durability error as suppressed
     */
    static void observedBuildFailure(IOException failure) {
        WarmRuntime owner = current;
        if (owner != null) {
            try { owner.ledger.disable(); } catch (IOException error) { failure.addSuppressed(error); }
        }
    }

    /** Keeps the workspace lock when framework destruction continues after pool cleanup failed.
     * @param closing document incarnation attempting to relinquish its lock
     * @return whether no selected pool still depends on this workspace owner
     */
    static boolean permitsWorkspaceRelease(DocumentRuntime closing) {
        WarmRuntime owner = current;
        return owner == null || owner.documents != closing;
    }

    /** Requires the selected owner instead of silently falling back to fresh uncontained workers.
     * @return exclusive enabled owner
     * @throws IOException unavailable or disabled runtime
     */
    static WarmRuntime current() throws IOException {
        WarmRuntime owner = current;
        if (!ENABLED || owner == null || owner.stopping || !owner.ledger.online()) throw new IOException("Worker pool unavailable");
        return owner;
    }

    /** Returns the bounded advisory coordinator.
     * @return installed pool
     */
    WarmWorkerPool pool() { return pool; }

    /** Returns the shared live-tree owner used by fresh operations as well.
     * @return exclusive metadata and cleanup ledger
     */
    WorkerPoolLedger ledger() { return ledger; }

    /** Returns the pinned image launcher shared by every enabled worker mode.
     * @return fixed helper launcher
     */
    WarmImageLauncher launcher() { return launcher; }

    /** Rejects new fresh reservations after shutdown has begun.
     * @throws IOException stopped or uncertain incarnation
     */
    synchronized void requireAccepting() throws IOException {
        if (stopping || !ledger.online()) throw new IOException("Worker runtime is stopping");
    }

    /** Registers a fully initialized reservation under the same admission monitor.
     * @param owned fresh run whose fields have already been assigned
     */
    synchronized void registerFresh(OwnedWorkerRun owned) { fresh.add(owned); }

    /** Detaches a fresh runner only after its positive tree and transport cleanup receipt.
     * @param owned terminal clean run
     */
    synchronized void finishedFresh(OwnedWorkerRun owned) { fresh.remove(owned); }

    /** Retires every owned worker before the dependent document runtime releases its lock.
     * @throws IOException unresolved owned cleanup
     * @throws InterruptedException interrupted shutdown, retaining ownership
     */
    @PreDestroy
    void close() throws IOException, InterruptedException {
        if (pool == null) return;
        OwnedWorkerRun[] active;
        synchronized (this) { stopping = true; active = fresh.toArray(OwnedWorkerRun[]::new); }
        IOException failure = stopFresh(active);
        try { pool.close(); } catch (IOException error) { failure = combine(failure, error); }
        for (OwnedWorkerRun run : active) {
            try { run.awaitStopped(); } catch (IOException error) { failure = combine(failure, error); }
        }
        if (failure != null) throw failure;
        ledger.close();
        synchronized (WarmRuntime.class) { if (current == this) current = null; }
    }

    /** Stops admission and signals every exact fresh owner, retaining all failures.
     * @param active bounded snapshot of admitted fresh runs
     * @return aggregated failure, or null after successful stop requests
     */
    private IOException stopFresh(OwnedWorkerRun[] active) {
        IOException failure = null;
        try { ledger.disable(); } catch (IOException error) { failure = error; }
        for (OwnedWorkerRun run : active) {
            try { run.requestStop(); } catch (IOException error) { failure = combine(failure, error); }
        }
        return failure;
    }

    /** Preserves every cleanup failure without weakening the shutdown result.
     * @param prior earlier failure, or null
     * @param next additional cleanup failure
     * @return accumulated failure
     */
    private static IOException combine(IOException prior, IOException next) {
        if (prior == null) return next;
        prior.addSuppressed(next);
        return prior;
    }
}
