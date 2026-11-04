package dev.allow.worker;

import dev.allow.dto.WorkerRequest;
import dev.allow.dto.WorkerResponse;
import java.io.IOException;
import java.io.PrintStream;
import java.util.Arrays;

/** One-shot child entry point; this class is never a Spring bean. */
public final class WorkerMain {
    /** Prevents construction of the entry point. */
    private WorkerMain() {}

    /**
     * Handles exactly one bounded request and exits.
     * @param arguments unused
     * @throws IOException invalid wire or failed output
     */
    public static void main(String[] arguments) throws IOException {
        PrintStream protocol = System.out;
        System.setOut(System.err);
        byte[] frame = System.in.readNBytes(262145);
        if (frame.length > 262144 || frame.length == 0 || frame[frame.length - 1] != '\n') {
            throw new IOException("Invalid request frame");
        }
        WorkerRequest request = JsonWire.decode(Arrays.copyOf(frame, frame.length - 1), WorkerRequest.class);
        WorkerResponse response = new WorkerResponse(1, new AlloyEngine().execute(request));
        byte[] output = JsonWire.encode(response);
        if (output.length >= 2097152) throw new IOException("Response exceeds limit");
        protocol.write(output);
        protocol.write('\n');
        protocol.flush();
    }
}
