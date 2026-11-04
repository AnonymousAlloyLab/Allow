package dev.allow.backend;

import java.io.IOException;
import java.net.Socket;
import java.net.http.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

/** Real TCP checks for bearer, Host, Origin and strict request boundaries. */
class HttpBoundaryTest {
    private static int port;
    private static Process server;
    private static Path log;
    private static final String AUTHORITY = "test-only-authority-" + "x".repeat(32);
    private final HttpClient client = HttpClient.newHttpClient();

    /**
     * Starts the production parent classpath without the worker's shaded logging classes.
     * @throws Exception unavailable local server
     */
    @BeforeAll
    static void start() throws Exception {
        try (java.net.ServerSocket socket = new java.net.ServerSocket(0)) {
            port = socket.getLocalPort();
        }
        log = Files.createTempFile("allow-http-test-", ".log");
        String java = Path.of(System.getProperty("java.home"), "bin/java").toString();
        ProcessBuilder builder = new ProcessBuilder(java, "-cp", "target/classes:target/dependency/*",
                AllowApplication.class.getName(), "--server.port=" + port, "--debug=false", "--trace=false",
                "--logging.level.root=WARN", "--logging.level.org.springframework=WARN");
        builder.environment().put("ALLOW_TOKEN", AUTHORITY);
        server = builder.redirectErrorStream(true).redirectOutput(log.toFile()).start();
        waitForServer();
    }

    /**
     * Polls only public startup liveness through authenticated config.
     * @throws Exception failed startup
     */
    private static void waitForServer() throws Exception {
        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/config"))
                .header("Authorization", "Bearer " + AUTHORITY).build();
        long deadline = System.nanoTime() + 15000000000L;
        while (System.nanoTime() < deadline && server.isAlive()) {
            try {
                if (client.send(request, HttpResponse.BodyHandlers.discarding()).statusCode() == 200) return;
            } catch (IOException error) {
                Thread.sleep(25);
            }
        }
        fail("Local HTTP server did not start");
    }

    /**
     * Reaps the test parent and removes its private log.
     * @throws Exception failed cleanup
     */
    @AfterAll
    static void stop() throws Exception {
        if (server != null) {
            server.destroyForcibly();
            server.waitFor();
        }
        if (log != null) Files.deleteIfExists(log);
    }

    /**
     * Rejects unauthenticated private reads and authenticated hostile origins.
     * @throws Exception HTTP failure
     */
    @Test
    void authorityAndOrigin() throws Exception {
        assertEquals(403, send("/api/config", null, null).statusCode());
        assertEquals(403, send("/api/config", "wrong", null).statusCode());
        assertEquals(403, send("/api/config", token(), "https://hostile.example").statusCode());
        assertEquals(200, send("/api/config", token(), "http://127.0.0.1:" + port).statusCode());
    }

    /**
     * A correct token cannot bypass Host routing.
     * @throws Exception TCP failure
     */
    @Test
    void hostileHost() throws Exception {
        String response = raw("GET /api/config HTTP/1.1\r\nHost: evil.example\r\nAuthorization: Bearer "
                + token() + "\r\nConnection: close\r\n\r\n");
        assertTrue(response.startsWith("HTTP/1.1 403"));
    }

    /**
     * Unknown, duplicate and oversized API bodies reject.
     * @throws Exception HTTP failure
     */
    @Test
    void strictBody() throws Exception {
        assertEquals(400, post("{\"source\":\"x\",\"source\":\"y\"}").statusCode());
        assertEquals(400, post("{\"source\":\"x\",\"unexpected\":true}").statusCode());
        assertEquals(400, post(" ".repeat(262145)).statusCode());
    }

    /**
     * Rejects missing, null and coerced JSON identity values.
     * @throws Exception HTTP failure
     */
    @Test
    void strictIdentityTypes() throws Exception {
        String prefix = "{\"source\":\"run {}\",\"commandIndex\":";
        String suffix = ",\"revision\":1,\"epoch\":1,\"operation\":\"ANALYZE\"}";
        for (String value : new String[]{"null", "\"1\"", "1.5", "true"}) {
            assertEquals(400, post(prefix + value + suffix).statusCode(), value);
        }
        assertEquals(400, post("{\"source\":\"run {}\",\"operation\":\"ANALYZE\"}").statusCode());
    }

    /**
     * Responses retain exact Unicode source and epoch identity.
     * @throws Exception HTTP failure
     */
    @Test
    void submitEchoesIdentity() throws Exception {
        String body = "{\"source\":\"// 😀\\nsig Person {} run {} for 3\",\"commandIndex\":0,"
                + "\"revision\":17,\"epoch\":22,\"operation\":\"VALIDATE\"}";
        HttpResponse<String> response = post(body);
        assertEquals(200, response.statusCode(), response.body());
        assertTrue(response.body().contains("\"revision\":17"));
        assertTrue(response.body().contains("\"epoch\":22"));
        assertFalse(response.body().contains(token()));
    }

    /**
     * Returns the test-only per-launch authority without logging it.
     * @return authority
     */
    private String token() {
        return AUTHORITY;
    }

    /**
     * Sends one private GET.
     * @param path route
     * @param token authority or null
     * @param origin origin or null
     * @return response
     * @throws Exception HTTP failure
     */
    private HttpResponse<String> send(String path, String token, String origin) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path));
        if (token != null) request.header("Authorization", "Bearer " + token);
        if (origin != null) request.header("Origin", origin);
        return client.send(request.GET().build(), HttpResponse.BodyHandlers.ofString());
    }

    /**
     * Sends a bounded JSON candidate.
     * @param body JSON
     * @return response
     * @throws Exception HTTP failure
     */
    private HttpResponse<String> post(String body) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/jobs"))
                .header("Authorization", "Bearer " + token()).header("Content-Type", "application/json")
                .header("Origin", "http://127.0.0.1:" + port)
                .POST(HttpRequest.BodyPublishers.ofString(body)).build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    /**
     * Sends raw headers because Java HttpClient owns its Host field.
     * @param request complete request
     * @return response
     * @throws IOException TCP failure
     */
    private String raw(String request) throws IOException {
        try (Socket socket = new Socket("127.0.0.1", port)) {
            socket.setSoTimeout(5000);
            socket.getOutputStream().write(request.getBytes(StandardCharsets.UTF_8));
            return new String(socket.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        }
    }
}
