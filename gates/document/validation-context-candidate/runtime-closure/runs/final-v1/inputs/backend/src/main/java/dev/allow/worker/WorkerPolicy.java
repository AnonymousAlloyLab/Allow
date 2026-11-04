package dev.allow.worker;

import edu.mit.csail.sdg.parser.CompModule;

/** Narrow child-only bridge to the existing whole-module and solver-resource policy. */
public final class WorkerPolicy {
    /** Prevents construction of the stateless policy bridge. */
    private WorkerPolicy() {}

    /** Applies the installed policy to the whole module and every parsed command.
     * @param world bounded, exact-source parsed module
     * @throws IllegalArgumentException unsupported import, bounds or AST resources
     */
    public static void check(CompModule world) {
        AstPolicy.checkAll(world);
    }
}
