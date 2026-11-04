package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Both-profile lifecycle checks and explicitly separate shared-transport boundary checks. */
class FreshTier1SafetyTest {
    /** The actual one-shot entrypoint rejects malformed and trailing private JSON in both profiles.
     * @throws Exception unavailable sandbox or cleanup
     */
    @Test
    void bothProfilesRejectMalformedPrivateFramesAndReap() throws Exception {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            for (String input : new String[]{"{}", "{", "{} {}"}) {
                Process child = launch(profile);
                assertThrows(IOException.class, new Exchange(child, input.getBytes(StandardCharsets.UTF_8), 1048577, 10000));
                assertFalse(child.isAlive());
                assertNotEquals(0, child.exitValue());
            }
        }
    }

    /** A deliberately accelerated transport deadline reaps a real fresh worker in both profiles.
     * @throws Exception unavailable sandbox or cleanup
     */
    @Test
    void bothProfilesReapAfterAcceleratedDeadline() throws Exception {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            Process child = launch(profile);
            assertThrows(IOException.class, new Exchange(child, JsonWire.encode(frame()), 1048577, 1));
            assertFalse(child.isAlive());
        }
    }

    /** Caller interruption cannot return while an actual profile-selected child is still running.
     * @throws Exception unavailable sandbox or cleanup
     */
    @Test
    void bothProfilesReapAfterInterruption() throws Exception {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            Process child = launch(profile);
            Thread.currentThread().interrupt();
            try {
                assertThrows(InterruptedException.class, new Exchange(child, JsonWire.encode(frame()), 1048577, 10000));
                assertFalse(child.isAlive());
            } finally {
                Thread.interrupted();
                FrameProcess.reap(child);
            }
        }
    }

    /** Exact private input boundaries distinguish accepted worker transport from prelaunch rejection.
     * @throws Exception unavailable sandbox or fixture encoding
     */
    @Test
    void bothProfilesPreserveExactPrivateInputBoundary() throws Exception {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            ObjectNode input = sizedFrame(2097151);
            DocumentWorker accepted = new DocumentWorker(profile);
            var result = accepted.validate(input.path("candidate"), input.path("baseArtifact"), input.path("ownedIdInventory"), "safety");
            assertEquals("INVALID", result.path("status").textValue());
            assertFalse(accepted.recovery().path("noWorkerStarted").booleanValue());
            for (int size : new int[]{2097152, 2097153}) {
                DocumentWorker denied = new DocumentWorker(profile);
                assertThrows(IOException.class, new Validate(denied, sizedFrame(size)));
                assertTrue(denied.recovery().path("noWorkerStarted").booleanValue());
            }
        }
    }

    /** Shared FrameProcess enforces the exact document stdout cap independently of compiler selection.
     * @throws Exception unavailable authored pipe fixture
     */
    @Test
    void sharedTransportPreservesExactOutputBoundary() throws Exception {
        for (int size : new int[]{1048576, 1048577, 1048578}) {
            Process child = new ProcessBuilder("/bin/cat").start();
            byte[] input = "x".repeat(size - 1).getBytes(StandardCharsets.US_ASCII);
            if (size <= 1048577) assertEquals(size, FrameProcess.exchange(child, input, 1048577, 10000).length);
            else assertThrows(IOException.class, new Exchange(child, input, 1048577, 10000));
            assertFalse(child.isAlive());
        }
    }

    /** Shared stderr capture preserves its exact independent cap without leaking unbounded diagnostics.
     * @throws Exception unavailable authored output fixture
     */
    @Test
    void sharedTransportPreservesExactStderrBoundary() throws Exception {
        String program = "import sys; sys.stderr.write('x'*int(sys.argv[1])); sys.stderr.flush(); "
                + "sys.stdin.buffer.read(); sys.stdout.write('{}\\n')";
        for (int size : new int[]{32767, 32768, 32769}) {
            Process child = new ProcessBuilder("/usr/bin/python3", "-c", program, Integer.toString(size)).start();
            if (size <= 32768) assertEquals(3, FrameProcess.exchange(child, new byte[0], 1048577, 10000).length);
            else assertThrows(IOException.class, new Exchange(child, new byte[0], 1048577, 10000));
            assertFalse(child.isAlive());
        }
    }

    /** Shared framing rejects multiple output records without treating them as a complete response.
     * @throws Exception unavailable authored pipe fixture
     */
    @Test
    void sharedTransportRejectsTrailingOutput() throws Exception {
        Process child = new ProcessBuilder("/bin/cat").start();
        assertThrows(IOException.class,
                new Exchange(child, "{}\n{}".getBytes(StandardCharsets.US_ASCII), 1048577, 10000));
        assertFalse(child.isAlive());
    }

    /** Launches the real fixed sandbox with full constructor and per-launch identity checks.
     * @param profile trusted finite profile
     * @return owned fresh process
     * @throws IOException unavailable installation or sandbox
     */
    private static Process launch(WorkerLaunchProfile profile) throws IOException {
        return new BubblewrapLauncher(Path.of("target"), true, profile).launch();
    }

    /** Creates a deterministic nonce-bearing private frame without generated-ID normalization.
     * @return authored complete worker input
     */
    private static ObjectNode frame() {
        ObjectNode value = JsonNodeFactory.instance.objectNode().put("protocol", 1)
                .put("requestId", "00000000-0000-4000-8000-000000000001").put("policyVersion", "safety").put("operation", "VALIDATE");
        value.putObject("candidate").put("mode", "SOURCE").put("source", "sig A {}");
        value.putObject("baseArtifact");
        value.putObject("ownedIdInventory");
        return value;
    }

    /** Sizes a deterministic-invalid candidate so the boundary check does not perform a huge parse.
     * @param size exact bytes before the production writer appends its newline
     * @return private frame with fixed-width nonce and exact encoded length
     * @throws IOException fixture encoding failure
     */
    private static ObjectNode sizedFrame(int size) throws IOException {
        ObjectNode value = frame();
        value.putObject("candidate").put("mode", "INTENTIONALLY_INVALID");
        ObjectNode inventory = value.putObject("ownedIdInventory").put("padding", "");
        inventory.put("padding", "x".repeat(size - JsonWire.encode(value).length));
        assertEquals(size, JsonWire.encode(value).length);
        return value;
    }

    /** Retains an exact process/frame exchange for failure assertions. */
    private record Exchange(Process child, byte[] input, int maximum, long timeout) implements Executable {
        /** Runs the unchanged bounded production transport.
         * @throws IOException expected frame or deadline failure
         * @throws InterruptedException expected caller interruption
         */
        @Override
        public void execute() throws IOException, InterruptedException { FrameProcess.exchange(child, input, maximum, timeout); }
    }

    /** Exercises the actual prelaunch serialization bound for either fixed profile. */
    private record Validate(DocumentWorker worker, ObjectNode frame) implements Executable {
        /** Submits the bounded or excessive private context through production orchestration.
         * @throws IOException expected prelaunch size rejection
         * @throws InterruptedException unexpected interruption
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            worker.validate(frame.path("candidate"), frame.path("baseArtifact"), frame.path("ownedIdInventory"), "safety");
        }
    }
}
