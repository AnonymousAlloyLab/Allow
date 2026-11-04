package dev.allow.corpus;

import dev.allow.egraph.Certificate;
import dev.allow.egraph.EngineInput;
import dev.allow.egraph.IslandResult;
import dev.allow.egraph.ProofChecker;
import dev.allow.egraph.ProofStep;
import dev.allow.egraph.RuleCatalog;
import dev.allow.egraph.Term;
import java.util.List;
import java.util.Map;

/** Builds a nontrivial checked structural augmentation of a captured root. */
final class TrainingVariant {
    /** Prevents construction of the stateless helper. */
    private TrainingVariant() { }

    /** Returns a checked distinct endpoint pair or an empty list on resource failure.
     * @param original checked target island
     * @return at most one independently checked variant certificate
     */
    static List<Variant> create(IslandResult original) {
        if (!"CHECKED".equals(original.certificateStatus()) || original.certificate() == null) return List.of();
        return fromCertificate(original.certificate());
    }

    /** Replays the original proof and a single pinned identity rule without an unnecessary search.
     * @param original previously checked source-to-representative proof
     * @return explicit proof-only variants, with no saturation claim
     */
    static List<Variant> fromCertificate(Certificate original) {
        RuleCatalog catalog = new RuleCatalog();
        ProofChecker checker = new ProofChecker(catalog);
        if (!checker.check(original, new EngineInput(original.context(), original.input()))) return List.of();
        Term source = original.input();
        Term truth = Term.node("TRUE", source.sort(), List.of());
        Term augmented = Term.node("AND", source.sort(), List.of(source, truth));
        ProofStep step = new ProofStep("RULE", augmented, source, List.of(), "B_AND_TRUE", Map.of("p", source));
        Certificate proof = new Certificate("allow-egraph-proof-v1", original.context(), catalog.digest(),
                augmented, source, List.of(step), 0);
        if (!checker.check(proof, new EngineInput(original.context(), augmented))) return List.of();
        return List.of(new Variant("CHECKED", augmented, source, proof, "PINNED_RULE_REPLAY"));
    }

    /** A checked augmentation, separate from a saturation result.
     * @param certificateStatus independent replay outcome
     * @param input augmented term
     * @param extracted original term linked to its existing representative by the original certificate
     * @param certificate one-step checked derivation
     * @param method explicit proof-only construction method
     */
    record Variant(String certificateStatus, Term input, Term extracted, Certificate certificate, String method) { }
}
