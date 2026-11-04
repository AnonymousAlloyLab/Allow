package dev.allow.corpus;

import dev.allow.egraph.Certificate;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.util.List;
import java.util.Map;

/** Internal bounded proof augmentation entry point; never admits new source records or solver evidence. */
public final class CorpusAugmentMain {
    /** Prevents construction of the one-shot entry point. */
    private CorpusAugmentMain() { }

    /** Checks an existing certificate and emits only a nonce-bound derived identity proof.
     * @param args unused
     * @throws IOException malformed frame or excessive output
     */
    public static void main(String[] args) throws IOException {
        byte[] input = System.in.readNBytes(524289);
        if (input.length > 524288 || input.length == 0 || input[input.length - 1] != '\n') {
            throw new IOException("Invalid augmentation frame");
        }
        Request request = JsonWire.decode(input, Request.class);
        validate(request);
        List<TrainingVariant.Variant> variants = TrainingVariant.fromCertificate(request.certificate());
        byte[] output = JsonWire.encode(Map.of("protocol", 1, "requestId", request.requestId(),
                "recordId", request.recordId(), "status", variants.isEmpty() ? "UNAVAILABLE" : "CHECKED",
                "variants", variants));
        if (output.length > 524288) throw new IOException("Augmentation output limit");
        System.out.write(output);
        System.out.write('\n');
        System.out.flush();
    }

    /** Validates identity without treating caller strings as paths or executable content.
     * @param request decoded immutable envelope
     * @throws IOException missing or invalid identity
     */
    private static void validate(Request request) throws IOException {
        if (request.protocol() != 1 || request.certificate() == null || request.requestId() == null
                || !request.requestId().matches("[a-f0-9-]{36}") || request.recordId() == null
                || !request.recordId().matches("[a-f0-9]{64}")) throw new IOException("Invalid augmentation identity");
    }

    /** Internal proof request; certificates remain untrusted until independent replay succeeds.
     * @param protocol wire version
     * @param requestId caller nonce
     * @param recordId existing record to which the caller must bind this proof
     * @param certificate original immutable source-to-representative derivation
     */
    private record Request(int protocol, String requestId, String recordId, Certificate certificate) { }
}
