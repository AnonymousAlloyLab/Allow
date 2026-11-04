package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;

/** Reads only the trusted launcher's private delegated-scope descriptor. */
final class WarmConfiguration {
    /** Prevents construction of the stateless configuration reader. */
    private WarmConfiguration() { }

    /** Verifies private file ownership and the exact containing cgroup before use.
     * @param installation canonical trusted installation root
     * @return canonical dedicated delegated scope root
     * @throws IOException absent, public, substituted or uncontained configuration
     */
    static Path read(Path installation) throws IOException {
        Path directory = installation.resolve(".runtime/warm-pool");
        Path file = directory.resolve("config.json");
        privatePath(directory, true, "rwx------");
        privatePath(file, false, "rw-------");
        if (Files.size(file) > 4096) throw new IOException("Worker configuration exceeds limit");
        JsonNode config = DocumentJson.decode(Files.readAllBytes(file));
        DocumentJson.fields(config, "schema", "cgroupRoot", "rootDevice", "rootInode");
        if (!config.path("schema").isInt() || config.path("schema").intValue() != 1
                || !config.path("cgroupRoot").isTextual()) throw new IOException("Invalid worker configuration");
        Path group = Path.of(config.path("cgroupRoot").textValue());
        verifyGroup(group, config);
        return group;
    }

    /** Checks canonical private ordinary files and their current-principal ownership.
     * @param path configured metadata path
     * @param directory whether a directory is required
     * @param permissions exact required POSIX mode
     * @throws IOException unsafe path, mode or owner
     */
    private static void privatePath(Path path, boolean directory, String permissions) throws IOException {
        boolean expected = directory ? Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)
                : Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS);
        if (!expected || !path.toRealPath().equals(path)
                || !Files.getPosixFilePermissions(path).equals(PosixFilePermissions.fromString(permissions))
                || !Files.getAttribute(path, "unix:uid").equals(Files.getAttribute(Path.of("/proc/self"), "unix:uid"))) {
            throw new IOException("Private worker metadata required");
        }
    }

    /** Binds launch configuration to the server's actual private control leaf.
     * @param group claimed delegated root
     * @param config closed private launcher descriptor
     * @throws IOException wrong root, kernel identity or process membership
     */
    private static void verifyGroup(Path group, JsonNode config) throws IOException {
        if (!group.isAbsolute() || !group.startsWith(Path.of("/sys/fs/cgroup")) || !group.toRealPath().equals(group)
                || !Files.getFileStore(group).type().equals("cgroup2")) throw new IOException("Private cgroup required");
        for (String name : new String[]{"rootDevice", "rootInode"}) {
            if (!config.path(name).isIntegralNumber() || !config.path(name).canConvertToLong()
                    || config.path(name).longValue() <= 0) throw new IOException("Invalid cgroup identity");
        }
        if ((long) Files.getAttribute(group, "unix:dev") != config.path("rootDevice").longValue()
                || (long) Files.getAttribute(group, "unix:ino") != config.path("rootInode").longValue()
                || !Files.getAttribute(group, "unix:uid").equals(Files.getAttribute(Path.of("/proc/self"), "unix:uid"))) {
            throw new IOException("Worker cgroup identity mismatch");
        }
        String membership = Files.readString(Path.of("/proc/self/cgroup")).trim();
        String expected = "0::/" + Path.of("/sys/fs/cgroup").relativize(group) + "/control";
        if (!membership.equals(expected)) throw new IOException("Server is outside its private control leaf");
    }
}
