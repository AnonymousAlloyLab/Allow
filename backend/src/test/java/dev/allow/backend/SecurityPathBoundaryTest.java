package dev.allow.backend;

import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Actual HTTP regressions for the previously unauthenticated normalized-path aliases. */
class SecurityPathBoundaryTest {
    private static final String TOKEN = "isolated-path-regression-" + "x".repeat(40);
    private static Process server;
    private static int port;
    private static Path log;
    private static Path assets;

    /** Starts a corpus-free private backend with a temporary public asset.
     * @throws Exception unavailable process or socket
     */
    @BeforeAll
    static void start() throws Exception {
        try (ServerSocket socket = new ServerSocket(0)) { port = socket.getLocalPort(); }
        log = Files.createTempFile("allow-path-regression-", ".log");
        assets = Files.createTempDirectory("allow-path-assets-");
        Files.createDirectory(assets.resolve("assets"));
        Files.writeString(assets.resolve("assets/allow-path-test.js"), "/* isolated static boundary */");
        ProcessBuilder builder = new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin/java").toString(),
                "-cp", "target/classes:target/dependency/*", AllowApplication.class.getName(),
                "--server.port=" + port, "--spring.web.resources.static-locations=" + assets.toUri());
        builder.environment().put("ALLOW_TOKEN", TOKEN);
        server = builder.redirectErrorStream(true).redirectOutput(log.toFile()).start();
        awaitServer();
    }

    /** Waits for authenticated readiness without sending SQL or model data.
     * @throws Exception failed startup
     */
    private static void awaitServer() throws Exception {
        long deadline = System.nanoTime() + 15000000000L;
        while (System.nanoTime() < deadline && server.isAlive()) {
            try {
                if (request("GET", "/api/config", true).startsWith("HTTP/1.1 200")) return;
            } catch (IOException ignored) {
                Thread.sleep(25);
            }
        }
        fail("Isolated path test server failed to start");
    }

    /** Reaps only the owned process and removes its temporary public fixture.
     * @throws Exception cleanup failure
     */
    @AfterAll
    static void stop() throws Exception {
        if (server != null) { server.destroyForcibly(); server.waitFor(); }
        if (log != null) Files.deleteIfExists(log);
        if (assets != null) {
            Files.deleteIfExists(assets.resolve("assets/allow-path-test.js"));
            Files.deleteIfExists(assets.resolve("assets"));
            Files.deleteIfExists(assets);
        }
    }

    /** Rejects encoded, matrix and dot-segment paths before reads or mutations.
     * @throws Exception request failure
     */
    @Test
    void routingAliasesNeverGrantAccess() throws Exception {
        for (String path : new String[]{"/%61pi/config", "/api;ignored/config", "/x/../api/config",
                "/assets/%2e%2e/api/config", "//api/config", "/api/./config", "/%61pi/jobs"}) {
            for (String method : new String[]{"GET", "POST"}) {
                for (boolean authorized : new boolean[]{false, true}) {
                    String response = request(method, path, authorized);
                    assertTrue(response.startsWith("HTTP/1.1 4"), method + " " + path);
                    assertFalse(response.contains(TOKEN));
                }
            }
        }
    }

    /** Preserves public reads, guards other methods and all unspecified paths.
     * @throws Exception request failure
     */
    @Test
    void publicExceptionsRemainNarrow() throws Exception {
        for (String method : new String[]{"GET", "HEAD"}) {
            assertTrue(request(method, "/assets/allow-path-test.js", false).startsWith("HTTP/1.1 200"));
        }
        assertTrue(request("POST", "/assets/allow-path-test.js", false).startsWith("HTTP/1.1 403"));
        assertTrue(request("GET", "/unlisted", false).startsWith("HTTP/1.1 403"));
        String rejected = request("GET", "/api/config", false);
        assertTrue(rejected.startsWith("HTTP/1.1 403"));
        assertTrue(rejected.contains("Cache-Control: no-store"));
        assertTrue(request("GET", "/api/config", true).startsWith("HTTP/1.1 200"));
    }

    /** Exercises raw path policy independent of container normalization.
     */
    @Test
    void canonicalPolicyRejectsAliasesAndNestedAssets() {
        for (String value : new String[]{"/%61pi/config", "/api;a/config", "/x/../api/config", "/a\\b", "//api/config"}) {
            assertFalse(RequestPaths.canonical(value), value);
        }
        assertFalse(RequestPaths.publicRead("GET", "/assets/a/b.js"));
        assertFalse(RequestPaths.publicRead("GET", "/assets/a.js/../api/config"));
        assertFalse(RequestPaths.publicRead("POST", "/"));
        assertTrue(RequestPaths.publicRead("GET", "/"));
        assertTrue(RequestPaths.publicRead("HEAD", "/index.html"));
    }

    /** Keeps existing encoded and literal document identifiers behind bearer authority.
     * @throws Exception request failure
     */
    @Test
    void documentIdentifierEncodingRemainsGuarded() throws Exception {
        String id = "12345678-1234-4234-8234-123456789abc";
        for (String separator : new String[]{":", "%3A"}) {
            String path = "/api/v1/documents/server" + separator + id;
            assertTrue(RequestPaths.canonical(path));
            assertFalse(RequestPaths.publicRead("GET", path));
            assertTrue(request("GET", path, false).startsWith("HTTP/1.1 403"));
            String admitted = request("GET", path, true);
            assertTrue(admitted.startsWith("HTTP/1.1 503"));
            assertTrue(admitted.contains("\"protocol\":1"));
        }
        for (String malformed : new String[]{"%3a", "%253A", "%3A%2F", "%3A:"}) {
            String path = "/api/v1/documents/server" + malformed + id;
            assertFalse(RequestPaths.canonical(path));
            assertTrue(request("GET", path, true).startsWith("HTTP/1.1 400"));
        }
        assertFalse(RequestPaths.canonical("/api/v1/documents/server%3A" + id + "x"));
        assertFalse(RequestPaths.canonical("/assets/server%3A" + id));
        assertFalse(RequestPaths.canonical("/api/v1/documents/server%3A" + id + "/%61nalyze"));
    }

    /** Sends exact raw request bytes so URI aliases cannot be normalized by a test client.
     * @param method request method
     * @param path raw path including malicious aliases
     * @param authorized whether to supply the known test capability
     * @return complete bounded response
     * @throws IOException request failure
     */
    private static String request(String method, String path, boolean authorized) throws IOException {
        try (Socket socket = new Socket("127.0.0.1", port)) {
            socket.setSoTimeout(5000);
            String bearer = authorized ? "Authorization: Bearer " + TOKEN + "\r\n" : "";
            String frame = method + " " + path + " HTTP/1.1\r\nHost: 127.0.0.1:" + port
                    + "\r\n" + bearer + "Content-Length: 0\r\nConnection: close\r\n\r\n";
            socket.getOutputStream().write(frame.getBytes(StandardCharsets.US_ASCII));
            return new String(socket.getInputStream().readNBytes(65536), StandardCharsets.UTF_8);
        }
    }
}
