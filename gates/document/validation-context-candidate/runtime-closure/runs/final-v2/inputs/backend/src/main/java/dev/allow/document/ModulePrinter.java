package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.HashMap;
import java.util.Map;

/** Prints a previously checked syntax forest as explicit Alloy source. */
final class ModulePrinter {
    private final JsonNode module;
    private final Map<String, String> names = new HashMap<>();
    private final Map<String, JsonNode> nodes = new HashMap<>();
    private final ArrayNode occurrences = JsonNodeFactory.instance.arrayNode();
    private final Map<String, int[]> anchors = new HashMap<>();

    /**
     * Creates a printer for a checked module.
     * @param module closed and checked module
     */
    ModulePrinter(JsonNode module) {
        this.module = module;
    }

    /**
     * Renders a complete module.
     * @return Alloy source
     */
    String print() {
        index();
        StringBuilder out = new StringBuilder();
        for (JsonNode sig : module.path("signatures")) signature(out, sig);
        for (JsonNode pred : module.path("predicates")) predicate(out, pred);
        for (JsonNode fact : module.path("facts")) body(out, fact, "fact");
        for (JsonNode assertion : module.path("assertions")) body(out, assertion, "assert");
        for (JsonNode command : module.path("commands")) command(out, command);
        return stripMarkers(out.toString());
    }

    /** Indexes all reference names and expression nodes. */
    private void index() {
        for (String key : new String[]{"signatures", "fields", "predicates", "facts", "assertions"}) {
            for (JsonNode item : module.path(key)) names.put(text(item, "id"), text(item, "name"));
        }
        for (JsonNode pred : module.path("predicates")) {
            for (JsonNode param : pred.path("parameters")) names.put(text(param, "id"), text(param, "name"));
        }
        for (JsonNode node : module.path("nodes")) {
            nodes.put(text(node, "id"), node);
            if (node.has("binder")) names.put(text(node.path("binder"), "id"), text(node.path("binder"), "name"));
        }
    }

    /**
     * Emits a signature and its owned fields.
     * @param out output buffer
     * @param sig signature declaration
     */
    private void signature(StringBuilder out, JsonNode sig) {
        StringBuilder block = new StringBuilder();
        String mult = text(sig, "multiplicity");
        if (!mult.equals("set")) block.append(mult).append(' ');
        block.append("sig ").append(text(sig, "name")).append(" {\n");
        boolean first = true;
        for (JsonNode field : module.path("fields")) {
            if (!text(field, "ownerSignatureId").equals(text(sig, "id"))) continue;
            if (!first) block.append(",\n");
            String body = "  " + text(field, "name") + ": " + text(field, "multiplicity")
                + " (" + columns(field.path("rangeColumns")) + ")";
            block.append(mark(text(field, "id"), "declaration", body));
            first = false;
        }
        block.append("\n}\n");
        out.append(mark(text(sig, "id"), "declaration", block.toString()));
    }

    /**
     * Emits a predicate and its explicitly set-valued parameters.
     * @param out output buffer
     * @param pred predicate declaration
     */
    private void predicate(StringBuilder out, JsonNode pred) {
        StringBuilder block = new StringBuilder("pred ").append(text(pred, "name")).append('[');
        boolean first = true;
        for (JsonNode parameter : pred.path("parameters")) {
            if (!first) block.append(", ");
            String body = text(parameter, "name") + ": set (" + columns(parameter.path("columns")) + ")";
            block.append(mark(text(parameter, "id"), "declarationBinder", body));
            first = false;
        }
        block.append("] { ").append(expr(text(pred, "bodyId"))).append(" }\n");
        out.append(mark(text(pred, "id"), "declaration", block.toString()));
    }

    /**
     * Emits a fact or assertion.
     * @param out output buffer
     * @param declaration named formula
     * @param keyword Alloy keyword
     */
    private void body(StringBuilder out, JsonNode declaration, String keyword) {
        String block = keyword + " " + text(declaration, "name") + " { "
            + expr(text(declaration, "bodyId")) + " }\n";
        out.append(mark(text(declaration, "id"), "declaration", block));
    }

    /**
     * Emits an explicitly bounded command.
     * @param out output buffer
     * @param command checked command
     */
    private void command(StringBuilder out, JsonNode command) {
        String block = text(command, "tag") + " " + names.get(text(command, "targetId")) + " for "
            + command.path("uniformScope").intValue() + " but 4 Int, 3 seq\n";
        out.append(mark(text(command, "id"), "declaration", block));
    }

    /**
     * Emits a nominal product schema.
     * @param columns signature identities
     * @return Alloy product expression
     */
    private String columns(JsonNode columns) {
        StringBuilder result = new StringBuilder();
        for (JsonNode column : columns) {
            if (!result.isEmpty()) result.append(" -> ");
            result.append(names.get(column.textValue()));
        }
        return result.toString();
    }

    /**
     * Emits a checked expression recursively.
     * @param id expression identity
     * @return parenthesized Alloy expression
     */
    private String expr(String id) {
        JsonNode node = nodes.get(id);
        String printed = expression(node, text(node, "tag"));
        return mark(id, "expression", printed);
    }

    /**
     * Emits the body of one checked expression.
     * @param node expression
     * @param tag closed operator tag
     * @return rendered expression, including nested markers
     */
    private String expression(JsonNode node, String tag) {
        if (tag.endsWith("_ref")) return mark(text(node, "id"), "reference", names.get(text(node, "targetId")));
        if (tag.equals("predicate_call")) return call(node);
        if (tag.equals("all_quant") || tag.equals("some_quant")) return quantifier(node, tag);
        if (node.has("operandId")) return unary(node, tag);
        return "(" + expr(text(node, "leftId")) + " " + mark(text(node, "id"), "operator", operator(tag))
            + " " + expr(text(node, "rightId")) + ")";
    }

    /**
     * Returns a defensive copy of the last print's expression spans.
     * @return ordered occurrence records
     */
    ArrayNode occurrences() {
        return occurrences.deepCopy();
    }

    /**
     * Returns one printer-internal declaration or binder boundary.
     * @param id declaration or binder identity
     * @return copied start/end boundary, or null if unavailable
     */
    int[] anchor(String id) {
        int[] span = anchors.get(id);
        return span == null ? null : span.clone();
    }

    /**
     * Marks one expression role for exact offset recording.
     * @param id expression identity
     * @param role closed occurrence role
     * @param text emitted text
     * @return marked text
     */
    private String mark(String id, String role, String text) {
        String key = id + "|" + role;
        return String.valueOf((char) 1) + key + (char) 2 + text + (char) 3 + key + (char) 4;
    }

    /**
     * Removes private traversal markers and records exact UTF-16 spans.
     * @param marked printer-internal marked text
     * @return valid Alloy source without markers
     * @throws IllegalStateException for an internal marker invariant failure
     */
    private String stripMarkers(String marked) {
        occurrences.removeAll();
        anchors.clear();
        StringBuilder source = new StringBuilder();
        Map<String, Integer> starts = new HashMap<>();
        for (int index = 0; index < marked.length();) {
            char c = marked.charAt(index++);
            if (c != 1 && c != 3) { source.append(c); continue; }
            int end = marked.indexOf(c == 1 ? (char) 2 : (char) 4, index);
            if (end < 0) throw new IllegalStateException("invalid printer marker");
            String id = marked.substring(index, end);
            if (c == 1) starts.put(id, source.length());
            else occurrence(id, starts.remove(id), source.length());
            index = end + 1;
        }
        if (!starts.isEmpty()) throw new IllegalStateException("unclosed printer marker");
        return source.toString();
    }

    /**
     * Stores one exact expression-role span.
     * @param id expression identity
     * @param start UTF-16 start
     * @param end UTF-16 exclusive end
     * @throws IllegalStateException if the opening marker is missing
     */
    private void occurrence(String id, Integer start, int end) {
        if (start == null) throw new IllegalStateException("missing printer marker");
        int separator = id.lastIndexOf('|');
        String nodeId = id.substring(0, separator);
        String role = id.substring(separator + 1);
        if (role.equals("declaration") || role.equals("declarationBinder")) {
            anchors.put(nodeId, new int[]{start, end});
            return;
        }
        ObjectNode item = occurrences.addObject();
        item.put("occurrenceId", nodeId + ":" + role);
        item.put("nodeId", nodeId);
        item.put("role", role);
        item.put("startUtf16", start);
        item.put("endUtf16", end);
    }

    /**
     * Emits an ordered predicate invocation.
     * @param node call
     * @return Alloy call expression
     */
    private String call(JsonNode node) {
        StringBuilder out = new StringBuilder(mark(text(node, "id"), "reference", names.get(text(node, "predicateId")))).append('[');
        boolean first = true;
        for (JsonNode arg : node.path("arguments")) {
            if (!first) out.append(", ");
            out.append(expr(arg.textValue()));
            first = false;
        }
        return out.append(']').toString();
    }

    /**
     * Emits a single-atom quantifier.
     * @param node quantifier
     * @param tag quantifier tag
     * @return Alloy quantifier
     */
    private String quantifier(JsonNode node, String tag) {
        JsonNode binder = node.path("binder");
        String declaration = mark(text(node, "id"), "binder", text(binder, "name")) + ": "
            + names.get(text(binder, "signatureId"));
        return "(" + mark(text(node, "id"), "operator", tag.equals("all_quant") ? "all" : "some") + " "
            + mark(text(binder, "id"), "declarationBinder", declaration) + " | " + expr(text(node, "bodyId")) + ")";
    }

    /**
     * Emits a unary expression.
     * @param node unary node
     * @param tag operator tag
     * @return Alloy expression
     */
    private String unary(JsonNode node, String tag) {
        String op = switch (tag) {
            case "some_test" -> "some";
            case "no_test" -> "no";
            case "one_test" -> "one";
            case "lone_test" -> "lone";
            case "transpose" -> "~";
            default -> "not";
        };
        return "(" + mark(text(node, "id"), "operator", op) + " (" + expr(text(node, "operandId")) + "))";
    }

    /**
     * Maps a checked binary operator to Alloy syntax.
     * @param tag operator tag
     * @return operator spelling
     */
    private String operator(String tag) {
        return switch (tag) {
            case "equal" -> "=";
            case "subset" -> "in";
            case "union" -> "+";
            case "intersection" -> "&";
            case "difference" -> "-";
            case "join" -> ".";
            case "product" -> "->";
            default -> tag;
        };
    }

    /**
     * Reads a required property from checked JSON.
     * @param n object
     * @param key property name
     * @return value
     */
    private static String text(JsonNode n, String key) {
        return n.path(key).textValue();
    }
}
