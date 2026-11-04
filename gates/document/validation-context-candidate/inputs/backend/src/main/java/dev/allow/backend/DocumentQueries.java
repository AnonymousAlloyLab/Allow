package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.dto.JobRequest;
import dev.allow.dto.JobView;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;

/** Authorized reads, advisory previews and accepted-revision solver selection. */
@Service
final class DocumentQueries {
    private final DocumentGateway gateway;
    private final DocumentRuntime runtime;
    private final JobService jobs;
    private final Map<String, JsonNode> analyses = new LinkedHashMap<>();

    /** Connects operation-only persistence, current policy and the bounded solver supervisor.
     * @param gateway scoped private store
     * @param runtime exclusive local incarnation
     * @param jobs existing isolated solver jobs
     */
    DocumentQueries(DocumentGateway gateway, DocumentRuntime runtime, JobService jobs) {
        this.gateway = gateway;
        this.runtime = runtime;
        this.jobs = jobs;
    }

    /** Lists bounded document summaries without model content.
     * @return authorized summaries
     * @throws IOException store unavailable
     * @throws InterruptedException interrupted private bridge
     */
    byte[] list() throws IOException, InterruptedException {
        return reply("OK", data("list", JsonNodeFactory.instance.objectNode()));
    }

    /** Reads a current head or immutable historical artifact in its revision envelope.
     * @param document authorized document identifier
     * @param revision historical target, or null for head
     * @return exact source and artifact-bound projection
     * @throws IOException missing or unavailable artifact
     * @throws InterruptedException interrupted private bridge
     */
    byte[] read(String document, Long revision) throws IOException, InterruptedException {
        ObjectNode result = (ObjectNode) readData(document, revision);
        result.set("revision", result.get("requestedRevision"));
        result.remove("requestedRevision");
        return reply("OK", result);
    }

    /** Obtains one scoped historical snapshot without allowing browser-selected scope.
     * @param document document identity
     * @param revision nullable historical revision
     * @return private read response
     * @throws IOException missing or unavailable snapshot
     * @throws InterruptedException interrupted store call
     */
    private JsonNode readData(String document, Long revision) throws IOException, InterruptedException {
        ObjectNode args = JsonNodeFactory.instance.objectNode().put("documentId", document);
        if (revision == null) args.putNull("revision"); else args.put("revision", revision);
        JsonNode result = data("read", args);
        if (!result.has("artifact")) throw new IOException("Document snapshot unavailable");
        return result;
    }

    /** Applies advisory validation to an exact request without advancing accepted state.
     * @param document authorized document
     * @param bytes retained original HTTP body
     * @return request-bound proposed source or diagnostics
     * @throws IOException malformed body or unavailable infrastructure
     * @throws InterruptedException interrupted child after reaping
     * @throws IllegalArgumentException invalid draft identity or envelope
     */
    byte[] validate(String document, byte[] bytes) throws IOException, InterruptedException {
        JsonNode request = DocumentJson.request(bytes);
        DocumentJson.fields(request, "draftId", "draftEpoch", "baseRevision", "candidate");
        if (!request.path("draftId").isTextual()) throw new IllegalArgumentException("Invalid draft ID");
        UUID.fromString(request.path("draftId").textValue());
        DocumentJson.revision(request, "draftEpoch");
        long base = DocumentJson.revision(request, "baseRevision");
        runtime.requireReady();
        WorkerCapacity.acquire();
        try {
            JsonNode artifact = readData(document, base).path("artifact");
            JsonNode candidate = request.path("candidate");
            JsonNode inventory = inventory(document, candidate.path("module"));
            DocumentWorker worker = new DocumentWorker();
            if (!worker.identity().equals(runtime.dependency())) throw new IOException("Validator build changed");
            JsonNode outcome = worker.validate(candidate, artifact, inventory, runtime.policy());
            return validationReply(request, bytes, outcome);
        } finally {
            WorkerCapacity.release();
        }
    }

    /** Resolves only the candidate's existing IDs against authorized immutable history.
     * @param document owned document
     * @param module submitted index/forest
     * @return ID-to-kind inventory, never a browser authority claim
     * @throws IOException missing inventory or size violation
     * @throws InterruptedException interrupted bridge
     */
    private JsonNode inventory(String document, JsonNode module) throws IOException, InterruptedException {
        Set<String> ids = new HashSet<>();
        ArrayDeque<JsonNode> pending = new ArrayDeque<>();
        pending.add(module);
        while (!pending.isEmpty()) {
            JsonNode value = pending.removeLast();
            if (value.isTextual() && value.textValue().startsWith("server:")) ids.add(value.textValue());
            for (JsonNode child : value) pending.add(child);
        }
        if (ids.size() > 4096) throw new IOException("Identity inventory exceeds limit");
        if (ids.isEmpty()) return JsonNodeFactory.instance.objectNode();
        ObjectNode args = JsonNodeFactory.instance.objectNode().put("documentId", document);
        ArrayNode list = args.putArray("ids");
        for (String id : ids) list.add(id);
        JsonNode result = data("ownedIds", args).path("ids");
        if (!result.isObject()) throw new IOException("Identity inventory unavailable");
        return result;
    }

    /** Binds a preview to exact request bytes, with SOURCE's additional exact-source identity.
     * @param request original draft intent
     * @param bytes exact serialized request
     * @param result independently checked worker envelope
     * @return bounded advisory response
     * @throws IOException malformed worker result or oversized serialization
     */
    private byte[] validationReply(JsonNode request, byte[] bytes, JsonNode result) throws IOException {
        String status = result.path("status").asText();
        if (status.equals("UNAVAILABLE")) return DocumentReplies.status("UNAVAILABLE");
        JsonNode checked = result.path("data");
        if (!checked.path("diagnostics").isArray()) throw new IOException("Missing diagnostics");
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("requestHash", Hashes.bytes(bytes));
        for (String name : new String[]{"draftId", "draftEpoch", "baseRevision"}) data.set(name, request.get(name));
        data.put("supportMode", checked.path("mode").asText("UNAVAILABLE"));
        data.set("diagnostics", draftDiagnostics(checked));
        data.set("proposedSource", checked.has("source") ? checked.get("source") : JsonNodeFactory.instance.nullNode());
        data.set("proposedSourceHash", checked.has("sourceHash") ? checked.get("sourceHash") : JsonNodeFactory.instance.nullNode());
        if (request.path("candidate").path("mode").asText().equals("SOURCE")) {
            data.put("sourceHash", Hashes.text(request.path("candidate").path("source").asText()));
        } else if (checked.has("sourceHash")) data.set("sourceHash", checked.get("sourceHash"));
        return reply(status, data);
    }

    /** Translates fresh server IDs back to submitted draft IDs for advisory diagnostics.
     * @param checked worker content and remapping
     * @return defensive bounded diagnostics in submitted identity space
     * @throws IOException diagnostic limit exceeded
     */
    private JsonNode draftDiagnostics(JsonNode checked) throws IOException {
        JsonNode diagnostics = checked.path("diagnostics").deepCopy();
        if (diagnostics.size() > 64 || JsonWire.encode(diagnostics).length > 32768) throw new IOException("Diagnostic limit");
        Map<String, String> inverse = new LinkedHashMap<>();
        var mappings = checked.path("idRemapping").fields();
        while (mappings.hasNext()) {
            var mapping = mappings.next();
            inverse.put(mapping.getValue().asText(), mapping.getKey());
        }
        for (JsonNode diagnostic : diagnostics) {
            if (diagnostic.isObject() && inverse.containsKey(diagnostic.path("nodeId").asText())) {
                ((ObjectNode) diagnostic).put("nodeId", inverse.get(diagnostic.path("nodeId").asText()));
            }
        }
        return diagnostics;
    }

    /** Resolves solver source/command entirely from an accepted immutable current-policy artifact.
     * @param document authorized document
     * @param bytes closed accepted-analysis selection
     * @return job and complete accepted analysis identity
     * @throws IOException unavailable artifact or infrastructure
     * @throws InterruptedException interrupted read
     */
    synchronized byte[] analyze(String document, byte[] bytes) throws IOException, InterruptedException {
        JsonNode request = DocumentJson.request(bytes);
        DocumentJson.fields(request, "acceptedRevision", "commandKey", "draftEpoch", "exactSourceHash");
        long revision = DocumentJson.revision(request, "acceptedRevision");
        long epoch = DocumentJson.revision(request, "draftEpoch");
        JsonNode artifact = readData(document, revision).path("artifact");
        JsonNode command = command(artifact, request);
        if (analyses.size() >= 128) analyses.remove(analyses.keySet().iterator().next());
        JobView job = jobs.submit(new JobRequest(artifact.path("source").textValue(), command.path("index").intValue(),
                revision, epoch, "ANALYZE"));
        ObjectNode key = analysisKey(document, revision, epoch, artifact, command, job);
        analyses.put(job.jobId(), key.deepCopy());
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("jobId", job.jobId());
        data.set("acceptedAnalysisKey", key);
        data.set("job", JsonWire.decode(JsonWire.encode(job), JsonNode.class));
        return reply("SUBMITTED", data);
    }

    /** Rejects absent, stale or substituted command descriptors without trusting a browser index.
     * @param artifact exact accepted content
     * @param request closed command selection
     * @return unique stored descriptor
     * @throws IllegalArgumentException stale policy/source or unknown command
     */
    private JsonNode command(JsonNode artifact, JsonNode request) {
        if (!runtime.policy().equals(artifact.path("policyVersion").asText())
                || !artifact.path("sourceHash").equals(request.path("exactSourceHash"))) {
            throw new IllegalArgumentException("Accepted source requires current-policy revalidation");
        }
        for (JsonNode command : artifact.path("analysisDescriptors")) {
            if (command.path("commandKey").equals(request.path("commandKey"))
                    && command.path("artifactId").equals(artifact.path("artifactId"))
                    && command.path("sourceHash").equals(artifact.path("sourceHash"))
                    && command.path("policyVersion").equals(artifact.path("policyVersion"))) return command;
        }
        throw new IllegalArgumentException("Unknown accepted command");
    }

    /** Reads accepted-document evidence only through its original full identity binding.
     * @param document authorized document
     * @param jobId opaque solver job
     * @return current or historical labeled result with complete evidence identity
     * @throws IOException unknown, stale-policy or unavailable job
     * @throws InterruptedException interrupted artifact lookup
     */
    synchronized byte[] analysis(String document, String jobId) throws IOException, InterruptedException {
        JsonNode key = analyses.get(jobId);
        if (key == null || !document.equals(key.path("documentId").asText())) throw new IOException("Unknown analysis");
        JsonNode current = readData(document, null);
        JobView job = jobs.get(jobId);
        if (job == null || !job.analysisKey().equals(key.path("jobAnalysisKey").asText())
                || !runtime.policy().equals(key.path("policyVersion").asText())) throw new IOException("Stale analysis");
        ObjectNode data = JsonNodeFactory.instance.objectNode().put("jobId", jobId);
        data.put("historical", current.path("headRevision").longValue() != key.path("acceptedRevision").longValue());
        data.set("acceptedAnalysisKey", key.deepCopy());
        data.set("job", JsonWire.decode(JsonWire.encode(job), JsonNode.class));
        return reply("OK", data);
    }

    /** Builds complete evidence identity without using expression labels as authority.
     * @param document owned document
     * @param revision immutable accepted revision
     * @param epoch presentation generation
     * @param artifact source/policy/dependency identity
     * @param command parser occurrence descriptor
     * @param job independently isolated solver job
     * @return complete accepted identity
     */
    private ObjectNode analysisKey(String document, long revision, long epoch, JsonNode artifact, JsonNode command, JobView job) {
        ObjectNode key = JsonNodeFactory.instance.objectNode().put("documentId", document)
                .put("acceptedRevision", revision).put("draftEpoch", epoch).put("jobAnalysisKey", job.analysisKey());
        for (String field : new String[]{"artifactId", "sourceHash", "policyVersion", "dependencyHash"}) {
            key.set(field, artifact.get(field).deepCopy());
        }
        key.set("commandKey", command.get("commandKey").deepCopy());
        key.set("options", command.get("options").deepCopy());
        return key;
    }

    /** Executes only an installed store operation and separates unavailable state from empty data.
     * @param operation fixed internal operation
     * @param args server-derived arguments
     * @return authorized response data
     * @throws IOException store/protocol failure
     * @throws InterruptedException interrupted private process
     */
    private JsonNode data(String operation, JsonNode args) throws IOException, InterruptedException {
        runtime.requireReady();
        JsonNode result = gateway.request(operation, args);
        if (!result.path("status").asText().equals("OK")) throw new IOException("Document store unavailable");
        return result.path("data").deepCopy();
    }

    /** Encodes a bounded nonterminal response identity.
     * @param status response category
     * @param data authoritative or advisory payload
     * @return complete envelope bytes
     * @throws IOException output limit exceeded
     */
    private byte[] reply(String status, JsonNode data) throws IOException {
        return DocumentReplies.encode(UUID.randomUUID().toString(), status, data);
    }
}
