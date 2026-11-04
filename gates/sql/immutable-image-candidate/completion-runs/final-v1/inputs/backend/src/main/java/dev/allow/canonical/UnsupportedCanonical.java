package dev.allow.canonical;

/** Internal fail-closed signal; deliberately contains no source-derived diagnostic. */
final class UnsupportedCanonical extends RuntimeException {
    /** Creates a fixed diagnostic that cannot disclose model identifiers. */
    UnsupportedCanonical() {
        super("Unsupported structural canonical profile");
    }
}
