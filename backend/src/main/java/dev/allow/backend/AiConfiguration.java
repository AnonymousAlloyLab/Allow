package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Closed private pilot configuration; no provider authority is browser-selectable. */
@Component
final class AiConfiguration {
    private final String mode;
    private final String terms;
    private final String tariff;
    private final Path root;
    private final String ledger;
    private final long ceiling;
    private String credential = "";

    /** Validates explicit installation choices without enabling anonymous inference.
     * @param mode OFF, FIXTURE or REMOTE_ASSISTED
     * @param directory trusted installation directory
     * @param ledger external operator ledger
     * @param ceiling immutable configured lifetime micro-USD ceiling
     * @param terms reviewed terms version
     * @param tariff reviewed tariff version
     * @param keyFile protected external credential path
     * @param keyStdin explicit inherited startup pipe selection
     * @param access closed installation access mode
     * @throws IOException unavailable protected credential
     * @throws IllegalArgumentException denied or malformed boundary state
     */
    AiConfiguration(@Value("${allow.ai.mode:OFF}") String mode, @Value("${allow.corpus.root:}") String directory,
            @Value("${allow.ai.ledger:}") String ledger, @Value("${allow.ai.ceiling-micro-usd:100000}") long ceiling,
            @Value("${allow.ai.terms-version:}") String terms, @Value("${allow.ai.tariff-version:}") String tariff,
            @Value("${allow.ai.key-file:}") String keyFile, @Value("${allow.ai.key-stdin:false}") boolean keyStdin,
            AccessMode access) throws IOException {
        if (!Set.of("OFF", "FIXTURE", "REMOTE_ASSISTED").contains(mode)) throw new IllegalArgumentException("Unknown AI mode");
        this.mode = mode;
        this.root = directory.isBlank() ? null : Path.of(directory).toAbsolutePath().normalize();
        this.ledger = ledger;
        this.ceiling = ceiling;
        this.terms = terms.isBlank() ? "fixture-v1" : terms;
        this.tariff = tariff;
        if (!mode.equals("OFF")) validate(access, keyFile, keyStdin);
    }

    /** Checks enabled-private requirements and reads only explicitly supplied credentials.
     * @param access installation routing mode
     * @param keyFile operator credential path
     * @param keyStdin explicitly selected private pipe
     * @throws IOException unavailable credential source
     * @throws IllegalArgumentException denied or malformed boundary state
     */
    private void validate(AccessMode access, String keyFile, boolean keyStdin) throws IOException {
        if (access.anonymous() || root == null || ceiling < 50000 || ceiling > 10000000
                || ledger.isBlank() || !Path.of(ledger).isAbsolute() || Path.of(ledger).normalize().startsWith(root)) {
            throw new IllegalArgumentException("Invalid private AI configuration");
        }
        if (remote()) {
            if (terms.equals("fixture-v1") || tariff.isBlank() || (keyFile.isBlank() == !keyStdin)) {
                throw new IllegalArgumentException("Reviewed AI configuration required");
            }
            requireCoreDisabled();
            credential = keyStdin ? decode(System.in.readNBytes(4097)) : readKey(Path.of(keyFile));
        } else if (!keyFile.isBlank() || keyStdin) throw new IllegalArgumentException("Fixture credentials forbidden");
    }

    /** Refuses to load a credential while JVM core dumping remains enabled.
     * @throws IOException unavailable or unsafe process limits
     */
    private void requireCoreDisabled() throws IOException {
        for (String line : Files.readAllLines(Path.of("/proc/self/limits"))) {
            if (line.startsWith("Max core file size")) {
                String[] columns = line.substring("Max core file size".length()).trim().split("\\s+");
                if (columns.length >= 2 && columns[0].equals("0")) return;
                throw new IOException("Core dumps must be disabled");
            }
        }
        throw new IOException("Core limit unavailable");
    }

    /** Reads a bounded owner-only external file without accepting linked paths.
     * @param path protected operator path
     * @return credential retained only in private memory
     * @throws IOException insecure, linked or oversized credential source
     */
    private String readKey(Path path) throws IOException {
        if (!path.isAbsolute() || path.normalize().startsWith(root)) throw new IOException("Invalid credential source");
        protectedAncestors(path);
        var before = Files.readAttributes(path, java.nio.file.attribute.PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        credentialAttributes(path, before);
        java.nio.ByteBuffer bytes = java.nio.ByteBuffer.allocate(4097);
        try (var input = java.nio.channels.FileChannel.open(path, java.nio.file.StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            while (bytes.hasRemaining() && input.read(bytes) > 0) { /* The fixed buffer bounds even a growing input. */ }
        }
        var after = Files.readAttributes(path, java.nio.file.attribute.PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        credentialAttributes(path, after);
        protectedAncestors(path);
        if (!java.util.Objects.equals(before.fileKey(), after.fileKey()) || before.size() != after.size()
                || !before.lastModifiedTime().equals(after.lastModifiedTime())) throw new IOException("Credential identity changed");
        return decode(java.util.Arrays.copyOf(bytes.array(), bytes.position()));
    }

    /** Requires owner-private parent and trusted nonlinked ancestors before a credential open.
     * @param path operator-selected external credential
     * @throws IOException unsafe ancestor or owner
     */
    private void protectedAncestors(Path path) throws IOException {
        if (!path.normalize().equals(path)) throw new IOException("Invalid credential source");
        var serviceOwner = Files.getOwner(root);
        Path parent = path.getParent();
        if (parent == null || !Files.getOwner(parent, LinkOption.NOFOLLOW_LINKS).equals(serviceOwner)
                || !Files.getPosixFilePermissions(parent, LinkOption.NOFOLLOW_LINKS)
                    .equals(java.nio.file.attribute.PosixFilePermissions.fromString("rwx------"))) throw new IOException("Private credential parent required");
        for (Path item = parent; item != null; item = item.getParent()) {
            var attributes = Files.readAttributes(item, java.nio.file.attribute.PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            long uid = ((Number) Files.getAttribute(item, "unix:uid", LinkOption.NOFOLLOW_LINKS)).longValue();
            int mode = ((Number) Files.getAttribute(item, "unix:mode", LinkOption.NOFOLLOW_LINKS)).intValue();
            boolean stickyRoot = !item.equals(parent) && uid == 0 && (mode & 01000) != 0;
            if (!attributes.isDirectory() || (!attributes.owner().equals(serviceOwner) && uid != 0)
                    || ((mode & 0022) != 0 && !stickyRoot)) throw new IOException("Untrusted credential ancestor");
        }
    }

    /** Validates descriptor-adjacent identity under the owner-private parent trust boundary.
     * @param path protected credential path
     * @param attributes nonfollowing file attributes
     * @throws IOException unsafe file or oversized credential
     */
    private void credentialAttributes(Path path, java.nio.file.attribute.PosixFileAttributes attributes) throws IOException {
        if (!attributes.isRegularFile() || attributes.fileKey() == null || attributes.size() > 4096
                || ((Number) Files.getAttribute(path, "unix:nlink", LinkOption.NOFOLLOW_LINKS)).longValue() != 1
                || !attributes.owner().equals(Files.getOwner(root))
                || !attributes.permissions().equals(java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"))) {
            throw new IOException("Invalid credential source");
        }
    }

    /** Validates only an ASCII non-whitespace key without echoing malformed bytes.
     * @param bytes bounded private input
     * @return nonempty credential
     * @throws IOException malformed credential
     */
    private String decode(byte[] bytes) throws IOException {
        if (bytes.length == 0 || bytes.length > 4096) throw new IOException("Invalid credential source");
        String value = new String(bytes, StandardCharsets.US_ASCII).stripTrailing();
        for (byte item : bytes) if (item < 0) throw new IOException("Invalid credential source");
        if (value.isEmpty() || value.chars().anyMatch(Character::isWhitespace)) throw new IOException("Invalid credential source");
        return value;
    }

    /** Provides authenticated nonsecret UI configuration.
     * @return bounded immutable-by-convention configuration
     */
    ObjectNode view() {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("mode", mode).put("model", "gpt-6.1-sol").put("termsVersion", terms);
        result.putObject("limits").put("jobSeconds", 60).put("calls", 2).put("sourceBytes", 32768).put("intentBytes", 4096);
        return result;
    }

    /** Requires an explicitly enabled private integration.
     * @throws AiFailure disabled installation
     */
    void requireEnabled() { if (mode.equals("OFF")) throw new AiFailure("AI_DISABLED"); }

    /** Identifies the selected paid provider.
     * @return whether remote inference is enabled
     */
    boolean remote() { return mode.equals("REMOTE_ASSISTED"); }

    /** Returns the trusted package root.
     * @return fixed installation path
     */
    Path root() { return root; }

    /** Returns the exact immutable configuration binding.
     * @return nonsecret configuration identity
     */
    String binding() { return mode + ":" + terms + ":" + tariff + ":" + ceiling; }

    /** Builds the only credential-bearing frame; callers never log or retain it.
     * @return fresh private initial provider choices
     */
    ObjectNode start() {
        return JsonNodeFactory.instance.objectNode().put("provider", mode).put("credential", credential)
                .put("ledger", ledger).put("ceiling", ceiling);
    }
    /** Drops the retained credential reference on shutdown without claiming memory erasure. */
    @jakarta.annotation.PreDestroy
    void closeCredential() { credential = ""; }

}
