package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Carries validated old comment tokens into a new printer-generated source. */
final class TriviaTransport {
    private final String printed;
    private final ArrayNode occurrences;
    private final ModulePrinter printer;
    private final List<Placement> placements = new ArrayList<>();
    private int orphaned;

    /**
     * Creates transport for one printer result.
     * @param printed marker-free generated source
     * @param occurrences generated source occurrence spans
     * @param printer printer with declaration boundaries
     */
    TriviaTransport(String printed, ArrayNode occurrences, ModulePrinter printer) {
        this.printed = printed;
        this.occurrences = occurrences.deepCopy();
        this.printer = printer;
    }

    /**
     * Transfers original comments and explicit expression copies.
     * @param base exact trusted base artifact
     * @param copies validated presentation-copy entries
     * @param remapping draft-to-server identity map
     * @return generated source, updated spans and fresh comment tokens
     */
    ObjectNode apply(JsonNode base, JsonNode copies, Map<String, String> remapping) {
        String previous = base.path("source").asText("");
        byte[] sourceBytes = previous.getBytes(StandardCharsets.UTF_8);
        boolean textOnly = base.path("mode").asText().equals("TEXT_ONLY");
        for (JsonNode token : base.path("trivia")) transfer(token, sourceBytes, textOnly, copies, remapping);
        placements.sort(Comparator.comparingInt(Placement::position).thenComparingInt(Placement::order)
            .thenComparingInt(Placement::copyOrder));
        return assemble();
    }

    /**
     * Schedules one original comment and its requested copies.
     * @param token trusted base comment token
     * @param source exact base bytes
     * @param textOnly whether base has no block anchors
     * @param copies validated copy entries
     * @param remapping target draft-to-server ID map
     * @throws IllegalArgumentException when a copy target is missing
     */
    private void transfer(JsonNode token, byte[] source, boolean textOnly, JsonNode copies, Map<String, String> remapping) {
        String payload = payload(token, source);
        ObjectNode anchor = token.path("anchor").deepCopy();
        int order = token.path("order").intValue();
        schedule(anchor.deepCopy(), payload, order, -1, textOnly);
        if (textOnly || !anchor.path("kind").asText().equals("expression")) return;
        for (int index = 0; index < copies.size(); index++) {
            JsonNode copy = copies.get(index);
            if (!copy.path("sourceNodeId").asText().equals(anchor.path("nodeId").asText())) continue;
            ObjectNode target = anchor.deepCopy();
            String targetId = remapping.get(copy.path("targetNodeId").asText());
            if (targetId == null) throw new IllegalArgumentException("missing copy identity");
            target.put("nodeId", targetId);
            schedule(target, payload, order, index, false);
        }
    }

    /**
     * Adds a comment placement or an explicit trailing orphan.
     * @param anchor requested anchor
     * @param payload exact token text
     * @param order original token order
     * @param copyOrder presentation-copy index, or -1 for original
     * @param forceOrphan whether old source had no block ownership
     * @throws IllegalArgumentException when a copied role is unavailable
     */
    private void schedule(ObjectNode anchor, String payload, int order, int copyOrder, boolean forceOrphan) {
        int position = forceOrphan ? -1 : position(anchor);
        if (position < 0) {
            if (copyOrder >= 0) throw new IllegalArgumentException("copy role unavailable");
            anchor.removeAll();
            anchor.put("kind", "orphan");
            position = printed.length();
            orphaned++;
        }
        placements.add(new Placement(position, order, copyOrder, payload, anchor));
    }

    /**
     * Resolves a closed anchor against the generated source.
     * @param anchor authoritative anchor
     * @return source offset or -1 if its owner/role disappeared
     */
    private int position(JsonNode anchor) {
        String kind = anchor.path("kind").asText();
        if (kind.equals("module-leading")) return 0;
        if (kind.equals("module-trailing") || kind.equals("orphan")) return printed.length();
        if (kind.equals("expression")) return expressionPosition(anchor);
        String id = kind.equals("binder") ? anchor.path("binderId").asText() : anchor.path("declarationId").asText();
        int[] span = printer.anchor(id);
        return span == null ? -1 : side(anchor, span[0], span[1]);
    }

    /**
     * Resolves an expression role against exact generated occurrence spans.
     * @param anchor expression anchor
     * @return source offset or -1 if unavailable
     */
    private int expressionPosition(JsonNode anchor) {
        for (JsonNode span : occurrences) {
            if (span.path("nodeId").equals(anchor.path("nodeId")) && span.path("role").equals(anchor.path("role"))) {
                return side(anchor, span.path("startUtf16").intValue(), span.path("endUtf16").intValue());
            }
        }
        return -1;
    }

    /**
     * Selects a span boundary according to a validated anchor side.
     * @param anchor anchor
     * @param start inclusive start
     * @param end exclusive end
     * @return requested boundary
     */
    private int side(JsonNode anchor, int start, int end) {
        return anchor.path("side").asText().equals("leading") ? start : end;
    }

    /**
     * Decodes a previously validated UTF-8 comment token exactly.
     * @param token token with byte span
     * @param source exact base bytes
     * @return comment payload
     * @throws IllegalArgumentException for malformed stored boundaries or bytes
     */
    private String payload(JsonNode token, byte[] source) {
        int start = token.path("startByte").asInt(-1);
        int end = token.path("endByte").asInt(-1);
        if (start < 0 || end < start || end > source.length) throw new IllegalArgumentException("comment boundaries");
        try {
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(source, start, end - start)).toString();
        } catch (CharacterCodingException error) {
            throw new IllegalArgumentException("comment encoding", error);
        }
    }

    /**
     * Produces final source, fresh trivia and shifted expression spans.
     * @return projection data
     * @throws IllegalArgumentException when final source exceeds its bound
     */
    private ObjectNode assemble() {
        StringBuilder source = new StringBuilder();
        ArrayNode tokens = JsonNodeFactory.instance.arrayNode();
        int cursor = 0;
        int bytes = 0;
        for (Placement p : placements) {
            String segment = printed.substring(cursor, p.position());
            source.append(segment).append('\n');
            bytes += byteLength(segment) + 1;
            int start = bytes;
            source.append(p.payload()).append('\n');
            bytes += byteLength(p.payload());
            int end = bytes++;
            token(tokens, p, start, end);
            cursor = p.position();
        }
        String tail = printed.substring(cursor);
        source.append(tail);
        bytes += byteLength(tail);
        if (bytes > 32768) throw new IllegalArgumentException("source limit");
        ObjectNode result = JsonNodeFactory.instance.objectNode();
        result.put("source", source.toString());
        result.set("trivia", tokens);
        result.set("occurrences", shifted());
        result.put("orphaned", orphaned);
        return result;
    }

    /**
     * Creates a fresh source-bound comment record.
     * @param tokens output token array
     * @param placement scheduled comment
     * @param start UTF-8 start
     * @param end UTF-8 end
     */
    private void token(ArrayNode tokens, Placement placement, int start, int end) {
        ObjectNode item = tokens.addObject();
        item.put("commentId", "server:" + UUID.randomUUID());
        item.put("startByte", start);
        item.put("endByte", end);
        item.put("order", tokens.size() - 1);
        item.set("anchor", placement.anchor().deepCopy());
    }

    /**
     * Adjusts all original expression spans for inserted comment text.
     * @return fresh occurrence array
     */
    private ArrayNode shifted() {
        ArrayNode result = occurrences.deepCopy();
        for (JsonNode node : result) {
            ObjectNode span = (ObjectNode) node;
            int start = span.path("startUtf16").intValue();
            int end = span.path("endUtf16").intValue();
            span.put("startUtf16", shiftedOffset(start, true));
            span.put("endUtf16", shiftedOffset(end, false));
        }
        return result;
    }

    /**
     * Adjusts one source boundary for inserted text.
     * @param original original UTF-16 boundary
     * @param includeEqual whether insertions exactly here precede this boundary
     * @return new UTF-16 boundary
     */
    private int shiftedOffset(int original, boolean includeEqual) {
        int result = original;
        for (Placement p : placements) {
            if (p.position() < original || (includeEqual && p.position() == original)) result += p.payload().length() + 2;
        }
        return result;
    }

    /**
     * Counts UTF-8 bytes in valid generated text.
     * @param text valid text
     * @return byte count
     */
    private int byteLength(String text) {
        return text.getBytes(StandardCharsets.UTF_8).length;
    }

    /** One bounded immutable comment placement. */
    private record Placement(int position, int order, int copyOrder, String payload, ObjectNode anchor) {}
}
