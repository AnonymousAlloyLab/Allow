package dev.allow.backend;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.SecureDirectoryStream;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributeView;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** Descriptor-owned cgroup generation; paths are never used for process killing. */
final class WorkerCgroup implements AutoCloseable {
    private final Path root;
    private final String relative;
    private final long device;
    private final long inode;
    private final Object key;
    private final SecureDirectoryStream<Path> parent;
    private final SecureDirectoryStream<Path> directory;
    private final Path component;
    private SeekableByteChannel events;
    private SeekableByteChannel kill;
    private Map<String, String> terminal = Map.of();

    /** Captures a generated directory and independently binds its descriptor identity.
     * @param root canonical delegated root
     * @param relative closed generated pool/group path
     * @param parent retained pool descriptor
     * @param directory retained group descriptor
     * @throws IOException changed or unsupported directory identity
     */
    private WorkerCgroup(Path root, String relative, SecureDirectoryStream<Path> parent,
            SecureDirectoryStream<Path> directory) throws IOException {
        this.root = root;
        this.relative = relative;
        this.parent = parent;
        this.directory = directory;
        this.component = Path.of(relative).getFileName();
        this.key = directory.getFileAttributeView(BasicFileAttributeView.class).readAttributes().fileKey();
        Path path = root.resolve(relative);
        this.device = (Long) Files.getAttribute(path, "unix:dev", LinkOption.NOFOLLOW_LINKS);
        this.inode = (Long) Files.getAttribute(path, "unix:ino", LinkOption.NOFOLLOW_LINKS);
        if (key == null || !key.equals(Files.readAttributes(path, BasicFileAttributes.class,
                LinkOption.NOFOLLOW_LINKS).fileKey())) throw new IOException("Worker group identity changed");
    }

    /** Creates only a generated private group below an already delegated private pool.
     * @param root canonical delegated root
     * @param relative closed pool/slot-generation path
     * @return retained exact group ownership
     * @throws IOException unsupported delegation or failed limits
     */
    static WorkerCgroup create(Path root, String relative) throws IOException {
        validate(root, relative);
        Path path = root.resolve(relative);
        Files.createDirectory(path);
        WorkerCgroup result = open(root, relative);
        try {
            result.write("pids.max", "32");
            result.write("memory.max", "1073741824");
            result.write("memory.swap.max", "0");
            result.requireLimits();
            if (!result.empty()) throw new IOException("New worker group is occupied");
            return result;
        } catch (IOException | RuntimeException failure) {
            failedCreation(result, failure);
            throw failure;
        }
    }

    /** Attempts exact empty removal after a captured setup failure and always closes descriptors.
     * @param owner complete captured identity, before any process launch was authorized
     * @param failure original setup error receiving cleanup diagnostics
     */
    private static void failedCreation(WorkerCgroup owner, Exception failure) {
        try { owner.remove(); }
        catch (IOException | RuntimeException removal) {
            if (removal != failure) failure.addSuppressed(removal);
        }
        try { owner.close(); }
        catch (IOException | RuntimeException closure) {
            if (closure != failure) failure.addSuppressed(closure);
        }
    }

    /** Opens existing ownership for conservative restart reconciliation.
     * @param root canonical delegated root
     * @param relative closed generated group path
     * @return captured descriptor owner
     * @throws IOException missing, symlinked or changed group
     */
    static WorkerCgroup open(Path root, String relative) throws IOException {
        validate(root, relative);
        SecureDirectoryStream<Path> parent = secure(root.resolve(Path.of(relative).getParent()));
        SecureDirectoryStream<Path> directory = null;
        WorkerCgroup result = null;
        try {
            directory = parent.newDirectoryStream(Path.of(relative).getFileName(), LinkOption.NOFOLLOW_LINKS);
            result = new WorkerCgroup(root, relative, parent, directory);
            result.events = result.openFile("cgroup.events", false);
            result.kill = result.openFile("cgroup.kill", true);
            return result;
        } catch (IOException failure) {
            if (result != null) result.close();
            else { if (directory != null) directory.close(); parent.close(); }
            throw failure;
        }
    }

    /** Rejects arbitrary paths and non-cgroup filesystems before any group mutation.
     * @param root trusted delegated root
     * @param relative generated group path
     * @throws IOException unsupported ownership
     */
    private static void validate(Path root, String relative) throws IOException {
        if (!root.isAbsolute() || !root.toRealPath().equals(root)
                || !Files.getFileStore(root).type().equals("cgroup2")
                || !relative.matches("pool-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/slot-[01]-g[1-9][0-9]*")) {
            throw new IOException("Worker delegation unavailable");
        }
    }

    /** Opens a no-follow secure directory without silently downgrading ownership.
     * @param path canonical directory
     * @return retained directory descriptor
     * @throws IOException unsupported provider or symlink
     */
    private static SecureDirectoryStream<Path> secure(Path path) throws IOException {
        if (!path.toRealPath().equals(path)) throw new IOException("Worker group link rejected");
        DirectoryStream<Path> stream = Files.newDirectoryStream(path);
        if (stream instanceof SecureDirectoryStream<Path> secure) return secure;
        stream.close();
        throw new IOException("Descriptor directory operations unavailable");
    }

    /** Opens a control file relative to the retained generation descriptor.
     * @param name fixed kernel control filename
     * @param writing whether write access is required
     * @return owned channel
     * @throws IOException missing or unsafe kernel control
     */
    private SeekableByteChannel openFile(String name, boolean writing) throws IOException {
        return directory.newByteChannel(Path.of(name), Set.of(LinkOption.NOFOLLOW_LINKS,
                writing ? StandardOpenOption.WRITE : StandardOpenOption.READ));
    }

    /** Writes one fixed kernel control value through the captured directory.
     * @param name fixed control filename
     * @param value bounded trusted value
     * @throws IOException short or failed kernel write
     */
    private void write(String name, String value) throws IOException {
        try (SeekableByteChannel channel = openFile(name, true)) {
            ByteBuffer data = StandardCharsets.US_ASCII.encode(value);
            if (channel.write(data) != value.length()) throw new IOException("Worker control write incomplete");
        }
    }

    /** Reads a bounded kernel metadata file through its retained descriptor.
     * @param channel exact owned control descriptor
     * @return ASCII metadata
     * @throws IOException unavailable, oversized or malformed metadata
     */
    private static String read(SeekableByteChannel channel) throws IOException {
        channel.position(0);
        ByteBuffer data = ByteBuffer.allocate(32769);
        while (data.hasRemaining() && channel.read(data) > 0) { /* Bounded kernel metadata only. */ }
        if (!data.hasRemaining()) throw new IOException("Worker metadata exceeds bound");
        data.flip();
        return StandardCharsets.US_ASCII.decode(data).toString();
    }

    /** Reads a fixed metadata filename.
     * @param name kernel metadata filename
     * @return bounded metadata
     * @throws IOException unavailable metadata
     */
    private String read(String name) throws IOException {
        try (SeekableByteChannel channel = openFile(name, false)) { return read(channel); }
    }

    /** Checks exact limits after writing them, before a helper may start.
     * @throws IOException kernel limits differ from the approved bounds
     */
    private void requireLimits() throws IOException {
        if (!read("pids.max").trim().equals("32") || !read("memory.max").trim().equals("1073741824")
                || !read("memory.swap.max").trim().equals("0")) throw new IOException("Worker limits unavailable");
    }

    /** Returns positive empty evidence; missing or malformed state is not absence.
     * @return whether populated is exactly zero
     * @throws IOException unavailable or ambiguous kernel observation
     */
    boolean empty() throws IOException {
        int found = 0;
        boolean empty = false;
        for (String line : read(events).split("\n")) {
            if (line.startsWith("populated ")) {
                found++;
                if (!line.equals("populated 0") && !line.equals("populated 1")) throw new IOException("Invalid populated state");
                empty = line.equals("populated 0");
            }
        }
        if (found != 1) throw new IOException("Missing populated observation");
        return empty;
    }

    /** Requests termination only through the already captured generation descriptor.
     * @throws IOException failed kernel request; capacity must remain reserved
     */
    void kill() throws IOException {
        kill.position(0);
        if (kill.write(StandardCharsets.US_ASCII.encode("1")) != 1) throw new IOException("Worker kill incomplete");
    }

    /** Captures terminal resource evidence after positive emptiness.
     * @throws IOException incomplete observations
     */
    void captureTerminal() throws IOException {
        if (!empty()) throw new IOException("Worker group remains occupied");
        Map<String, String> observed = new LinkedHashMap<>();
        observed.put("cgroup.events", read(events));
        for (String name : new String[] {"memory.peak", "memory.events", "pids.peak", "pids.events", "cpu.stat"}) {
            observed.put(name, read(name));
        }
        terminal = Map.copyOf(observed);
    }

    /** Removes only the captured empty directory, rejecting a replacement at its name.
     * @throws IOException missing or changed identity or nonempty group
     */
    void remove() throws IOException {
        Object current = parent.getFileAttributeView(component, BasicFileAttributeView.class,
                LinkOption.NOFOLLOW_LINKS).readAttributes().fileKey();
        if (!key.equals(current) || !empty()) throw new IOException("Worker group removal lacks evidence");
        parent.deleteDirectory(component);
    }

    /** Returns the generated relative path.
     * @return pool and slot-generation components
     */
    String relative() { return relative; }
    /** Returns the captured kernel device.
     * @return device number
     */
    long device() { return device; }
    /** Returns the captured directory inode.
     * @return positive inode number
     */
    long inode() { return inode; }
    /** Returns immutable terminal resource observations.
     * @return empty until terminal capture
     */
    Map<String, String> terminal() { return terminal; }

    /** Closes every retained descriptor, aggregating failures without omitting later closes.
     * @throws IOException one or more descriptor closes failed
     */
    @Override
    public void close() throws IOException {
        IOException failure = null;
        for (AutoCloseable handle : new AutoCloseable[] {events, kill, directory, parent}) {
            if (handle == null) continue;
            try { handle.close(); }
            catch (Exception error) {
                if (failure == null) failure = new IOException("Worker descriptor close failed");
                failure.addSuppressed(error);
            }
        }
        if (failure != null) throw failure;
    }
}
