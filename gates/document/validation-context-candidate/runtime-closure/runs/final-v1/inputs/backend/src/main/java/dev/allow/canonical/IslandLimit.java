package dev.allow.canonical;

/** Signals that typed lowering exceeded its finite input-term budget. */
final class IslandLimit extends RuntimeException {
    private static final long serialVersionUID = 1L;
}
