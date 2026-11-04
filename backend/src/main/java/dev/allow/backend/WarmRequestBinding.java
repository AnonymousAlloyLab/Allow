package dev.allow.backend;

import java.util.Objects;
import java.util.UUID;

/** Server-created immutable identity binding for one fresh context and one handoff.
 * @param nonce fresh server operation identity
 * @param requestHash hash of the exact advisory HTTP body
 * @param document authorized document identity
 * @param revision requested immutable base revision
 * @param policy installed validation policy
 * @param build full installed executable identity
 * @param poolNonce owning pool incarnation
 */
record WarmRequestBinding(String nonce, String requestHash, String document, long revision,
        String policy, String build, String poolNonce) {
    /** Rejects incomplete internal identities before creating a context permit.
     * @param nonce fresh server operation identity
     * @param requestHash hash of exact request bytes
     * @param document authorized document identity
     * @param revision immutable base revision
     * @param policy installed policy
     * @param build full installed executable identity
     * @param poolNonce pool incarnation
     * @throws IllegalArgumentException malformed internal identity
     * @throws NullPointerException absent identity component
     */
    WarmRequestBinding {
        canonicalUuid(Objects.requireNonNull(nonce));
        canonicalUuid(Objects.requireNonNull(poolNonce));
        Objects.requireNonNull(document);
        Objects.requireNonNull(policy);
        if (!document.startsWith("server:") || policy.isBlank()) throw new IllegalArgumentException("Invalid context scope");
        canonicalUuid(document.substring(7));
        if (!Objects.requireNonNull(requestHash).matches("[0-9a-f]{64}")
                || !Objects.requireNonNull(build).matches("[0-9a-f]{64}") || revision < 0 || revision > 9007199254740991L) {
            throw new IllegalArgumentException("Invalid advisory binding");
        }
    }

    /** Requires the same canonical UUID spelling used by the closed server protocols.
     * @param value internal identity spelling
     * @throws IllegalArgumentException noncanonical or malformed UUID
     */
    private static void canonicalUuid(String value) {
        if (!UUID.fromString(value).toString().equals(value)) throw new IllegalArgumentException("Invalid canonical identity");
    }
}
