package dev.allow.document;

import dev.allow.worker.SourcePolicy;
import dev.allow.worker.WorkerPolicy;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Parses exact source through the worker's file-based Alloy and policy boundary. */
final class SourceParser {
    /** Prevents construction of this stateless helper. */
    private SourceParser() {}

    /**
     * Parses exact source and checks all installed worker policy constraints.
     * @param source Unicode source with exact newlines
     * @return resolved parser module
     * @throws Err when Alloy rejects source
     * @throws IOException when isolated temporary I/O fails
     * @throws IllegalArgumentException when policy rejects source
     */
    static CompModule parse(String source) throws Err, IOException {
        SourcePolicy.check(source);
        Path path = Files.createTempFile("allow-document-", ".als");
        try {
            Files.writeString(path, source, StandardCharsets.UTF_8);
            CompModule result = CompUtil.parseEverything_fromFile(A4Reporter.NOP, null, path.toString());
            WorkerPolicy.check(result);
            return result;
        } finally {
            Files.deleteIfExists(path);
        }
    }
}
