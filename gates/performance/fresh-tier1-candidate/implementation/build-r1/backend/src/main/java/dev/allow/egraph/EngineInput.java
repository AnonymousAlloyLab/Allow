package dev.allow.egraph;
/** Typed mapper capability for one anonymous root.
     * @param context fixed semantic context
     * @param root finite original term
     */
public record EngineInput(Context context, Term root) { }
