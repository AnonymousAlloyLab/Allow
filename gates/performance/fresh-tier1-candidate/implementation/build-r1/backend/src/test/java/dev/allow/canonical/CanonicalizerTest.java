package dev.allow.canonical;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Checks parser-to-slot behavior with independent synthetic modules, never corpus copies. */
class CanonicalizerTest {
    /** Parses one in-memory module with a fixed synthetic filename.
     * @param source synthetic import-free Alloy text
     * @return fully resolved module
     * @throws Err if the fixture is invalid Alloy
     */
    private CompModule parse(String source) throws Err {
        String path = "/tmp/allow-slot-fixture.als";
        Map<String, String> files = new HashMap<>();
        files.put(path, source);
        return CompUtil.parseEverything_fromFile(A4Reporter.NOP, files, path);
    }

    /** Resolves and maps the first command in a synthetic module.
     * @param source independently authored Alloy fixture
     * @return structural profile result
     * @throws Err if the fixture cannot resolve
     */
    private CanonicalView view(String source) throws Err {
        CompModule module = parse(source);
        return new Canonicalizer().analyze(module, module.getAllCommands().get(0));
    }

    /** Requires actual available payloads so equality tests cannot pass on empty failures.
     * @param left first synthetic source
     * @param right capture-avoiding renamed source
     * @throws Err if a fixture is invalid
     */
    private void sameAnonymous(String left, String right) throws Err {
        CanonicalView first = view(left);
        CanonicalView second = view(right);
        assertEquals("AVAILABLE", first.status());
        assertEquals("AVAILABLE", second.status());
        assertEquals(first.payload(), second.payload());
        assertEquals(first.features(), second.features());
        assertEquals(first.sha256(), second.sha256());
    }

    /** Checks observed declaration renaming leaves anonymous bytes and vectors unchanged.
     * @throws Err if a synthetic module is invalid
     */
    @Test
    void renamesSignaturesWithoutLeakingLabels() throws Err {
        sameAnonymous("sig Person {} run { some Person } for 3",
                "sig CustomerSecret {} run { some CustomerSecret } for 3");
        CanonicalView result = view("sig CustomerSecret {} run { some CustomerSecret } for 3");
        assertFalse(result.payload().contains("CustomerSecret"));
        assertEquals(128, result.features().size());
    }

    /** Checks fields, predicate calls and lexical parameter identity under alpha-renaming.
     * @throws Err if a synthetic module is invalid
     */
    @Test
    void renamesFieldsPredicatesAndParameters() throws Err {
        sameAnonymous("sig Person { friends: set Person } pred ok[p: Person] { some p.friends } run { some p: Person | ok[p] } for 3",
                "sig Human { links: set Human } pred valid[q: Human] { some q.links } run { some q: Human | valid[q] } for 3");
    }

    /** Checks nested shadowing is resolved by binder identity rather than spelling.
     * @throws Err if a fixture is invalid
     */
    @Test
    void preservesShadowedBinderScopes() throws Err {
        sameAnonymous("sig A {} run { some x: A | (some x: A | some x) and some x } for 3",
                "sig Z {} run { some outer: Z | (some inner: Z | some inner) and some outer } for 3");
    }

    /** Distinguishes separate declaration roles within one fixed module context.
     * @throws Err if a fixture is invalid
     */
    @Test
    void distinctSignaturesDoNotCollapse() throws Err {
        CanonicalView a = view("sig A, B {} run { some A } for 3");
        CanonicalView b = view("sig A, B {} run { some B } for 3");
        assertEquals("AVAILABLE", a.status());
        assertEquals("AVAILABLE", b.status());
        assertNotEquals(a.payload(), b.payload());
    }

    /** Ensures allocation follows declaration order even when lexical sorting reverses.
     * @throws Err if an independent fixture is invalid
     */
    @Test
    void lexicalSpellingOrderCannotInfluenceSlots() throws Err {
        sameAnonymous("sig Zebra, Apple {} run { some Zebra and no Apple } for 3",
                "sig Apple, Zebra {} run { some Apple and no Zebra } for 3");
    }

    /** Distinguishes multiplicity operators and ordered relational operands.
     * @throws Err if a fixture is invalid
     */
    @Test
    void preservesMultiplicityAndOperandOrder() throws Err {
        CanonicalView set = view("sig A { r: set A } run { some A } for 3");
        CanonicalView lone = view("sig A { r: lone A } run { some A } for 3");
        assertEquals("AVAILABLE", set.status());
        assertEquals("AVAILABLE", lone.status());
        assertNotEquals(set.payload(), lone.payload());
        assertNotEquals(view("sig A, B {} run { some A -> B } for 3").payload(),
                view("sig A, B {} run { some B -> A } for 3").payload());
    }

    /** Ensures unsupported signature attributes cannot silently lose semantics.
     * @throws Err if a fixture is invalid
     */
    @Test
    void rejectsUnsupportedSignatureAttributes() throws Err {
        for (String prefix : new String[] {"one", "lone", "some", "abstract", "var"}) {
            CanonicalView result = view(prefix + " sig A {} run { some A } for 3");
            assertEquals("UNSUPPORTED_CANONICAL", result.status());
            assertEquals("", result.payload());
            assertTrue(result.features().isEmpty());
        }
    }

    /** Rejects inheritance and disjoint fields rather than inventing partial keys.
     * @throws Err if a fixture is invalid
     */
    @Test
    void rejectsInheritanceAndDisjointDeclarations() throws Err {
        assertEquals("UNSUPPORTED_CANONICAL", view("sig A {} sig B extends A {} run {} for 3").status());
        assertEquals("UNSUPPORTED_CANONICAL", view("sig A { disj r, s: set A } run {} for 3").status());
    }

    /** Preserves facts and scope values even when the selected predicate is identical.
     * @throws Err if a fixture is invalid
     */
    @Test
    void includesFactsAndScopeInPayload() throws Err {
        CanonicalView initial = view("sig A {} run { some A } for 3");
        CanonicalView changed = view("sig A {} fact { one A } run { some A } for 3");
        assertEquals("AVAILABLE", changed.status());
        assertNotEquals(initial.payload(), changed.payload());
        assertNotEquals(initial.payload(), view("sig A {} run { some A } for 4").payload());
    }

    /** Confirms emitted arrays round-trip without changing exact canonical bytes.
     * @throws Exception if the independent JSON parser rejects a payload
     */
    @Test
    void serializedPayloadRoundTrips() throws Exception {
        CanonicalView result = view("sig A {} run { some A } for 3");
        assertEquals("AVAILABLE", result.status());
        assertEquals(result.payload(), new ObjectMapper().readTree(result.payload()).toString());
        double sum = 0;
        for (double feature : result.features()) { sum += feature * feature; }
        assertEquals(1.0, sum, 1.0e-12);
    }

    /** Verifies arbitrary strings and temporal operators never produce embedding payloads.
     * @throws Err if a fixture is invalid
     */
    @Test
    void rejectsStringsAndTemporalOperators() throws Err {
        assertEquals("UNSUPPORTED_CANONICAL", view("run { some \"Secret\" } for 3").status());
        assertEquals("UNSUPPORTED_CANONICAL", view("sig A {} run { eventually some A } for 3").status());
    }
}
