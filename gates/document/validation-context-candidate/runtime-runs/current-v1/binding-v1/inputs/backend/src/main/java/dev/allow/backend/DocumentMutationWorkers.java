package dev.allow.backend;

import java.io.IOException;

/** Injectable ownership seam keeps coordinator tests independent of real sandbox startup. */
final class DocumentMutationWorkers {
    /** Prevents construction of the factory namespace. */
    private DocumentMutationWorkers() {}

    /** Creates a new validator owner before durable admission can be recorded. */
    interface Factory {
        /** Creates an isolated validator owner without launching a child.
         * @return owned validator
         * @throws IOException unavailable pinned validator installation
         */
        DocumentWorker create() throws IOException;
    }
}
