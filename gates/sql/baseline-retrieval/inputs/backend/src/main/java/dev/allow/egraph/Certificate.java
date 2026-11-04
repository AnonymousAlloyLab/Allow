package dev.allow.egraph;
import java.util.List;
/** Replayable anonymous equality certificate.
     */
public record Certificate(String profile, Context context, String rulesetDigest, Term input,
                          Term extracted, List<ProofStep> steps, int conclusion) {
    /** Freezes proof steps.
     * @param profile certificate version
     * @param context fixed context
     * @param rulesetDigest exact catalog digest
     * @param input original root
     * @param extracted chosen root
     * @param steps ordered derivation
     * @param conclusion root proof index
     */
    public Certificate { steps = List.copyOf(steps); }
}
