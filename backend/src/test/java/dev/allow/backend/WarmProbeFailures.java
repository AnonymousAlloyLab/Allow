package dev.allow.backend;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.lang.reflect.Field;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

/** Bounded private failure observations; discarded production exceptions cannot be reconstructed. */
final class WarmProbeFailures {
    /** Prevents construction of the stateless evidence helper. */
    private WarmProbeFailures() {}

    /** Captures bounded retained cause and suppression chains without printing private messages.
     * @param failure actual retained exception
     * @return bounded content-private diagnostic
     */
    static ObjectNode describe(Throwable failure) { return describe(failure, 0, new int[] {0}); }

    /** Limits the complete recursive diagnostic to sixteen nodes and four levels.
     * @param failure current retained exception
     * @param depth current nesting depth
     * @param count shared node counter
     * @return bounded diagnostic with explicit truncation
     */
    private static ObjectNode describe(Throwable failure, int depth, int[] count) {
        ObjectNode value = JsonNodeFactory.instance.objectNode();
        if (failure == null) return value.put("missing", true);
        if (depth >= 4 || count[0]++ >= 16) return value.put("truncated", true);
        String message = String.valueOf(failure.getMessage());
        value.put("type", failure.getClass().getName()).put("message", message.substring(0, Math.min(256, message.length())))
                .put("suppressedCount", failure.getSuppressed().length);
        if (failure.getCause() != null) value.set("cause", describe(failure.getCause(), depth + 1, count));
        ArrayNode suppressed = value.putArray("suppressed");
        Throwable[] errors = failure.getSuppressed();
        for (int index = 0; index < Math.min(2, errors.length); index++) suppressed.add(describe(errors[index], depth + 1, count));
        return value;
    }

    /** Reads current sticky coordinator problems after cleanup, with no inferred discarded cause.
     * @param pool actual coordinator or null before startup
     * @return at most two current retained failures and an explicit observation boundary
     */
    static ObjectNode retained(WarmWorkerPool pool) {
        ObjectNode value = JsonNodeFactory.instance.objectNode()
                .put("boundary", "FIRST_RETAINED_PROBLEM_ONLY_DISCARDED_CAUSES_UNAVAILABLE");
        ArrayNode rows = value.putArray("workers");
        if (pool == null) return value;
        try {
            Field live = WarmWorkerPool.class.getDeclaredField("live");
            live.setAccessible(true);
            for (Object worker : (Set<?>) live.get(pool)) {
                if (rows.size() == 2) { value.put("truncated", true); break; }
                rows.add(retainedWorker((WarmStandby) worker));
            }
        } catch (ReflectiveOperationException failure) { value.set("observationFailure", describe(failure)); }
        return value;
    }

    /** Reads the original token and atomic first problem without modifying either object.
     * @param worker actual currently retained standby
     * @return exact slot/generation plus the currently retained diagnostic
     * @throws ReflectiveOperationException unavailable gate observation fields
     */
    private static ObjectNode retainedWorker(WarmStandby worker) throws ReflectiveOperationException {
        Field tokenField = WarmStandby.class.getDeclaredField("token");
        Field problemField = WarmStandby.class.getDeclaredField("problem");
        tokenField.setAccessible(true);
        problemField.setAccessible(true);
        WorkerReservation token = (WorkerReservation) tokenField.get(worker);
        Throwable problem = (Throwable) ((AtomicReference<?>) problemField.get(worker)).get();
        ObjectNode value = JsonNodeFactory.instance.objectNode().put("slot", token.slot())
                .put("generation", token.generation()).put("phase", token.phase().name());
        value.set("problem", describe(problem));
        return value;
    }
}
