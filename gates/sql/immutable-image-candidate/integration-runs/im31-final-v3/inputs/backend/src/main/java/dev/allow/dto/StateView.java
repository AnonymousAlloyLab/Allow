package dev.allow.dto;

import java.util.List;

/** A single trace state; states are never merged into a fictitious instance. */
public record StateView(List<AtomView> atoms, List<RelationView> relations) {
    /**
     * Copies state data.
     * @param atoms distinct atoms
     * @param relations ordered tuples
     */
    public StateView {
        atoms = List.copyOf(atoms);
        relations = List.copyOf(relations);
    }
}
