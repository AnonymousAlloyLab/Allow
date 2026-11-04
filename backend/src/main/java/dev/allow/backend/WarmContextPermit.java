package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;

/** One-use local authority backed by the existing CLI's checked CLEAN receipt. */
final class WarmContextPermit {
    private final WarmRequestBinding binding;
    private DocumentValidationContext context;

    /** Retains a successfully checked context without exposing a public authority flag.
     * @param binding exact admitted operation identity
     * @param context freshly authorized context after the private gateway returned
     */
    private WarmContextPermit(WarmRequestBinding binding, DocumentValidationContext context) {
        this.binding = binding;
        this.context = context;
    }

    /** Obtains fresh context through the existing checked CLI/proxy cleanup composition.
     * @param gateway operation-only private persistence adapter
     * @param binding server-created admission identity
     * @param module candidate module used only for scoped identifier resolution
     * @param deadline original operation success deadline
     * @return one-use permit after successful context validation
     * @throws IOException context unavailable, malformed or late
     * @throws InterruptedException cancelled context operation
     */
    static WarmContextPermit read(DocumentGateway gateway, WarmRequestBinding binding, JsonNode module,
            WarmDeadline deadline) throws IOException, InterruptedException {
        deadline.check();
        DocumentValidationContext context = DocumentValidationContext.read(gateway, binding.document(),
                binding.revision(), module, deadline);
        deadline.check();
        return new WarmContextPermit(binding, context);
    }

    /** Consumes the exact context once and drops the permit's model references.
     * @param expected exact server admission identity
     * @return fresh authorized context owned by the single handoff
     * @throws IOException substituted, stale or already consumed permit
     */
    synchronized DocumentValidationContext consume(WarmRequestBinding expected) throws IOException {
        if (!binding.equals(expected) || context == null) throw new IOException("Unavailable context permit");
        DocumentValidationContext result = context;
        context = null;
        return result;
    }
}
