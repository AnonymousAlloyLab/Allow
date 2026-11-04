package dev.allow.backend;

import java.io.IOException;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Monotonic elapsed-budget and cancellation tests without production clock substitution. */
class WarmDeadlineTest {
    /** Invalid budgets cannot create unbounded or overflowed worker waits. */
    @Test
    void rejectsInvalidBudgets() {
        for (long value : new long[]{0, -1, 30001, Long.MAX_VALUE}) {
            assertThrows(IllegalArgumentException.class, new Create(value));
        }
        assertNotNull(new WarmDeadline(30000));
    }

    /** Remaining waits shrink while the original admission and expiry clocks stay fixed.
     * @throws Exception unexpected clock or interruption failure
     */
    @Test
    void retainsOriginalAdmissionAndExpiry() throws Exception {
        WarmDeadline deadline = new WarmDeadline(1000);
        long start = deadline.startedNanos();
        long expiry = deadline.expiresNanos();
        long first = deadline.remainingMillis();
        Thread.sleep(15);
        assertTrue(deadline.remainingMillis() < first);
        assertEquals(start, deadline.startedNanos());
        assertEquals(expiry, deadline.expiresNanos());
        assertEquals(TimeUnit.MILLISECONDS.toNanos(1000), expiry - start);
    }

    /** Expired budgets reject both acceptance and subsequent wait calculations.
     * @throws Exception unexpected interruption failure
     */
    @Test
    void rejectsAfterExpiration() throws Exception {
        WarmDeadline deadline = new WarmDeadline(10);
        Thread.sleep(30);
        assertThrows(IOException.class, deadline::check);
        assertThrows(IOException.class, deadline::remainingMillis);
    }

    /** Interruption is converted into explicit cancellation before success can be accepted. */
    @Test
    void rejectsCallerCancellation() {
        WarmDeadline deadline = new WarmDeadline(1000);
        Thread.currentThread().interrupt();
        try { assertThrows(InterruptedException.class, deadline::check); }
        finally { Thread.interrupted(); }
    }

    /** Supplies one candidate constructor budget to a checked assertion. */
    private record Create(long millis) implements Executable {
        /** Constructs the actual monotonic deadline. */
        @Override
        public void execute() { new WarmDeadline(millis); }
    }
}
