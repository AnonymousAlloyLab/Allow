package dev.allow.document;

/** Counts explicit top-level run/check tokens in already parsed exact source. */
final class CommandTokenCounter {
    private final String source;
    private int cursor;
    private int nesting;
    private int count;
    private boolean domainRestriction;

    /**
     * Creates a counter for the exact parsed source.
     * @param source source text
     */
    CommandTokenCounter(String source) {
        this.source = source;
    }

    /**
     * Counts authored command keywords without strings or comments.
     * @return number of top-level commands
     */
    int count() {
        while (cursor < source.length()) advance();
        return count;
    }

    /**
     * Reports whether the scan saw an authored domain restriction operator.
     * @return true if exact source contains a domain restriction token
     */
    boolean hasDomainRestriction() {
        return domainRestriction;
    }

    /** Consumes one token, comment, quoted literal or delimiter. */
    private void advance() {
        if (source.startsWith("//", cursor) || source.startsWith("--", cursor)) line();
        else if (source.startsWith("/*", cursor)) block();
        else if (source.charAt(cursor) == '"') quoted();
        else if (identifier(source.codePointAt(cursor))) word();
        else delimiter();
    }

    /** Consumes a line comment. */
    private void line() {
        cursor += 2;
        while (cursor < source.length() && source.charAt(cursor) != '\n' && source.charAt(cursor) != '\r') cursor++;
    }

    /**
     * Consumes a block comment.
     * @throws IllegalArgumentException if unclosed
     */
    private void block() {
        int end = source.indexOf("*/", cursor + 2);
        if (end < 0) throw new IllegalArgumentException("unclosed comment");
        cursor = end + 2;
    }

    /**
     * Consumes a quoted string and its escapes.
     * @throws IllegalArgumentException if unclosed
     */
    private void quoted() {
        cursor++;
        while (cursor < source.length()) {
            if (source.startsWith("<:", cursor)) domainRestriction = true;
        char value = source.charAt(cursor++);
            if (value == '\\' && cursor < source.length()) cursor++;
            else if (value == '"') return;
        }
        throw new IllegalArgumentException("unclosed string");
    }

    /** Consumes an identifier and recognizes unqualified top-level command tokens. */
    private void word() {
        int start = cursor;
        while (cursor < source.length() && identifier(source.codePointAt(cursor))) {
            cursor += Character.charCount(source.codePointAt(cursor));
        }
        String value = source.substring(start, cursor);
        if (nesting == 0 && (start == 0 || source.charAt(start - 1) != '/')
                && (value.equals("run") || value.equals("check"))) count++;
    }

    /** Tracks structural nesting for command keywords. */
    private void delimiter() {
        if (source.startsWith("<:", cursor)) domainRestriction = true;
        char value = source.charAt(cursor++);
        if (value == '{' || value == '(' || value == '[') nesting++;
        else if (value == '}' || value == ')' || value == ']') nesting--;
    }

    /**
     * Tests identifier characters conservatively.
     * @param value Unicode code point
     * @return whether the character continues an identifier
     */
    private boolean identifier(int value) {
        return Character.isJavaIdentifierPart(value) || value == '\'';
    }
}
