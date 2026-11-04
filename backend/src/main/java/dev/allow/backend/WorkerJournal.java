package dev.allow.backend;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/** Exclusive, metadata-only journal with forced temporary writes and atomic replacement. */
final class WorkerJournal implements AutoCloseable {
    private static final ObjectMapper JSON = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final Set<Path> LOCAL_OWNERS = new HashSet<>();
    private final Path directory;
    private boolean registered;
    private FileChannel directoryChannel;
    private FileChannel lockChannel;
    private FileLock lock;

    /** Acquires private durable ownership without creating an insecure workspace.
     * @param directory pre-provisioned canonical private directory
     * @throws IOException unsafe path or another ledger owner
     */
    WorkerJournal(Path directory) throws IOException {
        this.directory = directory;
        requirePrivate(directory, true);
        register(directory);
        registered = true;
        try {
            directoryChannel = FileChannel.open(directory, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS);
            lockChannel = FileChannel.open(directory.resolve("pool.lock"), Set.of(StandardOpenOption.CREATE,
                    StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS),
                    PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
            requirePrivate(directory.resolve("pool.lock"), false);
            lock = lockChannel.tryLock();
            if (lock == null) throw new IOException("Worker pool already owned");
        } catch (IOException | OverlappingFileLockException failure) {
            close();
            throw new IOException("Worker journal ownership unavailable", failure);
        }
    }

    /** Prevents opening a second descriptor that could disturb process-wide POSIX file locks.
     * @param path canonical metadata directory
     * @throws IOException an owner in this JVM already exists
     */
    private static synchronized void register(Path path) throws IOException {
        if (!LOCAL_OWNERS.add(path)) throw new IOException("Worker journal already owned locally");
    }

    /** Removes local ownership only after all locking descriptors were closed.
     * @param path canonical metadata directory
     */
    private static synchronized void unregister(Path path) { LOCAL_OWNERS.remove(path); }

    /** Loads only a bounded closed operational schema.
     * @return prior journal or null on the first installation
     * @throws IOException malformed or unsafe durable state
     */
    ObjectNode read() throws IOException {
        Path path = directory.resolve("pool.json");
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) return null;
        requirePrivate(path, false);
        if (Files.size(path) > 32768) throw new IOException("Worker journal exceeds bound");
        byte[] bytes;
        try (var input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) { bytes = input.readNBytes(32769); }
        if (bytes.length > 32768) throw new IOException("Worker journal exceeds bound");
        JsonNode node = JSON.readTree(bytes);
        validate(node);
        return (ObjectNode) node;
    }

    /** Loads strict prior state and permits a new root only after durable release of every slot.
     * @param root newly verified canonical delegated root
     * @return unchanged prior metadata, preserving generation counters, or null initially
     * @throws IOException root changed with any outstanding reservation or malformed metadata
     */
    ObjectNode readForRoot(Path root) throws IOException {
        ObjectNode prior = read();
        if (prior == null || prior.path("cgroupRoot").textValue().equals(root.toString())) return prior;
        for (JsonNode slot : prior.path("slots")) {
            if (!slot.isNull()) throw new IOException("Outstanding worker root changed");
        }
        return prior;
    }

    /** Commits a complete schema-checked record before a dependent external action.
     * @param state operational metadata only
     * @throws IOException failed forced write, rename or directory force
     */
    void write(ObjectNode state) throws IOException {
        validate(state);
        byte[] bytes = JSON.writeValueAsBytes(state);
        if (bytes.length > 32768) throw new IOException("Worker journal exceeds bound");
        Path temporary = directory.resolve(".pool-" + UUID.randomUUID() + ".tmp");
        try {
            forceTemporary(temporary, bytes);
            Files.move(temporary, directory.resolve("pool.json"), StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
            directoryChannel.force(true);
        } finally { Files.deleteIfExists(temporary); }
    }

    /** Forces every byte of a newly created private temporary record.
     * @param path unique temporary file
     * @param bytes bounded serialized metadata
     * @throws IOException write or fsync failure
     */
    private static void forceTemporary(Path path, byte[] bytes) throws IOException {
        try (FileChannel channel = FileChannel.open(path, Set.of(StandardOpenOption.CREATE_NEW,
                StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS),
                PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")))) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) channel.write(buffer);
            channel.force(true);
        }
    }

    /** Rejects links, nonprivate modes and noncanonical metadata paths.
     * @param path metadata file or directory
     * @param isDirectory whether this must be a directory
     * @throws IOException unsafe ownership metadata
     */
    private static void requirePrivate(Path path, boolean isDirectory) throws IOException {
        String mode = isDirectory ? "rwx------" : "rw-------";
        boolean kind = isDirectory ? Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)
                : Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS);
        long uid = ((Number) Files.getAttribute(Path.of("/proc/self"), "unix:uid")).longValue();
        if (((Number) Files.getAttribute(path, "unix:uid", LinkOption.NOFOLLOW_LINKS)).longValue() != uid) {
            throw new IOException("Worker journal owner mismatch");
        }
        if (!kind || !path.isAbsolute() || !path.toRealPath().equals(path)
                || !Files.getPosixFilePermissions(path).equals(PosixFilePermissions.fromString(mode))) {
            throw new IOException("Private worker journal required");
        }
        if (!isDirectory && ((Number) Files.getAttribute(path, "unix:nlink")).longValue() != 1) {
            throw new IOException("Linked worker journal rejected");
        }
    }

    /** Validates all durable fields without accepting private payload additions.
     * @param state complete serialized state
     * @throws IOException invalid schema or values
     */
    private static void validate(JsonNode state) throws IOException {
        fields(state, Set.of("schema", "poolNonce", "ownerPid", "ownerStartTicks", "bootId", "build",
                "policy", "generations", "slots", "cgroupRoot"));
        if (!state.path("schema").isInt() || state.path("schema").intValue() != 1) invalid();
        uuid(state.path("poolNonce"));
        uuid(state.path("bootId"));
        number(state.path("ownerPid"), 1);
        text(state.path("ownerStartTicks"), "[0-9]+", 32);
        text(state.path("build"), "[0-9a-f]{64}", 64);
        text(state.path("policy"), "[^\\x00\\r\\n]+", 256);
        text(state.path("cgroupRoot"), "/[^\\x00\\r\\n]+", 4096);
        if (!state.path("generations").isArray() || state.path("generations").size() != 2
                || !state.path("slots").isArray() || state.path("slots").size() != 2) invalid();
        for (int slot = 0; slot < 2; slot++) {
            number(state.path("generations").get(slot), 0);
            JsonNode record = state.path("slots").get(slot);
            if (!record.isNull()) validateSlot(state, record, slot);
        }
    }

    /** Checks each slot's closed identity and operational state.
     * @param state root owner metadata
     * @param slot serialized generation
     * @param index required slot index
     * @throws IOException invalid generation metadata
     */
    private static void validateSlot(JsonNode state, JsonNode slot, int index) throws IOException {
        fields(slot, Set.of("slot", "generation", "nonce", "standby", "phase", "attempted", "poisoned",
                "assigned", "published", "childPid", "childStartTicks", "group", "device", "inode"));
        number(slot.path("slot"), 0);
        number(slot.path("generation"), 1);
        if (slot.path("slot").longValue() != index || slot.path("generation").longValue()
                != state.path("generations").get(index).longValue()) invalid();
        uuid(slot.path("nonce"));
        for (String name : Set.of("standby", "attempted", "poisoned", "assigned", "published")) {
            if (!slot.path(name).isBoolean()) invalid();
        }
        text(slot.path("phase"), "RESERVED|STARTING|READY|ASSIGNED|STAGED|RETIRING|CLEAN|UNKNOWN", 16);
        number(slot.path("childPid"), 0);
        text(slot.path("childStartTicks"), "[0-9]*", 32);
        number(slot.path("device"), 0);
        number(slot.path("inode"), 1);
        String group = "pool-" + state.path("poolNonce").textValue() + "/slot-" + index
                + "-g" + slot.path("generation").longValue();
        if (!slot.path("group").isTextual() || !group.equals(slot.path("group").textValue())) invalid();
        if ((slot.path("childPid").longValue() == 0) != slot.path("childStartTicks").textValue().isEmpty()) invalid();
        if (!slot.path("attempted").booleanValue() && slot.path("childPid").longValue() != 0) invalid();
    }

    /** Requires an exact object field set.
     * @param node candidate object
     * @param expected closed field names
     * @throws IOException missing, extra or nonobject state
     */
    private static void fields(JsonNode node, Set<String> expected) throws IOException {
        if (node == null || !node.isObject()) invalid();
        Set<String> actual = new HashSet<>();
        node.fieldNames().forEachRemaining(actual::add);
        if (!actual.equals(expected)) invalid();
    }
    /** Checks a bounded nonnegative integer.
     * @param node serialized integer
     * @param minimum inclusive lower bound
     * @throws IOException invalid numeric value
     */
    private static void number(JsonNode node, long minimum) throws IOException {
        if (!node.isIntegralNumber() || !node.canConvertToLong() || node.longValue() < minimum) invalid();
    }
    /** Checks a closed bounded string.
     * @param node serialized string
     * @param pattern accepted syntax
     * @param maximum byte-safe ASCII length bound
     * @throws IOException invalid string
     */
    private static void text(JsonNode node, String pattern, int maximum) throws IOException {
        if (!node.isTextual() || node.textValue().length() > maximum || !node.textValue().matches(pattern)) invalid();
    }
    /** Checks canonical UUID spelling.
     * @param node serialized nonce
     * @throws IOException invalid nonce
     */
    private static void uuid(JsonNode node) throws IOException {
        text(node, "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", 36);
    }
    /** Fails without echoing journal contents.
     * @throws IOException closed-schema rejection
     */
    private static void invalid() throws IOException { throw new IOException("Invalid worker journal"); }

    /** Releases exclusive ownership after the coordinator has retired its workers.
     * @throws IOException failed descriptor close
     */
    @Override
    public void close() throws IOException {
        IOException failure = null;
        for (AutoCloseable handle : new AutoCloseable[] {lock, lockChannel, directoryChannel}) {
            if (handle == null) continue;
            try { handle.close(); }
            catch (Exception error) {
                if (failure == null) failure = new IOException("Worker journal close failed");
                failure.addSuppressed(error);
            }
        }
        if (failure != null) throw failure;
        if (registered) { unregister(directory); registered = false; }
    }
}
