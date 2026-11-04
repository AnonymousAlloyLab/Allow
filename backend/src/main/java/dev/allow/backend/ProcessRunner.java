package dev.allow.backend;

import dev.allow.dto.*;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.concurrent.*;

/** Supervises one child through exit, strict wire validation and unconditional reaping. */
final class ProcessRunner implements JobRunner {
    private static final Set<String> TERMINAL = Set.of("VALIDATED", "SAT", "UNSAT", "INVALID",
            "UNSUPPORTED", "UNKNOWN", "ERROR", "TIMEOUT", "CANCELLED");
    private final SandboxLauncher launcher;
    private final long timeoutMillis;

    /**
     * Stores a trusted launch implementation and deadline.
     * @param launcher sandbox-only launcher
     * @param timeoutMillis wall deadline
     */
    ProcessRunner(SandboxLauncher launcher, long timeoutMillis) {
        this.launcher = launcher;
        this.timeoutMillis = timeoutMillis;
    }

    /**
     * Identifies the pinned sandbox build and supervisor protocol.
     * @return exact worker context
     */
    @Override
    public String identity() {
        return launcher.identity() + ":protocol1:deadline" + timeoutMillis;
    }

    /**
     * Returns only validated terminal data after child exit.
     * @param request identity
     * @param control cancellation
     * @return terminal result
     * @throws Exception failed launch or protocol
     * @throws IOException invalid worker exit or wire
     */
    @Override
    public JobView execute(WorkerRequest request, JobControl control) throws Exception {
        WorkerCapacity.acquire();
        try {
            return runOwned(request, control);
        } finally {
            WorkerCapacity.release();
        }
    }

    /** Executes under the shared principal permit until sandbox exit.
     * @param request identity-bound job
     * @param control cancellation owner
     * @return bounded terminal response
     * @throws Exception child or protocol failure
     * @throws IOException invalid child exit or protocol frame
     */
    private JobView runOwned(WorkerRequest request, JobControl control) throws Exception {
        try (OwnedWorkerRun owned = new OwnedWorkerRun(launcher)) {
            return exchangeOwned(request, control, owned, owned.launch());
        }
    }

    /** Exchanges the existing solver protocol while retaining optional shared tree ownership.
     * @param request exact solver request
     * @param control existing cancellation owner
     * @param owned retained launch and cleanup lease
     * @param process directly owned sandbox process
     * @return complete existing solver result
     * @throws Exception stream, process or protocol failure
     * @throws IOException invalid process exit
     */
    private JobView exchangeOwned(WorkerRequest request, JobControl control, OwnedWorkerRun owned,
            Process process) throws Exception {
        control.attach(process);
        ExecutorService readers = Executors.newFixedThreadPool(3);
        owned.beginTransport();
        try {
            Future<byte[]> stdout = readers.submit(new BoundedCapture(process.getInputStream(), 2097152, control));
            Future<byte[]> stderr = readers.submit(new BoundedCapture(process.getErrorStream(), 65536, control));
            Future<Void> stdin = readers.submit(new FrameWriter(process, request, control));
            if (!process.waitFor(timeoutMillis, TimeUnit.MILLISECONDS)) {
                return outcome(request, "TIMEOUT", "Worker deadline exceeded.");
            }
            if (control.cancelled()) return outcome(request, "CANCELLED", "Cancelled.");
            byte[] frame = stdout.get(2, TimeUnit.SECONDS);
            stderr.get(2, TimeUnit.SECONDS);
            stdin.get(2, TimeUnit.SECONDS);
            if (process.exitValue() != 0) throw new IOException("Worker exited without a valid result");
            return decode(frame, request);
        } finally {
            finishExchange(process, control, readers, owned);
        }
    }

    /** Confirms managed stream tasks before the surrounding process-tree lease can release.
     * @param process owned direct child
     * @param control existing cancellation owner
     * @param readers owned stream executor
     * @param owned shared containment lease
     * @throws IOException managed transport task termination remains uncertain
     */
    private void finishExchange(Process process, JobControl control, ExecutorService readers,
            OwnedWorkerRun owned) throws IOException {
        control.stop();
        reap(process);
        closeStreams(process);
        readers.shutdownNow();
        if (owned.managed()) { FrameProcess.awaitTasks(readers); owned.transportFinished(); }
    }

    /** Writer runs beside readers so stalled stdin cannot evade the deadline. */
    private record FrameWriter(Process process, WorkerRequest request, JobControl control) implements Callable<Void> {
        /**
     * Sends one frame and closes stdin.
     * @return no value
     * @throws IOException oversized or failed pipe
     */
        @Override
        public Void call() throws IOException {
            byte[] input = JsonWire.encode(request);
            if (input.length >= 262144) throw new IOException("Worker input limit exceeded");
            try (var output = process.getOutputStream()) {
                output.write(input);
                output.write('\n');
            } catch (IOException error) {
                control.stop();
                throw error;
            }
            return null;
        }
    }

    /**
     * Validates framing, schema and echoed identity.
     * @param frame full stdout
     * @param request expected identity
     * @return response
     * @throws IOException malformed output
     */
    private JobView decode(byte[] frame, WorkerRequest request) throws IOException {
        if (frame.length < 2 || frame[frame.length - 1] != '\n') throw new IOException("Invalid worker frame");
        for (int index = 0; index < frame.length - 1; index++) {
            if (frame[index] == '\n' || frame[index] == '\r') throw new IOException("Multiple worker frames");
        }
        WorkerResponse envelope = JsonWire.decode(Arrays.copyOf(frame, frame.length - 1), WorkerResponse.class);
        if (!Arrays.equals(JsonWire.encode(envelope), Arrays.copyOf(frame, frame.length - 1))) {
            throw new IOException("Noncanonical worker frame");
        }
        JobView result = envelope.result();
        if (envelope.protocol() != 1 || result == null || !TERMINAL.contains(result.status())
                || !request.jobId().equals(result.jobId()) || !request.sourceHash().equals(result.sourceHash())
                || !request.analysisKey().equals(result.analysisKey()) || request.revision() != result.revision()
                || request.epoch() != result.epoch()) throw new IOException("Worker identity mismatch");
        return result;
    }

    /**
     * Closes all pipes after child reaping, unblocking remaining drain tasks.
     * @param process owned child
     */
    private void closeStreams(Process process) {
        try {
            process.getInputStream().close();
            process.getErrorStream().close();
            process.getOutputStream().close();
        } catch (IOException ignored) {
            // Confirmed child exit makes an already closed pipe harmless.
        }
    }

    /**
     * Keeps the permit until the sandbox has actually exited.
     * @param process owned child
     */
    private void reap(Process process) {
        boolean interrupted = false;
        while (process.isAlive()) {
            try {
                process.destroyForcibly();
                process.waitFor();
            } catch (InterruptedException error) {
                interrupted = true;
            }
        }
        if (interrupted) Thread.currentThread().interrupt();
    }

    /**
     * Creates supervisor-only failure status without inventing evidence.
     * @param request identity
     * @param status terminal status
     * @param message explanation
     * @return empty evidence
     */
    static JobView outcome(WorkerRequest request, String status, String message) {
        return new JobView(request.jobId(), status, request.sourceHash(), request.revision(), request.epoch(),
                request.analysisKey(), null, message, List.of(), null, null);
    }
}
