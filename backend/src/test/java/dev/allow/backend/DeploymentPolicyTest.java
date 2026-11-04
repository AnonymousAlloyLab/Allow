package dev.allow.backend;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Closed deployment configuration tests. */
class DeploymentPolicyTest {
    /** Confirms local and explicit deployment values. */
    @Test
    void validPolicies() {
        DeploymentPolicy local = new DeploymentPolicy("", "", "DEFAULT");
        assertEquals("127.0.0.1:8080", local.host(8080));
        assertEquals("http://127.0.0.1:8080", local.origin(8080));
        DeploymentPolicy remote = new DeploymentPolicy("https://allow.example:8443", "127.0.0.1:18081",
                "DOCUMENT_ADVISORY_TIER1");
        assertEquals("127.0.0.1:18081", remote.host(8080));
        assertEquals("https://allow.example:8443", remote.origin(8080));
        assertEquals(WorkerLaunchProfile.DOCUMENT_ADVISORY_TIER1, remote.advisoryProfile());
    }

    /** Rejects malformed, incomplete and unknown settings. */
    @Test
    void invalidPolicies() {
        for (String origin : new String[]{"http://allow.example", "https://ALLOW.example", "https://1.2.3.4",
                "https://allow.example/", "https://allow.example:443", "https://user@allow.example",
                "https://allow.example?x", "https://allow.example#x", "https://-bad.example", "https://allow"}) {
            rejected(origin, "127.0.0.1:18081", "DEFAULT");
        }
        rejected("https://allow.example", "", "DEFAULT");
        rejected("", "127.0.0.1:18081", "DEFAULT");
        rejected("https://allow.example", "127.0.0.1:80", "DEFAULT");
        rejected("https://allow.example", "localhost:18081", "DEFAULT");
        rejected("", "", "-XX:TieredStopAtLevel=1");
        rejected("", "", "DOCUMENT_ADVISORY_TIER1");
    }

    /** Checks one configuration fails closed.
     * @param origin requested origin
     * @param host requested host
     * @param profile requested profile
     */
    private void rejected(String origin, String host, String profile) {
        try {
            new DeploymentPolicy(origin, host, profile);
            fail("Invalid settings accepted: " + origin + " " + host + " " + profile);
        } catch (IllegalArgumentException expected) {
            assertNotNull(expected.getMessage());
        }
    }
}
