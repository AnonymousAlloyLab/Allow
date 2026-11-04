package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Base64;
import java.util.Set;

/** Gate-only exact frame and synthetic-context observations with explicit trust boundaries. */
final class WarmSemanticProtocol {
    /** Prevents construction of the stateless gate helper. */
    private WarmSemanticProtocol() {}

    /** Maps registered names to safe evidence basenames; the manifest separately checks uniqueness.
     * @param name original case-sensitive fixture identifier
     * @return lowercase private evidence basename
     */
    static String basename(String name) { return name.toLowerCase(java.util.Locale.ROOT).replace('_', '-'); }

    /** Constructs an explicitly assumed context without changing any production access boundary.
     * @param fixture unchanged decoded registered request
     * @return gate-created context, never a claimed SQL receipt
     * @throws Exception unavailable private gate reflection seam
     */
    static DocumentValidationContext context(JsonNode fixture) throws Exception {
        Constructor<DocumentValidationContext> type = DocumentValidationContext.class
                .getDeclaredConstructor(JsonNode.class, JsonNode.class);
        type.setAccessible(true);
        return type.newInstance(fixture.path("baseArtifact"), fixture.path("ownedIdInventory"));
    }

    /** Binds the unchanged fixture nonce and policy to this actual isolated pool incarnation.
     * @param fixture exact parsed private fixture
     * @param input original fixture bytes
     * @param build installed full executable identity
     * @param pool actual current pool incarnation
     * @return production-validated operation binding
     */
    static WarmRequestBinding binding(JsonNode fixture, byte[] input, String build, String pool) {
        return new WarmRequestBinding(fixture.path("requestId").textValue(), Hashes.bytes(input),
                "server:00000000-0000-0000-0000-000000000001", 0,
                fixture.path("policyVersion").textValue(), build, pool);
    }

    /** Creates only a gate-assumed permit; the actual production consumer still enforces one use.
     * @param binding actual isolated admission identity
     * @param context explicitly assumed private context
     * @return gate-only permit for finite entrypoint comparison
     * @throws Exception unavailable reflection seam
     */
    static WarmContextPermit permit(WarmRequestBinding binding, DocumentValidationContext context) throws Exception {
        Constructor<WarmContextPermit> type = WarmContextPermit.class
                .getDeclaredConstructor(WarmRequestBinding.class, DocumentValidationContext.class);
        type.setAccessible(true);
        return type.newInstance(binding, context);
    }

    /** Observes the actual production encoder and rejects any semantic adaptation of a valid fixture.
     * @param binding unchanged fixture nonce and policy bound to the isolated owner
     * @param fixture original parsed request
     * @param context explicitly assumed context
     * @param record private evidence receiving exact reconstructed-byte metadata
     * @throws Exception encoding rejection or changed request semantics
     */
    static void frame(WarmRequestBinding binding, JsonNode fixture, DocumentValidationContext context,
            ObjectNode record) throws Exception {
        Method encoder = WarmWorkerPool.class.getDeclaredMethod("frame", WarmRequestBinding.class,
                JsonNode.class, DocumentValidationContext.class);
        encoder.setAccessible(true);
        byte[] bytes = (byte[]) encoder.invoke(null, binding, fixture.path("candidate"), context);
        WarmProbeFiles.require(JsonWire.decode(bytes, JsonNode.class).equals(fixture), "Production frame changed fixture semantics");
        record.put("productionFrameSha256", Hashes.bytes(bytes)).put("productionFrameBytes", bytes.length)
                .put("productionFrameStrictJsonEqual", true);
    }

    /** Records the complete original response frame or explicitly identified pool reserialization.
     * @param fixture exact unchanged original request
     * @param bytes complete newline-terminated response representation
     * @param capture provenance of the retained bytes
     * @param record private finite result
     * @throws IOException malformed response, mismatched nonce or invalid framing
     */
    static void response(JsonNode fixture, byte[] bytes, String capture, ObjectNode record) throws IOException {
        WarmProbeFiles.require(bytes.length <= 1048577 && bytes.length > 1 && bytes[bytes.length - 1] == '\n',
                "Incomplete semantic response frame");
        for (int index = 0; index < bytes.length - 1; index++) {
            WarmProbeFiles.require(bytes[index] != '\n' && bytes[index] != '\r', "Multiple semantic response frames");
        }
        JsonNode response = DocumentJson.decode(bytes);
        DocumentJson.fields(response, "protocol", "requestId", "status", "data");
        WarmProbeFiles.require(response.path("protocol").isInt() && response.path("protocol").intValue() == 1
                && response.path("requestId").equals(fixture.path("requestId"))
                && Set.of("VALIDATED", "INVALID", "UNAVAILABLE").contains(response.path("status").asText()),
                "Semantic response identity mismatch");
        record.put("outcome", "COMPLETE_RESPONSE").put("requestIdentityMatches", true)
                .put("workerStatus", response.path("status").textValue()).put("responseCapture", capture)
                .put("responseBase64", Base64.getEncoder().encodeToString(bytes)).put("responseBytes", bytes.length)
                .put("responseSha256", Hashes.bytes(bytes));
    }

    /** Serializes every returned field without pretending that pool reserialization is raw stdout.
     * @param response complete actual cleaned pool result
     * @return compact complete response with one framing delimiter
     * @throws IOException unavailable JSON encoding
     */
    static byte[] framed(JsonNode response) throws IOException {
        byte[] encoded = JsonWire.encode(response);
        byte[] bytes = Arrays.copyOf(encoded, encoded.length + 1);
        bytes[bytes.length - 1] = '\n';
        return bytes;
    }

    /** Retains bounded private failure provenance without printing any model text to the console.
     * @param failure actual gate failure
     * @return private diagnostic object
     */
    static ObjectNode failure(Exception failure) {
        return WarmProbeFailures.describe(failure);
    }
}
