package dev.allow.backend;

import java.io.IOException;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/** Bounded one-frame process transport with concurrent input/output and unconditional reaping. */
final class FrameProcess {
    /** Prevents construction of the stateless process transport. */
    private FrameProcess() {}

    /** Exchanges one private frame and returns bytes only after successful child exit.
     * @param child newly owned process
     * @param input bounded serialized JSON without a newline
     * @param maximum maximum stdout bytes including framing
     * @param millis external wall deadline
     * @return complete single-line response frame
     * @throws IOException protocol, output, deadline or process failure
     * @throws InterruptedException interrupted caller after unconditional child reaping
     */
    static byte[] exchange(Process child, byte[] input, int maximum, long millis)
            throws IOException, InterruptedException {
        JobControl control = new JobControl();
        control.attach(child);
        ExecutorService tasks = Executors.newFixedThreadPool(3);
        Future<byte[]> output = tasks.submit(new BoundedCapture(child.getInputStream(), maximum, control));
        Future<byte[]> error = tasks.submit(new BoundedCapture(child.getErrorStream(), 32768, control));
        Future<Void> writer = tasks.submit(new Writer(child, input));
        try {
            if (!child.waitFor(millis, TimeUnit.MILLISECONDS)) throw new IOException("Child deadline exceeded");
            byte[] bytes = output.get(2, TimeUnit.SECONDS);
            error.get(2, TimeUnit.SECONDS);
            writer.get(2, TimeUnit.SECONDS);
            if (child.exitValue() != 0) throw new IOException("Child did not return a valid result");
            framing(bytes);
            return bytes;
        } catch (ExecutionException | TimeoutException failure) {
            throw new IOException("Child frame unavailable", failure);
        } finally {
            control.stop();
            reap(child);
            tasks.shutdownNow();
        }
    }

    /** Rejects multiple frames and unterminated protocol output.
     * @param bytes complete captured output
     * @throws IOException invalid framing
     */
    private static void framing(byte[] bytes) throws IOException {
        if (bytes.length < 2 || bytes[bytes.length - 1] != '\n') throw new IOException("Missing response frame");
        for (int index = 0; index < bytes.length - 1; index++) {
            if (bytes[index] == '\n' || bytes[index] == '\r') throw new IOException("Multiple response frames");
        }
    }

    /** Keeps resource ownership until exit, restoring interrupt status afterwards.
     * @param child process that must no longer execute
     */
    static void reap(Process child) {
        boolean interrupted = false;
        while (child.isAlive()) {
            try { child.destroyForcibly(); child.waitFor(); }
            catch (InterruptedException failure) { interrupted = true; }
        }
        try { child.getInputStream().close(); child.getErrorStream().close(); child.getOutputStream().close(); }
        catch (IOException ignored) { /* Exit is confirmed; already closed pipes are harmless. */ }
        if (interrupted) Thread.currentThread().interrupt();
    }

    /** Dedicated writer prevents a blocked child stdin from defeating the wall deadline. */
    private record Writer(Process child, byte[] input) implements Callable<Void> {
        /** Writes the bounded request and closes stdin.
         * @return no result
         * @throws IOException closed or stalled process pipe
         */
        @Override
        public Void call() throws IOException {
            try (var stream = child.getOutputStream()) { stream.write(input); stream.write('\n'); }
            return null;
        }
    }
}
