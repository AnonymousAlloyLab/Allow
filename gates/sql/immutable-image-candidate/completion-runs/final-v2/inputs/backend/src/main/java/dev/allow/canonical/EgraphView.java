package dev.allow.canonical;

import dev.allow.egraph.IslandResult;
import java.util.List;

/** Bounded collection of anonymous optimization islands.
     */
public record EgraphView(String profile, String rulesetDigest, String status,
        List<IslandResult> islands, boolean truncated) {
    /** Freezes the result collection.
     * @param profile output profile
     * @param rulesetDigest catalog identity
     *
     * @param status adapter status
     * @param islands bounded results
     * @param truncated omitted islands
     */
    public EgraphView { islands = List.copyOf(islands); }
}
