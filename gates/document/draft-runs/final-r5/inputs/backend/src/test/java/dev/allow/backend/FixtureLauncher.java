package dev.allow.backend;

import java.io.IOException;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicReference;

/** Trusted test-only launch seam for timeout/crash/wire tests. */
final class FixtureLauncher implements SandboxLauncher {
    private final String mode;
    private final AtomicReference<Process> process = new AtomicReference<>();

    /**
     * Selects a compiled test fixture.
     * @param mode behavior
     */
    FixtureLauncher(String mode) {
        this.mode = mode;
    }

    /**
     * Starts the test JVM without shell interpretation.
     * @return owned child
     * @throws IOException failed launch
     */
    @Override
    public Process launch() throws IOException {
        String java = Path.of(System.getProperty("java.home"), "bin/java").toString();
        Process child = new ProcessBuilder(java, "-cp", System.getProperty("java.class.path"),
                FakeChild.class.getName(), mode).start();
        process.set(child);
        return child;
    }

    /**
     * Inspects whether the launched child has exited.
     * @return physical liveness
     */
    boolean alive() {
        Process child = process.get();
        return child != null && child.isAlive();
    }
}
