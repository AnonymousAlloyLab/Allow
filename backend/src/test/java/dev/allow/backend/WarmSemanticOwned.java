package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Actual isolated ledger, helper and pool ownership for one gate-only semantic fixture. */
final class WarmSemanticOwned {
    private final String build;
    private final WorkerPoolLedger ledger;
    private final WarmImageLauncher launcher;
    private final Map<WorkerReservation, WarmProbeWitness> witnesses = new IdentityHashMap<>();
    private WarmWorkerPool pool;
    private WorkerReservation fresh;
    private Process direct;
    private Completion completion;

    /** Opens a new private incarnation; even malformed fixture policy cannot select installed policy.
     * @param root copied installation
     * @param group verified delegated root
     * @param build exact installed image identity
     * @param name registered fixture name
     * @throws Exception unavailable private journal or production owner
     */
    WarmSemanticOwned(Path root, Path group, String build, String name) throws Exception {
        this.build = build;
        Path journal = root.resolve(".runtime/warm-pool/journal").resolve(WarmSemanticProtocol.basename(name));
        Files.createDirectory(journal, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
        ledger = WorkerPoolLedger.open(journal, group, build, "document-v1");
        launcher = new WarmImageLauncher(root, root.resolve("backend/target"), build);
    }

    /** Uses the actual advisory pool, preserving exact fixture semantics and recording binding rejection.
     * @param fixture exact parsed registered request
     * @param input original registered bytes
     * @param record complete private outcome
     * @throws Exception failed actual worker, unexpected rejection or changed frame
     */
    void advisory(JsonNode fixture, byte[] input, ObjectNode record) throws Exception {
        record.put("route", "ACTUAL_WARM_WORKER_POOL_ASSUMED_CLEAN");
        WarmRequestBinding binding;
        try { binding = WarmSemanticProtocol.binding(fixture, input, build, ledger.poolNonce()); }
        catch (IllegalArgumentException rejected) {
            WarmProbeFiles.require(fixture.path("policyVersion").isTextual()
                    && fixture.path("policyVersion").textValue().isEmpty(), "Unexpected binding rejection");
            record.put("outcome", "BINDING_INPUT_REJECTED").put("outputEquivalence", "NOT_COMPARABLE")
                    .put("rejectionCode", "BLANK_POLICY_UNREACHABLE_INSTALLED_CONTEXT");
            return;
        }
        DocumentValidationContext context = WarmSemanticProtocol.context(fixture);
        if (input.length < 2097152) WarmSemanticProtocol.frame(binding, fixture, context, record);
        pool = new WarmWorkerPool(ledger, launcher, build, "document-v1");
        record.put("noWorkerStarted", false);
        pool.begin();
        capture(false);
        awaitReady();
        capture(true);
        record.put("noWorkerStarted", false).put("readyBeforeAdmission", true);
        WorkerReservation ready = ledger.reservations()[0];
        record.put("workerPid", ready.childPid()).put("workerStartTicks", ready.childStartTicks());
        validate(binding, fixture, context, input, record);
    }

    /** Requires exact production limit rejection or a published complete cleaned result.
     * @param binding unchanged fixture identity bound to this pool
     * @param fixture parsed exact fixture
     * @param context gate-assumed context only
     * @param input original fixture bytes
     * @param record complete private evidence
     * @throws Exception actual validation, publication or unexpected rejection
     */
    private void validate(WarmRequestBinding binding, JsonNode fixture, DocumentValidationContext context,
            byte[] input, ObjectNode record) throws Exception {
        WarmContextPermit permit = WarmSemanticProtocol.permit(binding, context);
        WorkerCapacity.acquire();
        if (input.length < 2097152) record.put("noPrivateHandoff", false);
        try (WarmResultLease lease = pool.validate(binding, fixture.path("candidate"), permit, new WarmDeadline(10000))) {
            record.put("noPrivateHandoff", false);
            WarmProbeFiles.require(input.length < 2097152, "Oversized private handoff accepted");
            capture(true);
            byte[] framed = WarmSemanticProtocol.framed(lease.result());
            WarmSemanticProtocol.response(fixture, framed, "RESERIALIZED_COMPLETE_POOL_RESPONSE", record);
            WarmProbeFiles.require(java.util.Arrays.equals(framed, lease.publish(framed)), "Published response changed");
            record.put("published", true);
        } catch (IOException rejected) {
            if (input.length < 2097152 || !"Internal validation context exceeds limit".equals(rejected.getMessage())) throw rejected;
            record.put("outcome", "INPUT_REJECTED").put("rejectionCode", "PRIVATE_INPUT_LIMIT")
                    .put("boundaryObservation", "ACTUAL_POOL_ENCODER_EXCEPTION_BEFORE_EXCHANGE");
        } finally { WorkerCapacity.release(); }
    }

    /** Runs fresh REVALIDATE through actual helper containment, without claiming selected runtime routing.
     * @param fixture exact parsed historical request
     * @param input original unchanged request bytes
     * @param record private complete result
     * @throws Exception failed helper, transport or actual owned cleanup
     */
    void fresh(JsonNode fixture, byte[] input, ObjectNode record) throws Exception {
        record.put("route", "DIRECT_HELPER_LEDGER_NOT_OWNEDWORKERRUN");
        fresh = ledger.reserveFresh();
        WarmProbeWitness witness = new WarmProbeWitness(ledger, fresh);
        witnesses.put(fresh, witness);
        ledger.markSpawnAttempt(fresh);
        record.put("noWorkerStarted", false);
        direct = launcher.spawn(ledger, WarmWorkerMode.FRESH_DOCUMENT);
        witness.observeChild(direct);
        ledger.attach(fresh, direct);
        witness.bootstrap(bootstrap(fresh));
        record.put("noWorkerStarted", false).put("workerPid", direct.pid()).put("workerStartTicks", fresh.childStartTicks());
        launcher.releaseBootstrap(ledger, fresh);
        launcher.awaitFreshSandbox(fresh);
        completion = new Completion(new AtomicBoolean());
        WorkerCapacity.acquire();
        try {
            record.put("noPrivateHandoff", false);
            byte[] bytes = FrameProcess.exchange(direct, input, 1048577, 10000, completion);
            WarmSemanticProtocol.response(fixture, bytes, "ACTUAL_STDOUT_FRAME", record);
            ledger.cleanup(fresh, System.nanoTime() + 2_500_000_000L, completion);
            ledger.release(fresh);
        } finally { WorkerCapacity.release(); }
    }

    /** Waits for actual production readiness without editing a lifecycle state.
     * @throws Exception failed startup or unavailable actual READY
     * @throws IOException no worker became ready within its startup budget
     */
    private void awaitReady() throws Exception {
        long end = System.nanoTime() + 5_000_000_000L;
        while (System.nanoTime() < end) {
            for (WorkerReservation token : ledger.reservations()) {
                if (token.phase() == WorkerReservation.Phase.READY) return;
                WarmProbeFiles.require(token.phase() != WorkerReservation.Phase.UNKNOWN, "Semantic startup became UNKNOWN");
            }
            TimeUnit.MILLISECONDS.sleep(1);
        }
        throw new IOException("Semantic standby did not become READY");
    }

    /** Opens independent observers before a known worker can be consumed and removed.
     * @param attached whether each pending actual spawn must be captured before shutdown
     * @throws Exception unavailable group or process attachment
     */
    private void capture(boolean attached) throws Exception {
        for (WorkerReservation token : ledger.reservations()) {
            WarmProbeWitness witness = witnesses.get(token);
            if (witness == null) { witness = new WarmProbeWitness(ledger, token); witnesses.put(token, witness); }
            if (attached) {
                while (token.child() == null && System.nanoTime() < token.startupDeadline()
                        && token.phase() != WorkerReservation.Phase.RELEASED) TimeUnit.MILLISECONDS.sleep(1);
                WarmProbeFiles.require(token.child() != null, "Semantic worker attachment unavailable");
            }
            witness.observeChild(token.child());
            if (token.child() != null) witness.bootstrap(bootstrap(token));
        }
    }

    /** Reads only the production public-bootstrap serializer without touching its pipe.
     * @param token actual durably attached worker
     * @return exact generated public descriptor
     * @throws Exception unavailable gate reflection observation
     */
    private ObjectNode bootstrap(WorkerReservation token) throws Exception {
        Method method = WarmImageLauncher.class.getDeclaredMethod("bootstrap", WorkerPoolLedger.class, WorkerReservation.class);
        method.setAccessible(true);
        return (ObjectNode) method.invoke(launcher, ledger, token);
    }

    /** Completes production shutdown and writes positive group receipts before releasing observers.
     * @param record private semantic result
     * @param ownership private complete kernel receipt
     * @param identities exact direct-child incarnation inventory
     * @param row finite summary receiving logical cleanup outcome
     * @throws Exception unavailable physical cleanup or retained capacity
     */
    void finish(ObjectNode record, ObjectNode ownership, ArrayNode identities, ObjectNode row) throws Exception {
        Exception failure = null;
        try { if (pool != null) capture(true); }
        catch (Exception error) { failure = error; }
        try { if (pool != null) pool.close(); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        ownership.set("retainedCoordinatorFailures", WarmProbeFailures.retained(pool));
        try { cleanupFresh(); summarize(record, ownership, identities, row); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        for (WarmProbeWitness witness : witnesses.values()) {
            try { witness.close(); }
            catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        }
        try { ledger.close(); }
        catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
        if (failure != null) throw failure;
    }

    /** Retires a failed fresh launch using its original retained Process and conservative task receipt.
     * @throws Exception unresolved actual child, group or transport ownership
     */
    private void cleanupFresh() throws Exception {
        if (fresh == null || fresh.phase() == WorkerReservation.Phase.RELEASED) return;
        ledger.cancel(fresh);
        ledger.cleanup(fresh, System.nanoTime() + 2_500_000_000L, this::closeFresh);
        ledger.release(fresh);
    }

    /** Reaps the original helper before validating the fresh stream task completion receipt.
     * @throws Exception actual direct child or managed tasks remain unresolved
     */
    private void closeFresh() throws Exception {
        if (direct != null) FrameProcess.reap(direct);
        if (completion != null) completion.close();
    }

    /** Distinguishes no allocated worker from positive emptiness of every actually allocated group.
     * @param record full semantic outcome
     * @param ownership complete private kernel receipt
     * @param identities original process incarnations
     * @param row finite case summary
     * @throws Exception absent terminal counters, unreaped child or retained reservation
     */
    private void summarize(ObjectNode record, ObjectNode ownership, ArrayNode identities, ObjectNode row) throws Exception {
        ArrayNode groups = ownership.putArray("groups");
        boolean empty = !witnesses.isEmpty();
        for (WarmProbeWitness witness : witnesses.values()) {
            ObjectNode terminal = witness.terminal();
            groups.add(terminal);
            empty &= witness.populatedZero();
            if (witness.identity() != null) identities.add(witness.identity());
            if (terminal.path("pid").equals(record.path("workerPid"))) record.set("workerExitCode", terminal.path("exitCode"));
        }
        WarmProbeFiles.require(ledger.reservations().length == 0 && (empty || witnesses.isEmpty()), "Semantic cleanup unconfirmed");
        ownership.put("perWorkerCgroup", true).put("poolNonce", ledger.poolNonce())
                .put("remainingReservations", 0).put("ledgerOnline", ledger.online()).put("noGroupAllocated", witnesses.isEmpty());
        record.put("reaped", true);
        row.putObject("cleanup").put("status", "PASS").put("populatedZero", empty)
                .put("directChildReaped", true).put("capacityRetained", false).put("noGroupAllocated", witnesses.isEmpty());
    }

    /** Receives actual production stream-task completion before group release. */
    static final class Completion implements FrameProcess.Completion, AutoCloseable {
        private final AtomicBoolean observed;
        /** Stores the private observation flag.
         * @param observed initially false actual task-completion observation
         */
        Completion(AtomicBoolean observed) { this.observed = observed; }
        /** Records the actual FrameProcess callback after all managed tasks terminate. */
        @Override
        public void closed() { observed.set(true); }
        /** Rejects an unobserved task completion instead of granting optimistic cleanup.
         * @throws IOException production transport did not confirm task termination
         */
        @Override
        public void close() throws IOException { WarmProbeFiles.require(observed.get(), "Semantic fresh tasks remain active"); }
    }
}
