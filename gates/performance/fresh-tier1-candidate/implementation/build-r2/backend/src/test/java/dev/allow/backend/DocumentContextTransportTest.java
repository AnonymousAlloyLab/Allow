package dev.allow.backend;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.MissingNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Actual one-shot bridge framing failures before a validation context can be returned. */
class DocumentContextTransportTest {
    @TempDir
    private Path directory;

    /** A private process cannot substitute an earlier request nonce.
     * @throws IOException unavailable temporary fixture
     */
    @Test
    void rejectsWrongNonceFromExitedBridge() throws IOException {
        DocumentGateway gateway = fixture("result['requestId'] = '00000000-0000-0000-0000-000000000001'");
        assertThrows(IOException.class, new Request(gateway));
    }

    /** A valid nonce does not authorize an unsupported private protocol.
     * @throws IOException unavailable temporary fixture
     */
    @Test
    void rejectsWrongProtocolFromExitedBridge() throws IOException {
        DocumentGateway gateway = fixture("result['protocol'] = 2");
        assertThrows(IOException.class, new Request(gateway));
    }

    /** Extra transport fields fail the existing closed outer-envelope contract.
     * @throws IOException unavailable temporary fixture
     */
    @Test
    void rejectsExtraTransportFields() throws IOException {
        DocumentGateway gateway = fixture("result['checked'] = True");
        assertThrows(IllegalArgumentException.class, new Request(gateway));
    }

    /** The advisory path classifies malformed private envelopes as unavailable infrastructure.
     * @throws IOException unavailable temporary fixture
     */
    @Test
    void classifiesExtraEnvelopeAsUnavailableContext() throws IOException {
        DocumentGateway gateway = fixture("result['checked'] = True");
        IOException failure = assertThrows(IOException.class, new ContextRead(gateway));
        assertInstanceOf(IllegalArgumentException.class, failure.getCause());
    }

    /** Creates an owned private fixture executable without invoking SQL or the actual store.
     * @param mutation fixed test-only Python statement changing the response
     * @return gateway using the exact existing one-shot transport and limits
     * @throws IOException temporary executable creation failure
     */
    private DocumentGateway fixture(String mutation) throws IOException {
        Path executable = directory.resolve(".tools/retrieval-venv/bin/python");
        Files.createDirectories(executable.getParent());
        String script = "#!/usr/bin/python3\nimport json,sys\nframe=json.load(sys.stdin)\n"
                + "result={'protocol':1,'requestId':frame['requestId'],'status':'OK','data':{}}\n"
                + mutation + "\nsys.stdout.write(json.dumps(result)+'\\n')\n";
        Files.writeString(executable, script);
        Files.setPosixFilePermissions(executable, PosixFilePermissions.fromString("rwx------"));
        return new DocumentGateway(directory.toString());
    }

    /** Supplies the closed operation name to an actual bounded fixture child. */
    private record Request(DocumentGateway gateway) implements Executable {
        /** Executes the bridge and observes the malformed private reply after exit.
         * @throws IOException expected identity/protocol failure
         * @throws InterruptedException interrupted fixture process
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            gateway.request("validationContext", JsonNodeFactory.instance.objectNode());
        }
    }

    /** Exercises the advisory-only private error classification boundary. */
    private record ContextRead(DocumentGateway gateway) implements Executable {
        /** Reads an exact base context through the real fixture gateway.
         * @throws IOException expected unavailable private context
         * @throws InterruptedException interrupted fixture process
         */
        @Override
        public void execute() throws IOException, InterruptedException {
            DocumentValidationContext.read(gateway, "server:00000000-0000-0000-0000-000000000001",
                    0, MissingNode.getInstance());
        }
    }
}
