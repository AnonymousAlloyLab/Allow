package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import java.io.IOException;
import java.util.Map;

/** Internal helpers for constructing bounded worker-only document results. */
final class EngineData {
    /** Prevents construction of this stateless helper. */
    private EngineData() {}

    /**
     * Requires a closed candidate variant.
     * @param node candidate object
     * @param fields exactly required field names
     * @throws IllegalArgumentException for any missing or extra field
     */
    static void shape(JsonNode node, String... fields) {
        if (!node.isObject() || node.size() != fields.length) throw new IllegalArgumentException("candidate shape");
        for (String field : fields) if (!node.hasNonNull(field)) throw new IllegalArgumentException("candidate field");
    }

    /**
     * Compares exact module content while ignoring node-registry array order.
     * @param first checked candidate module
     * @param second trusted base module
     * @return whether all declarations and ID-keyed nodes are identical
     */
    static boolean sameModule(JsonNode first, JsonNode second) {
        if (!first.isObject() || !second.isObject()) return false;
        ObjectNode a = first.deepCopy();
        ObjectNode b = second.deepCopy();
        JsonNode an = a.remove("nodes");
        JsonNode bn = b.remove("nodes");
        if (!a.equals(b) || an == null || bn == null || !an.isArray() || !bn.isArray() || an.size() != bn.size()) return false;
        java.util.Map<String, JsonNode> indexed = new java.util.HashMap<>();
        for (JsonNode node : an) if (indexed.put(node.path("id").asText(), node) != null) return false;
        for (JsonNode node : bn) {
            JsonNode match = indexed.remove(node.path("id").asText());
            if (match == null || !match.equals(node)) return false;
        }
        return indexed.isEmpty();
    }

    /**
     * Re-parses printer output and checks the full independently elaborated module.
     * @param module checked source module
     * @param source exact generated source
     * @return resolved parser module for descriptors
     * @throws Err if Alloy rejects source
     * @throws IOException if isolated parsing I/O fails
     * @throws IllegalArgumentException if structural correspondence fails
     */
    static CompModule roundTrip(JsonNode module, String source) throws Err, IOException {
        CompModule parsed = SourceParser.parse(source);
        int count = new CommandTokenCounter(source).count();
        JsonNode reconstructed = new AlloyModuleReader(parsed, true).read(count);
        if (!new ModuleEquivalence(module, reconstructed).matches()) throw new IllegalArgumentException("round-trip correspondence");
        return parsed;
    }

    /**
     * Creates a closed worker result without artifact authority.
     * @param mode support mode
     * @param source exact validated source
     * @param module checked module or null
     * @param occurrences verified source occurrences
     * @param trivia exact source comments
     * @param descriptors parser-derived internal command descriptors
     * @param diagnostics bounded projection notices
     * @param remapping draft-to-server ID map
     * @return independent result object
     */
    static ObjectNode result(String mode, String source, JsonNode module, JsonNode occurrences, JsonNode trivia,
            JsonNode descriptors, JsonNode diagnostics, Map<String, String> remapping) {
        ObjectNode result = JsonNodeFactory.instance.objectNode();
        result.put("mode", mode);
        result.put("source", source);
        result.put("sourceHash", ArtifactIntegrity.hash(source));
        if (module == null) result.putNull("module"); else result.set("module", module.deepCopy());
        result.set("occurrences", occurrences.deepCopy());
        result.set("trivia", trivia.deepCopy());
        result.set("analysisDescriptors", descriptors.deepCopy());
        result.set("diagnostics", diagnostics.deepCopy());
        ObjectNode ids = result.putObject("idRemapping");
        for (Map.Entry<String, String> entry : remapping.entrySet()) ids.put(entry.getKey(), entry.getValue());
        return result;
    }

    /**
     * Detects missing expression and applicable token-role locations.
     * @param module checked syntax forest
     * @param occurrences verified occurrence records
     * @return whether any expected role is unavailable
     */
    static boolean locationsUnavailable(JsonNode module, JsonNode occurrences) {
        java.util.Set<String> present = new java.util.HashSet<>();
        for (JsonNode occurrence : occurrences) present.add(occurrence.path("occurrenceId").asText());
        for (JsonNode node : module.path("nodes")) {
            String id = node.path("id").asText();
            String tag = node.path("tag").asText();
            if (!present.contains(id + ":expression")) return true;
            if ((tag.endsWith("_ref") || tag.equals("predicate_call")) && !present.contains(id + ":reference")) return true;
            if (!tag.endsWith("_ref") && !tag.equals("predicate_call") && !present.contains(id + ":operator")) return true;
            if (node.has("binder") && !present.contains(id + ":binder")) return true;
        }
        return false;
    }

    /**
     * Creates bounded machine-readable projection notices.
     * @param locationUnavailable whether any role has no reliable location
     * @param orphaned number of visible orphan comments
     * @return notice array
     */
    static ArrayNode notices(boolean locationUnavailable, int orphaned) {
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        if (locationUnavailable) result.addObject().put("code", "LOCATION_UNAVAILABLE").put("message", "Some source locations are unavailable.");
        if (orphaned > 0) result.addObject().put("code", "TRIVIA_RELOCATED").put("message", "Some comments moved to the orphan bucket.");
        return result;
    }

    /**
     * Counts explicitly orphaned comment records.
     * @param trivia comment token records
     * @return orphan count
     */
    static int orphanCount(JsonNode trivia) {
        int count = 0;
        for (JsonNode item : trivia) if (item.path("anchor").path("kind").asText().equals("orphan")) count++;
        return count;
    }
}
