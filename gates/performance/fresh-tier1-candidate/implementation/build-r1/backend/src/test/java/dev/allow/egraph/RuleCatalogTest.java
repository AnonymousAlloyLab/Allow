package dev.allow.egraph;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** Independent finite pointwise checks of the exact loaded Java registry. */
final class RuleCatalogTest {
    /** Every catalog law holds for all Boolean or pointwise membership assignments. */
    @Test void everyRegisteredRuleHasFiniteSemanticParity() {
        RuleCatalog catalog = new RuleCatalog(); int cases = 0;
        for (RuleCatalog.Rewrite rule : catalog.rules()) {
            List<String> names = new ArrayList<>(RuleCatalog.variables(rule.left()).keySet());
            for (int assignment = 0; assignment < 1 << names.size(); assignment++) {
                Sort sort = rule.family().equals("BOOL") ? Sort.bool() : Sort.relation(List.of(List.of("sig:0")));
                Map<String, Term> substitution = new LinkedHashMap<>();
                Map<String, Boolean> valuation = new LinkedHashMap<>();
                for (int i = 0; i < names.size(); i++) {
                    substitution.put(names.get(i), Term.atom(sort, names.get(i)));
                    valuation.put(names.get(i), (assignment & 1 << i) != 0);
                }
                assertEquals(eval(RuleCatalog.instantiate(rule.left(), substitution, sort), valuation),
                        eval(RuleCatalog.instantiate(rule.right(), substitution, sort), valuation), rule.id());
                cases++;
            }
        }
        assertEquals(34, catalog.rules().size()); assertEquals(128, cases);
    }
    /** A same-sized replacement of the embedded registry fails before JSON parsing.
     * @throws Exception when the approved resource cannot be read
     */
    @Test void alteredRegistryCannotBecomeSelfApproved() throws Exception {
        byte[] bytes;
        try (var stream = RuleCatalog.class.getResourceAsStream("/profiles/egraph-rules.json")) {
            assertNotNull(stream);
            bytes = stream.readAllBytes();
        }
        bytes[0] = '!';
        IllegalStateException error = assertThrows(IllegalStateException.class, new RegistryAttempt(bytes)::load);
        assertEquals("Unapproved rule registry", error.getMessage());
    }
    /** Constructor-owned and accessor-returned JSON trees cannot mutate a rewrite. */
    @Test void rewriteDefensivelyCopiesBothPatternBoundaries() {
        var mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        var left = mapper.createArrayNode().add("AND").add("p").add("p");
        var right = mapper.createArrayNode().add("NOT").add("p");
        RuleCatalog.Rewrite rewrite = new RuleCatalog.Rewrite("fixture", "BOOL", left, right);
        left.set(0, mapper.getNodeFactory().textNode("OR"));
        right.set(0, mapper.getNodeFactory().textNode("AND"));
        assertEquals("AND", rewrite.left().get(0).asText());
        assertEquals("NOT", rewrite.right().get(0).asText());
        ((com.fasterxml.jackson.databind.node.ArrayNode) rewrite.left()).removeAll();
        ((com.fasterxml.jackson.databind.node.ArrayNode) rewrite.right()).removeAll();
        assertEquals(3, rewrite.left().size());
        assertEquals(2, rewrite.right().size());
    }
    /** Package-private registry rejection action.
     * @param bytes deliberately altered catalog
     */
    private record RegistryAttempt(byte[] bytes) {
        /** Attempts to admit unapproved bytes through the package test seam. */
        void load() { new RuleCatalog(bytes); }
    }
    /** Evaluates one Boolean or pointwise relation term independently of matcher/checker.
     * @param term registered ground instance
     * @param valuation atom interpretation
     * @return Boolean value or tuple membership
     * @throws IllegalArgumentException when the catalog contains an unsupported operator
     */
    private boolean eval(Term term, Map<String, Boolean> valuation) {
        List<Term> children = term.children();
        return switch (term.op()) {
            case "ATOM" -> valuation.get(term.atom());
            case "TRUE" -> true;
            case "FALSE", "EMPTY" -> false;
            case "NOT" -> !eval(children.get(0), valuation);
            case "AND", "INTER" -> eval(children.get(0), valuation) && eval(children.get(1), valuation);
            case "OR", "UNION" -> eval(children.get(0), valuation) || eval(children.get(1), valuation);
            case "DIFF" -> eval(children.get(0), valuation) && !eval(children.get(1), valuation);
            default -> throw new IllegalArgumentException("Unexpected registry operator");
        };
    }
}
