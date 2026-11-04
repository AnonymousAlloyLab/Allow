package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.nio.file.Files;
import java.nio.file.Path;

/** Gate-only actual ownership probe; synthetic context explicitly assumes rather than proves SQL CLEAN. */
public final class WarmPoolProbeMain {
    /** Prevents construction of the fixed gate entry point. */
    private WarmPoolProbeMain() {}

    /** Runs only the registered finite cases inside the harness-provisioned delegated scope.
     * @param arguments exact runtime-root, cases and report option/value pairs
     * @throws Exception invalid harness identity or unavailable report storage
     */
    public static void main(String[] arguments) throws Exception {
        WarmProbeFiles.require(arguments.length == 6 && arguments[0].equals("--runtime-root")
                && arguments[2].equals("--cases") && arguments[4].equals("--report"), "Invalid probe arguments");
        Path root = Path.of(arguments[1]).toRealPath();
        Path cases = Path.of(arguments[3]);
        Path report = Path.of(arguments[5]);
        WarmProbeFiles.require(cases.equals(root.resolve(".gate/probe-cases.json"))
                && report.equals(root.resolve(".gate/evidence/java-probe.json")), "Unregistered report or cases path");
        WarmProbeFiles.require(Path.of("").toRealPath().equals(root.resolve("backend")), "Wrong probe working directory");
        String build = BuildIdentity.read(root.resolve("backend/target"));
        Path group = WarmConfiguration.read(root);
        ObjectNode result = run(root, cases, group, build);
        new WarmProbeFiles(root).save("java-probe.json", result);
        if (!result.path("status").asText().equals("PASS")) System.exit(1);
    }

    /** Evaluates every registered case while preserving finite failures as private bound evidence.
     * @param root copied installation
     * @param cases frozen case manifest
     * @param group verified delegated root
     * @param build full installed executable identity
     * @return complete finite report
     * @throws Exception invalid registration or unavailable evidence storage
     */
    private static ObjectNode run(Path root, Path cases, Path group, String build) throws Exception {
        byte[] manifest = Files.readAllBytes(cases);
        JsonNode plan = JsonWire.decode(manifest, JsonNode.class);
        WarmProbeFiles.require(plan.path("cases").isArray() && plan.path("cases").size() == 11, "Eleven registered cases required");
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("schema", 1).put("status", "PASS")
                .put("buildIdentity", build).put("caseManifestSha256", Hashes.bytes(manifest))
                .put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL");
        ArrayNode outcomes = result.putArray("cases");
        for (JsonNode item : plan.path("cases")) {
            if (result.path("status").asText().equals("BLOCKED")) {
                outcomes.addObject().put("id", item.path("id").asText()).put("status", "BLOCKED")
                        .put("reason", "NOT_EXECUTED_AFTER_PRIOR_FAILURE");
                continue;
            }
            ObjectNode outcome = WarmProbeSession.execute(root, cases, group, build, item);
            outcomes.add(outcome);
            if (!outcome.path("status").asText().equals("PASS")) result.put("status", "BLOCKED");
        }
        WarmProbeFiles.require(BuildIdentity.read(root.resolve("backend/target")).equals(build), "Probe build changed");
        return result;
    }
}
