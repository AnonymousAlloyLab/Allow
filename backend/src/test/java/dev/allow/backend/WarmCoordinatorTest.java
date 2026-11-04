package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.invocation.InvocationOnMock;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Finite coordinator race tests with a mocked kernel boundary; not containment/runtime evidence. */
class WarmCoordinatorTest {
    private WorkerPoolLedger ledger;
    private WarmWorkerPool pool;
    private WarmImageLauncher launcher;
    private WorkerReservation token;
    private WarmStandby worker;
    private WarmContextPermit permit;
    private WarmRequestBinding binding;
    private WarmDeadline deadline;
    private boolean unknownCleanup;
    private boolean interruptAfterRelease;
    private boolean failureAfterRelease;

    /** Installs local transition observations without spawning any alternate worker process.
     * @throws Exception unexpected mock setup failure
     */
    @BeforeEach
    void prepare() throws Exception {
        ledger = mock(WorkerPoolLedger.class);
        pool = mock(WarmWorkerPool.class);
        launcher = mock(WarmImageLauncher.class);
        token = new WorkerReservation(0, 1, true, null, System.nanoTime());
        worker = new WarmStandby(pool, ledger, launcher, token, "a".repeat(64));
        permit = mock(WarmContextPermit.class);
        binding = new WarmRequestBinding(UUID.randomUUID().toString(), "b".repeat(64), "server:" + UUID.randomUUID(), 0,
                "policy", "a".repeat(64), UUID.randomUUID().toString());
        deadline = new WarmDeadline(10000);
        when(permit.consume(binding)).thenReturn(mock(DocumentValidationContext.class));
        doAnswer(this::observeFence).when(pool).verifyImage();
        doAnswer(this::assignToken).when(ledger).assign(eq(token), anyString(), anyLong());
        doAnswer(this::stageToken).when(ledger).stage(token);
        doAnswer(this::cancelToken).when(ledger).cancel(token);
        doAnswer(this::cleanToken).when(ledger).cleanup(eq(token), anyLong(), any(AutoCloseable.class));
        doAnswer(this::releaseToken).when(ledger).release(token);
        doAnswer(this::publishToken).when(ledger).publish(eq(token), anyString(), anyString(), anyLong());
    }

    /** Reader failure callbacks perform no lifecycle, launch or cleanup calls. */
    @Test
    void failureSinkOnlySignalsAtomicFailure() {
        worker.failed(new IOException("fixture"));
        verifyNoInteractions(ledger, pool, launcher);
        assertTrue(worker.needsRetirement(System.nanoTime()));
    }

    /** A generation consumes its context permit exactly once.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void contextHandoffCannotBeRepeated() throws Exception {
        readyAndAssign();
        assertThrows(IOException.class, this::assignWorker);
        verify(permit, times(1)).consume(binding);
        verify(ledger, times(1)).assign(eq(token), eq(binding.nonce()), anyLong());
        assertTrue(token.active());
    }

    /** Rejected context authority cannot assign or expose a private request.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void stalePermitDoesNotConsumeGeneration() throws Exception {
        token.ready(System.nanoTime());
        when(permit.consume(binding)).thenThrow(new IOException("stale"));
        assertThrows(IOException.class, this::assignWorker);
        verify(ledger, never()).assign(any(), anyString(), anyLong());
        assertEquals(WorkerReservation.Phase.READY, token.phase());
    }

    /** Original admission expiry is checked before consuming the context.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void expiredAdmissionCannotConsumePermit() throws Exception {
        token.ready(System.nanoTime());
        deadline = WarmDeadline.fromStart(System.nanoTime() - 11_000_000_000L, 10000);
        assertThrows(IOException.class, this::assignWorker);
        verify(permit, never()).consume(any());
        verifyNoInteractions(ledger);
    }

    /** A staged response is not exposed as a lease before cleanup completes.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void stagePrecedesCleanupAndCleanTokenRemainsReserved() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        assertEquals(WorkerReservation.Phase.CLEAN, token.phase());
        assertTrue(token.active());
        var order = inOrder(ledger);
        order.verify(ledger).assign(eq(token), eq(binding.nonce()), anyLong());
        order.verify(ledger).stage(token);
        order.verify(ledger).cleanup(eq(token), anyLong(), any(AutoCloseable.class));
        verify(ledger, never()).release(any());
    }

    /** Failure observed after cleanup still prevents the final fence and publication.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void lateFailureSuppressesPublication() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        clearInvocations(pool);
        worker.failed(new IOException("cancelled"));
        assertThrows(IOException.class, this::publishWorker);
        verifyNoInteractions(pool);
        verify(ledger, never()).publish(any(), anyString(), anyString(), anyLong());
    }

    /** The final image scan and publication both execute while holding the ledger monitor.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void finalFenceAndPublicationShareExactMonitor() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        publishWorker();
        assertEquals(WorkerReservation.Phase.RELEASED, token.phase());
        verify(pool, times(2)).verifyImage();
        verify(ledger).publish(eq(token), eq(binding.nonce()), eq("a".repeat(64)), anyLong());
        verify(ledger).release(token);
    }

    /** An observed final-fence failure cannot invoke publication.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void finalImageFailurePreventsSuccess() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        doThrow(new IOException("changed")).when(pool).verifyImage();
        assertThrows(IOException.class, this::publishWorker);
        verify(ledger, never()).publish(any(), anyString(), anyString(), anyLong());
    }

    /** Closing an unpublished lease cancels and releases once despite repeated close calls.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void unpublishedLeaseCloseIsIdempotentAndDropsResult() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        WarmResultLease lease = lease();
        lease.close();
        lease.close();
        assertThrows(IOException.class, lease::result);
        verify(ledger, times(1)).cancel(token);
        verify(ledger, times(1)).cleanup(eq(token), anyLong(), any(AutoCloseable.class));
        verify(ledger, times(1)).release(token);
    }

    /** Watcher retirement before caller close cannot double-release a cleaned result.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void watcherAndCallerRetirementCannotDoubleRelease() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        WarmResultLease lease = lease();
        worker.retire();
        worker.retire();
        lease.close();
        verify(ledger, times(1)).release(token);
        verify(ledger, times(1)).cancel(token);
    }

    /** UNKNOWN gets one physical cleanup attempt and then retains capacity without watcher retries.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void unknownCleanupIsNotRetriedByWatcher() throws Exception {
        token.unknown();
        unknownCleanup = true;
        worker.retireQuietly();
        assertFalse(worker.needsRetirement(System.nanoTime()));
        assertEquals(WorkerReservation.Phase.UNKNOWN, token.phase());
        verify(ledger, times(1)).cleanup(eq(token), anyLong(), any(AutoCloseable.class));
        verify(ledger, never()).release(any());
    }

    /** A published lease returns exact bytes once and clears its private result.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void leasePublishesExactBytesAndCannotBeReadAgain() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        WarmResultLease lease = lease();
        byte[] bytes = new byte[] {1, 2, 3};
        assertSame(bytes, lease.publish(bytes));
        assertThrows(IOException.class, lease::result);
        lease.close();
        verify(ledger, never()).cancel(any());
        verify(ledger, times(1)).release(token);
    }

    /** An interrupt during journal completion is checked before public bytes can return.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void interruptAfterJournalSuppressesReplyAndDetaches() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        interruptAfterRelease = true;
        assertThrows(InterruptedException.class, this::publishWorker);
        assertFalse(Thread.currentThread().isInterrupted());
        assertEquals(WorkerReservation.Phase.RELEASED, token.phase());
        verify(pool).released(worker);
    }

    /** A failure observed during durable release is checked before public return.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void failureAfterJournalSuppressesReplyAndDetaches() throws Exception {
        readyAndAssign();
        worker.stageAndClean(deadline);
        failureAfterRelease = true;
        assertThrows(IOException.class, this::publishWorker);
        assertEquals(WorkerReservation.Phase.RELEASED, token.phase());
        verify(pool).released(worker);
    }

    /** Cancellation while waiting for readiness retires an unconsumed selected generation.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void waitingCancellationRetiresUnassignedGeneration() throws Exception {
        worker.abortRequest(binding.nonce());
        assertEquals(WorkerReservation.Phase.RELEASED, token.phase());
        assertThrows(IOException.class, this::awaitWorker);
        verify(ledger).cancel(token);
        verify(ledger).cleanup(eq(token), anyLong(), any(AutoCloseable.class));
        verify(ledger, never()).assign(any(), anyString(), anyLong());
    }

    /** A stale waiting caller cannot cancel a generation consumed by another operation.
     * @throws Exception unexpected local transition failure
     */
    @Test
    void differentOperationCannotCancelAssignedGeneration() throws Exception {
        readyAndAssign();
        worker.abortRequest(UUID.randomUUID().toString());
        assertEquals(WorkerReservation.Phase.ASSIGNED, token.phase());
        verify(ledger, never()).cancel(any());
    }

    /** Awaits the actual readiness future for named exception assertions.
     * @throws Exception failed or cancelled readiness
     */
    private void awaitWorker() throws Exception { worker.awaitReady(deadline); }

    /** Prepares a local READY transition before exercising the actual coordinator method.
     * @throws Exception unexpected context transition failure
     */
    private void readyAndAssign() throws Exception { token.ready(System.nanoTime()); assignWorker(); }
    /** Invokes the actual handoff for named exception assertions.
     * @throws Exception rejected or cancelled handoff
     */
    private void assignWorker() throws Exception { worker.assign(binding, permit, deadline); }
    /** Invokes the actual final publication for named exception assertions.
     * @throws Exception rejected or cancelled publication
     */
    private void publishWorker() throws Exception { worker.publish(binding, deadline); }
    /** Creates a lease with private fixture data after local mocked cleanup.
     * @return one-use staged lease
     */
    private WarmResultLease lease() {
        return new WarmResultLease(worker, binding, deadline, JsonNodeFactory.instance.objectNode().put("private", "fixture"));
    }
    /** Observes the exact locking boundary around executable scans.
     * @param invocation mocked call metadata
     * @return fixture image digest
     */
    private Object observeFence(InvocationOnMock invocation) {
        assertTrue(Thread.holdsLock(ledger));
        return "a".repeat(64);
    }
    /** Applies the local token's assignment without simulating SQL or kernel evidence.
     * @param invocation mocked call metadata
     * @return no result
     */
    private Object assignToken(InvocationOnMock invocation) {
        token.assign(invocation.getArgument(1), invocation.getArgument(2));
        return null;
    }
    /** Marks the local fixture staged.
     * @param invocation mocked call metadata
     * @return no result
     */
    private Object stageToken(InvocationOnMock invocation) { token.stage(); return null; }
    /** Marks cancellation sticky on the local token.
     * @param invocation mocked call metadata
     * @return no result
     */
    private Object cancelToken(InvocationOnMock invocation) { token.poison(); return null; }
    /** Models either explicit cleanup uncertainty or successful cleanup for control-flow tests.
     * @param invocation mocked call metadata
     * @return no result
     * @throws IOException explicit unknown cleanup fixture
     */
    private Object cleanToken(InvocationOnMock invocation) throws IOException {
        if (unknownCleanup) { token.unknown(); throw new IOException("unknown"); }
        assertTrue(token.phase() == WorkerReservation.Phase.STAGED || token.poisoned());
        token.clean();
        return null;
    }
    /** Requires CLEAN before the local mocked release.
     * @param invocation mocked call metadata
     * @return no result
     */
    private Object releaseToken(InvocationOnMock invocation) {
        assertEquals(WorkerReservation.Phase.CLEAN, token.phase());
        token.release();
        if (interruptAfterRelease) Thread.currentThread().interrupt();
        if (failureAfterRelease) worker.failed(new IOException("late failure"));
        return null;
    }
    /** Checks the final operation and monitor at the publication boundary.
     * @param invocation mocked call metadata
     * @return no result
     */
    private Object publishToken(InvocationOnMock invocation) {
        assertTrue(Thread.holdsLock(ledger));
        assertTrue(token.publishable(invocation.getArgument(1), invocation.getArgument(3)));
        token.publish();
        return null;
    }
}
