package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Err;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Worker-only parsing and preparation of two uploaded comparison models. */
public final class ComparisonModels {
    /** Result with two owned formula roots and explicit source correspondence. */
    public record Prepared(JsonNode module, String leftArmId, String rightArmId, JsonNode correspondence) {}
    /** Prevents construction of the stateless adapter. */
    private ComparisonModels() {}

    /**
     * Inspects a supported exact source and returns its predicate choices.
     * @param source exact authored source
     * @param expectedHash exact SHA-256 identity
     * @return bounded parser-derived descriptor
     * @throws Err Alloy rejection
     * @throws IOException temporary file failure
     */
    public static JsonNode inspect(String source, String expectedHash) throws Err, IOException {
        JsonNode module = parse(source, expectedHash);
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("sourceHash", expectedHash);
        ArrayNode choices = result.putArray("predicates");
        for (JsonNode predicate : module.path("predicates")) choices.add(descriptor(module, predicate));
        return result;
    }

    /**
     * Creates a shared checked comparison module for selected predicates.
     * @param leftSource exact first source
     * @param leftHash first source digest
     * @param leftName selected first predicate
     * @param rightSource exact second source
     * @param rightHash second source digest
     * @param rightName selected second predicate
     * @return independently checked synthetic module and arm identities
     * @throws Err Alloy rejection
     * @throws IOException temporary file failure
     */
    public static Prepared prepare(String leftSource, String leftHash, String leftName,
            String rightSource, String rightHash, String rightName) throws Err, IOException {
        ObjectNode left = parse(leftSource, leftHash);
        ObjectNode right = parse(rightSource, rightHash);
        return new ComparisonModelsMerge(left, right, leftName, rightName).prepare();
    }

    /**
     * Parses only supported bounded source through the existing worker policy.
     * @param source exact authored text
     * @param hash claimed digest
     * @return independently checked module
     * @throws Err Alloy rejection
     * @throws IOException temporary file failure
     * @throws IllegalArgumentException invalid input
     */
    private static ObjectNode parse(String source, String hash) throws Err, IOException {
        if (source == null || source.getBytes(StandardCharsets.UTF_8).length > 32768
                || !ArtifactIntegrity.hash(source).equals(hash)) throw new IllegalArgumentException("source identity or size");
        if (!new SourceFragmentGuard(source).supports()) throw new IllegalArgumentException("unsupported source fragment");
        var parsed = SourceParser.parse(source);
        ObjectNode module = new AlloyModuleReader(parsed, true).read(0);
        EngineData.roundTrip(module, new ModulePrinter(module).print());
        module.putArray("commands");
        return module;
    }

    /**
     * Projects a predicate and its ordered nominal parameter schemas.
     * @param module checked model
     * @param predicate parser-derived predicate
     * @return public descriptor
     */
    private static ObjectNode descriptor(JsonNode module, JsonNode predicate) {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("name", predicate.path("name").asText());
        ArrayNode params = result.putArray("parameters");
        for (JsonNode param : predicate.path("parameters")) {
            ObjectNode item = params.addObject().put("name", param.path("name").asText());
            ArrayNode columns = item.putArray("columns");
            for (JsonNode column : param.path("columns")) columns.add(ComparisonModelsSupport.name(module, column.asText()));
        }
        return result;
    }
}
