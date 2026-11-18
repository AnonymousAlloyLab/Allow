package dev.allow.backend;

/** Injectable bounded external operations; implementations never return provider details. */
interface AiAccessTransport {
    /** Verifies a single captcha token.
     * @param token opaque provider token
     * @return verified provider result
     */
    boolean captcha(String token);
    /** Sends the fixed verification message.
     * @param email validated mailbox
     * @param code eight-digit code
     * @return whether SMTP completed
     */
    boolean mail(String email, String code);
}
