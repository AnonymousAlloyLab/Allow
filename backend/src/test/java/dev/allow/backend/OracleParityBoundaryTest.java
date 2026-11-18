package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.document.ComparisonEngine;
import dev.allow.document.DocumentEngine;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Strict successful result and pre-admission request rejection regressions. */
class OracleParityBoundaryTest {
    /** Builds a valid independently parsed complete draft request.
     * @return exact bounded intent
     * @throws Exception source validation failure
     */
    private ObjectNode request() throws Exception {
        ObjectNode base = DocumentArtifacts.empty("policy", "dependency");
        ObjectNode source = JsonNodeFactory.instance.objectNode().put("mode", "SOURCE").put("source", "sig A {} pred P[x: set A] { some x }");
        JsonNode parsed = new DocumentEngine().validate(source, base, JsonNodeFactory.instance.objectNode(), "policy");
        JsonNode module = JsonWire.decode(parsed.path("module").toString().replace("server:", "draft:").getBytes(java.nio.charset.StandardCharsets.UTF_8), JsonNode.class);
        ObjectNode request = JsonNodeFactory.instance.objectNode().put("draftId", "00000000-0000-4000-8000-000000000002")
                .put("draftEpoch", 0).put("baseRevision", 0).put("artifactId", base.path("artifactId").asText()).put("scope", 2)
                .put("targetId", module.path("predicates").get(0).path("id").asText());
        ObjectNode candidate = request.putObject("candidate").put("mode", "BLOCK_SUPPORTED");
        candidate.set("module", module); candidate.putArray("presentationCopies");
        String oracle = "sig A {} pred Q[y: set A] { no y }";
        request.putObject("oracle").put("source", oracle).put("sourceHash", Hashes.text(oracle)).put("predicate", "Q");
        return request;
    }

    /** Real solver evidence passes, while substitutions and unknown fields fail publication.
     * @throws Exception fixture or solver failure
     */
    @Test void strictSuccessfulEvidence() throws Exception {
        ObjectNode request = request();
        ObjectNode result = (ObjectNode) new ComparisonEngine().execute("ORACLE_PARITY", request,
                DocumentArtifacts.empty("policy", "dependency"), JsonNodeFactory.instance.objectNode(), "policy");
        ComparisonResult.check(result, request, "ORACLE_PARITY");
        witnessNegatives(result, request);
        ObjectNode wrong = result.deepCopy().put("targetId", "P"); reject(wrong, request);
        wrong = result.deepCopy().put("bitwidth", "4"); reject(wrong, request);
        wrong = result.deepCopy().put("bitwidth", 4.9); reject(wrong, request);
        wrong = result.deepCopy().put("maxseq", "3"); reject(wrong, request);
        wrong = result.deepCopy(); ((ObjectNode) wrong.path("oracle")).put("sourceHash", "0".repeat(64)); reject(wrong, request);
        wrong = result.deepCopy().put("sourceHash", "0".repeat(64)); reject(wrong, request);
        wrong = result.deepCopy().put("classification", "AGREEMENT"); reject(wrong, request);
        wrong = result.deepCopy().put("extra", true); reject(wrong, request);
        wrong = result.deepCopy(); ((ObjectNode) wrong.path("correspondence")).put("extra", true); reject(wrong, request);
        wrong = result.deepCopy(); ((ObjectNode) wrong.path("categories").path("leftOnly").path("assignment").get(0)).put("leftName", "substituted");
        reject(wrong, request);
        wrong = result.deepCopy(); ((ObjectNode) wrong.path("categories")).remove("both"); reject(wrong, request);
    }

    /** Rejects malformed witness metadata and nested state or relation projections.
     * @param result valid owned-worker result
     * @param request exact original intent
     */
    private void witnessNegatives(ObjectNode result, JsonNode request) {
        ObjectNode wrong = result.deepCopy();
        ObjectNode witness = (ObjectNode) wrong.path("categories").path("leftOnly").path("witness");
        witness.put("traceLength", "garbage"); reject(wrong, request);
        wrong = result.deepCopy(); witness = (ObjectNode) wrong.path("categories").path("leftOnly").path("witness");
        witness.putObject("loopState"); reject(wrong, request);
        wrong = result.deepCopy(); witness = (ObjectNode) wrong.path("categories").path("leftOnly").path("witness");
        witness.putArray("states").addObject().put("unexpected", true); reject(wrong, request);
        wrong = result.deepCopy().put("bitwidth", 4294967300L); reject(wrong, request);
    }

    /** Rejects one malformed successful result.
     * @param result altered worker response
     * @param request original exact request
     */
    private void reject(JsonNode result, JsonNode request) { assertThrows(IOException.class, new Check(result, request)::run); }

    /** Closed body, exact hashes and complete block mode are required before store reads.
     * @throws Exception fixture failure
     */
    @Test void malformedBodyRejectedBeforeAdmission() throws Exception {
        ObjectNode request = request();
        ObjectNode wrong = request.deepCopy().put("extra", true); rejectBody(wrong);
        wrong = request.deepCopy(); ((ObjectNode) wrong.path("oracle")).put("extra", true); rejectBody(wrong);
        wrong = request.deepCopy(); ((ObjectNode) wrong.path("oracle")).put("sourceHash", "0".repeat(64)); rejectBody(wrong);
        wrong = request.deepCopy(); ((ObjectNode) wrong.path("candidate")).put("mode", "SOURCE"); rejectBody(wrong);
        wrong = request.deepCopy().put("scope", 6); rejectBody(wrong);
        wrong = request.deepCopy().put("targetId", ""); rejectBody(wrong);
    }

    /** Proves malformed public requests cannot reach context reads or worker admission.
     * @param request malformed exact intent
     * @throws Exception encoding failure
     */
    private void rejectBody(JsonNode request) throws Exception {
        DocumentGateway gateway = mock(DocumentGateway.class);
        DocumentRuntime runtime = mock(DocumentRuntime.class);
        DocumentComparison operation = new DocumentComparison(gateway, runtime);
        assertThrows(IllegalArgumentException.class, new Execute(operation, JsonWire.encode(request))::run);
        verifyNoInteractions(gateway, runtime);
    }

    /** Named exact successful-result checker callback. */
    private record Check(JsonNode result, JsonNode request) {
        /** Checks the original parity envelope.
         * @throws IOException malformed evidence
         */
        private void run() throws IOException { ComparisonResult.check(result, request, "ORACLE_PARITY"); }
    }

    /** Named exact public-request callback. */
    private record Execute(DocumentComparison operation, byte[] bytes) {
        /** Executes public admission validation.
         * @throws Exception rejected request or unavailable backend
         */
        private void run() throws Exception { operation.execute("server:00000000-0000-4000-8000-000000000001", bytes, "ORACLE_PARITY"); }
    }
}
