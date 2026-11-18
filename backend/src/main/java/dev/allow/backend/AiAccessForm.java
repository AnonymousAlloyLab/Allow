package dev.allow.backend;

import java.io.IOException;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Immutable validated applicant data without workspace authority. */
record AiAccessForm(String name, String email, String organization, String purpose, boolean acknowledged) {
    /** Validates the exact challenge schema.
     * @param data untrusted map
     * @return immutable applicant form
     * @throws IOException malformed form
     */
    static AiAccessForm parse(Map<?, ?> data) throws IOException {
        if (!(data.keySet().equals(Set.of("name", "email", "organization", "purpose", "acknowledged", "captchaToken"))
                || data.keySet().equals(Set.of("name", "email", "purpose", "acknowledged", "captchaToken")))
                || !Boolean.TRUE.equals(data.get("acknowledged"))) throw new IOException("Invalid request");
        String email = text(data, "email", 1, 254);
        if (!validEmail(email)) throw new IOException("Invalid request");
        return new AiAccessForm(text(data, "name", 1, 100), email.toLowerCase(Locale.ROOT),
                data.containsKey("organization") ? text(data, "organization", 0, 160) : "", text(data, "purpose", 20, 2000), true);
    }

    /** Reads a bounded string and rejects controls.
     * @param data source map
     * @param key field key
     * @param minimum lower bound
     * @param maximum upper bound
     * @return exact string
     * @throws IOException invalid field
     */
    static String text(Map<?, ?> data, String key, int minimum, int maximum) throws IOException {
        Object value = data.get(key);
        if (!(value instanceof String text) || text.length() < minimum || text.length() > maximum
                || text.chars().anyMatch(Character::isISOControl)) throw new IOException("Invalid request");
        return text;
    }

    /** Checks a bounded ASCII mailbox without header syntax.
     * @param email mailbox
     * @return accepted mailbox syntax
     */
    static boolean validEmail(String email) {
        if (email.length() > 254 || !email.matches("[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+")) return false;
        return email.indexOf('@') <= 64;
    }
}
