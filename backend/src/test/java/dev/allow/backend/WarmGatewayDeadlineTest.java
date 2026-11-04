package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Actual controlled gateway subprocesses test candidate budget clamping without PostgreSQL. */
class WarmGatewayDeadlineTest {
    @TempDir
    private Path root;

    /** The ordinary gateway still accepts a response beyond the shorter candidate test budget.
     * @throws Exception failed controlled executable or gateway exchange
     */
    @Test
    void preservesOrdinaryGatewayWait() throws Exception {
        DocumentGateway gateway = fixture(0.12);
        assertEquals("OK", gateway.request("validationContext", JsonNodeFactory.instance.objectNode()).path("status").asText());
        assertChildAbsent();
    }

    /** Candidate timeout reaps the actual private child rather than returning a late envelope.
     * @throws Exception failed controlled executable or process observation
     */
    @Test
    void clampsCandidateWaitAndReapsChild() throws Exception {
        DocumentGateway gateway = fixture(2);
        long start = System.nanoTime();
        assertThrows(IOException.class, new Request(gateway, new WarmDeadline(100)));
        assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start) < 1500);
        assertChildAbsent();
    }

    /** A timely candidate response preserves the unchanged closed private envelope.
     * @throws Exception failed controlled executable or gateway exchange
     */
    @Test
    void acceptsTimelyCandidateEnvelope() throws Exception {
        DocumentGateway gateway = fixture(0);
        assertEquals("OK", gateway.request("validationContext", JsonNodeFactory.instance.objectNode(),
                new WarmDeadline(1000)).path("status").asText());
        assertChildAbsent();
    }

    /** Writes one owned fixture executable at the gateway's existing fixed installation path.
     * @param delay public fixture response delay in seconds
     * @return actual gateway using the controlled executable
     * @throws IOException failed temporary executable creation
     */
    private DocumentGateway fixture(double delay) throws IOException {
        Path executable = root.resolve(".tools/retrieval-venv/bin/python");
        Files.createDirectories(executable.getParent());
        String script = "#!/usr/bin/python3\nimport os,json,sys,time\nfrom pathlib import Path\n"
                + "Path('child.pid').write_text(str(os.getpid()))\nframe=json.load(sys.stdin)\ntime.sleep(" + delay + ")\n"
                + "reply={'protocol':1,'requestId':frame['requestId'],'status':'OK','data':{}}\n"
                + "sys.stdout.write(json.dumps(reply)+'\\n')\n";
        Files.writeString(executable, script);
        Files.setPosixFilePermissions(executable, PosixFilePermissions.fromString("rwx------"));
        return new DocumentGateway(root.toString());
    }

    /** Requires actual direct-child absence after the gateway's cleanup has completed.
     * @throws IOException unavailable recorded child identity
     */
    private void assertChildAbsent() throws IOException {
        long pid = Long.parseLong(Files.readString(root.resolve("child.pid")));
        assertFalse(ProcessHandle.of(pid).isPresent());
    }

    /** Carries an exact candidate budget into a checked gateway assertion. */
    private record Request(DocumentGateway gateway, WarmDeadline deadline) implements Executable {
        /** Runs the actual deadline-aware private gateway transport.
         * @throws IOException expected deadline failure
         * @throws InterruptedException cancelled fixture
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            gateway.request("validationContext", JsonNodeFactory.instance.objectNode(), deadline);
        }
    }
}
