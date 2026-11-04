package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Base64;
import java.util.Set;

/** Gate-only complete-response probe using the real fresh sandbox and transport. */
public final class FreshTier1ProbeMain {
    /** Prevents construction of the gate entrypoint. */
    private FreshTier1ProbeMain() {}

    /** Writes a private result record; unexpected harness errors expose only a fixed code.
     * @param arguments exact target, fixed profile, input and output path pairs
     */
    public static void main(String[] arguments) {
        try {
            Options options = options(arguments);
            write(options.output(), run(options));
        } catch (Exception failure) {
            System.err.println("fresh_probe_failed");
            System.exit(2);
        }
    }

    /** Parses a closed gate-only interface with no arbitrary JVM option channel.
     * @param arguments fixed ordered argument pairs
     * @return validated probe selection
     * @throws IOException invalid invocation or profile
     */
    private static Options options(String[] arguments) throws IOException {
        if (arguments.length != 8 || !arguments[0].equals("--target") || !arguments[2].equals("--profile")
                || !arguments[4].equals("--input") || !arguments[6].equals("--output")) {
            throw new IOException("Invalid probe arguments");
        }
        WorkerLaunchProfile profile = switch (arguments[3]) {
            case "F0" -> WorkerLaunchProfile.DEFAULT;
            case "F1" -> WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1;
            default -> throw new IOException("Invalid probe profile");
        };
        return new Options(Path.of(arguments[1]), profile, Path.of(arguments[5]), Path.of(arguments[7]));
    }

    /** Executes one authored private frame while retaining complete bounded response bytes.
     * @param options fixed gate selection
     * @return complete content-private outcome record
     * @throws IOException unavailable input
     */
    private static ObjectNode run(Options options) throws IOException {
        byte[] input = input(options.input());
        ObjectNode record = JsonNodeFactory.instance.objectNode().put("schemaVersion", 1)
                .put("profile", options.profile().name()).put("inputSha256", Hashes.bytes(input))
                .put("inputBytes", input.length).put("outcome", "LAUNCH_UNAVAILABLE").put("noWorkerStarted", true);
        if (input.length >= 2097152) {
            return record.put("outcome", "INPUT_REJECTED").put("rejectionCode", "PRIVATE_INPUT_LIMIT");
        }
        long started = System.nanoTime();
        try {
            BubblewrapLauncher launcher = new BubblewrapLauncher(options.target(), true, options.profile());
            record.put("constructorNanos", System.nanoTime() - started).put("buildIdentity", launcher.identity());
            long launchStart = System.nanoTime();
            Process child = launcher.launch();
            record.put("launchNanos", System.nanoTime() - launchStart).put("noWorkerStarted", false);
            exchange(child, input, record);
        } catch (IOException failure) {
            record.put("outcome", "LAUNCH_UNAVAILABLE");
        } finally {
            record.put("totalNanos", System.nanoTime() - started);
        }
        return record;
    }

    /** Uses production frame exchange and reaps even after identity, timeout or output failure.
     * @param child process owned by this single probe
     * @param input exact frozen request bytes without added framing
     * @param record private outcome receiving bounded evidence
     */
    private static void exchange(Process child, byte[] input, ObjectNode record) {
        record.put("workerPid", child.pid());
        long started = System.nanoTime();
        try {
            record.put("workerStartTicks", ProcessIdentity.startTicks(child.pid()));
            byte[] bytes = FrameProcess.exchange(child, input, 1048577, 10000);
            record.put("responseBase64", Base64.getEncoder().encodeToString(bytes));
            record.put("responseBytes", bytes.length).put("responseSha256", Hashes.bytes(bytes));
            response(input, bytes, record);
        } catch (IOException | IllegalArgumentException failure) {
            record.put("outcome", "WORKER_UNAVAILABLE");
        } catch (InterruptedException failure) {
            record.put("outcome", "INTERRUPTED");
            Thread.currentThread().interrupt();
        } finally {
            record.put("exchangeNanos", System.nanoTime() - started);
            long reapStarted = System.nanoTime();
            FrameProcess.reap(child);
            record.put("reapNanos", System.nanoTime() - reapStarted).put("reaped", !child.isAlive());
            record.put("workerExitCode", child.exitValue());
        }
    }

    /** Requires the same complete response identity as production without normalizing data.
     * @param input exact request bytes
     * @param bytes complete captured output including framing
     * @param record private outcome receiving identity validation
     * @throws IOException malformed or unrelated envelope
     */
    private static void response(byte[] input, byte[] bytes, ObjectNode record) throws IOException {
        JsonNode request = DocumentJson.decode(input);
        JsonNode result = DocumentJson.decode(bytes);
        DocumentJson.fields(result, "protocol", "requestId", "status", "data");
        if (!request.path("requestId").isTextual() || !result.path("protocol").isInt()
                || result.path("protocol").intValue() != 1
                || !request.path("requestId").equals(result.path("requestId"))
                || !Set.of("VALIDATED", "INVALID", "UNAVAILABLE").contains(result.path("status").asText())) {
            throw new IOException("Probe response identity mismatch");
        }
        record.put("outcome", "COMPLETE_RESPONSE").put("requestIdentityMatches", true);
        record.put("workerStatus", result.path("status").textValue());
    }

    /** Reads only a regular bounded input, preserving its original private frame bytes.
     * @param path frozen request file
     * @return exact unframed request bytes
     * @throws IOException missing, symlinked or larger-than-capture input
     */
    private static byte[] input(Path path) throws IOException {
        if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Invalid probe input");
        try (var stream = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = stream.readNBytes(2097153);
            if (stream.read() != -1) throw new IOException("Probe input capture exceeds limit");
            return bytes;
        }
    }

    /** Creates a new owner-only result file without following or overwriting an existing path.
     * @param path private gate evidence destination
     * @param record complete bounded probe result
     * @throws IOException output collision or unavailable private storage
     */
    private static void write(Path path, ObjectNode record) throws IOException {
        var options = Set.of(StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        var permissions = PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------"));
        try (var channel = Files.newByteChannel(path, options, permissions)) {
            ByteBuffer bytes = ByteBuffer.wrap(JsonWire.encode(record));
            while (bytes.hasRemaining()) channel.write(bytes);
        }
    }

    /** Immutable gate inputs contain no JVM arguments or shared worker state. */
    private record Options(Path target, WorkerLaunchProfile profile, Path input, Path output) {}
}
