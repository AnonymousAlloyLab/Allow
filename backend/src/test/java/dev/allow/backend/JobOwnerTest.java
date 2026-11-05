package dev.allow.backend;

import dev.allow.dto.JobRequest;
import dev.allow.dto.JobView;
import dev.allow.dto.WorkerRequest;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Exercises owner isolation, expiry and actual cleanup using no external processes. */
class JobOwnerTest {
    /** Verifies foreign lookups and logical cancellation never release a live owner.
     * @throws Exception interrupted fixture
     */
    @Test
    void isolationAndPhysicalCleanup() throws Exception {
        OwnedRunner runner = new OwnedRunner();
        JobService jobs = new JobService(runner);
        try {
            jobs.registerOwner("a", System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
            jobs.registerOwner("b", System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
            JobView first = jobs.submit(input(), "a");
            assertTrue(runner.entered.await(2, TimeUnit.SECONDS));
            assertNull(jobs.get(first.jobId(), "b"));
            assertNull(jobs.get(first.jobId()));
            assertNull(jobs.cancel(first.jobId(), "b"));
            assertThrows(RejectedExecutionException.class, new Submit(jobs, "a")::run);
            jobs.cancelOwner("a");
            assertTrue(jobs.ownerBusy("a"));
            assertFalse(jobs.forgetOwner("a"));
            runner.release.countDown();
            awaitClean(jobs, "a");
            assertTrue(jobs.forgetOwner("a"));
            assertNull(jobs.get(first.jobId(), "a"));
        } finally {
            runner.release.countDown();
            jobs.close();
        }
    }

    /** Ensures expiration while queued prevents the runner from starting.
     * @throws Exception interrupted fixture
     */
    @Test
    void queuedExpiryNeverExecutes() throws Exception {
        OwnedRunner runner = new OwnedRunner();
        JobService jobs = new JobService(runner);
        try {
            jobs.submit(input());
            assertTrue(runner.entered.await(2, TimeUnit.SECONDS));
            jobs.registerOwner("queued", System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(100));
            JobView queued = jobs.submit(input(), "queued");
            Thread.sleep(150);
            assertNull(jobs.get(queued.jobId(), "queued"));
            runner.release.countDown();
            awaitClean(jobs, "queued");
            assertEquals(1, runner.calls.get());
            assertTrue(jobs.forgetOwner("queued"));
        } finally {
            runner.release.countDown();
            jobs.close();
        }
    }

    /** Bounds retained owned results while retaining the newest clean evidence.
     * @throws Exception interrupted fixture
     */
    @Test
    void retainedOwnerResultsAreBounded() throws Exception {
        OwnedRunner runner = new OwnedRunner();
        runner.release.countDown();
        JobService jobs = new JobService(runner);
        try {
            jobs.registerOwner("a", System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
            String first = null;
            for (int count = 0; count < 9; count++) {
                JobView current = jobs.submit(input(), "a");
                if (first == null) first = current.jobId();
                awaitClean(jobs, "a");
                assertNotNull(jobs.get(current.jobId(), "a"));
            }
            assertNull(jobs.get(first, "a"));
        } finally {
            jobs.close();
        }
    }

    /** Waits for actual runner cleanup rather than displayed terminal status.
     * @param jobs bounded supervisor
     * @param owner immutable owner
     * @throws InterruptedException interrupted wait
     */
    private void awaitClean(JobService jobs, String owner) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while (!jobs.ownerQuiescent(owner)) {
            assertTrue(System.nanoTime() < deadline);
            Thread.sleep(2);
        }
    }

    /** Supplies an independent bounded solver candidate.
     * @return test input
     */
    private static JobRequest input() { return new JobRequest("sig A {} run {} for 3", 0, 2, 3, "VALIDATE"); }

    /** Named callback keeps rejection tests free of inline authority capture.
     * @param jobs supervisor
     * @param owner immutable owner
     */
    private record Submit(JobService jobs, String owner) {
        /** Attempts one owned admission. */
        void run() { jobs.submit(input(), owner); }
    }

    /** Holds actual runner ownership independently from cancellation display. */
    private static final class OwnedRunner implements JobRunner {
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private final AtomicInteger calls = new AtomicInteger();

        /** Records explicit cleanup evidence only after the physical fixture releases.
         * @param request immutable worker request
         * @param control owned cleanup evidence
         * @return completed fixture outcome
         * @throws InterruptedException interrupted wait
         */
        @Override
        public JobView execute(WorkerRequest request, JobControl control) throws InterruptedException {
            calls.incrementAndGet();
            entered.countDown();
            try {
                release.await();
                return ProcessRunner.outcome(request, "VALIDATED", "Fixture completed");
            } finally {
                control.finished(true);
            }
        }
    }
}
