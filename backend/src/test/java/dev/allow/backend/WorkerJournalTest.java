package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Finite journal durability/schema checks; kernel crash persistence needs separate runtime evidence. */
class WorkerJournalTest {
    @TempDir
    private Path temporary;
    private WorkerJournal current;
    private ObjectNode candidate;

    /** Forced replacements preserve the closed record and exact private file mode.
     * @throws IOException unavailable local filesystem
     */
    @Test
    void completePrivateRecordsRoundTripAndReplace() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            assertNull(journal.read());
            ObjectNode initial = state();
            journal.write(initial);
            assertEquals(initial, journal.read());
            initial.put("policy", "document-v1:replacement");
            journal.write(initial);
            assertEquals(initial, journal.read());
            assertEquals(PosixFilePermissions.fromString("rw-------"), Files.getPosixFilePermissions(temporary.resolve("pool.json")));
            try (var members = Files.list(temporary)) { assertEquals(2, members.count()); }
        }
    }

    /** A second owner cannot obtain the same lock even in the same process.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void exclusiveOwnershipRejectsSecondWriter() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            assertThrows(IOException.class, this::openAnother);
            journal.write(state());
        }
        try (WorkerJournal reopened = new WorkerJournal(temporary)) { assertEquals(state(), reopened.read()); }
    }

    /** Private payload fields cannot enter durable operational metadata.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void privatePayloadAndUnknownFieldsAreRejectedBeforeReplacement() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            journal.write(state());
            for (String field : new String[] {"source", "context", "response", "password"}) {
                candidate = state().put(field, "private");
                assertThrows(IOException.class, this::writeCandidate);
                assertEquals(state(), journal.read());
            }
        }
    }

    /** Duplicate keys, trailing JSON and nonobjects are rejected on disk.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void ambiguousJsonCannotBecomeOperationalAuthority() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            String valid = state().toString();
            for (String invalid : new String[] {valid + " {}", "[]", valid.replace("\"schema\":1", "\"schema\":1,\"schema\":1")}) {
                journal.write(state());
                Files.writeString(temporary.resolve("pool.json"), invalid);
                assertThrows(IOException.class, this::readCurrent);
            }
        }
    }

    /** Oversized journal bytes are rejected before parsing.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void durableMetadataHasFiniteByteBound() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            journal.write(state());
            Files.writeString(temporary.resolve("pool.json"), " ".repeat(32769));
            assertThrows(IOException.class, this::readCurrent);
        }
    }

    /** JSON booleans and strings cannot substitute for exact integer authority.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void numericAndNonceTypesAreClosed() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            candidate = state().put("ownerPid", true);
            assertThrows(IOException.class, this::writeCandidate);
            candidate = state().put("schema", "1");
            assertThrows(IOException.class, this::writeCandidate);
            candidate = state().put("poolNonce", "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA");
            assertThrows(IOException.class, this::writeCandidate);
        }
    }

    /** Slot identity is bound to the pool, slot index and monotone generation.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void foreignGroupOrCounterCannotBeReconciled() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            candidate = occupied();
            journal.write(candidate);
            slot(candidate).put("group", "pool-00000000-0000-0000-0000-000000000002/slot-0-g1");
            assertThrows(IOException.class, this::writeCandidate);
            candidate = occupied();
            slot(candidate).put("generation", 2);
            assertThrows(IOException.class, this::writeCandidate);
            candidate = occupied();
            slot(candidate).put("phase", "RELEASED");
            assertThrows(IOException.class, this::writeCandidate);
        }
    }

    /** Child identity cannot appear without a durable attempted marker.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void contradictoryChildIdentityIsRejected() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            candidate = occupied();
            slot(candidate).put("childPid", 42).put("childStartTicks", "123");
            assertThrows(IOException.class, this::writeCandidate);
            candidate = occupied();
            slot(candidate).put("attempted", true).put("childStartTicks", "123");
            assertThrows(IOException.class, this::writeCandidate);
        }
    }

    /** Symlinked journal contents cannot replace the locked owner's record.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void symbolicJournalAliasesAreRejected() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            Path external = temporary.resolve("external");
            Files.writeString(external, state().toString());
            Files.createSymbolicLink(temporary.resolve("pool.json"), external);
            assertThrows(IOException.class, this::readCurrent);
        }
    }

    /** Hardlinked records cannot authorize a state potentially shared outside the journal.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void hardlinkedJournalIsRejected() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            journal.write(state());
            Files.createLink(temporary.resolve("alias"), temporary.resolve("pool.json"));
            assertThrows(IOException.class, this::readCurrent);
        }
    }

    /** World-readable metadata directories are rejected before lock acquisition.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void insecureDirectoryCannotOwnPool() throws IOException {
        Files.setPosixFilePermissions(temporary, PosixFilePermissions.fromString("rwxr-xr-x"));
        assertThrows(IOException.class, this::openAnother);
    }

    /** Ordinary filesystem fixtures cannot stand in for real cgroup ownership.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void ordinaryDirectoryCannotLaunchContainedWorkers() throws IOException {
        privateDirectory();
        assertThrows(IOException.class, this::openLedgerWithoutDelegation);
        try (WorkerJournal journal = new WorkerJournal(temporary)) { assertNull(journal.read()); }
    }

    /** A durably empty ledger permits a new delegated root without resetting generations.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void releasedJournalAllowsNewRootAndPreservesCounters() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            ObjectNode empty = state();
            empty.withArray("generations").set(0, JsonNodeFactory.instance.numberNode(17));
            empty.withArray("generations").set(1, JsonNodeFactory.instance.numberNode(29));
            journal.write(empty);
            ObjectNode prior = journal.readForRoot(Path.of("/sys/fs/cgroup/new-unique-scope"));
            assertEquals(empty, prior);
            assertEquals(17, prior.path("generations").get(0).longValue());
            assertEquals(29, prior.path("generations").get(1).longValue());
        }
    }

    /** Any outstanding phase, including CLEAN before release and UNKNOWN, pins the old root.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void outstandingReservationsRejectRootChanges() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            for (String phase : new String[] {"RESERVED", "STARTING", "READY", "ASSIGNED", "STAGED", "RETIRING", "CLEAN", "UNKNOWN"}) {
                ObjectNode outstanding = occupied();
                slot(outstanding).put("phase", phase);
                journal.write(outstanding);
                assertThrows(IOException.class, this::readDifferentRoot);
                assertEquals(outstanding, journal.readForRoot(Path.of("/sys/fs/cgroup/fixture")));
            }
        }
    }

    /** Root compatibility never bypasses the strict parser for malformed empty records.
     * @throws IOException unavailable private filesystem
     */
    @Test
    void malformedEmptyJournalCannotAuthorizeRootChange() throws IOException {
        try (WorkerJournal journal = new WorkerJournal(privateDirectory())) {
            current = journal;
            journal.write(state());
            Files.writeString(temporary.resolve("pool.json"), "{\"slots\":[null,null]}");
            assertThrows(IOException.class, this::readDifferentRoot);
        }
    }

    /** Exercises the actual restart-root guard with the parsed prior journal.
     * @throws IOException outstanding reservation or invalid schema
     */
    private void readDifferentRoot() throws IOException {
        current.readForRoot(Path.of("/sys/fs/cgroup/new-unique-scope"));
    }

    /** Reads the current fixture record for named exception assertions.
     * @throws IOException schema or identity rejection
     */
    private void readCurrent() throws IOException { current.read(); }
    /** Writes the selected fixture record for named exception assertions.
     * @throws IOException schema rejection
     */
    private void writeCandidate() throws IOException { current.write(candidate); }
    /** Attempts a second ownership claim without retaining it on success.
     * @throws IOException ownership rejection
     */
    private void openAnother() throws IOException { try (WorkerJournal ignored = new WorkerJournal(temporary)) { } }
    /** Exercises the actual ledger's delegation fence.
     * @throws IOException unsupported ordinary filesystem
     */
    private void openLedgerWithoutDelegation() throws IOException {
        try (WorkerPoolLedger ignored = WorkerPoolLedger.open(temporary, temporary, "a".repeat(64), "policy")) { }
    }
    /** Applies the provisioned private workspace mode.
     * @return canonical fixture directory
     * @throws IOException unavailable private mode
     */
    private Path privateDirectory() throws IOException {
        Files.setPosixFilePermissions(temporary, PosixFilePermissions.fromString("rwx------"));
        return temporary;
    }
    /** Builds an independently stated empty closed journal record.
     * @return operational metadata only
     */
    private static ObjectNode state() {
        ObjectNode state = JsonNodeFactory.instance.objectNode().put("schema", 1)
                .put("poolNonce", "00000000-0000-0000-0000-000000000001")
                .put("ownerPid", 123).put("ownerStartTicks", "456")
                .put("bootId", "00000000-0000-0000-0000-000000000002")
                .put("build", "a".repeat(64)).put("policy", "document-v1:fixture")
                .put("cgroupRoot", "/sys/fs/cgroup/fixture");
        state.putArray("generations").add(0).add(0);
        state.putArray("slots").addNull().addNull();
        return state;
    }
    /** Builds a reserved but never-attempted generation record.
     * @return operational fixture
     */
    private static ObjectNode occupied() {
        ObjectNode state = state();
        state.withArray("generations").set(0, JsonNodeFactory.instance.numberNode(1));
        ObjectNode slot = JsonNodeFactory.instance.objectNode().put("slot", 0).put("generation", 1)
                .put("nonce", "00000000-0000-0000-0000-000000000003").put("standby", true)
                .put("phase", "RESERVED").put("attempted", false).put("poisoned", false)
                .put("assigned", false).put("published", false).put("childPid", 0)
                .put("childStartTicks", "").put("group", "pool-00000000-0000-0000-0000-000000000001/slot-0-g1")
                .put("device", 1).put("inode", 2);
        state.withArray("slots").set(0, slot);
        return state;
    }
    /** Selects an operational slot fixture.
     * @param state occupied journal
     * @return first slot object
     */
    private static ObjectNode slot(ObjectNode state) { return (ObjectNode) state.path("slots").get(0); }
}
