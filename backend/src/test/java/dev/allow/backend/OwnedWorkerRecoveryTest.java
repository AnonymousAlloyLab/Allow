package dev.allow.backend;

import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Recovery guard regression with reflected operational fixtures; no process or cleanup proof is fabricated. */
class OwnedWorkerRecoveryTest {
    /** An attempted managed spawn with no returned Process cannot claim no-worker-started.
     * @throws ReflectiveOperationException unavailable private test observation seam
     * @throws IOException unexpected default constructor failure
     */
    @Test
    void attemptedUnkeyedSpawnSuppressesNoWorkerReceipt() throws ReflectiveOperationException, IOException {
        OwnedWorkerRun owned = new OwnedWorkerRun(mock(SandboxLauncher.class));
        WorkerReservation token = reservation(owned);
        token.attempting();
        assertTrue(owned.startupUncertain());
        DocumentWorker worker = capture(owned);
        assertThrows(IllegalStateException.class, worker::recovery);
        assertNull(owned.child());
    }

    /** Later UNKNOWN or cancellation cannot turn an attempted spawn into a no-spawn proof.
     * @throws ReflectiveOperationException unavailable private test observation seam
     * @throws IOException unexpected default constructor failure
     */
    @Test
    void unknownAttemptRemainsUncertainForRecovery() throws ReflectiveOperationException, IOException {
        OwnedWorkerRun owned = new OwnedWorkerRun(mock(SandboxLauncher.class));
        WorkerReservation token = reservation(owned);
        token.attempting();
        token.unknown();
        token.poison();
        assertTrue(owned.startupUncertain());
        DocumentWorker worker = capture(owned);
        assertThrows(IllegalStateException.class, worker::recovery);
    }

    /** A generation with positively no launch attempt retains the existing no-worker receipt.
     * @throws ReflectiveOperationException unavailable private test observation seam
     * @throws IOException unexpected default constructor failure
     */
    @Test
    void neverAttemptedReservationRetainsTruthfulNoWorkerReceipt() throws ReflectiveOperationException, IOException {
        OwnedWorkerRun owned = new OwnedWorkerRun(mock(SandboxLauncher.class));
        reservation(owned);
        assertFalse(owned.startupUncertain());
        assertTrue(capture(owned).recovery().path("noWorkerStarted").booleanValue());
    }

    /** Installs only a local metadata capability to exercise the managed recovery predicate.
     * @param owned default-disabled owner that has never spawned anything
     * @return token fixture without kernel authority
     * @throws ReflectiveOperationException unavailable final-field test seam
     */
    private static WorkerReservation reservation(OwnedWorkerRun owned) throws ReflectiveOperationException {
        WorkerReservation token = new WorkerReservation(0, 1, false, null, System.nanoTime());
        Field field = OwnedWorkerRun.class.getDeclaredField("reservation");
        field.setAccessible(true);
        field.set(owned, token);
        return token;
    }

    /** Calls the production recovery capture without invoking any alternate launcher.
     * @param owned operational fixture carrying attempted-spawn metadata
     * @return actual document worker recovery adapter
     * @throws ReflectiveOperationException unavailable private capture seam
     */
    private static DocumentWorker capture(OwnedWorkerRun owned) throws ReflectiveOperationException {
        DocumentWorker worker = new DocumentWorker(mock(SandboxLauncher.class), mock(ProcessIdentity.Reader.class));
        Method method = DocumentWorker.class.getDeclaredMethod("recoveryIdentity", OwnedWorkerRun.class);
        method.setAccessible(true);
        method.invoke(worker, owned);
        return worker;
    }
}
