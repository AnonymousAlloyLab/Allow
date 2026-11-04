package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

/** Pinned public-only helper transport; private input remains with the request supervisor. */
final class WarmImageLauncher {
    private static final String HELPER_SHA = "85f217246b6abeab699249f74e97abab586822678e7b573bbf5690588072dca0";
    private static final String ALLOY_SHA = "6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d";
    private final Path target;
    private final Path helper;
    private final Path javaHome;
    private final String expectedBuild;

    /** Captures full installation identity before reserving any worker.
     * @param installation canonical trusted Allow root
     * @param target copied compiled backend target
     * @param expectedBuild installed runtime's complete dependency identity
     * @throws IOException incomplete, linked or changed installation
     */
    WarmImageLauncher(Path installation, Path target, String expectedBuild) throws IOException {
        this.target = target.toAbsolutePath().normalize();
        this.helper = installation.resolve("scripts/warm_worker_image.py").toAbsolutePath().normalize();
        this.javaHome = Path.of(System.getProperty("java.home")).toRealPath();
        this.expectedBuild = expectedBuild;
        if (!this.target.toRealPath().equals(this.target) || !helper.toRealPath().equals(helper)) {
            throw new IOException("Linked worker installation rejected");
        }
        verify();
    }

    /** Performs fresh full installed-build, helper and solver checks.
     * @return exact current complete build identity
     * @throws IOException any observed executable mismatch
     */
    String verify() throws IOException {
        if (!HELPER_SHA.equals(Hashes.bytes(Files.readAllBytes(helper)))
                || !ALLOY_SHA.equals(Hashes.bytes(Files.readAllBytes(target.resolve("solver/alloy.jar"))))) {
            throw new IOException("Worker executable pin changed");
        }
        String current = BuildIdentity.read(target);
        if (!expectedBuild.equals(current)) throw new IOException("Worker build changed; restart required");
        return current;
    }

    /** Starts only the fixed helper; caller must persist its direct-child identity before release.
     * @param ledger exclusive pool owner
     * @param mode trusted installed entrypoint
     * @return direct owned process blocked on public bootstrap stdin
     * @throws IOException helper pin, installation or process failure
     */
    Process spawn(WorkerPoolLedger ledger, WarmWorkerMode mode) throws IOException {
        try { verify(); }
        catch (IOException failure) {
            try { ledger.disable(); } catch (IOException error) { failure.addSuppressed(error); }
            throw failure;
        }
        ProcessBuilder builder = new ProcessBuilder("/usr/bin/python3", "-I", helper.toString(), mode.argument(),
                Long.toString(ledger.ownerPid()), ledger.ownerStartTicks(), ledger.bootId(),
                ledger.cgroupRoot().toString(), Long.toString(ledger.rootDevice()), Long.toString(ledger.rootInode()));
        builder.environment().clear();
        builder.directory(target.toFile());
        return builder.start();
    }

    /** Writes one public metadata line after durable identity attachment, keeping stdin open.
     * @param ledger current owner
     * @param token attached exact generation
     * @throws IOException unavailable child or excessive bootstrap metadata
     */
    void releaseBootstrap(WorkerPoolLedger ledger, WorkerReservation token) throws IOException {
        byte[] bytes = JsonWire.encode(bootstrap(ledger, token));
        if (bytes.length >= 4096 || token.child() == null) throw new IOException("Worker bootstrap unavailable");
        var stream = token.child().getOutputStream();
        stream.write(bytes);
        stream.write('\n');
        stream.flush();
    }

    /** Builds the exact closed public descriptor without including model data or credentials.
     * @param ledger exclusive owner
     * @param token durable attached generation
     * @return bounded bootstrap descriptor
     */
    private ObjectNode bootstrap(WorkerPoolLedger ledger, WorkerReservation token) {
        ObjectNode node = JsonNodeFactory.instance.objectNode().put("protocol", 1);
        node.put("ownerPid", ledger.ownerPid()).put("ownerStartTicks", ledger.ownerStartTicks());
        node.put("bootId", ledger.bootId()).put("childPid", token.childPid());
        node.put("childStartTicks", token.childStartTicks()).put("poolNonce", ledger.poolNonce());
        node.put("slot", token.slot()).put("generation", token.generation()).put("workerNonce", token.nonce());
        node.put("cgroupRoot", ledger.cgroupRoot().toString()).put("cgroupRelative", token.group().relative());
        node.put("cgroupDevice", token.group().device()).put("cgroupInode", token.group().inode());
        node.put("target", target.toString()).put("buildSha256", expectedBuild);
        node.put("javaHome", javaHome.toString()).put("javaRuntimeVersion", System.getProperty("java.runtime.version"));
        return node;
    }

    /** Waits for helper exec before making private input available to a fresh worker pipe.
     * @param token attached direct child
     * @throws IOException early exit, changed incarnation or expired startup
     * @throws InterruptedException cancelled startup
     */
    void awaitFreshSandbox(WorkerReservation token) throws IOException, InterruptedException {
        Process child = token.child();
        Path executable = Path.of("/proc", Long.toString(token.childPid()), "exe");
        while (child.isAlive()) {
            if (System.nanoTime() - token.startupDeadline() >= 0) throw new IOException("Fresh worker startup expired");
            if (!token.childStartTicks().equals(ProcessIdentity.startTicks(token.childPid()))) {
                throw new IOException("Fresh worker identity changed");
            }
            if (Files.isSameFile(executable, Path.of("/usr/bin/bwrap"))) {
                if (!token.childStartTicks().equals(ProcessIdentity.startTicks(token.childPid()))) {
                    throw new IOException("Fresh worker incarnation changed at exec");
                }
                return;
            }
            TimeUnit.MILLISECONDS.sleep(1);
        }
        throw new IOException("Fresh worker failed before sandbox exec");
    }
}
