package dev.allow.backend;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Flow;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import static org.junit.jupiter.api.Assertions.*;

/** Isolated admission tests without real Google or SMTP traffic. */
class AiAccessRequestTest {
    /** Mutable deterministic clock for expiry tests. */
    private static final class Time extends Clock {
        private long now = 1000000;
        /** Returns UTC.
         * @return fixed zone
         */
        @Override public ZoneId getZone() { return ZoneOffset.UTC; }
        /** Keeps UTC clock.
         * @param zone ignored test zone
         * @return this clock
         */
        @Override public Clock withZone(ZoneId zone) { return this; }
        /** Returns mutable test instant.
         * @return current instant
         */
        @Override public Instant instant() { return Instant.ofEpochMilli(now); }
    }
    /** Counts persistence calls and can simulate uncertain writes. */
    private static final class Queue extends AiAccessQueue {
        private int count;
        private boolean fail;
        /** Creates a fake sink. */
        Queue() { super(Path.of("/unused")); }
        /** Records one attempt.
         * @param form immutable form
         * @param now timestamp
         * @param deadline challenge deadline
         * @param clock current clock
         * @return test identifier
         * @throws IOException simulated ambiguity
         */
        @Override synchronized String persist(AiAccessForm form, long now, long deadline, Clock clock) throws IOException {
            count++; if (fail) throw new IOException("Simulated"); return "request-id";
        }
    }
    /** Creates a validated immutable fixture.
     * @return form
     */
    private AiAccessForm form() { return new AiAccessForm("Applicant", "person@example.com", "", "A sufficiently long testing purpose", true); }
    /** Successful admission persists once and replay is denied. */
    @Test void persistsExactlyOnce() {
        Queue queue = new Queue(); Time time = new Time();
        AiAccessState state = new AiAccessState(time, new SecureRandom(), queue);
        Map<String, Object> sent = state.activate(form(), "12345678", state.deadline());
        String id = (String) sent.get("challenge");
        assertEquals("REQUESTED", state.verify(id, "12345678").get("status"));
        assertEquals("INVALID_REQUEST", state.verify(id, "12345678").get("status"));
        assertEquals(1, queue.count);
    }
    /** Ambiguous persistence terminally retires the challenge. */
    @Test void ambiguityCannotDuplicate() {
        Queue queue = new Queue(); queue.fail = true;
        AiAccessState state = new AiAccessState(new Time(), new SecureRandom(), queue);
        String id = (String) state.activate(form(), "12345678", state.deadline()).get("challenge");
        assertEquals("UNAVAILABLE", state.verify(id, "12345678").get("status"));
        assertEquals("INVALID_REQUEST", state.verify(id, "12345678").get("status"));
        assertEquals(1, queue.count);
    }
    /** Five wrong codes and deadline equality deny admission. */
    @Test void attemptsAndExpiry() {
        Queue queue = new Queue(); Time time = new Time();
        AiAccessState state = new AiAccessState(time, new SecureRandom(), queue);
        String id = (String) state.activate(form(), "12345678", state.deadline()).get("challenge");
        for (int i = 0; i < 5; i++) assertEquals("INVALID_REQUEST", state.verify(id, "00000000").get("status"));
        assertEquals("INVALID_REQUEST", state.verify(id, "12345678").get("status"));
        id = (String) state.activate(form(), "12345678", state.deadline()).get("challenge");
        time.now += 600000;
        assertEquals("INVALID_REQUEST", state.verify(id, "12345678").get("status"));
        assertEquals(0, queue.count);
    }
    /** Failed reservations consume global quota and concurrent slots are bounded. */
    @Test void quotaCountsFailures() {
        AiAccessState state = new AiAccessState(new Time(), new SecureRandom(), new Queue());
        assertTrue(state.reserve("a@example.com")); assertTrue(state.reserve("b@example.com"));
        assertFalse(state.reserve("c@example.com")); state.release(); state.release();
        for (int i = 0; i < 7; i++) { assertTrue(state.reserve("x" + i + "@example.com")); state.release(); }
        assertFalse(state.reserve("last@example.com"));
    }
    /** Default configuration exposes only disabled status and rejects null Origin.
     * @throws Exception fixture failure
     */
    @Test void closedHttpBoundary() throws Exception {
        DeploymentPolicy policy = new DeploymentPolicy("", "", "DEFAULT");
        AiAccessRequest intake = new AiAccessRequest("", policy, "");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/ai-access/config");
        MockHttpServletResponse response = new MockHttpServletResponse();
        assertTrue(intake.handle(request, response)); assertEquals("{\"enabled\":false}", response.getContentAsString());
        request = new MockHttpServletRequest("POST", "/api/ai-access/verify");
        request.addHeader("Origin", "null"); response = new MockHttpServletResponse();
        intake.handle(request, response); assertEquals(503, response.getStatus());
    }
    /** Deterministic transport records email without external traffic. */
    private static final class FakeTransport implements AiAccessTransport {
        private String code;
        private int calls;
        /** Accepts the offline provider fixture.
         * @param token ignored fixture
         * @return success
         */
        @Override public boolean captcha(String token) { calls++; return true; }
        /** Captures the code only inside the test fixture.
         * @param email ignored mailbox
         * @param value ephemeral code
         * @return success
         */
        @Override public boolean mail(String email, String value) { code = value; return true; }
    }
    /** Enabled API validates origin and persists the exact challenged form.
     * @throws Exception fixture failure
     */
    @Test void enabledBoundary() throws Exception {
        FakeTransport transport = new FakeTransport(); Queue queue = new Queue();
        AiAccessConfig config = new AiAccessConfig("smtp.example.com", 587, "user", "secret", "sender@example.com", "key", "secret", "example.com", Path.of("/unused"));
        AiAccessRequest intake = new AiAccessRequest(config, transport, new AiAccessState(new Time(), new SecureRandom(), queue), new DeploymentPolicy("", "", "DEFAULT"));
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/ai-access/challenge");
        request.setLocalPort(8080); request.setContentType("application/json"); request.addHeader("Origin", "null");
        request.setContent(dev.allow.worker.JsonWire.encode(Map.of("name", "Applicant", "email", "person@example.com", "organization", "", "purpose", "A sufficiently long testing purpose", "acknowledged", true, "captchaToken", "token")));
        MockHttpServletResponse response = new MockHttpServletResponse(); intake.handle(request, response);
        assertEquals(400, response.getStatus()); assertEquals(0, transport.calls);
        request.removeHeader("Origin"); request.addHeader("Origin", "http://127.0.0.1:8080");
        request.setContent(dev.allow.worker.JsonWire.encode(Map.of("name", "Applicant", "email", "person@example.com", "organization", "", "purpose", "A sufficiently long testing purpose", "acknowledged", true, "captchaToken", "token")));
        response = new MockHttpServletResponse(); intake.handle(request, response);
        assertEquals(200, response.getStatus()); assertNotNull(transport.code); assertEquals(0, queue.count);
        Map<?, ?> sent = dev.allow.worker.JsonWire.decode(response.getContentAsByteArray(), Map.class);
        request = new MockHttpServletRequest("POST", "/api/ai-access/verify"); request.setLocalPort(8080);
        request.setContentType("application/json"); request.addHeader("Origin", "http://127.0.0.1:8080");
        request.setContent(dev.allow.worker.JsonWire.encode(Map.of("challenge", sent.get("challenge"), "code", transport.code)));
        response = new MockHttpServletResponse(); intake.handle(request, response);
        assertEquals(200, response.getStatus()); assertEquals(1, queue.count);
    }
    /** Direct child navigation receives an authoritative opaque-origin sandbox.
     * @throws Exception fixture failure
     */
    @Test void childHttpSandbox() throws Exception {
        AiAccessRequest intake = new AiAccessRequest("", new DeploymentPolicy("", "", "DEFAULT"), "");
        MockHttpServletResponse response = new MockHttpServletResponse();
        intake.handle(new MockHttpServletRequest("GET", "/request-ai-access/captcha.html"), response);
        String csp = response.getHeader("Content-Security-Policy");
        assertTrue(csp.startsWith("sandbox allow-scripts;")); assertTrue(csp.contains("frame-ancestors 'self'"));
        assertFalse(csp.contains("allow-same-origin")); assertFalse(csp.contains("allow-forms"));
    }
    /** Real protected queue commits a 0600 pending record and rejects expiry.
     * @throws Exception fixture failure
     */
    @Test void durableProtectedQueue() throws Exception {
        Path directory = java.nio.file.Files.createTempDirectory(Path.of(System.getProperty("user.home")), ".allow-intake-test-",
                java.nio.file.attribute.PosixFilePermissions.asFileAttribute(java.nio.file.attribute.PosixFilePermissions.fromString("rwx------")));
        try {
            Time clock = new Time(); AiAccessQueue queue = new AiAccessQueue(directory);
            String id = queue.persist(form(), clock.millis(), clock.millis() + 1000, clock);
            Path file = directory.resolve(id + ".json");
            assertEquals(java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"), java.nio.file.Files.getPosixFilePermissions(file));
            Map<?, ?> record = dev.allow.worker.JsonWire.decode(java.nio.file.Files.readAllBytes(file), Map.class);
            assertEquals("PENDING", record.get("status")); assertEquals(id, record.get("requestId"));
            boolean rejected = false;
            try { queue.persist(form(), clock.millis(), clock.millis(), clock); }
            catch (IOException expected) { rejected = true; }
            assertTrue(rejected); java.nio.file.Files.delete(file);
        } finally { java.nio.file.Files.delete(directory); }
    }
    /** Queue capacity counts every file, including unrecognized operator files.
     * @throws Exception fixture failure
     */
    @Test void queueCapacityCountsAllEntries() throws Exception {
        Path directory = java.nio.file.Files.createTempDirectory(Path.of(System.getProperty("user.home")), ".allow-intake-capacity-",
                java.nio.file.attribute.PosixFilePermissions.asFileAttribute(java.nio.file.attribute.PosixFilePermissions.fromString("rwx------")));
        try {
            for (int i = 0; i < 1000; i++) java.nio.file.Files.createFile(directory.resolve("foreign-" + i));
            AiAccessQueue queue = new AiAccessQueue(directory); Time time = new Time(); boolean denied = false;
            try { queue.persist(form(), time.millis(), time.millis() + 1000, time); }
            catch (IOException expected) { denied = true; }
            assertTrue(denied);
        } finally {
            try (var entries = java.nio.file.Files.newDirectoryStream(directory)) {
                for (Path entry : entries) java.nio.file.Files.delete(entry);
            }
            java.nio.file.Files.delete(directory);
        }
    }
    /** Leaves a local response body stalled to exercise total HTTP timeout.
     * @param exchange local fixture connection
     * @throws IOException connection failure
     */
    private static void stalled(com.sun.net.httpserver.HttpExchange exchange) throws IOException {
        exchange.sendResponseHeaders(200, 100);
        exchange.getResponseBody().write(1); exchange.getResponseBody().flush();
    }
    /** Whole response deadline includes a stalled body without external traffic.
     * @throws Exception fixture failure
     */
    @Test void providerStallDeadline() throws Exception {
        com.sun.net.httpserver.HttpServer server = com.sun.net.httpserver.HttpServer.create(new java.net.InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", AiAccessRequestTest::stalled); server.start();
        long start = System.nanoTime(); boolean timedOut = false;
        try {
            java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder(java.net.URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/")).build();
            try { AiAccessNetwork.bounded(java.net.http.HttpClient.newHttpClient(), request); }
            catch (java.util.concurrent.TimeoutException expected) { timedOut = true; }
            assertTrue(timedOut); assertTrue(System.nanoTime() - start < 7000000000L);
        } finally { server.stop(0); }
    }
    /** SMTP capability absence, missing TLS and missing successful auth all deny sending. */
    @Test void smtpRequiresPositiveAuthentication() {
        org.eclipse.angus.mail.smtp.SMTPTransport smtp = org.mockito.Mockito.mock(org.eclipse.angus.mail.smtp.SMTPTransport.class);
        org.mockito.Mockito.when(smtp.isSSL()).thenReturn(true);
        assertFalse(AiAccessNetwork.authenticated(smtp));
        org.mockito.Mockito.when(smtp.supportsExtension("AUTH")).thenReturn(true);
        assertFalse(AiAccessNetwork.authenticated(smtp));
        org.mockito.Mockito.when(smtp.getLastReturnCode()).thenReturn(235);
        assertTrue(AiAccessNetwork.authenticated(smtp));
        org.mockito.Mockito.when(smtp.isSSL()).thenReturn(false);
        assertFalse(AiAccessNetwork.authenticated(smtp));
    }
    /** Provider overflow is cancelled before allocating unbounded body data. */
    @Test void boundedProviderBody() {
        AiAccessBody body = new AiAccessBody();
        body.onSubscribe(new Flow.Subscription() {
            /** Does not send automatic test bytes.
             * @param count ignored demand
             */
            @Override public void request(long count) { }
            /** Marks cancellation through exceptional completion. */
            @Override public void cancel() { }
        });
        body.onNext(List.of(ByteBuffer.allocate(8193)));
        assertTrue(body.getBody().toCompletableFuture().isCompletedExceptionally());
    }
}
