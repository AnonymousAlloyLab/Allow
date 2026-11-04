package dev.allow.backend;

import java.io.IOException;

/** Package-private launch seam for resource and denial tests. */
interface SandboxLauncher {
    /**
     * Identifies the trusted launcher for analysis provenance.
     * @return immutable implementation identity
     */
    default String identity() {
        return getClass().getName();
    }

    /**
     * Starts only an isolated child process.
     * @return sandbox process
     * @throws IOException isolation unavailable
     */
    Process launch() throws IOException;
}
