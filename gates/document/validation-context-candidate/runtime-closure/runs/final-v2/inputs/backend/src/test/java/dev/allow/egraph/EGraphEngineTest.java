package dev.allow.egraph;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** Nontrivial engine and independent replay adversaries.
     */
final class EGraphEngineTest {
    private final Sort bool = Sort.bool();
    private final Term p = Term.atom(bool, "[\"ref\",\"sig\",0]");
    private final Term q = Term.atom(bool, "[\"ref\",\"sig\",1]");
    /** Builds sorted context around a finite root.
     * @param root typed expression
     * @param atoms opaque inventory
     * @return trusted input
     */
    private EngineInput input(Term root, Term... atoms) {
        List<Term> inventory = new ArrayList<>(List.of(atoms)); inventory.sort(Comparator.comparing(Context::atomKey));
        return new EngineInput(new Context("[\"module\",1]", List.of(0), inventory), root);
    }
    /** Constructs a Boolean operator.
     * @param op closed operator
     * @param children operands
     * @return typed term
     */
    private Term node(String op, Term... children) { return Term.node(op, bool, List.of(children)); }
    /** Uses a generous deterministic-test deadline.
     * @return absolute monotonic deadline
     */
    private long deadline() { return System.nanoTime() + 5_000_000_000L; }
    /** Absorption exercises repeated-variable matching and finite extraction.
     */
    @Test void absorptionIsCheckedAndDeterministic() {
        EngineInput input = input(node("AND", p, node("OR", p, q)), p, q);
        EGraphEngine engine = new EGraphEngine();
        IslandResult first = engine.analyze(input, deadline()), second = engine.analyze(input, deadline());
        assertEquals("CHECKED", first.certificateStatus()); assertEquals(p, first.extracted());
        assertEquals(first.extracted(), second.extracted()); assertEquals(first.stats(), second.stats());
        assertTrue(new ProofChecker(new RuleCatalog()).check(first.certificate(), input));
        assertTrue(first.stats().get("unions") > 0);
    }
    /** Cyclic classes have finite witnesses and preserve parent congruence.
     */
    @Test void cyclicClassesAndMultilevelCongruence() {
        RuleCatalog catalog = new RuleCatalog(); EngineInput input = input(node("AND", p, p), p);
        ProofStore proofs = new ProofStore(new ProofChecker(catalog), input.context());
        EGraph graph = new EGraph(proofs, new RunBudget(deadline()));
        int a = graph.add(p), b = graph.add(input.root());
        int parentA = graph.add(node("NOT", node("NOT", p)));
        int parentB = graph.add(node("NOT", node("NOT", input.root())));
        int rule = proofs.append("RULE", input.root(), p, List.of(), "B_AND_IDEM", Map.of("p", p));
        graph.merge(b, a, rule); graph.rebuild();
        assertEquals(graph.find(parentA), graph.find(parentB));
        assertEquals(p, Extractor.extract(graph, b, new RunBudget(deadline())));
        ProofStep justification = proofs.get(graph.equality(parentA, parentB));
        assertEquals(graph.node(parentA), justification.left()); assertEquals(graph.node(parentB), justification.right());
    }
    /** Separate schemas reject even when arities agree.
     */
    @Test void schemasAndOperatorFamiliesStayDistinct() {
        Sort left = Sort.relation(List.of(List.of("sig:0"))), right = Sort.relation(List.of(List.of("sig:1")));
        Term a = Term.atom(left, "[\"ref\",\"sig\",0]"), b = Term.atom(right, "[\"ref\",\"sig\",1]");
        EngineInput input = input(Term.node("UNION", left, List.of(a, b)), a, b);
        assertEquals("UNAVAILABLE", new EGraphEngine().analyze(input, deadline()).certificateStatus());
        assertThrows(IllegalArgumentException.class, EGraphEngineTest::badSchema);
        assertEquals("UNAVAILABLE", new EGraphEngine().analyze(input(node("IPLUS", p, p), p), deadline()).certificateStatus());
    }
    /** Constructs a forbidden presentation-based schema.
     */
    private static void badSchema() { Sort.relation(List.of(List.of("HumanName"))); }
    /** Relation rewriting propagates through SOME into Boolean parents.
     */
    @Test void mixedRelationBridge() {
        Sort sort = Sort.relation(List.of(List.of("sig:0")));
        Term a = Term.atom(sort, "[\"ref\",\"sig\",0]");
        Term repeated = Term.node("INTER", sort, List.of(a, a));
        EngineInput input = input(node("SOME", repeated), a);
        IslandResult result = new EGraphEngine().analyze(input, deadline());
        assertEquals("CHECKED", result.certificateStatus()); assertEquals(node("SOME", a), result.extracted());
    }
    /** Unknown rules, changed substitutions and forward premises fail replay.
     */
    @Test void replayRejectsLocalForgeries() {
        EngineInput input = input(node("AND", p, p), p);
        ProofStep valid = new ProofStep("RULE", input.root(), p, List.of(), "B_AND_IDEM", Map.of("p", p));
        assertTrue(check(input, p, List.of(valid), 0));
        assertFalse(check(input, p, List.of(new ProofStep("RULE", input.root(), p, List.of(), "FORGED_UF", Map.of("p", p))), 0));
        assertFalse(check(input, p, List.of(new ProofStep("RULE", input.root(), p, List.of(), "B_AND_IDEM", Map.of("p", q))), 0));
        assertFalse(check(input, p, List.of(new ProofStep("TRANS", input.root(), p, List.of(0, 0), "", Map.of())), 0));
        assertFalse(check(input, p, List.of(new ProofStep("REFL", input.root(), p, List.of(), "", Map.of())), 0));
    }
    /** Wrong inventories and unrelated conclusions fail root binding.
     */
    @Test void replayRejectsContextAndConclusionTampering() {
        EngineInput input = input(p, p, q);
        ProofStep unrelated = new ProofStep("REFL", q, q, List.of(), "", Map.of());
        assertFalse(check(input, p, List.of(unrelated), 0));
        Certificate certificate = new Certificate("allow-egraph-proof-v1", input(p, p).context(), new RuleCatalog().digest(),
                p, p, List.of(new ProofStep("REFL", p, p, List.of(), "", Map.of())), 0);
        assertFalse(new ProofChecker(new RuleCatalog()).check(certificate, input));
        assertFalse(check(input(p, p), q, List.of(new ProofStep("REFL", q, q, List.of(), "", Map.of())), 0));
    }
    /** Deadlines retain honest incomplete state.
     */
    @Test void expiredDeadlineCannotClaimSaturation() {
        IslandResult result = new EGraphEngine().analyze(input(p, p), System.nanoTime() - 1);
        assertEquals("TIME_LIMIT", result.stopReason()); assertNotEquals("SATURATED", result.stopReason());
    }
    /** Deep proof chains and deep term trees reject before recursive serialization.
     */
    @Test void rejectsExcessiveProofAndTermDepth() {
        EngineInput input = input(p, p); List<ProofStep> steps = new ArrayList<>();
        steps.add(new ProofStep("REFL", p, p, List.of(), "", Map.of()));
        for (int i = 1; i < 130; i++) steps.add(new ProofStep("SYMM", p, p, List.of(i - 1), "", Map.of()));
        assertFalse(check(input, p, steps, 129));
        Term deep = p; for (int i = 0; i < 10000; i++) deep = node("NOT", deep);
        assertFalse(check(input, deep, List.of(new ProofStep("REFL", deep, deep, List.of(), "", Map.of())), 0));
    }
    /** Capped counting rejects repeated large atoms without building a huge JSON string.
     */
    @Test void cappedCertificateSizing() {
        Term large = Term.atom(bool, "x".repeat(100000)); EngineInput input = input(node("AND", large, large), large);
        ProofStep refl = new ProofStep("REFL", input.root(), input.root(), List.of(), "", Map.of());
        assertFalse(check(input, input.root(), List.of(refl), 0));
        assertEquals(262145, Wire.size(new Certificate("allow-egraph-proof-v1", input.context(), new RuleCatalog().digest(),
                input.root(), input.root(), List.of(refl), 0)));
    }
    /** Replays a synthetic certificate.
     * @param input trusted root
     * @param output proposed root
     * @param steps proof data
     * @param conclusion final index
     * @return replay result
     */
    private boolean check(EngineInput input, Term output, List<ProofStep> steps, int conclusion) {
        RuleCatalog catalog = new RuleCatalog();
        return new ProofChecker(catalog).check(new Certificate("allow-egraph-proof-v1", input.context(), catalog.digest(),
                input.root(), output, steps, conclusion), input);
    }
}
