package dev.allow.backend;

import dev.allow.worker.JsonWire;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.Semaphore;
import org.springframework.stereotype.Component;

/** Public routing resolves immutable scope and fences bounded response publication. */
@Component
final class PublicAccess {
    private final AccessMode mode;
    private final AnonymousSessions sessions;
    private final JobService jobs;
    private final Semaphore requests = new Semaphore(8);
    private final PublicBudget traffic = new PublicBudget(40, 20, System::nanoTime);

    /** Stores installation-scoped authority and resource owners.
     * @param mode closed installation profile
     * @param sessions bounded capability registry
     * @param jobs global job supervisor
     */
    PublicAccess(AccessMode mode, AnonymousSessions sessions, JobService jobs) {
        this.mode = mode;
        this.sessions = sessions;
        this.jobs = jobs;
    }

    /** Handles public routes only after exact path, Host and Origin validation.
     * @param request canonical current request
     * @param response original response
     * @param chain controller dispatch
     * @return whether this profile fully handled the request
     * @throws IOException disconnected response
     * @throws ServletException private/static controller failure
     */
    boolean handle(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        if (bootstrapConfig(request)) { chain.doFilter(request, response); return true; }
        if (!mode.anonymous()) return false;
        if (RequestPaths.publicRead(request.getMethod(), request.getRequestURI())) {
            chain.doFilter(request, response);
            return true;
        }
        try {
            if (enrollment(request)) enroll(request, response, chain);
            else guarded(request, response, chain);
        } catch (PublicFailure failure) {
            deny(response, failure.status(), failure.category());
        } catch (IOException | ServletException | RuntimeException failure) {
            deny(response, 503, "UNAVAILABLE");
        }
        return true;
    }

    /** Recognizes only the exact nonsecret bootstrap route without query aliases.
     * @param request canonical request
     * @return whether bootstrap configuration is public
     */
    private boolean bootstrapConfig(HttpServletRequest request) {
        return request.getMethod().equals("GET") && request.getRequestURI().equals("/api/public/config")
                && request.getQueryString() == null;
    }

    /** Identifies the single anonymous allocation route.
     * @param request canonical request
     * @return exact enrollment method/path
     */
    private boolean enrollment(HttpServletRequest request) {
        return request.getMethod().equals("POST") && request.getRequestURI().equals("/api/public/workspaces");
    }

    /** Requires explicit same-origin enrollment and stages the one-time capability response.
     * @param request exact-origin bounded enrollment
     * @param response outgoing response
     * @param chain controller dispatch
     * @throws IOException disconnected or oversized response
     * @throws ServletException controller failure
     * @throws PublicFailure invalid origin/enrollment authority or exhausted capacity
     */
    private void enroll(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        if (!single(request, "Origin") || request.getHeader("Authorization") != null
                || request.getQueryString() != null || request.getContentLengthLong() > 1024) {
            throw new PublicFailure(403, "FORBIDDEN");
        }
        if (!requests.tryAcquire()) throw new PublicFailure(429, "WORKSPACE_CAPACITY");
        try {
            PublicResponse staged = new PublicResponse(response);
            chain.doFilter(request, staged);
            staged.prepare();
            PublicWorkspace workspace = PublicWorkspace.from(request);
            if (workspace != null && !workspace.live()) throw new PublicFailure(401, "SESSION_EXPIRED");
            staged.copyBodyToResponse();
        } finally { requests.release(); }
    }

    /** Resolves authority before admitting guarded work or dispatching any private controller.
     * @param request current request
     * @param response original response
     * @param chain bounded controller dispatch
     * @throws IOException disconnected response
     * @throws ServletException controller failure
     * @throws PublicFailure invalid scope, forbidden route or exhausted capacity
     */
    private void guarded(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        if (request.getRequestURI().startsWith("/api/corpus") || !allowedRoute(request.getRequestURI())) {
            throw new PublicFailure(403, "FORBIDDEN");
        }
        if (!single(request, "Authorization")) throw new PublicFailure(401, "SESSION_EXPIRED");
        PublicWorkspace workspace = sessions.resolve(request.getHeader("Authorization"));
        if (!traffic.take() || !requests.tryAcquire()) throw new PublicFailure(429, "REQUEST_CAPACITY");
        boolean costly = request.getMethod().equals("POST");
        boolean entered = false;
        try {
            entered = workspace.enter(costly, jobs);
            if (!entered) throw new PublicFailure(workspace.live() ? 429 : 401,
                    workspace.live() ? "REQUEST_CAPACITY" : "SESSION_EXPIRED");
            workspace.attach(request);
            publish(request, response, chain, workspace);
        } finally {
            if (entered) workspace.leave(costly);
            requests.release();
        }
    }

    /** Exposes only document/job APIs and the caller's lifecycle metadata in public mode.
     * @param path canonical servlet path
     * @return whether scoped dispatch is permitted
     */
    private boolean allowedRoute(String path) {
        return path.equals("/api/config") || path.equals("/api/jobs") || path.startsWith("/api/jobs/")
                || path.equals("/api/v1/documents") || path.startsWith("/api/v1/documents/")
                || path.equals("/api/public/workspaces/current");
    }

    /** Applies the final monotonic publication fence after all synchronous work has returned.
     * @param request owned request
     * @param response original response
     * @param chain controller dispatch
     * @param workspace immutable owner
     * @throws IOException disconnected or oversized body
     * @throws ServletException controller failure
     * @throws PublicFailure authority expired before publication
     */
    private void publish(HttpServletRequest request, HttpServletResponse response, FilterChain chain,
                         PublicWorkspace workspace) throws IOException, ServletException {
        PublicResponse staged = new PublicResponse(response);
        chain.doFilter(request, staged);
        staged.prepare();
        boolean ended = request.getMethod().equals("DELETE")
                && request.getRequestURI().equals("/api/public/workspaces/current") && staged.getStatus() == 204;
        if (!workspace.live() && !ended) throw new PublicFailure(401, "SESSION_EXPIRED");
        staged.copyBodyToResponse();
    }

    /** Checks a single authority-header occurrence rather than a merged value.
     * @param request current request
     * @param name header name
     * @return exactly one occurrence
     */
    private boolean single(HttpServletRequest request, String name) {
        return Collections.list(request.getHeaders(name)).size() == 1;
    }

    /** Writes only fixed rejection categories; staged private bodies are discarded.
     * @param response original response
     * @param status denial/capacity status
     * @param category fixed category
     * @throws IOException disconnected client
     */
    private void deny(HttpServletResponse response, int status, String category) throws IOException {
        response.resetBuffer();
        response.setStatus(status);
        response.setHeader("Content-Length", null);
        response.setContentType("application/json");
        if (status == 429) response.setHeader("Retry-After", "60");
        response.getOutputStream().write(JsonWire.encode(Map.of("status", category)));
    }
}
