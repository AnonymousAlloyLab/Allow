package dev.allow.egraph;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** Mechanical invariants beyond semantic rule fixtures. */
final class EGraphMechanicsTest {
    /** Constructs a sorted atom context.
     * @param atoms opaque authority
     * @return immutable context
     */
    private Context context(List<Term> atoms) {
        List<Term> sorted = new ArrayList<>(atoms);
        sorted.sort(Comparator.comparing(Context::atomKey));
        return new Context("[\"module\",1]", List.of(0), sorted);
    }
    /** Constructs a Boolean operator.
     * @param op closed operator
     * @param children ordered arguments
     * @return typed ground term
     */
    private Term node(String op, Term... children) { return Term.node(op, Sort.bool(), List.of(children)); }
    /** Repeated variables match equivalent classes rather than differing syntax. */
    @Test void repeatedVariableRequiresClassEquality() {
        Term p = Term.atom(Sort.bool(), "[0]"), pp = node("AND", p, p);
        RuleCatalog catalog = new RuleCatalog();
        RunBudget budget = new RunBudget(Long.MAX_VALUE);
        ProofStore proofs = new ProofStore(new ProofChecker(catalog), context(List.of(p)));
        EGraph graph = new EGraph(proofs, budget);
        int pId = graph.add(p), ppId = graph.add(pp), target = graph.add(node("OR", p, pp));
        var pattern = catalog.rule("B_OR_IDEM").left();
        assertTrue(new Matcher(graph, budget).match(pattern, target, Map.of()).isEmpty());
        int rule = proofs.append("RULE", pp, p, List.of(), "B_AND_IDEM", Map.of("p", p));
        graph.merge(ppId, pId, rule);
        graph.rebuild();
        assertFalse(new Matcher(graph, budget).match(pattern, target, Map.of()).isEmpty());
    }
    /** Failed proof admission cannot perform a semantic union. */
    @Test void failedProofNeverMutatesUnionFind() {
        Term p = Term.atom(Sort.bool(), "[0]"), q = Term.atom(Sort.bool(), "[1]");
        RuleCatalog catalog = new RuleCatalog();
        ProofStore proofs = new ProofStore(new ProofChecker(catalog), context(List.of(p, q)));
        EGraph graph = new EGraph(proofs, new RunBudget(Long.MAX_VALUE));
        int a = graph.add(p), b = graph.add(q);
        assertThrows(IllegalArgumentException.class, new InvalidEdge(proofs, p, q)::append);
        assertNotEquals(graph.find(a), graph.find(b));
    }
    /** Node exhaustion during initial admission stays distinct from saturation. */
    @Test void nodeAdmissionLimitIsHonest() {
        List<Term> atoms = new ArrayList<>();
        for (int i = 0; i < 300; i++) atoms.add(Term.atom(Sort.bool(), "[" + i + "]"));
        Term root = balanced(atoms);
        IslandResult result = new EGraphEngine().analyze(new EngineInput(context(atoms), root), Long.MAX_VALUE);
        assertEquals("NODE_LIMIT", result.stopReason());
        assertNotEquals("SATURATED", result.stopReason());
    }
    /** Complete match enumeration can exhaust its independent counter. */
    @Test void matcherLimitIsHonest() {
        List<Term> atoms = new ArrayList<>();
        for (int i = 0; i < 120; i++) atoms.add(Term.atom(Sort.bool(), "[" + i + "]"));
        IslandResult result = new EGraphEngine().analyze(new EngineInput(context(atoms), balanced(atoms)), Long.MAX_VALUE);
        assertEquals("MATCH_LIMIT", result.stopReason());
    }
    /** Oversized finite input reports its own admission limit. */
    @Test void inputOccurrenceLimitIsHonest() {
        List<Term> atoms = new ArrayList<>();
        for (int i = 0; i < 1030; i++) atoms.add(Term.atom(Sort.bool(), "[" + i + "]"));
        IslandResult result = new EGraphEngine().analyze(new EngineInput(context(atoms), balanced(atoms)), Long.MAX_VALUE);
        assertEquals("INPUT_LIMIT", result.stopReason());
        assertEquals("UNAVAILABLE", result.certificateStatus());
    }
    /** Proof-byte admission rejects before leaving a new derivation in the store. */
    @Test void proofBudgetStopsBeforeAppend() {
        Term p = Term.atom(Sort.bool(), "[0]");
        ProofStore proofs = new ProofStore(new ProofChecker(new RuleCatalog()), context(List.of(p)));
        RunBudget.Limit limit = assertThrows(RunBudget.Limit.class, new ExhaustProof(proofs, p)::run);
        assertEquals("PROOF_LIMIT", limit.getMessage());
        assertTrue(proofs.steps().size() < 4096);
    }
    /** Resource-exhaustion action without anonymous callbacks.
     * @param proofs bounded proof store
     * @param term trusted atom
     */
    private record ExhaustProof(ProofStore proofs, Term term) {
        /** Appends independent reflexivity edges until the finite cap rejects. */
        void run() { for (int i = 0; i < 10000; i++) proofs.refl(term); }
    }
    /** Builds a shallow tree within the admitted depth bound.
     * @param terms finite leaves
     * @return balanced conjunction
     */
    private Term balanced(List<Term> terms) {
        if (terms.size() == 1) return terms.get(0);
        int half = terms.size() / 2;
        return node("AND", balanced(terms.subList(0, half)), balanced(terms.subList(half, terms.size())));
    }
    /** Invalid edge action for the exception assertion.
     * @param proofs checked store
     * @param p source atom
     * @param q unrelated target
     */
    private record InvalidEdge(ProofStore proofs, Term p, Term q) {
        /** Attempts a forged reflexivity edge. */
        void append() { proofs.append("REFL", p, q, List.of(), "", Map.of()); }
    }
}
