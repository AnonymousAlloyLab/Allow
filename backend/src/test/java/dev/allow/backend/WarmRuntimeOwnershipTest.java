package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.invocation.InvocationOnMock;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Actual private lock/journal regressions with inert metadata and assumed cleanup; no worker launches. */
class WarmRuntimeOwnershipTest {
    private static final String BUILD = "a".repeat(64);
    @TempDir
    private Path temporary;
    private DocumentRuntime documents;
    private WarmRuntime runtime;
    private WorkerPoolLedger ledger;
    private WorkerJournal journal;
    private WorkerReservation token;
    private WarmWorkerPool pool;
    private FileLock workspaceLock;
    private FileChannel workspaceChannel;
    private DocumentGateway failingGateway;
    private Path failedInstallation;
    private Path workspaceDirectory;

    /** Creates real private metadata ownership without selecting or launching a production pool.
     * @throws Exception unavailable local filesystem or reflected metadata seam
     */
    @BeforeEach
    void prepare() throws Exception {
        assertNull(field(WarmRuntime.class, null, "current", WarmRuntime.class));
        documents = new DocumentRuntime(mock(DocumentGateway.class), "");
        set(DocumentRuntime.class, documents, "dependency", BUILD);
        Path installation = temporary.resolve("owned-installation");
        Files.createDirectories(installation.resolve(".runtime"));
        workspaceDirectory = privateDirectory(installation.resolve(".runtime/documents"));
        Method acquire = DocumentRuntime.class.getDeclaredMethod("acquire", Path.class);
        acquire.setAccessible(true);
        acquire.invoke(documents, workspaceDirectory);
        set(DocumentRuntime.class, documents, "ready", true);
        workspaceLock = field(DocumentRuntime.class, documents, "lock", FileLock.class);
        workspaceChannel = field(DocumentRuntime.class, documents, "channel", FileChannel.class);
        journal = new WorkerJournal(privateDirectory(temporary.resolve("journal")));
        prepareLedger();
        pool = mock(WarmWorkerPool.class);
        runtime = new WarmRuntime(documents, "");
        set(WarmRuntime.class, runtime, "ledger", ledger);
        set(WarmRuntime.class, runtime, "pool", pool);
        set(WarmRuntime.class, null, "current", runtime);
        doAnswer(this::assumedCleanPool).when(pool).close();
    }

    /** Removes only test metadata ownership; no live worker or containment exists in this fixture.
     * @throws Exception unavailable reflection or metadata descriptor close
     */
    @AfterEach
    void releaseFixture() throws Exception {
        set(WarmRuntime.class, null, "current", null);
        if (documents != null) documents.close();
        if (journal != null && field(WorkerJournal.class, journal, "directoryChannel", FileChannel.class).isOpen()) {
            journal.close();
        }
    }

    /** Failed warm cleanup keeps the actual workspace lock valid when document destruction continues.
     * @throws Exception unavailable local metadata observation
     */
    @Test
    void failedWarmCleanupThenDocumentCloseRetainsLock() throws Exception {
        doThrow(new IOException("unresolved group")).when(pool).close();
        assertThrows(IOException.class, runtime::close);
        documents.close();
        assertTrue(workspaceLock.isValid());
        assertTrue(workspaceChannel.isOpen());
        assertFalse(WarmRuntime.permitsWorkspaceRelease(documents));
        assertThrows(IOException.class, documents::requireReady);
        assertFalse(ledger.online());
        assertEquals(WorkerReservation.Phase.RETIRING, token.phase());
        assertTrue(observerSeesLock(workspaceDirectory.resolve("server.lock")));
    }

    /** Successful assumed cleanup plus actual journal close permits the real workspace lock release.
     * @throws Exception unavailable local metadata observation
     */
    @Test
    void completedWarmAndLedgerClosePermitsWorkspaceRelease() throws Exception {
        runtime.close();
        assertTrue(WarmRuntime.permitsWorkspaceRelease(documents));
        assertNull(field(WarmRuntime.class, null, "current", WarmRuntime.class));
        documents.close();
        assertFalse(workspaceLock.isValid());
        assertFalse(workspaceChannel.isOpen());
        assertReacquirable(workspaceDirectory.resolve("server.lock"));
        assertFalse(observerSeesLock(workspaceDirectory.resolve("server.lock")));
        assertEquals(WorkerReservation.Phase.RELEASED, token.phase());
    }

    /** An unrelated constructor failure releases its own lock without releasing the retained owner.
     * @throws Exception unavailable local metadata observation
     */
    @Test
    void unrelatedFailedDocumentConstructorClosesOwnResources() throws Exception {
        failedInstallation = temporary.resolve("other-installation");
        Files.createDirectories(failedInstallation.resolve(".runtime"));
        privateDirectory(failedInstallation.resolve(".runtime/documents"));
        failingGateway = mock(DocumentGateway.class);
        when(failingGateway.request(eq("init"), any(JsonNode.class))).thenThrow(new IOException("context unavailable"));
        assertThrows(IOException.class, this::constructUnrelatedDocument);
        assertReacquirable(failedInstallation.resolve(".runtime/documents/server.lock"));
        assertTrue(workspaceLock.isValid());
        assertTrue(workspaceChannel.isOpen());
        assertSame(runtime, field(WarmRuntime.class, null, "current", WarmRuntime.class));
    }

    /** A failed duplicate constructor cannot drop the first owner's actual POSIX lock.
     * @throws Exception unavailable local metadata or observer process
     */
    @Test
    void sameWorkspaceDuplicatePreservesObservedOsLock() throws Exception {
        failedInstallation = workspaceDirectory.getParent().getParent();
        failingGateway = mock(DocumentGateway.class);
        Path lock = workspaceDirectory.resolve("server.lock");
        assertTrue(observerSeesLock(lock));
        assertThrows(IOException.class, this::constructUnrelatedDocument);
        assertTrue(workspaceLock.isValid());
        assertTrue(workspaceChannel.isOpen());
        assertTrue(observerSeesLock(lock));
        verifyNoInteractions(failingGateway);
        assertFalse(WarmRuntime.permitsWorkspaceRelease(documents));
    }

    /** Hardlinked lock aliases are rejected before opening and do not leave a registry claim.
     * @throws Exception unavailable local metadata filesystem
     */
    @Test
    void hardlinkedLockIsRejectedWithoutRegistryLeak() throws Exception {
        failedInstallation = temporary.resolve("linked-installation");
        Files.createDirectories(failedInstallation.resolve(".runtime"));
        Path directory = privateDirectory(failedInstallation.resolve(".runtime/documents"));
        Path original = temporary.resolve("original-lock");
        Files.writeString(original, "unchanged");
        Files.createLink(directory.resolve("server.lock"), original);
        failingGateway = mock(DocumentGateway.class);
        assertThrows(IOException.class, this::constructUnrelatedDocument);
        verifyNoInteractions(failingGateway);
        assertEquals("unchanged", Files.readString(original));
        assertEquals(2, ((Number) Files.getAttribute(original, "unix:nlink")).intValue());
        Files.delete(directory.resolve("server.lock"));
        when(failingGateway.request(eq("init"), any(JsonNode.class))).thenThrow(new IOException("fixture failure"));
        assertThrows(IOException.class, this::constructUnrelatedDocument);
        verify(failingGateway).request(eq("init"), any(JsonNode.class));
        assertReacquirable(directory.resolve("server.lock"));
    }

    /** A mismatch disables and durably poisons the exact ledger; a later match cannot revive it.
     * @throws Exception unavailable metadata durability or reflection
     */
    @Test
    void observedMismatchRemainsStickyAfterMatchingObservation() throws Exception {
        assertTrue(ledger.online());
        assertThrows(IOException.class, this::observeMismatch);
        assertFalse(ledger.online());
        assertTrue(token.poisoned());
        assertEquals("RETIRING", journal.read().path("slots").get(0).path("phase").textValue());
        assertTrue(journal.read().path("slots").get(0).path("poisoned").booleanValue());
        WarmRuntime.observeBuild(BUILD);
        assertFalse(ledger.online());
        assertTrue(token.poisoned());
        assertSame(ledger, runtime.ledger());
        verify(ledger, times(1)).disable();
    }

    /** An unreadable build observation also disables the currently associated ledger.
     * @throws Exception unavailable metadata durability
     */
    @Test
    void failedBuildObservationPoisonsExistingIncarnation() throws Exception {
        IOException failure = new IOException("unreadable image");
        WarmRuntime.observedBuildFailure(failure);
        assertFalse(ledger.online());
        assertTrue(token.poisoned());
        assertEquals(0, failure.getSuppressed().length);
        verify(ledger).disable();
    }

    /** A terminal journal failure cannot masquerade as a completed workspace-shutdown receipt.
     * @throws Exception unavailable metadata observation
     */
    @Test
    void ledgerCloseFailureRetainsWorkspaceOwner() throws Exception {
        WorkerJournal failedJournal = mock(WorkerJournal.class);
        doThrow(new IOException("close failed")).when(failedJournal).close();
        set(WorkerPoolLedger.class, ledger, "journal", failedJournal);
        assertThrows(IOException.class, runtime::close);
        documents.close();
        assertTrue(workspaceLock.isValid());
        assertTrue(workspaceChannel.isOpen());
        assertFalse(WarmRuntime.permitsWorkspaceRelease(documents));
    }

    /** Initializes real ledger state transitions around an inert, never-created cgroup identity.
     * @throws Exception unavailable reflected metadata seam
     */
    private void prepareLedger() throws Exception {
        ledger = mock(WorkerPoolLedger.class, CALLS_REAL_METHODS);
        String poolNonce = UUID.randomUUID().toString();
        WorkerCgroup group = mock(WorkerCgroup.class);
        when(group.relative()).thenReturn("pool-" + poolNonce + "/slot-0-g1");
        when(group.device()).thenReturn(1L);
        when(group.inode()).thenReturn(2L);
        token = new WorkerReservation(0, 1, true, group, System.nanoTime());
        set(WorkerPoolLedger.class, ledger, "slots", new WorkerReservation[] {token, null});
        set(WorkerPoolLedger.class, ledger, "generations", new long[] {1, 0});
        set(WorkerPoolLedger.class, ledger, "journal", journal);
        set(WorkerPoolLedger.class, ledger, "cgroupRoot", Path.of("/sys/fs/cgroup/metadata-fixture"));
        set(WorkerPoolLedger.class, ledger, "poolNonce", poolNonce);
        set(WorkerPoolLedger.class, ledger, "ownerPid", ProcessHandle.current().pid());
        set(WorkerPoolLedger.class, ledger, "ownerStart", WorkerReservation.startTicks(ProcessHandle.current().pid()));
        set(WorkerPoolLedger.class, ledger, "bootId", UUID.randomUUID().toString());
        set(WorkerPoolLedger.class, ledger, "build", BUILD);
        set(WorkerPoolLedger.class, ledger, "policy", "document-v1:fixture");
        set(WorkerPoolLedger.class, ledger, "online", true);
    }

    /** Supplies an explicitly assumed cleanup receipt; this test makes no kernel absence claim.
     * @param invocation mocked pool-close call
     * @return no value
     * @throws IOException failed real metadata release
     */
    private Object assumedCleanPool(InvocationOnMock invocation) throws IOException {
        synchronized (ledger) { token.clean(); ledger.release(token); }
        return null;
    }
    /** Invokes the real unrelated constructor's exception cleanup path.
     * @throws IOException expected mocked initialization failure
     * @throws InterruptedException unexpected caller cancellation
     */
    private void constructUnrelatedDocument() throws IOException, InterruptedException {
        new DocumentRuntime(failingGateway, failedInstallation.toString());
    }
    /** Supplies a distinct complete image digest to the real static observation guard.
     * @throws IOException expected identity mismatch
     */
    private void observeMismatch() throws IOException { WarmRuntime.observeBuild("b".repeat(64)); }
    /** Creates one genuinely private local metadata directory.
     * @param path new metadata directory
     * @return canonical created directory
     * @throws IOException unavailable private filesystem
     */
    private static Path privateDirectory(Path path) throws IOException {
        return Files.createDirectory(path, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
    }
    /** Confirms that a released metadata lock can actually be acquired again.
     * @param path released lock file
     * @throws IOException failed metadata file access
     */
    private static void assertReacquirable(Path path) throws IOException {
        try (FileChannel channel = FileChannel.open(path, StandardOpenOption.WRITE); FileLock lock = channel.tryLock()) {
            assertNotNull(lock);
            assertTrue(lock.isValid());
        }
    }
    /** Checks the actual POSIX record lock from a separate fixed metadata-only interpreter.
     * @param path owned lock file; no model or database content is read
     * @return whether the independent process observed a conflicting OS lock
     * @throws IOException failed observer launch or descriptor cleanup
     * @throws InterruptedException interrupted observer supervision
     */
    private static boolean observerSeesLock(Path path) throws IOException, InterruptedException {
        String script = "import errno,fcntl,os,sys\n"
                + "fd=os.open(sys.argv[1],os.O_WRONLY|os.O_NOFOLLOW)\n"
                + "try:\n fcntl.lockf(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)\n"
                + "except OSError as e:\n sys.exit(23 if e.errno in (errno.EACCES,errno.EAGAIN) else 24)\n"
                + "sys.exit(0)\n";
        ProcessBuilder builder = new ProcessBuilder("/usr/bin/python3", "-I", "-c", script, path.toString());
        builder.environment().clear();
        Process observer = builder.start();
        try {
            assertTrue(observer.waitFor(3, TimeUnit.SECONDS), "Metadata observer exceeded bound");
            int exit = observer.exitValue();
            assertTrue(exit == 0 || exit == 23, "Metadata observer failed");
            return exit == 23;
        } finally {
            observer.destroyForcibly();
            assertTrue(observer.waitFor(3, TimeUnit.SECONDS), "Metadata observer reap unavailable");
            observer.getInputStream().close();
            observer.getErrorStream().close();
            observer.getOutputStream().close();
        }
    }

    /** Installs metadata-only fixture state without adding production configuration authority.
     * @param type class declaring the field
     * @param owner object instance, or null for a static field
     * @param name exact private field name
     * @param value fixture value
     * @throws ReflectiveOperationException unavailable private test seam
     */
    private static void set(Class<?> type, Object owner, String name, Object value) throws ReflectiveOperationException {
        Field field = type.getDeclaredField(name);
        field.setAccessible(true);
        field.set(owner, value);
    }
    /** Reads actual retained descriptor or incarnation identity for assertions.
     * @param type class declaring the field
     * @param owner object instance, or null for a static field
     * @param name exact private field name
     * @param result expected runtime type
     * @param <T> expected field type
     * @return exact field value
     * @throws ReflectiveOperationException unavailable private test seam
     */
    private static <T> T field(Class<?> type, Object owner, String name, Class<T> result) throws ReflectiveOperationException {
        Field field = type.getDeclaredField(name);
        field.setAccessible(true);
        return result.cast(field.get(owner));
    }
}
