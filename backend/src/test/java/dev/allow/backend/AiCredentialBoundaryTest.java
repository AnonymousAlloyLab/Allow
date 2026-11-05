package dev.allow.backend;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Synthetic credentials only: protected provisioning without environment or public disclosure. */
class AiCredentialBoundaryTest {
    @TempDir
    private Path directory;

    /** A startup credential appears only in the private pipe frame and can be released.
     * @throws IOException unavailable synthetic filesystem fixture
     */
    @Test
    void protectedSyntheticCredentialIsNotInConfig() throws IOException {
        Path project = Files.createDirectory(directory.resolve("project"));
        Path key = directory.resolve("credential");
        Files.writeString(key, "synthetic-credential\n");
        Files.setPosixFilePermissions(key, PosixFilePermissions.fromString("rw-------"));
        AiConfiguration configuration = remote(project, key);
        assertFalse(configuration.view().toString().contains("synthetic-credential"));
        assertFalse(configuration.toString().contains("synthetic-credential"));
        assertEquals("synthetic-credential", configuration.start().path("credential").asText());
        configuration.closeCredential();
        assertEquals("", configuration.start().path("credential").asText());
    }

    /** Linked, broadly readable and oversized sources fail before entering graph state.
     * @throws IOException unavailable synthetic filesystem fixture
     */
    @Test
    void deniesInsecureLinkedAndOversizedSources() throws IOException {
        Path project = Files.createDirectory(directory.resolve("project"));
        Path key = directory.resolve("credential");
        Files.writeString(key, "synthetic");
        Files.setPosixFilePermissions(key, PosixFilePermissions.fromString("rw-r--r--"));
        assertThrows(IOException.class, new Configure(this, project, key));
        Files.setPosixFilePermissions(key, PosixFilePermissions.fromString("rw-------"));
        Path linked = directory.resolve("linked");
        Files.createSymbolicLink(linked, key);
        assertThrows(IOException.class, new Configure(this, project, linked));
        Files.writeString(key, "x".repeat(4097));
        assertThrows(IOException.class, new Configure(this, project, key));
    }

    /** Constructs a remote fixture without opening a provider connection.
     * @param project trusted fixture installation
     * @param key external synthetic credential file
     * @return closed remote configuration
     * @throws IOException unavailable or unsafe credential fixture
     */
    private AiConfiguration remote(Path project, Path key) throws IOException {
        return new AiConfiguration("REMOTE_ASSISTED", project.toString(), directory.resolve("ledger.json").toString(),
                100000, "reviewed-test-terms", "reviewed-test-tariff", key.toString(), false, new AccessMode("PRIVATE"));
    }

    /** Names a synthetic provisioning attempt.
     * @param test fixture owner
     * @param project isolated trusted root
     * @param key protected source
     */
    private record Configure(AiCredentialBoundaryTest test, Path project, Path key) implements Executable {
        /** Attempts explicit startup provisioning.
         * @throws IOException unavailable fixture
         */
        @Override
        public void execute() throws IOException { test.remote(project, key); }
    }
}
