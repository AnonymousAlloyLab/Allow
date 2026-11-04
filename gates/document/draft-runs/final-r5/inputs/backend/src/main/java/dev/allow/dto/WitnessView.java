package dev.allow.dto;

import java.util.List;

/** Bounded solver witness with explicit trace and display truncation. */
public record WitnessView(List<StateView> states, int traceLength, int loopState,
                          boolean truncated, String fullInstanceHash) {
    /**
     * Copies states.
     * @param states displayed states
     * @param traceLength full length
     * @param loopState loop successor
     * @param truncated display omission
     * @param fullInstanceHash full-data hash
     */
    public WitnessView {
        states = List.copyOf(states);
    }
}
