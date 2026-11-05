package dev.allow.backend;

/** Fixed public failure categories contain no model, capability or database details. */
final class PublicFailure extends RuntimeException {
    private final int status;
    private final String category;

    /** Stores a content-free HTTP failure.
     * @param status HTTP status
     * @param category closed public category
     */
    PublicFailure(int status, String category) {
        super(category);
        this.status = status;
        this.category = category;
    }

    /** Returns the HTTP denial or capacity status.
     * @return fixed status
     */
    int status() { return status; }

    /** Returns the safe response category.
     * @return fixed category
     */
    String category() { return category; }
}
