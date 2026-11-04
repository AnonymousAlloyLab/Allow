package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import java.io.IOException;
import java.util.Map;

/** Parses and conservatively elaborates one exact authored source candidate. */
final class SourceValidation {
    private final JsonNode candidate;

    /**
     * Creates a validator for one source candidate.
     * @param candidate closed SOURCE candidate
     */
    SourceValidation(JsonNode candidate) {
        this.candidate = candidate;
    }

    /**
     * Preserves exact source and chooses supported block or text-only mode.
     * @return provisional worker result
     * @throws Err if Alloy rejects the source
     * @throws IOException if isolated parsing I/O fails
     * @throws IllegalArgumentException for malformed candidate or correspondence failure
     */
    ObjectNode validate() throws Err, IOException {
        EngineData.shape(candidate, "mode", "source");
        if (!candidate.path("source").isTextual()) throw new IllegalArgumentException("source type");
        String source = candidate.path("source").textValue();
        CompModule parsed = SourceParser.parse(source);
        int commands = new CommandTokenCounter(source).count();
        if (!new SourceFragmentGuard(source).supports()) return textOnly(source, parsed, commands);
        AlloyModuleReader reader = new AlloyModuleReader(parsed, true);
        JsonNode module;
        try { module = reader.read(commands); }
        catch (IllegalArgumentException unsupported) { return textOnly(source, parsed, commands); }
        EngineData.roundTrip(module, new ModulePrinter(module).print());
        ArrayNode occurrences = new SourceReferenceMapper(source, module, reader.origins()).map();
        ArrayNode trivia = new SourceTriviaAttacher(source, module, occurrences).attach();
        ArrayNode descriptors = new CommandDescriptors(parsed, module.path("commands")).read(commands);
        return EngineData.result("BLOCK_SUPPORTED", source, module, occurrences, trivia, descriptors,
            EngineData.notices(EngineData.locationsUnavailable(module, occurrences), EngineData.orphanCount(trivia)), Map.of());
    }

    /**
     * Creates a parser-supported text-only result without fabricated syntax nodes.
     * @param source exact source
     * @param parsed policy-checked module
     * @param commands authored command count
     * @return provisional worker result
     */
    private ObjectNode textOnly(String source, CompModule parsed, int commands) {
        ArrayNode empty = JsonNodeFactory.instance.arrayNode();
        ArrayNode trivia = new TextTriviaScanner(source).scan();
        ArrayNode descriptors = new CommandDescriptors(parsed, null).read(commands);
        return EngineData.result("TEXT_ONLY", source, null, empty, trivia, descriptors, empty, Map.of());
    }
}
