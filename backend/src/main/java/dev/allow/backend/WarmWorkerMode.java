package dev.allow.backend;

/** Fixed installed entrypoints; neither browser input nor environment selects a mode. */
enum WarmWorkerMode {
    WARM_DOCUMENT("warm-document"), FRESH_DOCUMENT("fresh-document"), FRESH_SOLVER("fresh-solver");
    private final String argument;

    /** Stores one closed helper mode.
     * @param argument fixed installed helper argument
     */
    WarmWorkerMode(String argument) { this.argument = argument; }

    /** Returns the trusted command argument.
     * @return one of the three installed modes
     */
    String argument() { return argument; }
}
