package dev.allow.backend;

import dev.allow.worker.JsonWire;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Collections;
import java.util.Map;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.filter.OncePerRequestFilter;

/** Enforces exact loopback routing and bearer authority, including authenticated cross-origin requests. */
@Component
final class AuthorityFilter extends OncePerRequestFilter {
    private final LaunchAuthority authority;
    private final DeploymentPolicy policy;
    private final PublicAccess publicAccess;

    /**
     * Stores launch authority.
     * @param authority private verifier
     * @param policy exact routing policy
     * @param publicAccess isolated public profile
     */
    @Autowired
    AuthorityFilter(LaunchAuthority authority, DeploymentPolicy policy, PublicAccess publicAccess) {
        this.authority = authority;
        this.policy = policy;
        this.publicAccess = publicAccess;
    }

    /** Preserves the private-only isolated filter construction seam.
     * @param authority private launch verifier
     * @param policy exact routing policy
     */
    AuthorityFilter(LaunchAuthority authority, DeploymentPolicy policy) {
        this(authority, policy, null);
    }

    /**
     * Checks every request before API dispatch.
     * @param request browser request
     * @param response output
     * @param chain next filters
     * @throws IOException stream failure
     * @throws ServletException dispatch failure
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws IOException, ServletException {
        securityHeaders(response);
        if (!RequestPaths.canonical(request.getRequestURI())) {
            reject(response, 400);
            return;
        }
        if (!validRoute(request)) { reject(response, 403); return; }
        if (publicAccess != null && publicAccess.handle(request, response, chain)) return;
        boolean guarded = !RequestPaths.publicRead(request.getMethod(), request.getRequestURI());
        if (guarded && (!single(request, "Authorization") || !authority.accepts(request.getHeader("Authorization")))) {
            reject(response, 403);
            return;
        }
        chain.doFilter(request, response);
    }

    /** Checks exact routing before public or private authentication branches.
     * @param request canonical request
     * @return accepted Host and optional Origin
     */
    private boolean validRoute(HttpServletRequest request) {
        String origin = request.getHeader("Origin");
        return single(request, "Host") && policy.host(request.getLocalPort()).equals(request.getHeader("Host"))
                && (origin == null || (single(request, "Origin") && origin.equals(policy.origin(request.getLocalPort()))));
    }

    /** Applies non-disclosing security headers to successful and rejected responses.
     * @param response outgoing response
     */
    private void securityHeaders(HttpServletResponse response) {
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("Referrer-Policy", "no-referrer");
        response.setHeader("X-Content-Type-Options", "nosniff");
        response.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'");
    }

    /** Emits a fixed denial without echoing any route, authority or model data.
     * @param response outgoing response
     * @param status canonical-path or authority denial
     * @throws IOException disconnected output
     */
    private void reject(HttpServletResponse response, int status) throws IOException {
        response.setStatus(status);
        response.setContentType("application/json");
        response.getOutputStream().write(JsonWire.encode(Map.of("status", "FORBIDDEN")));
    }

    /**
     * Rejects repeated authority/routing headers.
     * @param request incoming request
     * @param name header name
     * @return one occurrence
     */
    private boolean single(HttpServletRequest request, String name) {
        return Collections.list(request.getHeaders(name)).size() == 1;
    }
}
