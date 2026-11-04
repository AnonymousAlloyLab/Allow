package dev.allow.canonical;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import edu.mit.csail.sdg.translator.A4Options;
import edu.mit.csail.sdg.translator.TranslateAlloyToKodkod;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.List;
import dev.allow.egraph.IslandResult;
import java.util.HexFormat;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Regression checks for captured anonymous roots and frozen structural output.
     */
class IslandAdapterTest {
    /** Resolves one synthetic in-memory fixture.
     * @param source Alloy source
     * @return parsed module
     * @throws Err on invalid fixture
     */
    private CompModule parse(String source) throws Err {
        String path = "/tmp/allow-island-fixture.als";
        return CompUtil.parseEverything_fromFile(A4Reporter.NOP, new HashMap<>(Map.of(path, source)), path);
    }

    /** Creates a single traversal and captures its exact roots.
     * @param source Alloy fixture
     * @return completed mapper
     * @throws Err on invalid fixture
     */
    private ModuleEncoder encoder(String source) throws Err {
        CompModule module = parse(source);
        ModuleEncoder encoder = new ModuleEncoder(module);
        encoder.encode(module.getAllCommands().get(0));
        return encoder;
    }

    /** Checks the pre-adapter golden payload, digest, and feature vector.
     * @throws Exception on fixture failure
     */
    @Test
    void structuralGoldenRemainsUnchanged() throws Exception {
        CompModule module = parse("sig A {} pred p[x: A] { some x } run p for 3");
        CanonicalView view = new Canonicalizer().analyze(module, module.getAllCommands().get(0));
        assertEquals("51a9495091a136f2f29dcac9adfae572ed37a5be22b788d373929d590b662a3f", view.sha256());
        byte[] features = new ObjectMapper().writeValueAsBytes(view.features());
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(features));
        assertEquals("02f80d10b297fe34823cdab66065c46ff2b439675604b06e57f7b8be86383ff9", hash);
    }

    /** Exercises root isolation and capture of independently allocated binders.
     * @throws Exception on fixture failure
     */
    @Test
    void capturesFunctionFactAndCommandOccurrences() throws Exception {
        ModuleEncoder encoder = encoder("sig A {} pred p[x: A] { some x } fact { some A } run p for 3");
        assertEquals(3, encoder.islands().size());
        assertEquals(java.util.List.of(3, 0, 5), encoder.islands().get(0).path());
        assertEquals(java.util.List.of(4, 0), encoder.islands().get(1).path());
        assertEquals(java.util.List.of(5, 6), encoder.islands().get(2).path());
        assertTrue(encoder.islands().get(0).tree().toString().contains("bound, 0"));
        assertTrue(encoder.islands().get(2).tree().toString().contains("bound, 1"));
    }

    /** Confirms unsupported binder bodies remain a single opaque atom.
     * @throws Exception on fixture failure
     */
    @Test
    void quantifierIsOpaque() throws Exception {
        ModuleEncoder encoder = encoder("sig A {} run { some x: A | some x and some x } for 3");
        var capture = encoder.islands().get(0);
        var term = new IslandLowering(encoder.slots()).lower(capture.expression(), capture.tree());
        String text = new ObjectMapper().writeValueAsString(term);
        assertTrue(text.contains("quantifier"));
        assertFalse(text.contains("sig A"));
        assertFalse(text.contains("\"op\":\"SOME\""));
    }

    /** Nominal identities remain distinct despite equal relation arity.
     * @throws Exception on fixture failure
     */
    @Test
    void distinctNominalColumnsRemainDistinct() throws Exception {
        ModuleEncoder first = encoder("sig A, B {} run { some A and some B } for 3");
        var capture = first.islands().get(0);
        var term = new IslandLowering(first.slots()).lower(capture.expression(), capture.tree());
        String text = new ObjectMapper().writeValueAsString(term);
        assertTrue(text.contains("sig:0"));
        assertTrue(text.contains("sig:1"));
        assertNotEquals("", text);
    }
    /** Renamed declarations and parameters preserve exact typed terms.
     * @throws Exception on fixture failure
     */
    @Test
    void renamedParametersKeepAnonymousTerms() throws Exception {
        ModuleEncoder a = encoder("sig A {} pred p[x: A] { some x and some x } run p");
        ModuleEncoder b = encoder("sig Hidden {} pred q[y: Hidden] { some y and some y } run q");
        var x = a.islands().get(0);
        var y = b.islands().get(0);
        assertEquals(new IslandLowering(a.slots()).lower(x.expression(), x.tree()),
                new IslandLowering(b.slots()).lower(y.expression(), y.tree()));
    }

    /** Distinct nominal operands cannot become a typed relation union.
     * @throws Exception on fixture failure
     */
    @Test
    void mixedSchemaUnionIsOpaque() throws Exception {
        ModuleEncoder encoder = encoder("sig A, B {} run { some (A + B) } for 3");
        var capture = encoder.islands().get(0);
        var term = new IslandLowering(encoder.slots()).lower(capture.expression(), capture.tree());
        String json = new ObjectMapper().writeValueAsString(term);
        assertFalse(json.contains("\"op\":\"UNION\""));
        assertTrue(json.contains("PLUS"));
    }

    /** Confirms a predicate body receives a checked nontrivial extraction.
     * @throws Exception on fixture failure
     */
    @Test
    void predicateBodyGetsCheckedExtraction() throws Exception {
        CompModule module = parse("sig A {} pred p[x: A] { some x and some x } run p for 3");
        CanonicalView view = new Canonicalizer().analyze(module, module.getAllCommands().get(0));
        var island = view.egraph().islands().get(0);
        assertEquals(java.util.List.of(3, 0, 5), island.rootPath());
        assertEquals("CHECKED", island.certificateStatus());
        assertEquals("AND", island.input().op());
        assertEquals("SOME", island.extracted().op());
        assertTrue(island.extractedCost() < island.inputCost());
    }

    /** Checks Boolean and relational identities with the actual bounded Alloy solver.
     * @throws Exception if a fixture or solver fails
     */
    @Test
    void alloySolverFindsNoBoundedCounterexample() throws Exception {
        assertNoCounterexample("sig A {} run { not ((some A and some A) iff some A) } for 3");
        assertNoCounterexample("sig A {} run { not ((A + A) = A) } for 3");
    }

    /** Solves a synthetic counterexample query.
     * @param source counterexample query
     * @throws Exception if parsing or solving fails
     */
    private void assertNoCounterexample(String source) throws Exception {
        CompModule module = parse(source);
        var solution = TranslateAlloyToKodkod.execute_command(A4Reporter.NOP, module.getAllReachableSigs(),
                module.getAllCommands().get(0), new A4Options());
        assertFalse(solution.satisfiable());
    }


    /** Rejects exponential IFF expansion before constructing oversized input.
     * @throws Exception on fixture failure
     */
    @Test
    void nestedIffRespectsLoweringBudget() throws Exception {
        String expression = "some A";
        for (int i = 0; i < 12; i++) { expression = "(" + expression + " iff some A)"; }
        ModuleEncoder encoder = encoder("sig A {} run { " + expression + " } for 3");
        var capture = encoder.islands().get(0);
        IslandLowering lowering = new IslandLowering(encoder.slots());
        boolean limited = false;
        try { lowering.lower(capture.expression(), capture.tree()); }
        catch (IslandLimit expected) { limited = true; }
        assertTrue(limited);
    }

    /** Counts bytes without allocating huge output and preserves a limit sentinel.
     * @throws Exception if fixture parsing fails
     */
    @Test
    void outputBudgetTruncatesAndReportsLimit() throws Exception {
        assertTrue(IslandAdapter.fits("a".repeat(524286)));
        assertFalse(IslandAdapter.fits("a".repeat(524287)));
        var previous = new IslandResult(List.of(3, 0, 5), "UNAVAILABLE", "ERROR",
                null, null, null, null, Map.of(), Map.of("large", "a".repeat(524288)), Map.of(), null);
        List<IslandResult> results = new ArrayList<>();
        results.add(previous);
        ModuleEncoder encoder = encoder("sig A {} run { some A } for 3");
        new IslandAdapter(encoder.slots()).appendLimit(results, List.of(5, 6), "digest");
        assertEquals(1, results.size());
        assertEquals("OUTPUT_LIMIT", results.get(0).stopReason());
        assertEquals(List.of(5, 6), results.get(0).rootPath());
    }

}
