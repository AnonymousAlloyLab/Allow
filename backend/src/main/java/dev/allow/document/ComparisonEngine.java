package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import edu.mit.csail.sdg.alloy4.Err;
import java.io.IOException;
import java.util.*;

/** Worker-only comparison entry point; no result grants document mutation authority. */
public final class ComparisonEngine {
    /** Creates one independent comparison engine. */
    public ComparisonEngine() {}

    /** Dispatches only the strict owned comparison operation inside the child.
     * @param operation trusted operation selection
     * @param request checked public intent
     * @param base exact authorized artifact
     * @param inventory scoped historical identity kinds
     * @param policy installed policy identity
     * @return complete comparison or inspection result
     * @throws DocumentValidationException invalid candidate
     * @throws IOException isolated infrastructure failure
     * @throws Err invalid or unsupported authored source
     * @throws IllegalArgumentException incomplete model
     */
    public JsonNode execute(String operation, JsonNode request, JsonNode base, JsonNode inventory, String policy)
            throws DocumentValidationException, IOException, Err {
        if (operation.equals("COMPARISON_MODEL")) return ComparisonModels.inspect(request.path("source").asText(), request.path("sourceHash").asText());
        if (operation.equals("COMPARE_MODELS")) return files(request);
        JsonNode checked = new DocumentEngine().validate(request.path("candidate"), base, inventory, policy);
        if (!checked.path("mode").asText().equals("BLOCK_SUPPORTED")) throw new IllegalArgumentException("Complete block model required");
        if (operation.equals("ORACLE_PARITY")) return oracle(request, checked);
        Map<String, String> inverse = inverse(checked.path("idRemapping"));
        String left = remap(request.path("leftId").asText(), checked.path("idRemapping"));
        String right = remap(request.path("rightId").asText(), checked.path("idRemapping"));
        ObjectNode result = compare(checked.path("module"), left, right, request.path("scope").intValue(), inverse);
        result.put("sourceHash", checked.path("sourceHash").asText());
        result.put("leftId", request.path("leftId").asText()).put("rightId", request.path("rightId").asText());
        return result;
    }

    /** Resolves only a validated predicate declaration before reusing paired-source comparison.
     * @param request exact candidate and oracle intent
     * @param checked independently validated complete candidate
     * @return four outcomes bound to the original target and oracle
     * @throws IOException isolated parser failure
     * @throws Err rejected synthesized source
     * @throws IllegalArgumentException target is not a predicate declaration
     */
    private ObjectNode oracle(JsonNode request, JsonNode checked) throws IOException, Err {
        String target = remap(request.path("targetId").asText(), checked.path("idRemapping"));
        String name = predicateName(checked.path("module"), target);
        ObjectNode pair = JsonNodeFactory.instance.objectNode();
        pair.set("scope", request.path("scope"));
        pair.putObject("left").put("source", checked.path("source").asText())
                .put("sourceHash", checked.path("sourceHash").asText()).put("predicate", name);
        pair.set("right", request.path("oracle"));
        ObjectNode result = files(pair);
        result.put("targetId", request.path("targetId").asText());
        result.set("oracle", selection(request.path("oracle")));
        return result;
    }

    /** Finds a selected declaration without accepting a body expression or arbitrary name.
     * @param module checked complete module
     * @param id independently remapped declaration identity
     * @return validated authored predicate name
     * @throws IllegalArgumentException identity does not name a predicate declaration
     */
    private String predicateName(JsonNode module, String id) {
        for (JsonNode predicate : module.path("predicates"))
            if (id.equals(predicate.path("id").asText())) return predicate.path("name").asText();
        throw new IllegalArgumentException("Selected target must be a predicate declaration");
    }

    /** Prepares two independently parsed files through the conservative checked context matcher.
     * @param request exact paired file selection
     * @return four-category result plus explicit correspondence
     * @throws IOException isolated parser or encoding failure
     * @throws Err Alloy source rejection
     */
    private ObjectNode files(JsonNode request) throws IOException, Err {
        JsonNode left = request.path("left"), right = request.path("right");
        ComparisonModels.Prepared prepared = ComparisonModels.prepare(left.path("source").asText(), left.path("sourceHash").asText(),
                left.path("predicate").asText(), right.path("source").asText(), right.path("sourceHash").asText(), right.path("predicate").asText());
        ObjectNode result = compare(prepared.module(), prepared.leftArmId(), prepared.rightArmId(), request.path("scope").intValue(), Map.of());
        result.set("correspondence", prepared.correspondence());
        labelAssignments(result, prepared.correspondence());
        result.set("left", selection(left)); result.set("right", selection(right));
        result.put("sourceHash", Hashes.text(left.path("sourceHash").asText() + ":" + right.path("sourceHash").asText()));
        return result;
    }

    /** Labels shared wrapper assignments with both original uploaded parameter names.
     * @param result complete checked comparison evidence
     * @param correspondence independently checked parameter map
     */
    private void labelAssignments(JsonNode result, JsonNode correspondence) {
        for (JsonNode category : result.path("categories")) for (JsonNode assignment : category.path("assignment")) {
            for (JsonNode parameter : correspondence.path("parameters")) {
                if (!assignment.path("id").equals(parameter.path("sharedId"))) continue;
                ((ObjectNode) assignment).put("name", parameter.path("leftName").asText())
                        .put("leftName", parameter.path("leftName").asText()).put("rightName", parameter.path("rightName").asText());
            }
        }
    }

    /** Returns source identity without reflecting uploaded source text in responses.
     * @param side exact file selection
     * @return public bounded selected source identity
     */
    private ObjectNode selection(JsonNode side) {
        return JsonNodeFactory.instance.objectNode().put("sourceHash", side.path("sourceHash").asText()).put("predicate", side.path("predicate").asText());
    }

    /** Checks and solves a prepared complete module under the common explicit bounds.
     * @param module validated complete forest
     * @param left first formula identity
     * @param right second formula identity
     * @param scope uniform scope
     * @param inverse checked-to-original binder identity map
     * @return complete bounded evidence
     * @throws IOException isolated parser/serialization failure
     * @throws Err synthesis or solver rejection
     * @throws IllegalArgumentException scope outside policy
     * @throws IllegalStateException solver or replay failure
     */
    private ObjectNode compare(JsonNode module, String left, String right, int scope, Map<String, String> inverse) throws IOException, Err {
        if (scope < 1 || scope > 5) throw new IllegalArgumentException("Comparison scope must be 1 through 5");
        ComparisonSolver solver = new ComparisonSolver(module, left, right, scope, inverse);
        ObjectNode result;
        try { result = solver.solve(); }
        catch (Err | IllegalArgumentException failure) { throw new IllegalStateException("Comparison solver or replay failure", failure); }
        result.put("moduleHash", Hashes.bytes(JsonWire.encode(module))).put("scope", scope).put("bitwidth", 4).put("maxseq", 3);
        return result;
    }

    /** Restores authored identities for free-variable evidence labels.
     * @param mapping checked worker remapping
     * @return independent inverse map
     */
    private Map<String, String> inverse(JsonNode mapping) {
        Map<String, String> result = new HashMap<>();
        var fields = mapping.fields();
        while (fields.hasNext()) { var field = fields.next(); result.put(field.getValue().asText(), field.getKey()); }
        return result;
    }

    /** Resolves a selected draft identity after independent validation remaps it.
     * @param id original selected node
     * @param mapping checked identity map
     * @return validated live identity
     */
    private String remap(String id, JsonNode mapping) { return mapping.path(id).asText(id); }
}
