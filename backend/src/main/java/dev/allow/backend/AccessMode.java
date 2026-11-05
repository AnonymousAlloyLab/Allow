package dev.allow.backend;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Closed installation profile; public enrollment never reuses private launch authority. */
@Component
final class AccessMode {
    private final boolean anonymous;

    /** Validates the operator-selected profile before any public route is enabled.
     * @param value PRIVATE or ANONYMOUS
     * @throws IllegalArgumentException unknown access profile
     */
    AccessMode(@Value("${allow.access-mode:PRIVATE}") String value) {
        if (!java.util.Set.of("PRIVATE", "ANONYMOUS").contains(value)) {
            throw new IllegalArgumentException("Unknown access mode");
        }
        anonymous = value.equals("ANONYMOUS");
    }

    /** Indicates whether capabilities must resolve to isolated temporary scopes.
     * @return public profile selection
     */
    boolean anonymous() { return anonymous; }
}
