package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.LongSupplier;
import org.junit.jupiter.api.Test;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Deterministic temporary authority, retention and publication tests without SQL or workers. */
class AnonymousSessionTest {
    /** Distinct capabilities resolve distinct immutable scopes and coordinator objects.
     * @throws Exception fixture setup failure
     */
    @Test
    void separateCapabilitiesAndScopes() throws Exception {
        Fixture fixture = new Fixture();
        AnonymousSessions sessions = fixture.sessions();
        try {
            String first = sessions.create().get("token").toString();
            String second = sessions.create().get("token").toString();
            PublicWorkspace a = sessions.resolve("Bearer " + first);
            PublicWorkspace b = sessions.resolve("Bearer " + second);
            assertNotEquals(first, second);
            assertNotEquals(a.owner(), b.owner());
            assertNotSame(a.queries(), b.queries());
            assertNotSame(a.mutations(), b.mutations());
            assertNotEquals(fixture.scopes.get(0), fixture.scopes.get(1));
            assertFalse(fixture.scopes.toString().contains(first));
            assertFalse(fixture.init.arguments.toString().contains(first));
            assertThrows(PublicFailure.class, new Resolve(sessions, "Bearer " + Hashes.text(first))::run);
        } finally { sessions.close(); }
    }

    /** Definite active reservations consume all four slots without evicting a visitor.
     * @throws Exception fixture setup failure
     */
    @Test
    void fourActiveSlotsRemainBounded() throws Exception {
        Fixture fixture = new Fixture();
        AnonymousSessions sessions = fixture.sessions();
        try {
            List<String> tokens = new ArrayList<>();
            for (int count = 0; count < 4; count++) tokens.add(sessions.create().get("token").toString());
            assertEquals(429, assertThrows(PublicFailure.class, sessions::create).status());
            for (String token : tokens) assertTrue(sessions.resolve("Bearer " + token).live());
        } finally { sessions.close(); }
    }

    /** Unknown initialization outcomes retain capacity instead of claiming SQL absence.
     * @throws Exception fixture setup failure
     */
    @Test
    void uncertainInitializationConsumesSlots() throws Exception {
        Fixture fixture = new Fixture();
        fixture.init.unknown = true;
        AnonymousSessions sessions = fixture.sessions();
        try {
            for (int count = 0; count < 4; count++) {
                assertEquals(503, assertThrows(PublicFailure.class, sessions::create).status());
            }
            assertEquals(429, assertThrows(PublicFailure.class, sessions::create).status());
            assertEquals(4, fixture.scopes.size());
        } finally { sessions.close(); }
    }

    /** Registered orphan scopes whose purge is uncertain remain capacity consuming.
     * @throws Exception fixture setup failure
     */
    @Test
    void restartOrphansRemainQuarantined() throws Exception {
        Fixture fixture = new Fixture();
        ObjectNode registry = response("READY");
        var entries = registry.withObject("data").putArray("workspaces");
        for (int count = 0; count < 4; count++) entries.add(orphan());
        when(fixture.gateway.request(eq("publicList"), any(JsonNode.class))).thenReturn(registry);
        fixture.purgeUnknown = true;
        AnonymousSessions sessions = fixture.sessions();
        try {
            assertEquals(429, assertThrows(PublicFailure.class, sessions::create).status());
            assertEquals(4, fixture.scopes.size());
            verify(fixture.jobs, times(4)).cancelOwner(anyString());
        } finally { sessions.close(); }
    }

    /** Shutdown racing a blocked initializer cannot revive access or permit new reservations.
     * @throws Exception interrupted fixture
     */
    @Test
    void shutdownFencesLateReadyInitialization() throws Exception {
        Fixture fixture = new Fixture();
        fixture.init.blocked = true;
        AnonymousSessions sessions = fixture.sessions();
        Creation work = new Creation(sessions);
        Thread thread = new Thread(work, "anonymous-initialization-fixture");
        thread.start();
        try {
            assertTrue(fixture.init.entered.await(2, TimeUnit.SECONDS));
            sessions.close();
            fixture.init.release.countDown();
            thread.join(2000);
            assertFalse(thread.isAlive());
            assertInstanceOf(PublicFailure.class, work.failure.get());
            assertEquals(503, ((PublicFailure) work.failure.get()).status());
            assertNull(work.result.get());
            assertEquals(503, assertThrows(PublicFailure.class, sessions::create).status());
        } finally {
            fixture.init.release.countDown();
            thread.join(2000);
            sessions.close();
        }
    }

    /** An exact monotonic deadline rejects the formerly valid capability.
     * @throws Exception fixture setup failure
     */
    @Test
    void monotonicExpiryRejectsCapability() throws Exception {
        Fixture fixture = new Fixture();
        AnonymousSessions sessions = fixture.sessions();
        try {
            String token = sessions.create().get("token").toString();
            PublicWorkspace workspace = sessions.resolve("Bearer " + token);
            fixture.clock.now.set(workspace.deadline());
            assertFalse(workspace.live());
            assertEquals(401, assertThrows(PublicFailure.class, new Resolve(sessions, "Bearer " + token)::run).status());
        } finally { sessions.close(); }
    }

    /** A controller's staged model cannot escape after its request crosses expiry.
     * @throws Exception fixture setup failure
     */
    @Test
    void publicationFenceDiscardsLateModel() throws Exception {
        Fixture fixture = new Fixture();
        AnonymousSessions sessions = fixture.sessions();
        try {
            String token = sessions.create().get("token").toString();
            PublicWorkspace workspace = sessions.resolve("Bearer " + token);
            PublicAccess access = new PublicAccess(new AccessMode("ANONYMOUS"), sessions, fixture.jobs);
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/documents");
            request.addHeader("Authorization", "Bearer " + token);
            MockHttpServletResponse accepted = new MockHttpServletResponse();
            assertTrue(access.handle(request, accepted, new ExpiringChain(fixture.clock, workspace.deadline() - 1)));
            assertEquals(200, accepted.getStatus());
            assertTrue(accepted.getContentAsString().contains("PRIVATE_MODEL_SENTINEL"));
            MockHttpServletResponse response = new MockHttpServletResponse();
            assertTrue(access.handle(request, response, new ExpiringChain(fixture.clock, workspace.deadline())));
            assertEquals(401, response.getStatus());
            assertFalse(response.getContentAsString().contains("PRIVATE_MODEL_SENTINEL"));
            assertTrue(response.getContentAsString().contains("SESSION_EXPIRED"));
            assertTrue(workspace.drained());
        } finally { sessions.close(); }
    }

    /** Builds a fixed internal envelope, never a real persistence response.
     * @param status lifecycle result
     * @return trusted fixture envelope
     */
    private static ObjectNode response(String status) {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("status", "OK");
        result.putObject("data").put("status", status);
        return result;
    }

    /** Creates one canonical registry scope that cannot refer to private identity.
     * @return orphan entry
     */
    private static ObjectNode orphan() {
        ObjectNode entry = JsonNodeFactory.instance.objectNode().put("incarnation", UUID.randomUUID().toString())
                .put("expiresAtEpochMillis", 1);
        entry.putObject("scope").put("version", 1).put("principalId", UUID.randomUUID().toString())
                .put("workspaceId", UUID.randomUUID().toString()).put("logicalLaunchId", UUID.randomUUID().toString());
        return entry;
    }

    /** Supplies an explicitly controlled monotonic test clock. */
    private static final class Clock implements LongSupplier {
        private final AtomicLong now = new AtomicLong(1000000000L);
        /** Returns only the test's current monotonic instant.
         * @return controlled nanoseconds
         */
        @Override
        public long getAsLong() { return now.get(); }
    }

    /** Resolves a supplied capability without an inline callback.
     * @param sessions authority registry
     * @param header complete Authorization value
     */
    private record Resolve(AnonymousSessions sessions, String header) {
        /** Attempts authority resolution. */
        void run() { sessions.resolve(header); }
    }

    /** Owns one blocked initialization thread and records outcomes without printing secrets. */
    private static final class Creation implements Runnable {
        private final AnonymousSessions sessions;
        private final AtomicReference<Map<String, Object>> result = new AtomicReference<>();
        private final AtomicReference<Throwable> failure = new AtomicReference<>();
        /** Stores the bounded registry.
         * @param sessions authority owner
         */
        private Creation(AnonymousSessions sessions) { this.sessions = sessions; }
        /** Captures the outcome for the joining test thread. */
        @Override
        public void run() {
            try { result.set(sessions.create()); }
            catch (Throwable error) { failure.set(error); }
        }
    }

    /** Stages a model body and advances time before the final authority check.
     * @param clock controlled clock
     * @param deadline exact expiration
     */
    private record ExpiringChain(Clock clock, long deadline) implements FilterChain {
        /** Simulates accepted internal work completing at expiry.
         * @param request scoped servlet request
         * @param response staged destination
         * @throws IOException broken fixture stream
         */
        @Override
        public void doFilter(ServletRequest request, ServletResponse response) throws IOException {
            response.getWriter().write("PRIVATE_MODEL_SENTINEL");
            clock.now.set(deadline);
        }
    }

    /** Controls initialization certainty and blocks without a real SQL connection. */
    private static final class Initialization implements Answer<JsonNode> {
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private final List<JsonNode> arguments = new ArrayList<>();
        private boolean unknown;
        private boolean blocked;
        /** Captures only server-owned registry arguments and returns a definite or unknown outcome.
         * @param invocation trusted bridge call
         * @return lifecycle envelope
         * @throws InterruptedException interrupted blocking fixture
         * @throws IOException simulated ambiguous SQL outcome
         */
        @Override
        public JsonNode answer(InvocationOnMock invocation) throws InterruptedException, IOException {
            arguments.add(((JsonNode) invocation.getArgument(1)).deepCopy());
            entered.countDown();
            if (blocked && !release.await(2, TimeUnit.SECONDS)) throw new IOException("Fixture timeout");
            if (unknown) throw new IOException("Unknown initialization outcome");
            return response("READY");
        }
    }

    /** Creates independent scoped bridge mocks while retaining no capability values. */
    private static final class Fixture implements Answer<DocumentGateway> {
        private final DocumentGateway gateway = mock(DocumentGateway.class);
        private final DocumentRuntime runtime = mock(DocumentRuntime.class);
        private final JobService jobs = mock(JobService.class);
        private final Clock clock = new Clock();
        private final Initialization init = new Initialization();
        private final List<JsonNode> scopes = new ArrayList<>();
        private boolean purgeUnknown;
        /** Configures only trusted lifecycle operations.
         * @throws Exception checked bridge setup failure
         */
        private Fixture() throws Exception {
            ObjectNode registry = response("READY");
            registry.withObject("data").putArray("workspaces");
            when(gateway.request(eq("publicList"), any(JsonNode.class))).thenReturn(registry);
            when(gateway.scoped(any(JsonNode.class))).thenAnswer(this);
            when(runtime.policy()).thenReturn("document-v1");
            when(jobs.ownerQuiescent(anyString())).thenReturn(true);
            when(jobs.forgetOwner(anyString())).thenReturn(true);
        }
        /** Builds the actual registry with maintenance disabled.
         * @return isolated authority registry
         * @throws Exception checked constructor failure
         */
        private AnonymousSessions sessions() throws Exception {
            return new AnonymousSessions(new AccessMode("ANONYMOUS"), gateway, runtime, jobs,
                    new DeploymentPolicy("https://allow.alloy4.fun", "127.0.0.1:18081", "DEFAULT"), clock, false);
        }
        /** Binds a new bridge to the supplied immutable identity.
         * @param invocation trusted server scope
         * @return independent lifecycle-only mock
         * @throws Throwable checked bridge setup failure
         */
        @Override
        public DocumentGateway answer(InvocationOnMock invocation) throws Throwable {
            scopes.add(((JsonNode) invocation.getArgument(0)).deepCopy());
            DocumentGateway scoped = mock(DocumentGateway.class);
            when(scoped.request(eq("publicInit"), any(JsonNode.class))).thenAnswer(init);
            when(scoped.request(eq("publicPurge"), any(JsonNode.class)))
                    .thenReturn(response(purgeUnknown ? "UNKNOWN" : "PURGED"));
            return scoped;
        }
    }
}
