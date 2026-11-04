package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Fixed compiler-option scope, exact sandbox arguments and unchanged launch fences. */
class WorkerLaunchProfileTest {
    @TempDir
    private Path temporary;

    /** Default document launch preserves the complete reviewed argument order.
     * @throws IOException incomplete local build or runtime
     */
    @Test
    void defaultArgumentsMatchFrozenCommand() throws IOException {
        Path target = Path.of("target").toAbsolutePath().normalize();
        BubblewrapLauncher launcher = new BubblewrapLauncher(target, true);
        assertEquals(expectedArguments(target, true), launcher.command(target.resolve("solver/alloy.jar")));
        BubblewrapLauncher explicit = new BubblewrapLauncher(target, true, WorkerLaunchProfile.DEFAULT);
        assertEquals(launcher.command(target.resolve("solver/alloy.jar")), explicit.command(target.resolve("solver/alloy.jar")));
    }

    /** Tier1 changes exactly one compiler argument without changing any other byte or order.
     * @throws IOException incomplete local build or runtime
     */
    @Test
    void advisoryTier1AddsExactlyOneArgument() throws IOException {
        Path target = Path.of("target").toAbsolutePath().normalize();
        BubblewrapLauncher launcher = new BubblewrapLauncher(target, true, WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1);
        List<String> actual = launcher.command(target.resolve("solver/alloy.jar"));
        List<String> expected = expectedArguments(target, true);
        expected.add(expected.indexOf("-Djava.awt.headless=true"), "-XX:TieredStopAtLevel=1");
        assertEquals(expected, actual);
        assertEquals(1, java.util.Collections.frequency(actual, "-XX:TieredStopAtLevel=1"));
    }

    /** Solver commands retain all original bytes and cannot select the advisory option.
     * @throws IOException incomplete local build or runtime
     */
    @Test
    void solverProfileCannotChange() throws IOException {
        Path target = Path.of("target").toAbsolutePath().normalize();
        BubblewrapLauncher launcher = new BubblewrapLauncher(target);
        assertEquals(expectedArguments(target, false), launcher.command(target.resolve("solver/alloy.jar")));
        assertThrows(IllegalArgumentException.class,
                new Construct(target, false, WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1));
        assertThrows(IllegalArgumentException.class, new Construct(target, true, null));
    }

    /** The advisory profile cannot accidentally revalidate durable history or start a child.
     * @throws IOException incomplete local build
     */
    @Test
    void tier1HistoryIsDeniedBeforeLaunch() throws IOException {
        DocumentWorker worker = new DocumentWorker(WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1);
        IOException error = assertThrows(IOException.class, new Revalidate(worker));
        assertEquals("Advisory profile cannot revalidate history", error.getMessage());
        assertTrue(worker.recovery().path("noWorkerStarted").booleanValue());
        assertTrue(worker.recovery().path("workerPid").isNull());
    }

    /** A missing installation still fails the actual constructor's complete identity scan. */
    @Test
    void constructorStillRequiresCompleteInstallation() {
        assertThrows(IOException.class, new Construct(temporary, true, WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1));
    }

    /** Class, resource and dependency mutations all fail the real per-launch full-build fence.
     * @throws IOException failed creation of the owned temporary installation
     */
    @Test
    void launchStillChecksAllBuildInputs() throws IOException {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            Path target = fixtureInstallation();
            for (String relative : List.of("classes/Fixture.class", "classes/static/index.html", "dependency/fixture.jar")) {
                BubblewrapLauncher launcher = new BubblewrapLauncher(target, true, profile);
                assertEquals(BuildIdentity.read(target), launcher.identity());
                Files.writeString(target.resolve(relative), "changed", StandardOpenOption.APPEND);
                IOException error = assertThrows(IOException.class, launcher::launch);
                assertEquals("Build changed; restart required", error.getMessage());
            }
        }
    }

    /** The separately pinned Alloy digest is checked before any sandbox process is launched.
     * @throws IOException failed creation of the owned temporary installation
     */
    @Test
    void launchStillRejectsChangedAlloy() throws IOException {
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            Path target = fixtureInstallation();
            BubblewrapLauncher launcher = new BubblewrapLauncher(target, true, profile);
            Files.writeString(target.resolve("solver/alloy.jar"), "changed", StandardOpenOption.APPEND);
            IOException error = assertThrows(IOException.class, launcher::launch);
            assertEquals("Alloy artifact hash mismatch", error.getMessage());
        }
    }

    /** Both fixed profiles execute the real constructor, launcher and one-frame reaping path.
     * @throws Exception unavailable sandbox or invalid authored fixture
     */
    @Test
    void bothProfilesValidateAndReapFreshWorkers() throws Exception {
        long previous = 0;
        for (WorkerLaunchProfile profile : WorkerLaunchProfile.values()) {
            DocumentWorker worker = new DocumentWorker(profile);
            var candidate = JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", "sig A {}");
            var empty = JsonNodeFactory.instance.objectNode();
            var result = worker.validate(candidate, empty, empty, "profile-test");
            assertEquals("VALIDATED", result.path("status").textValue());
            assertEquals("sig A {}", result.path("data").path("source").textValue());
            long pid = worker.recovery().path("workerPid").longValue();
            assertNotEquals(previous, pid);
            assertFalse(ProcessHandle.of(pid).isPresent());
            assertFalse(worker.recovery().path("noWorkerStarted").booleanValue());
            previous = pid;
        }
    }

    /** Builds an independently stated complete baseline command with resolved host paths.
     * @param target reviewed build installation
     * @param document whether the baseline document entrypoint is selected
     * @return mutable exact baseline argument list
     * @throws IOException unavailable local JDK
     */
    private static List<String> expectedArguments(Path target, boolean document) throws IOException {
        Path javaHome = Path.of(System.getProperty("java.home")).toRealPath();
        List<String> args = new ArrayList<>(List.of("/usr/bin/prlimit", "--as=2147483648", "--cpu=12", "--fsize=8388608",
                "/usr/bin/bwrap", "--unshare-all", "--new-session", "--die-with-parent", "--cap-drop", "ALL"));
        expectedMounts(args, target, javaHome);
        args.addAll(List.of("--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev", "--chdir", "/tmp",
                javaHome.resolve("bin/java").toString(), "-Xmx512m", "-Xss512k", "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=2",
                "-XX:MaxMetaspaceSize=128m", "-XX:CompressedClassSpaceSize=64m", "-XX:ReservedCodeCacheSize=48m",
                "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-Djava.io.tmpdir=/tmp", "-cp",
                "/app/classes:/app/solver.jar:/app/dependency/*",
                document ? "dev.allow.worker.DocumentWorkerMain" : "dev.allow.worker.WorkerMain"));
        return args;
    }

    /** Records every reviewed read-only mount without consulting launcher implementation.
     * @param args expected command receiving the mounts
     * @param target isolated build installation
     * @param javaHome resolved JDK root
     */
    private static void expectedMounts(List<String> args, Path target, Path javaHome) {
        args.addAll(List.of("--ro-bind", javaHome.toString(), javaHome.toString(),
                "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                "--ro-bind", "/etc/java-17-openjdk", "/etc/java-17-openjdk",
                "--ro-bind", target.resolve("classes").toString(), "/app/classes",
                "--ro-bind", target.resolve("dependency").toString(), "/app/dependency",
                "--ro-bind", target.resolve("solver/alloy.jar").toString(), "/app/solver.jar"));
    }

    /** Creates private mutable identity fixtures without modifying any active build byte.
     * @return temporary installation with the original pinned Alloy artifact
     * @throws IOException failed private fixture creation
     */
    private Path fixtureInstallation() throws IOException {
        Path target = Files.createTempDirectory(temporary, "installation-");
        Files.createDirectories(target.resolve("classes/static"));
        Files.createDirectories(target.resolve("dependency"));
        Files.createDirectories(target.resolve("solver"));
        Files.writeString(target.resolve("classes/Fixture.class"), "class fixture");
        Files.writeString(target.resolve("classes/static/index.html"), "resource fixture");
        Files.writeString(target.resolve("dependency/fixture.jar"), "dependency fixture");
        Files.copy(Path.of("target/solver/alloy.jar"), target.resolve("solver/alloy.jar"));
        return target;
    }

    /** Retains one trusted constructor invocation for fail-closed assertions. */
    private record Construct(Path target, boolean document, WorkerLaunchProfile profile) implements Executable {
        /** Calls the actual constructor with a deliberately rejected profile or installation.
         * @throws IOException unavailable installation
         */
        @Override
        public void execute() throws IOException { new BubblewrapLauncher(target, document, profile); }
    }

    /** Attempts history validation through an advisory-only worker owner. */
    private record Revalidate(DocumentWorker worker) implements Executable {
        /** Requires rejection before a sandbox can execute.
         * @throws IOException expected profile rejection
         * @throws InterruptedException unexpected worker interruption
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            var empty = JsonNodeFactory.instance.objectNode();
            worker.revalidate(empty, empty, "profile-test");
        }
    }
}
