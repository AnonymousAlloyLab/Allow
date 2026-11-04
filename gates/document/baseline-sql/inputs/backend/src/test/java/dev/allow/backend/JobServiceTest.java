package dev.allow.backend;

import dev.allow.dto.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Deterministically checks queue admission and late-completion arbitration. */
class JobServiceTest {
    /**
     * Cancellation does not allow the next runner before physical completion.
     * @throws Exception scheduling failure
     */
    @Test
    void cancelledJobKeepsAdmission() throws Exception {
        BlockingRunner runner = new BlockingRunner();
        JobService jobs = new JobService(runner);
        try {
            JobView first = jobs.submit(input());
            assertTrue(runner.entered.await(2, TimeUnit.SECONDS));
            JobView second = jobs.submit(input());
            assertEquals("CANCELLED", jobs.cancel(first.jobId()).status());
            Thread.sleep(50);
            assertEquals(1, runner.calls.get());
            assertEquals("QUEUED", jobs.get(second.jobId()).status());
            runner.release.countDown();
            awaitTerminal(jobs, second.jobId());
            assertEquals("CANCELLED", jobs.get(first.jobId()).status());
            assertEquals("VALIDATED", jobs.get(second.jobId()).status());
        } finally {
            runner.release.countDown();
            jobs.close();
        }
    }

    /**
     * Exactly four requests may queue behind the active runner.
     * @throws Exception scheduling failure
     */
    @Test
    void queueIsBounded() throws Exception {
        BlockingRunner runner = new BlockingRunner();
        JobService jobs = new JobService(runner);
        try {
            jobs.submit(input());
            assertTrue(runner.entered.await(2, TimeUnit.SECONDS));
            for (int count = 0; count < 4; count++) jobs.submit(input());
            assertThrows(RejectedExecutionException.class, new Submit(jobs)::run);
        } finally {
            runner.release.countDown();
            jobs.close();
        }
    }

    /**
     * Waits for a bounded terminal fixture result.
     * @param jobs supervisor
     * @param id job
     * @throws InterruptedException interrupted wait
     */
    private void awaitTerminal(JobService jobs, String id) throws InterruptedException {
        long deadline = System.nanoTime() + 2000000000L;
        while (jobs.get(id).status().equals("QUEUED") || jobs.get(id).status().equals("RUNNING")) {
            assertTrue(System.nanoTime() < deadline, "Job did not finish");
            Thread.sleep(5);
        }
    }

    /**
     * Creates a minimal candidate.
     * @return independent input
     */
    private static JobRequest input() {
        return new JobRequest("sig A {} run {} for 3", 0, 2, 3, "VALIDATE");
    }

    /** Named callback for rejection assertions. */
    private record Submit(JobService jobs) {
        /** Attempts a sixth admitted request. */
        void run() {
            jobs.submit(input());
        }
    }

    /** Ignores logical cancellation until the test releases physical execution. */
    private static final class BlockingRunner implements JobRunner {
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private final AtomicInteger calls = new AtomicInteger();

        /**
     * Holds admission until release.
     * @param request identity
     * @param control unused cancellation
     * @return late result
     * @throws InterruptedException interrupted fixture
     */
        @Override
        public JobView execute(WorkerRequest request, JobControl control) throws InterruptedException {
            calls.incrementAndGet();
            entered.countDown();
            release.await();
            return ProcessRunner.outcome(request, "VALIDATED", "Fixture completed");
        }
    }
}
