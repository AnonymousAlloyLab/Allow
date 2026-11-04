package dev.allow.backend;

import java.util.concurrent.Semaphore;
import java.util.concurrent.RejectedExecutionException;

/**
 * Shared local-principal admission across validation and legacy solver jobs.
 * This semaphore owns Java-launched processes. The SQL proxy independently
 * retains database leases until observed cleanup, including after Java exits.
 */
final class WorkerCapacity {
    private static final Semaphore PERMIT = new Semaphore(1);

    /** Prevents construction of the process-wide admission owner. */
    private WorkerCapacity() {}

    /** Acquires without a validation queue, before spawning or durable admission.
     * @throws RejectedExecutionException another local-principal operation is active
     */
    static void acquire() {
        if (!PERMIT.tryAcquire()) throw new RejectedExecutionException("Worker capacity reached");
    }

    /** Releases after owned child reap; this does not certify PostgreSQL cleanup. */
    static void release() {
        PERMIT.release();
    }
}
