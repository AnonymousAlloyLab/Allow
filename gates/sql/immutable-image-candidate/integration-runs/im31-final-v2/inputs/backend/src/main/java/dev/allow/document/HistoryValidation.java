package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import java.io.IOException;
import java.util.Map;

/** Revalidates immutable historical content under the current parser and policy. */
final class HistoryValidation {
    private final JsonNode artifact;
    private final JsonNode inventory;

    /**
     * Creates a history validator over server-authorized immutable data.
     * @param artifact historical artifact content
     * @param inventory historical identity-to-kind inventory
     */
    HistoryValidation(JsonNode artifact, JsonNode inventory) {
        this.artifact = artifact;
        this.inventory = inventory;
    }

    /**
     * Checks same-content history and derives fresh command descriptors.
     * @return fresh result preserving the historical content
     * @throws Err when Alloy now rejects the historical source
     * @throws IOException if isolated parser I/O fails
     * @throws IllegalArgumentException if old content no longer validates
     */
    ObjectNode revalidate() throws Err, IOException {
        new ArtifactIntegrity(artifact).check();
        String source = artifact.path("source").textValue();
        String mode = artifact.path("mode").textValue();
        CompModule parsed = SourceParser.parse(source);
        int commandCount = new CommandTokenCounter(source).count();
        JsonNode module = artifact.path("module");
        if (mode.equals("BLOCK_SUPPORTED")) checkBlock(module, source, parsed, commandCount);
        ArrayNode descriptors = new CommandDescriptors(parsed, mode.equals("BLOCK_SUPPORTED") ? module.path("commands") : null)
            .read(commandCount);
        ArrayNode diagnostics = EngineData.notices(mode.equals("BLOCK_SUPPORTED")
            && EngineData.locationsUnavailable(module, artifact.path("occurrences")), EngineData.orphanCount(artifact.path("trivia")));
        return EngineData.result(mode, source, mode.equals("BLOCK_SUPPORTED") ? module : null,
            artifact.path("occurrences"), artifact.path("trivia"), descriptors, diagnostics, Map.of());
    }

    /**
     * Checks old block identities and current-parser semantic correspondence.
     * @param module original immutable checked module
     * @param source historical exact source
     * @param parsed current-policy parsed module
     * @param commandCount authored command count
     * @throws IllegalArgumentException if history no longer belongs to the fragment
     */
    private void checkBlock(JsonNode module, String source, CompModule parsed, int commandCount) {
        if (!new SourceFragmentGuard(source).supports()) throw new IllegalArgumentException("historical fragment");
        IdentityRemapper mapper = new IdentityRemapper(inventory);
        mapper.remap(module);
        if (!mapper.mappings().isEmpty()) throw new IllegalArgumentException("historical draft identity");
        JsonNode reconstructed = new AlloyModuleReader(parsed, true, true).read(commandCount);
        if (!new ModuleEquivalence(module, reconstructed).matches()) throw new IllegalArgumentException("historical correspondence");
    }
}
