package dev.allow.backend;

import java.net.InetAddress;
import java.net.UnknownHostException;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.boot.web.servlet.server.ConfigurableServletWebServerFactory;
import org.springframework.stereotype.Component;

/** Enforces literal IPv4 loopback even if a generic Spring environment overrides server.address. */
@Component
final class LoopbackBinding implements WebServerFactoryCustomizer<ConfigurableServletWebServerFactory> {
    /**
     * Pins the listener independently of command-line Spring address options.
     * @param factory servlet listener
     * @throws IllegalStateException impossible invalid four-byte address
     */
    @Override
    public void customize(ConfigurableServletWebServerFactory factory) {
        try {
            factory.setAddress(InetAddress.getByAddress(new byte[]{127, 0, 0, 1}));
        } catch (UnknownHostException error) {
            throw new IllegalStateException("Loopback address unavailable", error);
        }
    }
}
