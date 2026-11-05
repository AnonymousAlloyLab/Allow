package dev.allow.backend;

import java.util.function.LongSupplier;

/** Synchronized finite token bucket driven only by the server's monotonic clock. */
final class PublicBudget {
    private final double capacity;
    private final double perSecond;
    private final LongSupplier clock;
    private double available;
    private long observed;

    /** Initializes a bounded admission bucket.
     * @param capacity initial and maximum burst
     * @param perSecond refill rate
     * @param clock trusted monotonic time
     */
    PublicBudget(double capacity, double perSecond, LongSupplier clock) {
        this.capacity = capacity;
        this.perSecond = perSecond;
        this.clock = clock;
        available = capacity;
        observed = clock.getAsLong();
    }

    /** Consumes a token without waiting or accumulating unbounded credit.
     * @return whether admission succeeded
     */
    synchronized boolean take() {
        long now = clock.getAsLong();
        available = Math.min(capacity, available + Math.max(0, now - observed) / 1_000_000_000.0 * perSecond);
        observed = now;
        if (available < 1) return false;
        available--;
        return true;
    }
}
