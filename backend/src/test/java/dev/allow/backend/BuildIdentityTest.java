package dev.allow.backend;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Guards behavior-changing resources against reuse of a stale analysis identity. */
class BuildIdentityTest {
    @TempDir
    private Path temporary;

    /** Requires a registry-only change to invalidate the exact compiled build identity.
     * @throws IOException if the synthetic filesystem cannot be created
     */
    @Test
    void registryBytesAffectIdentity() throws IOException {
        Path target = fixture();
        Path registry = target.resolve("classes/profiles/egraph-rules.json");
        Files.writeString(registry, "{\"version\":1}");
        String first = BuildIdentity.read(target);
        assertEquals(first, BuildIdentity.read(target));
        Files.writeString(registry, "{\"version\":2}");
        assertNotEquals(first, BuildIdentity.read(target));
    }

    /** Requires adding or deleting a classpath resource to change the fingerprint.
     * @throws IOException if a synthetic resource cannot be created or removed
     */
    @Test
    void resourcePresenceAffectsIdentity() throws IOException {
        Path target = fixture();
        String initial = BuildIdentity.read(target);
        Path settings = target.resolve("classes/application.properties");
        Files.writeString(settings, "setting=changed");
        assertNotEquals(initial, BuildIdentity.read(target));
        Files.delete(settings);
        assertEquals(initial, BuildIdentity.read(target));
    }

    /** Requires the packaged reference to be available and bound to the worker identity.
     * @throws IOException if the resource or synthetic build cannot be read
     */
    @Test
    void acgnReferenceIsPackagedAndAffectsIdentity() throws IOException {
        byte[] reference;
        try (var input = getClass().getResourceAsStream("/profiles/acgn-reference.json")) {
            assertNotNull(input);
            reference = input.readAllBytes();
        }
        assertTrue(new String(reference, StandardCharsets.UTF_8).contains("8770cb4b5f7133bad78058d9bc214f0ca36130d0"));
        Path target = fixture();
        String initial = BuildIdentity.read(target);
        Files.write(target.resolve("classes/profiles/acgn-reference.json"), reference);
        assertNotEquals(initial, BuildIdentity.read(target));
    }

    /** Creates isolated synthetic byte inputs without modifying the real running build.
     * @return temporary target root
     * @throws IOException if a directory or fixture file cannot be written
     */
    private Path fixture() throws IOException {
        Files.createDirectories(temporary.resolve("classes/profiles"));
        Files.createDirectories(temporary.resolve("dependency"));
        Files.createDirectories(temporary.resolve("solver"));
        Files.writeString(temporary.resolve("classes/Example.class"), "synthetic-class");
        Files.writeString(temporary.resolve("dependency/example.jar"), "synthetic-dependency");
        Files.writeString(temporary.resolve("solver/alloy.jar"), "synthetic-solver");
        return temporary;
    }
}
