package dev.allow.backend;

import dev.allow.worker.JsonWire;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Clock;
import java.util.Collections;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.core.io.ClassPathResource;

/** Separate fail-closed public intake with no workspace authority or token issuance. */
@Component
final class AiAccessRequest {
    private final AiAccessConfig config;
    private final AiAccessTransport transport;
    private final AiAccessState state;
    private final DeploymentPolicy policy;
    /** Loads optional protected configuration; failure leaves intake disabled.
     * @param path external JSON path or blank
     * @param policy exact public origin policy
     * @param installation installation directory
     * @throws IllegalStateException explicit configuration rejected
     */
    @org.springframework.beans.factory.annotation.Autowired
    AiAccessRequest(@Value("${allow.access-request.config:}") String path, DeploymentPolicy policy,
                    @Value("${allow.corpus.root:}") String installation) {
        AiAccessConfig loaded = null;
        try { if (!path.isBlank()) loaded = AiAccessConfig.load(path, java.nio.file.Path.of(installation.isBlank() ? System.getProperty("user.dir") : installation).toAbsolutePath().normalize()); }
        catch (Exception failure) { throw new IllegalStateException("AI access configuration rejected"); }
        config = loaded; this.policy = policy;
        transport = loaded == null ? null : new AiAccessNetwork(loaded, Clock.systemUTC());
        state = loaded == null ? null : new AiAccessState(Clock.systemUTC(), new java.security.SecureRandom(), new AiAccessQueue(loaded.queueDirectory()));
    }
    /** Creates an isolated test instance without network or mail.
     * @param config validated test configuration
     * @param transport fake transport
     * @param state bounded state
     * @param policy route policy
     */
    AiAccessRequest(AiAccessConfig config, AiAccessTransport transport, AiAccessState state, DeploymentPolicy policy) {
        this.config = config; this.transport = transport; this.state = state; this.policy = policy;
    }
    /** Intercepts only the separate exact intake route family.
     * @param request incoming request
     * @param response output
     * @return whether handled
     * @throws IOException disconnected output
     */
    boolean handle(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String path = request.getRequestURI();
        if (!path.startsWith("/api/ai-access/") && !path.equals("/request-ai-access") && !path.startsWith("/request-ai-access/")) return false;
        if (request.getQueryString() != null || request.getHeader("Authorization") != null) { send(response, Map.of("status", "INVALID_REQUEST")); return true; }
        if (path.startsWith("/request-ai-access")) { page(request, response); return true; }
        if (path.equals("/api/ai-access/config") && request.getMethod().equals("GET")) {
            send(response, config == null ? Map.of("enabled", false) : Map.of("enabled", true, "siteKey", config.siteKey())); return true;
        }
        if (config == null) { send(response, Map.of("status", "UNAVAILABLE")); return true; }
        if (!request.getMethod().equals("POST") || Collections.list(request.getHeaders("Origin")).size() != 1
                || !policy.origin(request.getLocalPort()).equals(request.getHeader("Origin"))) { send(response, Map.of("status", "INVALID_REQUEST")); return true; }
        try { send(response, post(path, request)); }
        catch (Exception failure) { send(response, Map.of("status", "INVALID_REQUEST")); }
        return true;
    }
    /** Parses bounded strict JSON and routes the two closed schemas.
     * @param path exact path
     * @param request incoming body
     * @return fixed result
     * @throws IOException malformed body
     */
    private Map<String, Object> post(String path, HttpServletRequest request) throws IOException {
        if (!"application/json".equals(request.getContentType()) || request.getContentLengthLong() > 8192) throw new IOException("Invalid request");
        byte[] bytes = request.getInputStream().readNBytes(8193);
        if (bytes.length > 8192) throw new IOException("Invalid request");
        DocumentJson.decode(bytes);
        Map<?, ?> data = JsonWire.decode(bytes, Map.class);
        if (path.equals("/api/ai-access/challenge")) return challenge(data);
        if (!path.equals("/api/ai-access/verify") || !data.keySet().equals(Set.of("challenge", "code"))) throw new IOException("Invalid request");
        String challenge = AiAccessForm.text(data, "challenge", 43, 43);
        String code = AiAccessForm.text(data, "code", 8, 8);
        if (!challenge.matches("[A-Za-z0-9_-]{43}") || !code.matches("[0-9]{8}")) throw new IOException("Invalid request");
        return state.verify(challenge, code);
    }
    /** Reserves limits and sends code only after verified captcha.
     * @param data closed form
     * @return fixed response
     * @throws IOException invalid form
     */
    private Map<String, Object> challenge(Map<?, ?> data) throws IOException {
        AiAccessForm form = AiAccessForm.parse(data);
        String token = AiAccessForm.text(data, "captchaToken", 1, 4096);
        if (!state.reserve(form.email())) return Map.of("status", "RATE_LIMITED");
        try {
            if (!transport.captcha(token)) return Map.of("status", "UNAVAILABLE");
            long deadline = state.deadline();
            String code = state.code();
            if (!transport.mail(form.email(), code)) return Map.of("status", "UNAVAILABLE");
            return state.activate(form, code, deadline);
        } finally { state.release(); }
    }
    /** Serves exact static resources with separate authoritative CSP.
     * @param request incoming resource request
     * @param response outgoing bytes
     * @throws IOException disconnected output
     */
    private void page(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String path = request.getRequestURI();
        Map<String, String> resources = Map.of("/request-ai-access", "index.html", "/request-ai-access/captcha.html", "captcha.html", "/request-ai-access/captcha.js", "captcha.js");
        if (!request.getMethod().equals("GET") || !resources.containsKey(path)) { send(response, Map.of("status", "INVALID_REQUEST")); return; }
        String file = resources.get(path);
        if (file.equals("captcha.html")) response.setHeader("Content-Security-Policy", "sandbox allow-scripts; default-src 'none'; script-src 'self' https://www.google.com/recaptcha/ https://www.gstatic.com/recaptcha/; frame-src https://www.google.com/recaptcha/ https://recaptcha.google.com/recaptcha/; connect-src https://www.google.com/recaptcha/; style-src 'unsafe-inline'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'");
        else response.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
        ClassPathResource resource = new ClassPathResource("static/request-ai-access/" + file);
        if (!resource.exists()) { send(response, Map.of("status", "UNAVAILABLE")); return; }
        response.setContentType(file.endsWith(".js") ? "text/javascript" : file.endsWith(".css") ? "text/css" : "text/html");
        try (java.io.InputStream input = resource.getInputStream()) { input.transferTo(response.getOutputStream()); }
    }
    /** Emits only fixed status data and opaque generated identifiers.
     * @param response output
     * @param data closed result
     * @throws IOException disconnected output
     */
    private void send(HttpServletResponse response, Map<String, ?> data) throws IOException {
        Object status = data.get("status");
        int code = "INVALID_REQUEST".equals(status) ? 400 : "RATE_LIMITED".equals(status) ? 429 : "UNAVAILABLE".equals(status) ? 503 : 200;
        response.setStatus(code); response.setHeader("Cache-Control", "no-store"); response.setContentType("application/json");
        response.getOutputStream().write(JsonWire.encode(data));
    }
}
