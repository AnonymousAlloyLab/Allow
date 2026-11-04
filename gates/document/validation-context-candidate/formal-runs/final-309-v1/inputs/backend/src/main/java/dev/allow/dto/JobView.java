package dev.allow.dto;

import dev.allow.canonical.CanonicalView;
import java.util.List;

/** Immutable public job state, bound to exact source and presentation identity. */
public record JobView(String jobId, String status, String sourceHash, long revision, long epoch,
                      String analysisKey, String commandKind, String message,
                      List<CommandView> commands, CanonicalView canonical, WitnessView witness) {
    /**
     * Copies command metadata.
     * @param jobId job identity
     * @param status state
     * @param sourceHash exact source hash
     * @param revision source revision
     * @param epoch presentation epoch
     * @param analysisKey exact analysis identity
     * @param commandKind run/check
     * @param message safe diagnostic
     * @param commands selections
     * @param canonical anonymous artifact
     * @param witness solver witness
     */
    public JobView {
        commands = List.copyOf(commands);
    }
}
