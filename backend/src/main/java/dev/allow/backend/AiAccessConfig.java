package dev.allow.backend;

import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFileAttributes;
import java.nio.file.attribute.PosixFilePermission;
import java.util.Map;
import java.util.Set;

/** Externally provisioned closed intake configuration and protected storage paths. */
record AiAccessConfig(String smtpHost, int smtpPort, String smtpUsername, String smtpPassword,
                      String sender, String siteKey, String captchaSecret, String hostname, Path queueDirectory) {
    /** Redacts externally provisioned secrets from diagnostics.
     * @return inert marker
     */
    @Override
    public String toString() { return "AiAccessConfig[REDACTED]"; }

    /** Loads bounded external JSON without exposing parsing details.
     * @param name absolute configuration path
     * @param installation protected installation root
     * @return validated configuration
     * @throws IOException invalid configuration
     */
    static AiAccessConfig load(String name, Path installation) throws IOException {
        Path path = Path.of(name);
        protectedPath(path, false);
        if (path.startsWith(installation) || ((Number) Files.getAttribute(path, "unix:nlink", LinkOption.NOFOLLOW_LINKS)).intValue() != 1) throw new IOException("Configuration rejected");
        if (Files.size(path) > 16384) throw new IOException("Configuration rejected");
        byte[] bytes;
        try (var input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) { bytes = input.readNBytes(16385); }
        if (bytes.length > 16384) throw new IOException("Configuration rejected");
        DocumentJson.decode(bytes);
        Map<?, ?> values = JsonWire.decode(bytes, Map.class);
        Set<String> keys = Set.of("smtpHost", "smtpPort", "smtpUsername", "smtpPassword", "sender", "siteKey", "captchaSecret", "hostname", "queueDirectory");
        if (!values.keySet().equals(keys)) throw new IOException("Configuration rejected");
        Object port = values.get("smtpPort");
        if (!(port instanceof Integer) || (Integer) port < 1 || (Integer) port > 65535) throw new IOException("Configuration rejected");
        AiAccessConfig result = new AiAccessConfig(text(values, "smtpHost", 253), (Integer) port,
                text(values, "smtpUsername", 254), text(values, "smtpPassword", 2048), text(values, "sender", 254),
                text(values, "siteKey", 200), text(values, "captchaSecret", 256), text(values, "hostname", 253),
                Path.of(text(values, "queueDirectory", 4096)));
        result.validate();
        if (result.queueDirectory().startsWith(installation) || result.queueDirectory().equals(path.getParent())) throw new IOException("Configuration rejected");
        return result;
    }

    /** Validates destination names and the separate queue.
     * @throws IOException unsafe settings
     */
    private void validate() throws IOException {
        if (!smtpHost.matches("[a-zA-Z0-9.-]+") || !hostname.matches("[a-z0-9.-]+")
                || !AiAccessForm.validEmail(sender) || !siteKey.matches("[A-Za-z0-9_-]+")
                || !captchaSecret.matches("[A-Za-z0-9_-]+")) throw new IOException("Configuration rejected");
        protectedPath(queueDirectory, true);
    }

    /** Reads one bounded printable configuration field.
     * @param values closed map
     * @param key expected key
     * @param maximum length bound
     * @return string value
     * @throws IOException invalid field
     */
    private static String text(Map<?, ?> values, String key, int maximum) throws IOException {
        Object value = values.get(key);
        if (!(value instanceof String text) || text.isEmpty() || text.length() > maximum
                || text.chars().anyMatch(Character::isISOControl)) throw new IOException("Configuration rejected");
        return text;
    }

    /** Rejects symlinks, unexpected ownership, and writable ancestors.
     * @param path absolute target
     * @param directory whether target is directory
     * @throws IOException untrusted path
     */
    static void protectedPath(Path path, boolean directory) throws IOException {
        if (!path.isAbsolute() || !path.normalize().equals(path)) throw new IOException("Path rejected");
        String owner = System.getProperty("user.name");
        Path current = path;
        while (current != null) {
            PosixFileAttributes a = Files.readAttributes(current, PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            boolean target = current.equals(path);
            if (a.isSymbolicLink() || (!a.owner().getName().equals(owner) && !a.owner().getName().equals("root"))
                    || a.permissions().contains(PosixFilePermission.GROUP_WRITE)
                    || a.permissions().contains(PosixFilePermission.OTHERS_WRITE)) throw new IOException("Path rejected");
            if (target && (!a.owner().getName().equals(owner) || (directory ? !a.isDirectory() : !a.isRegularFile())
                    || !a.permissions().equals(java.nio.file.attribute.PosixFilePermissions.fromString(directory ? "rwx------" : "rw-------")))) throw new IOException("Path rejected");
            if (!target && !directory && current.equals(path.getParent()) && !a.permissions().equals(java.nio.file.attribute.PosixFilePermissions.fromString("rwx------"))) throw new IOException("Path rejected");
            current = current.getParent();
        }
    }
}
