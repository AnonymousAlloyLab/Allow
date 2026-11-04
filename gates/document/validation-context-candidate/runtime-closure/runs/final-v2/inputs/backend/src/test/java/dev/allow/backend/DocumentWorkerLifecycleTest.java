package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Exercises owned-child recovery when Linux incarnation capture fails before any request write. */
class DocumentWorkerLifecycleTest {
    /** Failed identity capture still kills/reaps the exact child and preserves truthful recovery fields.
     * @throws IOException unavailable authored process fixture
     */
    @Test
    void reapsBeforeReturningUnidentifiedChildProof() throws IOException {
        Process child = new ProcessBuilder("/bin/sleep", "30").start();
        DocumentWorker worker = new DocumentWorker(new Existing(child), new MissingIdentity());
        assertThrows(IOException.class, new Validate(worker));
        assertFalse(child.isAlive());
        assertEquals(child.pid(), worker.recovery().path("workerPid").longValue());
        assertTrue(worker.recovery().path("workerStartTicks").isNull());
        assertFalse(worker.recovery().path("noWorkerStarted").booleanValue());
    }

    /** An interrupted caller cannot escape the mandatory owned-process reaping path.
     * @throws IOException unavailable authored process fixture
     */
    @Test
    void interruptedIdentityFailureStillReaps() throws IOException {
        Process child = new ProcessBuilder("/bin/sleep", "30").start();
        DocumentWorker worker = new DocumentWorker(new Existing(child), new MissingIdentity());
        Thread.currentThread().interrupt();
        try {
            assertThrows(IOException.class, new Validate(worker));
            assertFalse(child.isAlive());
            assertTrue(Thread.currentThread().isInterrupted());
            assertFalse(worker.recovery().path("noWorkerStarted").booleanValue());
        } finally { Thread.interrupted(); }
    }

    /** Before any launch, evidence truthfully distinguishes absence from a started-and-reaped child. */
    @Test
    void noWorkerEvidencePrecedesLaunch() {
        DocumentWorker worker = new DocumentWorker(new NeverLaunch(), new MissingIdentity());
        assertTrue(worker.recovery().path("noWorkerStarted").booleanValue());
        assertTrue(worker.recovery().path("workerPid").isNull());
    }

    /** Supplies an already owned authored process without invoking the production launcher. */
    private record Existing(Process child) implements SandboxLauncher {
        /** Transfers the fixture process to the worker's normal lifecycle.
         * @return owned process
         */
        @Override
        public Process launch() { return child; }
    }

    /** Rejects an unexpected launch in the pre-launch evidence fixture. */
    private record NeverLaunch() implements SandboxLauncher {
        /** Fails if inspection itself starts a process.
         * @return never returns
         * @throws IOException unexpected invocation
         */
        @Override
        public Process launch() throws IOException { throw new IOException("Unexpected launch"); }
    }

    /** Reproduces an unavailable /proc entry without depending on process-exit timing. */
    private record MissingIdentity() implements ProcessIdentity.Reader {
        /** Reports unavailable incarnation evidence for the owned child.
         * @param pid owned process
         * @return never returns
         * @throws IOException simulated early /proc disappearance
         */
        @Override
        public String read(long pid) throws IOException { throw new IOException("Identity unavailable"); }
    }

    /** Invokes the real worker orchestration with bounded inert JSON input. */
    private record Validate(DocumentWorker worker) implements Executable {
        /** Executes the startup path whose failure must not leak a process.
         * @throws IOException intended missing-identity result
         * @throws InterruptedException caller interrupted after reaping
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            var empty = JsonNodeFactory.instance.objectNode();
            worker.validate(empty, empty, empty, "policy");
        }
    }
}
