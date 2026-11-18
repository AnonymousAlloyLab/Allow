package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Comparison protocol and absolute pre-launch deadline tests through real owned processes. */
class DocumentComparisonWorkerTest {
    /** A slow launch consumes the original budget and cannot restart it at frame exchange.
     * @throws Exception process fixture unavailable
     */
    @Test void launchTimeConsumesBudgetAndChildIsReaped() throws Exception {
        Process child = new ProcessBuilder("/bin/sleep", "30").start();
        DocumentWorker worker = new DocumentWorker(new Delayed(child), ProcessIdentity::startTicks);
        assertThrows(IOException.class, new Compare(worker, 20));
        assertFalse(child.isAlive());
        assertFalse(worker.recovery().path("noWorkerStarted").asBoolean());
    }

    /** A bounded deterministic model denial survives the strict one-shot protocol.
     * @throws Exception process fixture unavailable
     */
    @Test void unsupportedIsDistinctFromUnsat() throws Exception {
        String code = "import json,sys; r=json.load(sys.stdin); print(json.dumps(dict(protocol=1,requestId=r['requestId'],status='UNSUPPORTED',data=dict(reason='Different background'))))";
        Process child = new ProcessBuilder("python3", "-c", code).start();
        DocumentWorker worker = new DocumentWorker(new Existing(child), ProcessIdentity::startTicks);
        var empty = JsonNodeFactory.instance.objectNode();
        var result = worker.compare("COMPARE_MODELS", empty, empty, empty, "policy", 2000);
        assertEquals("UNSUPPORTED", result.path("status").asText());
        assertFalse(result.path("data").has("categories"));
        assertFalse(child.isAlive());
        assertEquals(child.pid(), worker.recovery().path("workerPid").asLong());
    }

    /** Unknown worker status cannot pass protocol validation even when identity is correct.
     * @throws Exception process fixture unavailable
     */
    @Test void unknownStatusIsRejectedAndReaped() throws Exception {
        String code = "import json,sys; r=json.load(sys.stdin); print(json.dumps(dict(protocol=1,requestId=r['requestId'],status='MAGIC',data={})))";
        Process child = new ProcessBuilder("python3", "-c", code).start();
        DocumentWorker worker = new DocumentWorker(new Existing(child), ProcessIdentity::startTicks);
        assertThrows(IOException.class, new Compare(worker, 2000));
        assertFalse(child.isAlive());
    }

    /** Transfers one real process to the ordinary worker lifecycle. */
    private record Existing(Process child) implements SandboxLauncher {
        /** Returns the exact owned fixture process.
         * @return fixture child
         */
        public Process launch() { return child; }
    }

    /** Models launch/bootstrap latency without creating another process owner. */
    private record Delayed(Process child) implements SandboxLauncher {
        /** Delays launch long enough to exhaust a short original operation budget.
         * @return exact owned child
         * @throws IOException interrupted fixture delay
         */
        public Process launch() throws IOException {
            try { Thread.sleep(60); }
            catch (InterruptedException failure) { Thread.currentThread().interrupt(); throw new IOException("Interrupted fixture", failure); }
            return child;
        }
    }

    /** Executes comparison through the production transport with inert trusted JSON. */
    private record Compare(DocumentWorker worker, long millis) implements Executable {
        /** Exchanges one bounded comparison frame.
         * @throws IOException protocol or deadline failure
         * @throws InterruptedException cancellation after reaping
         */
        public void execute() throws IOException, InterruptedException {
            var empty = JsonNodeFactory.instance.objectNode();
            worker.compare("COMPARE", empty, empty, empty, "policy", millis);
        }
    }
}
