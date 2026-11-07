package dev.allow.backend;

import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Map;
import java.util.UUID;

/** Owner-protected bounded durable pending-review queue. */
class AiAccessQueue {
    private final Path directory;
    /** Stores an externally validated queue directory.
     * @param directory private queue
     */
    AiAccessQueue(Path directory) { this.directory = directory; }
    /** Persists one pending record and synchronizes its directory entry.
     * @param form immutable verified form
     * @param now accepted timestamp
     * @param deadline challenge deadline
     * @param clock current time source
     * @return opaque record identifier
     * @throws IOException full, untrusted, or ambiguous persistence
     */
    synchronized String persist(AiAccessForm form, long now, long deadline, java.time.Clock clock) throws IOException {
        AiAccessConfig.protectedPath(directory, true);
        int count = 0;
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(directory)) {
            for (Path ignored : entries) if (++count >= 1000) throw new IOException("Queue full");
        }
        String id = UUID.randomUUID().toString();
        byte[] bytes = JsonWire.encode(Map.of("requestId", id, "status", "PENDING", "createdAt", now, "verifiedAt", now, "form", form));
        Path target = directory.resolve(id + ".json");
        if (clock.millis() >= deadline) throw new IOException("Expired");
        try (FileChannel output = FileChannel.open(target, java.util.Set.of(StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE),
                PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")))) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) output.write(buffer);
            if (clock.millis() >= deadline) throw new IOException("Expired");
            output.force(true);
        }
        try (FileChannel parent = FileChannel.open(directory, StandardOpenOption.READ)) { parent.force(true); }
        return id;
    }
}
