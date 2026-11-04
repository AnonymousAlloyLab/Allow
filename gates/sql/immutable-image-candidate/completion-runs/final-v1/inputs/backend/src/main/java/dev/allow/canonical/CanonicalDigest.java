package dev.allow.canonical;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** SHA-256 integrity utility shared by anonymous artifacts and local features. */
final class CanonicalDigest {
    /** Prevents construction of a stateless hashing utility. */
    private CanonicalDigest() { }

    /** Hashes exact bytes using the required JDK SHA-256 provider.
     * @param bytes immutable input view, never retained
     * @return fresh digest bytes
     * @throws IllegalStateException if the required JDK algorithm is unavailable
     */
    static byte[] digest(byte[] bytes) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(bytes);
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    /** Formats the exact artifact digest for integrity checks.
     * @param artifact resolved anonymous artifact
     * @return lowercase hexadecimal SHA-256
     */
    static String hex(AnonymizedArtifact artifact) {
        return HexFormat.of().formatHex(digest(artifact.bytes()));
    }
}
