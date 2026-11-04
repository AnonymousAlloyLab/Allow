package dev.allow.document;

import java.util.ArrayList;
import java.util.List;

/** Bounded exact-source lexical tokenization for presentation correspondence. */
final class SourceLexer {
    private final String source;
    private final List<Token> tokens = new ArrayList<>();
    private int cursor;

    /**
     * Creates a lexer over already Unicode-validated bounded source.
     * @param source exact source without newline normalization
     */
    SourceLexer(String source) {
        this.source = source;
    }

    /**
     * Reads all non-whitespace tokens and comments in source order.
     * @return immutable token list
     */
    List<Token> read() {
        while (cursor < source.length()) next();
        return List.copyOf(tokens);
    }

    /** Consumes a token or whitespace from the source. */
    private void next() {
        if (Character.isWhitespace(source.charAt(cursor))) { cursor++; return; }
        int start = cursor;
        if (source.startsWith("//", cursor) || source.startsWith("--", cursor)) lineComment();
        else if (source.startsWith("/*", cursor)) blockComment();
        else if (source.charAt(cursor) == '"') quoted();
        else if (identifier(source.codePointAt(cursor))) word();
        else symbol();
        boolean comment = source.startsWith("//", start) || source.startsWith("--", start) || source.startsWith("/*", start);
        tokens.add(new Token(source.substring(start, cursor), start, cursor, comment));
    }

    /** Consumes a line comment without its line break. */
    private void lineComment() {
        cursor += 2;
        while (cursor < source.length() && source.charAt(cursor) != '\n' && source.charAt(cursor) != '\r') cursor++;
    }

    /**
     * Consumes a complete block comment.
     * @throws IllegalArgumentException if unterminated
     */
    private void blockComment() {
        int end = source.indexOf("*/", cursor + 2);
        if (end < 0) throw new IllegalArgumentException("unclosed comment");
        cursor = end + 2;
    }

    /**
     * Consumes an escaped string as one token.
     * @throws IllegalArgumentException if unterminated
     */
    private void quoted() {
        cursor++;
        while (cursor < source.length()) {
            char c = source.charAt(cursor++);
            if (c == '\\' && cursor < source.length()) cursor++;
            else if (c == '"') return;
        }
        throw new IllegalArgumentException("unclosed string");
    }

    /** Consumes a Unicode identifier or numeric token. */
    private void word() {
        while (cursor < source.length() && identifier(source.codePointAt(cursor))) {
            cursor += Character.charCount(source.codePointAt(cursor));
        }
    }

    /** Consumes a punctuation or multi-character Alloy operator. */
    private void symbol() {
        for (String operator : List.of("<=>", "=>", "->", "<:", ":>", "!=", "<=", ">=", "++", "&&", "||", "<<", ">>")) {
            if (source.startsWith(operator, cursor)) { cursor += operator.length(); return; }
        }
        cursor++;
    }

    /**
     * Tests whether a scalar may continue an Alloy identifier.
     * @param codePoint Unicode scalar
     * @return whether it belongs to a word token
     */
    private boolean identifier(int codePoint) {
        return Character.isJavaIdentifierPart(codePoint) || codePoint == '\'';
    }

    /** One exact token interval in UTF-16 units. */
    record Token(String text, int start, int end, boolean comment) {}
}
