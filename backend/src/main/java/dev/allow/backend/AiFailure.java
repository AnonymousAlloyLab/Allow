package dev.allow.backend;

/** Fixed non-disclosing AI boundary outcome. */
final class AiFailure extends RuntimeException {
    private final String code;

    /** Retains only a closed boundary category.
     * @param code safe constant selected by trusted code
     */
    AiFailure(String code) { super(code); this.code = code; }

    /** Returns the nonsecret public category.
     * @return fixed code
     */
    String code() { return code; }
}
