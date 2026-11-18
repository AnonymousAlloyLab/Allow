package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;

/** Display-only shrinking preserves full witness/assignment evidence hashes and truth replay. */
final class ComparisonDisplay {
    /** Prevents construction of the stateless display budget. */
    private ComparisonDisplay() {}

    /** Fits each category within one quarter of the existing bounded response transport.
     * @param category complete verified SAT category
     * @throws IOException bounded projection cannot fit safely
     */
    static void bound(ObjectNode category) throws IOException {
        for (int pass = 0; pass < 16; pass++) {
            if (JsonWire.encode(category).length <= 196608) return;
            for (JsonNode binding : category.path("assignment")) {
                if (halve((ArrayNode) binding.path("tuples"))) ((ObjectNode) binding).put("truncated", true);
            }
            ObjectNode witness = (ObjectNode) category.path("witness");
            for (JsonNode state : witness.path("states")) {
                boolean changed = halve((ArrayNode) state.path("atoms"));
                for (JsonNode relation : state.path("relations")) changed |= halve((ArrayNode) relation.path("tuples"));
                if (changed) witness.put("truncated", true);
            }
        }
        throw new IOException("Comparison display exceeds bounded transport");
    }

    /** Removes only display rows while retaining every full-data hash.
     * @param values bounded display array
     * @return whether any rows were removed
     */
    private static boolean halve(ArrayNode values) {
        int original = values.size();
        int keep = original / 2;
        while (values.size() > keep) values.remove(values.size() - 1);
        return original != keep;
    }
}
