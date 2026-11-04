package dev.allow.backend;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.Callable;

/** Drains one subprocess stream concurrently with the other, with a strict byte cap. */
final class BoundedCapture implements Callable<byte[]> {
    private final InputStream input;
    private final int limit;
    private final JobControl control;

    /**
     * Stores private stream ownership.
     * @param input process stream
     * @param limit bytes allowed
     * @param control kill owner
     */
    BoundedCapture(InputStream input, int limit, JobControl control) {
        this.input = input;
        this.limit = limit;
        this.control = control;
    }

    /**
     * Drains until EOF or kills on overflow.
     * @return complete bytes
     * @throws IOException oversized or failed stream
     */
    @Override
    public byte[] call() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int read;
        while ((read = input.read(buffer)) != -1) {
            if (output.size() + read > limit) {
                control.stop();
                throw new IOException("Worker stream limit exceeded");
            }
            output.write(buffer, 0, read);
        }
        return output.toByteArray();
    }
}
