package dev.allow.backend;

import dev.allow.dto.*;
import dev.allow.worker.Hashes;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Executes the pinned Alloy artifact through the real namespace sandbox. */
class WorkerIntegrationTest {
    /**
     * Verifies a fact-respecting SAT run and readable witness.
     * @throws Exception worker failure
     */
    @Test
    void satRun() throws Exception {
        JobView result = analyze("sig Person { friend: set Person } run { some Person } for 3");
        assertEquals("SAT", result.status(), result.message());
        assertEquals("run", result.commandKind());
        assertNotNull(result.witness());
        assertFalse(result.witness().states().isEmpty());
        assertEquals(64, result.witness().fullInstanceHash().length());
    }

    /**
     * Distinguishes bounded run absence from a worker error.
     * @throws Exception worker failure
     */
    @Test
    void unsatRun() throws Exception {
        JobView result = analyze("sig A {} fact { no A } run { some A } for 3");
        assertEquals("UNSAT", result.status(), result.message());
        assertEquals("run", result.commandKind());
        assertNull(result.witness());
    }

    /**
     * A SAT assertion check is a counterexample.
     * @throws Exception worker failure
     */
    @Test
    void satCheck() throws Exception {
        JobView result = analyze("sig A {} assert Empty { no A } check Empty for 3");
        assertEquals("SAT", result.status(), result.message());
        assertEquals("check", result.commandKind());
        assertNotNull(result.witness());
    }

    /**
     * A valid bounded assertion check returns UNSAT.
     * @throws Exception worker failure
     */
    @Test
    void unsatCheck() throws Exception {
        JobView result = analyze("sig A {} assert Identity { A = A } check Identity for 3");
        assertEquals("UNSAT", result.status(), result.message());
        assertEquals("check", result.commandKind());
    }

    /**
     * Type errors cannot turn into solver success.
     * @throws Exception worker failure
     */
    @Test
    void invalidSource() throws Exception {
        JobView result = analyze("sig A {} run { A and A } for 3");
        assertEquals("INVALID", result.status());
    }

    /**
     * Explicit imports reject before filesystem resolution.
     * @throws Exception worker failure
     */
    @Test
    void importRejectedInChild() throws Exception {
        JobView result = analyze("open util/ordering[A]\nsig A {} run {} for 3");
        assertEquals("UNSUPPORTED", result.status(), result.message());
    }

    /**
     * Validation compiles but never supplies a solver badge.
     * @throws Exception worker failure
     */
    @Test
    void validateOnly() throws Exception {
        WorkerRequest request = request("sig A {} run { some A } for 3", "VALIDATE");
        JobView result = runner().execute(request, new JobControl());
        assertEquals("VALIDATED", result.status(), result.message());
        assertNull(result.witness());
        assertEquals(request.sourceHash(), result.sourceHash());
        assertEquals(request.epoch(), result.epoch());
    }

    /**
     * Creates the production sandbox runner.
     * @return real supervised runner
     * @throws java.io.IOException incomplete build
     */
    private ProcessRunner runner() throws java.io.IOException {
        return new ProcessRunner(new BubblewrapLauncher(Path.of("target")), 10000);
    }

    /**
     * Sends one exact-source analysis.
     * @param source model
     * @return terminal result
     * @throws Exception failed child
     */
    private JobView analyze(String source) throws Exception {
        return runner().execute(request(source, "ANALYZE"), new JobControl());
    }

    /**
     * Builds deterministic fixture identity.
     * @param source model
     * @param operation action
     * @return request
     */
    static WorkerRequest request(String source, String operation) {
        return new WorkerRequest(1, "test-job", source, Hashes.text(source), Hashes.text("fixture:" + source),
                0, 7, 9, operation);
    }
}
