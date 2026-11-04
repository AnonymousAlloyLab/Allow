package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;

/** Private immutable gate evidence; never part of the production authority path. */
final class WarmProbeFiles {
    private final Path directory;

    /** Captures the existing private evidence directory under the copied installation.
     * @param root canonical copied installation
     * @throws IOException unavailable or aliased evidence directory
     */
    WarmProbeFiles(Path root) throws IOException {
        directory = root.resolve(".gate/evidence");
        require(directory.toRealPath().equals(directory), "Evidence directory alias");
    }

    /** Requires a concrete finite probe assertion rather than converting uncertainty to success.
     * @param condition actual observed predicate
     * @param message bounded infrastructure-only diagnostic
     * @throws IOException failed probe predicate
     */
    static void require(boolean condition, String message) throws IOException {
        if (!condition) throw new IOException(message);
    }

    /** Writes one non-overwriting private JSON artifact and returns its bound reference.
     * @param name fixed case-derived basename
     * @param value complete evidence value
     * @return relative path and exact SHA256
     * @throws IOException unavailable evidence storage
     */
    ObjectNode save(String name, JsonNode value) throws IOException {
        require(name.matches("[a-z0-9-]+\\.json"), "Invalid evidence basename");
        Path path = directory.resolve(name);
        byte[] bytes = JsonWire.encode(value);
        Files.createFile(path, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
        Files.write(path, bytes, StandardOpenOption.WRITE);
        return com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode()
                .put("path", name).put("sha256", Hashes.bytes(bytes));
    }

    /** Reads the exact registered fixture without accepting traversal or an unbound file.
     * @param casesPath frozen case manifest location
     * @param item one registered case
     * @return complete private protocol fixture
     * @throws IOException malformed path, changed fixture or invalid JSON
     */
    static JsonNode fixture(Path casesPath, JsonNode item) throws IOException {
        Path relative = Path.of(item.path("fixture").textValue());
        require(!relative.isAbsolute() && relative.normalize().equals(relative)
                && relative.getParent().equals(Path.of("fixtures/semantic")), "Invalid fixture path");
        Path path = casesPath.getParent().resolve(relative);
        require(path.toRealPath().equals(path), "Fixture alias");
        byte[] bytes = Files.readAllBytes(path);
        require(Hashes.bytes(bytes).equals(item.path("fixture_sha256").textValue()), "Fixture changed");
        return JsonWire.decode(bytes, JsonNode.class);
    }
}
