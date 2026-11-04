package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Exercises delayed warm dispatch without installing a runtime or inventing context authority. */
class WarmAdmissionDeadlineTest {
    private DocumentGateway gateway;
    private DocumentRuntime runtime;
    private JobService jobs;
    private DocumentQueries queries;

    /** Prepares passive dependencies before a test deliberately interrupts its own thread. */
    @BeforeEach
    void prepare() {
        gateway = mock(DocumentGateway.class);
        runtime = mock(DocumentRuntime.class);
        jobs = mock(JobService.class);
        queries = new DocumentQueries(gateway, runtime, jobs);
    }

    /** A dispatch delayed past admission expiry cannot start a pool or resolve a private context.
     * @throws Exception unavailable private dispatch test seam
     */
    @Test
    void expiredAdmissionIsNotRestartedAtDispatch() throws Exception {
        WarmDeadline deadline = WarmDeadline.fromStart(System.nanoTime() - 11_000_000_000L, 10000);
        Throwable cause = rejectedDispatch(deadline);
        assertInstanceOf(IOException.class, cause);
        assertEquals("Worker operation deadline exceeded", cause.getMessage());
    }

    /** Cancellation remains visible before any runtime or context lookup at delayed dispatch.
     * @throws Exception unavailable private dispatch test seam
     */
    @Test
    void cancelledAdmissionCannotStartDispatch() throws Exception {
        WarmDeadline deadline = new WarmDeadline(10000);
        Thread.currentThread().interrupt();
        try { assertInstanceOf(InterruptedException.class, rejectedDispatch(deadline)); }
        finally { Thread.interrupted(); }
    }

    /** Invokes the production warm dispatch with the exact previously captured budget.
     * @param deadline original operation budget
     * @return rejection before any dependency interaction
     * @throws Exception unavailable reflective method
     */
    private Throwable rejectedDispatch(WarmDeadline deadline) throws Exception {
        Method method = DocumentQueries.class.getDeclaredMethod("validateWarm", String.class, long.class,
                JsonNode.class, byte[].class, WarmDeadline.class);
        method.setAccessible(true);
        InvocationTargetException failure = assertThrows(InvocationTargetException.class,
                new Dispatch(method, queries, deadline));
        verifyNoInteractions(gateway, runtime, jobs);
        return failure.getCause();
    }

    /** Carries only a synthetic empty request and an already captured monotonic deadline. */
    private record Dispatch(Method method, DocumentQueries queries, WarmDeadline deadline) implements Executable {
        /** Calls the real private dispatch without enabling pooling or creating a context permit.
         * @throws Exception reflection or the expected wrapped dispatch rejection
         */
        @Override
        public void execute() throws Exception {
            method.invoke(queries, "server:00000000-0000-0000-0000-000000000001", 0L,
                    JsonNodeFactory.instance.objectNode(), new byte[0], deadline);
        }
    }
}
