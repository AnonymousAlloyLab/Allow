package dev.allow.backend;

import dev.allow.worker.Hashes;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.List;
import java.util.HexFormat;

/** Binds a launch to exact compiled worker/mapper bytes and runtime dependencies. */
final class BuildIdentity {
    /** Prevents construction of the stateless hashing utility. */
    private BuildIdentity() {}

    /**
     * Computes a deterministic build identity.
     * @param target build root
     * @return digest
     * @throws IOException incomplete build
     */
    static String read(Path target) throws IOException {
        MessageDigest digest = Hashes.digest();
        files(digest, target, target.resolve("classes"), true);
        files(digest, target, target.resolve("dependency"), false);
        file(digest, target, target.resolve("solver/alloy.jar"));
        digest.update(System.getProperty("java.runtime.version").getBytes(StandardCharsets.UTF_8));
        return HexFormat.of().formatHex(digest.digest());
    }

    /**
     * Hashes an ordered immutable-file inventory.
     * @param digest engine
     * @param root relative identity root
     * @param directory files
     * @param classes class-only mode
     * @throws IOException failed inventory
     */
    private static void files(MessageDigest digest, Path root, Path directory, boolean classes) throws IOException {
        List<Path> paths;
        try (var stream = Files.walk(directory)) {
            paths = stream.filter(Files::isRegularFile).sorted().toList();
        }
        for (Path path : paths) {
            if (path.toString().endsWith(classes ? ".class" : ".jar")) file(digest, root, path);
        }
    }

    /**
     * Streams trusted build files without allocating whole JARs.
     * @param digest engine
     * @param root relative root
     * @param path file
     * @throws IOException failed read
     */
    private static void file(MessageDigest digest, Path root, Path path) throws IOException {
        digest.update(root.relativize(path).toString().getBytes(StandardCharsets.UTF_8));
        digest.update((byte) 0);
        try (var input = Files.newInputStream(path)) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        digest.update((byte) 0);
    }
}
