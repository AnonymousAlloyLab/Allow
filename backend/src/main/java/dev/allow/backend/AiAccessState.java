package dev.allow.backend;

import java.io.IOException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Clock;
import java.util.ArrayDeque;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

/** Synchronized single-process quotas, immutable challenges and durable completion. */
final class AiAccessState {
    private final Clock clock;
    private final SecureRandom random;
    private final AiAccessQueue queue;
    private final Map<String, Pending> challenges = new HashMap<>();
    private final Map<String, ArrayDeque<Long>> emails = new HashMap<>();
    private final ArrayDeque<Long> global = new ArrayDeque<>();
    private final ArrayDeque<Long> verifies = new ArrayDeque<>();
    private int network;
    private int reservations;
    /** Captures immutable form and salted code digest. */
    private record Pending(AiAccessForm form, byte[] salt, byte[] digest, long deadline, int attempts) {}
    /** Stores injectable clock, entropy and queue.
     * @param clock time source
     * @param random secure entropy
     * @param queue durable sink
     */
    AiAccessState(Clock clock, SecureRandom random, AiAccessQueue queue) {
        this.clock = clock; this.random = random; this.queue = queue;
    }
    /** Reserves costs before any external operation, counting failed attempts.
     * @param email normalized mailbox
     * @return reservation accepted
     */
    synchronized boolean reserve(String email) {
        long now = clock.millis();
        cleanup(now);
        if (global.size() >= 10) return false;
        global.addLast(now);
        ArrayDeque<Long> history = emails.get(email);
        if (history == null) { history = new ArrayDeque<>(); emails.put(email, history); }
        if (history.size() >= 3 || (!history.isEmpty() && now - history.getLast() < 60000)) return false;
        history.addLast(now);
        if (network >= 2 || challenges.size() + reservations >= 100) return false;
        network++; reservations++;
        return true;
    }
    /** Releases a reserved external-work slot.
     */
    synchronized void release() { network--; reservations--; }
    /** Generates an unbiased fixed-width eight-digit code.
     * @return ephemeral code
     */
    String code() { return String.format(java.util.Locale.ROOT, "%08d", random.nextInt(100000000)); }
    /** Activates only a successfully delivered challenge before its deadline.
     * @param form immutable applicant
     * @param code ephemeral code
     * @param deadline expiry timestamp
     * @return response or unavailable
     */
    synchronized Map<String, Object> activate(AiAccessForm form, String code, long deadline) {
        if (clock.millis() >= deadline) return Map.of("status", "UNAVAILABLE");
        byte[] salt = new byte[32]; random.nextBytes(salt);
        byte[] id = new byte[32]; random.nextBytes(id);
        String key = Base64.getUrlEncoder().withoutPadding().encodeToString(id);
        challenges.put(key, new Pending(form, salt, digest(salt, code), deadline, 0));
        return Map.of("status", "CODE_SENT", "challenge", key, "expiresAt", deadline);
    }
    /** Returns the new challenge deadline.
     * @return ten-minute deadline
     */
    long deadline() { return clock.millis() + 600000; }
    /** Applies bounded attempts and atomically persists then consumes one request.
     * @param challenge opaque identifier
     * @param code candidate code
     * @return fixed completion response
     */
    synchronized Map<String, Object> verify(String challenge, String code) {
        long now = clock.millis();
        trim(verifies, now - 60000);
        if (verifies.size() >= 60) return Map.of("status", "RATE_LIMITED");
        verifies.addLast(now);
        Pending pending = challenges.get(challenge);
        if (pending == null) return Map.of("status", "INVALID_REQUEST");
        if (now >= pending.deadline() || pending.attempts() >= 5) { challenges.remove(challenge); return Map.of("status", "INVALID_REQUEST"); }
        if (!MessageDigest.isEqual(pending.digest(), digest(pending.salt(), code))) {
            if (pending.attempts() == 4) challenges.remove(challenge);
            else challenges.put(challenge, new Pending(pending.form(), pending.salt(), pending.digest(), pending.deadline(), pending.attempts() + 1));
            return Map.of("status", "INVALID_REQUEST");
        }
        if (clock.millis() >= pending.deadline()) return Map.of("status", "INVALID_REQUEST");
        try {
            String id = queue.persist(pending.form(), clock.millis(), pending.deadline(), clock);
            challenges.remove(challenge);
            return Map.of("status", "REQUESTED", "requestId", id);
        } catch (Exception failure) {
            challenges.remove(challenge);
            return Map.of("status", "UNAVAILABLE");
        }
    }
    /** Drops expired bounded state while preserving active reservation accounting.
     * @param now current time
     */
    private void cleanup(long now) {
        trim(global, now - 3600000);
        var iterator = emails.entrySet().iterator();
        while (iterator.hasNext()) {
            ArrayDeque<Long> history = iterator.next().getValue(); trim(history, now - 3600000);
            if (history.isEmpty()) iterator.remove();
        }
        var pending = challenges.entrySet().iterator();
        while (pending.hasNext()) if (pending.next().getValue().deadline() <= now) pending.remove();
    }
    /** Drops timestamps outside the active window.
     * @param values ordered timestamps
     * @param cutoff inclusive cutoff
     */
    private void trim(ArrayDeque<Long> values, long cutoff) {
        while (!values.isEmpty() && values.getFirst() <= cutoff) values.removeFirst();
    }
    /** Computes a salted code digest without storing plaintext.
     * @param salt independent salt
     * @param code ephemeral code
     * @return digest bytes
     * @throws IllegalStateException missing platform digest
     */
    private byte[] digest(byte[] salt, String code) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update(salt); return digest.digest(code.getBytes(java.nio.charset.StandardCharsets.US_ASCII));
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException("Digest unavailable"); }
    }
}
