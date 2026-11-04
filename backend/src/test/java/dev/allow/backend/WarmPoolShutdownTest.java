package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

/** Real coordinator shutdown and journal I/O tests; no worker, SQL or cgroup authority is simulated. */
class WarmPoolShutdownTest {
    @TempDir
    private Path temporary;

    /** Refilling cannot acquire a shutdown interrupt immediately before its durable journal write.
     * @throws Exception failed controlled executor or private filesystem
     */
    @Test
    void refillShutdownDoesNotInterruptJournalOwner() throws Exception { exercise("refill"); }

    /** The deadline watcher likewise finishes existing durable I/O without forced interruption.
     * @throws Exception failed controlled executor or private filesystem
     */
    @Test
    void watcherShutdownDoesNotInterruptJournalOwner() throws Exception { exercise("watcher"); }

    /** Holds actual journal work until the actual selected coordinator executor begins shutdown.
     * @param role private executor whose already-running task owns the write
     * @throws Exception failed synchronization, journal write or executor termination
     */
    private void exercise(String role) throws Exception {
        Files.setPosixFilePermissions(temporary, PosixFilePermissions.fromString("rwx------"));
        WarmWorkerPool pool = new WarmWorkerPool(mock(WorkerPoolLedger.class), mock(WarmImageLauncher.class),
                "a".repeat(64), "document-v1");
        try (WorkerJournal journal = new WorkerJournal(temporary)) {
            JournalTask task = new JournalTask(journal);
            ClosePool closing = new ClosePool(pool);
            Thread closer = new Thread(closing, "warm-test-shutdown-owner");
            try {
                ExecutorService owner = executor(pool, role);
                owner.execute(task);
                assertTrue(task.entered.await(2, TimeUnit.SECONDS));
                closer.start();
                awaitShutdown(owner, closer);
                task.release.countDown();
                closer.join(4000);
                assertFalse(closer.isAlive());
                assertNull(closing.failure.get());
                assertNull(task.failure.get());
                assertFalse(task.interrupted.get(), "Shutdown interrupted an existing journal owner");
                assertEquals(state(), journal.read());
                journal.write(state());
                assertTrue(executor(pool, "refill").isTerminated());
                assertTrue(executor(pool, "watcher").isTerminated());
            } finally { task.release.countDown(); closer.join(4000); pool.close(); }
        } finally { pool.close(); }
    }

    /** Waits for shutdown initiation without guessing a scheduling delay.
     * @param executor actual coordinator executor
     * @param closer sole close caller, which must finish shutdown initiation before release
     * @throws InterruptedException cancelled test supervisor
     */
    private static void awaitShutdown(ExecutorService executor, Thread closer) throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while ((!executor.isShutdown() || closer.getState() != Thread.State.TIMED_WAITING) && System.nanoTime() < end) {
            TimeUnit.MILLISECONDS.sleep(1);
        }
        assertTrue(executor.isShutdown(), "Pool close did not stop coordinator scheduling");
        assertEquals(Thread.State.TIMED_WAITING, closer.getState(), "Close did not reach its executor-termination wait");
    }

    /** Observes an actual executor solely to synchronize the controlled shutdown boundary.
     * @param pool actual coordinator whose close method is under test
     * @param role fixed private executor field name
     * @return the production-created task executor
     * @throws ReflectiveOperationException changed observation boundary
     */
    private static ExecutorService executor(WarmWorkerPool pool, String role) throws ReflectiveOperationException {
        Field field = WarmWorkerPool.class.getDeclaredField(role);
        field.setAccessible(true);
        return (ExecutorService) field.get(pool);
    }

    /** Builds a bounded operational journal record independently of coordinator implementation.
     * @return valid empty-slot metadata with no model data
     */
    private static ObjectNode state() {
        ObjectNode value = JsonNodeFactory.instance.objectNode().put("schema", 1)
                .put("poolNonce", "00000000-0000-0000-0000-000000000001")
                .put("ownerPid", 123).put("ownerStartTicks", "456")
                .put("bootId", "00000000-0000-0000-0000-000000000002")
                .put("build", "a".repeat(64)).put("policy", "document-v1")
                .put("cgroupRoot", "/sys/fs/cgroup/test-shutdown");
        value.putArray("generations").add(0).add(0);
        value.putArray("slots").addNull().addNull();
        return value;
    }

    /** Owns one actual durable write, retaining any interrupt until NIO observes its real semantics. */
    private static final class JournalTask implements Runnable {
        private final WorkerJournal journal;
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private final AtomicBoolean interrupted = new AtomicBoolean();
        private final AtomicReference<Throwable> failure = new AtomicReference<>();

        /** Retains the real private journal for this single controlled executor task.
         * @param journal actual metadata owner
         */
        private JournalTask(WorkerJournal journal) { this.journal = journal; }

        /** Writes only after shutdown begins; records real NIO failure without replacing its cause. */
        @Override
        public void run() {
            entered.countDown();
            try {
                awaitRelease();
                if (interrupted.get()) Thread.currentThread().interrupt();
                journal.write(state());
            } catch (Throwable error) { failure.set(error); }
            finally { Thread.interrupted(); }
        }

        /** Preserves a forced shutdown interrupt while waiting for the test supervisor's release.
         * @throws IllegalStateException bounded fixture synchronization failure
         */
        private void awaitRelease() {
            long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
            while (release.getCount() != 0 && System.nanoTime() < end) {
                try { release.await(10, TimeUnit.MILLISECONDS); }
                catch (InterruptedException expected) { interrupted.set(true); }
            }
            if (release.getCount() != 0) throw new IllegalStateException("Journal fixture release missing");
            if (Thread.currentThread().isInterrupted()) interrupted.set(true);
        }
    }

    /** Owns the actual close invocation so the supervisor can release blocked I/O deterministically. */
    private static final class ClosePool implements Runnable {
        private final WarmWorkerPool pool;
        private final AtomicReference<Throwable> failure = new AtomicReference<>();

        /** Retains the production coordinator to close without a mock shutdown implementation.
         * @param pool actual bounded executor owner
         */
        private ClosePool(WarmWorkerPool pool) { this.pool = pool; }

        /** Retains the exact close outcome instead of losing failure on a test-owned thread. */
        @Override
        public void run() {
            try { pool.close(); }
            catch (Throwable error) { failure.set(error); }
        }
    }
}
