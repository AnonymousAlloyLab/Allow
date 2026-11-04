package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import java.io.IOException;

/** Validates a full immutable block candidate in the isolated worker. */
final class BlockValidation {
    private final JsonNode candidate;
    private final JsonNode base;
    private final JsonNode inventory;

    /**
     * Creates validation state for a frozen request.
     * @param candidate complete block candidate
     * @param base authorized exact-base artifact
     * @param inventory server-owned identity-to-kind subset
     */
    BlockValidation(JsonNode candidate, JsonNode base, JsonNode inventory) {
        this.candidate = candidate;
        this.base = base;
        this.inventory = inventory;
    }

    /**
     * Rejects corrupt trusted base state as infrastructure unavailability.
     * @throws IllegalStateException if the stored base cannot be verified
     */
    private void checkBase() {
        try { new ArtifactIntegrity(base).check(); }
        catch (IllegalArgumentException corrupt) { throw new IllegalStateException("Invalid stored base artifact", corrupt); }
    }

    /**
     * Checks, prints, preserves comments and independently reparses the module.
     * @return provisional worker result
     * @throws Err if the generated source fails to parse
     * @throws IOException if isolated parsing I/O fails
     */
    ObjectNode validate() throws Err, IOException {
        EngineData.shape(candidate, "mode", "module", "presentationCopies");
        JsonNode module = candidate.path("module");
        new ModuleChecker(module).check();
        checkBase();
        new CopyValidator(base, module).check(candidate.path("presentationCopies"));
        if (base.path("mode").asText().equals("BLOCK_SUPPORTED") && EngineData.sameModule(module, base.path("module"))
                && candidate.path("presentationCopies").isEmpty()) {
            return new HistoryValidation(base, inventory).revalidate();
        }
        IdentityRemapper mapper = new IdentityRemapper(inventory);
        JsonNode finalModule = mapper.remap(module);
        new ModuleChecker(finalModule).check();
        ModulePrinter printer = new ModulePrinter(finalModule);
        String printed = printer.print();
        ObjectNode projection = new TriviaTransport(printed, printer.occurrences(), printer)
            .apply(base, candidate.path("presentationCopies"), mapper.mappings());
        String source = projection.path("source").textValue();
        CompModule parsed = EngineData.roundTrip(finalModule, source);
        ArrayNode descriptors = new CommandDescriptors(parsed, finalModule.path("commands"))
            .read(new CommandTokenCounter(source).count());
        return EngineData.result("BLOCK_SUPPORTED", source, finalModule, projection.path("occurrences"),
            projection.path("trivia"), descriptors, EngineData.notices(false, EngineData.orphanCount(projection.path("trivia"))), mapper.mappings());
    }
}
