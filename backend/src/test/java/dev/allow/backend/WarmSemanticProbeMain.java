package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

/** Gate-only complete semantic comparison driver; it grants no production context authority. */
public final class WarmSemanticProbeMain {
    /** Prevents construction of the fixed gate entry point. */
    private WarmSemanticProbeMain() {}

    /** Runs the frozen finite corpus in exactly one separately contained variant.
     * @param arguments fixed runtime-root, variant, manifest and report pairs
     * @throws Exception invalid registration or unavailable immutable evidence
     */
    public static void main(String[] arguments) throws Exception {
        WarmProbeFiles.require(arguments.length == 8 && arguments[0].equals("--runtime-root")
                && arguments[2].equals("--variant") && arguments[4].equals("--manifest")
                && arguments[6].equals("--report"), "Invalid semantic probe arguments");
        Path root = Path.of(arguments[1]).toRealPath();
        String variant = arguments[3];
        WarmProbeFiles.require(Set.of("W0", "W1").contains(variant), "Unregistered semantic variant");
        Path manifest = root.resolve(".gate/semantic-fixtures.json");
        WarmProbeFiles.require(Path.of(arguments[5]).equals(manifest)
                && Path.of(arguments[7]).equals(root.resolve(".gate/evidence/semantic-java.json"))
                && Path.of("").toRealPath().equals(root.resolve("backend")), "Unregistered semantic paths");
        String build = BuildIdentity.read(root.resolve("backend/target"));
        ObjectNode report = run(root, variant, manifest, build, WarmConfiguration.read(root));
        new WarmProbeFiles(root).save("semantic-java.json", report);
        if (!report.path("status").asText().equals("PASS")) System.exit(1);
    }

    /** Preserves every executed row before advancing and stops after unconfirmed runtime failure.
     * @param root copied installation
     * @param variant fixed baseline or candidate route
     * @param manifest frozen exact corpus
     * @param build installed full executable identity
     * @param group independently validated delegated root
     * @return finite result without inferred unexecuted success
     * @throws Exception invalid corpus or unavailable evidence
     */
    private static ObjectNode run(Path root, String variant, Path manifest, String build, Path group) throws Exception {
        byte[] bytes = Files.readAllBytes(manifest);
        JsonNode plan = JsonWire.decode(bytes, JsonNode.class);
        registration(plan);
        ObjectNode report = JsonNodeFactory.instance.objectNode().put("schema", 1).put("status", "PASS")
                .put("variant", variant).put("buildIdentity", build).put("caseManifestSha256", Hashes.bytes(bytes))
                .put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL")
                .put("selectedRuntimeRoute", "NOT_TESTED_PRODUCTION_DISABLED")
                .put("classification", "FINITE_CASE_CHECKS_NOT_PAIRWISE_EQUIVALENCE");
        ArrayNode rows = report.putArray("cases");
        boolean stopped = false;
        for (JsonNode item : plan.path("fixtures")) {
            if (stopped) {
                rows.addObject().put("id", item.path("name").asText()).put("status", "NOT_EXECUTED");
                continue;
            }
            ObjectNode row = WarmSemanticCase.execute(root, variant, group, build, item);
            rows.add(row);
            new WarmProbeFiles(root).save(WarmSemanticProtocol.basename(item.path("name").textValue()) + "-case.json", row);
            if (!row.path("status").asText().equals("PASS")) { report.put("status", "BLOCKED"); stopped = true; }
        }
        WarmProbeFiles.require(BuildIdentity.read(root.resolve("backend/target")).equals(build), "Semantic build changed");
        return report;
    }

    /** Requires the exact corpus cardinality and registered route split before launching any worker.
     * @param plan decoded frozen corpus manifest
     * @throws Exception missing, duplicate or rerouted corpus entries
     * @throws java.io.IOException unregistered operation
     */
    private static void registration(JsonNode plan) throws Exception {
        WarmProbeFiles.require(plan.path("fixtures").isArray() && plan.path("fixtures").size() == 190,
                "Exactly 190 semantic fixtures required");
        Set<String> names = new HashSet<>();
        Set<String> basenames = new HashSet<>();
        int advisory = 0;
        int fresh = 0;
        for (JsonNode item : plan.path("fixtures")) {
            String operation = item.path("operation").asText();
            WarmProbeFiles.require(names.add(item.path("name").asText())
                    && basenames.add(WarmSemanticProtocol.basename(item.path("name").asText()))
                    && item.path("W0_route").asText().equals("fresh-default"), "Invalid semantic registration");
            if (operation.equals("VALIDATE")) advisory++;
            else if (operation.equals("REVALIDATE")) fresh++;
            else throw new java.io.IOException("Unregistered semantic operation");
            WarmProbeFiles.require(item.path("W1_route").asText().equals(operation.equals("VALIDATE")
                    ? "warm-advisory" : "fresh-revalidate"), "Changed semantic route");
        }
        WarmProbeFiles.require(advisory == 153 && fresh == 37, "Changed semantic operation counts");
    }
}
