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
import org.springframework.web.filter.OncePerRequestFilter;

/** Enforces exact loopback routing and bearer authority, including authenticated cross-origin requests. */
@Component
final class AuthorityFilter extends OncePerRequestFilter {
    private final LaunchAuthority authority;

    /**
     * Stores launch authority.
     * @param authority private verifier
     */
    AuthorityFilter(LaunchAuthority authority) {
        this.authority = authority;
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
        String host = "127.0.0.1:" + request.getLocalPort();
        String origin = request.getHeader("Origin");
        boolean valid = single(request, "Host") && host.equals(request.getHeader("Host"))
                && (origin == null || (single(request, "Origin") && origin.equals("http://" + host)));
        boolean api = request.getRequestURI().startsWith("/api/");
        if (!valid || (api && (!single(request, "Authorization")
                || !authority.accepts(request.getHeader("Authorization"))))) {
            response.setStatus(403);
            response.setContentType("application/json");
            response.getOutputStream().write(JsonWire.encode(Map.of("status", "FORBIDDEN")));
            return;
        }
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("Referrer-Policy", "no-referrer");
        response.setHeader("X-Content-Type-Options", "nosniff");
        response.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'");
        chain.doFilter(request, response);
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
