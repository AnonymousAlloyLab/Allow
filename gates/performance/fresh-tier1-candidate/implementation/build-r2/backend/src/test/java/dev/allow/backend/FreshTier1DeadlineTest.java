package dev.allow.backend;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Exact production ten-second deadline against stopped, owned real sandbox launches. */
class FreshTier1DeadlineTest {
    /** Both profiles retain ownership through the unchanged ten-second timeout and mandatory reap.
     * @throws Exception failed sandbox launch, stop fixture or cleanup
     */
    @Test
    void bothProfilesEnforceActualTenSecondDeadlineAndReap() throws Exception {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            Process child = new BubblewrapLauncher(Path.of("target"), true, profile).launch();
            try {
                stopOwned(child);
                long started = System.nanoTime();
                IOException error = assertThrows(IOException.class, new Exchange(child));
                long elapsed = System.nanoTime() - started;
                assertEquals("Child deadline exceeded", error.getMessage());
                assertTrue(elapsed >= TimeUnit.SECONDS.toNanos(10));
                assertFalse(child.isAlive());
                System.out.println("deadline_fixture profile=" + profile + " elapsedNanos=" + elapsed + " reaped=true");
            } finally {
                FrameProcess.reap(child);
            }
        }
    }

    /** Stops only the newly created sandbox while retaining its parent-owned process handle.
     * @param child newly launched process blocked on this test's private input pipe
     * @throws Exception failed ownership observation or stop fixture
     */
    private static void stopOwned(Process child) throws Exception {
        String identity = ProcessIdentity.startTicks(child.pid());
        assertTrue(child.isAlive());
        Process signal = new ProcessBuilder("/bin/kill", "-STOP", Long.toString(child.pid())).start();
        try {
            assertTrue(signal.waitFor(5, TimeUnit.SECONDS));
            assertEquals(0, signal.exitValue());
            assertTrue(child.isAlive());
            assertEquals(identity, ProcessIdentity.startTicks(child.pid()));
        } finally {
            FrameProcess.reap(signal);
        }
    }

    /** Supplies the exact unchanged production timeout and output cap. */
    private record Exchange(Process child) implements Executable {
        /** Waits for the owned stopped process using production FrameProcess.
         * @throws IOException expected ten-second timeout
         * @throws InterruptedException unexpected external interruption
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            FrameProcess.exchange(child, "{}".getBytes(StandardCharsets.UTF_8), 1048577, 10000);
        }
    }
}
