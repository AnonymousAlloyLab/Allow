package dev.allow.backend;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Cancellation owner; a permit remains held by the runner until this process is reaped. */
final class JobControl {
    private final AtomicBoolean cancelled = new AtomicBoolean();
    private final AtomicReference<Process> process = new AtomicReference<>();
    private final AtomicBoolean clean = new AtomicBoolean();

    /** Records the owned runner's verified cleanup result, independently of display status.
     * @param verified whether startup and all owned process cleanup are certain
     */
    void finished(boolean verified) { clean.set(verified); }

    /** Requires both cleanup evidence and actual direct-child absence.
     * @return whether a completed runner can safely release its workspace
     */
    boolean cleanupSafe() {
        Process child = process.get();
        return clean.get() && (child == null || !child.isAlive());
    }

    /**
     * Attaches a process, handling cancellation that won the spawn race.
     * @param child newly spawned sandbox
     */
    void attach(Process child) {
        process.set(child);
        if (cancelled.get()) stop();
    }

    /** Marks cancellation and kills the sandbox process. */
    void cancel() {
        cancelled.set(true);
        stop();
    }

    /** Kills sandbox and its current descendants; namespace lifetime handles reparenting. */
    void stop() {
        Process child = process.get();
        if (child != null) {
            child.descendants().forEach(JobControl::kill);
            child.destroyForcibly();
        }
    }

    /**
     * Requests forced exit of a captured descendant handle.
     * @param handle owned child
     */
    private static void kill(ProcessHandle handle) {
        handle.destroyForcibly();
    }

    /**
     * Reports whether explicit cancellation was requested.
     * @return cancellation state
     */
    boolean cancelled() {
        return cancelled.get();
    }
}
