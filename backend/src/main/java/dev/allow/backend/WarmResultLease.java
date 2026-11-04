package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;

/** Private staged result whose public bytes require one final owned publication fence. */
final class WarmResultLease implements AutoCloseable {
    private WarmStandby worker;
    private WarmRequestBinding binding;
    private WarmDeadline deadline;
    private JsonNode result;
    private boolean published;

    /** Retains only a cleaned private result until its caller finishes the public envelope.
     * @param worker cleaned exact generation
     * @param binding admitted operation identity
     * @param deadline original success budget
     * @param result complete validated private envelope
     */
    WarmResultLease(WarmStandby worker, WarmRequestBinding binding, WarmDeadline deadline, JsonNode result) {
        this.worker = worker;
        this.binding = binding;
        this.deadline = deadline;
        this.result = result;
    }

    /** Supplies a defensive result copy without granting persistence or publication authority.
     * @return checked private envelope
     * @throws IOException already closed or published lease
     */
    synchronized JsonNode result() throws IOException {
        if (result == null || published) throw new IOException("Warm result lease is closed");
        return result.deepCopy();
    }

    /** Linearizes publication immediately before returning the caller's completed public bytes.
     * @param bytes unchanged public envelope built while the active permit remains held
     * @return exact public bytes after the final generation/build/deadline checks
     * @throws IOException closed, cancelled, expired or unavailable publication
     * @throws InterruptedException caller cancellation
     */
    synchronized byte[] publish(byte[] bytes) throws IOException, InterruptedException {
        if (result == null || published || bytes == null) throw new IOException("Warm publication unavailable");
        worker.publish(binding, deadline);
        published = true;
        clear();
        return bytes;
    }

    /** Cancels an unpublished result and always discards retained private references. */
    @Override
    public synchronized void close() {
        try {
            if (!published && worker != null) worker.abortOperation(binding.nonce());
        } finally { clear(); }
    }

    /** Removes all private and per-operation references from a terminal lease. */
    private void clear() {
        result = null;
        worker = null;
        binding = null;
        deadline = null;
    }
}
