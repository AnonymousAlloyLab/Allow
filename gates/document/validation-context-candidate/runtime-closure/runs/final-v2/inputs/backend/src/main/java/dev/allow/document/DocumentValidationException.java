package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;

/** A deterministic document validation denial with a defensive diagnostic snapshot. */
public final class DocumentValidationException extends Exception {
    private final String code;
    private final JsonNode diagnostics;

    /**
     * Creates a deterministic rejection.
     * @param code stable rejection category
     * @param diagnostics bounded structured diagnostics
     */
    public DocumentValidationException(String code, JsonNode diagnostics) {
        super(code);
        this.code = code;
        this.diagnostics = diagnostics.deepCopy();
    }

    /**
     * Returns the rejection category.
     * @return stable category
     */
    public String code() {
        return code;
    }

    /**
     * Returns a fresh diagnostic snapshot.
     * @return isolated diagnostic data
     */
    public JsonNode diagnostics() {
        return diagnostics.deepCopy();
    }
}
