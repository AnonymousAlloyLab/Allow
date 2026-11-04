package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Controlled real subprocess tests of finite framing and lifetime transport ownership. */
class WarmTransportTest {
    private static final String NONCE = "a3fd8aa2-9632-417b-944f-9029e725d92e";
    private static final String BUILD = "a".repeat(64);
    private static final String READY = "ALLOW-WARM-1 " + NONCE + " " + BUILD + "\n";
    private static final byte[] REQUEST = "{}".getBytes(StandardCharsets.UTF_8);

    /** One exact prelude authorizes one response and never a second request.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void exactReadyAndSingleResponse() throws Exception {
        try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'{}\\n')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            assertTrue(fixture.transport().readyNanos() > 0);
            assertArrayEquals("{}\n".getBytes(StandardCharsets.UTF_8), fixture.transport().exchange(REQUEST, new WarmDeadline(1000)));
            assertThrows(IOException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            assertNull(fixture.failure().value());
            assertFalse(fixture.child().isAlive());
        }
    }

    /** Early, duplicate, oversized and identity-substituted stdout fails before handoff.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void rejectsMalformedStartupAndSameChunkIdleBytes() throws Exception {
        for (String code : List.of("os.write(1,b'early\\n')", "os.write(1,R+R)", "os.write(1,b'x'*257)",
                "os.write(1,R.replace(b'" + NONCE + "',b'00000000-0000-0000-0000-000000000000'))",
                "os.write(1,R.replace(b'" + BUILD + "',b'" + "b".repeat(64) + "'))", "pass")) {
            try (Fixture fixture = launch(code + ";time.sleep(1)")) {
                assertTrue(fixture.failure().await());
                assertThrows(IOException.class, new AwaitReady(fixture.transport(), new WarmDeadline(1000)));
                assertThrows(IOException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            }
        }
    }

    /** Delayed bytes after READY are rejected while no private request has been sent.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void rejectsLateIdleOutput() throws Exception {
        try (Fixture fixture = launch("os.write(1,R);time.sleep(.1);os.write(1,b'late');time.sleep(2)")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            assertTrue(fixture.failure().await());
            assertThrows(IOException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
        }
    }

    /** EOF during startup or idle cannot supply a complete response.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void rejectsPrematureExit() throws Exception {
        for (String code : List.of("pass", "os.write(1,R)")) {
            try (Fixture fixture = launch(code)) {
                assertTrue(fixture.failure().await());
                assertThrows(IOException.class, new AwaitReady(fixture.transport(), new WarmDeadline(1000)));
            }
        }
    }

    /** Truncated, duplicate and over-limit private responses are never returned.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void rejectsMalformedPrivateResponses() throws Exception {
        for (String response : List.of("b'{}'", "b'{}\\n{}\\n'", "b'{}\\r\\n'", "b'x'*1048578", "b''")) {
            try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1," + response + ")")) {
                fixture.transport().awaitReady(new WarmDeadline(1000));
                assertThrows(IOException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            }
        }
    }

    /** A valid private frame cannot override the actual child's unsuccessful exit.
     * @throws Exception failed controlled subprocess or decoder observation
     */
    @Test
    void rejectsValidResponseFromNonzeroExit() throws Exception {
        String response = privateResponse(NONCE);
        assertEquals("VALIDATED", decode(response.getBytes(StandardCharsets.UTF_8), NONCE).path("status").asText());
        try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'"
                + response.replace("\n", "\\n") + "');sys.exit(17)")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            IOException failure = assertThrows(IOException.class,
                    new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            assertEquals("Worker exited without a valid result", failure.getMessage());
            assertFalse(fixture.child().isAlive());
            assertEquals(17, fixture.child().exitValue());
        }
    }

    /** Actual transport bytes with another nonce fail the coordinator's private decoder.
     * @throws Exception failed controlled subprocess or reflective decoder observation
     */
    @Test
    void rejectsWrongPrivateResponseNonce() throws Exception {
        String other = "63b1b599-e97f-420b-8a1b-4be76489af88";
        String response = privateResponse(other);
        try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'"
                + response.replace("\n", "\\n") + "')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            byte[] captured = fixture.transport().exchange(REQUEST, new WarmDeadline(1000));
            assertArrayEquals(response.getBytes(StandardCharsets.UTF_8), captured);
            assertEquals("VALIDATED", decode(captured, other).path("status").asText());
            IOException failure = assertThrows(IOException.class, new PrivateResponse(captured, NONCE));
            assertEquals("Document worker identity mismatch", failure.getMessage());
            assertNull(fixture.failure().value());
            assertFalse(fixture.child().isAlive());
            assertEquals(0, fixture.child().exitValue());
        }
    }

    /** Idle-only stderr overflow poisons the child before any private request handoff.
     * @throws Exception failed controlled subprocess or public fixture synchronization
     */
    @Test
    void rejectsIdleStderrBeyondLifetimeLimit() throws Exception {
        Path directory = Files.createTempDirectory("allow-warm-idle-stderr-");
        Path marker = directory.resolve("ready-observed");
        String code = "os.write(1,R)\nwhile not os.path.exists('" + marker + "'): time.sleep(.005)\n"
                + "os.write(2,b'x'*32769);time.sleep(3)";
        try (Fixture fixture = launch(code)) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            Files.createFile(marker);
            assertTrue(fixture.failure().await());
            assertEquals("Worker stderr exceeds lifetime limit", fixture.failure().value().getMessage());
            assertThrows(IOException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            assertTrue(fixture.child().waitFor(2, TimeUnit.SECONDS));
            assertFalse(fixture.child().isAlive());
        } finally { Files.deleteIfExists(marker); Files.delete(directory); }
    }

    /** The exact capture boundary succeeds while the next byte is denied in another test.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void permitsExactStdoutCaptureLimit() throws Exception {
        try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'x'*1048576+b'\\n')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            assertEquals(1048577, fixture.transport().exchange(REQUEST, new WarmDeadline(1000)).length);
        }
    }

    /** Stderr is charged across startup and request, including the exact 32768-byte boundary.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void enforcesWholeLifetimeStderrCap() throws Exception {
        String first = "os.write(2,b'x'*16000);os.write(1,R);sys.stdin.buffer.read();";
        try (Fixture fixture = launch(first + "os.write(2,b'x'*16768);os.write(1,b'{}\\n')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            assertEquals(3, fixture.transport().exchange(REQUEST, new WarmDeadline(1000)).length);
        }
        try (Fixture fixture = launch(first + "os.write(2,b'x'*16769);os.write(1,b'{}\\n')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            assertThrows(IOException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            assertTrue(fixture.failure().await());
        }
    }

    /** Startup and a blocked large stdin write stay within their caller's finite deadline.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void boundsStartupAndBlockedInput() throws Exception {
        try (Fixture fixture = launch("time.sleep(3)")) {
            assertThrows(IOException.class, new AwaitReady(fixture.transport(), new WarmDeadline(40)));
        }
        try (Fixture fixture = launch("os.write(1,R);time.sleep(3)")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            long start = System.nanoTime();
            assertThrows(IOException.class, new Exchange(fixture.transport(), new byte[1048576], new WarmDeadline(50)));
            assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start) < 1000);
        }
    }

    /** An interrupted caller receives cancellation and owned tasks are joined after child reap.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void interruptionPreventsPrivateHandoff() throws Exception {
        try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'{}\\n')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            Thread.currentThread().interrupt();
            try {
                assertThrows(InterruptedException.class, new Exchange(fixture.transport(), REQUEST, new WarmDeadline(1000)));
            } finally { Thread.interrupted(); }
            assertNull(fixture.failure().value());
            assertTrue(fixture.child().isAlive());
        }
    }

    /** Interruption during an actual blocked write/wait cancels the caller without accepting output.
     * @throws Exception failed controlled subprocess or interrupted test supervisor
     */
    @Test
    void interruptionCancelsBlockedExchange() throws Exception {
        try (Fixture fixture = launch("os.write(1,R);time.sleep(3)")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            InterruptedExchange exchange = new InterruptedExchange(fixture.transport());
            Thread caller = new Thread(exchange, "warm-test-interrupted-caller");
            caller.start();
            try {
                assertTrue(exchange.entered.await(1, TimeUnit.SECONDS));
                Thread.sleep(20);
                caller.interrupt();
                caller.join(1000);
                assertFalse(caller.isAlive());
                assertInstanceOf(InterruptedException.class, exchange.outcome.get());
            } finally { caller.interrupt(); caller.join(2000); }
        }
    }

    /** Invalid input sizes are denied without consuming an otherwise usable idle worker.
     * @throws Exception failed controlled subprocess
     */
    @Test
    void rejectsEmptyAndExclusiveInputLimit() throws Exception {
        try (Fixture fixture = launch("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'{}\\n')")) {
            fixture.transport().awaitReady(new WarmDeadline(1000));
            assertThrows(IOException.class, new Exchange(fixture.transport(), new byte[0], new WarmDeadline(1000)));
            assertThrows(IOException.class, new Exchange(fixture.transport(), new byte[2097152], new WarmDeadline(1000)));
            assertEquals(3, fixture.transport().exchange(REQUEST, new WarmDeadline(1000)).length);
        }
    }

    /** A first stream-close failure still shuts down all tasks and closes remaining streams.
     * @throws Exception failed controlled subprocess or reflective task observation
     */
    @Test
    void closeFailureStillJoinsEveryTransportTask() throws Exception {
        Process child = process("os.write(1,R);sys.stdin.buffer.read();os.write(1,b'{}\\n')");
        WarmTransport transport = new WarmTransport(new CloseFailureProcess(child), NONCE, BUILD, new FailureNote());
        try {
            transport.awaitReady(new WarmDeadline(1000));
            child.destroyForcibly();
            assertTrue(child.waitFor(2, TimeUnit.SECONDS));
            assertThrows(IOException.class, transport::close);
            assertTrue(executor(transport).isTerminated());
        } finally {
            child.destroyForcibly();
            child.waitFor(2, TimeUnit.SECONDS);
            try { transport.close(); } finally { executor(transport).shutdownNow(); }
        }
    }

    /** Starts a fixed public Python fixture without inherited environment or a shell.
     * @param body fixed test-only behavior
     * @return actual child process
     * @throws IOException unavailable fixture interpreter
     */
    private static Process process(String body) throws IOException {
        String script = "import os,sys,time\nR=" + "b'" + READY.replace("\n", "\\n") + "'\n" + body + "\n";
        ProcessBuilder builder = new ProcessBuilder("/usr/bin/python3", "-I", "-c", script);
        builder.environment().clear();
        return builder.start();
    }

    /** Attaches the actual lifetime transport to one controlled child process.
     * @param body fixed test-only child behavior
     * @return owned fixture with guaranteed cleanup
     * @throws IOException unavailable fixture process
     */
    private static Fixture launch(String body) throws IOException {
        Set<String> before = pipeDescriptors();
        Process child = process(body);
        Set<String> owned = pipeDescriptors();
        owned.removeAll(before);
        FailureNote note = new FailureNote();
        return new Fixture(child, new WarmTransport(child, NONCE, BUILD, note), note, owned);
    }

    /** Reads live kernel pipe identities without counting unrelated files or cached descriptors.
     * @return current pipe inode link values
     * @throws IOException unavailable Linux descriptor inventory
     */
    private static Set<String> pipeDescriptors() throws IOException {
        Set<String> result = new HashSet<>();
        try (var files = Files.list(Path.of("/proc/self/fd"))) {
            for (Path path : files.toList()) {
                try {
                    String value = Files.readSymbolicLink(path).toString();
                    if (value.startsWith("pipe:[")) result.add(value);
                } catch (NoSuchFileException closed) { /* Descriptor closed during observation. */ }
            }
        }
        return result;
    }

    /** Observes the private executor solely to verify task termination, never to grant authority.
     * @param transport tested stream owner
     * @return its existing task executor
     * @throws ReflectiveOperationException changed implementation field
     */
    private static ExecutorService executor(WarmTransport transport) throws ReflectiveOperationException {
        Field field = WarmTransport.class.getDeclaredField("tasks");
        field.setAccessible(true);
        return (ExecutorService) field.get(transport);
    }

    /** Supplies a complete public fixture frame accepted by the existing response grammar.
     * @param nonce fixed test operation identity
     * @return one JSON response line
     */
    private static String privateResponse(String nonce) {
        return "{\"protocol\":1,\"requestId\":\"" + nonce + "\",\"status\":\"VALIDATED\",\"data\":{}}\n";
    }

    /** Invokes the actual coordinator decoder without granting a context or pool reservation.
     * @param bytes captured controlled-child response
     * @param nonce admitted identity to require
     * @return actual decoded response
     * @throws Exception actual decoder rejection or changed reflective test boundary
     */
    private static JsonNode decode(byte[] bytes, String nonce) throws Exception {
        Method method = WarmWorkerPool.class.getDeclaredMethod("response", byte[].class, String.class);
        method.setAccessible(true);
        try { return (JsonNode) method.invoke(null, bytes, nonce); }
        catch (InvocationTargetException failure) {
            if (failure.getCause() instanceof IOException rejected) throw rejected;
            throw failure;
        }
    }

    /** Owns a controlled child and ensures transport tasks terminate after exact direct-child reap. */
    private record Fixture(Process child, WarmTransport transport, FailureNote failure, Set<String> pipes) implements AutoCloseable {
        /** Retires the owned fixture and independently checks task and process absence.
         * @throws Exception failed reaping or reader cleanup
         */
        @Override
        public void close() throws Exception {
            child.destroyForcibly();
            assertTrue(child.waitFor(3, TimeUnit.SECONDS));
            transport.close();
            assertFalse(child.isAlive());
            assertTrue(executor(transport).isTerminated());
            Set<String> remaining = pipeDescriptors();
            remaining.retainAll(pipes);
            assertTrue(remaining.isEmpty(), "Owned child pipe descriptors remain open");
        }
    }

    /** Runs one blocked private exchange on an explicitly owned interruptible caller thread. */
    private static final class InterruptedExchange implements Runnable {
        private final WarmTransport transport;
        private final CountDownLatch entered = new CountDownLatch(1);
        private final AtomicReference<Throwable> outcome = new AtomicReference<>();

        /** Retains the controlled stream owner for this single test invocation.
         * @param transport actual owned child transport
         */
        private InterruptedExchange(WarmTransport transport) { this.transport = transport; }

        /** Captures cancellation instead of leaking an exception from the test-owned thread. */
        @Override
        public void run() {
            entered.countDown();
            try {
                transport.exchange(new byte[1048576], new WarmDeadline(2000));
                outcome.set(new AssertionError("Unexpected successful blocked exchange"));
            } catch (Exception failure) { outcome.set(failure); }
        }
    }

    /** Collects one bounded failure notification without performing reader-thread cleanup. */
    private static final class FailureNote implements WarmTransport.FailureSink {
        private final AtomicReference<IOException> result = new AtomicReference<>();
        private final CountDownLatch observed = new CountDownLatch(1);

        /** Records the first sticky failure without blocking its reader.
         * @param failure bounded infrastructure failure
         */
        @Override
        public void failed(IOException failure) { result.compareAndSet(null, failure); observed.countDown(); }

        /** Waits for a finite failure observation.
         * @return whether a failure arrived
         * @throws InterruptedException cancelled fixture
         */
        boolean await() throws InterruptedException { return observed.await(2, TimeUnit.SECONDS); }

        /** Returns the observed infrastructure failure without exposing private output.
         * @return first failure or null
         */
        IOException value() { return result.get(); }
    }

    /** Carries one startup wait into a checked assertion. */
    private record AwaitReady(WarmTransport transport, WarmDeadline deadline) implements Executable {
        /** Executes one bounded readiness wait.
         * @throws IOException expected framing or deadline rejection
         * @throws InterruptedException expected caller cancellation
         */
        @Override
        public void execute() throws IOException, InterruptedException { transport.awaitReady(deadline); }
    }

    /** Carries one private handoff into a checked assertion. */
    private record Exchange(WarmTransport transport, byte[] input, WarmDeadline deadline) implements Executable {
        /** Executes one bounded exchange without bypassing the real transport.
         * @throws IOException expected framing or deadline rejection
         * @throws InterruptedException expected caller cancellation
         */
        @Override
        public void execute() throws IOException, InterruptedException { transport.exchange(input, deadline); }
    }

    /** Carries real captured bytes into the production coordinator's identity validator. */
    private record PrivateResponse(byte[] bytes, String nonce) implements Executable {
        /** Decodes without replacing the production check with test-only comparison logic.
         * @throws Exception expected identity rejection or changed reflective test boundary
         */
        @Override
        public void execute() throws Exception { decode(bytes, nonce); }
    }

    /** Delegates an actual child while injecting one first-close I/O failure. */
    private static final class CloseFailureProcess extends Process {
        private final Process child;
        private final OutputStream input;

        /** Wraps only the child's stdin close path, keeping real stdout, stderr and process state.
         * @param child actual owned subprocess
         */
        private CloseFailureProcess(Process child) {
            this.child = child;
            input = new FailingClose(child.getOutputStream());
        }

        /** Returns the injected stdin wrapper.
         * @return actual child input with one close failure
         */
        @Override
        public OutputStream getOutputStream() { return input; }

        /** Returns the real stdout pipe.
         * @return child output
         */
        @Override
        public InputStream getInputStream() { return child.getInputStream(); }

        /** Returns the real stderr pipe.
         * @return child diagnostics
         */
        @Override
        public InputStream getErrorStream() { return child.getErrorStream(); }

        /** Waits for the real child exit.
         * @return actual exit code
         * @throws InterruptedException interrupted wait
         */
        @Override
        public int waitFor() throws InterruptedException { return child.waitFor(); }

        /** Observes the real exit code.
         * @return child exit code
         */
        @Override
        public int exitValue() { return child.exitValue(); }

        /** Requests termination of this exact controlled child. */
        @Override
        public void destroy() { child.destroyForcibly(); }
    }

    /** Injects exactly one close failure without creating a simulated process or stream reader. */
    private static final class FailingClose extends FilterOutputStream {
        private boolean failed;

        /** Retains the actual child input pipe.
         * @param output real pipe
         */
        private FailingClose(OutputStream output) { super(output); }

        /** Fails once, allowing the fixture's final cleanup to close the real pipe.
         * @throws IOException deliberately injected first-close failure
         */
        @Override
        public void close() throws IOException {
            if (!failed) { failed = true; throw new IOException("Injected first close failure"); }
            super.close();
        }
    }
}
