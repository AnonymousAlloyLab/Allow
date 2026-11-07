package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.Hashes;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

/** Closed oracle parity provenance and shared-correspondence boundary. */
final class OracleParityResult {
    /** Prevents construction. */
    private OracleParityResult() {}

    /** Checks exact target, oracle, checked-source selection and correspondence.
     * @param data owned successful worker data
     * @param request original closed parity intent
     * @throws IOException malformed or substituted evidence
     */
    static void check(JsonNode data, JsonNode request) throws IOException {
        DocumentJson.fields(data, "synthesizedSourceHash", "categories", "classification", "moduleHash", "scope", "bitwidth", "maxseq",
                "sourceHash", "left", "right", "correspondence", "targetId", "oracle");
        require(data.path("targetId").equals(request.path("targetId")));
        require(data.path("bitwidth").canConvertToInt() && data.path("bitwidth").isIntegralNumber() && data.path("bitwidth").intValue() == 4);
        require(data.path("maxseq").canConvertToInt() && data.path("maxseq").isIntegralNumber() && data.path("maxseq").intValue() == 3);
        selection(data.path("left")); selection(data.path("right")); selection(data.path("oracle"));
        for (String field : new String[]{"sourceHash", "predicate"}) {
            require(data.path("right").path(field).equals(request.path("oracle").path(field)));
            require(data.path("oracle").path(field).equals(request.path("oracle").path(field)));
        }
        String combined = Hashes.text(data.path("left").path("sourceHash").asText() + ":" + data.path("right").path("sourceHash").asText());
        require(combined.equals(data.path("sourceHash").asText()));
        correspondence(data.path("correspondence"), data);
    }

    /** Checks a bounded source selection without reflecting uploaded source.
     * @param selection projected identity
     * @throws IOException malformed selection
     */
    private static void selection(JsonNode selection) throws IOException {
        DocumentJson.fields(selection, "sourceHash", "predicate");
        require(selection.path("sourceHash").isTextual() && selection.path("sourceHash").asText().matches("[0-9a-f]{64}"));
        text(selection.path("predicate"));
    }

    /** Checks closed positional shared parameter and declaration descriptions.
     * @param value shared correspondence
     * @param data paired source selections
     * @throws IOException malformed correspondence
     */
    private static void correspondence(JsonNode value, JsonNode data) throws IOException {
        DocumentJson.fields(value, "leftPredicate", "rightPredicate", "parameters", "declarations");
        require(value.path("leftPredicate").equals(data.path("left").path("predicate")));
        require(value.path("rightPredicate").equals(data.path("right").path("predicate")));
        array(value.path("parameters"), 16); array(value.path("declarations"), 2048);
        Set<String> ids = new HashSet<>();
        for (JsonNode parameter : value.path("parameters")) {
            DocumentJson.fields(parameter, "leftName", "rightName", "columns", "sharedId");
            text(parameter.path("leftName")); text(parameter.path("rightName")); text(parameter.path("sharedId"));
            require(ids.add(parameter.path("sharedId").asText())); array(parameter.path("columns"), 8);
            require(!parameter.path("columns").isEmpty());
            for (JsonNode column : parameter.path("columns")) text(column);
        }
        for (JsonNode declaration : value.path("declarations")) {
            DocumentJson.fields(declaration, "kind", "name"); text(declaration.path("name"));
            require(Set.of("signature", "field").contains(declaration.path("kind").asText()));
        }
        assignments(data, value.path("parameters"));
    }

    /** Binds each SAT assignment to the exact shared positional parameter schema.
     * @param data complete comparison evidence
     * @param parameters checked correspondence
     * @throws IOException missing or substituted assignment binding
     */
    private static void assignments(JsonNode data, JsonNode parameters) throws IOException {
        for (JsonNode category : data.path("categories")) {
            if (!category.path("status").asText().equals("SAT")) continue;
            ComparisonWitnessResult.check(category.path("witness"));
            require(category.path("assignment").isArray() && category.path("assignment").size() == parameters.size());
            for (JsonNode parameter : parameters) {
                JsonNode found = null;
                for (JsonNode binding : category.path("assignment"))
                    if (binding.path("id").equals(parameter.path("sharedId"))) found = binding;
                require(found != null);
                for (String field : new String[]{"leftName", "rightName", "columns"}) require(found.path(field).equals(parameter.path(field)));
                require(found.path("name").equals(parameter.path("leftName")));
            }
        }
    }

    /** Checks bounded arrays.
     * @param value exact array
     * @param maximum maximum cardinality
     * @throws IOException invalid array
     */
    private static void array(JsonNode value, int maximum) throws IOException { require(value.isArray() && value.size() <= maximum); }

    /** Checks a nonempty bounded name.
     * @param value exact name
     * @throws IOException malformed name
     */
    private static void text(JsonNode value) throws IOException { require(value.isTextual() && !value.asText().isEmpty() && value.asText().length() <= 128); }

    /** Rejects malformed owned-worker evidence.
     * @param condition required invariant
     * @throws IOException violation
     */
    private static void require(boolean condition) throws IOException { if (!condition) throw new IOException("Malformed oracle parity evidence"); }
}
