package dev.allow.document;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/** Conservatively screens exact source for the static closed syntax fragment. */
final class SourceFragmentGuard {
    private static final Set<String> EXCLUDED = Set.of("abstract", "as", "disj", "else", "enum", "exactly", "expect",
        "extends", "fun", "let", "module", "open", "private", "sum", "this", "var", "always", "eventually", "after",
        "before", "until", "releases", "historically", "once", "since", "triggered", "univ", "none", "iden");
    private static final Set<String> PUNCTUATION = Set.of("{", "}", "[", "]", "(", ")", ":", ",", "|", ".", "+", "-", "&", "->", "~", "=", "!", "=>", "<=>", "&&", "||");
    private final List<SourceLexer.Token> tokens = new ArrayList<>();

    /**
     * Creates a fragment guard for exact source.
     * @param source Unicode-validated source
     */
    SourceFragmentGuard(String source) {
        for (SourceLexer.Token token : new SourceLexer(source).read()) if (!token.comment()) tokens.add(token);
    }

    /**
     * Screens tokens before source elaboration and independent module checking.
     * @return whether every token belongs to the permitted closed syntax
     */
    boolean supports() {
        int braces = 0;
        for (int index = 0; index < tokens.size(); index++) {
            String value = tokens.get(index).text();
            if (value.equals("{")) braces++;
            if (value.equals("}")) braces--;
            if (EXCLUDED.contains(value) || !permitted(value, braces)) return false;
            if (braces == 0 && !topLevelForm(index, value)) return false;
        }
        return braces == 0;
    }

    /**
     * Rejects unknown punctuation and integer expressions.
     * @param value source token
     * @param braces current brace depth
     * @return whether the token may be part of this fragment
     */
    private boolean permitted(String value, int braces) {
        if (PUNCTUATION.contains(value)) return true;
        if (value.matches("[0-9]+")) return braces == 0;
        if (!value.matches("[A-Za-z][A-Za-z0-9_]{0,63}")) return false;
        return !value.startsWith("allow_");
    }

    /**
     * Rejects unsupported top-level shorthand before AST normalization.
     * @param index current token index
     * @param value token text
     * @return whether top-level declaration shape is allowed
     */
    private boolean topLevelForm(int index, String value) {
        if (value.equals("sig") || value.equals("fact") || value.equals("assert")) return namedThen(index, "{");
        if (value.equals("pred")) return namedThen(index, "{") || namedThen(index, "[");
        if (value.equals("run") || value.equals("check")) return hasName(index + 1);
        return true;
    }

    /**
     * Checks a declaration keyword, its single name and following delimiter.
     * @param index keyword index
     * @param delimiter allowed next delimiter
     * @return whether the next two tokens match
     */
    private boolean namedThen(int index, String delimiter) {
        return hasName(index + 1) && index + 2 < tokens.size() && tokens.get(index + 2).text().equals(delimiter);
    }

    /**
     * Checks the lexical shape of one declaration name.
     * @param index token index
     * @return whether it is a valid profile name
     */
    private boolean hasName(int index) {
        return index < tokens.size() && tokens.get(index).text().matches("[A-Za-z][A-Za-z0-9_]{0,63}");
    }
}
