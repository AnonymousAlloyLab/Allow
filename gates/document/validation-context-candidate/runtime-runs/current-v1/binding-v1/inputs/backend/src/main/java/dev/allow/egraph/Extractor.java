package dev.allow.egraph;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
/** Positive-cost fixed-point extraction yielding only finite acyclic term witnesses.
     */
final class Extractor {
    /** Prevents utility construction.
     */
    private Extractor() { }
    /** Relaxes finite tree witnesses in cyclic classes.
     * @param graph bounded graph
     * @param root input identifier
     * @param budget shared resources
     * @return least witnessed tree by unit cost and exact JSON
     */
    static Term extract(EGraph graph, int root, RunBudget budget) {
        Map<Integer, Term> best = new HashMap<>(); boolean changed;
        do {
            changed = false;
            for (int id = 0; id < graph.size(); id++) {
                budget.tick(); Term candidate = candidate(graph, id, best);
                if (candidate == null || candidate.cost() > 2048) continue;
                int owner = graph.find(id); Term old = best.get(owner);
                if (old == null || better(candidate, old)) { best.put(owner, candidate); changed = true; }
            }
        } while (changed);
        return best.getOrDefault(graph.find(root), graph.node(root));
    }
    /** Constructs a finite node only when all children have finite witnesses.
     * @param graph graph state
     * @param id concrete node
     * @param best current class witnesses
     * @return candidate or absent
     */
    private static Term candidate(EGraph graph, int id, Map<Integer, Term> best) {
        List<Term> children = new ArrayList<>();
        for (int child : graph.children(id)) {
            Term term = best.get(graph.find(child)); if (term == null) return null; children.add(term);
        }
        Term original = graph.node(id); return new Term(original.op(), original.sort(), original.atom(), children);
    }
    /** Compares unit tree cost then anonymous serialization.
     * @param candidate proposed tree
     * @param old current tree
     * @return whether candidate wins
     */
    private static boolean better(Term candidate, Term old) {
        return candidate.cost() < old.cost() || candidate.cost() == old.cost() && Wire.json(candidate).compareTo(Wire.json(old)) < 0;
    }
}
