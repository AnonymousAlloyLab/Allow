package dev.allow.document;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Extracts exact comment tokens for the no-IR TEXT_ONLY presentation. */
final class TextTriviaScanner {
    private final String source;
    private final Utf8Offsets offsets;
    private final List<int[]> comments = new ArrayList<>();
    private int firstCode = -1;

    /**
     * Creates a scanner for source already checked for Unicode and length.
     * @param source exact decoded source
     */
    TextTriviaScanner(String source) {
        this.source = source;
        this.offsets = new Utf8Offsets(source);
    }

    /**
     * Returns immutable-by-ownership token data for this source.
     * @return comment token array
     */
    ArrayNode scan() {
        int cursor = 0;
        while (cursor < source.length()) {
            if (Character.isWhitespace(source.charAt(cursor))) cursor++;
            else if (lineComment(cursor)) cursor = lineEnd(cursor);
            else if (source.startsWith("/*", cursor)) cursor = blockEnd(cursor);
            else {
                if (firstCode < 0) firstCode = cursor;
                cursor = source.charAt(cursor) == '"' ? stringEnd(cursor) : cursor + 1;
            }
        }
        return tokens();
    }

    /**
     * Determines whether an offset begins a line comment.
     * @param cursor UTF-16 position
     * @return true for either Alloy line-comment prefix
     */
    private boolean lineComment(int cursor) {
        return source.startsWith("//", cursor) || source.startsWith("--", cursor);
    }

    /**
     * Consumes a line comment without its line terminator.
     * @param start UTF-16 position
     * @return first position after comment
     */
    private int lineEnd(int start) {
        int end = start + 2;
        while (end < source.length() && source.charAt(end) != '\r' && source.charAt(end) != '\n') end++;
        comments.add(new int[]{start, end});
        return end;
    }

    /**
     * Consumes a block comment.
     * @param start UTF-16 position
     * @return first position after closing delimiter
     * @throws IllegalArgumentException when unclosed
     */
    private int blockEnd(int start) {
        int end = source.indexOf("*/", start + 2);
        if (end < 0) throw new IllegalArgumentException("unterminated comment");
        comments.add(new int[]{start, end + 2});
        return end + 2;
    }

    /**
     * Consumes an escaped quoted string without treating its contents as comments.
     * @param start opening quote
     * @return first position after close
     * @throws IllegalArgumentException when unclosed
     */
    private int stringEnd(int start) {
        int index = start + 1;
        while (index < source.length()) {
            char value = source.charAt(index++);
            if (value == '\\' && index < source.length()) index++;
            else if (value == '"') return index;
        }
        throw new IllegalArgumentException("unterminated string");
    }

    /**
     * Builds source-bound token records.
     * @return ordered comment records
     */
    private ArrayNode tokens() {
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        for (int index = 0; index < comments.size(); index++) {
            int[] span = comments.get(index);
            ObjectNode item = result.addObject();
            item.put("commentId", "server:" + UUID.randomUUID());
            item.put("startByte", bytesBefore(span[0]));
            item.put("endByte", bytesBefore(span[1]));
            item.put("order", index);
            item.putObject("anchor").put("kind", firstCode < 0 || span[0] < firstCode ? "module-leading" : "module-trailing");
        }
        return result;
    }

    /**
     * Converts a valid scalar boundary to its exact UTF-8 byte offset.
     * @param utf16 UTF-16 code-unit index
     * @return UTF-8 prefix length
     */
    private int bytesBefore(int utf16) {
        return offsets.at(utf16);
    }
}
