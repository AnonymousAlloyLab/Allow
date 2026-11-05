package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import dev.allow.worker.Hashes;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.function.LongSupplier;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/** Bounded anonymous capability registry; uncertain cleanup continues to consume a slot. */
@Service
final class AnonymousSessions {
    private static final long LIFETIME_SECONDS = 1800;
    private final AccessMode mode;
    private final DocumentGateway gateway;
    private final DocumentRuntime runtime;
    private final JobService jobs;
    private final DeploymentPolicy policy;
    private final LongSupplier clock;
    private final Map<String, PublicWorkspace> reservations = new LinkedHashMap<>();
    private final PublicBudget enrollment;
    private final SecureRandom random = new SecureRandom();
    private final Semaphore cleanup = new Semaphore(1);
    private ScheduledExecutorService maintenance;
    private boolean closed;

    /** Starts public lifecycle reconciliation only for the explicitly selected profile.
     * @param mode closed profile
     * @param gateway private operation-only bridge
     * @param runtime installation ownership and build fence
     * @param jobs shared isolated job budget
     * @param policy exact origin and advisory profile
     * @throws IOException unavailable persistent lifecycle registry
     * @throws InterruptedException interrupted reconciliation
     */
    @Autowired
    AnonymousSessions(AccessMode mode, DocumentGateway gateway, DocumentRuntime runtime,
                      JobService jobs, DeploymentPolicy policy) throws IOException, InterruptedException {
        this(mode, gateway, runtime, jobs, policy, System::nanoTime, true);
    }

    /** Supplies an isolated clock and disables background activity in deterministic tests.
     * @param mode closed profile
     * @param gateway trusted bridge
     * @param runtime installation ownership
     * @param jobs shared jobs
     * @param policy exact routing policy
     * @param clock monotonic time
     * @param background whether to schedule cleanup
     * @throws IOException unavailable lifecycle registry
     * @throws InterruptedException interrupted reconciliation
     */
    AnonymousSessions(AccessMode mode, DocumentGateway gateway, DocumentRuntime runtime,
                      JobService jobs, DeploymentPolicy policy, LongSupplier clock, boolean background)
            throws IOException, InterruptedException {
        this.mode = mode;
        this.gateway = gateway;
        this.runtime = runtime;
        this.jobs = jobs;
        this.policy = policy;
        this.clock = clock;
        enrollment = new PublicBudget(4, 1.0 / 60, clock);
        if (!mode.anonymous()) return;
        if (!policy.origin(0).startsWith("https://") || WarmRuntime.enabled()) {
            throw new IOException("Public profile requires HTTPS deployment and fresh workers");
        }
        runtime.requireReady();
        reconcile();
        if (background) startMaintenance();
    }

    /** Exposes only nonsecret profile and proposed operating bounds.
     * @return bootstrap configuration
     */
    Map<String, Object> configuration() {
        return Map.of("mode", mode.anonymous() ? "ANONYMOUS" : "PRIVATE", "maxSessions", 4,
                "lifetimeSeconds", LIFETIME_SECONDS, "maxDocuments", 3, "workspaceBytes", 16777216);
    }

    /** Allocates authority only after persistent registration and scoped initialization.
     * @return one-time secret and nonsecret expiration label
     * @throws PublicFailure disabled profile, capacity or uncertain initialization
     */
    Map<String, Object> create() {
        if (!mode.anonymous()) throw new PublicFailure(404, "NOT_FOUND");
        String token = token();
        PublicWorkspace workspace = reserve(Hashes.text(token));
        try {
            JsonNode args = JsonNodeFactory.instance.objectNode().put("policyVersion", runtime.policy())
                    .put("expiresAtEpochMillis", workspace.expiresAt()).put("incarnation", workspace.incarnation());
            JsonNode reply = workspace.gateway().request("publicInit", args);
            boolean ready = reply.path("status").asText().equals("OK")
                    && reply.path("data").path("status").asText().equals("READY");
            workspace.provisioned(ready);
            if (!workspace.live()) throw new PublicFailure(503, "WORKSPACE_UNAVAILABLE");
            return Map.of("token", token, "expiresAt", Instant.ofEpochMilli(workspace.expiresAt()).toString(),
                    "lifetimeSeconds", LIFETIME_SECONDS);
        } catch (IOException | InterruptedException | RuntimeException failure) {
            workspace.provisioned(false);
            if (failure instanceof InterruptedException) Thread.currentThread().interrupt();
            throw new PublicFailure(503, "WORKSPACE_UNAVAILABLE");
        }
    }

    /** Reserves quota before any SQL action; never evicts an existing reservation.
     * @param digest token verifier, never its plaintext
     * @return new provisioning workspace
     * @throws PublicFailure closed registry or exhausted enrollment capacity
     */
    private synchronized PublicWorkspace reserve(String digest) {
        if (closed) throw new PublicFailure(503, "WORKSPACE_UNAVAILABLE");
        if (reservations.size() >= 4 || !enrollment.take()) throw new PublicFailure(429, "WORKSPACE_CAPACITY");
        JsonNode scope = freshScope();
        long expires = System.currentTimeMillis() + LIFETIME_SECONDS * 1000;
        long deadline = clock.getAsLong() + TimeUnit.SECONDS.toNanos(LIFETIME_SECONDS);
        PublicWorkspace workspace = workspace(scope, UUID.randomUUID().toString(), expires, deadline);
        jobs.registerOwner(workspace.owner(), deadline);
        reservations.put(digest, workspace);
        return workspace;
    }

    /** Creates fresh immutable scope and separate retained coordinator state.
     * @param scope canonical identity
     * @param incarnation lifecycle registry generation
     * @param expires UTC expiry label
     * @param deadline monotonic deadline
     * @return independent workspace services
     * @throws IllegalArgumentException corrupt trusted registry identity
     */
    private PublicWorkspace workspace(JsonNode scope, String incarnation, long expires, long deadline) {
        validateScope(scope);
        if (!UUID.fromString(incarnation).toString().equals(incarnation)) throw new IllegalArgumentException("Invalid incarnation");
        DocumentGateway scoped = gateway.scoped(scope);
        String owner = scope.path("principalId").asText() + ":" + scope.path("workspaceId").asText();
        return new PublicWorkspace(scope, incarnation, expires, deadline, clock, scoped,
                new DocumentMutations(scoped, runtime), new DocumentQueries(scoped, runtime, jobs, policy, owner));
    }

    /** Checks closed canonical server-owned scope before creating service objects.
     * @param scope trusted private registry identity
     * @throws IllegalArgumentException noncanonical identity
     */
    private void validateScope(JsonNode scope) {
        DocumentJson.fields(scope, "version", "principalId", "workspaceId", "logicalLaunchId");
        if (!scope.path("version").isInt() || scope.path("version").intValue() != 1) throw new IllegalArgumentException("Invalid scope");
        for (String name : List.of("principalId", "workspaceId", "logicalLaunchId")) {
            String value = scope.path(name).asText();
            if (!UUID.fromString(value).toString().equals(value)) throw new IllegalArgumentException("Invalid scope");
        }
    }

    /** Resolves one exact opaque bearer without consulting browser-selected identifiers.
     * @param authorization complete unique Authorization header
     * @return active immutable workspace
     * @throws PublicFailure absent or expired capability
     */
    synchronized PublicWorkspace resolve(String authorization) {
        if (closed || authorization == null || !authorization.matches("Bearer [A-Za-z0-9_-]{43}")) {
            throw new PublicFailure(401, "SESSION_EXPIRED");
        }
        PublicWorkspace workspace = reservations.get(Hashes.text(authorization.substring(7)));
        if (workspace == null || !workspace.live()) throw new PublicFailure(401, "SESSION_EXPIRED");
        return workspace;
    }

    /** Revokes old capabilities and reconciles only registered anonymous scopes.
     * @throws IOException malformed or unavailable persistent registry
     * @throws InterruptedException interrupted lifecycle query
     */
    private void reconcile() throws IOException, InterruptedException {
        JsonNode envelope = gateway.request("publicList", JsonNodeFactory.instance.objectNode());
        JsonNode entries = envelope.path("data").path("workspaces");
        if (!envelope.path("status").asText().equals("OK")
                || !envelope.path("data").path("status").asText().equals("READY")
                || !entries.isArray() || entries.size() > 4) {
            throw new IOException("Public lifecycle registry unavailable");
        }
        for (JsonNode entry : entries) {
            PublicWorkspace workspace = workspace(entry.path("scope"), entry.path("incarnation").asText(),
                    entry.path("expiresAtEpochMillis").longValue(), clock.getAsLong());
            workspace.provisioned(false);
            reservations.put("orphan:" + workspace.owner(), workspace);
        }
        maintain();
    }

    /** Retires expired capabilities and releases capacity only on a definite purge receipt. */
    void maintain() {
        if (!cleanup.tryAcquire()) return;
        try {
            for (PublicWorkspace workspace : snapshot()) {
                if (!workspace.retiring()) continue;
                workspace.retire();
                jobs.cancelOwner(workspace.owner());
                if (!workspace.drained() || !jobs.ownerQuiescent(workspace.owner())) continue;
                if (purge(workspace) && jobs.forgetOwner(workspace.owner())) release(workspace);
            }
        } finally { cleanup.release(); }
    }

    /** Takes a bounded snapshot without holding the enrollment lock across SQL.
     * @return currently reserved scopes
     */
    private synchronized List<PublicWorkspace> snapshot() { return new ArrayList<>(reservations.values()); }

    /** Releases exactly the purged reservation, never another visitor's capacity.
     * @param workspace definitely purged workspace object
     */
    private synchronized void release(PublicWorkspace workspace) { reservations.values().remove(workspace); }

    /** Requests guarded transactional deletion; any ambiguity retains the reservation.
     * @param workspace revoked and drained scope
     * @return definite registered-scope deletion or absence
     */
    private boolean purge(PublicWorkspace workspace) {
        try {
            JsonNode args = JsonNodeFactory.instance.objectNode().put("incarnation", workspace.incarnation());
            JsonNode reply = workspace.gateway().request("publicPurge", args);
            return reply.path("status").asText().equals("OK")
                    && java.util.Set.of("PURGED", "ABSENT").contains(reply.path("data").path("status").asText());
        } catch (IOException | RuntimeException failure) {
            return false;
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    /** Creates a cryptographically unpredictable one-time capability.
     * @return URL-safe secret, never written to disk or logs
     */
    private String token() {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    /** Allocates independent principal, workspace and launch identities.
     * @return closed internal scope
     */
    private JsonNode freshScope() {
        return JsonNodeFactory.instance.objectNode().put("version", 1)
                .put("principalId", UUID.randomUUID().toString()).put("workspaceId", UUID.randomUUID().toString())
                .put("logicalLaunchId", UUID.randomUUID().toString());
    }

    /** Starts one daemon cleanup task, never one thread per visitor. */
    private void startMaintenance() {
        maintenance = Executors.newSingleThreadScheduledExecutor(new MaintenanceThread());
        maintenance.scheduleWithFixedDelay(new Maintenance(this), 30, 30, TimeUnit.SECONDS);
    }

    /** Revokes authority during shutdown; persisted registry retains unfinished cleanup. */
    @PreDestroy
    synchronized void close() {
        closed = true;
        if (maintenance != null) maintenance.shutdownNow();
        for (PublicWorkspace workspace : reservations.values()) {
            workspace.retire();
            jobs.cancelOwner(workspace.owner());
        }
    }

    /** Documented scheduler command keeps cleanup errors content-free and capacity retained. */
    private record Maintenance(AnonymousSessions owner) implements Runnable {
        /** Attempts bounded cleanup without terminating future maintenance on one failure. */
        @Override
        public void run() {
            try { owner.maintain(); }
            catch (RuntimeException failure) { /* Retain all uncertain reservations. */ }
        }
    }

    /** Creates the single private daemon maintenance thread. */
    private static final class MaintenanceThread implements ThreadFactory {
        /** Names a daemon without inheriting any per-request authority.
         * @param work fixed cleanup command
         * @return daemon thread
         */
        @Override
        public Thread newThread(Runnable work) {
            Thread thread = new Thread(work, "allow-public-cleanup");
            thread.setDaemon(true);
            return thread;
        }
    }
}
