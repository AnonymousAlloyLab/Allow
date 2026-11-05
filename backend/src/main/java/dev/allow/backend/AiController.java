package dev.allow.backend;

import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import org.springframework.http.ResponseEntity;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Existing-bearer private AI routes with no automatic document mutation endpoint. */
@RestController
@RequestMapping(value = "/api/ai/v1", produces = "application/json")
final class AiController {
    private final AiService service;
    private final AccessMode access;

    /** Stores installation-owned authority; anonymous sessions cannot dispatch here.
     * @param service bounded private coordinator
     * @param access closed profile gate
     */
    AiController(AiService service, AccessMode access) { this.service = service; this.access = access; }

    /** Returns only authenticated nonsecret configuration.
     * @param request exact canonical HTTP request
     * @return config envelope
     * @throws IOException serialization failure
     */
    @GetMapping("/config")
    byte[] config(HttpServletRequest request) throws IOException { route(request); return reply("OK", service.config()); }

    /** Prepares one exact-bound proposal without dispatch before consent.
     * @param request bounded authenticated create
     * @return scoped job envelope
     * @throws IOException malformed body or serialization failure
     */
    @PostMapping(value = "/jobs", consumes = "application/json")
    byte[] create(HttpServletRequest request) throws IOException { return reply("SUBMITTED", service.create(body(request))); }

    /** Polls retained status without resuming graph work.
     * @param id opaque scoped UUID
     * @param request exact authenticated route
     * @return current view envelope
     * @throws IOException serialization failure
     */
    @GetMapping("/jobs/{id}")
    byte[] read(@PathVariable String id, HttpServletRequest request) throws IOException {
        route(request); identifier(id); return reply("OK", service.read(id));
    }

    /** Approves one exact current provider payload.
     * @param id scoped job
     * @param request exact disclosure request
     * @return current job view
     * @throws IOException unavailable head or serialization
     * @throws InterruptedException interrupted scoped read
     */
    @PostMapping(value = "/jobs/{id}/disclosure", consumes = "application/json")
    byte[] consent(@PathVariable String id, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id); return reply("OK", service.consent(id, body(request)));
    }

    /** Cancels publication and drains owned work.
     * @param id scoped job
     * @param request exact bound cancellation
     * @return terminal job view
     * @throws IOException malformed body or serialization failure
     */
    @PostMapping(value = "/jobs/{id}/cancel", consumes = "application/json")
    byte[] cancel(@PathVariable String id, HttpServletRequest request) throws IOException {
        identifier(id); return reply("OK", service.cancel(id, body(request)));
    }

    /** Returns a short local apply receipt after authoritative revalidation.
     * @param id scoped job
     * @param request exact proposal approval
     * @return draft-only receipt
     * @throws IOException unavailable worker/head or serialization failure
     * @throws InterruptedException interrupted owned validator
     */
    @PostMapping(value = "/jobs/{id}/approve", consumes = "application/json")
    byte[] approve(@PathVariable String id, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id); return reply("OK", service.approve(id, body(request)));
    }

    /** Applies private profile and exact no-query policy before every route.
     * @param request canonical current request
     * @throws AiFailure denied or malformed boundary state
     */
    private void route(HttpServletRequest request) {
        if (access.anonymous()) throw new AiFailure("FORBIDDEN");
        if (request.getQueryString() != null) throw new AiFailure("INVALID_REQUEST");
    }

    /** Bounds raw input before strict JSON allocation.
     * @param request private exact HTTP request
     * @return exact retained bytes
     * @throws IOException unavailable request body
     * @throws AiFailure denied or malformed boundary state
     */
    private byte[] body(HttpServletRequest request) throws IOException {
        route(request);
        byte[] bytes = request.getInputStream().readNBytes(262145);
        if (bytes.length > 262144) throw new AiFailure("INVALID_REQUEST");
        return bytes;
    }

    /** Enforces canonical UUID handles without deriving ownership from spelling.
     * @param id opaque identifier
     * @throws AiFailure denied or malformed boundary state
     */
    private void identifier(String id) {
        if (!java.util.UUID.fromString(id).toString().equals(id)) throw new AiFailure("INVALID_REQUEST");
    }

    /** Encodes the existing bounded protocol envelope.
     * @param status fixed operation outcome
     * @param data defensive nonsecret payload
     * @return bounded JSON bytes
     * @throws IOException serialization failure
     */
    private byte[] reply(String status, com.fasterxml.jackson.databind.JsonNode data) throws IOException {
        return DocumentReplies.encode(java.util.UUID.randomUUID().toString(), status, data);
    }

    /** Emits only safe error categories and never raw infrastructure/provider exceptions.
     * @param failure caught request or infrastructure failure
     * @return non-disclosing response
     * @throws IOException serialization failure
     */
    @ExceptionHandler({AiFailure.class, IOException.class, InterruptedException.class, IllegalArgumentException.class,
            java.util.concurrent.RejectedExecutionException.class})
    ResponseEntity<byte[]> failure(Exception failure) throws IOException {
        if (failure instanceof InterruptedException) Thread.currentThread().interrupt();
        String code = failure instanceof AiFailure denied ? denied.code() : "UNAVAILABLE";
        if (failure instanceof IllegalArgumentException) code = "INVALID_REQUEST";
        int status = code.equals("FORBIDDEN") ? 403 : code.equals("NOT_FOUND") ? 404 : code.equals("UNAVAILABLE") ? 503 : 400;
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(DocumentReplies.status(code));
    }
}
