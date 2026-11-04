package dev.allow.backend;

import java.net.URI;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Closed deployment routing and advisory worker selection. */
@Component
final class DeploymentPolicy {
    private final String origin;
    private final String tunnelHost;
    private final WorkerLaunchProfile advisoryProfile;

    /** Validates deployment settings before the service can start.
     * @param origin exact public HTTPS origin or empty for local mode
     * @param tunnelHost exact local tunnel authority or empty for local mode
     * @param profile closed advisory profile name
     * @throws IllegalArgumentException malformed settings
     */
    DeploymentPolicy(@Value("${allow.deployment.origin:}") String origin,
                     @Value("${allow.deployment.tunnel-host:}") String tunnelHost,
                     @Value("${allow.document.advisory-profile:DEFAULT}") String profile) {
        if (origin.isEmpty() != tunnelHost.isEmpty()) throw new IllegalArgumentException("Incomplete deployment route");
        if (!origin.isEmpty() && (!validOrigin(origin) || !validTunnel(tunnelHost))) {
            throw new IllegalArgumentException("Invalid deployment route");
        }
        try {
            advisoryProfile = WorkerLaunchProfile.valueOf(profile);
        } catch (IllegalArgumentException error) {
            throw new IllegalArgumentException("Invalid advisory profile", error);
        }
        if (origin.isEmpty() && advisoryProfile != WorkerLaunchProfile.DEFAULT) {
            throw new IllegalArgumentException("Advisory profile requires deployment routing");
        }
        this.origin = origin;
        this.tunnelHost = tunnelHost;
    }

    /** Checks canonical HTTPS DNS origin with an optional nondefault port.
     * @param value configured origin
     * @return whether the origin is canonical
     */
    private boolean validOrigin(String value) {
        try {
            URI uri = URI.create(value);
            String host = uri.getHost();
            if (!"https".equals(uri.getScheme()) || host == null || host.length() > 253
                    || uri.getRawUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null
                    || !uri.getRawPath().isEmpty() || !host.matches("[a-z0-9.-]+")
                    || !host.contains(".") || host.matches("[0-9.]+") || !validLabels(host)) return false;
            int port = uri.getPort();
            if (port == 443 || port == 0 || port > 65535) return false;
            return value.equals("https://" + host + (port == -1 ? "" : ":" + port));
        } catch (IllegalArgumentException error) {
            return false;
        }
    }

    /** Checks DNS labels without accepting empty or hyphen-edge labels.
     * @param host ASCII host name
     * @return whether each label is valid
     */
    private boolean validLabels(String host) {
        for (String label : host.split("\\.", -1)) {
            if (label.length() > 63 || !label.matches("[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")) return false;
        }
        return true;
    }

    /** Checks the fixed IPv4 loopback tunnel authority.
     * @param value tunnel authority
     * @return whether its port is canonical and unprivileged
     */
    private boolean validTunnel(String value) {
        if (!value.matches("127\\.0\\.0\\.1:[1-9][0-9]{0,4}")) return false;
        int port = Integer.parseInt(value.substring("127.0.0.1:".length()));
        return port >= 1024 && port <= 65535;
    }

    /** Returns expected Host for the active mode.
     * @param localPort server port
     * @return exact authority
     */
    String host(int localPort) {
        return tunnelHost.isEmpty() ? "127.0.0.1:" + localPort : tunnelHost;
    }

    /** Returns expected browser Origin for the active mode.
     * @param localPort server port
     * @return exact origin
     */
    String origin(int localPort) {
        return origin.isEmpty() ? "http://127.0.0.1:" + localPort : origin;
    }

    /** Returns the fixed advisory selection.
     * @return advisory launch profile
     */
    WorkerLaunchProfile advisoryProfile() {
        return advisoryProfile;
    }
}
