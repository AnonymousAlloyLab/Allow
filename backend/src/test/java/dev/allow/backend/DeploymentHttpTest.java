package dev.allow.backend;

import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Real TCP checks of deployment routing. */
class DeploymentHttpTest {
    private static final String TOKEN = "deployment-test-" + "x".repeat(32);

    /** Exercises exact route and duplicate authority headers.
     * @throws Exception process or network failure
     */
    @Test
    void deploymentBoundary() throws Exception {
        int port;
        try (ServerSocket socket = new ServerSocket(0)) { port = socket.getLocalPort(); }
        Path log = Files.createTempFile("allow-deployment-http-", ".log");
        ProcessBuilder builder = new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin/java").toString(),
                "-cp", "target/classes:target/dependency/*", AllowApplication.class.getName(),
                "--server.port=" + port, "--allow.deployment.origin=https://allow.example",
                "--allow.deployment.tunnel-host=127.0.0.1:18081",
                "--allow.document.advisory-profile=DOCUMENT_ADVISORY_TIER1", "--logging.level.root=WARN");
        builder.environment().put("ALLOW_TOKEN", TOKEN);
        Process server = builder.redirectErrorStream(true).redirectOutput(log.toFile()).start();
        try {
            awaitServer(port, server);
            check(port, "Host: 127.0.0.1:18081\r\n", "Origin: https://allow.example\r\n", 200);
            check(port, "Host: 127.0.0.1:18081\r\n", "", 200);
            check(port, "Host: evil.example\r\n", "Origin: https://allow.example\r\n", 403);
            check(port, "Host: 127.0.0.1:18081\r\n", "Origin: https://evil.example\r\n", 403);
            check(port, "Host: 127.0.0.1:18081\r\n", "Origin: https://allow.example\r\nOrigin: https://allow.example\r\n", 403);
            check(port, "Host: 127.0.0.1:18081\r\n", "Authorization: Bearer " + TOKEN + "\r\n", 403);
            spoofingAndBearer(port);
        } finally {
            server.destroyForcibly();
            server.waitFor();
            Files.deleteIfExists(log);
        }
    }

    /** Rejects missing or wrong bearer and proxy-header attempts to override routing.
     * @param port server port
     * @throws Exception network failure
     */
    private void spoofingAndBearer(int port) throws Exception {
        String host = "Host: 127.0.0.1:18081\r\n";
        assertTrue(raw(port, host + "Connection: close\r\n\r\n").startsWith("HTTP/1.1 403"));
        assertTrue(raw(port, host + "Authorization: Bearer wrong\r\nConnection: close\r\n\r\n")
                .startsWith("HTTP/1.1 403"));
        check(port, "Host: evil.example\r\n", "X-Forwarded-Host: 127.0.0.1:18081\r\n", 403);
        check(port, host, "Origin: https://evil.example\r\nX-Forwarded-Proto: https\r\n"
                + "X-Forwarded-Host: allow.example\r\n", 403);
        String duplicate = request(port, host + host, "");
        assertTrue(duplicate.startsWith("HTTP/1.1 400") || duplicate.startsWith("HTTP/1.1 403"));
    }

    /** Waits for the explicit route to become available.
     * @param port server port
     * @param server owned process
     * @throws Exception server failed to start
     */
    private void awaitServer(int port, Process server) throws Exception {
        long deadline = System.nanoTime() + 15000000000L;
        while (System.nanoTime() < deadline && server.isAlive()) {
            try {
                if (request(port, "Host: 127.0.0.1:18081\r\n", "").contains(" 200 ")) return;
            } catch (java.io.IOException ignored) {
                Thread.sleep(25);
            }
        }
        fail("Deployment HTTP server did not start");
    }

    /** Checks one response status.
     * @param port server port
     * @param host raw Host header
     * @param extra additional raw headers
     * @param status expected status
     * @throws Exception network failure
     */
    private void check(int port, String host, String extra, int status) throws Exception {
        assertTrue(request(port, host, extra).startsWith("HTTP/1.1 " + status));
    }

    /** Sends raw headers so repeated authority is exercised.
     * @param port server port
     * @param host raw Host header
     * @param extra additional raw headers
     * @return complete response
     * @throws Exception network failure
     */
    private String request(int port, String host, String extra) throws Exception {
        return raw(port, host + "Authorization: Bearer " + TOKEN + "\r\n" + extra + "Connection: close\r\n\r\n");
    }

    /** Sends a request with precisely the supplied headers.
     * @param port server port
     * @param headers complete raw headers
     * @return complete response
     * @throws Exception network failure
     */
    private String raw(int port, String headers) throws Exception {
        try (Socket socket = new Socket("127.0.0.1", port)) {
            String request = "GET /api/config HTTP/1.1\r\n" + headers;
            socket.getOutputStream().write(request.getBytes(StandardCharsets.US_ASCII));
            return new String(socket.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        }
    }
}
