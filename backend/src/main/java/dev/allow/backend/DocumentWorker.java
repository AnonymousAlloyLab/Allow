package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Path;
import java.util.UUID;

/** Runs authoritative document validation only inside the pinned sandbox. */
final class DocumentWorker {
    private final SandboxLauncher launcher;
    private final ProcessIdentity.Reader identityReader;
    private final WorkerLaunchProfile profile;
    private long pid;
    private String startTicks;
    private boolean reaped;
    private boolean startupUncertain;

    /** Captures the exact build identity before any document can be validated.
     * @throws IOException unavailable build
     */
    DocumentWorker() throws IOException {
        this(WorkerLaunchProfile.DEFAULT);
    }

    /** Selects a fixed package-owned profile for an advisory-only worker.
     * @param profile trusted compiler choice, never a public request field
     * @throws IOException unavailable build
     */
    DocumentWorker(WorkerLaunchProfile profile) throws IOException {
        this(new BubblewrapLauncher(Path.of("target"), true, profile), ProcessIdentity::startTicks, profile);
    }

    /** Installs process seams for lifecycle tests without changing production sandbox selection.
     * @param launcher owned process factory
     * @param identityReader kernel incarnation reader
     */
    DocumentWorker(SandboxLauncher launcher, ProcessIdentity.Reader identityReader) {
        this(launcher, identityReader, WorkerLaunchProfile.DEFAULT);
    }

    /** Retains immutable profile authority alongside the owned launch and identity seams.
     * @param launcher owned process factory
     * @param identityReader kernel incarnation reader
     * @param profile fixed trusted launch profile
     */
    private DocumentWorker(SandboxLauncher launcher, ProcessIdentity.Reader identityReader, WorkerLaunchProfile profile) {
        this.profile = profile;
        this.launcher = launcher;
        this.identityReader = identityReader;
    }

    /** Validates one candidate under the caller's already held shared worker permit.
     * @param candidate exact submitted candidate
     * @param base authorized immutable base artifact
     * @param inventory authorized existing ID-to-kind subset
     * @param policy current frozen parser/policy version
     * @return checked result or deterministic diagnostic envelope
     * @throws IOException sandbox, deadline or response failure
     * @throws InterruptedException caller interruption after reaping
     */
    JsonNode validate(JsonNode candidate, JsonNode base, JsonNode inventory, String policy)
            throws IOException, InterruptedException {
        String nonce = UUID.randomUUID().toString();
        ObjectNode frame = JsonNodeFactory.instance.objectNode();
        frame.put("protocol", 1).put("requestId", nonce).put("policyVersion", policy).put("operation", "VALIDATE");
        frame.set("candidate", candidate.deepCopy());
        frame.set("baseArtifact", base.deepCopy());
        frame.set("ownedIdInventory", inventory.deepCopy());
        return execute(frame, nonce);
    }

    /** Rechecks exact historical content without reprinting or changing its identities/maps.
     * @param artifact authorized immutable historical content
     * @param inventory server-resolved existing ID inventory
     * @param policy current frozen policy
     * @return fresh validation envelope with unchanged source/IR/map content
     * @throws IOException unavailable validator or invalid private protocol
     * @throws InterruptedException caller interruption after child reaping
     */
    JsonNode revalidate(JsonNode artifact, JsonNode inventory, String policy) throws IOException, InterruptedException {
        if (profile != WorkerLaunchProfile.DEFAULT) throw new IOException("Advisory profile cannot revalidate history");
        String nonce = UUID.randomUUID().toString();
        ObjectNode frame = JsonNodeFactory.instance.objectNode().put("protocol", 1).put("requestId", nonce)
                .put("policyVersion", policy).put("operation", "REVALIDATE");
        frame.putNull("candidate");
        frame.set("baseArtifact", artifact.deepCopy());
        frame.set("ownedIdInventory", inventory.deepCopy());
        return execute(frame, nonce);
    }

    /** Exchanges one immutable internal frame while capturing proof of owned process exit.
     * @param frame complete validation or historical revalidation context
     * @param nonce expected response identity
     * @return validated private response
     * @throws IOException unavailable process or output
     * @throws InterruptedException caller interruption after child exit
     */
    private JsonNode execute(JsonNode frame, String nonce) throws IOException, InterruptedException {
        byte[] input = JsonWire.encode(frame);
        if (input.length >= 2097152) throw new IOException("Internal validation context exceeds limit");
        OwnedWorkerRun owned = new OwnedWorkerRun(launcher);
        try {
            Process child = owned.launch();
            pid = child.pid();
            startTicks = identityReader.read(pid);
            return response(owned.exchange(input, 1048577, 10000), nonce);
        } finally {
            try { owned.close(); }
            finally { recoveryIdentity(owned); }
        }
    }

    /** Preserves started-child evidence even when managed startup or cleanup failed.
     * @param owned retained launch and cleanup owner
     */
    private void recoveryIdentity(OwnedWorkerRun owned) {
        startupUncertain = owned.startupUncertain();
        Process child = owned.child();
        if (child == null) return;
        pid = child.pid();
        if (startTicks == null) startTicks = owned.observedStartTicks();
        reaped = owned.clean() && !child.isAlive();
    }

    /** Validates the one-shot worker envelope before any persistence frame is constructed.
     * @param bytes captured bounded response
     * @param nonce expected request identity
     * @return validated envelope
     * @throws IOException malformed or unrelated result
     */
    private JsonNode response(byte[] bytes, String nonce) throws IOException {
        JsonNode result = DocumentJson.decode(bytes);
        DocumentJson.fields(result, "protocol", "requestId", "status", "data");
        if (!result.path("protocol").isInt() || result.path("protocol").intValue() != 1
                || !nonce.equals(result.path("requestId").asText())
                || !java.util.Set.of("VALIDATED", "INVALID", "UNAVAILABLE").contains(result.path("status").asText())) {
            throw new IOException("Document worker identity mismatch");
        }
        return result;
    }

    /** Returns the process identity only after the owned sandbox has exited.
     * @return private recovery evidence or null when no worker was started
     * @throws IllegalStateException work is still active
     */
    JsonNode recovery() {
        ObjectNode proof = JsonNodeFactory.instance.objectNode();
        if (startupUncertain) throw new IllegalStateException("Worker startup ownership is uncertain");
        if (pid == 0) return proof.putNull("workerPid").putNull("workerStartTicks").put("noWorkerStarted", true);
        if (!reaped) throw new IllegalStateException("Reaping is not established");
        return proof.put("workerPid", pid).put("workerStartTicks", startTicks).put("noWorkerStarted", false);
    }

    /** Returns exact validator build identity for the accepted artifact dependency fence.
     * @return immutable dependency hash
     */
    String identity() {
        return launcher.identity();
    }
}
