package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.util.Set;

/** Strict successful comparison payload boundary before owner-bound publication. */
final class ComparisonResult {
    /** Prevents construction of the stateless result validator. */
    private ComparisonResult() {}

    /** Checks exact successful payload structure and the requested selection/bounds.
     * @param data bounded owned child data
     * @param request original closed intent
     * @param operation trusted route dispatch
     * @throws IOException missing, malformed or substituted child evidence
     */
    static void check(JsonNode data, JsonNode request, String operation) throws IOException {
        try {
            if (operation.equals("COMPARISON_MODEL")) { inspection(data, request); return; }
            if (operation.equals("COMPARE")) {
                DocumentJson.fields(data, "synthesizedSourceHash", "categories", "classification", "moduleHash", "scope", "bitwidth", "maxseq", "sourceHash", "leftId", "rightId");
                require(data.path("leftId").equals(request.path("leftId")) && data.path("rightId").equals(request.path("rightId")));
            } else if (operation.equals("ORACLE_PARITY")) {
                OracleParityResult.check(data, request);
            } else {
                DocumentJson.fields(data, "synthesizedSourceHash", "categories", "classification", "moduleHash", "scope", "bitwidth", "maxseq", "sourceHash", "left", "right", "correspondence");
                selection(data.path("left"), request.path("left")); selection(data.path("right"), request.path("right"));
                require(data.path("correspondence").isObject());
            }
            require(data.path("scope").equals(request.path("scope")) && data.path("bitwidth").asInt() == 4 && data.path("maxseq").asInt() == 3);
            for (String field : new String[]{"synthesizedSourceHash", "moduleHash", "sourceHash"}) hash(data.path(field));
            categories(data);
        } catch (IllegalArgumentException malformed) { throw new IOException("Malformed comparison evidence", malformed); }
    }

    /** Checks parser-derived inspection choices against exact uploaded bytes.
     * @param data owned inspection response
     * @param request original uploaded source/hash
     * @throws IOException malformed descriptor or source mismatch
     */
    private static void inspection(JsonNode data, JsonNode request) throws IOException {
        DocumentJson.fields(data, "sourceHash", "predicates");
        require(data.path("sourceHash").equals(request.path("sourceHash")));
        array(data.path("predicates"), 128);
        Set<String> names = new java.util.HashSet<>();
        for (JsonNode predicate : data.path("predicates")) {
            DocumentJson.fields(predicate, "name", "parameters");
            require(predicate.path("name").isTextual() && names.add(predicate.path("name").asText()));
            array(predicate.path("parameters"), 16);
            for (JsonNode parameter : predicate.path("parameters")) {
                DocumentJson.fields(parameter, "name", "columns");
                require(parameter.path("name").isTextual()); columns(parameter.path("columns"));
            }
        }
    }

    /** Binds file selections without trusting filenames or guessed predicate names.
     * @param result projected source selection
     * @param request original exact selection
     * @throws IOException selection mismatch
     */
    private static void selection(JsonNode result, JsonNode request) throws IOException {
        DocumentJson.fields(result, "sourceHash", "predicate");
        require(result.path("sourceHash").equals(request.path("sourceHash")) && result.path("predicate").equals(request.path("predicate")));
    }

    /** Verifies four complete outcomes and derives the only admissible classification.
     * @param data complete comparison result
     * @throws IOException incomplete or contradictory result
     */
    private static void categories(JsonNode data) throws IOException {
        JsonNode categories = data.path("categories");
        DocumentJson.fields(categories, "both", "leftOnly", "rightOnly", "neither");
        String[] names = {"both", "leftOnly", "rightOnly", "neither"};
        boolean all = true;
        for (int index = 0; index < 4; index++) {
            JsonNode category = categories.path(names[index]);
            String status = category.path("status").asText();
            require(Set.of("SAT", "UNSAT").contains(status));
            if (status.equals("SAT")) { witness(category, index); all = false; }
            else DocumentJson.fields(category, "status");
        }
        boolean different = categories.path("leftOnly").path("status").asText().equals("SAT")
                || categories.path("rightOnly").path("status").asText().equals("SAT");
        require(data.path("classification").asText().equals(all ? "NO_INSTANCES" : different ? "DISTINGUISHED" : "AGREEMENT"));
    }

    /** Verifies truth-pair replay, full-evidence hashes and bounded witness assignments.
     * @param category one complete SAT result
     * @param index expected truth category
     * @throws IOException missing or malformed evidence
     */
    private static void witness(JsonNode category, int index) throws IOException {
        DocumentJson.fields(category, "status", "left", "right", "witness", "assignment", "evidenceHash");
        require(category.path("left").isBoolean() && category.path("left").asBoolean() == (index < 2));
        require(category.path("right").isBoolean() && category.path("right").asBoolean() == (index == 0 || index == 2));
        hash(category.path("evidenceHash"));
        JsonNode witness = category.path("witness");
        DocumentJson.fields(witness, "states", "traceLength", "loopState", "truncated", "fullInstanceHash");
        hash(witness.path("fullInstanceHash")); array(witness.path("states"), 10);
        require(witness.path("truncated").isBoolean());
        array(category.path("assignment"), 32);
        Set<String> ids = new java.util.HashSet<>();
        for (JsonNode binding : category.path("assignment")) {
            if (binding.has("leftName")) DocumentJson.fields(binding, "id", "name", "columns", "truncated", "tuples", "leftName", "rightName");
            else DocumentJson.fields(binding, "id", "name", "columns", "truncated", "tuples");
            require(binding.path("id").isTextual() && ids.add(binding.path("id").asText()) && binding.path("name").isTextual());
            columns(binding.path("columns")); array(binding.path("tuples"), 1000); require(binding.path("truncated").isBoolean());
            for (JsonNode row : binding.path("tuples")) {
                require(row.isArray() && row.size() == binding.path("columns").size());
                for (JsonNode atom : row) require(atom.isTextual());
            }
        }
    }

    /** Checks a nonempty nominal product schema.
     * @param columns ordered nominal signature names
     * @throws IOException malformed schema
     */
    private static void columns(JsonNode columns) throws IOException {
        array(columns, 8); require(!columns.isEmpty());
        for (JsonNode column : columns) require(column.isTextual());
    }

    /** Requires a bounded array without coercion.
     * @param value candidate array
     * @param maximum item limit
     * @throws IOException invalid array
     */
    private static void array(JsonNode value, int maximum) throws IOException { require(value.isArray() && value.size() <= maximum); }

    /** Checks full SHA-256 identity syntax.
     * @param value identity string
     * @throws IOException missing or invalid identity
     */
    private static void hash(JsonNode value) throws IOException { require(value.isTextual() && value.asText().matches("[0-9a-f]{64}")); }

    /** Rejects malformed worker evidence independently of authored model failures.
     * @param condition validated invariant
     * @throws IOException worker protocol violation
     */
    private static void require(boolean condition) throws IOException { if (!condition) throw new IOException("Malformed comparison evidence"); }
}
