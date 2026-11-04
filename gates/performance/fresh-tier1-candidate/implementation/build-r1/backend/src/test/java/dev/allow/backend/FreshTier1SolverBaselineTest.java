package dev.allow.backend;

import java.io.IOException;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Authored bounded solver workloads retain the unmodified default WorkerMain profile. */
class FreshTier1SolverBaselineTest {
    /** Acyclic optional edges admit a satisfying instance at the reviewed scope ceiling.
     * @throws Exception failed solver or supervision
     */
    @Test
    void defaultSolverHandlesBoundedSatWorkload() throws Exception {
        analyze("sig Node { edge: set Node } pred p { some Node and all n: Node | n not in n.^edge } "
                + "run p for 8 but exactly 8 Node", "SAT");
    }

    /** A finite total successor relation cannot satisfy the frozen acyclicity fact.
     * @throws Exception failed solver or supervision
     */
    @Test
    void defaultSolverHandlesBoundedUnsatWorkload() throws Exception {
        analyze("sig Node { edge: one Node } fact { all n: Node | n not in n.^edge } "
                + "run {} for 8 but exactly 8 Node", "UNSAT");
    }

    /** Runs the full production solver supervisor and records finite observations only.
     * @param source exact authored SAT or UNSAT model
     * @param expected required terminal outcome
     * @throws Exception failed sandbox, solver, identity or reaping
     */
    private static void analyze(String source, String expected) throws Exception {
        TrackedLauncher launcher = new TrackedLauncher();
        ProcessRunner runner = new ProcessRunner(launcher, 10000);
        var request = WorkerIntegrationTest.request(source, "ANALYZE");
        long started = System.nanoTime();
        var result = runner.execute(request, new JobControl());
        long elapsed = System.nanoTime() - started;
        assertEquals(expected, result.status());
        assertEquals(request.sourceHash(), result.sourceHash());
        assertTrue(launcher.reaped());
        System.out.println("solver_fixture profile=DEFAULT status=" + result.status()
                + " elapsedNanos=" + elapsed + " reaped=true");
    }

    /** Captures the actual default sandbox handle without replacing its launch behavior. */
    private static final class TrackedLauncher implements SandboxLauncher {
        private final BubblewrapLauncher delegate;
        private Process child;

        /** Captures the unchanged default solver launcher and full build identity.
         * @throws IOException incomplete installation
         */
        private TrackedLauncher() throws IOException { delegate = new BubblewrapLauncher(Path.of("target")); }

        /** Executes the real full-check launcher, retaining the exact returned process handle.
         * @return newly owned sandbox process
         * @throws IOException unavailable sandbox or changed identity
         */
        @Override
        public Process launch() throws IOException {
            child = delegate.launch();
            return child;
        }

        /** Keeps the production identity instead of substituting a fixture digest.
         * @return full build identity
         */
        @Override
        public String identity() { return delegate.identity(); }

        /** Reports exit only for the exact process returned by the real launcher.
         * @return whether an owned process was started and is no longer alive
         */
        private boolean reaped() { return child != null && !child.isAlive(); }
    }
}
