package dev.allow.backend;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import org.springframework.stereotype.Component;

/** Per-launch bearer authority; it is never returned from an HTTP endpoint. */
@Component
final class LaunchAuthority {
    private final byte[] expected;

    /**
     * Uses launcher authority or privately creates one for direct development.
     * @throws IOException private token file cannot be created
     * @throws IllegalArgumentException insufficient supplied token entropy
     */
    LaunchAuthority() throws IOException {
        String token = System.getenv("ALLOW_TOKEN");
        if (token == null || token.isBlank()) token = createToken();
        if (token.length() < 32) throw new IllegalArgumentException("ALLOW_TOKEN must contain at least 32 characters");
        expected = ("Bearer " + token).getBytes(StandardCharsets.UTF_8);
    }

    /**
     * Creates a nonlogging private bootstrap file.
     * @return unpredictable token
     * @throws IOException persistence failure
     */
    private String createToken() throws IOException {
        byte[] random = new byte[32];
        new SecureRandom().nextBytes(random);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(random);
        Path directory = Path.of(".runtime");
        Files.createDirectories(directory);
        Files.setPosixFilePermissions(directory, PosixFilePermissions.fromString("rwx------"));
        Path file = directory.resolve("token");
        Files.deleteIfExists(file);
        Files.createFile(file, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
        Files.writeString(file, token, StandardCharsets.UTF_8);
        return token;
    }

    /**
     * Compares bearer bytes without exposing the secret.
     * @param header supplied Authorization
     * @return match
     */
    boolean accepts(String header) {
        return header != null && MessageDigest.isEqual(expected, header.getBytes(StandardCharsets.UTF_8));
    }
}
