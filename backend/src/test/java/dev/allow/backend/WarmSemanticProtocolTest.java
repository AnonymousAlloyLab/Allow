package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Finite gate-oracle checks; these establish no worker, SQL or cgroup acceptance. */
final class WarmSemanticProtocolTest {
    /** Preserves the fixed request nonce and every semantic field through the actual pool encoder.
     * @throws Exception unexpected production encoding or identity failure
     */
    @Test
    void preservesExactFrameSemantics() throws Exception {
        ObjectNode fixture = fixture();
        ObjectNode record = JsonNodeFactory.instance.objectNode();
        WarmSemanticProtocol.frame(binding(fixture), fixture, WarmSemanticProtocol.context(fixture), record);
        assertTrue(record.path("productionFrameStrictJsonEqual").booleanValue());
        assertEquals(JsonWire.encode(fixture).length, record.path("productionFrameBytes").intValue());
    }

    /** Refuses to silently discard an unrepresentable field from the original frozen request.
     * @throws Exception unexpected fixture setup failure
     */
    @Test
    void rejectsAdaptedFixtureShape() throws Exception {
        ObjectNode fixture = fixture().put("unrepresentable", true);
        try {
            WarmSemanticProtocol.frame(binding(fixture), fixture, WarmSemanticProtocol.context(fixture),
                    JsonNodeFactory.instance.objectNode());
            fail("Unexpected semantic adaptation");
        } catch (IOException expected) { assertEquals("Production frame changed fixture semantics", expected.getMessage()); }
    }

    /** Keeps the blank-policy corpus row outside production binding authority.
     * @throws Exception unexpected fixture setup failure
     */
    @Test
    void rejectsBlankInstalledPolicy() throws Exception {
        ObjectNode fixture = fixture().put("policyVersion", "");
        try { binding(fixture); fail("Blank policy unexpectedly bound"); }
        catch (IllegalArgumentException expected) { assertNotNull(expected.getMessage()); }
    }

    /** Distinguishes the legal payload boundary from the exact production encoder rejection.
     * @throws Exception unexpected boundary construction or production behavior
     */
    @Test
    void checksExactPayloadBoundary() throws Exception {
        ObjectNode fixture = padded(2097151);
        ObjectNode record = JsonNodeFactory.instance.objectNode();
        WarmSemanticProtocol.frame(binding(fixture), fixture, WarmSemanticProtocol.context(fixture), record);
        assertEquals(2097151, record.path("productionFrameBytes").intValue());
        fixture = padded(2097152);
        try {
            WarmSemanticProtocol.frame(binding(fixture), fixture, WarmSemanticProtocol.context(fixture), record);
            fail("Exclusive payload cap accepted");
        } catch (InvocationTargetException expected) {
            assertInstanceOf(IOException.class, expected.getCause());
            assertEquals("Internal validation context exceeds limit", expected.getCause().getMessage());
        }
    }

    /** Labels complete pool reserialization explicitly while keeping the original nonce checked.
     * @throws Exception unexpected response encoding or identity behavior
     */
    @Test
    void preservesResponseProvenanceAndNonce() throws Exception {
        ObjectNode fixture = fixture();
        ObjectNode response = JsonNodeFactory.instance.objectNode().put("protocol", 1)
                .put("requestId", fixture.path("requestId").textValue()).put("status", "UNAVAILABLE");
        response.putObject("data");
        byte[] bytes = WarmSemanticProtocol.framed(response);
        ObjectNode record = JsonNodeFactory.instance.objectNode();
        WarmSemanticProtocol.response(fixture, bytes, "RESERIALIZED_COMPLETE_POOL_RESPONSE", record);
        assertEquals("RESERIALIZED_COMPLETE_POOL_RESPONSE", record.path("responseCapture").textValue());
        assertEquals(bytes.length, record.path("responseBytes").intValue());
        response.put("requestId", "00000000-0000-0000-0000-000000000099");
        try {
            WarmSemanticProtocol.response(fixture, WarmSemanticProtocol.framed(response), "ACTUAL_STDOUT_FRAME", record);
            fail("Substituted response nonce accepted");
        } catch (IOException expected) { assertEquals("Semantic response identity mismatch", expected.getMessage()); }
    }

    /** Constructs one fixed public test request without any server context claim.
     * @return exact private protocol shape
     */
    private static ObjectNode fixture() {
        ObjectNode value = JsonNodeFactory.instance.objectNode().put("protocol", 1)
                .put("requestId", "00000000-0000-0000-0000-000000000001")
                .put("policyVersion", "document-v1").put("operation", "VALIDATE");
        value.putObject("candidate").put("mode", "SOURCE").put("source", "sig A {}");
        value.putNull("baseArtifact");
        value.putObject("ownedIdInventory");
        return value;
    }

    /** Pads inside a deliberately unrecognized candidate field to reach an exact byte boundary.
     * @param length desired encoded payload length without framing delimiter
     * @return fixed-nonce exact-length request
     * @throws IOException failed fixture encoding
     */
    private static ObjectNode padded(int length) throws IOException {
        ObjectNode value = fixture();
        ObjectNode candidate = (ObjectNode) value.path("candidate");
        candidate.put("padding", "");
        candidate.put("padding", "x".repeat(length - JsonWire.encode(value).length));
        assertEquals(length, JsonWire.encode(value).length);
        return value;
    }

    /** Constructs the same strict gate binding used by the finite runner.
     * @param fixture fixed test protocol request
     * @return validated production binding
     * @throws IOException failed request encoding
     */
    private static WarmRequestBinding binding(ObjectNode fixture) throws IOException {
        return WarmSemanticProtocol.binding(fixture, JsonWire.encode(fixture), "1".repeat(64),
                "00000000-0000-0000-0000-000000000002");
    }
}
