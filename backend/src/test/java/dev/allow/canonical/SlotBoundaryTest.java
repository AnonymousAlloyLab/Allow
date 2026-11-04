package dev.allow.canonical;

import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.alloy4.Pos;
import edu.mit.csail.sdg.ast.ExprVar;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.fail;

/** Exercises scope and byte boundaries omitted by ordinary end-to-end solver fixtures. */
class SlotBoundaryTest {
    /** Parses independent synthetic source without corpus paths or ambient imports.
     * @param source import-free source
     * @return resolved module
     * @throws Err if the fixture is invalid
     */
    private CompModule parse(String source) throws Err {
        String path = "/tmp/allow-slot-boundary.als";
        Map<String, String> files = new HashMap<>();
        files.put(path, source);
        return CompUtil.parseEverything_fromFile(A4Reporter.NOP, files, path);
    }

    /** Maps a synthetic fixture and requires nonempty supported behavior.
     * @param source import-free fixture
     * @return available canonical view
     * @throws Err if the fixture is invalid
     */
    private CanonicalView view(String source) throws Err {
        CompModule module = parse(source);
        CanonicalView result = new Canonicalizer().analyze(module, module.getAllCommands().get(0));
        assertEquals("AVAILABLE", result.status());
        return result;
    }

    /** Checks that later binder domains resolve preceding lexical declarations.
     * @throws Err if either capture-avoiding synthetic fixture is invalid
     */
    @Test
    void dependentDomainsPreserveReferences() throws Err {
        CanonicalView first = view("sig A {} run { some x: A, y: x | some y } for 3");
        CanonicalView renamed = view("sig Z {} run { some outer: Z, inner: outer | some inner } for 3");
        assertEquals(first.payload(), renamed.payload());
        assertEquals(first.features(), renamed.features());
        assertNotEquals(first.payload(), view("sig A {} run { some x: A, y: A | some y } for 3").payload());
    }

    /** Checks let shadowing and references after nested scope exit.
     * @throws Err if either synthetic fixture is invalid
     */
    @Test
    void letScopeIsCaptureAvoiding() throws Err {
        CanonicalView first = view("sig A {} run { some x: A | (let x = A | some x) and some x } for 3");
        CanonicalView renamed = view("sig Z {} run { some outer: Z | (let inner = Z | some inner) and some outer } for 3");
        assertEquals(first.payload(), renamed.payload());
        assertEquals(first.features(), renamed.features());
    }

    /** Requires rejection of an unbound parser identity even if its spelling matches a signature.
     * @throws Err if the declaration fixture is invalid
     */
    @Test
    void freeReferencesNeverBecomeGlobalSlots() throws Err {
        CompModule module = parse("sig A {} run {} for 3");
        SlotRegistry slots = new SlotRegistry(module);
        ExprVar local = ExprVar.make(Pos.UNKNOWN, "A");
        rejectFree(slots, local);
        Map<edu.mit.csail.sdg.ast.ExprHasName, Integer> saved = slots.snapshot();
        assertEquals(0, slots.bind(local));
        Sig signature = module.getAllSigs().iterator().next();
        assertEquals(List.of("ref", "bound", 0), slots.reference(local));
        assertEquals(List.of("ref", "sig", 0), slots.reference(signature));
        assertNotEquals(slots.reference(local), slots.reference(signature));
        slots.restore(saved);
        rejectFree(slots, local);
        assertEquals(1, slots.bind(ExprVar.make(Pos.UNKNOWN, "A")));
    }

    /** Asserts an unbound reference fails closed without a lambda test adapter.
     * @param slots current scope
     * @param variable parser-owned reference with no visible declaration
     */
    private void rejectFree(SlotRegistry slots, ExprVar variable) {
        try {
            slots.reference(variable);
            fail("A free variable acquired an anonymous slot");
        } catch (UnsupportedCanonical expected) {
            assertEquals(UnsupportedCanonical.class, expected.getClass());
        }
    }

    /** Requires relation arity to affect the whole anonymous declaration structure.
     * @throws Err if either synthetic declaration is invalid
     */
    @Test
    void fieldArityCannotCollapse() throws Err {
        CanonicalView binary = view("sig A { r: set A } run {} for 3");
        CanonicalView ternary = view("sig A { r: set A -> A } run {} for 3");
        assertNotEquals(binary.payload(), ternary.payload());
    }

    /** Checks exact typed framing for tags, namespaces, child order and null versus empty.
     */
    @Test
    void framingSeparatesStructuralValues() {
        assertNotEquals(bytes("ref", "sig", 0), bytes("ref", "bound", 0));
        assertNotEquals(bytes("number", 1), bytes("constant", "TRUE"));
        assertNotEquals(bytes("list", List.of(0, 1)), bytes("list", List.of(1, 0)));
        assertNotEquals(bytes("function", 0, null, List.of()), bytes("function", 0, List.of(), null));
        assertEquals("[\"ref\",\"sig\",0]", bytes("ref", "sig", 0));
    }

    /** Serializes internal grammar fixtures without adding presentation data.
     * @param tag structural constructor
     * @param values typed ordered values
     * @return exact compact JSON
     */
    private String bytes(String tag, Object... values) {
        return AnonymizedArtifact.fromStructure(CanonicalNodes.node(tag, values)).payload();
    }

    /** Checks a fixed byte/hash/vector oracle computed independently in Python from the frozen profile.
     */
    @Test
    void exactBytesDetermineFeatures() {
        List<Object> command = CanonicalNodes.node("command", false, 3, -1, -1, List.of(),
                CanonicalNodes.node("constant", "TRUE"));
        AnonymizedArtifact artifact = AnonymizedArtifact.fromStructure(
                CanonicalNodes.node("module", 1, List.of(), List.of(), List.of(), command));
        String expected = "[\"module\",1,[],[],[],[\"command\",false,3,-1,-1,[],[\"constant\",\"TRUE\"]]]";
        assertArrayEquals(expected.getBytes(StandardCharsets.UTF_8), artifact.bytes());
        assertEquals("500bb93067f18d12e464d2f37cdec657925ebb43b4a981c7acea0ad8786ad3bf",
                CanonicalDigest.hex(artifact));
        List<Double> features = new EmbeddingEncoder().encode(artifact);
        List<Integer> occupied = List.of(5, 12, 30, 31, 36, 41, 53, 72, 77, 81, 90, 91, 95, 119, 120, 126);
        assertEquals(128, features.size());
        for (int index = 0; index < 128; index++) {
            int count = index == 36 || index == 77 ? 2 : occupied.contains(index) ? 1 : 0;
            assertEquals(count / Math.sqrt(22), features.get(index), 1.0e-15);
        }
    }
}
