package dev.allow.backend;

import dev.allow.dto.WorkerRequest;
import dev.allow.dto.WorkerResponse;
import dev.allow.worker.JsonWire;

/** Test-only subprocess; production has no environmental forced-status path. */
public final class FakeChild {
    /** Prevents construction of the fixture entry point. */
    private FakeChild() {}

    /**
     * Exercises hostile process behavior.
     * @param arguments test mode
     * @throws Exception fixture I/O
     */
    public static void main(String[] arguments) throws Exception {
        String mode = arguments[0];
        if (mode.equals("SLEEP")) {
            Thread.sleep(30000);
            return;
        }
        if (mode.equals("CRASH")) {
            System.exit(3);
            return;
        }
        WorkerRequest request = JsonWire.decode(System.in.readAllBytes(), WorkerRequest.class);
        if (mode.equals("STDERR")) System.err.print("x".repeat(70000));
        if (mode.equals("STDOUT")) System.out.print("x".repeat(2097153));
        if (mode.equals("DUPKEY")) System.out.println("{\"protocol\":1,\"protocol\":1,\"result\":null}");
        else {
            WorkerResponse response = new WorkerResponse(1, ProcessRunner.outcome(request, "VALIDATED", "Fixture"));
            System.out.write(JsonWire.encode(response));
            if (mode.equals("WHITESPACE")) System.out.print(" ");
            System.out.write('\n');
            if (mode.equals("TRAILING")) System.out.println("{}");
        }
    }
}
