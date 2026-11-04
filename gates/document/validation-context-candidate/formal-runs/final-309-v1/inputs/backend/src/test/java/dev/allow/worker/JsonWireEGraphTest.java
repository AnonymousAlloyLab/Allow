package dev.allow.worker;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.egraph.Certificate;
import dev.allow.egraph.Context;
import dev.allow.egraph.EngineInput;
import dev.allow.egraph.IslandResult;
import dev.allow.egraph.ProofChecker;
import dev.allow.egraph.ProofStep;
import dev.allow.egraph.RuleCatalog;
import dev.allow.egraph.Sort;
import dev.allow.egraph.Term;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

/** Checks that transport nesting counts do not accidentally reject the admitted term grammar. */
class JsonWireEGraphTest {
    /** Keeps record-valued previews canonical after the generic JSON maps are reconstructed.
     * @throws IOException if a bounded result cannot traverse the strict codec
     */
    @Test
    void genericPreviewRoundTripKeepsCanonicalFrame() throws IOException {
        Term term = Term.atom(Sort.bool(), "[\"constant\",\"TRUE\"]");
        Map<String, Object> group = Map.of("id", 0, "nodes", List.of(term));
        IslandResult result = new IslandResult(List.of(0), "UNAVAILABLE", "ERROR", null, null,
                null, null, Map.of("nodes", 1L), Map.of("classes", List.of(group), "truncated", false),
                Map.of(), null);
        byte[] original = JsonWire.encode(result);
        IslandResult decoded = JsonWire.decode(original, IslandResult.class);
        assertArrayEquals(original, JsonWire.encode(decoded));
    }

    /** Round-trips a checked depth-100 term whose JSON uses more than 140 nested containers.
     * @throws IOException if the valid certificate cannot traverse the strict codec
     */
    @Test
    void admittedProofDepthSurvivesTransport() throws IOException {
        Sort bool = Sort.bool();
        Term atom = Term.atom(bool, "[\"unary\",\"SOME\",[\"ref\",\"sig\",0]]");
        Term root = atom;
        for (int i = 0; i < 100; i++) {
            root = Term.node("NOT", bool, List.of(root));
        }
        Context context = new Context("[\"module\",1]", List.of(0), List.of(atom));
        RuleCatalog rules = new RuleCatalog();
        ProofStep step = new ProofStep("REFL", root, root, List.of(), "", Map.of());
        Certificate certificate = new Certificate("allow-egraph-proof-v1", context, rules.digest(),
                root, root, List.of(step), 0);
        Certificate received = JsonWire.decode(JsonWire.encode(certificate), Certificate.class);
        assertEquals(certificate, received);
        assertTrue(new ProofChecker(rules).check(received, new EngineInput(context, root)));
    }

    /** Retains an independent transport cap for deeply nested malformed frames.
     * @throws IOException if a failure other than the intended nesting constraint occurs
     */
    @Test
    void excessiveWireNestingStillRejects() throws IOException {
        byte[] wire = ("[".repeat(400) + "0" + "]".repeat(400)).getBytes(StandardCharsets.UTF_8);
        try {
            JsonWire.decode(wire, JsonNode.class);
            fail("Wire nesting exceeded its fixed transport cap");
        } catch (com.fasterxml.jackson.core.exc.StreamConstraintsException expected) {
            assertTrue(expected.getMessage().contains("nesting depth"));
        }
    }
}
