package dev.allow.egraph;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
/** Checked append-only proof DAG; new semantic edges are validated before graph mutation.
     */
final class ProofStore {
    private final List<ProofStep> steps = new ArrayList<>();
    private final ProofChecker checker;
    private final Context context;
    private int bytes;
    /** Binds local replay to one context.
     * @param checker separate replay implementation
     * @param context fixed authority
     */
    ProofStore(ProofChecker checker, Context context) { this.checker = checker; this.context = context; }
    /** Checks and appends one derivation.
     * @param kind constructor
     * @param left endpoint
     * @param right endpoint
     * @param premises preceding edges
     * @param rule closed identifier
     * @param substitution rule variables
     * @return proof index
     * @throws RunBudget.Limit when validation or resource checks reject the operation
     */
    int append(String kind, Term left, Term right, List<Integer> premises, String rule, Map<String, Term> substitution) {
        if (steps.size() >= 4096) throw new RunBudget.Limit("PROOF_LIMIT");
        ProofStep step = new ProofStep(kind, left, right, premises, rule, substitution);
        steps.add(step);
        try {
            checker.local(steps, steps.size() - 1, context);
            int size = Wire.size(step);
            if (bytes + size > 240000) throw new RunBudget.Limit("PROOF_LIMIT");
            bytes += size;
            return steps.size() - 1;
        } catch (RuntimeException error) {
            steps.remove(steps.size() - 1);
            throw error;
        }
    }
    /** Constructs an exact reflexivity edge.
     * @param term concrete endpoint
     * @return proof index
     */
    int refl(Term term) { return append("REFL", term, term, List.of(), "", Map.of()); }
    /** Reverses a checked edge.
     * @param index existing proof
     * @return reversed proof
     */
    int reverse(int index) {
        ProofStep step = steps.get(index);
        return append("SYMM", step.right(), step.left(), List.of(index), "", Map.of());
    }
    /** Composes checked edges.
     * @param first preceding equality
     * @param second following equality
     * @return composed proof
     */
    int compose(int first, int second) {
        return append("TRANS", steps.get(first).left(), steps.get(second).right(), List.of(first, second), "", Map.of());
    }
    /** Returns immutable proof data.
     * @return ordered proof snapshot
     */
    List<ProofStep> steps() { return List.copyOf(steps); }
    /** Returns a checked concrete edge.
     * @param index proof index
     * @return stored proof
     */
    ProofStep get(int index) { return steps.get(index); }
}
