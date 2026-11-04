package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Finite Java/TypeScript agreement against the same concrete module fixtures. */
class DocumentTypeAgreementTest {
    private static final Set<String> TAGS = Set.of(
        "signature_ref", "field_ref", "variable_ref", "predicate_call", "and", "or", "not", "implies", "iff",
        "some_test", "no_test", "one_test", "lone_test", "equal", "subset", "union", "intersection", "difference",
        "join", "product", "transpose", "all_quant", "some_quant");

    /**
     * Compares both validators on each positive and negative registered example.
     * @throws IOException if the shared fixture cannot be read
     */
    @Test
    void agreesWithRegisteredTypeScriptCases() throws IOException {
        JsonNode root = fixtures();
        assertEquals(1, root.path("protocol").intValue());
        assertTrue(root.path("tagInventory").isArray());
        Set<String> inventory = new HashSet<>();
        for (JsonNode tag : root.path("tagInventory")) assertTrue(tag.isTextual() && inventory.add(tag.textValue()));
        assertEquals(TAGS, inventory);
        JsonNode cases = root.path("cases");
        assertTrue(cases.isArray());
        assertEquals(46, cases.size());
        Set<String> seen = new HashSet<>();
        for (JsonNode example : cases) checkExample(example, seen);
        assertEquals(46, seen.size());
    }

    /**
     * Checks one fixture's registration, TypeScript outcome and Java decision.
     * @param example concrete shared module fixture
     * @param seen observed tag/variant pairs
     */
    private void checkExample(JsonNode example, Set<String> seen) {
        String tag = example.path("tag").asText();
        String variant = example.path("variant").asText();
        String id = example.path("caseId").asText();
        assertTrue(TAGS.contains(tag), id);
        assertTrue(variant.equals("positive") || variant.equals("negative"), id);
        assertEquals(tag + "-" + variant, id);
        assertTrue(seen.add(id), id);
        assertTrue(example.path("expectedAccepted").isBoolean(), id);
        boolean expected = example.path("expectedAccepted").booleanValue();
        assertEquals(variant.equals("positive"), expected, id);
        assertTrue(example.path("expectedDiagnosticCategory").isNull(), id);
        JsonNode diagnostics = example.path("typescriptDiagnostics");
        assertTrue(diagnostics.isArray(), id);
        assertEquals(expected, diagnostics.isEmpty(), id + " TypeScript recorded outcome");
        assertEquals(expected, accepted(example.path("module")), id + " Java checker outcome");
    }

    /**
     * Evaluates the exact finite Java checker decision.
     * @param module complete untrusted module
     * @return true exactly when the checker accepts it
     */
    private boolean accepted(JsonNode module) {
        try {
            new ModuleChecker(module).check();
            return true;
        } catch (IllegalArgumentException invalid) {
            return false;
        }
    }

    /**
     * Loads the generated shared fixture from test resources.
     * @return strictly decoded fixture root
     * @throws IOException if missing or malformed
     */
    private JsonNode fixtures() throws IOException {
        InputStream stream = getClass().getResourceAsStream("/document-type-cases.json");
        if (stream == null) throw new IOException("Missing shared document type cases");
        try (stream) {
            return JsonWire.decode(stream.readAllBytes(), JsonNode.class);
        }
    }
}
