package dev.allow.egraph;
import java.util.List;
import java.util.Map;
/** Explicit local equality justification.
     */
public record ProofStep(String kind, Term left, Term right, List<Integer> premises,
                        String rule, Map<String, Term> substitution) {
    /** Copies derivation data.
     * @param kind proof constructor
     * @param left source
     * @param right target
     * @param premises prior steps
     * @param rule registry identifier
     * @param substitution typed ground substitution
     */
    public ProofStep { premises = List.copyOf(premises); substitution = Map.copyOf(substitution); }
}
