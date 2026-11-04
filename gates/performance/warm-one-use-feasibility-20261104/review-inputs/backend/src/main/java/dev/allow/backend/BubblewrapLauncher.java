package dev.allow.backend;

import dev.allow.worker.Hashes;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Linux-only fail-closed sandbox; no inherited environment or home/project mounts. */
final class BubblewrapLauncher implements SandboxLauncher {
    private static final String ALLOY_SHA = "6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d";
    private final Path target;
    private final String expectedBuild;
    private final String entryPoint;
    private final WorkerLaunchProfile profile;

    /**
     * Uses the backend build directory.
     * @param target absolute target root
     * @throws IOException incomplete build
     */
    BubblewrapLauncher(Path target) throws IOException {
        this(target, false);
    }

    /** Selects one of the two installed, fixed sandbox entry points.
     * @param target compiled installation root
     * @param document whether to start the document validator
     * @throws IOException incomplete installation
     */
    BubblewrapLauncher(Path target, boolean document) throws IOException {
        this(target, document, WorkerLaunchProfile.DEFAULT);
    }

    /** Selects a fixed advisory profile without changing solver or durable defaults.
     * @param target compiled installation root
     * @param document whether to start the document validator
     * @param profile trusted package-owned compiler choice
     * @throws IOException incomplete installation
     * @throws IllegalArgumentException absent profile or advisory option for a solver
     */
    BubblewrapLauncher(Path target, boolean document, WorkerLaunchProfile profile) throws IOException {
        if (profile == null || (!document && profile != WorkerLaunchProfile.DEFAULT)) {
            throw new IllegalArgumentException("Invalid worker launch profile");
        }
        this.profile = profile;
        this.target = target.toAbsolutePath().normalize();
        this.expectedBuild = BuildIdentity.read(this.target);
        this.entryPoint = document ? "dev.allow.worker.DocumentWorkerMain" : "dev.allow.worker.WorkerMain";
    }

    /**
     * Starts a memory/CPU/file-limited sandbox; absence of tools fails closed.
     * @return isolated process
     * @throws IOException missing artifacts or failed launch
     */
    @Override
    public Process launch() throws IOException {
        Path solver = target.resolve("solver/alloy.jar");
        if (!ALLOY_SHA.equals(Hashes.bytes(Files.readAllBytes(solver)))) {
            throw new IOException("Alloy artifact hash mismatch");
        }
        if (!expectedBuild.equals(BuildIdentity.read(target))) throw new IOException("Build changed; restart required");
        List<String> command = command(solver);
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.environment().clear();
        builder.directory(target.toFile());
        return builder.start();
    }

    /**
     * Builds an argument list without a shell.
     * @param solver pinned artifact
     * @return launcher command
     * @throws IOException invalid runtime layout
     */
    List<String> command(Path solver) throws IOException {
        Path javaHome = Path.of(System.getProperty("java.home")).toRealPath();
        String java = javaHome.resolve("bin/java").toString();
        List<String> args = new ArrayList<>(List.of("/usr/bin/prlimit", "--as=2147483648", "--cpu=12", "--fsize=8388608",
                "/usr/bin/bwrap", "--unshare-all", "--new-session", "--die-with-parent", "--cap-drop", "ALL"));
        mount(args, javaHome.toString(), javaHome.toString());
        mount(args, "/lib", "/lib");
        mount(args, "/lib64", "/lib64");
        mount(args, "/etc/java-17-openjdk", "/etc/java-17-openjdk");
        mount(args, target.resolve("classes").toString(), "/app/classes");
        mount(args, target.resolve("dependency").toString(), "/app/dependency");
        mount(args, solver.toString(), "/app/solver.jar");
        args.addAll(List.of("--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev", "--chdir", "/tmp",
                java, "-Xmx512m", "-Xss512k", "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=2",
                "-XX:MaxMetaspaceSize=128m", "-XX:CompressedClassSpaceSize=64m", "-XX:ReservedCodeCacheSize=48m"));
        if (profile == WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1) args.add("-XX:TieredStopAtLevel=1");
        args.addAll(List.of("-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-Djava.io.tmpdir=/tmp", "-cp",
                "/app/classes:/app/solver.jar:/app/dependency/*", entryPoint));
        return args;
    }

    /**
     * Returns exact compiled/dependency/runtime identity.
     * @return snapshot hash
     */
    @Override
    public String identity() {
        return expectedBuild;
    }

    /**
     * Adds a required read-only mount.
     * @param args command list
     * @param source host path
     * @param destination sandbox path
     * @throws IOException missing runtime component
     */
    private void mount(List<String> args, String source, String destination) throws IOException {
        if (!Files.exists(Path.of(source))) throw new IOException("Required sandbox runtime component missing");
        args.addAll(List.of("--ro-bind", source, destination));
    }
}
