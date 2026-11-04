package dev.allow.backend;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/** Sole lifetime stream owner for one READY prelude and one private response. */
final class WarmTransport implements AutoCloseable {
    /** Receives sticky protocol failures without waiting for cleanup on a reader thread. */
    interface FailureSink {
        /** Marks the owned generation failed; cleanup remains its supervisor's responsibility.
         * @param failure bounded protocol failure without captured private output
         */
        void failed(IOException failure);
    }

    private enum Phase { STARTUP, IDLE, REQUEST, COMPLETE, FAILED, CLOSED }
    private final Process child;
    private final FailureSink failures;
    private final String expectedReady;
    private final ExecutorService tasks = Executors.newFixedThreadPool(3);
    private final CompletableFuture<Void> ready = new CompletableFuture<>();
    private final ByteArrayOutputStream prelude = new ByteArrayOutputStream(128);
    private ByteArrayOutputStream response = new ByteArrayOutputStream(8192);
    private final Future<Void> output;
    private final Future<Void> error;
    private Phase phase = Phase.STARTUP;
    private IOException problem;
    private long readyNanos;

    /** Starts both readers before the public bootstrap barrier is released.
     * @param child directly owned helper/bubblewrap process
     * @param nonce generation-bound canonical worker nonce
     * @param image expected complete image identity
     * @param failures nonblocking sticky-failure listener
     */
    WarmTransport(Process child, String nonce, String image, FailureSink failures) {
        this.child = child;
        this.failures = failures;
        expectedReady = "ALLOW-WARM-1 " + nonce + " " + image + "\n";
        output = tasks.submit(this::readOutput);
        error = tasks.submit(this::drainError);
    }

    /** Waits for the exact bounded prelude without starting a private request.
     * @param deadline original reservation startup deadline
     * @throws IOException malformed, failed or late readiness
     * @throws InterruptedException cancelled startup
     */
    void awaitReady(WarmDeadline deadline) throws IOException, InterruptedException {
        await(ready, deadline);
        synchronized (this) {
            checkProblem();
            if (phase != Phase.IDLE) throw new IOException("Worker is not idle and ready");
        }
        deadline.check();
    }

    /** Returns the observed readiness clock used for the fixed idle expiry.
     * @return monotonic READY time, or zero before readiness
     */
    synchronized long readyNanos() { return readyNanos; }

    /** Sends exactly one private frame after the caller has consumed its CLEAN permit.
     * @param input bounded serialized request without a trailing newline
     * @param deadline original admission success deadline
     * @return complete framed private response after successful direct-child exit
     * @throws IOException protocol, stream, deadline or process failure
     * @throws InterruptedException cancelled request
     */
    byte[] exchange(byte[] input, WarmDeadline deadline) throws IOException, InterruptedException {
        deadline.check();
        beginRequest(input);
        Future<Void> writer = tasks.submit(new Writer(child, input));
        if (!child.waitFor(deadline.remainingMillis(), TimeUnit.MILLISECONDS)) {
            throw new IOException("Worker request deadline exceeded");
        }
        deadline.check();
        await(writer, deadline);
        await(output, deadline);
        await(error, deadline);
        if (child.exitValue() != 0) throw new IOException("Worker exited without a valid result");
        byte[] bytes = completedResponse();
        framing(bytes);
        deadline.check();
        return bytes;
    }

    /** Atomically rejects reuse, known failures and oversized private input.
     * @param input encoded private request
     * @throws IOException failed phase, reused worker or excessive input
     */
    private synchronized void beginRequest(byte[] input) throws IOException {
        checkProblem();
        if (phase != Phase.IDLE || input.length == 0 || input.length >= 2097152) {
            throw new IOException("Invalid one-use worker handoff");
        }
        phase = Phase.REQUEST;
    }

    /** Drains stdout continuously, including the period when the worker is idle.
     * @return no retained reader result
     * @throws IOException malformed phase output or failed stream
     */
    private Void readOutput() throws IOException {
        try {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = child.getInputStream().read(buffer)) != -1) accept(buffer, count);
            finishOutput();
            return null;
        } catch (IOException failure) {
            fail(failure);
            throw failure;
        }
    }

    /** Applies the prelude and response caps under the same handoff phase monitor.
     * @param bytes newly read stdout bytes
     * @param count number of available bytes
     * @throws IOException unexpected idle output or excessive framing data
     */
    private synchronized void accept(byte[] bytes, int count) throws IOException {
        int offset = 0;
        while (offset < count && phase == Phase.STARTUP) acceptPrelude(bytes[offset++]);
        if (offset == count) return;
        if (phase != Phase.REQUEST) throw reject("Unexpected output outside private request");
        if (response.size() + count - offset > 1048577) throw reject("Worker response exceeds limit");
        response.write(bytes, offset, count - offset);
    }

    /** Checks a single bounded ASCII readiness line without reading beyond its delimiter.
     * @param value next stdout byte
     * @throws IOException malformed or oversized readiness
     */
    private void acceptPrelude(byte value) throws IOException {
        if (prelude.size() == 256) throw reject("Worker readiness exceeds limit");
        prelude.write(value);
        if (value != '\n') return;
        if (!expectedReady.equals(prelude.toString(StandardCharsets.US_ASCII))) {
            throw reject("Worker readiness identity mismatch");
        }
        readyNanos = System.nanoTime();
        phase = Phase.IDLE;
        ready.complete(null);
    }

    /** Records EOF only after a request has been handed off.
     * @throws IOException premature or unrelated EOF
     */
    private synchronized void finishOutput() throws IOException {
        if (phase == Phase.CLOSED) return;
        if (phase != Phase.REQUEST) throw reject("Worker exited outside private request");
        phase = Phase.COMPLETE;
    }

    /** Counts and discards stderr under one lifetime cap without retaining model text.
     * @return no retained stderr content
     * @throws IOException stream failure or excess lifetime stderr
     */
    private Void drainError() throws IOException {
        try {
            byte[] buffer = new byte[4096];
            int total = 0;
            int count;
            while ((count = child.getErrorStream().read(buffer)) != -1) {
                total += count;
                if (total > 32768) throw new IOException("Worker stderr exceeds lifetime limit");
            }
            return null;
        } catch (IOException failure) {
            fail(failure);
            throw failure;
        }
    }

    /** Marks a protocol rejection before releasing the phase monitor.
     * @param message bounded infrastructure-only explanation
     * @return sticky failure for the current reader
     */
    private IOException reject(String message) {
        if (problem == null) problem = new IOException(message);
        phase = Phase.FAILED;
        ready.completeExceptionally(problem);
        return problem;
    }

    /** Signals failure without performing a self-joining cleanup on the reader thread.
     * @param failure infrastructure-only failure
     */
    private void fail(IOException failure) {
        synchronized (this) {
            if (phase == Phase.CLOSED) return;
            if (problem == null) problem = failure;
            phase = Phase.FAILED;
            ready.completeExceptionally(problem);
        }
        child.destroyForcibly();
        failures.failed(failure);
    }

    /** Rejects any previously observed protocol failure.
     * @throws IOException sticky generation failure
     */
    private void checkProblem() throws IOException {
        if (problem != null) throw problem;
    }

    /** Copies the complete private result only after the reader has reached valid EOF.
     * @return defensive response bytes
     * @throws IOException premature or failed response
     */
    private synchronized byte[] completedResponse() throws IOException {
        checkProblem();
        if (phase != Phase.COMPLETE) throw new IOException("Worker response is incomplete");
        return response.toByteArray();
    }

    /** Requires exactly one newline-terminated private response.
     * @param bytes full captured response
     * @throws IOException missing delimiter or multiple frames
     */
    private static void framing(byte[] bytes) throws IOException {
        if (bytes.length < 2 || bytes[bytes.length - 1] != '\n') throw new IOException("Missing worker frame");
        for (int index = 0; index < bytes.length - 1; index++) {
            if (bytes[index] == '\n' || bytes[index] == '\r') throw new IOException("Multiple worker frames");
        }
    }

    /** Waits only within the original deadline and rechecks after task completion.
     * @param future owned transport task
     * @param deadline original success budget
     * @param <T> task result type
     * @return completed task result
     * @throws IOException failed task or elapsed budget
     * @throws InterruptedException caller cancellation
     */
    private static <T> T await(Future<T> future, WarmDeadline deadline) throws IOException, InterruptedException {
        try {
            T result = future.get(deadline.remainingMillis(), TimeUnit.MILLISECONDS);
            deadline.check();
            return result;
        } catch (ExecutionException | TimeoutException failure) {
            throw new IOException("Worker transport unavailable", failure);
        }
    }

    /** Closes streams after owned process termination and requires reader task completion.
     * @throws IOException stream closure failure or retained reader task
     * @throws InterruptedException interrupted cleanup, which must retain ownership
     */
    @Override
    public void close() throws IOException, InterruptedException {
        synchronized (this) {
            phase = Phase.CLOSED;
            ready.completeExceptionally(new IOException("Worker transport closed"));
        }
        IOException closureFailure = null;
        try { closeStreams(); }
        catch (IOException failure) { closureFailure = failure; }
        finally { tasks.shutdownNow(); }
        if (!tasks.awaitTermination(2, TimeUnit.SECONDS)) throw new IOException("Worker readers remain active");
        synchronized (this) { response = new ByteArrayOutputStream(0); prelude.reset(); }
        if (closureFailure != null) throw closureFailure;
    }

    /** Attempts every stream closure even when an earlier close fails.
     * @throws IOException at least one owned stream did not close normally
     */
    private void closeStreams() throws IOException {
        IOException failure = null;
        for (AutoCloseable stream : new AutoCloseable[]{child.getOutputStream(), child.getInputStream(), child.getErrorStream()}) {
            try { stream.close(); }
            catch (Exception error) {
                if (failure == null) failure = new IOException("Worker stream closure failed", error);
                else failure.addSuppressed(error);
            }
        }
        if (failure != null) throw failure;
    }

    /** Owns the sole private write and closes stdin after its one complete frame. */
    private record Writer(Process child, byte[] input) implements Callable<Void> {
        /** Writes one frame without retaining an open request stream.
         * @return no result
         * @throws IOException closed or failed child input
         */
        @Override
        public Void call() throws IOException {
            try (var stream = child.getOutputStream()) {
                stream.write(input);
                stream.write('\n');
            }
            return null;
        }
    }
}
