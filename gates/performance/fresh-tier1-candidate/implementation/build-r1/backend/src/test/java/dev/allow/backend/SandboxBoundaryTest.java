package dev.allow.backend;

import java.io.IOException;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Uses the production sandbox arguments with a mounted test-only probe entry point. */
class SandboxBoundaryTest {
    /**
     * The child cannot see a host canary or connect to a parent loopback listener.
     * @throws Exception sandbox failure
     */
    @Test
    void filesystemAndNetworkDenied() throws Exception {
        Path canary = Files.createTempFile("allow-private-canary-", ".txt");
        Files.writeString(canary, "private test fixture");
        try (ServerSocket server = new ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))) {
            Process process = probe(canary, server.getLocalPort());
            try {
                assertTrue(process.waitFor(5, TimeUnit.SECONDS));
                assertEquals(0, process.exitValue());
                String output = new String(process.getInputStream().readNBytes(1024), StandardCharsets.UTF_8);
                assertEquals("true:true", output.trim());
            } finally {
                process.destroyForcibly();
                process.waitFor();
            }
        } finally {
            Files.deleteIfExists(canary);
        }
    }

    /**
     * Selects the test probe without exposing a production environment hook.
     * @param canary host-only path
     * @param port parent port
     * @return isolated child
     * @throws IOException launch failure
     */
    private Process probe(Path canary, int port) throws IOException {
        Path target = Path.of("target").toAbsolutePath();
        BubblewrapLauncher launcher = new BubblewrapLauncher(target);
        List<String> args = launcher.command(target.resolve("solver/alloy.jar"));
        String java = Path.of(System.getProperty("java.home"), "bin/java").toString();
        int executable = args.indexOf(java);
        args.addAll(executable, List.of("--ro-bind", target.resolve("test-classes").toString(), "/app/testclasses"));
        args.set(args.indexOf("-cp") + 1, "/app/testclasses:/app/classes:/app/solver.jar:/app/dependency/*");
        args.set(args.size() - 1, SandboxProbe.class.getName());
        args.add(canary.toString());
        args.add(Integer.toString(port));
        ProcessBuilder builder = new ProcessBuilder(args);
        builder.environment().clear();
        return builder.start();
    }
}
