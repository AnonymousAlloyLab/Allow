package dev.allow.egraph;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
/** Actual hash-consed typed graph with checked union-find and congruence rebuilding.
     */
final class EGraph {
    private final List<Term> nodes = new ArrayList<>();
    private final List<List<Integer>> children = new ArrayList<>();
    private final List<Integer> parents = new ArrayList<>();
    private final List<List<Edge>> edges = new ArrayList<>();
    private final Map<Term, Integer> exact = new HashMap<>();
    private final Map<Key, Integer> hashcons = new LinkedHashMap<>();
    private final ProofStore proofs;
    private final RunBudget budget;
    private long rebuilds;
    /** Creates a context-confined graph.
     * @param proofs checked derivations
     * @param budget finite resources
     */
    EGraph(ProofStore proofs, RunBudget budget) { this.proofs = proofs; this.budget = budget; }
    /** Adds a finite ground term and justifies canonicalized collisions.
     * @param term concrete syntax
     * @return stable node identifier
     * @throws RunBudget.Limit when validation or resource checks reject the operation
     */
    int add(Term term) {
        budget.tick(); Integer known = exact.get(term); if (known != null) return known;
        List<Integer> operands = new ArrayList<>();
        for (Term child : term.children()) operands.add(add(child));
        if (nodes.size() >= 512) throw new RunBudget.Limit("NODE_LIMIT");
        int id = nodes.size(); nodes.add(term); children.add(List.copyOf(operands));
        parents.add(id); edges.add(new ArrayList<>()); exact.put(term, id);
        Key key = key(id); Integer owner = hashcons.putIfAbsent(key, id);
        if (owner != null && find(owner) != find(id)) merge(id, owner, congruence(id, owner));
        return id;
    }
    /** Finds a representative with path compression.
     * @param id stable node
     * @return current representative
     */
    int find(int id) {
        int root = id;
        while (parents.get(root) != root) root = parents.get(root);
        while (parents.get(id) != id) { int next = parents.get(id); parents.set(id, root); id = next; }
        return root;
    }
    /** Applies a previously checked concrete edge before mutation.
     * @param left stable endpoint
     * @param right stable endpoint
     * @param proof derivation index
     * @return whether classes changed
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    boolean merge(int left, int right, int proof) {
        if (find(left) == find(right)) return false;
        ProofStep edge = proofs.get(proof);
        if (!edge.left().equals(nodes.get(left)) || !edge.right().equals(nodes.get(right))
                || !nodes.get(left).sort().equals(nodes.get(right).sort())) throw new IllegalArgumentException("Merge endpoints");
        budget.union();
        int a = find(left), b = find(right); parents.set(Math.max(a, b), Math.min(a, b));
        edges.get(left).add(new Edge(right, proof, false)); edges.get(right).add(new Edge(left, proof, true));
        return true;
    }
    /** Rebuilds all congruence keys to a fixed point, including cycles.
     */
    void rebuild() {
        boolean changed;
        do {
            changed = false; hashcons.clear(); rebuilds++;
            for (int id = 0; id < nodes.size(); id++) {
                budget.tick(); Integer owner = hashcons.putIfAbsent(key(id), id);
                if (owner != null && find(owner) != find(id)) changed |= merge(id, owner, congruence(id, owner));
            }
        } while (changed);
    }
    /** Constructs checked child congruence.
     * @param left concrete node
     * @param right concrete node
     * @return proof index
     */
    private int congruence(int left, int right) {
        List<Integer> premises = new ArrayList<>();
        for (int i = 0; i < children.get(left).size(); i++) premises.add(equality(children.get(left).get(i), children.get(right).get(i)));
        return proofs.append("CONGRUENCE", nodes.get(left), nodes.get(right), premises, "", Map.of());
    }
    /** Reconstructs equality from a proof forest rather than trusting class membership.
     * @param left concrete endpoint
     * @param right concrete endpoint
     * @return checked proof
     */
    int equality(int left, int right) {
        if (left == right) return proofs.refl(nodes.get(left));
        Map<Integer, Path> seen = searchPath(left, right);
        List<Edge> path = new ArrayList<>();
        int current = right;
        while (current != left) {
            Path link = seen.get(current);
            path.add(link.edge());
            current = link.previous();
        }
        int result = -1;
        for (int i = path.size() - 1; i >= 0; i--) {
            Edge edge = path.get(i);
            int proof = edge.reverse() ? proofs.reverse(edge.proof()) : edge.proof();
            result = result < 0 ? proof : proofs.compose(result, proof);
        }
        return result;
    }
    /** Finds a concrete proof-forest path independently of union-find membership.
     * @param left concrete starting node
     * @param right concrete target node
     * @return breadth-first predecessor links
     * @throws IllegalArgumentException when no derivation path exists
     */
    private Map<Integer, Path> searchPath(int left, int right) {
        Map<Integer, Path> seen = new HashMap<>();
        ArrayDeque<Integer> queue = new ArrayDeque<>();
        seen.put(left, null);
        queue.add(left);
        while (!queue.isEmpty() && !seen.containsKey(right)) {
            budget.tick();
            int current = queue.remove();
            for (Edge edge : edges.get(current)) {
                if (!seen.containsKey(edge.target())) {
                    seen.put(edge.target(), new Path(current, edge));
                    queue.add(edge.target());
                }
            }
        }
        if (!seen.containsKey(right)) throw new IllegalArgumentException("No concrete justification");
        return seen;
    }
    /** Computes a structural canonical key.
     * @param id stable node
     * @return exact sorted congruence key
     */
    private Key key(int id) {
        List<Integer> operands = new ArrayList<>(); for (int child : children.get(id)) operands.add(find(child));
        Term term = nodes.get(id); return new Key(term.op(), term.sort(), term.atom(), List.copyOf(operands));
    }
    /** Returns deterministic concrete members.
     * @param root representative
     * @return stable node sequence
     */
    List<Integer> members(int root) {
        List<Integer> result = new ArrayList<>();
        for (int i = 0; i < nodes.size(); i++) if (find(i) == find(root)) result.add(i);
        return result;
    }
    /** Returns a concrete node.
     * @param id stable identifier
     * @return immutable term
     */
    Term node(int id) { return nodes.get(id); }
    /** Returns concrete child identifiers.
     * @param id stable identifier
     * @return immutable operands
     */
    List<Integer> children(int id) { return children.get(id); }
    /** Returns the allocated enode count.
     * @return finite graph size
     */
    int size() { return nodes.size(); }
    /** Returns rebuild passes.
     * @return pass counter
     */
    long rebuilds() { return rebuilds; }
    /** Exact congruence signature.
     * @param op operator
     * @param sort schema
     * @param atom payload
     * @param children representatives
     */
    private record Key(String op, Sort sort, String atom, List<Integer> children) { }
    /** Checked forest edge.
     * @param target concrete target
     * @param proof justification
     * @param reverse orientation
     */
    private record Edge(int target, int proof, boolean reverse) { }
    /** Breadth-first predecessor.
     * @param previous prior node
     * @param edge traversed proof
     */
    private record Path(int previous, Edge edge) { }
}
