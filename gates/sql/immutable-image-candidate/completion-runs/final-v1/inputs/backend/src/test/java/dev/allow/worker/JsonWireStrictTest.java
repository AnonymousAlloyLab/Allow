package dev.allow.worker;

import dev.allow.dto.WorkerRequest;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;
import static org.junit.jupiter.api.Assertions.assertThrows;

/** Ensures the shared worker codec rejects coerced protocol identity. */
class JsonWireStrictTest {
    /** Rejects null, string, fractional, boolean and missing protocol fields. */
    @Test
    void invalidProtocolNumbers() {
        for (String value : new String[]{"null", "\"1\"", "1.5", "true"}) {
            assertThrows(IOException.class, new DecodeAction("\"protocol\":" + value + ","));
        }
        assertThrows(IOException.class, new DecodeAction(""));
    }

    /**
     * Decodes a worker request with the given protocol field.
     * @param protocol optional raw protocol member
     * @throws IOException invalid worker frame
     */
    private static void decode(String protocol) throws IOException {
        String body = "{" + protocol + "\"jobId\":\"j\",\"source\":\"run {}\","
                + "\"sourceHash\":\"h\",\"analysisKey\":\"k\",\"commandIndex\":0,"
                + "\"revision\":0,\"epoch\":0,\"operation\":\"ANALYZE\"}";
        JsonWire.decode(body.getBytes(StandardCharsets.UTF_8), WorkerRequest.class);
    }
    /** Carries a malformed input to the assertion callback. */
    private record DecodeAction(String protocol) implements Executable {
        /** Executes the malformed decode.
         * @throws IOException rejected input
         */
        @Override
        public void execute() throws IOException {
            decode(protocol);
        }
    }
}
