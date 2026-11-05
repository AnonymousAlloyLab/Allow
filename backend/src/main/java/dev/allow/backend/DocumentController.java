package dev.allow.backend;

import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Bearer-authenticated document API with bounded reads before JSON allocation. */
@RestController
@RequestMapping(value = "/api/v1/documents", produces = "application/json")
final class DocumentController {
    private final DocumentMutations mutations;
    private final DocumentQueries queries;
    private final AiService ai;

    /** Stores the independent command and query services behind the existing authority filter.
     * @param mutations serialized durable mutation coordinator
     * @param queries scoped reads and isolated previews
     * @param ai bounded private AI cancellation coordinator
     */
    @org.springframework.beans.factory.annotation.Autowired
    DocumentController(DocumentMutations mutations, DocumentQueries queries, AiService ai) {
        this.mutations = mutations;
        this.queries = queries;
        this.ai = ai;
    }

    /** Preserves isolated document tests without introducing AI authority.
     * @param mutations existing scoped mutation coordinator
     * @param queries existing document queries
     */
    DocumentController(DocumentMutations mutations, DocumentQueries queries) { this(mutations, queries, null); }

    /** Drains conflicting background AI before an ordinary manual admission.
     * @param document affected document, or null for workspace create
     */
    private void preempt(String document) { if (ai != null) ai.preempt(document); }

    /** Lists only the authenticated workspace's bounded document summaries.
     * @param request authenticated scoped request
     * @return JSON envelope
     * @throws IOException store unavailable
     * @throws InterruptedException interrupted bridge
     */
    @GetMapping
    byte[] list(HttpServletRequest request) throws IOException, InterruptedException { return queries(request).list(); }

    /** Creates revision zero and its exact idempotent creation receipt.
     * @param request bounded original HTTP intent
     * @return original stored response or truthful availability outcome
     * @throws IOException malformed body or unavailable pre-admission infrastructure
     * @throws InterruptedException interrupted coordinator
     */
    @PostMapping(consumes = "application/json")
    byte[] create(HttpServletRequest request) throws IOException, InterruptedException {
        return mutation(request, "CREATE", "CREATE");
    }

    /** Reads a head or retained immutable revision without granting scope through the path.
     * @param id owned server document identifier
     * @param revision optional historical revision
     * @param request authenticated scoped request
     * @return accepted artifact with revision envelope
     * @throws IOException unavailable snapshot
     * @throws InterruptedException interrupted store
     * @throws IllegalArgumentException invalid historical revision
     */
    @GetMapping("/{id}")
    byte[] read(@PathVariable String id, @RequestParam(required = false) Long revision, HttpServletRequest request)
            throws IOException, InterruptedException {
        identifier(id);
        if (revision != null && (revision < 0 || revision > 9007199254740991L)) throw new IllegalArgumentException("Invalid revision");
        return queries(request).read(id, revision);
    }

    /** Validates a draft diagnostically without creating an accepted revision.
     * @param id owned document
     * @param request exact bounded advisory request
     * @return request-bound preview or diagnostics
     * @throws IOException malformed request or unavailable validator
     * @throws InterruptedException interrupted child after reaping
     */
    @PostMapping(value = "/{id}/validate", consumes = "application/json")
    byte[] validate(@PathVariable String id, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id);
        preempt(id);
        return queries(request).validate(id, body(request));
    }

    /** Appends a fully checked candidate under exact receipt, policy and revision fences.
     * @param id owned document
     * @param request exact original intent
     * @return committed/replayed receipt or truthful failure outcome
     * @throws IOException malformed request or unavailable pre-admission service
     * @throws InterruptedException interrupted coordinator
     */
    @PostMapping(value = "/{id}/commit", consumes = "application/json")
    byte[] commit(@PathVariable String id, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id);
        return mutation(request, id, "COMMIT");
    }

    /** Restores explicitly selected historical content as a fresh current-policy revision.
     * @param id owned document
     * @param request target revision, direction and exact retry key
     * @return immutable outcome without mutating prior history
     * @throws IOException malformed request or unavailable pre-admission service
     * @throws InterruptedException interrupted coordinator
     */
    @PostMapping(value = "/{id}/history-copy", consumes = "application/json")
    byte[] history(@PathVariable String id, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id);
        return mutation(request, id, "HISTORY_COPY");
    }

    /** Resolves an accepted command key server-side before submitting bounded analysis.
     * @param id owned document
     * @param request accepted revision, command identity and presentation epoch
     * @return job with complete accepted evidence identity
     * @throws IOException unavailable artifact or solver
     * @throws InterruptedException interrupted store call
     */
    @PostMapping(value = "/{id}/analyze", consumes = "application/json")
    byte[] analyze(@PathVariable String id, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id);
        preempt(id);
        return queries(request).analyze(id, body(request));
    }

    /** Polls accepted-document evidence without using the legacy draft-only result identity.
     * @param id owned document
     * @param job opaque job identifier
     * @param request authenticated scoped request
     * @return labeled current or historical result
     * @throws IOException unknown or unavailable evidence
     * @throws InterruptedException interrupted store read
     */
    @GetMapping("/{id}/analysis/{job}")
    byte[] analysis(@PathVariable String id, @PathVariable String job, HttpServletRequest request) throws IOException, InterruptedException {
        identifier(id);
        return queries(request).analysis(id, job);
    }

    /** Converts only pre-admission/query failures; mutation uncertainty is handled by its coordinator.
     * @param failure bounded request or infrastructure error
     * @return content-free error envelope
     * @throws IOException serialization failure
     */
    @ExceptionHandler({IOException.class, InterruptedException.class, IllegalArgumentException.class,
            java.util.concurrent.RejectedExecutionException.class})
    ResponseEntity<byte[]> failure(Exception failure) throws IOException {
        if (failure instanceof InterruptedException) Thread.currentThread().interrupt();
        boolean malformed = failure instanceof IllegalArgumentException;
        return ResponseEntity.status(malformed ? 400 : 503).contentType(MediaType.APPLICATION_JSON)
                .body(DocumentReplies.status(malformed ? "INVALID_REQUEST" : "UNAVAILABLE"));
    }

    /** Preserves the exact raw route and body when constructing receipt authority.
     * @param request authenticated HTTP request
     * @param document owned document or reserved CREATE
     * @param operation server-selected operation
     * @return serialized outcome
     * @throws IOException malformed request or unavailable pre-admission bridge
     * @throws InterruptedException interrupted coordinator
     * @throws IllegalArgumentException unsupported mutation query parameters
     */
    private byte[] mutation(HttpServletRequest request, String document, String operation)
            throws IOException, InterruptedException {
        if (request.getQueryString() != null) throw new IllegalArgumentException("Mutation query parameters unsupported");
        preempt(document.equals("CREATE") ? null : document);
        return mutations(request).mutate(new DocumentRequest(document, request.getRequestURI(), operation, body(request)));
    }

    /** Resolves only the trusted request's immutable query owner.
     * @param request authenticated request
     * @return scoped or existing private queries
     */
    private DocumentQueries queries(HttpServletRequest request) {
        PublicWorkspace workspace = PublicWorkspace.from(request);
        return workspace == null ? queries : workspace.queries();
    }

    /** Resolves only the trusted request's immutable mutation owner.
     * @param request authenticated request
     * @return scoped or existing private mutations
     */
    private DocumentMutations mutations(HttpServletRequest request) {
        PublicWorkspace workspace = PublicWorkspace.from(request);
        return workspace == null ? mutations : workspace.mutations();
    }

    /** Enforces the complete HTTP byte budget before JSON parsing or draft expansion.
     * @param request input stream owner
     * @return exact original body
     * @throws IOException failed body read
     * @throws IllegalArgumentException excess request size
     */
    private byte[] body(HttpServletRequest request) throws IOException {
        byte[] bytes = request.getInputStream().readNBytes(262145);
        if (bytes.length > 262144) throw new IllegalArgumentException("Request exceeds limit");
        return bytes;
    }

    /** Checks canonical server identifiers without deriving authority from their spelling.
     * @param id decoded path identifier
     * @throws IllegalArgumentException invalid path identifier
     */
    private void identifier(String id) {
        if (!id.matches("server:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")) {
            throw new IllegalArgumentException("Invalid document identifier");
        }
    }
}
