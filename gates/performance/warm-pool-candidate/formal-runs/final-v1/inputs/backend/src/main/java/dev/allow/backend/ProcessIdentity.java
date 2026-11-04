package dev.allow.backend;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Linux process identity includes start ticks so recycled PIDs never prove ownership. */
final class ProcessIdentity {
    /** Narrow kernel-reader seam for testing a child that exits before identification. */
    interface Reader {
        /** Reads the exact process incarnation or reports unavailable evidence.
         * @param pid owned child identifier
         * @return kernel start ticks
         * @throws IOException absent or unreadable process identity
         */
        String read(long pid) throws IOException;
    }

    /** Prevents construction of the identity reader. */
    private ProcessIdentity() {}

    /** Reads kernel start ticks while the owned child is still waiting for stdin.
     * @param pid owned process identifier
     * @return exact start-time tick string
     * @throws IOException process absent or malformed kernel record
     */
    static String startTicks(long pid) throws IOException {
        String record = Files.readString(Path.of("/proc", Long.toString(pid), "stat"));
        int close = record.lastIndexOf(')');
        if (close < 0) throw new IOException("Process identity unavailable");
        String[] fields = record.substring(close + 2).split(" ");
        if (fields.length <= 19 || !fields[19].matches("[0-9]+")) throw new IOException("Invalid process identity");
        return fields[19];
    }
}
