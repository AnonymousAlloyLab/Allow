package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import dev.allow.worker.Hashes;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Real Alloy/SAT4J partition tests, including shared relational and singleton assignments. */
class ComparisonSolverTest {
    /** Parses a supported complete model in the same worker-side adapter.
     * @param source authored fixture
     * @return checked module
     * @throws Exception parsing failure
     */
    private JsonNode module(String source) throws Exception {
        return new SourceValidation(JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", source)).validate().path("module");
    }

    /** Selects a unique fixture expression by its closed tag.
     * @param module checked fixture
     * @param tag expression tag
     * @return live formula identity
     * @throws AssertionError missing fixture expression
     */
    private String node(JsonNode module, String tag) {
        for (JsonNode node : module.path("nodes")) if (node.path("tag").asText().equals(tag)) return node.path("id").asText();
        throw new AssertionError("Missing fixture expression " + tag);
    }

    /** Solves the some/no subtrees with their exact shared environment.
     * @param source fixture source
     * @return complete category response
     * @throws Exception parse or solver failure
     */
    private JsonNode solve(String source) throws Exception {
        JsonNode module = module(source);
        return new ComparisonSolver(module, node(module, "some_test"), node(module, "no_test"), 2, Map.of()).solve();
    }

    /** Set-valued parameters share one assignment, including the empty relation.
     * @throws Exception solver failure
     */
    @Test void sharedSetParameter() throws Exception {
        JsonNode result = solve("sig A {} pred P[x: set A] { some x and no x }");
        assertEquals("UNSAT", result.path("categories").path("both").path("status").asText());
        assertEquals("UNSAT", result.path("categories").path("neither").path("status").asText());
        assertEquals("SAT", result.path("categories").path("leftOnly").path("status").asText());
        assertEquals("SAT", result.path("categories").path("rightOnly").path("status").asText());
        assertEquals("x", result.path("categories").path("leftOnly").path("assignment").get(0).path("name").asText());
        assertFalse(result.path("categories").path("leftOnly").path("assignment").get(0).path("tuples").isEmpty());
        assertTrue(result.path("categories").path("rightOnly").path("assignment").get(0).path("tuples").isEmpty());
    }

    /** Distinct lexical identities denote independent variables and realize every category.
     * @throws Exception solver failure
     */
    @Test void distinctBinders() throws Exception {
        JsonNode result = solve("sig A {} pred P[x: set A] { some x } pred Q[y: set A] { no y }");
        for (JsonNode category : result.path("categories")) {
            assertEquals("SAT", category.path("status").asText());
            assertEquals(2, category.path("assignment").size());
            assertNotEquals(category.path("assignment").get(0).path("id"), category.path("assignment").get(1).path("id"));
        }
    }

    /** Synthesis keeps distinct identities independent even when their display names coincide.
     * @throws Exception parsing failure
     */
    @Test void sameNameIdentitySynthesis() throws Exception {
        assertTrue(module("sig A {} pred P[x: set A] { some x } pred Q[x: set A] { no x }").isNull());
        JsonNode module = module("sig A {} pred P[x: set A] { some x } pred Q[y: set A] { no y }");
        ((com.fasterxml.jackson.databind.node.ObjectNode) module.path("predicates").get(1).path("parameters").get(0)).put("name", "x");
        ComparisonSyntax syntax = new ComparisonSyntax(module);
        String source = syntax.source(node(module, "some_test"), node(module, "no_test"), 2);
        assertEquals(2, syntax.variables().size());
        assertNotEquals(syntax.variableNames().get(0), syntax.variableNames().get(1));
        assertEquals(4, SourceParser.parse(source).getAllCommands().size());
    }

    /** Ancestor/internal and descendant/free uses of one binder retain correct lexical scope.
     * @throws Exception solver failure
     */
    @Test void ancestorAndDescendantArms() throws Exception {
        JsonNode module = module("sig A {} pred P { all x: A | some x }");
        JsonNode result = new ComparisonSolver(module, node(module, "all_quant"), node(module, "some_test"), 2, Map.of()).solve();
        assertEquals("SAT", result.path("categories").path("both").path("status").asText());
        assertEquals("UNSAT", result.path("categories").path("rightOnly").path("status").asText());
        assertEquals(1, result.path("categories").path("both").path("assignment").get(0).path("tuples").size());
    }

    /** Existential ancestors do not create ambiguous skolems for descendant free binders.
     * @throws Exception solver failure
     */
    @Test void existentialAncestorAndDescendantArms() throws Exception {
        JsonNode module = module("sig A {} pred P { some x: A | some x }");
        JsonNode result = new ComparisonSolver(module, node(module, "some_quant"), node(module, "some_test"), 2, Map.of()).solve();
        assertEquals("SAT", result.path("categories").path("both").path("status").asText());
        assertEquals("UNSAT", result.path("categories").path("rightOnly").path("status").asText());
        assertEquals(1, result.path("categories").path("both").path("assignment").get(0).path("tuples").size());
    }

    /** Preserved existential facts and helper calls cannot alias joint assignment skolems.
     * @throws Exception solver failure
     */
    @Test void preservedFactExistentialsHaveSeparateNames() throws Exception {
        String[] sources = {"sig A {} fact F { some x: A | some x }",
                "sig A {} pred P { some x: A | some x } fact F { P }"};
        for (String source : sources) {
            JsonNode module = module(source);
            JsonNode result = new ComparisonSolver(module, node(module, "some_quant"), node(module, "some_test"), 2, Map.of()).solve();
            assertEquals("AGREEMENT", result.path("classification").asText());
            assertEquals("SAT", result.path("categories").path("both").path("status").asText());
            assertEquals(1, result.path("categories").path("both").path("assignment").get(0).path("tuples").size());
        }
    }

    /** Product-valued parameters retain every ordered schema column.
     * @throws Exception solver failure
     */
    @Test void sharedProductParameter() throws Exception {
        JsonNode result = solve("sig A {} pred P[x: set A -> A] { some x and no x }");
        JsonNode binding = result.path("categories").path("leftOnly").path("assignment").get(0);
        assertEquals(2, binding.path("columns").size());
        assertEquals(2, binding.path("tuples").get(0).size());
        assertEquals("DISTINGUISHED", result.path("classification").asText());
    }

    /** Captured atom quantifiers cannot become empty or multi-atom sets.
     * @throws Exception solver failure
     */
    @Test void singletonAndEmptyDomain() throws Exception {
        String source = "sig A {} pred P { all x: A | some x and no x }";
        JsonNode result = solve(source);
        assertEquals("SAT", result.path("categories").path("leftOnly").path("status").asText());
        assertEquals("UNSAT", result.path("categories").path("rightOnly").path("status").asText());
        assertEquals(1, result.path("categories").path("leftOnly").path("assignment").get(0).path("tuples").size());
        assertEquals("NO_INSTANCES", solve(source + " fact empty { no A }").path("classification").asText());
    }

    /** Original fact owners are preserved and zero free variables replay successfully.
     * @throws Exception solver failure
     */
    @Test void factsAndIdenticalArms() throws Exception {
        JsonNode result = solve("sig A {} fact owner { some A } pred P { no A }");
        assertEquals("UNSAT", result.path("categories").path("rightOnly").path("status").asText());
        JsonNode module = module("sig A {} pred P { some A }");
        String arm = node(module, "some_test");
        JsonNode same = new ComparisonSolver(module, arm, arm, 2, Map.of()).solve();
        assertEquals("AGREEMENT", same.path("classification").asText());
        assertEquals("UNSAT", same.path("categories").path("leftOnly").path("status").asText());
    }

    /** Independently parsed files run through preparation, common parameters and real solving.
     * @throws Exception solver failure
     */
    @Test void fileComparison() throws Exception {
        String left = "sig A {} pred left[x: set A] { some x }", right = "sig A {} pred right[y: set A] { no y }";
        var request = JsonNodeFactory.instance.objectNode().put("scope", 2);
        request.putObject("left").put("source", left).put("sourceHash", Hashes.text(left)).put("predicate", "left");
        request.putObject("right").put("source", right).put("sourceHash", Hashes.text(right)).put("predicate", "right");
        JsonNode result = new ComparisonEngine().execute("COMPARE_MODELS", request, null, null, "test");
        assertEquals("DISTINGUISHED", result.path("classification").asText());
        assertEquals(1, result.path("correspondence").path("parameters").size());
    }
}
