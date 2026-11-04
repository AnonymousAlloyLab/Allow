package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.JsonWire;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.concurrent.RejectedExecutionException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

/** Authenticated read-only corpus API using server-owned record identities and evidence. */
@RestController
@RequestMapping("/api/corpus")
final class CorpusController {
    private final CorpusGateway gateway;

    /** Stores the bounded local corpus bridge.
     * @param gateway supervised metadata/retrieval adapter
     */
    CorpusController(CorpusGateway gateway) { this.gateway = gateway; }

    /** Reports counts, active embedding profiles and quarantine state without model source.
     * @return corpus status envelope
     */
    @GetMapping("/status")
    JsonNode status() { return call("status", "", 20); }

    /** Lists eligible records for selecting a structured retrieval query.
     * @return bounded record metadata
     */
    @GetMapping("/records")
    JsonNode records() { return call("list", "", 20); }

    /** Searches from an existing authorized record; supplied vectors or witness flags are invalid.
     * @param request bounded request body
     * @return ranked candidate envelopes
     * @throws ResponseStatusException malformed request or unavailable corpus
     */
    @PostMapping(value = "/search", consumes = "application/json")
    JsonNode search(HttpServletRequest request) {
        try {
            byte[] body = request.getInputStream().readNBytes(4097);
            if (body.length > 4096) throw new IOException("Request too large");
            Search query = JsonWire.decode(body, Search.class);
            if (query.recordId() == null || !query.recordId().matches("[a-f0-9]{64}")
                    || query.limit() < 1 || query.limit() > 20) throw new IOException("Invalid query");
            return call("search", query.recordId(), query.limit());
        } catch (IOException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Choose a stored record and limit 1–20.");
        }
    }

    /** Maps local failures to bounded public errors without exposing credentials or subprocess logs.
     * @param operation fixed bridge operation
     * @param recordId server-validated content identity
     * @param limit bounded result count
     * @return bridge response
     * @throws ResponseStatusException service capacity or availability error
     */
    private JsonNode call(String operation, String recordId, int limit) {
        try {
            return gateway.request(operation, recordId, limit);
        } catch (RejectedExecutionException error) {
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "Corpus request capacity reached.");
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Corpus request interrupted.");
        } catch (IOException error) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Local corpus is unavailable.");
        }
    }

    /** Immutable strict search input; unsupported JSON fields reject in the shared wire codec. */
    private record Search(String recordId, int limit) {}
}
