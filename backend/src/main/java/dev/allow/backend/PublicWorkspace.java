package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.servlet.http.HttpServletRequest;
import java.util.function.LongSupplier;

/** Immutable scope and independently retained coordinators for one temporary capability. */
final class PublicWorkspace {
    private static final String ATTRIBUTE = PublicWorkspace.class.getName();
    private final String owner;
    private final String incarnation;
    private final long expiresAt;
    private final long deadline;
    private final LongSupplier clock;
    private final DocumentGateway gateway;
    private final DocumentMutations mutations;
    private final DocumentQueries queries;
    private boolean active;
    private boolean revoked;
    private boolean provisioning = true;
    private boolean expensive;
    private int requests;

    /** Binds all retained document state to an immutable server-created scope.
     * @param scope trusted identity
     * @param incarnation registry ownership generation
     * @param expiresAt absolute UTC expiry label
     * @param deadline monotonic authorization deadline
     * @param clock trusted clock
     * @param gateway scoped persistence bridge
     * @param mutations scoped command coordinator
     * @param queries scoped query coordinator
     */
    PublicWorkspace(JsonNode scope, String incarnation, long expiresAt, long deadline, LongSupplier clock,
                    DocumentGateway gateway, DocumentMutations mutations, DocumentQueries queries) {
        owner = scope.path("principalId").asText() + ":" + scope.path("workspaceId").asText();
        this.incarnation = incarnation;
        this.expiresAt = expiresAt;
        this.deadline = deadline;
        this.clock = clock;
        this.gateway = gateway;
        this.mutations = mutations;
        this.queries = queries;
    }

    /** Resolves only the object installed by the authority filter.
     * @param request current servlet request
     * @return trusted scope, or null for the private profile
     */
    static PublicWorkspace from(HttpServletRequest request) {
        Object value = request.getAttribute(ATTRIBUTE);
        return value instanceof PublicWorkspace workspace ? workspace : null;
    }

    /** Attaches already-resolved authority; client headers never choose this object.
     * @param request authenticated current request
     */
    void attach(HttpServletRequest request) { request.setAttribute(ATTRIBUTE, this); }

    /** Completes provisioning while retaining expired or failed reservations.
     * @param success whether initialization returned a definite READY receipt
     */
    synchronized void provisioned(boolean success) {
        provisioning = false;
        active = success && !revoked && clock.getAsLong() - deadline < 0;
    }

    /** Resolves current authority at its monotonic deadline.
     * @return whether new operations and publication are permitted
     */
    synchronized boolean live() { return active && clock.getAsLong() - deadline < 0; }

    /** Revokes access immediately without claiming that workers or rows are absent. */
    synchronized void retire() { revoked = true; active = false; }

    /** Separates provisioning from a revoked scope ready to begin draining.
     * @return whether retirement can cancel owned work
     */
    synchronized boolean retiring() { return !provisioning && !live(); }

    /** Reserves bounded concurrent work without a waiting queue.
     * @param costly whether this operation can start validation or solver work
     * @param jobs shared job owner
     * @return whether this request acquired a lease
     */
    synchronized boolean enter(boolean costly, JobService jobs) {
        if (!live() || requests >= 2 || (costly && (expensive || jobs.ownerBusy(owner)))) return false;
        requests++;
        if (costly) expensive = true;
        return true;
    }

    /** Releases only the request reservation held by this filter invocation.
     * @param costly whether this lease reserved the expensive-operation lane
     * @throws IllegalStateException caller does not own a reservation
     */
    synchronized void leave(boolean costly) {
        if (requests <= 0) throw new IllegalStateException("Missing public request owner");
        requests--;
        if (costly) expensive = false;
    }

    /** Checks Java-owned drain evidence before privileged SQL cleanup is attempted.
     * @return whether this revoked scope has no unresolved Java operation
     */
    synchronized boolean drained() {
        return !provisioning && !live() && requests == 0 && mutations.cleanupSafe() && queries.cleanupSafe();
    }

    /** Returns the immutable server-derived owner key.
     * @return internal owner identity
     */
    String owner() { return owner; }

    /** Returns the persistent lifecycle generation.
     * @return canonical private UUID
     */
    String incarnation() { return incarnation; }

    /** Returns a nonsecret UTC expiry for presentation.
     * @return epoch milliseconds
     */
    long expiresAt() { return expiresAt; }

    /** Returns the clock-bound job deadline.
     * @return monotonic nanoseconds
     */
    long deadline() { return deadline; }

    /** Returns a conservative remaining lifetime for presentation.
     * @return whole seconds remaining under the server clock
     */
    long remainingSeconds() {
        return Math.max(0, java.util.concurrent.TimeUnit.NANOSECONDS.toSeconds(deadline - clock.getAsLong()));
    }

    /** Returns the immutable scope's persistence bridge.
     * @return private bridge
     */
    DocumentGateway gateway() { return gateway; }

    /** Returns only this workspace's command coordinator.
     * @return scoped mutable command state
     */
    DocumentMutations mutations() { return mutations; }

    /** Returns only this workspace's query coordinator.
     * @return scoped analysis retention
     */
    DocumentQueries queries() { return queries; }
}
