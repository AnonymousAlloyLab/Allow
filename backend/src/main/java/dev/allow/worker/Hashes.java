package dev.allow.worker;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Shared exact-byte SHA-256 identity; digests are never semantic proofs. */
public final class Hashes {
    /** Prevents construction of the stateless utility. */
    private Hashes() {}

    /**
     * Hashes exact UTF-8 source.
     * @param value source text
     * @return lowercase SHA-256
     */
    public static String text(String value) {
        return bytes(value.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Hashes a complete byte sequence.
     * @param value bytes
     * @return lowercase SHA-256
     */
    public static String bytes(byte[] value) {
        return HexFormat.of().formatHex(digest().digest(value));
    }

    /**
     * Creates an independent streaming digest.
     * @return SHA-256 engine
     * @throws IllegalStateException unavailable SHA256 provider
     */
    public static MessageDigest digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }
}
