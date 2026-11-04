package dev.allow.backend;

import java.util.concurrent.Semaphore;
import java.util.concurrent.RejectedExecutionException;

/** Shared local-principal admission across document validation and legacy solver jobs. */
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

    /** Releases only after the owner has reaped every child it started. */
    static void release() {
        PERMIT.release();
    }
}
