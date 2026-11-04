package dev.allow.dto;

import java.util.List;

/** Ordered relation tuples; tuple positions are semantically significant. */
public record RelationView(String name, int arity, List<List<String>> tuples) {
    /**
     * Copies tuples to prevent callers mutating witness data.
     * @param name label
     * @param arity column count
     * @param tuples ordered rows
     */
    public RelationView {
        tuples = tuples.stream().map(List::copyOf).toList();
    }
}
