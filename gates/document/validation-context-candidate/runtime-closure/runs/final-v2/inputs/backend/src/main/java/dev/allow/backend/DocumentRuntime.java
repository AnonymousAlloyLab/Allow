package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Exclusive durable workspace incarnation and installed validator policy fence. */
@Component
final class DocumentRuntime {
    private final String dependency;
    private final String policy;
    private FileChannel channel;
    private FileLock lock;
    private boolean ready;

    /** Locks the private workspace and installs its exact trusted build policy on startup.
     * @param gateway private operation-only store bridge
     * @param directory trusted installation root; blank disables document endpoints
     * @throws IOException unavailable installation, identity or exclusive ownership
     * @throws InterruptedException interrupted store initialization
     */
    DocumentRuntime(DocumentGateway gateway, @Value("${allow.corpus.root:}") String directory)
            throws IOException, InterruptedException {
        dependency = directory.isBlank() ? "unavailable" : BuildIdentity.read(Path.of("target"));
        policy = "document-v1:" + dependency;
        if (directory.isBlank()) return;
        try {
            acquire(Path.of(directory).toAbsolutePath().normalize().resolve(".runtime/documents"));
            initialize(gateway);
            ready = true;
        } catch (IOException | InterruptedException | RuntimeException failure) {
            close();
            throw failure;
        }
    }

    /** Rejects unsafe directory links and concurrent local server incarnations.
     * @param directory provisioned private workspace metadata directory
     * @throws IOException missing or unsafe identity/lock
     */
    private void acquire(Path directory) throws IOException {
        if (!Files.isDirectory(directory, LinkOption.NOFOLLOW_LINKS)
                || !directory.toRealPath().equals(directory)
                || !Files.getPosixFilePermissions(directory).equals(PosixFilePermissions.fromString("rwx------"))) {
            throw new IOException("Bootstrap private document storage before launch");
        }
        Path path = directory.resolve("server.lock");
        channel = FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-------"));
        lock = channel.tryLock();
        if (lock == null) throw new IOException("Document workspace already has a server owner");
    }

    /** Serializes a trusted software-policy installation using the existing workspace lock.
     * @param gateway authenticated internal store
     * @throws IOException unavailable policy transaction
     * @throws InterruptedException interrupted store operation
     */
    private void initialize(DocumentGateway gateway) throws IOException, InterruptedException {
        JsonNode reply = gateway.request("init", JsonNodeFactory.instance.objectNode().put("policyVersion", policy));
        if (!reply.path("status").asText().equals("OK")) throw new IOException("Document store unavailable");
        JsonNode data = reply.path("data");
        if (data.path("status").asText().equals("POLICY_MISMATCH")) {
            JsonNode installed = gateway.request("policy", JsonNodeFactory.instance.objectNode()
                    .put("expectedPolicyVersion", data.path("policyVersion").textValue()).put("policyVersion", policy));
            if (!installed.path("status").asText().equals("OK")) throw new IOException("Policy installation unavailable");
            reply = gateway.request("init", JsonNodeFactory.instance.objectNode().put("policyVersion", policy));
        }
        if (!reply.path("status").asText().equals("OK") || !reply.path("data").path("status").asText().equals("READY")) {
            throw new IOException("Document policy is not ready");
        }
    }

    /** Requires an initialized private workspace before document operations.
     * @throws IOException document runtime disabled or closed
     */
    void requireReady() throws IOException {
        if (!ready) throw new IOException("Document runtime unavailable");
    }

    /** Returns the installed immutable policy identity.
     * @return version bound to the exact local validator build
     */
    String policy() { return policy; }

    /** Returns the pinned worker build identity.
     * @return complete class/dependency hash
     */
    String dependency() { return dependency; }

    /** Releases incarnation authority only when the owning application stops. */
    @PreDestroy
    void close() {
        ready = false;
        try { if (lock != null) lock.release(); }
        catch (IOException ignored) { /* Closing the owned descriptor releases the kernel lock. */ }
        try { if (channel != null) channel.close(); }
        catch (IOException ignored) { /* Process termination remains the final ownership boundary. */ }
    }
}
