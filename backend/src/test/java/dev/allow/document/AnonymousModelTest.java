package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.*;

/** Finite structural disclosure and exact inverse-inventory regression cases. */
class AnonymousModelTest {
    private static final String SOURCE = "// private comment\nsig Person { friend: set Person }\n"
            + "pred chosen[x: set Person] { all y: Person | y in x }\npred entry { chosen[Person] }\nrun entry for 3 but 4 Int, 3 seq\n";

    /** Checks actual Alloy parser/elaborator output before and after inverse renaming.
     * @throws DocumentValidationException invalid authored fixture
     */
    @Test
    void anonymizesEveryNameAndRestoresReferences() throws DocumentValidationException {
        AnonymousModel model = new AnonymousModel(module(SOURCE));
        String anonymous = model.source();
        assertFalse(anonymous.contains("Person"));
        assertFalse(anonymous.contains("friend"));
        assertFalse(anonymous.contains("chosen"));
        assertFalse(anonymous.contains("private comment"));
        String restored = model.restore(module(anonymous));
        assertTrue(restored.contains("Person"));
        assertTrue(restored.contains("friend"));
        assertTrue(restored.contains("chosen"));
        assertTrue(restored.contains("x:"));
        assertTrue(restored.contains("y:"));
        assertFalse(restored.contains("private comment"));
        assertTrue(module(restored).isObject());
    }

    /** New declarations cannot be guessed back into private display names.
     * @throws DocumentValidationException invalid fixture
     */
    @Test
    void rejectsUnknownMissingAndReboundSlots() throws DocumentValidationException {
        AnonymousModel model = new AnonymousModel(module(SOURCE));
        JsonNode unknown = module(model.source().replace("Slot0", "Unexpected"));
        assertThrows(IllegalArgumentException.class, new Restore(model, unknown));
        ObjectNode missing = (ObjectNode) module(model.source());
        ((com.fasterxml.jackson.databind.node.ArrayNode) missing.path("nodes")).removeAll();
        assertThrows(IllegalArgumentException.class, new Restore(model, missing));
        JsonNode rebound = module(model.source());
        String signature = rebound.path("signatures").path(0).path("name").asText();
        String predicate = rebound.path("predicates").path(0).path("name").asText();
        ((ObjectNode) rebound.path("signatures").path(0)).put("name", predicate);
        ((ObjectNode) rebound.path("predicates").path(0)).put("name", signature);
        assertThrows(IllegalArgumentException.class, new Restore(model, rebound));
    }

    /** A bounded formula repair retains inventory while receiving ordinary parser checking.
     * @throws DocumentValidationException invalid fixture
     */
    @Test
    void allowsFormulaChangeWithoutNameExpansion() throws DocumentValidationException {
        AnonymousModel model = new AnonymousModel(module("sig Secret {}\npred desired { some Secret }\nrun desired for 3 but 4 Int, 3 seq\n"));
        String repaired = model.restore(module(model.source().replace("some (", "no (")));
        assertTrue(repaired.contains("Secret"));
        assertTrue(repaired.contains("no ("));
        assertTrue(module(repaired).isObject());
    }

    /** Uses actual document parsing, typing and projection for authored source.
     * @param source complete fixture
     * @return checked supported module
     * @throws DocumentValidationException invalid fixture
     */
    private JsonNode module(String source) throws DocumentValidationException {
        ObjectNode candidate = JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", source);
        JsonNode result = new DocumentEngine().validate(candidate, JsonNodeFactory.instance.objectNode(), JsonNodeFactory.instance.objectNode(), "test");
        assertEquals("BLOCK_SUPPORTED", result.path("mode").asText());
        return result.path("module");
    }

    /** Names the rejected restore operation without an undocumented lambda.
     * @param model original local map
     * @param generated proposed complete module
     */
    private record Restore(AnonymousModel model, JsonNode generated) implements Executable {
        /** Attempts the structural inverse. */
        @Override
        public void execute() { model.restore(generated); }
    }
}
