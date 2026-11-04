package dev.allow.canonical;

import java.util.Set;

/** Frozen Alloy operator allowlists from spec/slot-profile.json; no source-derived tags. */
final class OperatorPolicy {
    private static final Set<String> UNARY = Set.of(
        "SOMEOF", "LONEOF", "ONEOF", "SETOF",
        "EXACTLYOF", "NOT", "NO", "SOME",
        "LONE", "ONE", "TRANSPOSE", "RCLOSURE",
        "CLOSURE", "CARDINALITY", "CAST2INT", "CAST2SIGINT",
        "NOOP");
    private static final Set<String> BINARY = Set.of(
        "ARROW", "ANY_ARROW_SOME", "ANY_ARROW_ONE", "ANY_ARROW_LONE",
        "SOME_ARROW_ANY", "SOME_ARROW_SOME", "SOME_ARROW_ONE", "SOME_ARROW_LONE",
        "ONE_ARROW_ANY", "ONE_ARROW_SOME", "ONE_ARROW_ONE", "ONE_ARROW_LONE",
        "LONE_ARROW_ANY", "LONE_ARROW_SOME", "LONE_ARROW_ONE", "LONE_ARROW_LONE",
        "ISSEQ_ARROW_LONE", "JOIN", "DOMAIN", "RANGE",
        "INTERSECT", "PLUSPLUS", "PLUS", "IPLUS",
        "MINUS", "IMINUS", "MUL", "DIV",
        "REM", "EQUALS", "NOT_EQUALS", "IMPLIES",
        "LT", "LTE", "GT", "GTE",
        "NOT_LT", "NOT_LTE", "NOT_GT", "NOT_GTE",
        "SHL", "SHA", "SHR", "IN",
        "NOT_IN", "AND", "OR", "IFF");
    private static final Set<String> LIST = Set.of(
        "AND", "OR", "DISJOINT");
    private static final Set<String> QUANTIFIER = Set.of(
        "ALL", "NO", "LONE", "ONE",
        "SOME", "SUM", "COMPREHENSION");
    private static final Set<String> CONSTANT = Set.of(
        "TRUE", "FALSE", "IDEN", "MIN",
        "MAX", "NEXT", "EMPTYNESS");

    /** Prevents construction of the closed operator policy. */
    private OperatorPolicy() { }

    /** Checks a trusted parser enum against its frozen constructor family.
     * @param family structural node family
     * @param operator parser enum name, never expression text
     * @return validated enum name
     * @throws UnsupportedCanonical if an operator is outside this static profile
     */
    static String checked(String family, String operator) {
        Set<String> allowed = switch (family) {
            case "unary" -> UNARY;
            case "binary" -> BINARY;
            case "list" -> LIST;
            case "quantifier" -> QUANTIFIER;
            case "constant" -> CONSTANT;
            default -> throw new UnsupportedCanonical();
        };
        if (!allowed.contains(operator)) { throw new UnsupportedCanonical(); }
        return operator;
    }
}
