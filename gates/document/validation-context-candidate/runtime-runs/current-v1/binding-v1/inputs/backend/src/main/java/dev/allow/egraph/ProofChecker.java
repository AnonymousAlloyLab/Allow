package dev.allow.egraph;
import java.util.HashSet;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Map;
/** Independent ground derivation replay; has no access to graph state.
     */
public final class ProofChecker {
    private final RuleCatalog catalog;
    /** Shares only the immutable registry.
     * @param catalog pinned registry
     */
    public ProofChecker(RuleCatalog catalog) { this.catalog = catalog; }
    /** Replays and binds a complete certificate.
     * @param certificate submitted proof
     * @param expected trusted original input
     * @return whether every local obligation holds
     */
    public boolean check(Certificate certificate, EngineInput expected) {
        try {
            validateContext(expected.context());
            validateContext(certificate.context());
            term(expected.root(), expected.context(), 0);
            term(certificate.input(), expected.context(), 0); term(certificate.extracted(), expected.context(), 0);
            if (!certificate.profile().equals("allow-egraph-proof-v1")
                    || !certificate.context().equals(expected.context())
                    || !certificate.rulesetDigest().equals(catalog.digest())
                    || !certificate.input().equals(expected.root())) return false;
            if (certificate.steps().size() > 4096) return false;
            for (ProofStep step : certificate.steps()) {
                term(step.left(), expected.context(), 0); term(step.right(), expected.context(), 0);
                for (Term binding : step.substitution().values()) term(binding, expected.context(), 0);
            }
            if (Wire.size(certificate) > 262144) return false;
            for (int i = 0; i < certificate.steps().size(); i++) local(certificate.steps(), i, expected.context());
            ProofStep conclusion = certificate.steps().get(certificate.conclusion());
            return conclusion.left().equals(certificate.input()) && conclusion.right().equals(certificate.extracted())
                    && certificate.extracted().cost() <= certificate.input().cost();
        } catch (RuntimeException error) { return false; }
    }
    /** Checks the fixed context and unique atom inventory.
     * @param context trusted anonymous boundary
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    static void validateContext(Context context) {
        for (Term atom : context.atoms()) {
            if (!atom.op().equals("ATOM") || !atom.children().isEmpty() || atom.atom().length() > 131072) {
                throw new IllegalArgumentException("Inventory leaf");
            }
        }
        if (context.module().isEmpty() || context.module().length() > 131072 || context.rootPath().size() > 128
                || context.atoms().size() > 2048 || context.rootPath().isEmpty()
                || new HashSet<>(context.atoms()).size() != context.atoms().size()) throw new IllegalArgumentException("Context");
        for (Integer index : context.rootPath()) if (index < 0) throw new IllegalArgumentException("Root path");
        String previous = "";
        for (Term atom : context.atoms()) {
            String key = Context.atomKey(atom);
            if (key.compareTo(previous) <= 0) throw new IllegalArgumentException("Inventory order");
            previous = key;
            if (!atom.op().equals("ATOM") || !atom.children().isEmpty()) throw new IllegalArgumentException("Inventory");
            term(atom, context, 0);
        }
    }
    /** Validates a finite sorted constructor tree.
     * @param value candidate term
     * @param context fixed atom authority
     * @param depth current depth
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    static void term(Term value, Context context, int depth) {
        ArrayDeque<Visit> work = new ArrayDeque<>(); work.add(new Visit(value, depth)); int count = 0;
        while (!work.isEmpty()) {
            Visit visit = work.removeLast();
            if (++count > 2048 || visit.depth() > 128) throw new IllegalArgumentException("Term limit");
            shape(visit.term(), context);
            for (Term child : visit.term().children()) work.add(new Visit(child, visit.depth() + 1));
        }
    }
    /** Checks one nonrecursive constructor.
     * @param value constructor
     * @param context atom authority
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    private static void shape(Term value, Context context) {
        String op = value.op(); List<Term> children = value.children();
        int arity = switch (op) {
            case "ATOM", "TRUE", "FALSE", "EMPTY" -> 0;
            case "NOT", "SOME", "NO" -> 1;
            case "AND", "OR", "UNION", "INTER", "DIFF" -> 2;
            default -> throw new IllegalArgumentException("Operator");
        };
        if (children.size() != arity) throw new IllegalArgumentException("Arity");
        if (op.equals("ATOM")) {
            if (value.atom().isEmpty() || value.atom().length() > 131072 || !context.atoms().contains(value)) throw new IllegalArgumentException("Fresh atom");
        } else if (!value.atom().isEmpty()) throw new IllegalArgumentException("Payload");
        boolean relation = List.of("EMPTY", "UNION", "INTER", "DIFF").contains(op);
        if (!op.equals("ATOM") && !value.sort().kind().equals(relation ? "REL" : "BOOL")) throw new IllegalArgumentException("Sort");
        for (Term child : children) {
            if (op.equals("SOME") || op.equals("NO")) {
                if (!child.sort().kind().equals("REL")) throw new IllegalArgumentException("Bridge sort");
            } else if (!child.sort().equals(value.sort())) throw new IllegalArgumentException("Child sort");
        }
    }
    /** Iterative bounded traversal entry.
     * @param term current constructor
     * @param depth root distance
     */
    private record Visit(Term term, int depth) { }
    /** Checks one prior-premise-only local edge.
     * @param steps accumulated proof
     * @param index candidate index
     * @param context fixed authority
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    void local(List<ProofStep> steps, int index, Context context) {
        proofDepth(steps, index);
        ProofStep step = steps.get(index); term(step.left(), context, 0); term(step.right(), context, 0);
        if (!step.left().sort().equals(step.right().sort())) throw new IllegalArgumentException("Endpoint sort");
        for (int premise : step.premises()) if (premise < 0 || premise >= index) throw new IllegalArgumentException("Forward premise");
        if (!step.kind().equals("RULE") && (!step.rule().isEmpty() || !step.substitution().isEmpty())) throw new IllegalArgumentException("Extraneous data");
        switch (step.kind()) {
            case "REFL" -> require(step.premises().isEmpty() && step.left().equals(step.right()));
            case "SYMM" -> symmetry(step, steps);
            case "TRANS" -> transitivity(step, steps);
            case "CONGRUENCE" -> congruence(step, steps);
            case "RULE" -> rule(step, context);
            default -> throw new IllegalArgumentException("Proof constructor");
        }
    }
    /** Rejects excessive proof-premise depth without recursion.
     * @param steps proof prefix
     * @param index candidate conclusion
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    private static void proofDepth(List<ProofStep> steps, int index) {
        int[] depths = new int[index + 1];
        for (int i = 0; i <= index; i++) {
            int depth = 1;
            for (int premise : steps.get(i).premises()) {
                if (premise < 0 || premise >= i) throw new IllegalArgumentException("Forward premise");
                depth = Math.max(depth, depths[premise] + 1);
            }
            if (depth > 128) throw new IllegalArgumentException("Proof depth");
            depths[i] = depth;
        }
    }
    /** Rejects a failed local condition.
     * @param condition required proposition
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    private static void require(boolean condition) { if (!condition) throw new IllegalArgumentException("Invalid proof"); }
    /** Checks reversal.
     * @param step conclusion
     * @param steps preceding edges
     */
    private static void symmetry(ProofStep step, List<ProofStep> steps) {
        require(step.premises().size() == 1); ProofStep premise = steps.get(step.premises().get(0));
        require(step.left().equals(premise.right()) && step.right().equals(premise.left()));
    }
    /** Checks exact intermediate equality.
     * @param step conclusion
     * @param steps preceding edges
     */
    private static void transitivity(ProofStep step, List<ProofStep> steps) {
        require(step.premises().size() == 2);
        ProofStep first = steps.get(step.premises().get(0)), second = steps.get(step.premises().get(1));
        require(step.left().equals(first.left()) && first.right().equals(second.left()) && step.right().equals(second.right()));
    }
    /** Checks ordered constructor congruence.
     * @param step conclusion
     * @param steps preceding edges
     */
    private static void congruence(ProofStep step, List<ProofStep> steps) {
        Term left = step.left(), right = step.right();
        require(left.op().equals(right.op()) && left.atom().equals(right.atom())
                && left.children().size() == right.children().size() && step.premises().size() == left.children().size());
        for (int i = 0; i < step.premises().size(); i++) {
            ProofStep premise = steps.get(step.premises().get(i));
            require(premise.left().equals(left.children().get(i)) && premise.right().equals(right.children().get(i)));
        }
    }
    /** Checks exact catalog instantiation.
     * @param step rule edge
     * @param context fixed atom authority
     */
    private void rule(ProofStep step, Context context) {
        RuleCatalog.Rewrite rule = catalog.rule(step.rule());
        require(step.premises().isEmpty() && step.left().sort().kind().equals(rule.family()));
        require(step.substitution().keySet().equals(RuleCatalog.variables(rule.left()).keySet()));
        for (Term binding : step.substitution().values()) term(binding, context, 0);
        require(step.left().equals(RuleCatalog.instantiate(rule.left(), step.substitution(), step.left().sort())));
        require(step.right().equals(RuleCatalog.instantiate(rule.right(), step.substitution(), step.left().sort())));
    }
}
