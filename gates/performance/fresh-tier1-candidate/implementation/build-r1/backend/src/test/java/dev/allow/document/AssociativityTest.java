package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Exercises ordered boolean reconstruction against the real Alloy parser. */
final class AssociativityTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * The registered 500-node witness survives both block and source validation.
     * @throws Exception if reading, parsing or validation fails
     */
    @Test
    void registeredWitnessRoundTrips() throws Exception {
        JsonNode fixture = MAPPER.readTree(Path.of("..", "gates", "document", "headless-preview-fixture.json").toFile());
        JsonNode module = fixture.path("module");
        assertEquals(500, module.path("nodes").size());
        new ModuleChecker(module).check();
        String source = fixture.path("source").asText();
        EngineData.roundTrip(module, source);
        checkBlockAndHistory(module);
        ObjectNode request = MAPPER.createObjectNode().put("mode", "SOURCE").put("source", "// 😀\r\n" + source.replace("\n", "\r\n"));
        JsonNode result = new SourceValidation(request).validate();
        assertEquals("BLOCK_SUPPORTED", result.path("mode").asText());
        assertEquals(request.path("source"), result.path("source"));
        assertEquals(500, result.path("module").path("nodes").size());
        assertFalse(result.path("occurrences").isEmpty());
        new ArtifactIntegrity(result).check();
    }

    /**
     * Exercises block acceptance and same-content history for the witness.
     * @param module registered checked module
     * @throws Exception if validation fails
     */
    private void checkBlockAndHistory(JsonNode module) throws Exception {
        ObjectNode inventory = MAPPER.createObjectNode();
        for (String key : new String[] {"signatures", "fields", "predicates", "facts", "assertions", "commands", "nodes"}) {
            for (JsonNode item : module.path(key)) {
                String kind = key.equals("nodes") ? "expression" : key.equals("commands") ? "command" : item.path("tag").asText();
                inventory.put(item.path("id").asText(), kind);
            }
        }
        ObjectNode base = MAPPER.createObjectNode().put("mode", "TEXT_ONLY").put("source", "")
            .put("sourceHash", ArtifactIntegrity.hash(""));
        base.putNull("module");
        base.putArray("occurrences");
        base.putArray("trivia");
        ObjectNode blockRequest = MAPPER.createObjectNode().put("mode", "BLOCK_SUPPORTED");
        blockRequest.set("module", module);
        blockRequest.putArray("presentationCopies");
        JsonNode block = new BlockValidation(blockRequest, base, inventory).validate();
        assertTrue(new ModuleEquivalence(module, block.path("module")).matches());
        for (JsonNode node : block.path("module").path("nodes")) inventory.put(node.path("id").asText(), "expression");
        new ArtifactIntegrity(block).check();
        JsonNode history = new HistoryValidation(block, inventory).revalidate();
        for (String key : new String[] {"source", "sourceHash", "module", "occurrences", "trivia"}) {
            assertEquals(block.path(key), history.path(key));
        }
    }

    /**
     * Associative comparison preserves sequence, operators and scope boundaries.
     * @throws Exception if parsing fails
     */
    @Test
    void rejectsChangedOrderedOperandsAndOperators() throws Exception {
        JsonNode original = read("some A and some B and no A");
        assertTrue(new ModuleEquivalence(original, read("some A and (some B and no A)")).matches());
        for (String altered : new String[] {"some B and some A and no A", "some A and no A",
                "some A and some B and some B and no A", "some A or some B or no A",
                "some A and (some B or no A)", "some A implies (some B and no A)"}) {
            assertFalse(new ModuleEquivalence(original, read(altered)).matches(), altered);
        }
    }

    /**
     * Public source output still enforces the depth and node limits.
     * @throws Exception if parsing fails
     */
    @Test
    void rejectsPublicDepthAndNodeOverflow() throws Exception {
        String deep = "not (".repeat(33) + "some A" + ")".repeat(33);
        assertEquals("TEXT_ONLY", sourceMode(deep));
        String many = String.join(" and ", java.util.Collections.nCopies(172, "some A"));
        assertEquals("TEXT_ONLY", sourceMode(many));
    }

    /**
     * Runs supported-fragment classification for an authored body.
     * @param body expression body
     * @return resulting support mode
     * @throws Exception if parsing fails
     */
    private String sourceMode(String body) throws Exception {
        String source = "sig A {} pred p { " + body + " } run p for 3 but 4 Int, 3 seq";
        return new SourceValidation(MAPPER.createObjectNode().put("mode", "SOURCE").put("source", source))
            .validate().path("mode").asText();
    }

    /**
     * Checks the largest transient unary chain on the worker stack profile.
     * @throws Exception if the fixture cannot be read
     */
    @Test
    void transientDepthIsStackSafe() throws Exception {
        ObjectNode module = (ObjectNode) MAPPER.readTree(Path.of("..", "gates", "document", "headless-preview-fixture.json").toFile()).path("module");
        var nodes = module.putArray("nodes");
        String previous = "draft:00000000-0000-4000-8000-000000000001";
        nodes.addObject().put("tag", "signature_ref").put("id", previous).put("targetId", module.path("signatures").get(0).path("id").asText());
        for (int i = 2; i <= 512; i++) {
            String id = String.format("draft:00000000-0000-4000-8000-%012x", i);
            nodes.addObject().put("tag", i == 2 ? "some_test" : "not").put("id", id).put("operandId", previous);
            previous = id;
        }
        ((ObjectNode) module.path("predicates").get(0)).put("bodyId", previous);
        assertDoesNotThrow(new ModuleChecker(module, 512)::check);
        assertThrows(IllegalArgumentException.class, new ModuleChecker(module)::check);
    }

    /**
     * Parses one complete module using independent nominal checking.
     * @param body predicate expression
     * @return reconstructed module
     * @throws Exception if parsing fails
     */
    private JsonNode read(String body) throws Exception {
        String source = "sig A {} sig B {} pred p { " + body + " } run p for 3 but 4 Int, 3 seq";
        return new AlloyModuleReader(SourceParser.parse(source), false).read(1);
    }
}
