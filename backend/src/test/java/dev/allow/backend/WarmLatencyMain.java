package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Set;

/** Finite copied-installation component diagnostic; never selects production warm runtime. */
public final class WarmLatencyMain {
    private static final String CONTRACT = "626a50b7afa537c906b38219c8646ca1043d59dbf38187820ad8b56a9f1253f2";

    /** Prevents construction of the command-line gate producer. */
    private WarmLatencyMain() {}

    /** Runs exactly one declared variant and writes bounded evidence after teardown.
     * @param args six fixed root, plan and report arguments
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception malformed declaration or evidence write failure
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 6 || !args[0].equals("--runtime-root") || !args[2].equals("--plan")
                || !args[4].equals("--report")) throw new IOException("Expected root, plan and report arguments");
        Path root = Path.of(args[1]).toRealPath();
        JsonNode plan = DocumentJson.decode(Files.readAllBytes(Path.of(args[3])));
        validate(root, plan);
        byte[] input = Files.readAllBytes(Path.of(plan.path("fixture").asText()));
        if (!Hashes.bytes(input).equals(plan.path("fixtureSha256").asText())) throw new IOException("Fixture digest mismatch");
        JsonNode fixture = DocumentJson.decode(input);
        if (!"VALIDATE".equals(fixture.path("operation").asText())
                || !"document-v1".equals(fixture.path("policyVersion").asText())) throw new IOException("Wrong fixture policy");
        ObjectNode report = report(plan, root);
        new WarmLatencySeries(root, plan, fixture, report).run();
        write(Path.of(args[5]), report);
        if (!"COMPLETE".equals(report.path("status").asText())) throw new IOException("Diagnostic variant failed; report retained");
    }

    /** Rejects declarations outside the exact finite diagnostic profiles and counts.
     * @param root copied installation root
     * @param plan parsed immutable variant declaration
     * @throws IOException rejected declaration or unavailable ownership evidence
     * @throws Exception wrong working target, selected production runtime or unsupported declaration
     */
    private static void validate(Path root, JsonNode plan) throws Exception {
        if (WarmRuntime.enabled() || !Path.of("target").toRealPath().equals(root.resolve("backend/target"))) {
            throw new IOException("Expected copied disabled-runtime backend target");
        }
        if (plan.path("schema").asInt() != 1 || !CONTRACT.equals(plan.path("contractSha256").asText())
                || !Set.of("FRESH", "POOL_SERIAL", "POOL_READY", "POOL_EMPTY").contains(plan.path("profile").asText())) {
            throw new IOException("Unregistered diagnostic plan");
        }
        int warmups = plan.path("warmups").asInt(-1), measured = plan.path("measured").asInt(-1);
        boolean preflight = "PREFLIGHT".equals(plan.path("mode").asText());
        boolean empty = "POOL_EMPTY".equals(plan.path("profile").asText());
        if (preflight ? warmups != 0 || measured != 1 : !"MEASURED".equals(plan.path("mode").asText())
                || warmups != (empty ? 0 : 20) || measured != (empty ? 20 : 100)) {
            throw new IOException("Unregistered diagnostic counts");
        }
        if (preflight && !Set.of("FRESH", "POOL_SERIAL").contains(plan.path("profile").asText())) {
            throw new IOException("Unregistered preflight profile");
        }
    }

    /** Creates small report metadata before any operation timers start.
     * @param plan frozen finite variant declaration
     * @param root copied production installation
     * @return report header bound to actual installed executable identity
     * @throws IOException incomplete copied build
     */
    private static ObjectNode report(JsonNode plan, Path root) throws IOException {
        ObjectNode report = JsonNodeFactory.instance.objectNode().put("schema", 1)
                .put("variantId", plan.path("variantId").asText()).put("profile", plan.path("profile").asText())
                .put("mode", plan.path("mode").asText()).put("contractSha256", CONTRACT)
                .put("fixtureSha256", plan.path("fixtureSha256").asText())
                .put("buildSha256", BuildIdentity.read(root.resolve("backend/target")))
                .put("contextBoundary", "TEST_ASSUMED_CLEAN_CONTEXT_NO_SQL")
                .put("expectedWarmups", plan.path("warmups").asInt()).put("expectedMeasured", plan.path("measured").asInt());
        report.put("route", "FRESH".equals(plan.path("profile").asText())
                ? "ACTUAL_DOCUMENT_WORKER_DEFAULT_DISABLED_POOL" : "ACTUAL_WARM_WORKER_POOL_ASSUMED_CLEAN");
        return report;
    }

    /** Writes new private complete report bytes after the owned series has stopped.
     * @param path new private evidence destination
     * @param report complete buffered result
     * @throws IOException existing destination or evidence write failure
     */
    private static void write(Path path, ObjectNode report) throws IOException {
        Files.createFile(path, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
        Files.write(path, JsonWire.encode(report), StandardOpenOption.WRITE);
    }
}
