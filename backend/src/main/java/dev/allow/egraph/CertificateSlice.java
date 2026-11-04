package dev.allow.egraph;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
/** Export-only dependency slicing; internal graph proof history and budgets remain intact. */
final class CertificateSlice {
    /** Prevents construction of the stateless export helper. */
    private CertificateSlice() { }
    /** Keeps only conclusion dependencies in original topological order.
     * @param original checked internal proof history
     * @return independently replayable compact certificate
     */
    static Certificate compact(Certificate original) {
        boolean[] needed = reachable(original.steps(), original.conclusion());
        int[] indices = new int[needed.length];
        Arrays.fill(indices, -1);
        List<ProofStep> steps = new ArrayList<>();
        for (int index = 0; index < needed.length; index++) {
            if (!needed[index]) continue;
            ProofStep old = original.steps().get(index);
            List<Integer> premises = new ArrayList<>();
            for (int premise : old.premises()) premises.add(indices[premise]);
            indices[index] = steps.size();
            steps.add(new ProofStep(old.kind(), old.left(), old.right(), premises, old.rule(), old.substitution()));
        }
        return new Certificate(original.profile(), original.context(), original.rulesetDigest(), original.input(),
                original.extracted(), steps, indices[original.conclusion()]);
    }
    /** Marks exact transitive proof premises without recursive traversal.
     * @param steps original topologically ordered history
     * @param conclusion selected root equality
     * @return dependency membership by original index
     */
    private static boolean[] reachable(List<ProofStep> steps, int conclusion) {
        boolean[] needed = new boolean[steps.size()];
        ArrayDeque<Integer> pending = new ArrayDeque<>();
        pending.add(conclusion);
        while (!pending.isEmpty()) {
            int index = pending.removeLast();
            if (needed[index]) continue;
            needed[index] = true;
            for (int premise : steps.get(index).premises()) pending.add(premise);
        }
        return needed;
    }
}
