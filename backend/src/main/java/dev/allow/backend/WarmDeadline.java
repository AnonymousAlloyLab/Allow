package dev.allow.backend;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/** Monotonic success deadline; expiration never certifies process cleanup. */
final class WarmDeadline {
    private final long started;
    private final long expires;

    /** Starts a bounded operation budget without using a wall clock.
     * @param millis positive duration in milliseconds
     * @throws IllegalArgumentException invalid or excessive duration
     */
    WarmDeadline(long millis) {
        if (millis <= 0 || millis > 30000) throw new IllegalArgumentException("Invalid worker deadline");
        started = System.nanoTime();
        expires = started + TimeUnit.MILLISECONDS.toNanos(millis);
    }

    /** Retains a previously recorded origin instead of restarting an elapsed budget.
     * @param startedNanos original monotonic admission or reservation time
     * @param millis fixed positive budget
     * @return deadline tied to the original origin, including when already expired
     * @throws IllegalArgumentException invalid budget or future origin
     */
    static WarmDeadline fromStart(long startedNanos, long millis) {
        if (millis <= 0 || millis > 30000 || System.nanoTime() - startedNanos < 0) {
            throw new IllegalArgumentException("Invalid original worker deadline");
        }
        return new WarmDeadline(startedNanos, startedNanos + TimeUnit.MILLISECONDS.toNanos(millis));
    }

    /** Stores an already validated monotonic interval.
     * @param startedNanos original start
     * @param expiresNanos fixed expiration
     */
    private WarmDeadline(long startedNanos, long expiresNanos) {
        started = startedNanos;
        expires = expiresNanos;
    }

    /** Rejects cancellation and elapsed budgets before accepting a successful action.
     * @throws IOException elapsed operation budget
     * @throws InterruptedException caller cancellation
     */
    void check() throws IOException, InterruptedException {
        if (Thread.interrupted()) throw new InterruptedException("Worker operation interrupted");
        if (expires - System.nanoTime() <= 0) throw new IOException("Worker operation deadline exceeded");
    }

    /** Returns a bounded wait duration; callers must check again after the wait.
     * @return remaining milliseconds, rounded up only for a submillisecond remainder
     * @throws IOException elapsed operation budget
     * @throws InterruptedException caller cancellation
     */
    long remainingMillis() throws IOException, InterruptedException {
        check();
        return Math.max(1, TimeUnit.NANOSECONDS.toMillis(expires - System.nanoTime()));
    }

    /** Returns the original admission clock for generation-bound ledger checks.
     * @return monotonic admission time
     */
    long startedNanos() { return started; }

    /** Returns the fixed success deadline without resetting its origin.
     * @return monotonic expiration time
     */
    long expiresNanos() { return expires; }
}
