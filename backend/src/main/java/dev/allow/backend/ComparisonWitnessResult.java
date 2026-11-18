package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

/** Strict bounded SAT witness projection validation for oracle parity publication. */
final class ComparisonWitnessResult {
    /** Prevents construction. */
    private ComparisonWitnessResult() {}

    /** Checks static comparison trace metadata and every displayed state.
     * @param witness owned checked-solver projection
     * @throws IOException malformed display evidence
     */
    static void check(JsonNode witness) throws IOException {
        DocumentJson.fields(witness, "states", "traceLength", "loopState", "truncated", "fullInstanceHash");
        integer(witness.path("traceLength"), 1, 10);
        integer(witness.path("loopState"), -1, witness.path("traceLength").intValue() - 1);
        require(witness.path("truncated").isBoolean());
        array(witness.path("states"), 10);
        require(witness.path("states").size() == witness.path("traceLength").intValue());
        for (JsonNode state : witness.path("states")) state(state);
    }

    /** Checks closed atom memberships and ordered relation projections.
     * @param state one complete bounded display state
     * @throws IOException malformed state
     */
    private static void state(JsonNode state) throws IOException {
        DocumentJson.fields(state, "atoms", "relations");
        array(state.path("atoms"), 1000); array(state.path("relations"), 128);
        Set<String> ids = new HashSet<>(), names = new HashSet<>();
        for (JsonNode atom : state.path("atoms")) {
            DocumentJson.fields(atom, "id", "memberships"); text(atom.path("id"));
            require(ids.add(atom.path("id").asText())); array(atom.path("memberships"), 2048);
            require(!atom.path("memberships").isEmpty());
            for (JsonNode member : atom.path("memberships")) text(member);
        }
        for (JsonNode relation : state.path("relations")) {
            DocumentJson.fields(relation, "name", "arity", "tuples"); text(relation.path("name"));
            require(names.add(relation.path("name").asText())); integer(relation.path("arity"), 1, 8);
            array(relation.path("tuples"), 1000);
            for (JsonNode row : relation.path("tuples")) {
                require(row.isArray() && row.size() == relation.path("arity").intValue());
                for (JsonNode atom : row) text(atom);
            }
        }
    }

    /** Requires exact bounded integer metadata without coercion or overflow.
     * @param value candidate integer
     * @param minimum inclusive minimum
     * @param maximum inclusive maximum
     * @throws IOException invalid integer
     */
    private static void integer(JsonNode value, int minimum, int maximum) throws IOException {
        require(value.isIntegralNumber() && value.canConvertToInt() && value.intValue() >= minimum && value.intValue() <= maximum);
    }

    /** Requires a bounded display string.
     * @param value exact display identity
     * @throws IOException malformed text
     */
    private static void text(JsonNode value) throws IOException { require(value.isTextual() && !value.asText().isEmpty() && value.asText().length() <= 512); }

    /** Requires a bounded array.
     * @param value candidate array
     * @param maximum maximum size
     * @throws IOException invalid array
     */
    private static void array(JsonNode value, int maximum) throws IOException { require(value.isArray() && value.size() <= maximum); }

    /** Rejects malformed witness projection data.
     * @param condition required invariant
     * @throws IOException violation
     */
    private static void require(boolean condition) throws IOException { if (!condition) throw new IOException("Malformed comparison witness"); }
}
