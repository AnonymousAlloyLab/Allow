package dev.allow.backend;

import java.io.IOException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Local token transitions and Linux identity observations, without claiming cgroup integration. */
class WorkerReservationTest {
    /** Cancellation after CLEAN remains sticky and suppresses otherwise eligible publication. */
    @Test
    void cancelledCleanResultCannotPublish() {
        WorkerReservation token = token(true);
        long now = System.nanoTime();
        token.assign("request", now);
        token.stage();
        token.clean();
        assertTrue(token.publishable("request", now));
        token.poison();
        assertEquals(WorkerReservation.Phase.CLEAN, token.phase());
        assertFalse(token.publishable("request", now));
        assertTrue(token.releasable());
    }

    /** UNKNOWN survives subsequent cancellation and never becomes release authority. */
    @Test
    void unknownCancellationDoesNotRestoreCleanup() {
        WorkerReservation token = token(true);
        token.attempting();
        token.unknown();
        token.poison();
        assertEquals(WorkerReservation.Phase.UNKNOWN, token.phase());
        assertTrue(token.attempted());
        assertFalse(token.releasable());
    }

    /** A consumed token remains active through retirement and frees only on release. */
    @Test
    void capacityCountsIncludeRetirementAndUnknown() {
        WorkerReservation token = token(true);
        assertTrue(token.unassigned());
        token.assign("request", System.nanoTime());
        assertFalse(token.unassigned());
        assertTrue(token.active());
        token.unknown();
        assertTrue(token.active());
        token.clean();
        token.release();
        assertFalse(token.active());
        assertFalse(token.unassigned());
    }

    /** A fresh reservation immediately occupies the shared active position. */
    @Test
    void freshReservationUsesActiveCapacity() {
        WorkerReservation token = token(false);
        assertTrue(token.active());
        assertFalse(token.unassigned());
        assertFalse(token.attempted());
        assertFalse(token.releasable());
    }

    /** Exact operation identity and strict deadline apply after cleanup. */
    @Test
    void publicationRejectsWrongNonceDeadlineAndRepeat() {
        WorkerReservation token = token(true);
        long now = System.nanoTime();
        token.assign("request", now);
        token.stage();
        token.clean();
        assertFalse(token.publishable("other", now));
        assertFalse(token.publishable("request", now + 10_000_000_000L));
        assertTrue(token.publishable("request", now + 9_999_999_999L));
        token.publish();
        assertFalse(token.publishable("request", now));
        assertTrue(token.releasable());
    }

    /** Current identity is present; different start ticks denote a different incarnation.
     * @throws IOException unavailable procfs
     */
    @Test
    void exactLinuxIncarnationIsRequired() throws IOException {
        long pid = ProcessHandle.current().pid();
        String start = WorkerReservation.startTicks(pid);
        assertTrue(start.matches("[0-9]+"));
        assertFalse(WorkerReservation.absent(pid, start));
        assertTrue(WorkerReservation.absent(pid, "0"));
        assertFalse(WorkerReservation.absent(0, "0"));
        assertFalse(WorkerReservation.absent(pid, ""));
    }

    /** Creates only local token-state fixtures; no fake group can be admitted by the ledger.
     * @param standby whether the fixture starts unassigned
     * @return isolated token with no kernel authority
     */
    private static WorkerReservation token(boolean standby) {
        return new WorkerReservation(0, 1, standby, null, System.nanoTime());
    }
}
