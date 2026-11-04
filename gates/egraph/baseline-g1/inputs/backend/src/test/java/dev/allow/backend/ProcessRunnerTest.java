package dev.allow.backend;

import dev.allow.dto.*;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Adversarial child process paths use only package-private injection seams. */
class ProcessRunnerTest {
    /**
     * Deadline kills/reaps a child that does not consume stdin.
     * @throws Exception supervisor failure
     */
    @Test
    void timeoutReapsStalledInput() throws Exception {
        FixtureLauncher launcher = new FixtureLauncher("SLEEP");
        WorkerRequest request = WorkerIntegrationTest.request("\n".repeat(32000), "ANALYZE");
        JobView result = new ProcessRunner(launcher, 100).execute(request, new JobControl());
        assertEquals("TIMEOUT", result.status());
        assertFalse(launcher.alive());
    }

    /**
     * Explicit cancellation survives a late child exit.
     * @throws Exception supervisor failure
     */
    @Test
    void cancellationReaps() throws Exception {
        FixtureLauncher launcher = new FixtureLauncher("SLEEP");
        JobControl control = new JobControl();
        RunCall call = new RunCall(new ProcessRunner(launcher, 10000), control);
        Thread thread = new Thread(call);
        thread.start();
        long deadline = System.nanoTime() + 2000000000L;
        while (!launcher.alive() && System.nanoTime() < deadline) Thread.sleep(5);
        assertTrue(launcher.alive());
        control.cancel();
        thread.join(3000);
        assertFalse(thread.isAlive());
        assertFalse(launcher.alive());
        assertNull(call.failure.get());
        assertEquals("CANCELLED", call.result.get().status());
    }

    /** Crash and malformed streams cannot become UNSAT. */
    @Test
    void hostileFramesReject() {
        for (String mode : new String[]{"CRASH", "DUPKEY", "TRAILING", "WHITESPACE", "STDERR", "STDOUT"}) {
            FixtureLauncher launcher = new FixtureLauncher(mode);
            ProcessRunner runner = new ProcessRunner(launcher, 3000);
            assertThrows(Exception.class, new Invoke(runner)::run, mode);
            assertFalse(launcher.alive(), mode);
        }
    }

    /** Sandbox launch denial has no unsandboxed fallback. */
    @Test
    void deniedSandboxRejects() {
        ProcessRunner runner = new ProcessRunner(new DeniedLauncher(), 1000);
        assertThrows(IOException.class, new Invoke(runner)::run);
    }

    /** Test-only callable adapter. */
    private record Invoke(ProcessRunner runner) {
        /**
     * Invokes one fixture.
     * @throws Exception expected rejection path
     */
        void run() throws Exception {
            runner.execute(WorkerIntegrationTest.request("sig A {} run {}", "ANALYZE"), new JobControl());
        }
    }

    /** Injects an unavailable sandbox without changing production environment. */
    private static final class DeniedLauncher implements SandboxLauncher {
        /**
     * Fails closed.
     * @return no child
     * @throws IOException unavailable sandbox
     */
        @Override
        public Process launch() throws IOException {
            throw new IOException("Sandbox denied");
        }
    }

    /** Captures asynchronous supervisor results without undocumented callbacks. */
    private static final class RunCall implements Runnable {
        private final ProcessRunner runner;
        private final JobControl control;
        private final AtomicReference<JobView> result = new AtomicReference<>();
        private final AtomicReference<Exception> failure = new AtomicReference<>();

        /**
     * Stores fixture runner.
     * @param runner supervisor
     * @param control cancellation owner
     */
        RunCall(ProcessRunner runner, JobControl control) {
            this.runner = runner;
            this.control = control;
        }

        /** Runs one child and records its terminal result. */
        @Override
        public void run() {
            try {
                result.set(runner.execute(WorkerIntegrationTest.request("sig A {} run {}", "ANALYZE"), control));
            } catch (Exception error) {
                failure.set(error);
            }
        }
    }
}
