package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Structural slot names for already validated complete models, without source trivia. */
public final class AnonymousModel {
    private final Map<String, Entry> inventory = new LinkedHashMap<>();
    private final String source;

    /** Records only locally retained declaration identity.
     * @param kind closed declaration kind
     * @param name original display spelling
     * @param shape nominal declaration relationship
     */
    private record Entry(String kind, String name, String shape) {}

    /** Retains a checked named declaration for deterministic traversal.
     * @param kind declaration category
     * @param node mutable copied declaration
     * @param owner owning predicate ID for parameters
     */
    private record Named(String kind, ObjectNode node, String owner) {}

    /** Anonymizes only a complete module previously checked by the trusted worker.
     * @param module checked bounded supported module
     */
    public AnonymousModel(JsonNode module) {
        JsonNode anonymous = module.deepCopy();
        List<Named> declarations = named(anonymous);
        Map<String, String> slots = new HashMap<>();
        for (Named declaration : declarations) {
            String slot = "Slot" + slots.size();
            slots.put(declaration.node().path("id").asText(), slot);
        }
        for (Named declaration : declarations) {
            ObjectNode node = declaration.node();
            String slot = slots.get(node.path("id").asText());
            inventory.put(slot, new Entry(declaration.kind(), node.path("name").asText(), shape(declaration, slots)));
            node.put("name", slot);
        }
        source = new ModulePrinter(anonymous).print();
    }

    /** Returns freshly printed anonymous source without comments or presentation IDs.
     * @return anonymous Alloy source
     */
    public String source() { return source; }

    /** Restores only the exact compatible anonymous declaration inventory.
     * @param generated checked supported generated module
     * @return named source requiring independent ordinary worker validation
     * @throws IllegalArgumentException unknown, duplicate or incompatible slot declaration
     */
    public String restore(JsonNode generated) {
        JsonNode restored = generated.deepCopy();
        List<Named> declarations = named(restored);
        Map<String, String> slots = new HashMap<>();
        Map<String, Named> seen = new HashMap<>();
        for (Named declaration : declarations) {
            String slot = declaration.node().path("name").asText();
            if (!inventory.containsKey(slot) || seen.put(slot, declaration) != null) throw new IllegalArgumentException("UNSUPPORTED_PROFILE");
            slots.put(declaration.node().path("id").asText(), slot);
        }
        if (!seen.keySet().equals(inventory.keySet())) throw new IllegalArgumentException("UNSUPPORTED_PROFILE");
        for (Map.Entry<String, Named> item : seen.entrySet()) {
            Entry expected = inventory.get(item.getKey());
            if (!expected.kind().equals(item.getValue().kind()) || !expected.shape().equals(shape(item.getValue(), slots))) {
                throw new IllegalArgumentException("UNSUPPORTED_PROFILE");
            }
            item.getValue().node().put("name", expected.name());
        }
        return new ModulePrinter(restored).print();
    }

    /** Enumerates every declaration and binder in fixed structural array order.
     * @param module checked complete module copy
     * @return ordered names
     */
    private static List<Named> named(JsonNode module) {
        List<Named> result = new ArrayList<>();
        for (String key : new String[]{"signatures", "fields", "predicates", "facts", "assertions"}) {
            for (JsonNode node : module.path(key)) result.add(new Named(key, (ObjectNode) node, null));
        }
        for (JsonNode predicate : module.path("predicates")) {
            for (JsonNode parameter : predicate.path("parameters")) result.add(new Named("parameter", (ObjectNode) parameter, predicate.path("id").asText()));
        }
        for (JsonNode node : module.path("nodes")) {
            if (node.has("binder")) result.add(new Named("quantifier", (ObjectNode) node.path("binder"), null));
        }
        return result;
    }

    /** Binds nominal field/parameter/binder schemas without expression-body restrictions.
     * @param declaration checked named item
     * @param names checked ID to anonymous slot map
     * @return exact relationship descriptor
     */
    private static String shape(Named declaration, Map<String, String> names) {
        JsonNode node = declaration.node();
        StringBuilder out = new StringBuilder();
        if (declaration.owner() != null) out.append("owner:").append(names.get(declaration.owner())).append(';');
        for (String key : new String[]{"ownerSignatureId", "signatureId"}) {
            if (node.has(key)) out.append(key).append(':').append(names.get(node.path(key).asText())).append(';');
        }
        for (String key : new String[]{"columns", "rangeColumns"}) {
            for (JsonNode column : node.path(key)) out.append(key).append(':').append(names.get(column.asText())).append(';');
        }
        return out.toString();
    }
}
