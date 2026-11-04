package dev.allow.dto;

import java.util.List;

/** One readable atom with all returned signature memberships. */
public record AtomView(String id, List<String> memberships) {
    /**
     * Copies memberships.
     * @param id atom identity
     * @param memberships signature labels
     */
    public AtomView {
        memberships = List.copyOf(memberships);
    }
}
