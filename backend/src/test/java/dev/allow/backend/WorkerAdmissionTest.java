package dev.allow.backend;

import dev.allow.dto.JobRequest;
import dev.allow.dto.JobView;
import dev.allow.dto.WorkerRequest;
import java.io.IOException;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Distinguishes definite permit rejection from uncertain attempted sandbox startup. */
class WorkerAdmissionTest {
    /** Permit rejection proves no launch and cannot permanently quarantine a public owner.
     * @throws Exception interrupted fixture or launcher verification failure
     */
    @Test
    void rejectedPermitRetainsNoWorkerCleanupEvidence() throws Exception {
        SandboxLauncher launcher = mock(SandboxLauncher.class);
        when(launcher.identity()).thenReturn("admission-fixture");
        JobService jobs = new JobService(new ProcessRunner(launcher, 1000));
        WorkerCapacity.acquire();
        try {
            jobs.registerOwner("public-owner", System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
            JobView job = jobs.submit(input(), "public-owner");
            awaitTerminal(jobs, job.jobId(), "public-owner");
            awaitQuiescent(jobs, "public-owner");
            assertEquals("ERROR", jobs.get(job.jobId(), "public-owner").status());
            assertFalse(jobs.ownerBusy("public-owner"));
            assertTrue(jobs.forgetOwner("public-owner"));
            verify(launcher, never()).launch();
        } finally {
            WorkerCapacity.release();
            jobs.close();
        }
    }

    /** An attempted launcher exception cannot inherit the definite no-admission proof.
     * @throws Exception checked runner failure
     */
    @Test
    void uncertainLauncherExceptionRetainsUnsafeCleanup() throws Exception {
        SandboxLauncher launcher = mock(SandboxLauncher.class);
        when(launcher.launch()).thenThrow(new IOException("Uncertain attempted startup"));
        ProcessRunner runner = new ProcessRunner(launcher, 1000);
        JobControl control = new JobControl();
        assertThrows(IOException.class, new Execute(runner, control)::run);
        assertFalse(control.cleanupSafe());
        verify(launcher).launch();
    }

    /** Waits for a bounded displayed terminal outcome without assuming reaping.
     * @param jobs supervisor
     * @param id opaque job
     * @param owner immutable scope
     * @throws InterruptedException interrupted wait
     */
    private void awaitTerminal(JobService jobs, String id, String owner) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while (true) {
            String status = jobs.get(id, owner).status();
            if (!status.equals("QUEUED") && !status.equals("RUNNING")) return;
            assertTrue(System.nanoTime() < deadline, "Job did not finish");
            Thread.sleep(2);
        }
    }

    /** Separately waits for actual task exit and cleanup evidence.
     * @param jobs supervisor
     * @param owner immutable scope
     * @throws InterruptedException interrupted wait
     */
    private void awaitQuiescent(JobService jobs, String owner) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while (!jobs.ownerQuiescent(owner)) {
            assertTrue(System.nanoTime() < deadline, "Definite no-start job retained quarantine");
            Thread.sleep(2);
        }
    }

    /** Supplies bounded independent worker input.
     * @return browser candidate
     */
    private static JobRequest input() { return new JobRequest("sig A {} run {} for 3", 0, 2, 3, "VALIDATE"); }

    /** Calls the actual runner without hiding checked failure in an inline callback.
     * @param runner production runner
     * @param control cleanup owner
     */
    private record Execute(ProcessRunner runner, JobControl control) {
        /** Attempts one worker launch.
         * @throws Exception bounded runner failure
         */
        void run() throws Exception {
            runner.execute(new WorkerRequest(1, "fixture", input().source(), "hash", "key", 0, 2, 3, "VALIDATE"), control);
        }
    }
}
