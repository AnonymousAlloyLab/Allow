package dev.allow.backend;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.MockedStatic;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Creation-failure control-flow regressions; cgroup observations are mocked, journal durability is real. */
class WorkerCreationFailureTest {
    @TempDir
    private Path temporary;
    private WorkerJournal journal;
    private WorkerPoolLedger ledger;
    private WorkerReservation existing;
    private String poolNonce;
    private Path root;

    /** Initializes bounded operational state without creating a cgroup or spawning a process.
     * @throws Exception unavailable private metadata fixture
     */
    @BeforeEach
    void prepare() throws Exception {
        Files.setPosixFilePermissions(temporary, PosixFilePermissions.fromString("rwx------"));
        journal = new WorkerJournal(temporary);
        ledger = mock(WorkerPoolLedger.class, CALLS_REAL_METHODS);
        poolNonce = UUID.randomUUID().toString();
        root = Path.of("/sys/fs/cgroup/creation-fixture");
        existing = new WorkerReservation(0, 1, false, group(0), System.nanoTime());
        set("slots", new WorkerReservation[] {existing, null});
        set("generations", new long[] {1, 0});
        set("journal", journal);
        set("cgroupRoot", root);
        set("poolNonce", poolNonce);
        set("ownerPid", ProcessHandle.current().pid());
        set("ownerStart", WorkerReservation.startTicks(ProcessHandle.current().pid()));
        set("bootId", UUID.randomUUID().toString());
        set("build", "a".repeat(64));
        set("policy", "document-v1:fixture");
        set("online", true);
    }

    /** Releases only the private metadata fixture; no live containment exists.
     * @throws IOException failed private journal close
     */
    @AfterEach
    void closeJournal() throws IOException { if (journal != null) journal.close(); }

    /** The first failed group creation disables admission and poisons the existing generation.
     * @throws Exception unexpected metadata operation failure
     */
    @Test
    void failedCreationDisablesIncarnationWithoutRepeatAttempt() throws Exception {
        IOException failure = new IOException("containment unavailable");
        try (MockedStatic<WorkerCgroup> groups = mockStatic(WorkerCgroup.class)) {
            groups.when(this::createGroup).thenThrow(failure);
            assertSame(failure, assertThrows(IOException.class, ledger::reserveStandby));
            assertFalse(ledger.online());
            assertTrue(existing.poisoned());
            assertEquals("RETIRING", journal.read().path("slots").get(0).path("phase").textValue());
            assertEquals(1, journal.read().path("generations").get(1).longValue());
            assertThrows(IOException.class, ledger::reserveStandby);
            assertThrows(IOException.class, ledger::reserveFresh);
            groups.verify(this::createGroup, times(1));
            groups.verifyNoMoreInteractions();
        }
    }

    /** Runtime failures at the containment boundary also prevent further creation attempts.
     * @throws Exception unexpected metadata operation failure
     */
    @Test
    void runtimeCreationFailureIsAlsoSticky() throws Exception {
        IllegalStateException failure = new IllegalStateException("invalid provider");
        try (MockedStatic<WorkerCgroup> groups = mockStatic(WorkerCgroup.class)) {
            groups.when(this::createGroup).thenThrow(failure);
            assertSame(failure, assertThrows(IllegalStateException.class, ledger::reserveStandby));
            assertFalse(ledger.online());
            assertTrue(existing.poisoned());
            assertThrows(IOException.class, ledger::reserveStandby);
            groups.verify(this::createGroup, times(1));
            groups.verifyNoMoreInteractions();
        }
    }

    /** A failed retirement fsync preserves the original setup error and cannot restore admission.
     * @throws Exception unexpected metadata operation failure
     */
    @Test
    void failedRetirementPersistenceCannotEnableRetry() throws Exception {
        WorkerJournal unavailable = mock(WorkerJournal.class);
        IOException disk = new IOException("journal unavailable");
        doThrow(disk).when(unavailable).write(any(ObjectNode.class));
        set("journal", unavailable);
        IOException setup = new IOException("containment unavailable");
        try (MockedStatic<WorkerCgroup> groups = mockStatic(WorkerCgroup.class)) {
            groups.when(this::createGroup).thenThrow(setup);
            assertSame(setup, assertThrows(IOException.class, ledger::reserveStandby));
            assertArrayEquals(new Throwable[] {disk}, setup.getSuppressed());
            assertFalse(ledger.online());
            assertTrue(existing.poisoned());
            assertThrows(IOException.class, ledger::reserveStandby);
            groups.verify(this::createGroup, times(1));
        }
    }

    /** Fresh containment creation follows the same failure fence while a standby exists.
     * @throws Exception unexpected metadata operation failure
     */
    @Test
    void freshCreationFailurePoisonsExistingStandby() throws Exception {
        existing = new WorkerReservation(0, 1, true, group(0), System.nanoTime());
        set("slots", new WorkerReservation[] {existing, null});
        try (MockedStatic<WorkerCgroup> groups = mockStatic(WorkerCgroup.class)) {
            groups.when(this::createGroup).thenThrow(new IOException("containment unavailable"));
            assertThrows(IOException.class, ledger::reserveFresh);
            assertFalse(ledger.online());
            assertTrue(existing.poisoned());
            assertThrows(IOException.class, ledger::reserveFresh);
            groups.verify(this::createGroup, times(1));
        }
    }

    /** Successful creation retains normal capacity and does not activate the failure fence.
     * @throws Exception unexpected metadata operation failure
     */
    @Test
    void successfulCreationPreservesNormalAdmissionState() throws Exception {
        WorkerCgroup created = group(1);
        try (MockedStatic<WorkerCgroup> groups = mockStatic(WorkerCgroup.class)) {
            groups.when(this::createGroup).thenReturn(created);
            WorkerReservation reserved = ledger.reserveStandby();
            assertSame(created, reserved.group());
            assertTrue(ledger.online());
            assertFalse(existing.poisoned());
            assertEquals(2, ledger.reservations().length);
            assertThrows(IOException.class, ledger::reserveStandby);
            groups.verify(this::createGroup, times(1));
        }
    }

    /** A fully captured failed setup attempts descriptor-bound removal before closing ownership.
     * @throws Exception unavailable private cleanup observation seam
     */
    @Test
    void capturedCreationFailureAttemptsRemovalThenClose() throws Exception {
        WorkerCgroup owner = mock(WorkerCgroup.class);
        IOException original = new IOException("limit failure");
        failedCapturedCreation(owner, original);
        var order = inOrder(owner);
        order.verify(owner).remove();
        order.verify(owner).close();
        assertEquals(0, original.getSuppressed().length);
    }

    /** Failed empty/identity observation still closes descriptors and preserves both diagnostics.
     * @throws Exception unavailable private cleanup observation seam
     */
    @Test
    void uncertainRemovalStillClosesAndPreservesPrimaryFailure() throws Exception {
        WorkerCgroup owner = mock(WorkerCgroup.class);
        IOException original = new IOException("limit failure");
        IOException removal = new IOException("empty observation unavailable");
        IOException closure = new IOException("close unavailable");
        doThrow(removal).when(owner).remove();
        doThrow(closure).when(owner).close();
        failedCapturedCreation(owner, original);
        assertArrayEquals(new Throwable[] {removal, closure}, original.getSuppressed());
        var order = inOrder(owner);
        order.verify(owner).remove();
        order.verify(owner).close();
    }

    /** A provider runtime failure during removal cannot skip retained descriptor closure.
     * @throws Exception unavailable private cleanup observation seam
     */
    @Test
    void runtimeRemovalFailureCannotSkipClose() throws Exception {
        WorkerCgroup owner = mock(WorkerCgroup.class);
        IOException original = new IOException("limit failure");
        IllegalStateException removal = new IllegalStateException("provider unavailable");
        doThrow(removal).when(owner).remove();
        failedCapturedCreation(owner, original);
        assertArrayEquals(new Throwable[] {removal}, original.getSuppressed());
        verify(owner).close();
    }

    /** Names the exact production factory invocation for the static-boundary mock.
     * @return never a real group in these tests
     * @throws IOException explicit fixture containment failure
     */
    private WorkerCgroup createGroup() throws IOException {
        return WorkerCgroup.create(root, "pool-" + poolNonce + "/slot-1-g1");
    }
    /** Supplies inert closed journal metadata without any process or filesystem authority.
     * @param slot metadata slot index
     * @return mocked identity only
     */
    private WorkerCgroup group(int slot) {
        WorkerCgroup group = mock(WorkerCgroup.class);
        when(group.relative()).thenReturn("pool-" + poolNonce + "/slot-" + slot + "-g1");
        when(group.device()).thenReturn(1L);
        when(group.inode()).thenReturn((long) slot + 2);
        return group;
    }
    /** Executes the real failure handler with a mocked descriptor boundary.
     * @param owner inert captured-owner fixture
     * @param failure primary setup exception
     * @throws ReflectiveOperationException unavailable private test seam
     */
    private static void failedCapturedCreation(WorkerCgroup owner, Exception failure) throws ReflectiveOperationException {
        Method method = WorkerCgroup.class.getDeclaredMethod("failedCreation", WorkerCgroup.class, Exception.class);
        method.setAccessible(true);
        method.invoke(null, owner, failure);
    }
    /** Installs only operational fixture state into actual ledger transition methods.
     * @param name exact private field name
     * @param value inert metadata fixture
     * @throws ReflectiveOperationException unavailable private test seam
     */
    private void set(String name, Object value) throws ReflectiveOperationException {
        Field field = WorkerPoolLedger.class.getDeclaredField(name);
        field.setAccessible(true);
        field.set(ledger, value);
    }
}
