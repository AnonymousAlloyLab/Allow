package dev.allow.egraph;
/** Shared deadline with independent finite counters.
     */
final class RunBudget {
    private final long deadline;
    private long matches;
    private long unions;
    /** Stores the caller's shared monotonic deadline.
     * @param deadline absolute nanosecond deadline
     */
    RunBudget(long deadline) { this.deadline = deadline; }
    /** Checks time before bounded work.
     * @throws Limit when validation or resource checks reject the operation
     */
    void tick() { if (System.nanoTime() >= deadline) throw new Limit("TIME_LIMIT"); }
    /** Charges one matcher expansion.
     * @throws Limit when validation or resource checks reject the operation
     */
    void match() { tick(); if (++matches > 4096) throw new Limit("MATCH_LIMIT"); }
    /** Charges one successful semantic union.
     * @throws Limit when validation or resource checks reject the operation
     */
    void union() { tick(); if (++unions > 1024) throw new Limit("UNION_LIMIT"); }
    /** Returns charged match attempts.
     * @return match count
     */
    long matches() { return matches; }
    /** Returns charged unions.
     * @return union count
     */
    long unions() { return unions; }
    /** Finite exhaustion distinct from failed semantics.
     */
    static final class Limit extends RuntimeException {
        /** Stores a closed termination reason.
     * @param reason limit identifier
     */
        Limit(String reason) { super(reason); }
    }
}
