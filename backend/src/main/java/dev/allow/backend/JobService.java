package dev.allow.backend;

import dev.allow.dto.*;
import dev.allow.worker.Hashes;
import dev.allow.worker.SourcePolicy;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.stereotype.Service;

/** Bounded in-memory jobs; one executor thread owns worker admission until reaping. */
@Service
final class JobService {
    private final Map<String, JobRecord> jobs = new LinkedHashMap<>();
    private final Map<String, String> owners = new HashMap<>();
    private final Map<String, Long> deadlines = new HashMap<>();
    private final ThreadPoolExecutor executor;
    private final JobRunner runner;

    /**
     * Creates the production isolated runner with a ten-second deadline.
     * @throws IOException incomplete build
     */
    JobService() throws IOException {
        this(new ProcessRunner(new BubblewrapLauncher(Path.of("target")), 10000));
    }

    /**
     * Injects a trusted runner for tests.
     * @param runner lifecycle implementation
     */
    JobService(JobRunner runner) {
        this.runner = runner;
        executor = new ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(4));
    }

    /**
     * Validates and queues an immutable candidate.
     * @param input browser candidate
     * @return exact identity
     * @throws RejectedExecutionException queue full
     * @throws IllegalArgumentException invalid source or identity
     */
    synchronized JobView submit(JobRequest input) { return submit(input, ""); }

    /** Queues a candidate under a registered immutable owner.
     * @param input bounded browser candidate
     * @param owner trusted scope or private sentinel
     * @return exact identity
     * @throws RejectedExecutionException expired owner or bounded capacity exhausted
     * @throws IllegalArgumentException invalid operation or identity
     */
    synchronized JobView submit(JobRequest input, String owner) {
        if (!authorized(owner)) throw new RejectedExecutionException("Workspace expired");
        if (!owner.isEmpty() && ownerBusy(owner)) throw new RejectedExecutionException("Workspace busy");
        SourcePolicy.check(input.source());
        if (input.revision() < 0 || input.epoch() < 0 || input.commandIndex() < 0
                || !("ANALYZE".equals(input.operation()) || "VALIDATE".equals(input.operation()))) {
            throw new IllegalArgumentException("Invalid operation or identity.");
        }
        if (!owner.isEmpty()) evictOwner(owner);
        evict();
        String id = UUID.randomUUID().toString();
        String hash = Hashes.text(input.source());
        String key = Hashes.text(hash + ":" + input.commandIndex() + ":" + input.revision()
                + ":" + input.epoch() + ":" + input.operation() + ":alloy6.2.0-sat4j2.3.1-noOverflow-v1:" + runner.identity());
        WorkerRequest request = new WorkerRequest(1, id, input.source(), hash, key,
                input.commandIndex(), input.revision(), input.epoch(), input.operation());
        JobRecord job = new JobRecord(request);
        executor.execute(new JobTask(this, job, runner, owner));
        jobs.put(id, job);
        owners.put(id, owner);
        return job.view();
    }

    /**
     * Evicts oldest terminal entries while preserving active jobs. *
     * @throws RejectedExecutionException retention capacity exhausted
     */
    private void evict() {
        if (jobs.size() < 128) return;
        Iterator<Map.Entry<String, JobRecord>> iterator = jobs.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<String, JobRecord> entry = iterator.next();
            if (entry.getValue().cleanupSafe()) {
                owners.remove(entry.getKey());
                iterator.remove();
                return;
            }
        }
        throw new RejectedExecutionException("Job retention limit");
    }

    /**
     * Gets an authorized immutable snapshot.
     * @param id opaque job id
     * @return view or null
     */
    synchronized JobView get(String id) {
        return get(id, "");
    }

    /**
     * Cancels an owned job idempotently.
     * @param id opaque job id
     * @return view or null
     */
    synchronized JobView cancel(String id) {
        return cancel(id, "");
    }

    /** Cancels/reaps jobs when Spring stops; no permit can leak into another launch. */
    @PreDestroy
    synchronized void close() {
        for (JobRecord record : jobs.values()) record.cancel();
        executor.shutdownNow();
    }

    /** Registers a fresh owner before any public submission.
     * @param owner fresh server-allocated owner
     * @param expiresAtNanos absolute monotonic deadline
     * @throws IllegalArgumentException empty, reused or expired owner
     */
    synchronized void registerOwner(String owner, long expiresAtNanos) {
        if (owner == null || owner.isEmpty() || deadlines.containsKey(owner)) {
            throw new IllegalArgumentException("Invalid or reused owner");
        }
        if (expiresAtNanos - System.nanoTime() <= 0) throw new IllegalArgumentException("Expired owner");
        deadlines.put(owner, expiresAtNanos);
    }

    /** Tests a registered owner without deriving authority from an identifier.
     * @param owner immutable scope or private sentinel
     * @return whether publication remains permitted
     */
    private boolean authorized(String owner) {
        if (owner == null) return false;
        if (owner.isEmpty()) return true;
        Long deadline = deadlines.get(owner);
        return deadline != null && deadline - System.nanoTime() > 0;
    }

    /** Reads only an exact owner's unexpired job.
     * @param id opaque job identity
     * @param owner trusted owner
     * @return owned view or null
     */
    synchronized JobView get(String id, String owner) {
        if (!authorized(owner) || !owner.equals(owners.get(id))) return null;
        JobRecord record = jobs.get(id);
        return record == null ? null : record.view();
    }

    /** Cancels only an exact owner's unexpired job.
     * @param id opaque job identity
     * @param owner trusted owner
     * @return owned view or null
     */
    synchronized JobView cancel(String id, String owner) {
        if (!authorized(owner) || !owner.equals(owners.get(id))) return null;
        JobRecord record = jobs.get(id);
        return record == null ? null : record.cancel();
    }

    /** Retains ownership until every runner proves actual cleanup.
     * @param owner immutable workspace owner
     * @return whether any task remains unresolved
     */
    synchronized boolean ownerBusy(String owner) {
        for (Map.Entry<String, JobRecord> entry : jobs.entrySet()) {
            if (owner.equals(owners.get(entry.getKey())) && !entry.getValue().cleanupSafe()) return true;
        }
        return false;
    }

    /** Reports the cleanup fence separately from displayed cancellation.
     * @param owner immutable workspace owner
     * @return whether every owned task is clean
     */
    synchronized boolean ownerQuiescent(String owner) { return !ownerBusy(owner); }

    /** Revokes execution for all jobs without claiming physical reaping.
     * @param owner immutable workspace owner
     * @throws IllegalArgumentException private or absent owner
     */
    synchronized void cancelOwner(String owner) {
        if (owner == null || owner.isEmpty()) throw new IllegalArgumentException("Public owner required");
        if (deadlines.containsKey(owner)) deadlines.put(owner, System.nanoTime());
        for (Map.Entry<String, JobRecord> entry : jobs.entrySet()) {
            if (owner.equals(owners.get(entry.getKey()))) entry.getValue().cancel();
        }
    }

    /** Releases only a completely drained owner's retained state.
     * @param owner immutable workspace owner
     * @return whether all owned state was safely removed
     */
    synchronized boolean forgetOwner(String owner) {
        if (owner == null || owner.isEmpty() || ownerBusy(owner)) return false;
        Iterator<Map.Entry<String, JobRecord>> iterator = jobs.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<String, JobRecord> entry = iterator.next();
            if (owner.equals(owners.get(entry.getKey()))) {
                owners.remove(entry.getKey());
                iterator.remove();
            }
        }
        deadlines.remove(owner);
        return true;
    }

    /** Makes space within the fixed per-workspace retained-job budget.
     * @param owner immutable workspace owner
     * @throws RejectedExecutionException no safely reclaimable result
     */
    private void evictOwner(String owner) {
        int count = 0;
        String oldest = null;
        for (Map.Entry<String, JobRecord> entry : jobs.entrySet()) {
            if (!owner.equals(owners.get(entry.getKey()))) continue;
            count++;
            if (oldest == null && entry.getValue().cleanupSafe()) oldest = entry.getKey();
        }
        if (count < 8) return;
        if (oldest == null) throw new RejectedExecutionException("Workspace retention limit");
        jobs.remove(oldest);
        owners.remove(oldest);
    }

    /** Rejects expired queued work at its actual execution transition.
     * @param job exact queued record
     * @param owner immutable owner
     * @return whether running was admitted
     */
    private synchronized boolean start(JobRecord job, String owner) {
        if (!authorized(owner)) job.cancel();
        return job.start();
    }

    /** Runnable keeps display cancellation separate from actual runner cleanup. */
    private record JobTask(JobService service, JobRecord job, JobRunner runner, String owner) implements Runnable {
        /** Executes until the runner's cleanup path has completed. */
        @Override
        public void run() {
            try {
                if (!service.start(job, owner)) return;
                job.finish(runner.execute(job.request(), job.control()));
            } catch (Exception error) {
                job.finish(ProcessRunner.outcome(job.request(), "ERROR", "Isolated worker unavailable or failed."));
            } finally {
                job.executionFinished();
            }
        }
    }
}
