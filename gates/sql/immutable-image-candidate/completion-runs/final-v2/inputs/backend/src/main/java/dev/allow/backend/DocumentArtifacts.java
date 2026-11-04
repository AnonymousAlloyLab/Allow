package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.UUID;

/** Trusted artifact envelopes separate durable identity from worker-computed content. */
final class DocumentArtifacts {
    /** Prevents construction of the stateless artifact assembler. */
    private DocumentArtifacts() {}

    /** Constructs revision zero from the explicitly proved empty module case.
     * @param policy current parser/policy identity
     * @param dependency exact installed worker build hash
     * @return bounded empty accepted artifact
     * @throws IOException serialization failure
     */
    static ObjectNode empty(String policy, String dependency) throws IOException {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("mode", "BLOCK_SUPPORTED")
                .put("source", "").put("sourceHash", Hashes.text(""));
        ObjectNode module = JsonNodeFactory.instance.objectNode().put("version", 1);
        for (String field : new String[]{"signatures", "fields", "predicates", "facts", "assertions", "commands", "nodes"}) {
            module.putArray(field);
        }
        result.set("module", module);
        for (String field : new String[]{"occurrences", "trivia", "analysisDescriptors"}) result.putArray(field);
        return checked(result, policy, dependency);
    }

    /** Assigns fresh artifact and command identities to independently checked content.
     * @param result completed isolated worker result
     * @param policy current parser/policy fence
     * @param dependency exact validator build
     * @return immutable-by-convention artifact snapshot
     * @throws IOException malformed, unrelated or oversized worker data
     */
    static ObjectNode checked(JsonNode result, String policy, String dependency) throws IOException {
        ObjectNode artifact = JsonNodeFactory.instance.objectNode().put("artifactId", "server:" + UUID.randomUUID())
                .put("policyVersion", policy).put("dependencyHash", dependency);
        for (String key : new String[]{"mode", "source", "sourceHash", "module", "occurrences", "trivia"}) {
            if (!result.has(key)) throw new IOException("Incomplete checked artifact");
            artifact.set(key, result.get(key).deepCopy());
        }
        if (!artifact.path("source").isTextual() || !artifact.path("sourceHash").isTextual()
                || !Hashes.text(artifact.path("source").textValue()).equals(artifact.path("sourceHash").textValue())) {
            throw new IOException("Checked source identity mismatch");
        }
        artifact.set("analysisDescriptors", descriptors(result.path("analysisDescriptors"), artifact));
        if (JsonWire.encode(artifact).length > 1048576) throw new IOException("Artifact exceeds limit");
        return artifact;
    }

    /** Freezes parser command occurrences independently of block IR availability.
     * @param input internal parser descriptors
     * @param artifact exact source/policy/artifact envelope
     * @return public closed artifact-bound descriptors
     * @throws IOException malformed descriptor or budget violation
     */
    private static ArrayNode descriptors(JsonNode input, JsonNode artifact) throws IOException {
        if (!input.isArray() || input.size() > 32) throw new IOException("Invalid command inventory");
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        boolean block = artifact.path("mode").asText().equals("BLOCK_SUPPORTED");
        if (block && artifact.path("module").path("commands").size() != input.size()) {
            throw new IOException("Command inventory mismatch");
        }
        for (int index = 0; index < input.size(); index++) {
            JsonNode command = input.get(index);
            if (!command.path("index").isInt() || command.path("index").intValue() != index
                    || !command.path("options").isObject() || !command.path("label").isTextual()
                    || command.path("label").textValue().getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 256
                    || !java.util.Set.of("run", "check").contains(command.path("kind").asText())) {
                throw new IOException("Invalid checked command");
            }
            commandBinding(command, artifact, index, block);
            ObjectNode item = result.addObject().put("commandKey", UUID.randomUUID().toString()).put("index", index);
            for (String field : new String[]{"kind", "label", "options"}) item.set(field, command.get(field).deepCopy());
            for (String field : new String[]{"artifactId", "sourceHash", "policyVersion"}) {
                item.set(field, artifact.get(field).deepCopy());
            }
        }
        return result;
    }

    /** Checks the private descriptor-to-IR mapping before storing its ordered index relation.
     * @param command worker parser descriptor
     * @param artifact typed module or text-only content
     * @param index exact parser occurrence index
     * @param block whether a typed module exists
     * @throws IOException inconsistent parser/IR command identity
     */
    private static void commandBinding(JsonNode command, JsonNode artifact, int index, boolean block) throws IOException {
        if (!block) {
            if (command.has("irCommandId")) throw new IOException("Text-only descriptor has an invented IR command");
            return;
        }
        JsonNode ir = artifact.path("module").path("commands").get(index);
        if (ir == null || !ir.path("id").equals(command.path("irCommandId"))
                || !ir.path("tag").equals(command.path("kind"))
                || ir.path("uniformScope").intValue() != command.path("options").path("overall").intValue()
                || command.path("options").path("bitwidth").intValue() != 4
                || command.path("options").path("maxseq").intValue() != 3) {
            throw new IOException("Checked command does not match its IR occurrence");
        }
    }
}
