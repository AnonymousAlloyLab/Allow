package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Gate-only raw CPU accounting, independent of component request timers. */
final class WarmLatencyResources {
    /** Prevents construction of this stateless helper. */
    private WarmLatencyResources() {}

    /** Samples the declared outer scope without interpreting kernel counters.
     * @param path frozen outer cpu.stat path
     * @return observation instant and exact kernel text
     * @throws IOException missing or excessive accounting data
     */
    static ObjectNode cpu(Path path) throws IOException {
        long observed = System.nanoTime();
        String raw = Files.readString(path);
        if (raw.length() > 16384) throw new IOException("CPU accounting exceeds bound");
        return JsonNodeFactory.instance.objectNode().put("observedNs", observed).put("raw", raw);
    }
}
