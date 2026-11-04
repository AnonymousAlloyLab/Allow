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
    synchronized JobView submit(JobRequest input) {
        SourcePolicy.check(input.source());
        if (input.revision() < 0 || input.epoch() < 0 || input.commandIndex() < 0
                || !("ANALYZE".equals(input.operation()) || "VALIDATE".equals(input.operation()))) {
            throw new IllegalArgumentException("Invalid operation or identity.");
        }
        evict();
        String id = UUID.randomUUID().toString();
        String hash = Hashes.text(input.source());
        String key = Hashes.text(hash + ":" + input.commandIndex() + ":" + input.revision()
                + ":" + input.epoch() + ":" + input.operation() + ":alloy6.2.0-sat4j2.3.1-noOverflow-v1:" + runner.identity());
        WorkerRequest request = new WorkerRequest(1, id, input.source(), hash, key,
                input.commandIndex(), input.revision(), input.epoch(), input.operation());
        JobRecord job = new JobRecord(request);
        executor.execute(new JobTask(job, runner));
        jobs.put(id, job);
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
            if (iterator.next().getValue().terminal()) {
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
        JobRecord record = jobs.get(id);
        return record == null ? null : record.view();
    }

    /**
     * Cancels an owned job idempotently.
     * @param id opaque job id
     * @return view or null
     */
    synchronized JobView cancel(String id) {
        JobRecord record = jobs.get(id);
        return record == null ? null : record.cancel();
    }

    /** Cancels/reaps jobs when Spring stops; no permit can leak into another launch. */
    @PreDestroy
    synchronized void close() {
        for (JobRecord record : jobs.values()) record.cancel();
        executor.shutdownNow();
    }

    /** Runnable avoids undocumented inline callbacks and preserves absorbing state. */
    private record JobTask(JobRecord job, JobRunner runner) implements Runnable {
        /** Executes until the runner has reaped its sandbox. */
        @Override
        public void run() {
            if (!job.start()) return;
            try {
                job.finish(runner.execute(job.request(), job.control()));
            } catch (Exception error) {
                job.finish(ProcessRunner.outcome(job.request(), "ERROR", "Isolated worker unavailable or failed."));
            }
        }
    }
}
