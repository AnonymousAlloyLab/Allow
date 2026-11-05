package dev.allow.backend;

import java.io.IOException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.springframework.mock.web.MockHttpServletResponse;
import static org.junit.jupiter.api.Assertions.*;

/** Regression checks for bounded allocation and publication only after the authority fence. */
final class PublicResponseTest {
    private static final int LIMIT = 3145728;

    /** Rejects every explicit cache allocation above the bound before touching the delegate. */
    @Test
    void rejectsOversizedAllocations() {
        for (String operation : new String[]{"int", "long", "buffer"}) {
            MockHttpServletResponse delegate = new MockHttpServletResponse();
            PublicResponse response = new PublicResponse(delegate);
            assertThrows(IllegalArgumentException.class, new Allocation(response, operation, LIMIT + 1L));
            assertThrows(IllegalArgumentException.class, new Allocation(response, operation, -1));
            assertEquals(0, response.getContentSize());
            assertFalse(delegate.isCommitted());
        }
    }

    /** Long allocation requests cannot overflow into an accepted small integer. */
    @Test
    void rejectsLongOverflow() {
        PublicResponse response = new PublicResponse(new MockHttpServletResponse());
        assertThrows(IllegalArgumentException.class, new Allocation(response, "long", Long.MAX_VALUE));
    }

    /** Header declarations never publish content or bypass the actual stream ceiling.
     * @throws IOException unexpected stream failure
     */
    @Test
    void lengthHeadersDoNotBypassWrites() throws IOException {
        for (boolean append : new boolean[]{false, true}) {
            MockHttpServletResponse delegate = new MockHttpServletResponse();
            PublicResponse response = new PublicResponse(delegate);
            if (append) response.addHeader("Content-Length", Integer.toString(LIMIT + 1));
            else response.setHeader("Content-Length", Integer.toString(LIMIT + 1));
            assertThrows(IOException.class, new WriteBytes(response, LIMIT + 1));
            assertEquals(0, response.getContentSize());
            assertEquals(0, delegate.getContentAsByteArray().length);
            assertFalse(delegate.isCommitted());
        }
    }

    /** Exact-limit output remains staged and the next byte is rejected.
     * @throws IOException unexpected stream failure
     */
    @Test
    void streamedOverflowNeverPublishes() throws IOException {
        MockHttpServletResponse delegate = new MockHttpServletResponse();
        PublicResponse response = new PublicResponse(delegate);
        response.getOutputStream().write(new byte[LIMIT]);
        assertThrows(IOException.class, new WriteBytes(response, 1));
        response.flushBuffer();
        assertEquals(LIMIT, response.getContentSize());
        assertEquals(0, delegate.getContentAsByteArray().length);
        assertFalse(delegate.isCommitted());
    }

    /** PrintWriter's swallowed write failure must surface before publication.
     * @throws IOException unexpected writer construction failure
     */
    @Test
    void writerOverflowFailsPreparation() throws IOException {
        MockHttpServletResponse delegate = new MockHttpServletResponse();
        PublicResponse response = new PublicResponse(delegate);
        response.getWriter().write("x".repeat(LIMIT + 1));
        assertThrows(IOException.class, response::prepare);
        assertTrue(response.getContentSize() <= LIMIT);
        assertEquals(0, delegate.getContentAsByteArray().length);
        assertFalse(delegate.isCommitted());
    }

    /** Redirects cannot flush a staged private body or publish their destination.
     * @throws IOException unexpected stream failure
     */
    @Test
    void redirectDoesNotCommit() throws IOException {
        MockHttpServletResponse delegate = new MockHttpServletResponse();
        PublicResponse response = new PublicResponse(delegate);
        response.getOutputStream().write(new byte[]{1, 2, 3});
        assertThrows(IOException.class, new Redirect(response));
        assertEquals(0, delegate.getContentAsByteArray().length);
        assertNull(delegate.getRedirectedUrl());
        assertFalse(delegate.isCommitted());
    }

    /** Container errors discard cached bytes and suppress diagnostic messages.
     * @throws IOException unexpected stream failure
     */
    @Test
    void errorDiscardsStreamedBody() throws IOException {
        MockHttpServletResponse delegate = new MockHttpServletResponse();
        PublicResponse response = new PublicResponse(delegate);
        response.getOutputStream().write(new byte[]{1, 2, 3});
        response.sendError(503, "private diagnostic");
        response.prepare();
        assertEquals(0, response.getContentSize());
        assertEquals(503, delegate.getStatus());
        assertNull(delegate.getErrorMessage());
        assertFalse(delegate.isCommitted());
    }

    /** Pending character encoding must not resurrect discarded private output on error.
     * @throws IOException unexpected writer failure
     */
    @Test
    void errorDiscardsUnflushedWriterBody() throws IOException {
        MockHttpServletResponse delegate = new MockHttpServletResponse();
        PublicResponse response = new PublicResponse(delegate);
        response.getWriter().write("private staged content");
        response.sendError(503);
        response.prepare();
        assertEquals(0, response.getContentSize());
        assertEquals(0, delegate.getContentAsByteArray().length);
        assertFalse(delegate.isCommitted());
    }

    /** Applies one explicit allocation declaration without a lambda. */
    private record Allocation(PublicResponse response, String operation, long size) implements Executable {
        /** Invokes the selected allocation entry point.
         * @throws IllegalArgumentException unknown test allocation operation
         */
        @Override
        public void execute() {
            switch (operation) {
                case "int" -> response.setContentLength((int) size);
                case "long" -> response.setContentLengthLong(size);
                case "buffer" -> response.setBufferSize((int) size);
                default -> throw new IllegalArgumentException("Unknown allocation test");
            }
        }
    }

    /** Performs one capped binary write. */
    private record WriteBytes(PublicResponse response, int size) implements Executable {
        /** Writes the requested bytes.
         * @throws IOException response limit reached
         */
        @Override
        public void execute() throws IOException { response.getOutputStream().write(new byte[size]); }
    }

    /** Exercises the redirect publication escape path. */
    private record Redirect(PublicResponse response) implements Executable {
        /** Attempts an unsupported redirect.
         * @throws IOException expected rejection
         */
        @Override
        public void execute() throws IOException { response.sendRedirect("https://example.invalid/private"); }
    }
}
