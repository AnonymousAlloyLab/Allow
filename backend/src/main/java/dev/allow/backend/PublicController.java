package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.time.Instant;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Narrow anonymous enrollment and capability-scoped lifecycle endpoints. */
@RestController
@RequestMapping("/api/public")
final class PublicController {
    private final AnonymousSessions sessions;

    /** Stores the bounded server-owned session allocator.
     * @param sessions installation registry
     */
    PublicController(AnonymousSessions sessions) { this.sessions = sessions; }

    /** Returns nonsecret configuration for both private and anonymous clients.
     * @return closed presentation configuration
     */
    @GetMapping("/config")
    Map<String, Object> configuration() { return sessions.configuration(); }

    /** Accepts only an empty bounded JSON enrollment intent.
     * @param request exact-origin request admitted by the filter
     * @return fresh capability once
     * @throws IOException malformed or oversized input
     * @throws PublicFailure enrollment request exceeds its limit
     */
    @PostMapping(value = "/workspaces", consumes = "application/json")
    ResponseEntity<Map<String, Object>> create(HttpServletRequest request) throws IOException {
        byte[] bytes = request.getInputStream().readNBytes(1025);
        if (bytes.length > 1024) throw new PublicFailure(400, "INVALID_REQUEST");
        JsonNode body = DocumentJson.request(bytes);
        DocumentJson.fields(body);
        Map<String, Object> result = sessions.create();
        sessions.resolve("Bearer " + result.get("token")).attach(request);
        return ResponseEntity.status(201).body(result);
    }

    /** Reports only the current capability's expiration, never other workspaces.
     * @param request authenticated session request
     * @return nonsecret current session metadata
     */
    @GetMapping("/workspaces/current")
    Map<String, Object> current(HttpServletRequest request) {
        PublicWorkspace workspace = require(request);
        return Map.of("mode", "ANONYMOUS", "expiresAt", Instant.ofEpochMilli(workspace.expiresAt()).toString(),
                "lifetimeSeconds", workspace.remainingSeconds());
    }

    /** Revokes the current capability; asynchronous drain retains its capacity slot.
     * @param request authenticated session request
     * @return empty acknowledgement of access revocation, not physical erasure
     */
    @DeleteMapping("/workspaces/current")
    ResponseEntity<Void> end(HttpServletRequest request) {
        require(request).retire();
        return ResponseEntity.noContent().build();
    }

    /** Resolves only filter-installed authority.
     * @param request current request
     * @return current scoped services
     * @throws PublicFailure absent or expired authority
     */
    private PublicWorkspace require(HttpServletRequest request) {
        PublicWorkspace workspace = PublicWorkspace.from(request);
        if (workspace == null || !workspace.live()) throw new PublicFailure(401, "SESSION_EXPIRED");
        return workspace;
    }

    /** Emits fixed capacity/expiry errors without exception details.
     * @param failure bounded public failure
     * @return content-free error
     */
    @ExceptionHandler(PublicFailure.class)
    ResponseEntity<Map<String, String>> failed(PublicFailure failure) {
        return ResponseEntity.status(failure.status()).header("Retry-After", "60")
                .body(Map.of("status", failure.category()));
    }

    /** Prevents malformed enrollment bodies from disclosing parser diagnostics.
     * @param failure invalid original request
     * @return fixed malformed-request response
     */
    @ExceptionHandler({IOException.class, IllegalArgumentException.class})
    ResponseEntity<Map<String, String>> invalid(Exception failure) {
        return ResponseEntity.badRequest().body(Map.of("status", "INVALID_REQUEST"));
    }
}
