package dev.allow.worker;

import java.nio.charset.StandardCharsets;

/** Import-free lexical preflight before any Alloy resolver is invoked. */
public final class SourcePolicy {
    /** Prevents construction of the stateless guard. */
    private SourcePolicy() {}

    /**
     * Validates size/Unicode and forbids real open tokens.
     * @param source exact draft
     * @throws IllegalArgumentException rejected source
     */
    public static void check(String source) {
        if (source == null || source.getBytes(StandardCharsets.UTF_8).length > 32768) {
            throw new IllegalArgumentException("Source must be at most 32768 UTF-8 bytes.");
        }
        unicode(source);
        int cursor = 0;
        while (cursor < source.length()) {
            int skipped = skip(source, cursor);
            if (skipped != cursor) {
                cursor = skipped;
            } else if (Character.isJavaIdentifierPart(source.charAt(cursor))) {
                int start = cursor++;
                while (cursor < source.length()
                        && Character.isJavaIdentifierPart(source.charAt(cursor))) cursor++;
                if (source.substring(start, cursor).equals("open")) {
                    throw new IllegalArgumentException("Imports are unsupported in this local slice.");
                }
            } else {
                cursor++;
            }
        }
    }

    /**
     * Rejects invalid Unicode rather than hashing replacement bytes.
     * @param source exact text
     * @throws IllegalArgumentException invalid surrogate sequence
     */
    private static void unicode(String source) {
        for (int index = 0; index < source.length(); index++) {
            char value = source.charAt(index);
            if (Character.isHighSurrogate(value)) {
                if (++index >= source.length() || !Character.isLowSurrogate(source.charAt(index))) {
                    throw new IllegalArgumentException("Invalid Unicode source.");
                }
            } else if (Character.isLowSurrogate(value)) {
                throw new IllegalArgumentException("Invalid Unicode source.");
            }
        }
    }

    /**
     * Skips comments or strings without interpreting their contents.
     * @param text source
     * @param start position
     * @return next position or start
     */
    private static int skip(String text, int start) {
        if (text.startsWith("//", start) || text.startsWith("--", start)) {
            return lineEnd(text, start + 2);
        }
        if (text.startsWith("/*", start)) {
            int end = text.indexOf("*/", start + 2);
            return end < 0 ? text.length() : end + 2;
        }
        return text.charAt(start) == '"' ? stringEnd(text, start + 1) : start;
    }

    /**
     * Skips through a CR, LF or CRLF line-comment terminator.
     * @param text exact source
     * @param index first comment-content position
     * @return position after the terminator, or the source end
     */
    private static int lineEnd(String text, int index) {
        while (index < text.length() && text.charAt(index) != '\r' && text.charAt(index) != '\n') index++;
        if (index < text.length() && text.charAt(index++) == '\r'
                && index < text.length() && text.charAt(index) == '\n') index++;
        return index;
    }

    /**
     * Skips one escaped quoted string.
     * @param text source
     * @param index first content unit
     * @return position after close
     */
    private static int stringEnd(String text, int index) {
        while (index < text.length()) {
            char value = text.charAt(index++);
            if (value == '\\') index++;
            else if (value == '"') return index;
        }
        return text.length();
    }
}
