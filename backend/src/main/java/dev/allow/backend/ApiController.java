package dev.allow.backend;

import dev.allow.dto.JobRequest;
import dev.allow.dto.JobView;
import dev.allow.worker.JsonWire;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.RejectedExecutionException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

/** Authenticated local API; request body allocation is explicitly bounded. */
@RestController
@RequestMapping("/api")
final class ApiController {
    private final JobService jobs;

    /**
     * Stores the bounded job supervisor.
     * @param jobs job owner
     */
    ApiController(JobService jobs) {
        this.jobs = jobs;
    }

    /**
     * Queues an exact-source candidate.
     * @param request bounded HTTP request
     * @return identity-bound job
     * @throws ResponseStatusException malformed or rejected request
     */
    @PostMapping(value = "/jobs", consumes = "application/json")
    JobView submit(HttpServletRequest request) {
        try {
            byte[] body = request.getInputStream().readNBytes(262145);
            if (body.length > 262144) throw new IllegalArgumentException("Request too large.");
            return jobs.submit(JsonWire.decode(body, JobRequest.class), owner(request));
        } catch (IOException | IllegalArgumentException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid candidate.");
        } catch (RejectedExecutionException error) {
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "Job capacity reached.");
        }
    }

    /**
     * Reads one job.
     * @param id opaque identity
     * @param request authenticated scoped request
     * @return immutable state
     */
    @GetMapping("/jobs/{id}")
    JobView get(@PathVariable String id, HttpServletRequest request) {
        return require(jobs.get(id, owner(request)));
    }

    /**
     * Cancels one job without creating absence evidence.
     * @param id opaque identity
     * @param request authenticated scoped request
     * @return absorbing cancelled or prior terminal state
     */
    @DeleteMapping("/jobs/{id}")
    JobView cancel(@PathVariable String id, HttpServletRequest request) {
        return require(jobs.cancel(id, owner(request)));
    }

    /**
     * Reports capabilities without source or launch secrets.
     * @return local limits and assurance boundary
     */
    @GetMapping("/config")
    Map<String, Object> config() {
        return Map.of("sourceBytes", 32768, "activeWorkers", 1, "queueLimit", 4,
                "solver", "Alloy 6.2.0 / SAT4J 2.3.1", "assurance", "BOUNDED_ONLY",
                "canonicalProfile", "allow-slot-ast-v1", "remoteEmbedding", false,
                "maxScopeAndBitwidth", 8, "maxTrace", 10, "noOverflow", true);
    }

    /** Resolves job ownership from only the trusted request attribute.
     * @param request authenticated request
     * @return immutable public owner or private sentinel
     */
    private String owner(HttpServletRequest request) {
        PublicWorkspace workspace = PublicWorkspace.from(request);
        return workspace == null ? "" : workspace.owner();
    }

    /**
     * Converts unknown ids into a content-free 404.
     * @param view nullable lookup
     * @return existing job
     * @throws ResponseStatusException unknown job
     */
    private JobView require(JobView view) {
        if (view == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        return view;
    }
}
