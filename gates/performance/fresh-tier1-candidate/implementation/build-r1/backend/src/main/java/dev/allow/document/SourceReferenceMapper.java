package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Pos;
import edu.mit.csail.sdg.ast.Expr;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Conservatively maps source references when parser coordinates can be verified. */
final class SourceReferenceMapper {
    private final String source;
    private final JsonNode module;
    private final Map<String, Expr> origins;
    private final Map<String, String> names = new HashMap<>();
    private final java.util.Set<Integer> tokenStarts = new java.util.HashSet<>();
    private final java.util.Set<Integer> tokenEnds = new java.util.HashSet<>();

    /**
     * Creates a mapper for the exact source and its elaborated syntax.
     * @param source exact original source
     * @param module fully checked elaborated module
     * @param origins parser expression objects indexed by node ID
     */
    SourceReferenceMapper(String source, JsonNode module, Map<String, Expr> origins) {
        this.source = source;
        this.module = module;
        this.origins = origins;
    }

    /**
     * Maps only references with verified file-parser token boundaries.
     * @return occurrence records; missing roles mean unavailable
     */
    ArrayNode map() {
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        indexNames();
        for (SourceLexer.Token token : new SourceLexer(source).read()) {
            if (!token.comment()) { tokenStarts.add(token.start()); tokenEnds.add(token.end()); }
        }
        for (JsonNode node : module.path("nodes")) {
            expression(node, result);
            reference(node, result);
            operator(node, result);
        }
        return unique(result);
    }

    /**
     * Omits every reference involved in an ambiguous interval collision.
     * @param candidates provisional source spans
     * @return unambiguous copied spans
     */
    private ArrayNode unique(ArrayNode candidates) {
        Map<String, Integer> counts = new HashMap<>();
        for (JsonNode item : candidates) {
            String role = item.path("role").asText();
            counts.merge(role + ":" + key(item), 1, Integer::sum);
        }
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        for (JsonNode item : candidates) {
            String role = item.path("role").asText();
            if (counts.getOrDefault(role + ":" + key(item), 0) == 1) result.add(item.deepCopy());
        }
        return result;
    }

    /**
     * Identifies a source interval independent of occurrence identity.
     * @param span occurrence record
     * @return interval key
     */
    private String key(JsonNode span) {
        return span.path("startUtf16").asInt() + ":" + span.path("endUtf16").asInt();
    }

    /** Indexes declared display names by their checked stable identities. */
    private void indexNames() {
        for (String key : List.of("signatures", "fields", "predicates")) {
            for (JsonNode n : module.path(key)) names.put(n.path("id").textValue(), n.path("name").textValue());
        }
        for (JsonNode p : module.path("predicates")) {
            for (JsonNode n : p.path("parameters")) names.put(n.path("id").textValue(), n.path("name").textValue());
        }
        for (JsonNode n : module.path("nodes")) {
            if (n.has("binder")) names.put(n.path("binder").path("id").textValue(), n.path("binder").path("name").textValue());
        }
    }

    /**
     * Records an expression span only when coordinates and token boundaries agree.
     * @param node checked expression node
     * @param result occurrence array
     */
    private void expression(JsonNode node, ArrayNode result) {
        String id = node.path("id").textValue();
        Expr origin = origins.get(id);
        if (origin == null) return;
        Expr expression = node.path("tag").asText().endsWith("_ref") ? origin : origin.deNOP();
        int[] span = interval(expression.span());
        if (span == null || !tokenStarts.contains(span[0]) || !tokenEnds.contains(span[1])) return;
        occurrence(result, id, "expression", span);
    }

    /**
     * Records a reference only when the exact parser token is verified.
     * @param node checked expression node
     * @param result occurrence array
     */
    private void reference(JsonNode node, ArrayNode result) {
        String tag = node.path("tag").asText();
        if (!tag.endsWith("_ref")) return;
        String id = node.path("id").textValue();
        Expr origin = origins.get(id);
        String target = names.get(node.path("targetId").textValue());
        if (origin == null || target == null) return;
        int[] span = verified(origin.pos, target);
        if (span == null) span = verified(origin.span(), target);
        if (span == null) return;
        occurrence(result, id, "reference", span);
    }

    /**
     * Records an operator only when its exact token and position agree.
     * @param node checked expression node
     * @param result occurrence array
     */
    private void operator(JsonNode node, ArrayNode result) {
        String tag = node.path("tag").asText();
        String expected = operatorToken(tag);
        Expr origin = origins.get(node.path("id").textValue());
        if (expected == null || origin == null) return;
        int[] span = verified(origin.pos, expected);
        if (span != null) occurrence(result, node.path("id").textValue(), "operator", span);
    }

    /**
     * Maps a closed operator to its canonical source spelling.
     * @param tag expression tag
     * @return canonical token or null for a non-operator
     */
    private String operatorToken(String tag) {
        return switch (tag) {
            case "and", "or", "not", "implies", "iff" -> tag;
            case "some_test", "some_quant" -> "some";
            case "no_test" -> "no";
            case "one_test" -> "one";
            case "lone_test" -> "lone";
            case "all_quant" -> "all";
            case "equal" -> "=";
            case "subset" -> "in";
            case "union" -> "+";
            case "intersection" -> "&";
            case "difference" -> "-";
            case "join" -> ".";
            case "product" -> "->";
            case "transpose" -> "~";
            default -> null;
        };
    }

    /**
     * Verifies a parser position against exact source and line/column coordinates.
     * @param pos Alloy position
     * @param expected exact reference token
     * @return verified half-open UTF-16 interval, or null
     */
    private int[] verified(Pos pos, String expected) {
        int[] span = interval(pos);
        return span != null && source.substring(span[0], span[1]).equals(expected) ? span : null;
    }

    /**
     * Converts a parser position only after exact line/column verification.
     * @param pos parser position
     * @return valid half-open UTF-16 interval or null
     */
    private int[] interval(Pos pos) {
        if (pos == null || pos == Pos.UNKNOWN) return null;
        int[] span;
        try { span = pos.toStartEnd(source); } catch (RuntimeException error) { return null; }
        if (span == null || span.length != 2 || span[0] < 0 || span[1] <= span[0] || span[1] > source.length()) return null;
        int[] first = coordinate(span[0]);
        int[] last = coordinate(span[1] - 1);
        return first[0] == pos.x && first[1] == pos.y && last[0] == pos.x2 && last[1] == pos.y2 ? span : null;
    }

    /**
     * Computes one-based UTF-16 line and column coordinates without normalization.
     * @param index UTF-16 index in the exact source
     * @return column and line
     */
    private int[] coordinate(int index) {
        int line = 1;
        int column = 1;
        for (int i = 0; i < index; i++) {
            if (source.charAt(i) == '\r') {
                if (i + 1 < index && source.charAt(i + 1) == '\n') i++;
                line++;
                column = 1;
            } else if (source.charAt(i) == '\n') { line++; column = 1; }
            else column++;
        }
        return new int[]{column, line};
    }

    /**
     * Adds one exact source-bound occurrence.
     * @param result occurrence array
     * @param id expression ID
     * @param role closed role
     * @param span verified source interval
     */
    private void occurrence(ArrayNode result, String id, String role, int[] span) {
        ObjectNode item = result.addObject();
        item.put("occurrenceId", id + ":" + role);
        item.put("nodeId", id);
        item.put("role", role);
        item.put("startUtf16", span[0]);
        item.put("endUtf16", span[1]);
    }
}
