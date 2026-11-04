package dev.allow.egraph;
import java.util.List;
/** Exact anonymous module, selected root and fixed opaque inventory.
     */
public record Context(String module, List<Integer> rootPath, List<Term> atoms) {
    /** Copies context collections.
     * @param module exact anonymous module
     * @param rootPath numeric root address
     * @param atoms ordered unique atoms
     */
    public Context { rootPath = List.copyOf(rootPath); atoms = List.copyOf(atoms); }
    /** Orders an inventory entry by exact compact anonymous JSON.
     * @param term opaque atom
     * @return stable sort key
     */
    public static String atomKey(Term term) { return Wire.json(List.of(term.sort(), term.atom())); }
}
