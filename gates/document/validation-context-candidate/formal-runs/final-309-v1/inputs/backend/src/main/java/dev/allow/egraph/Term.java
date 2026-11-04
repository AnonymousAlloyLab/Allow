package dev.allow.egraph;
import java.util.List;
/** Immutable finite ground term; opaque atoms contain anonymous structural JSON only.
     */
public record Term(String op, Sort sort, String atom, List<Term> children) {
    /** Defensively stores a finite constructor.
     * @param op operator
     * @param sort exact sort
     * @param atom opaque payload
     * @param children ordered operands
     */
    public Term { children = List.copyOf(children); }
    /** Creates a closed operator node.
     * @param op operator
     * @param sort result sort
     * @param children operands
     * @return term
     */
    public static Term node(String op, Sort sort, List<Term> children) { return new Term(op, sort, "", children); }
    /** Creates an opaque anonymous leaf.
     * @param sort resolved sort
     * @param json anonymous structural bytes
     * @return leaf
     */
    public static Term atom(Sort sort, String json) { return new Term("ATOM", sort, json, List.of()); }
    /** Counts tree occurrences rather than shared objects.
     * @return positive tree cost
     */
    public int cost() {
        int result = 1;
        for (Term child : children) result = Math.addExact(result, child.cost());
        return result;
    }
}
