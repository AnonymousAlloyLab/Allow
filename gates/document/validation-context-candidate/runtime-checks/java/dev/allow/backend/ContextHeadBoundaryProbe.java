package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Set;

/** Isolated negative context reply with a valid positive base and an older observed head. */
public final class ContextHeadBoundaryProbe {
    /** Prevents instantiation of the fixture. */
    private ContextHeadBoundaryProbe() { }

    /** Exercises the actual private response validator without a database or live service.
     * @param args no arguments
     * @throws Exception reflection or unexpected validator failure
     * @throws AssertionError a head older than base was accepted
     */
    public static void main(String[] args) throws Exception {
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("documentId", "server:00000000-0000-4000-8000-000000000001")
                .put("baseRevision", 1).put("headObserved", 0);
        data.putObject("artifact");
        data.putObject("ownedIdInventory");
        Method method = DocumentValidationContext.class.getDeclaredMethod("checked", JsonNode.class, String.class,
                long.class, Set.class);
        method.setAccessible(true);
        try {
            method.invoke(null, data, data.path("documentId").textValue(), 1L, Set.of());
            throw new AssertionError("head below base accepted");
        } catch (InvocationTargetException failure) {
            if (!(failure.getCause() instanceof IOException)
                    || !"Validation context identity mismatch".equals(failure.getCause().getMessage())) throw failure;
        }
        System.out.println("PASS baseRevision=1 headObserved=0 denied as unavailable");
    }
}
