package dev.allow.corpus;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Checks isolated pool admission and anonymous identities against real Alloy. */
class CorpusEngineTest {
    /** Builds a complete response without an existing source command.
     * @throws Exception test setup failure
     */
    @Test void fullAndChecked() throws Exception {
        CorpusResponse result = run("sig A {r:set A}\npred p {some r}", 0);
        assertEquals("FULL", result.status());
        Map<?, ?> record = (Map<?, ?>) result.record();
        assertEquals(3, ((PoolBuilder.Pool) record.get("positive")).members().size());
        assertEquals(3, ((PoolBuilder.Pool) record.get("negative")).members().size());
        assertEquals(1, ((List<?>) record.get("trainingVariants")).size());
    }

    /** A fixed identity augmentation needs one checked rule regardless of search complexity.
     * @throws Exception solver setup failure
     */
    @Test void directAugmentationAvoidsSaturationBudget() throws Exception {
        CorpusResponse response = run("sig A {r:set A} pred p {some r and (some r or no r)}", 0);
        assertEquals("FULL", response.status());
        Map<?, ?> record = (Map<?, ?>) response.record();
        var variant = (TrainingVariant.Variant) ((List<?>) record.get("trainingVariants")).get(0);
        assertEquals("PINNED_RULE_REPLAY", variant.method());
        assertEquals(1, variant.certificate().steps().size());
        assertEquals("B_AND_TRUE", variant.certificate().steps().get(0).rule());
        assertNotEquals(variant.input(), variant.extracted());
        var checker = new dev.allow.egraph.ProofChecker(new dev.allow.egraph.RuleCatalog());
        assertTrue(checker.check(variant.certificate(), new dev.allow.egraph.EngineInput(
                variant.certificate().context(), variant.input())));
    }

    /** Facts remain active when constructing the negative query.
     * @throws Exception test setup failure
     */
    @Test void factsAndNegation() throws Exception {
        CorpusResponse result = run("sig A {}\nfact {no A}\npred p {some A}", 0);
        Map<?, ?> record = (Map<?, ?>) result.record();
        assertEquals("UNSAT", ((PoolBuilder.Pool) record.get("positive")).existence());
        assertEquals("SAT", ((PoolBuilder.Pool) record.get("negative")).existence());
        result = run("sig A {}\nfact {some A and no A}\npred p {some A}", 0);
        record = (Map<?, ?>) result.record();
        assertEquals("UNSAT", ((PoolBuilder.Pool) record.get("negative")).existence());
    }

    /** Anonymous environment ignores selected command and user names.
     * @throws Exception test setup failure
     */
    @Test void contextAndRenaming() throws Exception {
        var first = run("sig A {r:set A}\npred p {some r}", 0);
        var second = run("sig B {s:set B}\npred q {some s}\nrun q for 7", 0);
        Map<?, ?> a = (Map<?, ?>) first.record();
        Map<?, ?> b = (Map<?, ?>) second.record();
        assertEquals(a.get("context"), b.get("context"));
        assertEquals(((PoolBuilder.Pool) a.get("positive")).members(),
                ((PoolBuilder.Pool) b.get("positive")).members());
    }

    /** Discovery excludes parser helper and parameterized predicate.
     * @throws Exception test setup failure
     */
    @Test void discoveryAndInvalidTargets() throws Exception {
        String source = "sig A {}\npred p[x:A] {some x}\npred q {some A}";
        assertEquals(List.of(1), run(source, -1).targetSlots());
        assertEquals("REJECTED", run(source, 0).status());
        assertEquals("REJECTED", run(source, 9).status());
    }

    /** Atom limits leave a partial outcome with no invented witness.
     * @throws Exception test setup failure
     */
    @Test void atomLimitIsPartial() throws Exception {
        String source = "sig A,B,C {}\nfact {#A=3 and #B=3 and #C=3}\npred p {some A}";
        CorpusResponse result = run(source, 0);
        assertEquals("PARTIAL", result.status());
        Map<?, ?> record = (Map<?, ?>) result.record();
        PoolBuilder.Pool pool = (PoolBuilder.Pool) record.get("positive");
        assertEquals("SAT", pool.existence());
        assertEquals("LIMIT", pool.termination());
        assertTrue(pool.members().isEmpty());
    }

    /** Retained facts calling the target change the environment dependency identity.
     * @throws Exception test setup failure
     */
    @Test void targetDependentFacts() throws Exception {
        var first = run("sig A {}\npred p {some A}\nfact {p}", 0);
        var second = run("sig A {}\npred p {no A}\nfact {p}", 0);
        Map<?, ?> a = (Map<?, ?>) first.record();
        Map<?, ?> b = (Map<?, ?>) second.record();
        assertNotEquals(a.get("context"), b.get("context"));
    }

    /** Generated command helpers never alter source slots or anonymous corpus evidence.
     * @throws Exception test setup failure
     */
    @Test void generatedCommandHelpersExcluded() throws Exception {
        String prefix = "sig A {r:set A}\npred p {some r}\n";
        String suffix = "pred q {some r}\n";
        String[] commands = {"", "run {p} for 3\n", "run {} for 3\n",
                "check {p} for 3\n", "run {p} for 3\nrun {} for 4\n"};
        Map<?, ?> reference = (Map<?, ?>) run(prefix + suffix, 1).record();
        for (String command : commands) {
            String source = prefix + command + suffix;
            assertEquals(List.of(0, 1), run(source, -1).targetSlots());
            CorpusResponse response = run(source, 1);
            assertEquals("FULL", response.status());
            Map<?, ?> actual = (Map<?, ?>) response.record();
            assertEquals(reference.get("context"), actual.get("context"));
            assertEquals(reference.get("predicate"), actual.get("predicate"));
            assertEquals(reference.get("positive"), actual.get("positive"));
            assertEquals(reference.get("negative"), actual.get("negative"));
        }
    }

    /** Unsupported declaration attributes have a stable reason, without source text.
     * @throws Exception test setup failure
     */
    @Test void signatureProfileReason() throws Exception {
        CorpusResponse response = run("one sig A {}\npred p {some A}", 0);
        assertEquals("SIGNATURE_PROFILE_UNSUPPORTED", response.reason());
    }

    /** Every supported N requires that many distinct complete members in each polarity.
     * @throws Exception hashing or solver setup failure
     */
    @Test void configurablePoolSizes() throws Exception {
        String source = "sig A {r:set A} sig B {} pred p {some r}";
        for (int count : new int[]{3, 4, 5}) {
            CorpusResponse response = run(source, 0, count);
            assertEquals("FULL", response.status());
            Map<?, ?> record = (Map<?, ?>) response.record();
            for (String polarity : List.of("positive", "negative")) {
                PoolBuilder.Pool pool = (PoolBuilder.Pool) record.get(polarity);
                assertEquals(count, pool.members().size());
                assertEquals(count, new java.util.HashSet<>(pool.members()).size());
                assertEquals("SAT", pool.existence());
                assertEquals("CAP_REACHED", pool.termination());
            }
        }
        assertEquals("REJECTED", run(source, 0, 2).status());
        assertEquals("REJECTED", run(source, 0, 6).status());
    }

    /** Invokes the engine with an exact source identity.
     * @param source test model
     * @param slot target or discovery
     * @return worker response
     * @throws Exception digest failure
     */
    private CorpusResponse run(String source, int slot) throws Exception {
        return run(source, slot, 3);
    }

    /** Invokes a selected N with the exact source identity.
     * @param source test model
     * @param slot target or discovery
     * @param count requested members per polarity
     * @return worker response
     * @throws Exception digest failure
     */
    private CorpusResponse run(String source, int slot, int count) throws Exception {
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(source.getBytes(StandardCharsets.UTF_8)));
        return new CorpusEngine().execute(new CorpusRequest(1, source, hash, slot, count, "test", "test"));
    }
}
