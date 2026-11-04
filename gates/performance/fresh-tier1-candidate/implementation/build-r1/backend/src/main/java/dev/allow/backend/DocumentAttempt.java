package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/** One admitted owner generation; only the supervisor can produce its reaping evidence. */
final class DocumentAttempt {
    private final DocumentRequest request;
    private final DocumentWorker worker;
    private final String nonce;
    private final String document;
    private boolean finished;

    /** Captures an admitted generation before its worker can start.
     * @param request original immutable HTTP intent
     * @param worker owned isolated validator
     * @param admission successful private admission data
     */
    DocumentAttempt(DocumentRequest request, DocumentWorker worker, JsonNode admission) {
        this.request = request;
        this.worker = worker;
        nonce = admission.path("nonce").textValue();
        document = admission.path("documentId").textValue();
    }

    /** Returns original exact identity, never a newly serialized substitute.
     * @return bound request
     */
    DocumentRequest request() { return request; }

    /** Returns the isolated validator owned by this generation.
     * @return worker owner
     */
    DocumentWorker worker() { return worker; }

    /** Returns the private finalization fence.
     * @return random owner nonce
     */
    String nonce() { return nonce; }

    /** Returns the admitted resulting document ID, including reserved CREATE identity.
     * @return server-owned document identifier
     */
    String document() { return document; }

    /** Marks the coordinator finished only after every child invocation has been reaped. */
    void finish() { finished = true; }

    /** Binds explicit recovery evidence to the same supervisor and current secret nonce.
     * @return private recovery frame
     * @throws java.io.IOException missing supervisor identity
     * @throws IllegalStateException work has not finished
     */
    ObjectNode recovery() throws java.io.IOException {
        if (!finished) throw new IllegalStateException("Admission is still running");
        ObjectNode result = request.identity().put("nonce", nonce).put("ownerPid", ProcessHandle.current().pid())
                .put("ownerStartTicks", ProcessIdentity.startTicks(ProcessHandle.current().pid()));
        result.setAll((ObjectNode) worker.recovery());
        return result;
    }
}
