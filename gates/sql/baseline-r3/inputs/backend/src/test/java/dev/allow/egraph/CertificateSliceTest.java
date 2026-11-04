package dev.allow.egraph;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** Export slicing preserves the exact derivation while discarding unrelated graph history. */
final class CertificateSliceTest {
    /** Unused steps disappear while congruence/transitivity dependencies retain valid new indices. */
    @Test void keepsAndReindexesOnlyReachableDerivation() {
        Term p = Term.atom(Sort.bool(), "[0]"), repeated = and(p, p), input = and(repeated, p);
        Context context = new Context("[\"module\",1]", List.of(0), List.of(p));
        List<ProofStep> history = List.of(
                new ProofStep("REFL", input, input, List.of(), "", Map.of()),
                new ProofStep("RULE", repeated, p, List.of(), "B_AND_IDEM", Map.of("p", p)),
                new ProofStep("REFL", repeated, repeated, List.of(), "", Map.of()),
                new ProofStep("REFL", p, p, List.of(), "", Map.of()),
                new ProofStep("CONGRUENCE", input, repeated, List.of(1, 3), "", Map.of()),
                new ProofStep("TRANS", input, p, List.of(4, 1), "", Map.of()),
                new ProofStep("REFL", p, p, List.of(), "", Map.of()));
        RuleCatalog catalog = new RuleCatalog();
        Certificate original = new Certificate("allow-egraph-proof-v1", context, catalog.digest(), input, p, history, 5);
        Certificate compact = CertificateSlice.compact(original);
        assertEquals(7, original.steps().size()); assertEquals(4, compact.steps().size());
        assertEquals(3, compact.conclusion());
        assertEquals(List.of(0, 1), compact.steps().get(2).premises());
        assertEquals(List.of(2, 0), compact.steps().get(3).premises());
        assertEquals("B_AND_IDEM", compact.steps().get(0).rule());
        assertTrue(new ProofChecker(catalog).check(compact, new EngineInput(context, input)));
        assertTrue(Wire.size(compact) < Wire.size(original));
    }
    /** Constructs a typed conjunction for proof endpoints.
     * @param left first operand
     * @param right second operand
     * @return immutable Boolean term
     */
    private static Term and(Term left, Term right) { return Term.node("AND", Sort.bool(), List.of(left, right)); }
}
