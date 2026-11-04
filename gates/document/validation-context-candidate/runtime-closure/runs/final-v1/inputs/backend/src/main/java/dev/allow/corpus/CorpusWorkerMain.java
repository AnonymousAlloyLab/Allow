package dev.allow.corpus;

import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.io.PrintStream;
import java.util.Arrays;

/** Dedicated one-shot corpus worker. */
public final class CorpusWorkerMain {
    /** Prevents construction of the entry point. */
    private CorpusWorkerMain() { }

    /** Reads and writes one bounded strict JSON frame.
     * @param args unused
     * @throws IOException invalid input or output
     */
    public static void main(String[] args) throws IOException {
        PrintStream protocol = System.out;
        System.setOut(System.err);
        byte[] frame = System.in.readNBytes(524289);
        if (frame.length == 0 || frame.length > 524288 || frame[frame.length - 1] != '\n') {
            throw new IOException("Invalid frame");
        }
        CorpusRequest request = JsonWire.decode(Arrays.copyOf(frame, frame.length - 1), CorpusRequest.class);
        byte[] output = JsonWire.encode(new CorpusEngine().execute(request));
        if (output.length >= 2097152) throw new IOException("Output limit");
        protocol.write(output);
        protocol.write('\n');
        protocol.flush();
    }
}
