package dev.allow.corpus;

/** One immutable isolated corpus request.
 * @param protocol wire version
 * @param source original source
 * @param sourceHash UTF-8 SHA-256
 * @param targetSlot function slot, or -1 for discovery
 * @param N requested distinct examples per polarity
 * @param requestId private request identity
 * @param toolchain supervisor build identity
 */
public record CorpusRequest(int protocol, String source, String sourceHash, int targetSlot, int N,
                            String requestId, String toolchain) { }
