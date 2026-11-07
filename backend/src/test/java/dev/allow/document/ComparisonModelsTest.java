package dev.allow.document;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

/** Real parser and checked-module tests for uploaded predicate comparison. */
class ComparisonModelsTest {
    private static final String A = "sig A {}\npred helper[x: set A] { some x }\npred left[y: set A] { helper[y] }\nfact f { some A }\n";
    private static final String B = "sig A {}\npred helper[x: set A] { some x }\npred right[z: set A] { no z }\nfact f { some A }\n";
    /** Prepares a model pair.
     * @param a first source
     * @param b second source
     * @return prepared comparison
     * @throws Exception failed parsing
     */
    private ComparisonModels.Prepared prepare(String a, String b) throws Exception {
        return ComparisonModels.prepare(a, ArtifactIntegrity.hash(a), "left", b, ArtifactIntegrity.hash(b), "right");
    }
    /** Parses differing names into shared-call arms.
     * @throws Exception failure
     */
    @Test void compatibleModels() throws Exception {
        assertEquals("left", ComparisonModels.inspect(A, ArtifactIntegrity.hash(A)).path("predicates").get(1).path("name").asText());
        String renamed = B.replace("helper[x: set A] { some x }", "helper[w: set A] { some w }");
        var value = prepare(A + "run left for 3\n", renamed + "run right for 4\n");
        assertNotEquals(value.leftArmId(), value.rightArmId());
        assertTrue(value.correspondence().path("parameters").get(0).path("sharedId").asText().startsWith("server:"));
        assertEquals("y", value.correspondence().path("parameters").get(0).path("leftName").asText());
        assertEquals("z", value.correspondence().path("parameters").get(0).path("rightName").asText());
    }
    /** Rejects incompatible backgrounds, selected dependencies and unsupported source. */
    @Test void rejectsUnsafeModels() {
        assertThrows(IllegalArgumentException.class, this::helperMismatch);
        assertThrows(IllegalArgumentException.class, this::multiplicityMismatch);
        assertThrows(IllegalArgumentException.class, this::dependencyMismatch);
        assertThrows(IllegalArgumentException.class, this::badSource);
        assertThrows(IllegalArgumentException.class, this::schemaMismatch);
    }
    /** Exercises helper mismatch.
     * @throws Exception expected denial
     */
    private void helperMismatch() throws Exception { prepare(A, B.replace("some x", "no x")); }
    /** Exercises multiplicity mismatch.
     * @throws Exception expected denial
     */
    private void multiplicityMismatch() throws Exception { prepare(A, B.replace("sig A", "one sig A")); }
    /** Exercises selected dependency denial.
     * @throws Exception expected denial
     */
    private void dependencyMismatch() throws Exception { prepare(A, B.replace("some A", "right[A]")); }
    /** Exercises parameter schema denial.
     * @throws Exception expected denial
     */
    private void schemaMismatch() throws Exception { prepare(A, B.replace("z: set A", "z: set A -> A")); }
    /** Exercises unsupported source denial.
     * @throws Exception expected denial
     */
    private void badSource() throws Exception { String source = "open util/ordering[A]"; ComparisonModels.inspect(source, ArtifactIntegrity.hash(source)); }
    /** Checks background facts and assertions independently. */
    @Test void rejectsChangedFormulas() {
        assertThrows(IllegalArgumentException.class, this::factMismatch);
        assertThrows(IllegalArgumentException.class, this::assertionMismatch);
    }
    /** Rejects changed fact content.
     * @throws Exception expected denial
     */
    private void factMismatch() throws Exception { prepare(A, B.replace("some A", "no A")); }
    /** Rejects changed assertion content.
     * @throws Exception expected denial
     */
    private void assertionMismatch() throws Exception {
        prepare(A + "assert checkA { some A }\n", B + "assert checkA { no A }\n");
    }
    /** Rejects a selected call through multiple retained helpers. */
    @Test void rejectsTransitiveDependency() {
        assertThrows(IllegalArgumentException.class, this::transitiveDependency);
    }
    /** Constructs a helper dependency chain.
     * @throws Exception expected denial
     */
    private void transitiveDependency() throws Exception {
        String a = "sig A {} pred left { some A } pred inner { left[] } pred outer { inner[] } fact f { outer[] }";
        String b = "sig A {} pred right { no A } pred inner { right[] } pred outer { inner[] } fact f { outer[] }";
        prepare(a, b);
    }
    /** Accepts alpha-renamed binders and rejects changed reference identities.
     * @throws Exception unexpected parser failure
     */
    @Test void nestedBindersUseIdentity() throws Exception {
        String a = "sig A {} fact f { all x: A | all y: A | x = y } pred left { some A }";
        String b = "sig A {} fact f { all u: A | all v: A | u = v } pred right { no A }";
        assertNotNull(prepare(a, b));
        assertThrows(IllegalArgumentException.class, this::changedBinderTarget);
    }
    /** Changes the identity used in a nested binder expression.
     * @throws Exception expected denial
     */
    private void changedBinderTarget() throws Exception {
        String a = "sig A {} fact f { all x: A | all y: A | x = y } pred left { some A }";
        String b = "sig A {} fact f { all u: A | all v: A | u = u } pred right { no A }";
        prepare(a, b);
    }
    /** Rejects positional schema reversal even at the same arity. */
    @Test void rejectsReorderedColumns() {
        assertThrows(IllegalArgumentException.class, this::reorderedColumns);
    }
    /** Constructs two different ordered product schemas.
     * @throws Exception expected denial
     */
    private void reorderedColumns() throws Exception {
        String a = "sig A {} sig B {} pred left[x: set A -> B] { some x }";
        String b = "sig A {} sig B {} pred right[y: set B -> A] { some y }";
        prepare(a, b);
    }
    /** Accepts equivalent declaration orders, identical selected names and zero parameters.
     * @throws Exception unexpected parser failure
     */
    @Test void supportsReorderingAndZeroParameters() throws Exception {
        String a = "sig A {} sig B {} pred common { some A } fact f { some B }";
        String b = "sig B {} sig A {} fact f { some B } pred common { no A }";
        var result = ComparisonModels.prepare(a, ArtifactIntegrity.hash(a), "common", b, ArtifactIntegrity.hash(b), "common");
        assertTrue(result.correspondence().path("parameters").isEmpty());
        assertEquals("common", result.correspondence().path("leftPredicate").asText());
        assertEquals("common", result.correspondence().path("rightPredicate").asText());
    }

}
