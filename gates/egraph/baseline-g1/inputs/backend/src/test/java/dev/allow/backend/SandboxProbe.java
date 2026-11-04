package dev.allow.backend;

import java.io.IOException;
import java.net.*;
import java.nio.file.*;

/** Test-only program observes sandbox boundaries without reading canary contents. */
public final class SandboxProbe {
    /** Prevents construction of the test entry point. */
    private SandboxProbe() {}

    /**
     * Reports filesystem/network denial.
     * @param arguments canary path and parent port
     */
    public static void main(String[] arguments) {
        boolean hidden = !Files.exists(Path.of(arguments[0]));
        boolean isolated = true;
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", Integer.parseInt(arguments[1])), 300);
            isolated = false;
        } catch (IOException error) {
            isolated = true;
        }
        System.out.println(hidden + ":" + isolated);
    }
}
