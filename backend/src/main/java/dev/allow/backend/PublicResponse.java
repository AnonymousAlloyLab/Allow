package dev.allow.backend;

import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.WriteListener;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import org.springframework.web.util.ContentCachingResponseWrapper;

/** Bounded response staging permits a final capability fence before any body is sent. */
final class PublicResponse extends ContentCachingResponseWrapper {
    private static final int LIMIT = 3145728;
    private ServletOutputStream bounded;
    private PrintWriter writer;

    /** Wraps only an authenticated/enrollment response, never an unbounded stream.
     * @param response original servlet response
     */
    PublicResponse(HttpServletResponse response) { super(response); }

    /** Caps allocation requested by a controller before any bytes reach the stream.
     * @param length declared response bytes
     * @throws IllegalArgumentException declaration exceeds the staging budget
     */
    @Override
    public void setContentLength(int length) { boundedLength(length); super.setContentLength(length); }

    /** Caps the long-form length declaration before Spring resizes its cache.
     * @param length declared response bytes
     * @throws IllegalArgumentException declaration exceeds the staging budget
     */
    @Override
    public void setContentLengthLong(long length) { boundedLength(length); super.setContentLengthLong(length); }

    /** Caps direct buffer-size requests made by response infrastructure.
     * @param size requested bytes
     * @throws IllegalArgumentException request exceeds the staging budget
     */
    @Override
    public void setBufferSize(int size) { boundedLength(size); super.setBufferSize(size); }

    /** Rejects redirects because Spring's inherited implementation publishes before returning.
     * @param location unused redirect destination
     * @throws IOException redirects are not a public API response
     */
    @Override
    public void sendRedirect(String location) throws IOException { throw new IOException("Public API redirects forbidden"); }

    /** Validates allocation limits without truncation or signed overflow.
     * @param size requested byte count
     * @throws IllegalArgumentException invalid cache allocation
     */
    private void boundedLength(long size) {
        if (size < 0 || size > LIMIT) throw new IllegalArgumentException("Public response exceeds limit");
    }

    /** Prevents accidental large controller responses from exhausting staging memory.
     * @return capped cache stream
     * @throws IOException cache unavailable
     */
    @Override
    public ServletOutputStream getOutputStream() throws IOException {
        if (bounded == null) bounded = new BoundedOutput(super.getOutputStream());
        return bounded;
    }

    /** Routes character responses through the same byte cap.
     * @return cached UTF-8 writer
     * @throws IOException unavailable output
     */
    @Override
    public PrintWriter getWriter() throws IOException {
        if (writer == null) writer = new PrintWriter(new OutputStreamWriter(getOutputStream(), StandardCharsets.UTF_8));
        return writer;
    }

    /** Discards encoded and still-buffered characters without publishing either. */
    @Override
    public void resetBuffer() {
        if (writer != null) writer.flush();
        super.resetBuffer();
    }

    /** Clears any character encoder bytes before resetting staged status and headers. */
    @Override
    public void reset() {
        if (writer != null) writer.flush();
        super.reset();
    }

    /** Buffers content-free errors rather than committing an unfenced container response.
     * @param status fixed error status
     */
    @Override
    public void sendError(int status) { resetBuffer(); setStatus(status); }

    /** Suppresses potentially sensitive container exception messages.
     * @param status fixed error status
     * @param message unused diagnostic
     */
    @Override
    public void sendError(int status, String message) { sendError(status); }

    /** Flushes local character encoding before the final publication check.
     * @throws IOException capped character output failed
     */
    void prepare() throws IOException {
        if (writer != null) {
            writer.flush();
            if (writer.checkError()) throw new IOException("Public response output failed");
        }
    }

    /** Counts bytes before delegating to the servlet cache. */
    private static final class BoundedOutput extends ServletOutputStream {
        private final ServletOutputStream output;
        private int size;

        /** Stores the cache stream.
         * @param output bounded destination
         */
        private BoundedOutput(ServletOutputStream output) { this.output = output; }

        /** Writes one byte only within the fixed response ceiling.
         * @param value byte value
         * @throws IOException response too large
         */
        @Override
        public void write(int value) throws IOException {
            if (size >= LIMIT) throw new IOException("Public response exceeds limit");
            size++;
            output.write(value);
        }

        /** Checks a bulk write before allocating it in the cache.
         * @param bytes source bytes
         * @param offset source offset
         * @param length requested count
         * @throws IOException response too large
         */
        @Override
        public void write(byte[] bytes, int offset, int length) throws IOException {
            if (length < 0 || length > LIMIT - size) throw new IOException("Public response exceeds limit");
            size += length;
            output.write(bytes, offset, length);
        }

        /** Reports synchronous readiness.
         * @return whether the cache stream is ready
         */
        @Override
        public boolean isReady() { return output.isReady(); }

        /** Rejects asynchronous publication outside the synchronous authority lease.
         * @param listener unsupported asynchronous writer
         * @throws IllegalStateException asynchronous publication is forbidden
         */
        @Override
        public void setWriteListener(WriteListener listener) { throw new IllegalStateException("Async responses unsupported"); }
    }
}
