package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Real candidate validation, remapping and SAT4J oracle parity regressions. */
class OracleParityEngineTest {
    /** Builds a complete draft with fresh client identities and an exact oracle envelope.
     * @param source candidate authored model
     * @param oracle exact reference model
     * @return request with a live predicate declaration selection
     * @throws Exception parsing failure
     */
    private ObjectNode request(String source, String oracle) throws Exception {
        JsonNode parsed = new SourceValidation(JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", source)).validate();
        ObjectNode module = parsed.path("module").deepCopy();
        String json = module.toString().replace("server:", "draft:");
        module = (ObjectNode) dev.allow.worker.JsonWire.decode(json.getBytes(java.nio.charset.StandardCharsets.UTF_8), JsonNode.class);
        ObjectNode request = JsonNodeFactory.instance.objectNode().put("scope", 2)
                .put("targetId", module.path("predicates").get(0).path("id").asText());
        ObjectNode candidate = request.putObject("candidate").put("mode", "BLOCK_SUPPORTED");
        candidate.set("module", module); candidate.putArray("presentationCopies");
        request.putObject("oracle").put("source", oracle).put("sourceHash", Hashes.text(oracle)).put("predicate", "Q");
        return request;
    }

    /** Creates an exact empty authorized base for independent DocumentEngine validation.
     * @return valid text-only artifact
     */
    private ObjectNode base() {
        ObjectNode base = JsonNodeFactory.instance.objectNode().put("mode", "TEXT_ONLY").put("source", "").put("sourceHash", Hashes.text(""));
        base.putNull("module"); base.putArray("occurrences"); base.putArray("trivia");
        return base;
    }

    /** Runs the actual owned-worker comparison implementation in the test JVM.
     * @param request exact draft and reference intent
     * @return complete validated categories
     * @throws Exception validation, parsing or solver failure
     */
    private JsonNode run(JsonNode request) throws Exception {
        return new ComparisonEngine().execute("ORACLE_PARITY", request, base(), JsonNodeFactory.instance.objectNode(), "test");
    }

    /** Identical predicates give nonvacuous bounded agreement after fresh target-ID remapping.
     * @throws Exception validation or solver failure
     */
    @Test void identicalFreshTarget() throws Exception {
        ObjectNode request = request("sig A {} pred P { some A }", "sig A {} pred Q { some A }");
        assertTrue(request.path("targetId").asText().startsWith("draft:"));
        JsonNode result = run(request);
        assertEquals(request.path("targetId"), result.path("targetId"));
        assertEquals("AGREEMENT", result.path("classification").asText());
        assertEquals("UNSAT", result.path("categories").path("leftOnly").path("status").asText());
        assertEquals("UNSAT", result.path("categories").path("rightOnly").path("status").asText());
        assertEquals("SAT", result.path("categories").path("both").path("status").asText());
        assertEquals("P", result.path("left").path("predicate").asText());
        assertEquals(request.path("oracle").path("sourceHash"), result.path("oracle").path("sourceHash"));
    }

    /** Opposing parameterized predicates replay opposing values on a shared assignment.
     * @throws Exception solver failure
     */
    @Test void oppositeSharedParameters() throws Exception {
        JsonNode result = run(request("sig A {} pred P[x: set A] { some x }", "sig A {} pred Q[y: set A] { no y }"));
        assertEquals("DISTINGUISHED", result.path("classification").asText());
        JsonNode category = result.path("categories").path("leftOnly");
        assertEquals("SAT", category.path("status").asText());
        assertTrue(category.path("left").asBoolean()); assertFalse(category.path("right").asBoolean());
        assertEquals("x", category.path("assignment").get(0).path("leftName").asText());
        assertEquals("y", category.path("assignment").get(0).path("rightName").asText());
    }

    /** Contradictory retained facts cannot produce green evidence.
     * @throws Exception solver failure
     */
    @Test void vacuousBackground() throws Exception {
        JsonNode result = run(request("sig A {} fact F { some A and no A } pred P { some A }",
                "sig A {} fact F { some A and no A } pred Q { some A }"));
        assertEquals("NO_INSTANCES", result.path("classification").asText());
        for (JsonNode category : result.path("categories")) assertEquals("UNSAT", category.path("status").asText());
    }

    /** Body identities and predicate display names never substitute for declaration identities.
     * @throws Exception fixture parsing failure
     */
    @Test void rejectsNonDeclarationTarget() throws Exception {
        ObjectNode request = request("sig A {} pred P { some A }", "sig A {} pred Q { some A }");
        request.put("targetId", request.path("candidate").path("module").path("predicates").get(0).path("bodyId").asText());
        assertThrows(IllegalArgumentException.class, new Run(request)::run);
        request.put("targetId", "P");
        assertThrows(IllegalArgumentException.class, new Run(request)::run);
    }

    /** Incompatible background, parameter schemas and incomplete surroundings fail closed.
     * @throws Exception fixture parsing failure
     */
    @Test void rejectsUnsupportedContext() throws Exception {
        assertThrows(IllegalArgumentException.class, new Run(request("sig A {} pred P { some A }", "sig B {} pred Q { some B }"))::run);
        assertThrows(IllegalArgumentException.class, new Run(request("sig A {} pred P[x: set A] { some x }", "sig A {} pred Q { some A }"))::run);
        ObjectNode request = request("sig A {} pred P { some A }", "sig A {} pred Q { some A }");
        ((ObjectNode) request.path("candidate").path("module").path("nodes").get(0)).put("tag", "hole");
        assertThrows(DocumentValidationException.class, new Run(request)::run);
    }

    /** Named exception-check callback retaining one exact fixture. */
    private final class Run {
        private final JsonNode request;
        /** Captures one request.
         * @param request exact fixture
         */
        private Run(JsonNode request) { this.request = request; }
        /** Executes the parity implementation.
         * @throws Exception validation or solver failure
         */
        private void run() throws Exception { OracleParityEngineTest.this.run(request); }
    }
}
